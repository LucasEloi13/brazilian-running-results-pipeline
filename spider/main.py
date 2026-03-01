
import yaml
import logging
from config.logger_config import setup_global_logger
from src.extractors.event_name_extractor import EventNameExtractor

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

    
    
    # Create extractor
    extractor = EventNameExtractor(config)
    
    # Extract 2 pages (pages 1 and 2)
    all_events = extractor.extract(pages=2)
    
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