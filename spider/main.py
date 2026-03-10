
import yaml
import logging
from typing import Any
from config.logger_config import setup_global_logger
from src.extractors.event_name_extractor import EventNameExtractor
from src.database.connections.postgres import PostgresConnection
from src.storage.event_name_storage import EventNameStorage

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
    genders = pipeline_config.get("genders") or ["M", "F"]

    if batch_size <= 0:
        logger.warning("Invalid batch_size=%s. Using fallback=500", batch_size)
        batch_size = 500

    logger.info(
        "Pipeline config: extraction_mode=%s pages=%s batch_size=%s genders=%s",
        extraction_mode,
        pages,
        batch_size,
        genders,
    )

    batch: list[dict[str, Any]] = []
    summary = {"inserted": 0, "skipped": 0}
    extracted_total = 0

    for event in extractor.iter_events(pages=pages, use_full=use_full):
        batch.append(event)
        extracted_total += 1

        if len(batch) >= batch_size:
            partial = storage.store_events(batch, genders=genders)
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
        partial = storage.store_events(batch, genders=genders)
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


if __name__ == "__main__":

    config = load_config()

    setup_global_logger(
        log_level=config["logging"]["log_level"],
        log_filename=config["logging"]["log_filename"],  
        log_dir=config["logging"]["log_dir"]
    )
    
    logger.info("Application started")

    # Initialize database connection
    db = PostgresConnection()
    
    # Create extractor
    extractor = EventNameExtractor(config)
    storage = EventNameStorage(db)
    
    pipeline_config = config.get("pipeline", {})
    storage_summary = run_stream_pipeline(extractor, storage, pipeline_config)
    logger.info("Storage summary: %s", storage_summary)