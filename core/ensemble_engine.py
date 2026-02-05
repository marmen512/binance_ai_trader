import joblib
import numpy as np

from core.feature_builder import FeatureBuilder


FEATURES = [
    "ret1","ret3","ret12",
    "vol10",
    "ema_diff",
    "rsi",
    "body_pct",
    "vol_spike"
]


class EnsembleEngine:

    def __init__(self):

        self.models = [
            joblib.load("models/rf_btc_5m.pkl"),
            joblib.load("models/gb_btc_5m.pkl"),
            joblib.load("models/et_btc_5m.pkl")
        ]

        self.weights = [0.4, 0.3, 0.3]
        self.fb = FeatureBuilder()

    def signal(self, df):

        df = self.fb.build(df)
        row = df.iloc[-1:][FEATURES]

        probs = []
        preds = []

        for m in self.models:
            p = m.predict_proba(row)[0]
            probs.append(p)
            preds.append(m.predict(row)[0])

        probs = np.array(probs)

        weighted = np.average(probs, axis=0, weights=self.weights)

        cls = np.argmax(weighted)
        conf = weighted[cls]

        if conf < 0.6:
            return "HOLD", conf

        if cls == 2:
            return "BUY", conf
        if cls == 0:
            return "SELL", conf

        return "HOLD", conf
