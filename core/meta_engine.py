"""
MetaEngine - мета-двигун, що комбінує кілька двигунів.
"""
import numpy as np
from core.meta_tracker import EngineTracker


class MetaEngine:
    """
    Комбінує сигнали від декількох двигунів використовуючи динамічні ваги.
    """
    
    def __init__(self, engines: dict):
        """
        Args:
            engines: словник {engine_name: engine_instance}
        """
        self.engines = engines
        self.engine_names = list(engines.keys())
        self.tracker = EngineTracker(self.engine_names)
    
    def signal(self, df):
        """
        Генерує мета-сигнал на основі зважених сигналів від усіх двигунів.
        
        Args:
            df: DataFrame з OHLCV даними
            
        Returns:
            tuple: (signal, confidence)
        """
        # Отримуємо ваги двигунів
        weights = self.tracker.get_weights()
        
        # Збираємо сигнали від усіх двигунів
        signals = []
        probs = []
        
        for name in self.engine_names:
            try:
                sig, prob = self.engines[name].signal(df)
                signals.append(sig)
                probs.append(prob)
            except Exception as e:
                print(f"⚠️ Помилка при отриманні сигналу з {name}: {e}")
                signals.append('HOLD')
                probs.append(0.0)
        
        # Конвертуємо сигнали в числові значення
        signal_map = {'SELL': -1, 'HOLD': 0, 'BUY': 1}
        numeric_signals = [signal_map.get(s, 0) for s in signals]
        
        # Зважена сума сигналів
        weighted_sum = sum(w * s * p for (name, w), s, p in zip(weights.items(), numeric_signals, probs))
        weighted_prob = sum(w * p for (name, w), p in zip(weights.items(), probs))
        
        # Визначаємо фінальний сигнал
        if weighted_sum > 0.3:
            final_signal = 'BUY'
        elif weighted_sum < -0.3:
            final_signal = 'SELL'
        else:
            final_signal = 'HOLD'
        
        return final_signal, weighted_prob
    
    def update_tracker(self, engine_name: str, pnl: float):
        """
        Оновлює трекер після виконання трейду.
        
        Args:
            engine_name: назва двигуна, що згенерував сигнал
            pnl: profit/loss трейду
        """
        self.tracker.update(engine_name, pnl)
