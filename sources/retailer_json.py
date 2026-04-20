"""Generic retailer JSON endpoint poller.

Many retailers expose product data via JSON APIs used by their own frontends.
You find these by opening the retailer site, DevTools -> Network tab -> filter
to XHR/Fetch, and looking for requests that return product lists.

This class polls one configured endpoint and extracts products via JSONPath-ish
dotted paths. Intentionally simple — once you know what you want, extend it.
"""
import logging
from typing import List, Optional

import requests

from .base import Deal, DealSource

log = logging.getLogger(__name__)


class RetailerJSON(DealSource):
    def __init__(
        self,
        name: str,
        url: str,
        price_path: str,
        title_path: str,
        link_template: str = "",
        headers: Optional[dict] = None,
    ):
        self.name = f"Retailer:{name}"
        self.url = url
        self.price_path = price_path
        self.title_path = title_path
        self.link_template = link_template
        self.headers = headers or {
            # Mimic a real browser — most retailer APIs reject default Python UA
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }

    def fetch(self) -> List[Deal]:
        try:
            resp = requests.get(self.url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            log.error(f"[{self.name}] Request failed: {e}")
            return []
        except ValueError as e:
            log.error(f"[{self.name}] Invalid JSON: {e}")
            return []

        # This is intentionally basic — customize per retailer once you pick one.
        # For now it assumes a flat list of products at some path.
        deals = self._extract_deals(data)
        log.info(f"[{self.name}] Fetched {len(deals)} deals.")
        return deals

    def _extract_deals(self, data) -> List[Deal]:
        """Override this per-retailer once you've inspected the response shape.
        The default tries to be permissive but won't work for complex payloads."""
        deals = []
        products = self._find_product_list(data)

        for p in products:
            try:
                price = float(self._get_nested(p, self.price_path.split(".")))
                title = str(self._get_nested(p, self.title_path.split(".")))
                url = self.link_template.format(**p) if self.link_template else self.url
                deals.append(Deal(
                    source=self.name,
                    title=title,
                    url=url,
                    price=price,
                ))
            except (KeyError, TypeError, ValueError) as e:
                log.debug(f"[{self.name}] Skipping malformed product: {e}")
                continue

        return deals

    @staticmethod
    def _find_product_list(data):
        """Heuristic: walk the JSON looking for the first list of dicts."""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data
        if isinstance(data, dict):
            for v in data.values():
                found = RetailerJSON._find_product_list(v)
                if found:
                    return found
        return []

    @staticmethod
    def _get_nested(d, keys):
        for k in keys:
            d = d[k]
        return d
