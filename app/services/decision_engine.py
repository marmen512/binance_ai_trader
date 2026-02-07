from app.core.config import settings
from app.core.db import SessionLocal
from app.models.orm_models import Signal, ReplicatedTrade
from app.services.features import build_features_from_signal
from adaptive.ml_online import OnlineModel
from rq import Queue
from redis import Redis
from app.services.finance_utils import compute_pnl_from_orders
from datetime import datetime

redis_conn = Redis.from_url(settings.REDIS_URL)
q = Queue(connection=redis_conn)

def decide_and_replicate(signal_id: int, min_pnl: float = None):
    db = SessionLocal()
    try:
        signal = db.get(Signal, signal_id)
        if not signal:
            return {"error": "signal not found"}
        pnl = signal.pnl
        if pnl is None and signal.orders:
            pnl = compute_pnl_from_orders(signal.orders)
        min_pnl = min_pnl if min_pnl is not None else settings.COPY_PNL_THRESHOLD
        if pnl is None or pnl < min_pnl:
            signal.processed = True
            db.add(signal)
            db.commit()
            return {"skipped": True, "pnl": pnl}
        # Placeholder trader metrics / market context
        trader_metrics = {"winrate": 0.5, "avg_pnl": 0.0}
        market_context = {}
        features = build_features_from_signal({
            "side": signal.side,
            "quantity": signal.quantity,
            "price": signal.price,
            "leverage": signal.leverage
        }, trader_metrics, market_context)
        model = OnlineModel.load()
        score = model.predict_proba(features)
        threshold = settings.DECISION_THRESHOLD
        if score >= threshold:
            rep = ReplicatedTrade(
                source=signal.source,
                source_trade_id=signal.external_id,
                trader_id=signal.trader_id,
                symbol=signal.symbol,
                side=signal.side,
                original_price=signal.price,
                executed_price=signal.price,
                quantity=signal.quantity,
                leverage=signal.leverage,
                pnl=pnl,
                fees=0.0,
                opened_at=signal.created_at,
                status="replicated",
                raw=signal.raw,
                decision_score=score,
                decision_threshold=threshold,
                features_snapshot=features
            )
            db.add(rep)
            signal.processed = True
            db.add(signal)
            db.commit()
            db.refresh(rep)
            # enqueue simulation job
            q.enqueue("app.workers.jobs.simulate_replicated_trade", rep.id)
            return {"replicated_id": rep.id, "score": score}
        else:
            signal.processed = True
            db.add(signal)
            db.commit()
            return {"skipped_by_score": True, "score": score}
    finally:
        db.close()
