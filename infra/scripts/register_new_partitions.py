#!/usr/bin/env python3
"""
Register only new S3 partitions on Glue/Athena using ALTER TABLE ADD PARTITION.

This avoids full scans done by MSCK REPAIR TABLE on every run.

Requirements
------------
    pip install boto3 pyyaml

Usage
-----
    python infra/scripts/register_new_partitions.py
    python infra/scripts/register_new_partitions.py --dry-run
    python infra/scripts/register_new_partitions.py --batch-size 100
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from pathlib import Path
from typing import Any

import boto3
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "spider" / "config" / "config.yml"

DATABASE = "running_results"
TABLE = "results_csv"

# Glue partition keys order in results_csv table.
PARTITION_KEYS = ("state", "city", "modality", "pcd", "gender_partition", "event")

# S3 path uses gender=... but Glue key is gender_partition.
_PARTITION_REGEX = re.compile(
    r"^"
    r"state=(?P<state>[^/]+)/"
    r"city=(?P<city>[^/]+)/"
    r"modality=(?P<modality>[^/]+)/"
    r"pcd=(?P<pcd>[^/]+)/"
    r"gender=(?P<gender_partition>[^/]+)/"
    r"event=(?P<event>[^/]+)/"
)

logger = logging.getLogger("register_new_partitions")


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def _build_session(config: dict[str, Any]) -> boto3.Session:
    s3_cfg = config.get("s3", {})
    profile = s3_cfg.get("profile_name") or None
    region = s3_cfg.get("region") or "us-east-1"
    return boto3.Session(profile_name=profile, region_name=region)


def _build_athena_client(session: boto3.Session):
    return session.client("athena")


def _build_glue_client(session: boto3.Session):
    return session.client("glue")


def _build_s3_client(session: boto3.Session):
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
    resp = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": output_location},
    )
    execution_id = resp["QueryExecutionId"]
    state, execution = _wait_for_query(client, execution_id)
    if state != "SUCCEEDED":
        reason = execution["QueryExecution"]["Status"].get("StateChangeReason", "")
        raise RuntimeError(f"Athena query {state}: {reason}\\n---\\n{query}")
    return execution_id


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _partition_location(base_prefix: str, values: tuple[str, ...]) -> str:
    state, city, modality, pcd, gender_partition, event = values
    return (
        f"{base_prefix}/"
        f"state={state}/city={city}/modality={modality}/pcd={pcd}/"
        f"gender={gender_partition}/event={event}/"
    )


def _get_registered_partitions(glue_client) -> set[tuple[str, ...]]:
    partitions: set[tuple[str, ...]] = set()
    paginator = glue_client.get_paginator("get_partitions")

    for page in paginator.paginate(DatabaseName=DATABASE, TableName=TABLE):
        for partition in page.get("Partitions", []):
            values = tuple(partition.get("Values", []))
            if len(values) == len(PARTITION_KEYS):
                partitions.add(values)

    return partitions


def _extract_partition_tuple_from_key(results_prefix: str, key: str) -> tuple[str, ...] | None:
    normalized_prefix = results_prefix.strip("/") + "/"
    if not key.startswith(normalized_prefix):
        return None

    relative = key[len(normalized_prefix) :]
    match = _PARTITION_REGEX.match(relative)
    if not match:
        return None

    groups = match.groupdict()
    return tuple(groups[k] for k in PARTITION_KEYS)


def _get_partitions_from_s3(s3_client, bucket: str, results_prefix: str) -> set[tuple[str, ...]]:
    partitions: set[tuple[str, ...]] = set()
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=results_prefix.strip("/") + "/"):
        for obj in page.get("Contents", []):
            key = obj.get("Key", "")
            if not key.endswith(".csv"):
                continue
            partition_values = _extract_partition_tuple_from_key(results_prefix, key)
            if partition_values:
                partitions.add(partition_values)

    return partitions


def _build_add_partition_query(base_s3_prefix: str, partitions: list[tuple[str, ...]]) -> str:
    clauses = []
    for values in partitions:
        key_values = ", ".join(
            f"{key}='{_escape_sql_literal(value)}'" for key, value in zip(PARTITION_KEYS, values)
        )
        location = _partition_location(base_s3_prefix.rstrip("/"), values)
        clauses.append(f"PARTITION ({key_values}) LOCATION '{location}'")

    return f"ALTER TABLE {TABLE} ADD IF NOT EXISTS\\n" + "\\n".join(clauses)


def register_new_partitions(*, dry_run: bool = False, batch_size: int = 100) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    config = _load_config()
    session = _build_session(config)
    s3_client = _build_s3_client(session)
    glue_client = _build_glue_client(session)
    athena_client = _build_athena_client(session)

    bucket = config["s3"]["bucket"]
    results_prefix = config["s3"].get("results_prefix", "results").strip("/")
    output_location = _athena_output(config)
    base_s3_prefix = f"s3://{bucket}/{results_prefix}"

    logger.info("Loading currently registered partitions from Glue...")
    registered = _get_registered_partitions(glue_client)
    logger.info("Glue partitions: %d", len(registered))

    logger.info("Scanning S3 objects to discover partition paths...")
    discovered = _get_partitions_from_s3(s3_client, bucket, results_prefix)
    logger.info("S3 partitions discovered: %d", len(discovered))

    new_partitions = sorted(discovered - registered)
    if not new_partitions:
        logger.info("No new partitions to register.")
        return 0

    logger.info("New partitions to register: %d", len(new_partitions))
    if dry_run:
        sample = new_partitions[: min(10, len(new_partitions))]
        logger.info("Dry-run enabled. Sample new partitions: %s", sample)
        return len(new_partitions)

    added = 0
    for i in range(0, len(new_partitions), batch_size):
        batch = new_partitions[i : i + batch_size]
        query = _build_add_partition_query(base_s3_prefix, batch)
        _run_query(athena_client, query, output_location)
        added += len(batch)
        logger.info("Registered %d/%d partitions", added, len(new_partitions))

    logger.info("Finished. Registered %d new partitions.", added)
    return added


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Register only new results_csv partitions using ALTER TABLE ADD PARTITION."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect new partitions without executing ALTER TABLE.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="How many partitions to add per ALTER TABLE statement.",
    )
    args = parser.parse_args()

    try:
        register_new_partitions(dry_run=args.dry_run, batch_size=args.batch_size)
    except Exception:
        logger.exception("register_new_partitions failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
