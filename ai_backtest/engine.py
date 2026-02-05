"""
AI Backtester - Інтеграція всіх компонентів для бектестування.
"""
import pandas as pd
import numpy as np
import sys
import os

# Додаємо кореневу директорію до шляху
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_detector import RegimeDetector
from core.probability_gate import pass_probability
from core.position_sizer import compute_position_size


class AIBacktester:
    """
    Бектестер AI-стратегії з інтеграцією всіх компонентів.
    """
    
    def __init__(self, engine, initial_balance=10000, fee=0.0004, slippage=0.0002):
        """
        Ініціалізація бектестера.
        
        Args:
            engine: Ансамблевий двигун з методом signal()
            initial_balance: Початковий баланс
            fee: Комісія за угоду (0.0004 = 0.04%)
            slippage: Проковзування (0.0002 = 0.02%)
        """
        self.engine = engine
        self.initial_balance = initial_balance
        self.fee = fee
        self.slippage = slippage
        
        self.regime_detector = RegimeDetector()
    
    def run(self, df: pd.DataFrame, feature_cols: list) -> dict:
        """
        Запускає бектест на історичних даних.
        
        Args:
            df: DataFrame з OHLCV даними та ознаками
            feature_cols: Список назв колонок-ознак
            
        Returns:
            Словник з результатами: equity_curve, trades, final_balance
        """
        balance = self.initial_balance
        position = None  # None або {'type': 'LONG', 'size': ..., 'entry_price': ...}
        
        equity_curve = []
        trades = []
        
        print(f"Запуск бектесту на {len(df)} свічках...")
        
        for i in range(50, len(df)):  # Пропускаємо перші 50 для розрахунку режиму
            row = df.iloc[i]
            price = row['close']
            
            # Поточні ознаки
            features = {col: row[col] for col in feature_cols}
            
            # Визначення режиму
            regime = self.regime_detector.detect(df.iloc[:i+1])
            
            # Отримання сигналу
            signal, prob = self.engine.signal(features)
            
            # Перевірка ворот ймовірності
            if not pass_probability(prob, regime):
                signal = 'HOLD'
            
            # Виконання торгівлі
            if position is None:
                # Немає позиції - можемо відкрити
                if signal == 'BUY':
                    # Обчислення волатильності
                    volatility = features.get('vol10', 0.01)
                    position_size = compute_position_size(balance, volatility)
                    
                    # Відкриття позиції
                    entry_price = price * (1 + self.slippage)
                    cost = position_size * entry_price
                    fee_cost = cost * self.fee
                    
                    if cost + fee_cost <= balance:
                        balance -= (cost + fee_cost)
                        position = {
                            'type': 'LONG',
                            'size': position_size,
                            'entry_price': entry_price,
                            'entry_time': row.get('timestamp', i)
                        }
            else:
                # Є позиція - можемо закрити
                if signal == 'SELL' or signal == 'HOLD':
                    # Закриття позиції
                    exit_price = price * (1 - self.slippage)
                    revenue = position['size'] * exit_price
                    fee_cost = revenue * self.fee
                    
                    balance += (revenue - fee_cost)
                    
                    # Запис угоди
                    pnl = (exit_price - position['entry_price']) * position['size'] - (position['size'] * position['entry_price'] * self.fee + revenue * self.fee)
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row.get('timestamp', i),
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'return': (exit_price - position['entry_price']) / position['entry_price']
                    })
                    
                    position = None
            
            # Поточна вартість портфеля
            if position:
                portfolio_value = balance + position['size'] * price
            else:
                portfolio_value = balance
            
            equity_curve.append({
                'timestamp': row.get('timestamp', i),
                'balance': portfolio_value
            })
        
        # Закриття позиції в кінці, якщо вона відкрита
        if position:
            final_price = df.iloc[-1]['close']
            exit_price = final_price * (1 - self.slippage)
            revenue = position['size'] * exit_price
            fee_cost = revenue * self.fee
            balance += (revenue - fee_cost)
            
            pnl = (exit_price - position['entry_price']) * position['size'] - (position['size'] * position['entry_price'] * self.fee + revenue * self.fee)
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': df.iloc[-1].get('timestamp', len(df)-1),
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'size': position['size'],
                'pnl': pnl,
                'return': (exit_price - position['entry_price']) / position['entry_price']
            })
        
        return {
            'equity_curve': equity_curve,
            'trades': trades,
            'final_balance': balance
        }
