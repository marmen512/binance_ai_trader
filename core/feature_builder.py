import pandas as pd


class FeatureBuilder:
    """Build features for ML models"""
    
    def build(self, df):
        """Build technical features on OHLCV data"""
        df = df.copy()
        
        # Returns
        df["ret1"] = df["close"].pct_change(1)
        df["ret3"] = df["close"].pct_change(3)
        df["ret12"] = df["close"].pct_change(12)
        
        # Volatility
        df["vol10"] = df["close"].pct_change().rolling(10).std()
        
        # EMA difference
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["ema_diff"] = (ema12 - ema26) / df["close"]
        
        # RSI
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))
        
        # Body percentage
        df["body_pct"] = (df["close"] - df["open"]).abs() / (df["high"] - df["low"] + 1e-10)
        
        # Volume spike
        df["vol_spike"] = df["volume"] / (df["volume"].rolling(20).mean() + 1e-10)
        
        # Drop NaN rows
        df = df.dropna()
        
        return df
