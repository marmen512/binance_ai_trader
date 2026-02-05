"""
Feature builder for generating ML features from OHLCV data.
"""
import pandas as pd
import numpy as np


class FeatureBuilder:
    """
    Builds technical indicator features from OHLCV data.
    """
    
    def __init__(self):
        pass
    
    def build(self, df):
        """
        Build features from OHLCV dataframe.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
            
        Returns:
            Feature array ready for model prediction
        """
        features = []
        
        # Price-based features
        if 'close' in df.columns:
            close = df['close'].values
            
            # Returns
            if len(close) > 1:
                returns = np.diff(close) / close[:-1]
                features.append(returns[-1] if len(returns) > 0 else 0)
            else:
                features.append(0)
            
            # Moving averages
            if len(close) >= 20:
                sma_20 = np.mean(close[-20:])
                features.append((close[-1] - sma_20) / sma_20)
            else:
                features.append(0)
            
            if len(close) >= 50:
                sma_50 = np.mean(close[-50:])
                features.append((close[-1] - sma_50) / sma_50)
            else:
                features.append(0)
        else:
            features.extend([0, 0, 0])
        
        # Volume features
        if 'volume' in df.columns and len(df) >= 20:
            volume = df['volume'].values
            vol_ma = np.mean(volume[-20:])
            if vol_ma > 0:
                features.append(volume[-1] / vol_ma)
            else:
                features.append(1)
        else:
            features.append(1)
        
        # Volatility
        if 'close' in df.columns and len(df) >= 20:
            returns = df['close'].pct_change().values[-20:]
            volatility = np.std(returns[~np.isnan(returns)])
            features.append(volatility)
        else:
            features.append(0)
        
        return np.array(features).reshape(1, -1)
