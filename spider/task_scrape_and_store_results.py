import logging

from config.logger_config import setup_global_logger
from main import load_config
from src.database.connections.postgres import PostgresConnection
from src.extractors.event_result_extractor import EventResultExtractor
from src.storage.event_result_storage import EventResultStorage

logger = logging.getLogger("task_scrape_and_store_results")


def run() -> dict[str, int]:
    config = load_config()
    setup_global_logger(
        log_level=config["logging"]["log_level"],
        log_filename=config["logging"]["log_filename"],
        log_dir=config["logging"]["log_dir"],
    )

    db = PostgresConnection()
    extractor = EventResultExtractor(config)
    storage = EventResultStorage(db=db, config=config)

    summary = storage.process_queue(extractor=extractor)
    logger.info("Task 2 completed: %s", summary)
    return summary


if __name__ == "__main__":
    run()
