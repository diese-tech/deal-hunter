"""Slickdeals RSS source. Free, public, reliable."""
import logging
import re
from typing import List

import feedparser

from .base import Deal, DealSource

log = logging.getLogger(__name__)

# Matches $0.01, $5, $5.99, etc. Captures the number.
PRICE_PATTERN = re.compile(r"\$(\d+(?:\.\d{1,2})?)")


class SlickdealsRSS(DealSource):
    def __init__(self, name: str, url: str):
        self.name = f"Slickdeals:{name}"
        self.url = url

    def fetch(self) -> List[Deal]:
        try:
            feed = feedparser.parse(self.url)
        except Exception as e:
            log.error(f"[{self.name}] Feed parse failed: {e}")
            return []

        if feed.bozo and not feed.entries:
            log.warning(f"[{self.name}] Malformed feed, no entries.")
            return []

        deals = []
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            desc = entry.get("summary", "").strip()

            if not title or not url:
                continue

            price = self._extract_price(title) or self._extract_price(desc)

            deals.append(Deal(
                source=self.name,
                title=title,
                url=url,
                price=price,
                description=desc[:500],   # Truncate long descriptions
            ))

        log.info(f"[{self.name}] Fetched {len(deals)} deals.")
        return deals

    @staticmethod
    def _extract_price(text: str) -> float | None:
        """Pull the first $ price out of text. Takes the LOWEST if multiple
        (since deal titles often read '$5 (was $50)')."""
        if not text:
            return None
        matches = PRICE_PATTERN.findall(text)
        if not matches:
            return None
        try:
            return min(float(m) for m in matches)
        except ValueError:
            return None
