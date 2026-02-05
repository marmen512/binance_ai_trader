"""
Модуль AI-бектестингу торгової стратегії.

Цей модуль реалізує симуляцію торгівлі з урахуванням комісій,
проковзування та складних умов входу/виходу.
"""

import pandas as pd
import numpy as np
from core.decision_engine import DecisionEngine
from core.risk_filter import risk_filter


class AIBacktester:
    """
    Клас для бектестингу торгової стратегії на історичних даних.
    
    Симулює торгівлю з урахуванням:
    - Комісій біржі
    - Проковзування (slippage)
    - Управління позицією
    - Генерації сигналів через DecisionEngine
    """
    
    def __init__(self, decision_engine, initial_capital=10000, 
                 fee_rate=0.001, slippage=0.0005):
        """
        Ініціалізує бектестер.
        
        Параметри:
            decision_engine (DecisionEngine): механізм генерації сигналів
            initial_capital (float): початковий капітал (за замовчуванням 10000 USDT)
            fee_rate (float): ставка комісії біржі (за замовчуванням 0.001 = 0.1%)
            slippage (float): проковзування при виконанні ордерів (за замовчуванням 0.0005 = 0.05%)
        """
        self.engine = decision_engine
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        
    def run(self, df, window_size=100, use_risk_filter=True):
        """
        Запускає бектест на історичних даних.
        
        Параметри:
            df (pd.DataFrame): DataFrame з OHLCV даними
            window_size (int): розмір вікна історії для генерації сигналів
            use_risk_filter (bool): чи використовувати ризик-фільтр
            
        Повертає:
            tuple: (equity_curve, trades)
                equity_curve (pd.DataFrame): крива капіталу з timestamp та equity
                trades (list): список виконаних угод
        """
        print("=" * 60)
        print("ЗАПУСК AI БЕКТЕСТУ")
        print("=" * 60)
        print(f"Початковий капітал: {self.initial_capital} USDT")
        print(f"Комісія: {self.fee_rate*100}%")
        print(f"Проковзування: {self.slippage*100}%")
        print(f"Ризик-фільтр: {'Увімкнено' if use_risk_filter else 'Вимкнено'}")
        print(f"Розмір даних: {len(df)} свічок")
        print("=" * 60)
        
        # Ініціалізація
        capital = self.initial_capital
        position = 0  # 0 = немає позиції, 1 = лонг, -1 = шорт
        entry_price = 0
        trades = []
        equity_curve = []
        
        # Проходимо по даних з вікном
        for i in range(window_size, len(df)):
            # Беремо вікно даних для генерації сигналу
            window_df = df.iloc[i-window_size:i].copy()
            current_price = df.iloc[i]['close']
            timestamp = df.iloc[i]['timestamp']
            
            # Генеруємо сигнал
            signal, prob = self.engine.signal(window_df)
            
            # Застосовуємо ризик-фільтр якщо потрібно
            if use_risk_filter:
                recent_returns = window_df['close'].pct_change().tail(10)
                volatility = recent_returns.std()
                signal = risk_filter(signal, prob, volatility)
            
            # Логіка торгівлі
            if position == 0:  # Немає позиції
                if signal == 'BUY':
                    # Відкриваємо лонг
                    entry_price = current_price * (1 + self.slippage)
                    position = 1
                    
                    # Комісія при вході
                    capital *= (1 - self.fee_rate)
                    
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'LONG_ENTRY',
                        'price': entry_price,
                        'signal_prob': prob,
                        'capital': capital
                    })
                    
                elif signal == 'SELL':
                    # Відкриваємо шорт
                    entry_price = current_price * (1 - self.slippage)
                    position = -1
                    
                    # Комісія при вході
                    capital *= (1 - self.fee_rate)
                    
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'SHORT_ENTRY',
                        'price': entry_price,
                        'signal_prob': prob,
                        'capital': capital
                    })
                    
            elif position == 1:  # У лонг позиції
                if signal == 'SELL' or signal == 'HOLD':
                    # Закриваємо лонг
                    exit_price = current_price * (1 - self.slippage)
                    pnl_pct = (exit_price - entry_price) / entry_price
                    
                    # Оновлюємо капітал з урахуванням PnL та комісії
                    capital *= (1 + pnl_pct)
                    capital *= (1 - self.fee_rate)
                    
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'LONG_EXIT',
                        'price': exit_price,
                        'pnl_pct': pnl_pct,
                        'capital': capital
                    })
                    
                    position = 0
                    
            elif position == -1:  # У шорт позиції
                if signal == 'BUY' or signal == 'HOLD':
                    # Закриваємо шорт
                    exit_price = current_price * (1 + self.slippage)
                    pnl_pct = (entry_price - exit_price) / entry_price
                    
                    # Оновлюємо капітал з урахуванням PnL та комісії
                    capital *= (1 + pnl_pct)
                    capital *= (1 - self.fee_rate)
                    
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'SHORT_EXIT',
                        'price': exit_price,
                        'pnl_pct': pnl_pct,
                        'capital': capital
                    })
                    
                    position = 0
            
            # Зберігаємо поточний капітал
            equity_curve.append({
                'timestamp': timestamp,
                'equity': capital
            })
        
        # Закриваємо позицію в кінці якщо залишилась відкритою
        if position != 0:
            final_price = df.iloc[-1]['close']
            if position == 1:
                exit_price = final_price * (1 - self.slippage)
                pnl_pct = (exit_price - entry_price) / entry_price
            else:
                exit_price = final_price * (1 + self.slippage)
                pnl_pct = (entry_price - exit_price) / entry_price
            
            capital *= (1 + pnl_pct)
            capital *= (1 - self.fee_rate)
            
            trades.append({
                'timestamp': df.iloc[-1]['timestamp'],
                'action': 'FORCE_CLOSE',
                'price': exit_price,
                'pnl_pct': pnl_pct,
                'capital': capital
            })
        
        # Конвертуємо у DataFrame
        equity_df = pd.DataFrame(equity_curve)
        
        print(f"\nБектест завершено!")
        print(f"Кількість угод: {len(trades)}")
        print(f"Фінальний капітал: {capital:.2f} USDT")
        print(f"Прибуток/Збиток: {capital - self.initial_capital:.2f} USDT ({(capital/self.initial_capital - 1)*100:.2f}%)")
        
        return equity_df, trades
