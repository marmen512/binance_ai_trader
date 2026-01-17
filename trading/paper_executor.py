from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from core.logging import setup_logger
from trading.paper_trading import PaperTradeOnceResult

logger = setup_logger("binance_ai_trader.paper_executor")


@dataclass(frozen=True)
class TradeRecord:
    timestamp: str
    entry_price: float
    exit_price: Optional[float]
    direction: str  # BUY, SELL, HOLD
    pnl_pct: Optional[float]
    reasoning: str
    model_id: str
    entry_ts: str
    exit_ts: Optional[str]
    status: str  # OPEN, CLOSED


class PaperTradingExecutor:
    def __init__(self, replay_path: str | Path = Path("ai_data") / "paper" / "replay.jsonl"):
        self.replay_path = Path(replay_path)
        self.replay_path.parent.mkdir(parents=True, exist_ok=True)
        self.open_trades: dict[str, TradeRecord] = {}
        
    def execute_trade(self, result: PaperTradeOnceResult, market_data: dict) -> Optional[TradeRecord]:
        timestamp = market_data.get("timestamp", pd.Timestamp.now().isoformat())
        mid_price = result.mid_price
        direction = "HOLD"
        
        if result.target_position > 0:
            direction = "BUY"
        elif result.target_position < 0:
            direction = "SELL"
            
        if direction == "HOLD":
            return None
            
        trade_id = f"{result.model_id}_{timestamp}"
        
        trade = TradeRecord(
            timestamp=timestamp,
            entry_price=mid_price,
            exit_price=None,
            direction=direction,
            pnl_pct=None,
            reasoning=f"Model prediction: {result.y_hat:.4f}, Target position: {result.target_position:.4f}",
            model_id=result.model_id,
            entry_ts=timestamp,
            exit_ts=None,
            status="OPEN"
        )
        
        self.open_trades[trade_id] = trade
        self._log_trade(trade)
        
        logger.info(f"Opened paper trade: {trade_id} {direction} @ {mid_price}")
        return trade
    
    def close_trades(self, current_price: float, timestamp: str) -> list[TradeRecord]:
        closed_trades = []
        
        for trade_id, trade in list(self.open_trades.items()):
            if trade.status == "OPEN":
                closed_trade = TradeRecord(
                    timestamp=trade.timestamp,
                    entry_price=trade.entry_price,
                    exit_price=current_price,
                    direction=trade.direction,
                    pnl_pct=self._calculate_pnl_pct(trade.entry_price, current_price, trade.direction),
                    reasoning=trade.reasoning,
                    model_id=trade.model_id,
                    entry_ts=trade.entry_ts,
                    exit_ts=timestamp,
                    status="CLOSED"
                )
                
                closed_trades.append(closed_trade)
                del self.open_trades[trade_id]
                self._log_trade(closed_trade)
                
                logger.info(f"Closed paper trade: {trade_id} PnL: {closed_trade.pnl_pct:.2f}%")
        
        return closed_trades
    
    def _calculate_pnl_pct(self, entry_price: float, exit_price: float, direction: str) -> float:
        if direction == "BUY":
            return ((exit_price - entry_price) / entry_price) * 100.0
        elif direction == "SELL":
            return ((entry_price - exit_price) / entry_price) * 100.0
        else:
            return 0.0
    
    def _log_trade(self, trade: TradeRecord) -> None:
        with open(self.replay_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(trade), ensure_ascii=False) + "\n")
    
    def get_open_trades(self) -> dict[str, TradeRecord]:
        return self.open_trades.copy()
    
    def load_replay_buffer(self) -> list[TradeRecord]:
        if not self.replay_path.exists():
            return []
        
        trades = []
        with open(self.replay_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    trade_data = json.loads(line)
                    trades.append(TradeRecord(**trade_data))
        
        return trades
