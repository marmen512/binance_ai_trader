import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


FEATURES = [
    "ret_1", "ret_5",
    "volatility_10",
    "ema_diff",
    "rsi",
    "body_pct"
]


def train(csv_path="data/candles.csv"):
    df = pd.read_csv(csv_path)

    fb = FeatureBuilder()
    df = fb.build(df)
    df = build_target(df)

    X = df[FEATURES]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)
    print("TEST ACC:", acc)

    joblib.dump(model, "models/signal_model.pkl")


if __name__ == "__main__":
    train()
