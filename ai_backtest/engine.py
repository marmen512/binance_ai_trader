"""
AI Backtesting Engine
Backtests AI trading strategies with regime detection, probability gate, and position sizing
"""
import pandas as pd
import numpy as np
from datetime import datetime


class AIBacktester:
    """
    AI Backtesting Engine
    Integrates regime detection, probability gate, and position sizing
    """
    
    def __init__(self, engine, regime_detector=None, probability_gate=None, 
                 position_sizer=None, initial_balance=10000, fee_rate=0.001):
        """
        Initialize AI backtester
        
        Args:
            engine: Trading engine (EnsembleEngine or RegimeModelEngine)
            regime_detector: RegimeDetector instance (optional)
            probability_gate: ProbabilityGate instance (optional)
            position_sizer: PositionSizer instance (optional)
            initial_balance: Starting balance
            fee_rate: Trading fee rate (default 0.001 = 0.1%)
        """
        self.engine = engine
        self.regime_detector = regime_detector
        self.probability_gate = probability_gate
        self.position_sizer = position_sizer
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        
        # State variables
        self.balance = initial_balance
        self.position = 0  # Current position in base currency
        self.position_value = 0  # Value of position in quote currency
        self.trades = []
        self.equity_curve = []
    
    def run(self, df):
        """
        Run backtest on dataframe
        
        Args:
            df: DataFrame with OHLCV data and features
            
        Returns:
            Dict with backtest results
        """
        self.balance = self.initial_balance
        self.position = 0
        self.position_value = 0
        self.trades = []
        self.equity_curve = []
        
        # Need at least 100 rows for features
        start_idx = 100
        
        for i in range(start_idx, len(df)):
            # Get data up to current point
            current_df = df.iloc[:i+1]
            current_price = df.iloc[i]['close']
            
            # Detect regime if detector available
            regime = None
            if self.regime_detector:
                regime = self.regime_detector.detect(current_df)
            
            # Generate signal
            signal, confidence = self.engine.signal(current_df)
            
            # Apply probability gate if available
            if self.probability_gate and regime:
                passed, signal = self.probability_gate.pass_probability(signal, confidence, regime)
            
            # Calculate position size if sizer available
            if self.position_sizer:
                position_size = self.position_sizer.compute_position_size(
                    current_df, self.balance, regime
                )
            else:
                position_size = self.balance * 0.1  # Default 10% of balance
            
            # Execute trades
            if signal == "BUY" and self.position == 0:
                # Open long position
                cost = position_size * (1 + self.fee_rate)
                if cost <= self.balance:
                    self.position = position_size / current_price
                    self.position_value = position_size
                    self.balance -= cost
                    
                    self.trades.append({
                        'timestamp': df.iloc[i]['timestamp'] if 'timestamp' in df.columns else i,
                        'type': 'BUY',
                        'price': current_price,
                        'size': self.position,
                        'value': position_size,
                        'balance': self.balance,
                        'regime': regime,
                        'confidence': confidence
                    })
            
            elif signal == "SELL" and self.position > 0:
                # Close long position
                proceeds = self.position * current_price * (1 - self.fee_rate)
                self.balance += proceeds
                
                self.trades.append({
                    'timestamp': df.iloc[i]['timestamp'] if 'timestamp' in df.columns else i,
                    'type': 'SELL',
                    'price': current_price,
                    'size': self.position,
                    'value': proceeds,
                    'balance': self.balance,
                    'regime': regime,
                    'confidence': confidence
                })
                
                self.position = 0
                self.position_value = 0
            
            # Calculate total equity
            if self.position > 0:
                equity = self.balance + (self.position * current_price)
            else:
                equity = self.balance
            
            self.equity_curve.append({
                'timestamp': df.iloc[i]['timestamp'] if 'timestamp' in df.columns else i,
                'equity': equity,
                'balance': self.balance,
                'position_value': self.position * current_price if self.position > 0 else 0
            })
        
        # Close any open position at end
        if self.position > 0:
            final_price = df.iloc[-1]['close']
            proceeds = self.position * final_price * (1 - self.fee_rate)
            self.balance += proceeds
            
            self.trades.append({
                'timestamp': df.iloc[-1]['timestamp'] if 'timestamp' in df.columns else len(df)-1,
                'type': 'SELL',
                'price': final_price,
                'size': self.position,
                'value': proceeds,
                'balance': self.balance,
                'regime': regime,
                'confidence': confidence
            })
            
            self.position = 0
        
        # Calculate final equity
        final_equity = self.balance
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'final_equity': final_equity,
            'total_return': (final_equity / self.initial_balance - 1) * 100,
            'num_trades': len(self.trades),
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
