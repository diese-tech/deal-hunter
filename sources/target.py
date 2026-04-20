"""Target clearance source — queries redsky plp_search_v2 endpoint.

Target exposes its product listing data via redsky.target.com. The `key` in
the URL is Target's public frontend key — not a secret. Response shape:
  data.search.products[] -> { tcin, item.product_description.title, price.current_retail, ... }
"""
import logging
import uuid
from typing import List, Optional

import requests

from .base import Deal, DealSource

log = logging.getLogger(__name__)


class TargetClearance(DealSource):
    """Polls one Target category (default: sitewide clearance) via redsky."""

    BASE_URL = "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2"

    # Target's public frontend API key. Not secret — present in their own HTML.
    DEFAULT_KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e96"

    def __init__(
        self,
        name: str = "Clearance",
        category: str = "5q0ga",     # sitewide clearance
        count: int = 24,
        zip_code: str = "34711",
        store_id: str = "1519",
        api_key: str = DEFAULT_KEY,
    ):
        self.name = f"Target:{name}"
        self.category = category
        self.count = count
        self.zip_code = zip_code
        self.store_id = store_id
        self.api_key = api_key

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://www.target.com/",
            "Origin": "https://www.target.com",
        }

    def _build_params(self, offset: int = 0) -> dict:
        # visitor_id is required but not tied to identity — generate a fresh one.
        # Format matches Target's: 32 hex chars uppercase.
        visitor_id = uuid.uuid4().hex.upper()

        return {
            "category": self.category,
            "count": self.count,
            "default_purchasability_filter": "true",
            "include_sponsored": "false",
            "include_review_summarization": "true",
            "offset": offset,
            "page": f"/c/{self.category}",
            "platform": "desktop",
            "pricing_store_id": self.store_id,
            "spellcheck": "true",
            "store_ids": self.store_id,
            "visitor_id": visitor_id,
            "scheduled_delivery_store_id": self.store_id,
            "zip": self.zip_code,
            "key": self.api_key,
            "channel": "WEB",
            "include_dmc_dmr": "true",
            "useragent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
        }

    def fetch(self) -> List[Deal]:
        """Fetch one page of results. For now we just grab the first `count` items;
        pagination can be added later if we want deeper coverage."""
        try:
            resp = requests.get(
                self.BASE_URL,
                params=self._build_params(),
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            log.error(f"[{self.name}] Request failed: {e}")
            return []
        except ValueError as e:
            log.error(f"[{self.name}] Invalid JSON: {e}")
            return []

        products = self._get_products(data)
        deals = []
        for p in products:
            deal = self._parse_product(p)
            if deal:
                deals.append(deal)

        log.info(f"[{self.name}] Fetched {len(deals)} deals "
                 f"(from {len(products)} products).")
        return deals

    @staticmethod
    def _get_products(data: dict) -> list:
        """Defensive extraction in case Target tweaks the path."""
        try:
            return data["data"]["search"]["products"] or []
        except (KeyError, TypeError):
            log.warning("[Target] Unexpected response shape; no products found.")
            return []

    @staticmethod
    def _parse_product(p: dict) -> Optional[Deal]:
        try:
            tcin = p.get("tcin") or p.get("original_tcin")
            if not tcin:
                return None

            price = None
            price_obj = p.get("price") or {}
            current = price_obj.get("current_retail")
            if current is not None:
                price = float(current)

            original_price = None
            was = price_obj.get("reg_retail") or price_obj.get("formatted_comparison_price")
            if isinstance(was, (int, float)):
                original_price = float(was)
            elif isinstance(was, str):
                try:
                    original_price = float(was.lstrip("$").split()[0])
                except (ValueError, IndexError):
                    original_price = None

            # Title lives in item.product_description.title in full responses.
            item = p.get("item") or {}
            desc = item.get("product_description") or {}
            title = desc.get("title") or f"Target TCIN {tcin}"

            return Deal(
                source="Target:Clearance",
                title=title,
                url=f"https://www.target.com/p/-/A-{tcin}",
                price=price,
                original_price=original_price,
            )
        except Exception as e:
            log.debug(f"[Target] Skipped malformed product: {e}")
            return None