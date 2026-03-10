import time
import requests
import logging
from dataclasses import asdict
from typing import Iterator

from src.extractors.base import Extractor
from src.parses.event_name_parser import _has_events, _parse_page

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

    def iter_events(self, pages: int | None = 1, use_full: bool = False) -> Iterator[dict]:
        page_num = 0
        total_events = 0

        if use_full:
            logger.info("Starting full extraction")
        else:
            logger.info("Starting extraction of %s pages", pages)

        while True:
            if not use_full and pages is not None and page_num >= pages:
                break

            try:
                html = self._fetch_page(page_num)
            except requests.HTTPError as exc:
                logger.error("Failed fetching page %s: %s", page_num, exc)
                break

            if not _has_events(html):
                logger.info("Page %s has no events. Stopping.", page_num)
                break

            events = _parse_page(html, self.base_url)
            page_payload = [asdict(e) for e in events]
            total_events += len(page_payload)
            logger.info(
                "Page %s extracted %s events (total=%s)",
                page_num,
                len(page_payload),
                total_events,
            )

            for event in page_payload:
                yield event

            page_num += 1

            if self.request_delay > 0:
                time.sleep(self.request_delay)

        if use_full:
            logger.info("Full extraction completed: %s events extracted", total_events)
        else:
            logger.info("Extraction completed: %s events extracted", total_events)

    def extract(self, pages: int = 1, **kwargs) -> list[dict]:
        return list(self.iter_events(pages=pages, use_full=False))

    def extract_full(self) -> list[dict]:
        return list(self.iter_events(use_full=True))