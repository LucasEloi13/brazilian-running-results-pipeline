import hashlib
import logging
from datetime import date as dt_date
from typing import Any

from src.database.connections.postgres import PostgresConnection

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
	def __init__(self, db: PostgresConnection | None = None):
		self.db = db or PostgresConnection()

	@staticmethod
	def build_slug_hash(slug: str) -> str:
		normalized_slug = (slug or "").strip().lower()
		return hashlib.md5(normalized_slug.encode("utf-8")).hexdigest()

	def _event_hash_exists(self, cur, hash_slug: str) -> bool:
		cur.execute(
			"SELECT 1 FROM event WHERE hash_slug = %s LIMIT 1",
			(hash_slug,),
		)
		return cur.fetchone() is not None

	def _get_or_create_state(self, cur, state_abbr: str) -> int:
		abbreviation = (state_abbr or "").strip().upper()
		if len(abbreviation) != 2:
			logger.warning(
				"State abbreviation inválida (%s). Usando fallback=%s",
				state_abbr,
				UNKNOWN_STATE_ABBR,
			)
			abbreviation = UNKNOWN_STATE_ABBR

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
		return cur.fetchone()[0]

	def _get_or_create_city(self, cur, city_name: str, state_id: int) -> int:
		normalized_name = (city_name or "").strip()
		if not normalized_name:
			logger.warning("City name vazio. Usando fallback=%s", UNKNOWN_CITY_NAME)
			normalized_name = UNKNOWN_CITY_NAME

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
		return cur.fetchone()[0]

	def _get_or_create_date(self, cur, event: dict[str, Any]) -> int:
		day = event.get("day")
		month = event.get("month")
		year = event.get("year")

		if day is None or month is None or year is None:
			raise ValueError("Data da corrida incompleta")

		event_date = dt_date(int(year), int(month), int(day))
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
		return cur.fetchone()[0]

	def _insert_event(self, cur, event: dict[str, Any], city_id: int, date_id: int, hash_slug: str) -> int:
		cur.execute(
			"""
			INSERT INTO event (slug, hash_slug, name, city_id, date_id)
			VALUES (%s, %s, %s, %s, %s)
			RETURNING id
			""",
			(
				event["slug"].strip(),
				hash_slug,
				(event.get("name") or "").strip(),
				city_id,
				date_id,
			),
		)
		return cur.fetchone()[0]

	def _insert_modalities(self, cur, event_id: int, distances: list[dict[str, Any]] | None) -> int:
		if not distances:
			return 0

		inserted_count = 0
		for distance_item in distances:
			km_raw = distance_item.get("km")
			if km_raw is None:
				continue

			try:
				distance_km = int(km_raw)
			except (TypeError, ValueError):
				continue

			finishers_raw = distance_item.get("finishers")
			finishers = int(finishers_raw) if finishers_raw is not None else None

			cur.execute(
				"""
				INSERT INTO modality (event_id, distance, finishers)
				VALUES (%s, %s, %s)
				ON CONFLICT (event_id, distance) DO UPDATE
					SET finishers = EXCLUDED.finishers
				""",
				(event_id, distance_km, finishers),
			)
			inserted_count += 1

		return inserted_count

	def store_event(self, event: dict[str, Any]) -> bool:
		slug = (event.get("slug") or "").strip()
		if not slug:
			logger.warning("Evento ignorado: slug ausente")
			return False

		hash_slug = self.build_slug_hash(slug)

		with self.db.cursor() as cur:
			if self._event_hash_exists(cur, hash_slug):
				logger.info("Evento já existe (hash_slug=%s). Inserção ignorada.", hash_slug)
				return False

			state_id = self._get_or_create_state(cur, event.get("state"))
			city_id = self._get_or_create_city(cur, event.get("city"), state_id)
			date_id = self._get_or_create_date(cur, event)
			event_id = self._insert_event(cur, event, city_id, date_id, hash_slug)
			modality_count = self._insert_modalities(cur, event_id, event.get("distances"))

		logger.info(
			"Evento inserido com sucesso: slug=%s hash_slug=%s event_id=%s modalidades=%s",
			slug,
			hash_slug,
			event_id,
			modality_count,
		)
		return True

	def store_events(self, events: list[dict[str, Any]]) -> dict[str, int]:
		summary = {"inserted": 0, "skipped": 0}

		for event in events:
			try:
				was_inserted = self.store_event(event)
				if was_inserted:
					summary["inserted"] += 1
				else:
					summary["skipped"] += 1
			except Exception as exc:
				summary["skipped"] += 1
				logger.exception(
					"Falha ao persistir evento slug=%s: %s",
					event.get("slug"),
					exc,
				)

		logger.info(
			"Persistência finalizada: %s inseridos, %s ignorados",
			summary["inserted"],
			summary["skipped"],
		)
		return summary
