import pandas as pd
import joblib

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier
)

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


FEATURES = [
    "ret1","ret3","ret12",
    "vol10",
    "ema_diff",
    "rsi",
    "body_pct",
    "vol_spike"
]

df = pd.read_csv("data/btcusdt_5m.csv")

fb = FeatureBuilder()
df = fb.build(df)
df = build_target(df)

X = df[FEATURES]
y = df["target"]

split = int(len(df)*0.8)

Xtr, Xte = X[:split], X[split:]
ytr, yte = y[:split], y[split:]


models = {
    "rf": RandomForestClassifier(
        n_estimators=300,
        max_depth=7,
        n_jobs=-1
    ),
    "gb": GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4
    ),
    "et": ExtraTreesClassifier(
        n_estimators=400,
        max_depth=8,
        n_jobs=-1
    )
}

for name, model in models.items():
    model.fit(Xtr, ytr)
    acc = model.score(Xte, yte)
    print(name, "ACC:", acc)
    joblib.dump(model, f"models/{name}_btc_5m.pkl")

print("ensemble models saved")
