"""Deal Hunter — entry point.

Run: python main.py           (continuous, on schedule)
Run: python main.py --once    (single pass, useful for testing)
"""
import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from filters import ClearanceFilter
from notifiers import DiscordNotifier
from sources import RetailerJSON, SlickdealsRSS
from storage import SeenStore


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("deal_hunter.log"),
        ],
    )


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_sources(config: dict) -> list:
    sources = []
    for feed in config.get("slickdeals_feeds", []):
        sources.append(SlickdealsRSS(name=feed["name"], url=feed["url"]))
    for ep in config.get("retailer_endpoints", []):
        sources.append(RetailerJSON(
            name=ep["name"],
            url=ep["url"],
            price_path=ep["price_path"],
            title_path=ep["title_path"],
            link_template=ep.get("link_template", ""),
        ))
    return sources


def run_once(sources, filt, store, notifier, log):
    log.info(f"=== Scan starting: {len(sources)} source(s) ===")
    all_deals = []
    for src in sources:
        all_deals.extend(src.fetch())

    log.info(f"Total raw deals: {len(all_deals)}")
    matched = filt.apply(all_deals)
    log.info(f"Matching filter: {len(matched)}")

    new_deals = store.filter_unseen(matched)
    log.info(f"New (unseen) deals: {len(new_deals)}")

    if new_deals:
        sent = notifier.send_batch(new_deals)
        log.info(f"Sent {sent}/{len(new_deals)} to Discord")
    else:
        log.info("No new deals to send.")

    log.info("=== Scan complete ===\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--test-alert", action="store_true",
                        help="Send a fake deal to Discord to verify webhook works")
    args = parser.parse_args()

    # Load env
    load_dotenv()
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    setup_logging(log_level)
    log = logging.getLogger("main")

    if not webhook or "YOUR_WEBHOOK" in webhook:
        log.error("DISCORD_WEBHOOK_URL missing or placeholder. Edit .env first.")
        sys.exit(1)

    # Handle --test-alert before any other setup
    if args.test_alert:
        from datetime import datetime, timezone
        from sources.base import Deal
        notifier = DiscordNotifier(webhook_url=webhook)
        fake_deal = Deal(
            source="TEST",
            title="🧪 Test Alert — if you see this, Discord works",
            url="https://example.com/test",
            price=0.01,
            original_price=99.99,
            description="This is a test alert from Deal Hunter. You can ignore/delete it.",
            found_at=datetime.now(timezone.utc),
        )
        ok = notifier.send(fake_deal)
        log.info(f"Test alert sent: {ok}")
        sys.exit(0 if ok else 1)

    config = load_config()
    sources = build_sources(config)
    if not sources:
        log.error("No sources configured. Edit config.yaml.")
        sys.exit(1)

    filt = ClearanceFilter(
        max_price=float(config.get("max_price", 5.00)),
        penny_keywords=config.get("penny_keywords", []),
    )
    store = SeenStore()
    notifier = DiscordNotifier(webhook_url=webhook)

    # Cold-start warm-up: seed dedup silently, DON'T also run a scan after.
    cold_start = not Path("data/seen.db").exists() or _db_is_empty(store)
    if cold_start:
        log.info("Cold start detected — warming dedup store (no alerts sent).")
        for src in sources:
            raw = src.fetch()
            matched = filt.apply(raw)
            for d in matched:
                store.mark_seen(d.unique_id(), d.source, d.title)
        log.info("Dedup warmed. Next scheduled scan will alert on new deals only.")
        if args.once:
            # On cold start, --once IS the warm-up. Don't double-scan.
            return

    if args.once:
        run_once(sources, filt, store, notifier, log)
        return

    # Scheduled mode
    interval = int(config.get("poll_interval_minutes", 5))
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_once,
        "interval",
        minutes=interval,
        args=[sources, filt, store, notifier, log],
    )
    log.info(f"Scheduler started. Scanning every {interval} minute(s). Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down.")


def _db_is_empty(store: SeenStore) -> bool:
    with store._conn() as c:
        cur = c.execute("SELECT COUNT(*) FROM seen")
        return cur.fetchone()[0] == 0


if __name__ == "__main__":
    main()
