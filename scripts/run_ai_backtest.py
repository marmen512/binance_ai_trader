import pandas as pd
from core.ensemble_engine import EnsembleEngine

# Load historical data
df = pd.read_csv("data/btcusdt_5m.csv")

# Initialize ensemble engine
engine = EnsembleEngine()

# Backtest simulation
positions = []
equity = [10000.0]  # Starting with $10,000

for i in range(100, len(df)):
    # Get historical window
    window = df.iloc[:i+1].copy()
    
    # Get signal from ensemble
    signal, confidence = engine.signal(window)
    
    # Simple position tracking
    positions.append({
        "index": i,
        "signal": signal,
        "confidence": confidence,
        "price": df.iloc[i]["close"]
    })
    
    # Update equity (simplified)
    if i > 0 and len(positions) > 1:
        prev_signal = positions[-2]["signal"]
        curr_price = df.iloc[i]["close"]
        prev_price = df.iloc[i-1]["close"]
        
        if prev_signal == "BUY":
            equity.append(equity[-1] * (1 + (curr_price - prev_price) / prev_price))
        elif prev_signal == "SELL":
            equity.append(equity[-1] * (1 - (curr_price - prev_price) / prev_price))
        else:
            equity.append(equity[-1])

# Results
print(f"Final Equity: ${equity[-1]:.2f}")
print(f"Return: {(equity[-1] / equity[0] - 1) * 100:.2f}%")
print(f"Total Trades: {len(positions)}")

# Save results
results_df = pd.DataFrame(positions)
results_df.to_csv("backtest_results.csv", index=False)
print("Backtest results saved to backtest_results.csv")

# Save equity curve
equity_df = pd.DataFrame({"equity": equity})
equity_df.to_csv("equity_curve.csv", index=False)
print("Equity curve saved to equity_curve.csv")
