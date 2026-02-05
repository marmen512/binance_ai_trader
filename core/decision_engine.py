import joblib
from core.feature_builder import FeatureBuilder

FEATURES = [
    "ret1","ret3","ret12",
    "vol10",
    "ema_diff",
    "rsi",
    "body_pct",
    "vol_spike"
]


class DecisionEngine:

    def __init__(self):
        self.model = joblib.load("models/btc_5m_model.pkl")
        self.fb = FeatureBuilder()

    def signal(self, df):

        df = self.fb.build(df)
        row = df.iloc[-1:][FEATURES]

        pred = self.model.predict(row)[0]
        prob = self.model.predict_proba(row)[0].max()

        if prob < 0.58:
            return "HOLD", prob

        return ("BUY" if pred==1 else "SELL"), prob
