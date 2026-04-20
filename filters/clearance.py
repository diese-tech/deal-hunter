"""Filter logic: decides which deals are worth alerting on."""
from typing import List

from sources.base import Deal


class ClearanceFilter:
    """Alerts on:
      1. Any deal with parsed price <= max_price, OR
      2. Any deal whose title/description contains a 'penny keyword'
         (even if price couldn't be parsed — don't miss YMMV / glitch deals).
    """

    def __init__(self, max_price: float, penny_keywords: List[str]):
        self.max_price = max_price
        # Lowercase once, match case-insensitively
        self.penny_keywords = [kw.lower() for kw in penny_keywords]

    def matches(self, deal: Deal) -> bool:
        # Rule 1: explicit price match
        if deal.price is not None and deal.price <= self.max_price:
            return True

        # Rule 2: keyword match (catches glitches, penny deals, YMMV)
        haystack = f"{deal.title} {deal.description}".lower()
        return any(kw in haystack for kw in self.penny_keywords)

    def apply(self, deals: List[Deal]) -> List[Deal]:
        return [d for d in deals if self.matches(d)]
