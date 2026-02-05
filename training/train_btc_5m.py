import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
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

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=7,
    n_jobs=-1
)

model.fit(Xtr, ytr)

print("ACC:", model.score(Xte, yte))

joblib.dump(model, "models/btc_5m_model.pkl")
print("model saved")
