
import yaml
import logging
from config.logger_config import setup_global_logger
from src.extractors.event_name_extractor import EventNameExtractor
from src.database.connections.postgres import PostgresConnection
from src.storage.event_name_storage import EventNameStorage

# Get logger with custom name (single file, no self.logger needed)
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
    
    # Extract 2 pages (pages 1 and 2)
    all_events = extractor.extract(pages=2)
    storage_summary = storage.store_events(all_events)
    logger.info(
        "Persistência de eventos finalizada: %s inseridos, %s ignorados",
        storage_summary["inserted"],
        storage_summary["skipped"],
    )
    
    # Print results
    print("\nPrimeiros 15 eventos:")
    for i, event in enumerate(all_events[:15]):
        print(f"\n{i+1}. {event['name']}")
        print(f"   URL: {event['url']}")
        print(f"   Slug: {event['slug']}")
        print(f"   Cidade: {event['city']}, {event['state']}")
        print(f"   Data: {event['day']}/{event['month']}/{event['year']}")
        print(f"   Total de finalizadores: {event['total_finishers']}")
        if event['distances']:
            print(f"   Distâncias: {event['distances']}")
    
    logger.info("Application finished")