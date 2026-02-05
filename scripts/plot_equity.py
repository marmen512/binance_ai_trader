"""
Plot Equity Curve
Visualize backtest equity curve using matplotlib
"""
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from core.ensemble_engine import EnsembleEngine
from core.regime_detector import RegimeDetector
from core.probability_gate import ProbabilityGate
from core.position_sizer import PositionSizer
from ai_backtest.engine import AIBacktester


def plot_equity():
    """Plot equity curve from backtest"""
    
    print("Loading data...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Building features...")
    builder = FeatureBuilder()
    df = builder.build(df)
    df = df.dropna()
    
    print("Running backtest...")
    engine = EnsembleEngine()
    regime_detector = RegimeDetector()
    probability_gate = ProbabilityGate()
    position_sizer = PositionSizer()
    
    backtester = AIBacktester(
        engine=engine,
        regime_detector=regime_detector,
        probability_gate=probability_gate,
        position_sizer=position_sizer,
        initial_balance=10000
    )
    
    results = backtester.run(df)
    
    print("Plotting equity curve...")
    equity_df = pd.DataFrame(results['equity_curve'])
    
    plt.figure(figsize=(12, 6))
    plt.plot(equity_df.index, equity_df['equity'], label='Total Equity', linewidth=2)
    plt.plot(equity_df.index, equity_df['balance'], label='Cash Balance', alpha=0.7)
    
    plt.axhline(y=results['initial_balance'], color='gray', linestyle='--', 
                label='Initial Balance', alpha=0.5)
    
    plt.title('AI Trading Backtest - Equity Curve')
    plt.xlabel('Time Step')
    plt.ylabel('Equity ($)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = 'equity_curve.png'
    plt.savefig(output_path, dpi=150)
    print(f"Saved: {output_path}")
    
    plt.show()


if __name__ == '__main__':
    plot_equity()
