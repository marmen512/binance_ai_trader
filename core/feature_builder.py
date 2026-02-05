import pandas as pd
import numpy as np


class FeatureBuilder:

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # returns
        df["ret_1"] = df["close"].pct_change()
        df["ret_5"] = df["close"].pct_change(5)

        # volatility
        df["volatility_10"] = df["ret_1"].rolling(10).std()

        # EMA
        df["ema_9"] = df["close"].ewm(span=9).mean()
        df["ema_21"] = df["close"].ewm(span=21).mean()
        df["ema_diff"] = df["ema_9"] - df["ema_21"]

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        df["rsi"] = 100 - (100 / (1 + rs))

        # candle features
        df["range"] = df["high"] - df["low"]
        df["body"] = df["close"] - df["open"]
        df["body_pct"] = df["body"] / (df["range"] + 1e-9)

        return df.dropna()
