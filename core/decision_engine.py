import joblib
import pandas as pd

from core.feature_builder import FeatureBuilder


FEATURES = [
    "ret_1", "ret_5",
    "volatility_10",
    "ema_diff",
    "rsi",
    "body_pct"
]


class DecisionEngine:

    def __init__(self, model_path="models/signal_model.pkl"):
        self.model = joblib.load(model_path)
        self.fb = FeatureBuilder()

    def predict(self, df: pd.DataFrame):

        df = self.fb.build(df)
        row = df.iloc[-1:][FEATURES]

        pred = self.model.predict(row)[0]
        prob = self.model.predict_proba(row)[0].max()

        if prob < 0.55:
            return "HOLD", prob

        if pred == 1:
            return "BUY", prob
        if pred == -1:
            return "SELL", prob

        return "HOLD", prob
