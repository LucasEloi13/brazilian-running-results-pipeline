import hashlib
import logging
from datetime import date as dt_date
from typing import Any

from src.database.connections.postgres import PostgresConnection
from psycopg2.extras import execute_values

logger = logging.getLogger("EventNameStorage")

UNKNOWN_STATE_ABBR = "NI"
UNKNOWN_STATE_NAME = "Não informado"
UNKNOWN_CITY_NAME = "Não informado"


STATE_NAME_BY_ABBR = {
	"AC": "Acre",
	"AL": "Alagoas",
	"AP": "Amapá",
	"AM": "Amazonas",
	"BA": "Bahia",
	"CE": "Ceará",
	"DF": "Distrito Federal",
	"ES": "Espírito Santo",
	"GO": "Goiás",
	"MA": "Maranhão",
	"MT": "Mato Grosso",
	"MS": "Mato Grosso do Sul",
	"MG": "Minas Gerais",
	"PA": "Pará",
	"PB": "Paraíba",
	"PR": "Paraná",
	"PE": "Pernambuco",
	"PI": "Piauí",
	"RJ": "Rio de Janeiro",
	"RN": "Rio Grande do Norte",
	"RS": "Rio Grande do Sul",
	"RO": "Rondônia",
	"RR": "Roraima",
	"SC": "Santa Catarina",
	"SP": "São Paulo",
	"SE": "Sergipe",
	"TO": "Tocantins",
}


class EventNameStorage:
	CACHE_MAX_SIZE = 50_000

	def __init__(self, db: PostgresConnection | None = None):
		self.db = db or PostgresConnection()
		self._state_cache: dict[str, int] = {}
		self._city_cache: dict[tuple[str, int], int] = {}
		self._date_cache: dict[dt_date, int] = {}

	@staticmethod
	def build_slug_hash(slug: str) -> str:
		normalized_slug = (slug or "").strip().lower()
		return hashlib.md5(normalized_slug.encode("utf-8")).hexdigest()

	@staticmethod
	def _bounded_set(cache: dict, key: Any, value: Any) -> None:
		if len(cache) >= EventNameStorage.CACHE_MAX_SIZE:
			cache.clear()
		cache[key] = value

	def _get_or_create_state(self, cur, state_abbr: str) -> int:
		abbreviation = (state_abbr or "").strip().upper()
		if len(abbreviation) != 2:
			abbreviation = UNKNOWN_STATE_ABBR

		cached_id = self._state_cache.get(abbreviation)
		if cached_id is not None:
			return cached_id

		state_name = STATE_NAME_BY_ABBR.get(abbreviation, UNKNOWN_STATE_NAME)
		cur.execute(
			"""
			INSERT INTO state (name, abbreviation)
			VALUES (%s, %s)
			ON CONFLICT (abbreviation) DO UPDATE
				SET name = EXCLUDED.name
			RETURNING id
			""",
			(state_name, abbreviation),
		)
		state_id = cur.fetchone()[0]
		self._bounded_set(self._state_cache, abbreviation, state_id)
		return state_id

	def _get_or_create_city(self, cur, city_name: str, state_id: int) -> int:
		normalized_name = (city_name or "").strip()
		if not normalized_name:
			normalized_name = UNKNOWN_CITY_NAME

		cache_key = (normalized_name, state_id)
		cached_id = self._city_cache.get(cache_key)
		if cached_id is not None:
			return cached_id

		cur.execute(
			"""
			INSERT INTO city (name, state_id)
			VALUES (%s, %s)
			ON CONFLICT (name, state_id) DO UPDATE
				SET name = EXCLUDED.name
			RETURNING id
			""",
			(normalized_name, state_id),
		)
		city_id = cur.fetchone()[0]
		self._bounded_set(self._city_cache, cache_key, city_id)
		return city_id

	def _get_or_create_date(self, cur, event: dict[str, Any]) -> int:
		day = event.get("day")
		month = event.get("month")
		year = event.get("year")

		if day is None or month is None or year is None:
			raise ValueError("Incomplete race date")

		event_date = dt_date(int(year), int(month), int(day))
		cached_id = self._date_cache.get(event_date)
		if cached_id is not None:
			return cached_id

		day_of_week = event_date.isoweekday()
		cur.execute(
			"""
			INSERT INTO date (date, day, month, year, day_of_week, is_holiday)
			VALUES (%s, %s, %s, %s, %s, FALSE)
			ON CONFLICT (date) DO UPDATE
				SET day_of_week = EXCLUDED.day_of_week
			RETURNING id
			""",
			(
				event_date,
				event_date.day,
				event_date.month,
				event_date.year,
				day_of_week,
			),
		)
		date_id = cur.fetchone()[0]
		self._bounded_set(self._date_cache, event_date, date_id)
		return date_id

	def _bulk_upsert_events(self, cur, rows: list[tuple[str, str, str, int, int]]) -> dict[str, int]:
		if not rows:
			return {}

		execute_values(
			cur,
			"""
			INSERT INTO event (slug, hash_slug, name, city_id, date_id)
			VALUES %s
			ON CONFLICT (hash_slug) DO UPDATE
				SET slug = EXCLUDED.slug,
					name = EXCLUDED.name,
					city_id = EXCLUDED.city_id,
					date_id = EXCLUDED.date_id
			RETURNING id, hash_slug
			""",
			rows,
			page_size=1000,
		)

		return {hash_slug: event_id for event_id, hash_slug in cur.fetchall()}

	def _bulk_insert_jobs(self, cur, rows: list[tuple[int]]) -> dict[int, int]:
		if not rows:
			return {}

		execute_values(
			cur,
			"""
			INSERT INTO extraction_job (event_id)
			VALUES %s
			ON CONFLICT (event_id) DO NOTHING
			RETURNING id, event_id
			""",
			rows,
			page_size=1000,
		)

		return {event_id: job_id for job_id, event_id in cur.fetchall()}

	def store_events(self, events: list[dict[str, Any]]) -> dict[str, int]:
		summary = {"inserted": 0, "skipped": 0}

		event_rows: list[tuple[str, str, str, int, int]] = []

		with self.db.cursor() as cur:
			for event in events:
				slug = (event.get("slug") or "").strip()
				if not slug:
					summary["skipped"] += 1
					logger.warning("Event ignored: slug missing")
					continue

				hash_slug = self.build_slug_hash(slug)
				state_id = self._get_or_create_state(cur, event.get("state"))
				city_id = self._get_or_create_city(cur, event.get("city"), state_id)
				date_id = self._get_or_create_date(cur, event)

				event_rows.append(
					(
						slug,
						hash_slug,
						(event.get("name") or "").strip(),
						city_id,
						date_id,
					)
				)

			event_map = self._bulk_upsert_events(cur, event_rows)
			summary["inserted"] += len(event_map)
			summary["skipped"] += max(0, len(event_rows) - len(event_map))

			job_rows = [(event_id,) for event_id in event_map.values()]
			job_map = self._bulk_insert_jobs(cur, job_rows)

		logger.info(
			"Bulk persistence completed: inserted_events=%s skipped_events=%s jobs=%s",
			summary["inserted"],
			summary["skipped"],
			len(job_map),
		)
		return summary
