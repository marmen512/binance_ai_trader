"""
Feature engineering utilities for OHLCV data.
"""
import pandas as pd
import numpy as np


def compute_ohlcv_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical indicators and features from OHLCV data.
    
    Args:
        df: DataFrame with columns [timestamp, open, high, low, close, volume]
        
    Returns:
        DataFrame with original columns plus computed features
    """
    df = df.copy()
    
    # Basic price features
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    
    # Volatility (rolling std of returns)
    df['volatility'] = df['returns'].rolling(window=20).std()
    
    # Average True Range (ATR)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(window=14).mean()
    
    # Candle body percentage
    df['candle_body_pct'] = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
    
    # High-low spread
    df['high_low_spread'] = (df['high'] - df['low']) / df['close']
    
    # Exponential Moving Averages
    df['ema_fast'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # RSI (Relative Strength Index)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    
    # Volume spike (normalized volume)
    vol_ma = df['volume'].rolling(window=20).mean()
    df['vol_spike'] = df['volume'] / (vol_ma + 1e-10)
    
    # Lagged returns
    df['ret_1'] = df['returns'].shift(1)
    df['ret_3'] = df['returns'].shift(3)
    df['ret_5'] = df['returns'].shift(5)
    
    return df


def last_row_features(df: pd.DataFrame) -> dict:
    """
    Extract features from the last row of a DataFrame for inference.
    
    Args:
        df: DataFrame with computed features (output of compute_ohlcv_features)
        
    Returns:
        Dictionary of feature name -> value for the last row
    """
    if len(df) == 0:
        return {}
    
    last_row = df.iloc[-1]
    
    # List of feature columns to extract
    feature_cols = [
        'returns', 'log_returns', 'volatility', 'atr', 
        'candle_body_pct', 'high_low_spread',
        'ema_fast', 'ema_slow', 'rsi', 'macd', 
        'vol_spike', 'ret_1', 'ret_3', 'ret_5'
    ]
    
    features = {}
    for col in feature_cols:
        if col in last_row.index:
            val = last_row[col]
            # Convert to float, handling NaN
            features[col] = float(val) if pd.notna(val) else 0.0
        else:
            features[col] = 0.0
    
    return features
