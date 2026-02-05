"""
Feature engineering module for OHLCV data.

Computes technical indicators and features from OHLCV candle data
for use in trading signal models.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ohlcv_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute OHLCV-derived features for model training/inference.
    
    Args:
        df: DataFrame with columns: open, high, low, close, volume
            (timestamp is optional but recommended as index)
    
    Returns:
        DataFrame with original columns plus computed features
    """
    result = df.copy()
    
    # Basic returns
    result['return'] = result['close'].pct_change()
    result['log_return'] = np.log(result['close'] / result['close'].shift(1))
    
    # Price-based features
    result['high_low_spread'] = (result['high'] - result['low']) / result['close']
    result['open_close_spread'] = (result['close'] - result['open']) / result['open']
    result['candle_body'] = abs(result['close'] - result['open']) / result['close']
    
    # Average True Range (ATR) - 14 period
    high_low = result['high'] - result['low']
    high_close = abs(result['high'] - result['close'].shift(1))
    low_close = abs(result['low'] - result['close'].shift(1))
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    result['atr_14'] = true_range.rolling(window=14, min_periods=1).mean()
    result['atr_14_norm'] = result['atr_14'] / result['close']
    
    # Exponential Moving Averages
    result['ema_9'] = result['close'].ewm(span=9, adjust=False).mean()
    result['ema_21'] = result['close'].ewm(span=21, adjust=False).mean()
    result['ema_50'] = result['close'].ewm(span=50, adjust=False).mean()
    
    # EMA crossovers
    result['ema_9_21_cross'] = (result['ema_9'] - result['ema_21']) / result['close']
    result['ema_9_50_cross'] = (result['ema_9'] - result['ema_50']) / result['close']
    
    # RSI (Relative Strength Index) - 14 period
    delta = result['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14, min_periods=1).mean()
    avg_loss = loss.rolling(window=14, min_periods=1).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    result['rsi_14'] = 100 - (100 / (1 + rs))
    
    # MACD (Moving Average Convergence Divergence)
    ema_12 = result['close'].ewm(span=12, adjust=False).mean()
    ema_26 = result['close'].ewm(span=26, adjust=False).mean()
    result['macd'] = ema_12 - ema_26
    result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
    result['macd_hist'] = result['macd'] - result['macd_signal']
    result['macd_norm'] = result['macd'] / result['close']
    
    # Volatility
    result['volatility_10'] = result['return'].rolling(window=10, min_periods=1).std()
    result['volatility_30'] = result['return'].rolling(window=30, min_periods=1).std()
    
    # Volume features
    result['volume_ma_20'] = result['volume'].rolling(window=20, min_periods=1).mean()
    result['volume_spike'] = result['volume'] / (result['volume_ma_20'] + 1e-10)
    result['volume_change'] = result['volume'].pct_change()
    
    return result


def last_row_features(df: pd.DataFrame) -> dict[str, float]:
    """
    Extract features from the last row of a DataFrame for real-time inference.
    
    Args:
        df: DataFrame with OHLCV data and computed features
    
    Returns:
        Dictionary mapping feature names to values
    """
    if df.empty:
        raise ValueError("DataFrame is empty, cannot extract features")
    
    # Compute features if not already present
    if 'return' not in df.columns:
        df = compute_ohlcv_features(df)
    
    last_row = df.iloc[-1]
    
    # Define feature columns to extract (excluding raw OHLCV and NaN-prone columns)
    feature_cols = [
        'return', 'log_return', 
        'high_low_spread', 'open_close_spread', 'candle_body',
        'atr_14_norm',
        'ema_9_21_cross', 'ema_9_50_cross',
        'rsi_14',
        'macd_norm', 'macd_hist',
        'volatility_10', 'volatility_30',
        'volume_spike', 'volume_change'
    ]
    
    features = {}
    for col in feature_cols:
        if col in last_row.index:
            val = last_row[col]
            # Replace NaN/inf with 0
            if pd.isna(val) or np.isinf(val):
                val = 0.0
            features[col] = float(val)
        else:
            features[col] = 0.0
    
    return features
