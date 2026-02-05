"""
Скрипт для візуалізації кривої капіталу.

Завантажує результати бектесту та будує графік.
"""
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

# Додаємо корінь проекту до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.decision_engine import DecisionEngine
from ai_backtest.engine import AIBacktester


def main():
    csv_path = 'data/btcusdt_5m.csv'
    
    print("Завантаження даних...")
    df = pd.read_csv(csv_path)
    
    # Ініціалізуємо DecisionEngine
    print("Ініціалізація DecisionEngine...")
    engine = DecisionEngine(model_path='models/btc_5m_model.pkl')
    
    # Генеруємо сигнали
    print("Генерація сигналів...")
    signals = []
    for i in range(len(df)):
        df_subset = df.iloc[:i+1]
        try:
            signal, prob = engine.signal(df_subset)
            signals.append(signal)
        except:
            signals.append("HOLD")
    
    signals_series = pd.Series(signals)
    
    # Запускаємо бектест
    print("Запуск бектесту...")
    backtester = AIBacktester(initial_balance=10000.0, fee_rate=0.001, slippage=0.0005)
    results = backtester.run(df, signals_series)
    
    # Будуємо графік
    print("Побудова графіку...")
    plt.figure(figsize=(14, 7))
    
    # Графік equity curve
    plt.subplot(2, 1, 1)
    plt.plot(results['equity_curve'], label='Equity', linewidth=2)
    plt.axhline(y=backtester.initial_balance, color='r', linestyle='--', 
                label=f'Initial: ${backtester.initial_balance}')
    plt.title('Крива Капіталу AI Бектест', fontsize=14, fontweight='bold')
    plt.xlabel('Час (індекс свічки)')
    plt.ylabel('Капітал ($)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Графік ціни BTC
    plt.subplot(2, 1, 2)
    plt.plot(df['close'].values, label='BTC Price', color='orange', linewidth=1.5)
    
    # Позначаємо угоди
    for trade in results['trades']:
        idx = trade['index']
        price = trade['price']
        if trade['type'] == 'BUY':
            plt.scatter(idx, price, color='green', marker='^', s=100, 
                       label='Buy' if idx == results['trades'][0]['index'] else '')
        elif trade['type'] == 'SELL':
            plt.scatter(idx, price, color='red', marker='v', s=100,
                       label='Sell' if 'Sell' not in plt.gca().get_legend_handles_labels()[1] else '')
    
    plt.title('Ціна BTC з Позначенням Угод', fontsize=14, fontweight='bold')
    plt.xlabel('Час (індекс свічки)')
    plt.ylabel('Ціна ($)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Зберігаємо графік
    output_path = 'backtest_equity_curve.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nГрафік збережено в {output_path}")
    
    # Показуємо графік (якщо можливо)
    try:
        plt.show()
    except:
        print("Неможливо відобразити графік (немає дисплею)")


if __name__ == '__main__':
    main()
