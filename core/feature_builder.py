"""
Feature Builder for AI Trading Pipeline
Computes technical indicators and features from OHLCV data
"""
import pandas as pd
import numpy as np


class FeatureBuilder:
    """Build features from OHLCV data"""
    
    def __init__(self):
        pass
    
    def build(self, df):
        """
        Build features from OHLCV dataframe
        
        Args:
            df: DataFrame with columns [open, high, low, close, volume]
            
        Returns:
            DataFrame with features added
        """
        df = df.copy()
        
        # Price returns
        df['ret1'] = df['close'].pct_change(1)
        df['ret3'] = df['close'].pct_change(3)
        df['ret12'] = df['close'].pct_change(12)
        
        # Volatility
        df['vol10'] = df['ret1'].rolling(10).std()
        
        # EMAs
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_diff'] = (df['ema9'] - df['ema21']) / df['ema21']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Candle features
        df['range'] = (df['high'] - df['low']) / df['close']
        df['body'] = (df['close'] - df['open']) / df['close']
        df['body_pct'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        
        # Volume spike
        df['vol_spike'] = df['volume'] / (df['volume'].rolling(20).mean() + 1e-10)
        
        return df
