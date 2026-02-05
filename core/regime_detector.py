"""
Regime Detector
Detects market regime based on volatility and trend
"""
import numpy as np
import pandas as pd


class RegimeDetector:
    """Detect market regime: VOLATILE, TREND, or RANGE"""
    
    def __init__(self, vol_window=20, trend_window=50):
        """
        Initialize regime detector
        
        Args:
            vol_window: Window for volatility calculation
            trend_window: Window for trend detection
        """
        self.vol_window = vol_window
        self.trend_window = trend_window
    
    def detect(self, df):
        """
        Detect current market regime
        
        Args:
            df: DataFrame with OHLCV data and features
            
        Returns:
            String: "VOLATILE", "TREND", or "RANGE"
        """
        # Calculate recent volatility
        returns = df['close'].pct_change()
        recent_vol = returns.iloc[-self.vol_window:].std()
        
        # Calculate historical volatility for comparison
        hist_vol = returns.iloc[-100:].std() if len(returns) >= 100 else recent_vol
        
        # Calculate trend strength using EMA
        if 'ema9' in df.columns and 'ema21' in df.columns:
            ema_diff = abs(df['ema9'].iloc[-1] - df['ema21'].iloc[-1]) / df['close'].iloc[-1]
        else:
            ema9 = df['close'].ewm(span=9, adjust=False).mean()
            ema21 = df['close'].ewm(span=21, adjust=False).mean()
            ema_diff = abs(ema9.iloc[-1] - ema21.iloc[-1]) / df['close'].iloc[-1]
        
        # Regime classification
        # VOLATILE: High volatility compared to historical
        if recent_vol > hist_vol * 1.5:
            return "VOLATILE"
        
        # TREND: Strong EMA separation
        if ema_diff > 0.02:
            return "TREND"
        
        # RANGE: Low volatility and weak trend
        return "RANGE"
