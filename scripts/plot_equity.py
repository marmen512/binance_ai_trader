import pandas as pd
import matplotlib.pyplot as plt

from core.decision_engine import DecisionEngine
from ai_backtest.engine import AIBacktester


df = pd.read_csv("data/btcusdt_5m.csv")

engine = DecisionEngine()
bt = AIBacktester(engine)

res = bt.run(df)

plt.plot(res["equity"])
plt.title("AI Equity Curve")
plt.show()
