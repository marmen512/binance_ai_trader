from fastapi import APIRouter
from app.models.schemas import SignalIn
from app.core.db import SessionLocal
from app.models.orm_models import Signal
from app.core.config import settings
from redis import Redis
from rq import Queue
from datetime import datetime

router = APIRouter(prefix="/api/v1/copytrades", tags=["copytrades"])
redis_conn = Redis.from_url(settings.REDIS_URL)
q = Queue(connection=redis_conn)

@router.post("/ingest")
def ingest(signal_in: SignalIn, min_pnl: float = None):
    db = SessionLocal()
    try:
        s = Signal(
            trader_id=signal_in.trader_id,
            source=signal_in.source,
            external_id=signal_in.external_id,
            symbol=signal_in.symbol,
            side=signal_in.side,
            price=signal_in.price,
            quantity=signal_in.quantity,
            leverage=signal_in.leverage or 1.0,
            pnl=signal_in.pnl,
            orders=[o.dict() for o in (signal_in.orders or [])],
            raw=signal_in.raw,
            processed=False,
            created_at=signal_in.timestamp
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        q.enqueue("app.services.decision_engine.decide_and_replicate", s.id, min_pnl)
        return {"signal_id": s.id, "queued": True}
    finally:
        db.close()
