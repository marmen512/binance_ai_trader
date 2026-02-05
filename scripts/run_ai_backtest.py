import pandas as pd

from core.decision_engine import DecisionEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics


df = pd.read_csv("data/btcusdt_5m.csv")

engine = DecisionEngine()
bt = AIBacktester(engine)

result = bt.run(df)

metrics = compute_metrics(result["trades"]) 

print("\n=== AI BACKTEST ===")
print("Final balance:", round(result["final_balance"], 2))
print(metrics)
