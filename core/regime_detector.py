"""
Regime detector for market classification.
"""
import pandas as pd


class RegimeDetector:
    """
    Detects market regime based on volatility and trend indicators.
    """
    
    def __init__(self, vol_threshold=0.02, trend_threshold=0.01):
        """
        Args:
            vol_threshold: ATR/price threshold for high volatility
            trend_threshold: Absolute price change threshold for trending
        """
        self.vol_threshold = vol_threshold
        self.trend_threshold = trend_threshold
    
    def detect(self, df):
        """
        Detect regime for each row in dataframe.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with 'regime' column added (TREND, RANGE, VOLATILE)
        """
        result = df.copy()
        
        # Calculate volatility (ATR as % of close)
        if 'atr_14' in df.columns and 'close' in df.columns:
            vol = df['atr_14'] / df['close']
        elif 'close' in df.columns:
            # Simple volatility measure
            vol = df['close'].pct_change().rolling(14).std()
        else:
            vol = pd.Series(0, index=df.index)
        
        # Calculate trend strength
        if 'close' in df.columns:
            price_change = df['close'].pct_change(20).abs()
        else:
            price_change = pd.Series(0, index=df.index)
        
        # Classify regime
        regime = []
        for i in range(len(df)):
            v = vol.iloc[i] if i < len(vol) else 0
            t = price_change.iloc[i] if i < len(price_change) else 0
            
            if pd.isna(v) or pd.isna(t):
                regime.append('RANGE')
            elif v > self.vol_threshold:
                regime.append('VOLATILE')
            elif t > self.trend_threshold:
                regime.append('TREND')
            else:
                regime.append('RANGE')
        
        result['regime'] = regime
        return result
    
    def get_current_regime(self, df):
        """
        Get regime for the most recent data point.
        """
        result = self.detect(df)
        return result['regime'].iloc[-1] if len(result) > 0 else 'RANGE'
