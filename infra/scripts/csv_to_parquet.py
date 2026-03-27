#!/usr/bin/env python3
"""
Incremental CSV → Parquet loader for dim_results using Athena.

Strategy
--------
* Registers only new partitions on results_csv with ALTER TABLE ADD PARTITION.
* Finds job_ids present in results_csv but absent from dim_results.
* Runs a single INSERT INTO dim_results ... WHERE job_id IN (...).
* Falls back to full refresh (--full-refresh flag or on first run).

Requirements
------------
    pip install boto3 pyyaml

Usage
-----
    python csv_to_parquet.py              # incremental (default)
    python csv_to_parquet.py --full-refresh
    python csv_to_parquet.py --use-msck   # fallback path
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

import boto3
import yaml

# ---------------------------------------------------------------------------
# Config / constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "spider" / "config" / "config.yml"

DATABASE = "running_results"
SOURCE_TABLE = "results_csv"
TARGET_TABLE = "dim_results"

# Column order must match the storage_descriptor order in glue.tf (results_csv + dim_results) exactly.
# First: partition columns from S3 path (these are extracted from path, not CSV)
# Then: all CSV columns in exact header order
_TARGET_COLUMNS = (
    # Partition columns (from S3 path structure)
    "state",
    "city",
    "modality",
    "pcd",
    "gender_partition",
    "event",
    # CSV columns (MUST match results_csv header order exactly)
    "geral",
    "cat",
    "numero",
    "nome",
    "equipe",
    "pace",
    "tempo",
    "gap",
    "raw_row_id",
    "overall",
    "category",
    "bib",
    "athlete_name",
    "team",
    "finish_time",
    "job_id",
    "task_id",
    "event_id",
    "modality_id",
    "gender",  # CSV column
    "distance_km",
    "is_pcd",
    "raw_category_name",
)
TARGET_COLUMN_LIST = ", ".join(_TARGET_COLUMNS)


def _to_int(column_name: str) -> str:
    return f"TRY_CAST(NULLIF(TRIM(CAST({column_name} AS VARCHAR)), '') AS INTEGER)"


def _to_bool(column_name: str) -> str:
    normalized = f"LOWER(TRIM(CAST({column_name} AS VARCHAR)))"
    return f"""
CASE
    WHEN {normalized} IN ('true', 't', '1', 'yes', 'y', 'sim') THEN TRUE
    WHEN {normalized} IN ('false', 'f', '0', 'no', 'n', 'nao', 'não') THEN FALSE
    ELSE NULL
END
""".strip()


def _to_text(column_name: str) -> str:
    return f"NULLIF(TRIM(CAST({column_name} AS VARCHAR)), '')"


SELECT_COLUMN_LIST = ",\n    ".join(
    [
        "state",
        "city",
        "modality",
        "pcd",
        "gender_partition",
        "event",
        f"{_to_int('geral')} AS geral",
        "cat",
        "numero",
        "nome",
        "equipe",
        f"{_to_text('pace')} AS pace",
        f"{_to_text('tempo')} AS tempo",
        f"{_to_text('gap')} AS gap",
        f"{_to_int('raw_row_id')} AS raw_row_id",
        f"{_to_int('overall')} AS overall",
        "category",
        "bib",
        "athlete_name",
        "team",
        f"{_to_text('finish_time')} AS finish_time",
        f"{_to_int('job_id')} AS job_id",
        f"{_to_int('task_id')} AS task_id",
        f"{_to_int('event_id')} AS event_id",
        f"{_to_int('modality_id')} AS modality_id",
        "gender",
        "distance_km",
        f"{_to_bool('is_pcd')} AS is_pcd",
        "raw_category_name",
    ]
)

logger = logging.getLogger("csv_to_parquet")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def _build_athena_client(config: dict[str, Any]):
    s3_cfg = config.get("s3", {})
    profile = s3_cfg.get("profile_name") or None
    region = s3_cfg.get("region") or "us-east-1"
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("athena")


def _build_s3_client(config: dict[str, Any]):
    s3_cfg = config.get("s3", {})
    profile = s3_cfg.get("profile_name") or None
    region = s3_cfg.get("region") or "us-east-1"
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("s3")


def _athena_output(config: dict[str, Any]) -> str:
    bucket = config["s3"]["bucket"]
    return f"s3://{bucket}/athena-results/"


def _wait_for_query(client, execution_id: str, poll_s: float = 2.0) -> tuple[str, dict]:
    while True:
        resp = client.get_query_execution(QueryExecutionId=execution_id)
        state = resp["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return state, resp
        time.sleep(poll_s)


def _run_query(client, query: str, output_location: str) -> str:
    """Submit an Athena query, wait for completion, return execution_id."""
    logger.debug("Athena query:\n%s", query)
    resp = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": output_location},
    )
    execution_id = resp["QueryExecutionId"]
    state, execution = _wait_for_query(client, execution_id)
    if state != "SUCCEEDED":
        reason = execution["QueryExecution"]["Status"].get("StateChangeReason", "")
        raise RuntimeError(f"Athena query {state}: {reason}\n---\n{query}")
    return execution_id


def _fetch_single_column(client, execution_id: str) -> list[str]:
    """Return all values of the first column, skipping the header row."""
    paginator = client.get_paginator("get_query_results")
    values: list[str] = []
    first_page = True
    for page in paginator.paginate(QueryExecutionId=execution_id):
        for row in page["ResultSet"]["Rows"]:
            if first_page:
                first_page = False
                continue  # skip header
            cell = row["Data"][0]
            values.append(cell.get("VarCharValue", ""))
    return values


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def repair_source_table() -> None:
    """Register only new partitions for results_csv using incremental ALTER TABLE."""
    from register_new_partitions import register_new_partitions

    logger.info("Registering only new partitions on %s ...", SOURCE_TABLE)
    added = register_new_partitions(dry_run=False, batch_size=100)
    logger.info("Incremental partition sync complete on %s (new=%d).", SOURCE_TABLE, added)


def repair_source_table_with_msck(client, output_location: str) -> None:
    """Fallback path: full metadata repair (slower on many partitions)."""
    logger.info("Running MSCK REPAIR TABLE %s ...", SOURCE_TABLE)
    _run_query(client, f"MSCK REPAIR TABLE {SOURCE_TABLE}", output_location)
    logger.info("Partitions refreshed on %s.", SOURCE_TABLE)


def get_loaded_job_ids(client, output_location: str) -> set[str] | None:
    """
    Return job_ids already in dim_results.
    Returns None when the table has no data (first run / empty prefix).
    """
    try:
        eid = _run_query(
            client,
            f"SELECT DISTINCT job_id FROM {TARGET_TABLE}",
            output_location,
        )
        return set(_fetch_single_column(client, eid))
    except RuntimeError as exc:
        logger.warning("Could not read %s (probably first run): %s", TARGET_TABLE, exc)
        return None


def get_csv_job_ids(client, output_location: str) -> set[str]:
    """Return all job_ids available in results_csv."""
    eid = _run_query(
        client,
        f"SELECT DISTINCT job_id FROM {SOURCE_TABLE}",
        output_location,
    )
    return set(_fetch_single_column(client, eid))


def insert_job_ids(client, output_location: str, job_ids: set[str]) -> None:
    """INSERT INTO dim_results only the rows belonging to the given job_ids."""
    ids_literal = ", ".join(f"'{jid}'" for jid in sorted(job_ids))
    query = f"""
INSERT INTO {TARGET_TABLE} ({TARGET_COLUMN_LIST})
SELECT
    {SELECT_COLUMN_LIST}
FROM   {SOURCE_TABLE}
WHERE  job_id IN ({ids_literal})
""".strip()
    _run_query(client, query, output_location)
    logger.info("Inserted %d new job_id(s) into %s: %s", len(job_ids), TARGET_TABLE, sorted(job_ids))


def _clear_parquet_prefix(s3_client, bucket: str, prefix: str) -> int:
    """Delete all objects under prefix. Returns number of objects deleted."""
    paginator = s3_client.get_paginator("list_objects_v2")
    to_delete: list[dict] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            to_delete.append({"Key": obj["Key"]})

    deleted = 0
    for i in range(0, len(to_delete), 1000):
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": to_delete[i : i + 1000]},
        )
        deleted += len(to_delete[i : i + 1000])

    return deleted


def full_refresh(athena_client, s3_client, config: dict[str, Any], output_location: str) -> None:
    """
    1. Clear existing Parquet objects from dims/results/.
    2. INSERT INTO dim_results SELECT everything from results_csv.
    """
    bucket = config["s3"]["bucket"]
    dims_prefix = config.get("dimensions_pipeline", {}).get("prefix", "dims")
    target_s3_prefix = f"{dims_prefix}/results/"

    logger.info("Full refresh: clearing s3://%s/%s", bucket, target_s3_prefix)
    deleted = _clear_parquet_prefix(s3_client, bucket, target_s3_prefix)
    logger.info("Deleted %d object(s) from S3.", deleted)

    query = f"""
INSERT INTO {TARGET_TABLE} ({TARGET_COLUMN_LIST})
SELECT
    {SELECT_COLUMN_LIST}
FROM   {SOURCE_TABLE}
""".strip()
    _run_query(athena_client, query, output_location)

    # Report final row count.
    eid = _run_query(
        athena_client,
        f"SELECT COUNT(*) FROM {TARGET_TABLE}",
        output_location,
    )
    rows = _fetch_single_column(athena_client, eid)
    logger.info("Full refresh complete: %s rows in %s.", rows[0] if rows else "?", TARGET_TABLE)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(force_full_refresh: bool = False, use_msck: bool = False) -> None:
    config = _load_config()
    athena = _build_athena_client(config)
    s3 = _build_s3_client(config)
    output = _athena_output(config)

    # Always refresh partition metadata first so new CSV partitions are visible to Athena.
    if use_msck:
        repair_source_table_with_msck(athena, output)
    else:
        repair_source_table()

    if force_full_refresh:
        logger.info("Full refresh requested via --full-refresh.")
        full_refresh(athena, s3, config, output)
        return

    # --- Incremental path ---
    loaded_ids = get_loaded_job_ids(athena, output)

    if loaded_ids is None:
        logger.info("%s appears empty — running initial full load.", TARGET_TABLE)
        full_refresh(athena, s3, config, output)
        return

    csv_ids = get_csv_job_ids(athena, output)
    new_ids = csv_ids - loaded_ids

    if not new_ids:
        logger.info("%s is already up-to-date (%d job_id(s) loaded).", TARGET_TABLE, len(loaded_ids))
        return

    logger.info(
        "Incremental load: %d new job_id(s) out of %d total in %s.",
        len(new_ids),
        len(csv_ids),
        SOURCE_TABLE,
    )
    insert_job_ids(athena, output, new_ids)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Load dim_results (CSV → Parquet) via Athena INSERT INTO."
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Wipe existing Parquet data and reload everything from scratch.",
    )
    parser.add_argument(
        "--use-msck",
        action="store_true",
        help="Use MSCK REPAIR TABLE instead of incremental partition registration.",
    )
    args = parser.parse_args()

    try:
        run(force_full_refresh=args.full_refresh, use_msck=args.use_msck)
    except Exception:
        logger.exception("csv_to_parquet failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
