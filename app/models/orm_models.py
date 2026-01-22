from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.core.db import Base

class Trader(Base):
    __tablename__ = "traders"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    config = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    trader_id = Column(String, index=True)
    source = Column(String, index=True)
    external_id = Column(String, index=True)
    symbol = Column(String)
    side = Column(String)
    price = Column(Float, nullable=True)
    quantity = Column(Float)
    leverage = Column(Float, default=1.0)
    pnl = Column(Float, nullable=True)
    orders = Column(JSON, default=[])
    raw = Column(JSON, default={})
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class ReplicatedTrade(Base):
    __tablename__ = "replicated_trades"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    source_trade_id = Column(String, index=True)
    trader_id = Column(String, index=True)
    symbol = Column(String, index=True)
    side = Column(String)
    original_price = Column(Float)
    executed_price = Column(Float, nullable=True)
    quantity = Column(Float)
    leverage = Column(Float, default=1.0)
    pnl = Column(Float, nullable=True)
    fees = Column(Float, default=0.0)
    opened_at = Column(DateTime)
    closed_at = Column(DateTime, nullable=True)
    status = Column(String, default="replicated")
    raw = Column(JSON, default={})
    decision_score = Column(Float, nullable=True)
    decision_threshold = Column(Float, nullable=True)
    features_snapshot = Column(JSON, nullable=True)
    success_label = Column(Integer, nullable=True)  # 1 / 0
    outcome_pnl = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
