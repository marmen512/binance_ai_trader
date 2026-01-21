from app.core.db import SessionLocal
from app.models.orm_models import ReplicatedTrade
from app.services.finance_utils import compute_pnl_from_orders
from app.services.ml_online import OnlineModel

def simulate_replicated_trade(rep_id: int):
    db = SessionLocal()
    try:
        rep = db.get(ReplicatedTrade, rep_id)
        if not rep:
            return
        pnl = None
        if rep.raw and rep.raw.get("orders"):
            pnl = compute_pnl_from_orders(rep.raw.get("orders", []))
        else:
            # fallback: simple 0 pnl (extend with backtester)
            pnl = 0.0
        rep.outcome_pnl = pnl
        rep.success_label = 1 if (pnl is not None and pnl > 0) else 0
        rep.status = "closed"
        db.add(rep)
        db.commit()
        # immediate online training
        train_online_from_example(rep.id)
    finally:
        db.close()

def train_online_from_example(rep_id: int):
    db = SessionLocal()
    try:
        rep = db.get(ReplicatedTrade, rep_id)
        if not rep or not rep.features_snapshot:
            return
        features = rep.features_snapshot
        label = int(rep.success_label or 0)
        model = OnlineModel.load()
        try:
            model.learn(features, label)
            model.save()
        except Exception:
            pass
    finally:
        db.close()
