
import yaml
import logging
from typing import Any
from config.logger_config import setup_global_logger
from src.extractors.event_name_extractor import EventNameExtractor
from src.extractors.event_result_extractor import EventResultExtractor
from src.database.connections.postgres import PostgresConnection
from src.storage.event_name_storage import EventNameStorage
from src.storage.event_result_storage import EventResultStorage

logger = logging.getLogger("main")


def load_config() -> dict:
    with open("config/config.yml", "r") as f:
        return yaml.safe_load(f)


def run_stream_pipeline(
    extractor: EventNameExtractor,
    storage: EventNameStorage,
    pipeline_config: dict[str, Any],
) -> dict[str, int]:
    extraction_mode = str(pipeline_config.get("extraction_mode", "paged")).strip().lower()
    use_full = extraction_mode == "full"
    pages = int(pipeline_config.get("pages", 1))
    batch_size = int(pipeline_config.get("batch_size", 500))

    if batch_size <= 0:
        logger.warning("Invalid batch_size=%s. Using fallback=500", batch_size)
        batch_size = 500

    logger.info(
        "Pipeline config: extraction_mode=%s pages=%s batch_size=%s",
        extraction_mode,
        pages,
        batch_size,
    )

    batch: list[dict[str, Any]] = []
    summary = {"inserted": 0, "skipped": 0}
    extracted_total = 0

    for event in extractor.iter_events(pages=pages, use_full=use_full):
        batch.append(event)
        extracted_total += 1

        if len(batch) >= batch_size:
            partial = storage.store_events(batch)
            summary["inserted"] += partial["inserted"]
            summary["skipped"] += partial["skipped"]
            logger.info(
                "Batch persisted: size=%s extracted_total=%s inserted=%s skipped=%s",
                len(batch),
                extracted_total,
                summary["inserted"],
                summary["skipped"],
            )
            batch.clear()

    if batch:
        partial = storage.store_events(batch)
        summary["inserted"] += partial["inserted"]
        summary["skipped"] += partial["skipped"]
        logger.info(
            "Final batch persisted: size=%s extracted_total=%s inserted=%s skipped=%s",
            len(batch),
            extracted_total,
            summary["inserted"],
            summary["skipped"],
        )

    logger.info(
        "Pipeline completed: extracted=%s inserted=%s skipped=%s",
        extracted_total,
        summary["inserted"],
        summary["skipped"],
    )
    return summary


def setup_logging(config: dict[str, Any]) -> None:
    setup_global_logger(
        log_level=config["logging"]["log_level"],
        log_filename=config["logging"]["log_filename"],
        log_dir=config["logging"]["log_dir"],
    )


def run_extract_and_store_names(
    config: dict[str, Any],
    db: PostgresConnection,
) -> dict[str, int]:
    extractor = EventNameExtractor(config)
    storage = EventNameStorage(db)
    pipeline_config = config.get("pipeline", {})

    logger.info("Starting task extract_and_store_names")
    summary = run_stream_pipeline(extractor, storage, pipeline_config)
    logger.info("Finished task extract_and_store_names: %s", summary)
    return summary


def run_scrape_and_store_results(
    config: dict[str, Any],
    db: PostgresConnection,
) -> dict[str, int]:
    extractor = EventResultExtractor(config)
    storage = EventResultStorage(db=db, config=config)

    logger.info("Starting task scrape_and_store_results")
    summary = storage.process_queue(extractor=extractor)
    logger.info("Finished task scrape_and_store_results: %s", summary)
    return summary


def run_full_pipeline_simulation() -> dict[str, dict[str, int]]:
    config = load_config()
    setup_logging(config)

    logger.info("Application started")
    logger.info("Starting local orchestration for Airflow simulation")

    db = PostgresConnection()

    task_1_summary = run_extract_and_store_names(config, db)
    task_2_summary = run_scrape_and_store_results(config, db)

    summary = {
        "extract_and_store_names": task_1_summary,
        "scrape_and_store_results": task_2_summary,
    }
    logger.info("Local orchestration completed: %s", summary)
    return summary


if __name__ == "__main__":
    run_full_pipeline_simulation()