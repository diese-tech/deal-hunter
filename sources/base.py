"""Base class all deal sources inherit from."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Deal:
    """Canonical deal format — every source normalizes to this."""
    source: str              # e.g. "Slickdeals:Frontpage"
    title: str
    url: str
    price: Optional[float] = None   # None if price can't be parsed
    original_price: Optional[float] = None
    description: str = ""
    found_at: datetime = field(default_factory=datetime.utcnow)

    def unique_id(self) -> str:
        """Used for dedup. URL is usually stable enough."""
        return self.url


class DealSource:
    """Every source implements fetch() -> list of Deals."""
    name: str = "base"

    def fetch(self) -> List[Deal]:
        raise NotImplementedError
