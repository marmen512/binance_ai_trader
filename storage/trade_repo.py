from core.trade_model import Trade
from storage.db import get_conn


class TradeRepo:

    def save_trade(self, trade: Trade):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
        INSERT OR REPLACE INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.trade_id,
            trade.source,
            trade.leader_id,
            trade.symbol,
            trade.side,
            trade.entry_price,
            trade.exit_price,
            trade.qty,
            trade.pnl,
            trade.opened_at,
            trade.closed_at,
        ))

        conn.commit()
        conn.close()

    def close_trade(self, trade_id: str, exit_price: float, pnl: float, closed_at: str):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
        UPDATE trades
        SET exit_price=?, pnl=?, closed_at=?
        WHERE trade_id=?
        """, (exit_price, pnl, closed_at, trade_id))

        conn.commit()
        conn.close()

    def get_open_trades(self):
        conn = get_conn()
        cur = conn.cursor()

        rows = cur.execute("""
        SELECT * FROM trades WHERE closed_at IS NULL
        """).fetchall()

        conn.close()
        return rows

    def get_all_trades(self):
        conn = get_conn()
        cur = conn.cursor()

        rows = cur.execute("SELECT * FROM trades").fetchall()

        conn.close()
        return rows
