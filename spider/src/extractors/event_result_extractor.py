import logging
from typing import Any
import time

import requests

from src.extractors.base import Extractor
from src.parses.event_modality_parser import parse_modality_targets
from src.parses.event_result_parser import parse_result_rows

logger = logging.getLogger("EventResultExtractor")


class EventResultExtractor(Extractor):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)

        result_cfg = config.get("extact_event_result", {})

        self.request_timeout_s = int(result_cfg.get("request_timeout_s", 60))
        self.request_delay_s = float(result_cfg.get("request_delay_s", 0.0))

        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": result_cfg.get(
                    "user_agent",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36",
                )
            }
        )

    def build_event_url(self, slug: str) -> str:
        clean_slug = (slug or "").strip().strip("/")
        return f"{self.base_url}/evento/{clean_slug}/"

    def _fetch_html(self, url: str) -> str:
        response = self._session.get(url, timeout=self.request_timeout_s)
        response.raise_for_status()
        if self.request_delay_s > 0:
            time.sleep(self.request_delay_s)
        return response.text

    def discover_modalities(self, slug: str) -> list[dict[str, Any]]:
        url = self.build_event_url(slug)
        logger.info("Discovering modalities: %s", url)
        html = self._fetch_html(url)
        targets = parse_modality_targets(html, self.base_url)
        logger.info("Modality targets discovered: %s | slug=%s", len(targets), slug)
        return targets

    def extract_results(self, url: str) -> list[dict[str, str]]:
        logger.info("Scraping results table: %s", url)
        html = self._fetch_html(url)
        rows = parse_result_rows(html)
        logger.info("Rows parsed: %s | url=%s", len(rows), url)
        return rows

    def extract(self, **kwargs) -> list[dict[str, str]]:
        url = kwargs.get("url")
        if not url:
            raise ValueError("extract(url=...) requires a result URL")
        return self.extract_results(url)
