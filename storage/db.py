import sqlite3
from pathlib import Path

DB_PATH = Path("storage/trades.db")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        trade_id TEXT PRIMARY KEY,
        source TEXT,
        leader_id TEXT,
        symbol TEXT,
        side TEXT,
        entry_price REAL,
        exit_price REAL,
        qty REAL,
        pnl REAL,
        opened_at TEXT,
        closed_at TEXT
    )
    """)

    conn.commit()
    conn.close()
