
import yaml
import logging
from config.logger_config import setup_global_logger
from src.extractors.event_name_extractor import EventNameExtractor
from src.database.connections.postgres import PostgresConnection
from src.storage.event_name_storage import EventNameStorage

logger = logging.getLogger("main")


def load_config() -> dict:
    with open("config/config.yml", "r") as f:
        return yaml.safe_load(f)


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
    
    # Extract all events
    # all_events = extractor.extract_full()
    all_events = extractor.extract(pages=1)
    storage_summary = storage.store_events(all_events)