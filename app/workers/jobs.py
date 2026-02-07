from app.core.db import SessionLocal
from app.models.orm_models import ReplicatedTrade
from app.services.finance_utils import compute_pnl_from_orders
from app.services.ml_online import OnlineModel
import logging

logger = logging.getLogger(__name__)


def simulate_replicated_trade(rep_id: int):
    """
    Simulate a replicated trade and compute its outcome.
    
    This function is idempotent and can be safely retried.
    
    Args:
        rep_id: ID of the replicated trade to simulate
        
    Returns:
        dict: Result of the simulation including PnL and status
    """
    db = SessionLocal()
    try:
        rep = db.get(ReplicatedTrade, rep_id)
        if not rep:
            logger.warning(f"ReplicatedTrade {rep_id} not found")
            return {"error": "ReplicatedTrade not found", "rep_id": rep_id}
        
        # Skip if already processed
        if rep.status == "closed":
            logger.info(f"ReplicatedTrade {rep_id} already closed, skipping")
            return {
                "success": True,
                "rep_id": rep_id,
                "status": "already_closed",
                "pnl": rep.outcome_pnl
            }
        
        pnl = None
        if rep.raw and rep.raw.get("orders"):
            try:
                pnl = compute_pnl_from_orders(rep.raw.get("orders", []))
            except Exception as e:
                logger.error(f"Error computing PnL for rep {rep_id}: {str(e)}")
                # Use fallback PnL
                pnl = 0.0
        else:
            # fallback: simple 0 pnl (extend with backtester)
            pnl = 0.0
        
        rep.outcome_pnl = pnl
        rep.success_label = 1 if (pnl is not None and pnl > 0) else 0
        rep.status = "closed"
        db.add(rep)
        db.commit()
        db.refresh(rep)
        
        # immediate online training
        try:
            train_online_from_example(rep.id)
        except Exception as e:
            logger.error(f"Error in online training for rep {rep_id}: {str(e)}")
            # Don't fail the whole job if training fails
        
        logger.info(f"Successfully simulated trade {rep_id} with PnL {pnl}")
        return {
            "success": True,
            "rep_id": rep_id,
            "pnl": pnl,
            "success_label": rep.success_label
        }
        
    except Exception as e:
        logger.error(f"Error simulating replicated trade {rep_id}: {str(e)}", exc_info=True)
        raise  # Re-raise to mark job as failed
    finally:
        db.close()


def train_online_from_example(rep_id: int):
    """
    Train the online model from a replicated trade example.
    
    This function is idempotent and can be safely retried.
    
    Args:
        rep_id: ID of the replicated trade to learn from
        
    Returns:
        dict: Result of the training operation
    """
    db = SessionLocal()
    try:
        rep = db.get(ReplicatedTrade, rep_id)
        if not rep:
            logger.warning(f"ReplicatedTrade {rep_id} not found for training")
            return {"error": "ReplicatedTrade not found", "rep_id": rep_id}
        
        if not rep.features_snapshot:
            logger.warning(f"No features_snapshot for rep {rep_id}, skipping training")
            return {"skipped": True, "reason": "No features_snapshot", "rep_id": rep_id}
        
        features = rep.features_snapshot
        label = int(rep.success_label or 0)
        
        try:
            model = OnlineModel.load()
            model.learn(features, label)
            model.save()
            
            logger.info(f"Successfully trained online model from rep {rep_id}")
            return {
                "success": True,
                "rep_id": rep_id,
                "label": label
            }
        except Exception as e:
            logger.error(f"Error in online model training for rep {rep_id}: {str(e)}")
            raise  # Re-raise to mark job as failed
            
    except Exception as e:
        logger.error(f"Error training from example {rep_id}: {str(e)}", exc_info=True)
        raise  # Re-raise to mark job as failed
    finally:
        db.close()
