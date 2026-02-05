"""
Модуль для запуску AI-керованого бектесту.
"""
import pandas as pd
import numpy as np
import sys
import os

# Додаємо корінь проекту до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AIBacktester:
    """
    Клас для проведення бектесту торгової стратегії на основі AI сигналів.
    
    Симулює торгівлю з урахуванням комісій та проковзування.
    """
    
    def __init__(self, initial_balance=10000.0, fee_rate=0.001, slippage=0.0005):
        """
        Ініціалізує бектестер.
        
        Args:
            initial_balance: початковий баланс
            fee_rate: ставка комісії (0.001 = 0.1%)
            slippage: проковзування (0.0005 = 0.05%)
        """
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        self.slippage = slippage
    
    def run(self, df: pd.DataFrame, signals: pd.Series) -> dict:
        """
        Виконує бектест.
        
        Args:
            df: DataFrame з даними (має містити 'close')
            signals: Series з сигналами ("BUY", "SELL", "HOLD")
            
        Returns:
            dict з результатами: equity_curve, trades, final_balance
        """
        balance = self.initial_balance
        position = 0.0  # Розмір позиції в базовій валюті
        equity_curve = []
        trades = []
        
        for i in range(len(df)):
            close_price = df['close'].iloc[i]
            signal = signals.iloc[i] if i < len(signals) else "HOLD"
            
            # Обчислюємо поточний капітал
            equity = balance + position * close_price
            equity_curve.append(equity)
            
            # Виконуємо торгову дію
            if signal == "BUY" and position == 0:
                # Відкриваємо довгу позицію
                entry_price = close_price * (1 + self.slippage)
                position = (balance * 0.95) / entry_price  # Використовуємо 95% балансу
                fee = position * entry_price * self.fee_rate
                balance = balance - position * entry_price - fee
                
                trades.append({
                    'index': i,
                    'type': 'BUY',
                    'price': entry_price,
                    'size': position,
                    'fee': fee
                })
                
            elif signal == "SELL" and position > 0:
                # Закриваємо позицію
                exit_price = close_price * (1 - self.slippage)
                proceeds = position * exit_price
                fee = proceeds * self.fee_rate
                balance = balance + proceeds - fee
                
                trades.append({
                    'index': i,
                    'type': 'SELL',
                    'price': exit_price,
                    'size': position,
                    'fee': fee
                })
                
                position = 0.0
        
        # Закриваємо позицію в кінці, якщо вона відкрита
        if position > 0:
            close_price = df['close'].iloc[-1]
            exit_price = close_price * (1 - self.slippage)
            proceeds = position * exit_price
            fee = proceeds * self.fee_rate
            balance = balance + proceeds - fee
            position = 0.0
        
        final_balance = balance
        
        return {
            'equity_curve': equity_curve,
            'trades': trades,
            'final_balance': final_balance
        }
