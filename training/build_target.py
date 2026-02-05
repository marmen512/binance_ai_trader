"""
Target Builder for AI Trading Pipeline
Creates trading targets based on forward returns
"""
import pandas as pd
import numpy as np


def build_target(df, horizon=6):
    """
    Build trading target based on forward returns
    
    Args:
        df: DataFrame with OHLCV data
        horizon: Forward looking horizon in periods (default 6)
        
    Returns:
        DataFrame with 'target' column added
        target = -1 (SELL), 0 (HOLD), 1 (BUY)
    """
    df = df.copy()
    
    # Calculate forward return
    df['fwd_ret'] = df['close'].shift(-horizon) / df['close'] - 1
    
    # Create target based on forward return thresholds
    # BUY if forward return > 0.5%
    # SELL if forward return < -0.5%
    # HOLD otherwise
    df['target'] = 0
    df.loc[df['fwd_ret'] > 0.005, 'target'] = 1  # BUY
    df.loc[df['fwd_ret'] < -0.005, 'target'] = -1  # SELL
    
    # Drop the forward return column (used only for target creation)
    df = df.drop('fwd_ret', axis=1)
    
    return df
