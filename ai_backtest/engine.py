"""
AI Backtester with drift detection integration.
"""
import pandas as pd
import numpy as np
from core.drift_detector import DriftDetector
from core.regime_detector import RegimeDetector
from core.probability_gate import ProbabilityGate
from core.position_sizer import PositionSizer


class AIBacktester:
    """
    Backtester that integrates drift detection, regime detection, probability gate,
    and position sizing with ML-based trading engine.
    """
    
    def __init__(self, data, engine, initial_balance=10000, fee_rate=0.001):
        """
        Args:
            data: DataFrame with OHLCV data
            engine: Trading engine (ensemble or adaptive)
            initial_balance: Starting balance
            fee_rate: Trading fee rate (0.001 = 0.1%)
        """
        self.data = data.copy()
        self.engine = engine
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.fee_rate = fee_rate
        
        # Position tracking
        self.position = None  # 'LONG' or None
        self.entry_price = None
        self.position_size = 0
        
        # Components
        self.drift = DriftDetector()
        self.regime_detector = RegimeDetector()
        self.probability_gate = ProbabilityGate(min_probability=0.6)
        self.position_sizer = PositionSizer()
        
        # Tracking
        self.trades = []
        self.equity_curve = []
        
    def run(self):
        """
        Run backtest on data.
        """
        print(f"[AIBacktester] Starting backtest on {len(self.data)} bars")
        
        for i in range(100, len(self.data)):  # Start after warmup period
            # Get historical data up to current point
            hist_data = self.data.iloc[:i+1].copy()
            
            # Get current price
            current_price = self.data.iloc[i]['close']
            
            # Get signal from engine
            try:
                signal, probability = self.engine.signal(hist_data)
            except Exception as e:
                signal, probability = 'HOLD', 0.5
            
            # Apply probability gate
            signal = self.probability_gate.filter(signal, probability)
            
            # Execute trading logic
            if self.position is None:
                # No position - check for entry
                if signal == 'BUY':
                    # Calculate position size
                    size = self.position_sizer.calculate_size(probability, self.balance)
                    
                    if size > 0:
                        # Enter long position
                        cost = current_price * (1 + self.fee_rate)
                        shares = size / cost
                        
                        self.position = 'LONG'
                        self.entry_price = current_price
                        self.position_size = shares
                        self.balance -= size
                        
            else:
                # Have position - check for exit
                if signal == 'SELL' or signal == 'HOLD':
                    # Close position
                    proceeds = self.position_size * current_price * (1 - self.fee_rate)
                    pnl = proceeds - (self.position_size * self.entry_price)
                    
                    self.balance += proceeds
                    
                    # Record trade
                    self.trades.append({
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'return_pct': (current_price - self.entry_price) / self.entry_price * 100
                    })
                    
                    # Add trade to drift detector
                    self.drift.add_trade(pnl)
                    
                    # Check for drift
                    if self.drift.drifted():
                        print(f"[AIBacktester] DRIFT DETECTED at bar {i}!")
                        print(f"[AIBacktester] Drift stats: {self.drift.get_stats()}")
                    
                    # Reset position
                    self.position = None
                    self.entry_price = None
                    self.position_size = 0
            
            # Track equity
            current_equity = self.balance
            if self.position is not None:
                current_equity += self.position_size * current_price
            
            self.equity_curve.append({
                'bar': i,
                'equity': current_equity,
                'balance': self.balance
            })
        
        # Close any open position at end
        if self.position is not None:
            final_price = self.data.iloc[-1]['close']
            proceeds = self.position_size * final_price * (1 - self.fee_rate)
            pnl = proceeds - (self.position_size * self.entry_price)
            self.balance += proceeds
            
            self.trades.append({
                'entry_price': self.entry_price,
                'exit_price': final_price,
                'pnl': pnl,
                'return_pct': (final_price - self.entry_price) / self.entry_price * 100
            })
            
            self.drift.add_trade(pnl)
        
        print(f"[AIBacktester] Backtest complete")
        print(f"[AIBacktester] Trades: {len(self.trades)}")
        print(f"[AIBacktester] Final balance: ${self.balance:.2f}")
        
        return self.get_metrics()
    
    def get_balance(self):
        """Get final balance."""
        return self.balance
    
    def get_metrics(self):
        """Calculate backtest metrics."""
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] <= 0]
        
        return {
            'total_trades': len(self.trades),
            'total_return_pct': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'win_rate': len(wins) / len(self.trades) if len(self.trades) > 0 else 0,
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0
        }
