import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import logging
import re
import unicodedata
from typing import Any

import boto3
from psycopg2.extras import execute_values

from src.database.connections.postgres import PostgresConnection

logger = logging.getLogger("EventResultStorage")


class EventResultStorage:
    def __init__(self, db: PostgresConnection | None = None, config: dict[str, Any] | None = None):
        self.db = db or PostgresConnection()
        self.config = config or {}

        result_cfg = self.config.get("result_pipeline", {})
        s3_cfg = self.config.get("s3", {})

        self.batch_size = int(result_cfg.get("batch_size", 5))
        if self.batch_size <= 0:
            self.batch_size = 5
        self.task_workers = int(result_cfg.get("task_workers", self.batch_size))
        if self.task_workers <= 0:
            self.task_workers = 1
        self.max_attempts_total = int(result_cfg.get("max_attempts_total", 15))

        self.s3_bucket = s3_cfg.get("bucket")
        self.s3_prefix = (s3_cfg.get("results_prefix") or "results").strip("/")
        self.s3_region = s3_cfg.get("region")
        s3_profile = s3_cfg.get("profile_name") or None
        if self.s3_bucket:
            session = boto3.Session(profile_name=s3_profile, region_name=self.s3_region)
            self._s3_client = session.client("s3")
        else:
            self._s3_client = None

    @staticmethod
    def _slugify(raw: str) -> str:
        clean = unicodedata.normalize("NFKD", raw or "").encode("ascii", "ignore").decode("ascii")
        clean = re.sub(r"[^a-zA-Z0-9]+", "-", clean).strip("-").lower()
        return clean or "unknown"

    @staticmethod
    def _format_distance(distance_km: Any) -> str:
        distance = float(distance_km)
        return f"{int(distance)}k" if distance.is_integer() else f"{distance:.1f}k"

    def fetch_actionable_jobs(self) -> list[dict[str, Any]]:
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT
                    j.id AS job_id,
                    j.event_id,
                    e.slug,
                    c.name AS city_name,
                    s.abbreviation AS state_abbr
                FROM extraction_job j
                JOIN event e ON e.id = j.event_id
                JOIN city c ON c.id = e.city_id
                JOIN state s ON s.id = c.state_id
                WHERE j.status IN ('pending', 'failed')
                ORDER BY j.updated_at ASC, j.id
                """,
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def fetch_actionable_tasks(self, job_ids: list[int]) -> list[dict[str, Any]]:
        if not job_ids:
            return []

        with self.db.cursor() as cur:
            cur.execute(
                """
                WITH candidate_tasks AS (
                    SELECT t.id
                    FROM extraction_task t
                    WHERE t.job_id = ANY(%s)
                      AND t.status IN ('pending', 'failed')
                      AND t.attempts < %s
                    ORDER BY t.attempts ASC, t.last_attempt_at NULLS FIRST, t.id
                    FOR UPDATE SKIP LOCKED
                ),
                claimed_tasks AS (
                    UPDATE extraction_task t
                    SET status = 'in_progress',
                        attempts = t.attempts + 1,
                        last_attempt_at = NOW(),
                        error_msg = NULL
                    FROM candidate_tasks c
                    WHERE t.id = c.id
                    RETURNING
                        t.id AS task_id,
                        t.job_id,
                        t.modality_id,
                        t.gender,
                        t.source_url,
                        t.attempts
                )
                SELECT
                    t.task_id,
                    t.job_id,
                    t.modality_id,
                    t.gender,
                    t.source_url,
                    t.attempts,
                    j.event_id,
                    e.slug,
                    m.distance_km,
                    m.is_pcd,
                    m.raw_category_name,
                    c.name AS city_name,
                    s.abbreviation AS state_abbr
                FROM claimed_tasks t
                JOIN extraction_job j ON j.id = t.job_id
                JOIN modality m ON m.id = t.modality_id
                JOIN event e ON e.id = j.event_id
                JOIN city c ON c.id = e.city_id
                JOIN state s ON s.id = c.state_id
                ORDER BY t.attempts ASC, t.task_id
                """,
                (job_ids, self.max_attempts_total),
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def _bulk_upsert_modalities(self, event_id: int, targets: list[dict[str, Any]]) -> dict[str, int]:
        if not targets:
            return {}

        modality_by_raw_name: dict[str, tuple[int, float, bool, str]] = {}
        for target in targets:
            raw_category_name = str(target["raw_category_name"])
            modality_by_raw_name[raw_category_name] = (
                event_id,
                float(target["distance_km"]),
                bool(target["is_pcd"]),
                raw_category_name,
            )

        rows = list(modality_by_raw_name.values())

        with self.db.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO modality (event_id, distance_km, is_pcd, raw_category_name)
                VALUES %s
                ON CONFLICT (event_id, raw_category_name) DO UPDATE
                    SET distance_km = EXCLUDED.distance_km,
                        is_pcd = EXCLUDED.is_pcd
                RETURNING id, raw_category_name
                """,
                rows,
                page_size=500,
            )
            return {raw_category_name: modality_id for modality_id, raw_category_name in cur.fetchall()}

    def _bulk_upsert_tasks(self, job_id: int, modality_map: dict[str, int], targets: list[dict[str, Any]]) -> int:

        task_map: dict[tuple[int, str], str] = {}
        for target in targets:
            modality_id = modality_map.get(str(target.get("raw_category_name")))
            if not modality_id:
                continue
            gender = str(target.get("gender"))
            source_url = str(target.get("source_url"))
            task_map[(modality_id, gender)] = source_url

        rows: list[tuple[int, int, str, str]] = []
        for (modality_id, gender), source_url in task_map.items():
            rows.append((job_id, modality_id, gender, source_url))

        if not rows:
            return 0

        with self.db.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO extraction_task (job_id, modality_id, gender, source_url)
                VALUES %s
                ON CONFLICT (job_id, modality_id, gender) DO UPDATE
                    SET source_url = EXCLUDED.source_url
                """,
                rows,
                page_size=500,
            )
        return len(rows)

    def discover_and_create_tasks(self, extractor, job: dict[str, Any]) -> int:
        targets = extractor.discover_modalities(job["slug"])
        if not targets:
            raise RuntimeError(f"No modality targets discovered for slug={job['slug']}")

        modality_map = self._bulk_upsert_modalities(int(job["event_id"]), targets)
        return self._bulk_upsert_tasks(int(job["job_id"]), modality_map, targets)

    def _build_s3_key(self, task: dict[str, Any]) -> str:
        state = self._slugify(task.get("state_abbr") or "ni")
        city = self._slugify(task.get("city_name") or "nao-informado")
        distance = self._format_distance(task["distance_km"])
        is_pcd = "true" if bool(task.get("is_pcd")) else "false"
        slug = self._slugify(task.get("slug") or "unknown-event")
        gender = (task.get("gender") or "M").upper()
        filename = f"job_{task['job_id']}_task_{task['task_id']}.csv"

        return (
            f"{self.s3_prefix}/"
            f"state={state}/city={city}/modality={distance}/pcd={is_pcd}/gender={gender}/event={slug}/"
            f"{filename}"
        )

    def upload_to_s3(
        self,
        task: dict[str, Any],
        rows: list[dict[str, Any]],
    ) -> str | None:
        if not self._s3_client or not self.s3_bucket or not rows:
            return None

        enriched_rows: list[dict[str, str]] = []
        for row in rows:
            enriched = {k: "" if v is None else str(v) for k, v in row.items()}
            enriched["job_id"] = str(task["job_id"])
            enriched["task_id"] = str(task["task_id"])
            enriched["event_id"] = str(task["event_id"])
            enriched["modality_id"] = str(task["modality_id"])
            enriched["gender"] = str(task["gender"])
            enriched["distance_km"] = self._format_distance(task["distance_km"])
            enriched["is_pcd"] = str(bool(task["is_pcd"])).lower()
            enriched["raw_category_name"] = str(task["raw_category_name"])
            enriched_rows.append(enriched)

        output = io.StringIO()
        fieldnames = list(enriched_rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

        key = self._build_s3_key(task=task)
        self._s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=key,
            Body=output.getvalue().encode("utf-8"),
            ContentType="text/csv",
        )
        return f"s3://{self.s3_bucket}/{key}"

    def mark_task_success(self, task_id: int, row_count: int, s3_path: str | None) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE extraction_task
                SET
                    status = 'completed',
                    s3_path = %s,
                    row_count = %s,
                    last_attempt_at = NOW(),
                    error_msg = NULL
                WHERE id = %s
                """,
                (s3_path, row_count, task_id),
            )

    def mark_task_failure(self, task_id: int, error_msg: str) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE extraction_task
                SET status = 'failed',
                    error_msg = %s
                WHERE id = %s
                """,
                (error_msg[:2000], task_id),
            )

    def mark_job_failed(self, job_id: int) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE extraction_job
                SET status = 'failed',
                    updated_at = NOW()
                WHERE id = %s
                """,
                (job_id,),
            )

    def refresh_job_status(self, job_id: int) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE extraction_job j
                SET
                    status = CASE
                        WHEN NOT EXISTS (
                            SELECT 1
                            FROM extraction_task t
                            WHERE t.job_id = j.id
                        ) THEN 'pending'
                        WHEN EXISTS (
                            SELECT 1
                            FROM extraction_task t
                            WHERE t.job_id = j.id
                              AND t.status = 'pending'
                        ) THEN 'pending'
                                                WHEN EXISTS (
                                                        SELECT 1
                                                        FROM extraction_task t
                                                        WHERE t.job_id = j.id
                                                            AND t.status = 'in_progress'
                                                ) THEN 'pending'
                        WHEN NOT EXISTS (
                            SELECT 1
                            FROM extraction_task t
                            WHERE t.job_id = j.id
                              AND t.status <> 'completed'
                        ) THEN 'completed'
                        WHEN EXISTS (
                            SELECT 1
                            FROM extraction_task t
                            WHERE t.job_id = j.id
                              AND t.status = 'failed'
                        ) THEN 'failed'
                        ELSE 'pending'
                    END,
                    updated_at = NOW()
                WHERE j.id = %s
                """,
                (job_id,),
            )

    @staticmethod
    def _chunk(tasks: list, size: int):
        for i in range(0, len(tasks), size):
            yield tasks[i : i + size]

    def _build_task_extractor(self, extractor):
        return extractor.__class__(self.config)

    def _process_task(self, extractor, task: dict[str, Any]) -> dict[str, int | str]:
        task_id = int(task["task_id"])
        job_id = int(task["job_id"])
        task_extractor = None

        try:
            task_extractor = self._build_task_extractor(extractor)
            rows = task_extractor.extract_results(task["source_url"])

            s3_path = self.upload_to_s3(task=task, rows=rows)
            if not s3_path:
                raise RuntimeError("S3 upload skipped or no rows parsed; configure bucket and verify source HTML")

            self.mark_task_success(task_id, row_count=len(rows), s3_path=s3_path)
            self.refresh_job_status(job_id)

            logger.info("Task completed: task_id=%s rows=%s s3_path=%s", task_id, len(rows), s3_path)
            return {"status": "completed", "row_count": len(rows)}

        except Exception as exc:
            error_msg = str(exc)
            try:
                self.mark_task_failure(task_id, error_msg)
                self.refresh_job_status(job_id)
            except Exception as persist_exc:
                logger.error("Failed to persist task failure: task_id=%s error=%s", task_id, persist_exc)

            logger.error("Task failed: task_id=%s error=%s", task_id, error_msg)
            return {"status": "failed", "row_count": 0}

        finally:
            if task_extractor and hasattr(task_extractor, "close"):
                task_extractor.close()

    def process_queue(self, extractor) -> dict[str, int]:
        jobs = self.fetch_actionable_jobs()
        summary = {
            "jobs": len(jobs),
            "tasks_discovered": 0,
            "tasks_fetched": 0,
            "completed": 0,
            "failed": 0,
            "uploaded_rows": 0,
        }

        logger.info(
            "Jobs to process: %s | batch_size=%s | task_workers=%s",
            len(jobs),
            self.batch_size,
            self.task_workers,
        )

        for batch_num, batch in enumerate(self._chunk(jobs, self.batch_size), start=1):
            logger.info("Processing batch %s (%s jobs)", batch_num, len(batch))

            batch_job_ids = [int(job["job_id"]) for job in batch]

            for job in batch:
                job_id = int(job["job_id"])
                try:
                    created_tasks = self.discover_and_create_tasks(extractor, job)
                    summary["tasks_discovered"] += created_tasks
                    self.refresh_job_status(job_id)
                except Exception as exc:
                    self.mark_job_failed(job_id)
                    logger.error("Modality discovery failed: job_id=%s error=%s", job_id, exc)

            tasks = self.fetch_actionable_tasks(batch_job_ids)
            summary["tasks_fetched"] += len(tasks)

            if not tasks:
                continue

            max_workers = min(self.task_workers, len(tasks))
            logger.info("Submitting %s tasks with max_workers=%s", len(tasks), max_workers)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self._process_task, extractor, task) for task in tasks]

                for future in as_completed(futures):
                    result = future.result()
                    if result["status"] == "completed":
                        summary["completed"] += 1
                        summary["uploaded_rows"] += int(result["row_count"])
                    else:
                        summary["failed"] += 1

        return summary
