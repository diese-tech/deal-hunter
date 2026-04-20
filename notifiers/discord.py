"""Discord webhook notifier — posts deals as rich embeds."""
import logging
import time
from typing import List

import requests

from sources.base import Deal

log = logging.getLogger(__name__)


class DiscordNotifier:
    # Discord webhooks are rate-limited to ~30/min. We pace to 1/sec to be safe.
    MIN_DELAY = 1.1

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, deal: Deal) -> bool:
        embed = {
            "title": deal.title[:256],   # Discord embed title limit
            "url": deal.url,
            "description": deal.description[:500] if deal.description else "",
            "color": 0x00FF00 if (deal.price and deal.price <= 1) else 0xFFAA00,
            "fields": [],
            "footer": {"text": deal.source},
            "timestamp": deal.found_at.isoformat(),
        }

        if deal.price is not None:
            embed["fields"].append({
                "name": "Price",
                "value": f"${deal.price:.2f}",
                "inline": True,
            })
        if deal.original_price is not None:
            embed["fields"].append({
                "name": "Was",
                "value": f"${deal.original_price:.2f}",
                "inline": True,
            })

        payload = {"embeds": [embed]}

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code == 429:
                # Rate limited — back off and retry once
                retry_after = float(resp.json().get("retry_after", 2))
                log.warning(f"Discord rate limit, sleeping {retry_after}s")
                time.sleep(retry_after)
                resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            log.error(f"Discord send failed: {e}")
            return False

    def send_batch(self, deals: List[Deal]) -> int:
        sent = 0
        for deal in deals:
            if self.send(deal):
                sent += 1
            time.sleep(self.MIN_DELAY)
        return sent
