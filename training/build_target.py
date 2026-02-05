import pandas as pd
import numpy as np


def build_target(df: pd.DataFrame, horizon=5, threshold=0.004):
    future = df["close"].shift(-horizon)
    ret = (future - df["close"]) / df["close"]

    target = np.zeros(len(df))
    target[ret > threshold] = 1
    target[ret < -threshold] = -1

    df["target"] = target
    return df.dropna()
