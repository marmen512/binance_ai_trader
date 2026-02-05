"""
MetaBacktester — бектестер для MetaEngine з усіма інтеграціями.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_detector import RegimeDetector
from core.probability_gate import pass_probability
from core.position_sizer import compute_position_size


class MetaBacktester:
    """Бектестер для мета-движка з усіма компонентами."""

    def __init__(self, meta_engine, initial_balance=10000, fee=0.0004, slippage=0.0002):
        """
        Ініціалізація MetaBacktester.

        Args:
            meta_engine: MetaEngine інстанція
            initial_balance (float): Початковий баланс
            fee (float): Комісія за трейд
            slippage (float): Проковзування
        """
        self.meta_engine = meta_engine
        self.initial_balance = initial_balance
        self.fee = fee
        self.slippage = slippage
        self.regime_detector = RegimeDetector()

    def run(self, df):
        """
        Запускає бектест на даних.

        Args:
            df (pd.DataFrame): DataFrame з OHLCV даними

        Returns:
            dict: Результати бектесту (balance, trades, equity)
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

            # Отримуємо сигнал від мета-движка
            signal, prob, used_names = self.meta_engine.signal(window)

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
                    'entry_idx': i,
                    'used_names': used_names
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

                # Оновлюємо мета-движок
                self.meta_engine.update(position['used_names'], pnl)

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

            # Оновлюємо мета-движок
            self.meta_engine.update(position['used_names'], pnl)

        return {
            'balance': balance,
            'trades': trades,
            'equity': equity
        }
