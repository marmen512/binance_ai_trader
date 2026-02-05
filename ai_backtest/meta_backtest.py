"""
MetaBacktester - бектестинг з мета-двигуном.
"""
import pandas as pd
from core.regime_detector import RegimeDetector
from core.probability_gate import pass_probability
from core.position_sizer import compute_position_size


class MetaBacktester:
    """
    Бектестер для мета-стратегії з кількома двигунами.
    """
    
    def __init__(self, meta_engine, initial_balance=10000.0):
        self.meta_engine = meta_engine
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = None
        self.trades = []
        self.equity = [initial_balance]
        
        self.fee = 0.0004
        self.slippage = 0.0002
        
        self.regime_detector = RegimeDetector()
    
    def run(self, df: pd.DataFrame, window_size: int = 100):
        """
        Запускає мета-бектест.
        """
        for i in range(window_size, len(df)):
            window = df.iloc[:i+1].copy()
            current_price = window['close'].iloc[-1]
            
            # Визначаємо режим
            regime = self.regime_detector.detect(window)
            
            # Генеруємо мета-сигнал
            signal, prob = self.meta_engine.signal(window)
            
            # Перевіряємо probability gate
            if not pass_probability(prob, regime):
                signal = 'HOLD'
            
            # Обчислюємо волатильність
            returns = window['close'].pct_change()
            vol = returns.rolling(window=20).std().iloc[-1]
            
            # Логіка торгівлі
            if self.position is None:
                if signal == 'BUY':
                    size = compute_position_size(self.balance, vol)
                    entry_price = current_price * (1 + self.slippage)
                    cost = size + size * self.fee
                    
                    if cost <= self.balance:
                        self.position = {
                            'side': 'LONG',
                            'size': size,
                            'entry_price': entry_price,
                            'entry_idx': i,
                            'signal_source': 'meta'
                        }
                        self.balance -= cost
                
                elif signal == 'SELL':
                    size = compute_position_size(self.balance, vol)
                    entry_price = current_price * (1 - self.slippage)
                    cost = size * self.fee
                    
                    if cost <= self.balance:
                        self.position = {
                            'side': 'SHORT',
                            'size': size,
                            'entry_price': entry_price,
                            'entry_idx': i,
                            'signal_source': 'meta'
                        }
                        self.balance -= cost
            
            else:
                close_position = False
                
                if self.position['side'] == 'LONG' and signal in ['SELL', 'HOLD']:
                    close_position = True
                elif self.position['side'] == 'SHORT' and signal in ['BUY', 'HOLD']:
                    close_position = True
                
                if close_position:
                    exit_price = current_price * (1 - self.slippage if self.position['side'] == 'LONG' else 1 + self.slippage)
                    
                    if self.position['side'] == 'LONG':
                        pnl = (exit_price - self.position['entry_price']) / self.position['entry_price'] * self.position['size']
                    else:
                        pnl = (self.position['entry_price'] - exit_price) / self.position['entry_price'] * self.position['size']
                    
                    pnl -= self.position['size'] * self.fee
                    
                    self.balance += self.position['size'] + pnl
                    
                    self.trades.append({
                        'entry_idx': self.position['entry_idx'],
                        'exit_idx': i,
                        'side': self.position['side'],
                        'entry_price': self.position['entry_price'],
                        'exit_price': exit_price,
                        'size': self.position['size'],
                        'pnl': pnl,
                        'regime': regime
                    })
                    
                    # Оновлюємо трекер (використовуємо best engine для атрибуції)
                    best_engine = self.meta_engine.tracker.get_best_engine()
                    self.meta_engine.update_tracker(best_engine, pnl)
                    
                    self.position = None
            
            # Оновлюємо equity
            total_equity = self.balance
            if self.position is not None:
                if self.position['side'] == 'LONG':
                    unrealized_pnl = (current_price - self.position['entry_price']) / self.position['entry_price'] * self.position['size']
                else:
                    unrealized_pnl = (self.position['entry_price'] - current_price) / self.position['entry_price'] * self.position['size']
                total_equity += self.position['size'] + unrealized_pnl
            
            self.equity.append(total_equity)
        
        # Закриваємо відкриту позицію
        if self.position is not None:
            exit_price = df['close'].iloc[-1]
            if self.position['side'] == 'LONG':
                pnl = (exit_price - self.position['entry_price']) / self.position['entry_price'] * self.position['size']
            else:
                pnl = (self.position['entry_price'] - exit_price) / self.position['entry_price'] * self.position['size']
            
            pnl -= self.position['size'] * self.fee
            self.balance += self.position['size'] + pnl
            self.position = None
        
        return self.balance, self.trades, self.equity
