import time
import yaml
import requests
import logging
from dataclasses import asdict

from src.extractors.base import Extractor
from src.parses.event_name_parser import _has_events, _parse_page

# Get logger with class name (single file, no self.logger needed)
logger = logging.getLogger("EventNameExtractor")


class EventNameExtractor(Extractor):
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        self.api_endpoint = config["extact_event_name"]["api_endpoint"]
        self.request_delay = config["extact_event_name"]["request_delay"]
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": config["extact_event_name"]["user_agent"]}
            )

    def _fetch_page(self, page: int) -> str:
        url = f"{self.base_url}{self.api_endpoint}?page={page}"
        response = self._session.get(url)
        response.raise_for_status()
        return response.text

    def extract(self, pages: int = 1, **kwargs) -> list[dict]:
        all_events: list[dict] = []
        logger.info(f"Starting extraction of {pages} pages")
        for page_num in range(1, pages + 1):
            html = self._fetch_page(page_num)
            
            if not _has_events(html):
                logger.info(f"Page {page_num} has no events. Stopping.")
                break
            
            events = _parse_page(html, self.base_url)
            all_events.extend(asdict(e) for e in events)

            logger.info(f"Page {page_num} extracted {len(events)} events (total={len(all_events)})")
            if page_num < pages:
                time.sleep(self.request_delay)
        logger.info(f"Extraction completed: {len(all_events)} events extracted")
        return all_events

    def extract_full(self) -> list[dict]:
        import time
        all_events: list[dict] = []
        page_num = 0
        
        logger.info(f"Starting full extraction")
        while True:            
            html = self._fetch_page(page_num)
            
            if not _has_events(html):
                logger.info(f"Page {page_num} has no events. Stopping.")
                break
            
            events = _parse_page(html, self.base_url)
            all_events.extend(asdict(e) for e in events)
            logger.info(f"Page {page_num} extracted {len(events)} events (total={len(all_events)})")
            page_num += 1
            time.sleep(self.request_delay)
        logger.info(f"Full extraction completed: {len(all_events)} events extracted")
        return all_events