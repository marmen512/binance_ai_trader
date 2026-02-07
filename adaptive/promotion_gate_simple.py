"""Promotion Gate - Phase 7 (Simplified)

Compare shadow vs frozen metrics and determine if promotion should occur.
No auto-promotion without explicit metrics verification.
"""

import logging

logger = logging.getLogger(__name__)


def should_promote(shadow_metrics, frozen_metrics):
    """
    Determine if shadow model should be promoted to frozen.
    
    Promotion criteria:
    - Shadow expectancy must be better than frozen
    - Shadow drawdown must not exceed frozen
    
    Args:
        shadow_metrics: Dict with 'expectancy' and 'drawdown' keys
        frozen_metrics: Dict with 'expectancy' and 'drawdown' keys
        
    Returns:
        True if shadow should be promoted, False otherwise
    """
    # Validate inputs
    if not isinstance(shadow_metrics, dict) or not isinstance(frozen_metrics, dict):
        logger.error("Metrics must be dictionaries")
        return False
    
    required_keys = ["expectancy", "drawdown"]
    for key in required_keys:
        if key not in shadow_metrics:
            logger.error(f"Shadow metrics missing '{key}'")
            return False
        if key not in frozen_metrics:
            logger.error(f"Frozen metrics missing '{key}'")
            return False
    
    # Check promotion criteria
    shadow_exp = shadow_metrics["expectancy"]
    frozen_exp = frozen_metrics["expectancy"]
    shadow_dd = shadow_metrics["drawdown"]
    frozen_dd = frozen_metrics["drawdown"]
    
    # Expectancy improvement check
    exp_improved = shadow_exp > frozen_exp
    
    # Drawdown control check
    dd_controlled = shadow_dd <= frozen_dd
    
    result = exp_improved and dd_controlled
    
    if result:
        logger.info(
            f"PROMOTION APPROVED: "
            f"expectancy {frozen_exp:.4f} → {shadow_exp:.4f}, "
            f"drawdown {frozen_dd:.4f} → {shadow_dd:.4f}"
        )
    else:
        reasons = []
        if not exp_improved:
            reasons.append(f"expectancy not improved ({shadow_exp:.4f} <= {frozen_exp:.4f})")
        if not dd_controlled:
            reasons.append(f"drawdown exceeded ({shadow_dd:.4f} > {frozen_dd:.4f})")
        
        logger.info(f"PROMOTION REJECTED: {', '.join(reasons)}")
    
    return result


def calculate_metrics(trades_df):
    """
    Calculate expectancy and drawdown from trades DataFrame.
    
    Args:
        trades_df: DataFrame with 'pnl' column
        
    Returns:
        Dict with 'expectancy' and 'drawdown' keys
    """
    if trades_df.empty:
        return {"expectancy": 0.0, "drawdown": 0.0}
    
    # Expectancy = average PnL per trade
    expectancy = trades_df["pnl"].mean()
    
    # Drawdown = maximum peak-to-trough decline
    cumulative = trades_df["pnl"].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max).min()
    
    # Convert to absolute value for comparison
    drawdown = abs(drawdown)
    
    return {
        "expectancy": float(expectancy),
        "drawdown": float(drawdown),
    }
