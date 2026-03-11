import logging

from config.logger_config import setup_global_logger
from main import load_config, run_stream_pipeline
from src.database.connections.postgres import PostgresConnection
from src.extractors.event_name_extractor import EventNameExtractor
from src.storage.event_name_storage import EventNameStorage

logger = logging.getLogger("task_extract_and_store_names")


def run() -> dict[str, int]:
    config = load_config()
    setup_global_logger(
        log_level=config["logging"]["log_level"],
        log_filename=config["logging"]["log_filename"],
        log_dir=config["logging"]["log_dir"],
    )

    db = PostgresConnection()
    extractor = EventNameExtractor(config)
    storage = EventNameStorage(db)

    pipeline_config = config.get("pipeline", {})
    summary = run_stream_pipeline(extractor, storage, pipeline_config)
    logger.info("Task 1 completed: %s", summary)
    return summary


if __name__ == "__main__":
    run()
