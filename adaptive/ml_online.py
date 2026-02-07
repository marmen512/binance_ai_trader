import pickle
from pathlib import Path
from river import linear_model, optim, preprocessing, compose
from app.core.config import settings

class OnlineModel:
    def __init__(self):
        self.model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.LogisticRegression(optimizer=optim.SGD(0.01))
        )

    def predict_proba(self, x: dict) -> float:
        out = self.model.predict_proba_one(x)
        if isinstance(out, dict):
            return float(out.get(1, 0.0))
        try:
            return float(out)
        except Exception:
            return 0.0

    def learn(self, x: dict, y: int):
        self.model.learn_one(x, y)

    def save(self, path: str = None):
        p = Path(path or settings.ONLINE_MODEL_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            pickle.dump(self.model, f)

    @classmethod
    def load(cls, path: str = None):
        p = Path(path or settings.ONLINE_MODEL_PATH)
        inst = cls()
        if p.exists():
            try:
                with open(p, "rb") as f:
                    inst.model = pickle.load(f)
            except Exception:
                inst.save(path)
        else:
            inst.save(path)
        return inst
