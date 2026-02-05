import pandas as pd
import matplotlib.pyplot as plt

# Load equity curve
equity_df = pd.read_csv("equity_curve.csv")

# Plot
plt.figure(figsize=(12, 6))
plt.plot(equity_df["equity"], linewidth=2)
plt.title("AI Backtest Equity Curve", fontsize=16)
plt.xlabel("Time Period", fontsize=12)
plt.ylabel("Equity ($)", fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("equity_curve.png", dpi=300)
print("Equity curve plot saved to equity_curve.png")
plt.show()
