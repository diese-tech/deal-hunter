"""SQLite-backed dedup store — prevents re-alerting same deal."""
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)


class SeenStore:
    def __init__(self, db_path: str = "data/seen.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_schema(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS seen (
                    id TEXT PRIMARY KEY,
                    source TEXT,
                    title TEXT,
                    first_seen TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_first_seen ON seen(first_seen)")

    def is_seen(self, deal_id: str) -> bool:
        with self._conn() as c:
            cur = c.execute("SELECT 1 FROM seen WHERE id = ? LIMIT 1", (deal_id,))
            return cur.fetchone() is not None

    def mark_seen(self, deal_id: str, source: str, title: str):
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO seen(id, source, title, first_seen) VALUES (?, ?, ?, ?)",
                (deal_id, source, title, datetime.utcnow().isoformat()),
            )

    def filter_unseen(self, deals) -> list:
        """Return only deals we haven't seen, and mark them as seen."""
        unseen = []
        for deal in deals:
            did = deal.unique_id()
            if not self.is_seen(did):
                unseen.append(deal)
                self.mark_seen(did, deal.source, deal.title)
        return unseen

    def prune_older_than(self, days: int = 30):
        """Housekeeping — drop old entries to keep the DB small."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._conn() as c:
            cur = c.execute("DELETE FROM seen WHERE first_seen < ?", (cutoff,))
            log.info(f"Pruned {cur.rowcount} old entries.")
