import logging
from typing import Any

from config.logger_config import setup_global_logger
from main import load_config
from src.database.connections.postgres import PostgresConnection
from src.storage.dimensions_storage import DimensionsStorage

logger = logging.getLogger("task_export_dimensions")


def run(
    dimensions: list[str] | None = None,
    force_dimensions: set[str] | None = None,
    respect_frequency: bool = True,
) -> list[dict[str, Any]]:
    config = load_config()
    setup_global_logger(
        log_level=config["logging"]["log_level"],
        log_filename=config["logging"]["log_filename"],
        log_dir=config["logging"]["log_dir"],
    )

    db = PostgresConnection()
    storage = DimensionsStorage(db=db, config=config)
    try:
        summary = storage.export_dimensions(
            dimensions=dimensions,
            force_dimensions=force_dimensions,
            respect_frequency=respect_frequency,
        )
        logger.info("Dimensions task completed: %s", summary)
        return summary
    finally:
        storage.close()


if __name__ == "__main__":
    run()