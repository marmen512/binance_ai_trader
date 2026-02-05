import pandas as pd
from core.decision_engine import DecisionEngine

df = pd.read_csv("data/btcusdt_5m.csv")

engine = DecisionEngine()

sig, prob = engine.signal(df)

print("SIGNAL:", sig, "CONF:", prob)
