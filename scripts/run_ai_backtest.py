"""
Скрипт для запуску AI-керованого бектесту.

Використовує DecisionEngine для генерації сигналів та AIBacktester для симуляції торгівлі.
"""
import sys
import os
import pandas as pd

# Додаємо корінь проекту до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.decision_engine import DecisionEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics


def main():
    csv_path = 'data/btcusdt_5m.csv'
    
    print("Завантаження даних...")
    df = pd.read_csv(csv_path)
    print(f"Завантажено {len(df)} рядків")
    
    # Ініціалізуємо DecisionEngine
    print("\nІніціалізація DecisionEngine...")
    engine = DecisionEngine(model_path='models/btc_5m_model.pkl')
    
    # Генеруємо сигнали для кожної свічки
    print("Генерація сигналів...")
    signals = []
    for i in range(len(df)):
        # Використовуємо дані до поточного моменту
        df_subset = df.iloc[:i+1]
        try:
            signal, prob = engine.signal(df_subset)
            signals.append(signal)
        except:
            # Якщо недостатньо даних, утримуємося
            signals.append("HOLD")
    
    signals_series = pd.Series(signals)
    print(f"Згенеровано {len(signals)} сигналів")
    print(f"BUY: {(signals_series == 'BUY').sum()}, " +
          f"SELL: {(signals_series == 'SELL').sum()}, " +
          f"HOLD: {(signals_series == 'HOLD').sum()}")
    
    # Запускаємо бектест
    print("\nЗапуск бектесту...")
    backtester = AIBacktester(
        initial_balance=10000.0,
        fee_rate=0.001,
        slippage=0.0005
    )
    results = backtester.run(df, signals_series)
    
    # Виводимо результати
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТИ БЕКТЕСТУ")
    print("="*60)
    print(f"Початковий баланс: ${backtester.initial_balance:.2f}")
    print(f"Кінцевий баланс: ${results['final_balance']:.2f}")
    
    pnl = results['final_balance'] - backtester.initial_balance
    pnl_pct = (pnl / backtester.initial_balance) * 100
    print(f"Прибуток/збиток: ${pnl:.2f} ({pnl_pct:+.2f}%)")
    
    # Обчислюємо метрики
    print("\n" + "="*60)
    print("МЕТРИКИ ТОРГІВЛІ")
    print("="*60)
    metrics = compute_metrics(results['trades'])
    print(f"Кількість угод: {metrics['num_trades']}")
    print(f"Winrate: {metrics['winrate']*100:.2f}%")
    print(f"Середній виграш: ${metrics['avg_win']:.2f}")
    print(f"Середній програш: ${metrics['avg_loss']:.2f}")
    print(f"Очікувана прибутковість: ${metrics['expectancy']:.2f}")
    print("="*60)


if __name__ == '__main__':
    main()
