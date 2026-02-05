"""
AIBacktester — інтеграція всіх компонентів для бектестингу AI моделей.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_detector import RegimeDetector
from core.probability_gate import pass_probability
from core.position_sizer import compute_position_size
from core.drift_detector import DriftDetector


class AIBacktester:
    """Бектестер для AI торгових стратегій з інтеграцією всіх компонентів."""

    def __init__(self, engine, initial_balance=10000, fee=0.0004, slippage=0.0002):
        """
        Ініціалізація AIBacktester.

        Args:
            engine: Торговий движок (EnsembleEngine, RegimeModelEngine, тощо)
            initial_balance (float): Початковий баланс
            fee (float): Комісія за трейд (0.0004 = 0.04%)
            slippage (float): Проковзування (0.0002 = 0.02%)
        """
        self.engine = engine
        self.initial_balance = initial_balance
        self.fee = fee
        self.slippage = slippage
        self.regime_detector = RegimeDetector()
        self.drift = DriftDetector()

    def run(self, df):
        """
        Запускає бектест на даних.

        Args:
            df (pd.DataFrame): DataFrame з OHLCV даними

        Returns:
            dict: Результати бектесту (equity_curve, trades, final_balance)
        """
        balance = self.initial_balance
        position = None
        trades = []
        equity = [balance]

        for i in range(100, len(df)):
            window = df.iloc[max(0, i-100):i]
            current_row = df.iloc[i]

            # Визначаємо режим
            regime = self.regime_detector.detect(window)

            # Отримуємо сигнал від движка
            signal, prob = self.engine.signal(window)

            # Перевіряємо probability gate
            if not pass_probability(prob, regime):
                signal = 'HOLD'

            # Обчислюємо волатильність для position sizing
            vol = window['close'].rolling(20).std().iloc[-1] if len(window) >= 20 else 0.01

            # Виконуємо торгові дії
            if position is None and signal == 'BUY':
                # Відкриваємо LONG
                position_size = compute_position_size(balance, vol)
                entry_price = current_row['close'] * (1 + self.slippage)
                position = {
                    'type': 'LONG',
                    'entry_price': entry_price,
                    'size': position_size,
                    'entry_idx': i
                }
                balance -= position_size * entry_price * self.fee

            elif position is not None and position['type'] == 'LONG' and signal == 'SELL':
                # Закриваємо LONG
                exit_price = current_row['close'] * (1 - self.slippage)
                pnl = position['size'] * (exit_price - position['entry_price'])
                pnl -= position['size'] * exit_price * self.fee
                balance += position['size'] * exit_price
                balance += pnl

                trades.append({
                    'entry_idx': position['entry_idx'],
                    'exit_idx': i,
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': 'LONG'
                })

                # Перевіряємо дрифт
                self.drift.add_trade(pnl)
                if self.drift.drifted():
                    print(f"⚠️  DRIFT DETECTED at index {i} — retrain needed")

                position = None

            equity.append(balance)

        # Якщо є відкрита позиція, закриваємо її
        if position is not None:
            exit_price = df.iloc[-1]['close'] * (1 - self.slippage)
            pnl = position['size'] * (exit_price - position['entry_price'])
            pnl -= position['size'] * exit_price * self.fee
            balance += position['size'] * exit_price
            balance += pnl

            trades.append({
                'entry_idx': position['entry_idx'],
                'exit_idx': len(df) - 1,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'type': 'LONG'
            })

        return {
            'equity_curve': equity,
            'trades': trades,
            'final_balance': balance
        }
