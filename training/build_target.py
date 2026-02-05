import pandas as pd
import numpy as np


def build_target(df, forward_periods=5, threshold=0.002):
    """
    Build classification target for trading:
    - BUY (2): if future return > threshold
    - SELL (0): if future return < -threshold
    - HOLD (1): otherwise
    """
    df = df.copy()
    
    # Calculate forward return
    df["fwd_ret"] = df["close"].pct_change(forward_periods).shift(-forward_periods)
    
    # Create target
    df["target"] = 1  # Default to HOLD
    df.loc[df["fwd_ret"] > threshold, "target"] = 2  # BUY
    df.loc[df["fwd_ret"] < -threshold, "target"] = 0  # SELL
    
    # Drop rows with NaN target
    df = df.dropna(subset=["target"])
    
    return df
