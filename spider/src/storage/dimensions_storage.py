import logging
import os
import re
import sys
from decimal import Decimal
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from psycopg2 import sql

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connections.postgres import PostgresConnection

load_dotenv(override=True)

logger = logging.getLogger("DimensionsStorage")

FREQUENCY_POLICY_BY_DIMENSION = {
    "state": "once",
    "city": "weekly",
    "date": "weekly",
    "event": "always",
    "modality": "always",
    "extraction_job": "always",
    "extraction_task": "always",
}

PARQUET_TYPE_OVERRIDES_BY_DIMENSION: dict[str, dict[str, pa.DataType]] = {
    # Keep modality parquet aligned with Glue table types in infra/glue.tf.
    "modality": {
        "id": pa.int32(),
        "event_id": pa.int32(),
        "distance_km": pa.float64(),
        "is_pcd": pa.bool_(),
        "raw_category_name": pa.string(),
    }
}

QUERY_BY_DIMENSION = {
    "extraction_job": "SELECT * FROM extraction_job",
    "extraction_task": "SELECT * FROM extraction_task WHERE status = 'completed'",
}


def _load_config() -> dict[str, Any]:
    config_path = PROJECT_ROOT / "config" / "config.yml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _validate_identifier(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Invalid table identifier: {identifier}")
    return identifier


class DimensionsStorage:
    def __init__(self, db: PostgresConnection | None = None, config: dict[str, Any] | None = None):
        self.db = db or PostgresConnection()
        self.config = config or _load_config()

        s3_cfg = self.config.get("s3", {})
        dims_cfg = self.config.get("dimensions_pipeline", {})

        self.s3_bucket = str(s3_cfg.get("bucket") or "").strip()
        self.s3_region = str(s3_cfg.get("region") or os.getenv("AWS_REGION") or "us-east-1").strip()
        self.s3_profile = str(s3_cfg.get("profile_name") or "").strip() or None
        self.dimensions_prefix = str(dims_cfg.get("prefix") or "dims").strip("/")
        self.weekly_interval = timedelta(days=int(dims_cfg.get("weekly_interval_days", 7)))

        if not self.s3_bucket:
            raise ValueError("Missing s3.bucket configuration for dimensions export")

        session = boto3.Session(profile_name=self.s3_profile, region_name=self.s3_region)
        self.s3_client = session.client("s3")

    def _destination_key(self, dimension: str) -> str:
        return f"{self.dimensions_prefix}/{dimension}/data.parquet"

    def _object_last_modified(self, key: str) -> datetime | None:
        try:
            response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=key)
            return response.get("LastModified")
        except ClientError as exc:
            error_code = (exc.response or {}).get("Error", {}).get("Code", "")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    def _should_export(self, dimension: str, force: bool = False) -> tuple[bool, str]:
        if force:
            return True, "forced"

        policy = FREQUENCY_POLICY_BY_DIMENSION[dimension]
        if policy == "always":
            return True, "always"

        key = self._destination_key(dimension)
        last_modified = self._object_last_modified(key)
        if last_modified is None:
            return True, "missing-object"

        if policy == "once":
            return False, "already-exported"

        now_utc = datetime.now(UTC)
        if now_utc - last_modified.astimezone(UTC) >= self.weekly_interval:
            return True, "weekly-window-reached"

        return False, "weekly-window-not-reached"

    def _fetch_dimension_rows(self, dimension: str) -> tuple[list[str], list[tuple[Any, ...]]]:
        query = QUERY_BY_DIMENSION.get(dimension)
        with self.db.cursor() as cur:
            if query:
                cur.execute(query)
            else:
                table_name = _validate_identifier(dimension)
                cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name)))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return columns, rows

    @staticmethod
    def _coerce_values_for_arrow(values: list[Any], target_type: pa.DataType) -> list[Any]:
        if pa.types.is_floating(target_type):
            return [float(value) if isinstance(value, Decimal) else value for value in values]
        return values

    @staticmethod
    def _build_parquet_bytes(
        dimension: str,
        columns: list[str],
        rows: list[tuple[Any, ...]],
    ) -> bytes:
        arrays: dict[str, list[Any]] = {column: [] for column in columns}
        for row in rows:
            for index, column in enumerate(columns):
                arrays[column].append(row[index])

        type_overrides = PARQUET_TYPE_OVERRIDES_BY_DIMENSION.get(dimension, {})
        pa_arrays = []
        for column in columns:
            if column in type_overrides:
                target_type = type_overrides[column]
                values = DimensionsStorage._coerce_values_for_arrow(arrays[column], target_type)
                pa_arrays.append(pa.array(values, type=target_type))
            else:
                pa_arrays.append(pa.array(arrays[column]))

        table = pa.Table.from_arrays(pa_arrays, names=columns)
        output = BytesIO()
        pq.write_table(table, output, compression="snappy")
        return output.getvalue()

    def export_dimension(
        self,
        dimension: str,
        force: bool = False,
        respect_frequency: bool = True,
    ) -> dict[str, Any]:
        if dimension not in FREQUENCY_POLICY_BY_DIMENSION:
            raise ValueError(
                f"Unknown dimension '{dimension}'. Allowed: {', '.join(FREQUENCY_POLICY_BY_DIMENSION)}"
            )

        if respect_frequency:
            should_export, reason = self._should_export(dimension, force=force)
        else:
            should_export, reason = True, "airflow-scheduled"

        if not should_export:
            logger.info("Skipping dimension export: dimension=%s reason=%s", dimension, reason)
            return {"dimension": dimension, "status": "skipped", "reason": reason, "rows": 0}

        columns, rows = self._fetch_dimension_rows(dimension)
        payload = self._build_parquet_bytes(dimension, columns, rows)
        key = self._destination_key(dimension)
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=key,
            Body=payload,
            ContentType="application/octet-stream",
        )

        logger.info(
            "Dimension exported: dimension=%s rows=%s key=s3://%s/%s",
            dimension,
            len(rows),
            self.s3_bucket,
            key,
        )
        return {"dimension": dimension, "status": "exported", "reason": reason, "rows": len(rows)}

    def export_dimensions(
        self,
        dimensions: list[str] | None = None,
        force_dimensions: set[str] | None = None,
        respect_frequency: bool = True,
    ) -> list[dict[str, Any]]:
        selected = dimensions or list(FREQUENCY_POLICY_BY_DIMENSION.keys())
        force_dimensions = force_dimensions or set()

        summary: list[dict[str, Any]] = []
        for dimension in selected:
            summary.append(
                self.export_dimension(
                    dimension=dimension,
                    force=dimension in force_dimensions,
                    respect_frequency=respect_frequency,
                )
            )
        return summary

    def close(self) -> None:
        self.db.close()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    storage = DimensionsStorage()
    try:
        summary = storage.export_dimensions()
        logger.info("Dimensions export finished: %s", summary)
    finally:
        storage.close()


if __name__ == "__main__":
    main()