import sqlite3
from pathlib import Path


class TraderAnalytics:

    def __init__(self, db_path: str = "storage/trades.db"):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def leader_summary(self, leader_id: str):
        with self._conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT pnl
                FROM trades
                WHERE leader_id = ?
                AND pnl IS NOT NULL
            """, (leader_id,))

            rows = [r[0] for r in cur.fetchall() if r[0] is not None]

            if not rows:
                return {
                    "leader_id": leader_id,
                    "trades": 0,
                    "total_pnl": 0,
                    "roi": 0,
                    "winrate": 0,
                    "avg_pnl": 0,
                }

            total = len(rows)
            wins = len([x for x in rows if x > 0])
            total_pnl = sum(rows)
            roi = total_pnl / total
            avg = total_pnl / total

            return {
                "leader_id": leader_id,
                "trades": total,
                "total_pnl": total_pnl,
                "roi": roi,
                "winrate": wins / total,
                "avg_pnl": avg,
            }

    def all_leaders(self):
        with self._conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT DISTINCT leader_id
                FROM trades
                WHERE leader_id IS NOT NULL
            """)

            leaders = [r[0] for r in cur.fetchall()]

        return [self.leader_summary(l) for l in leaders]
