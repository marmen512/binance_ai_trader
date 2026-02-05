"""
Скрипт візуалізації equity curve з результатів бектесту.
"""
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys


if __name__ == '__main__':
    print("=== Візуалізація Equity Curve ===\n")
    
    # Завантаження equity curve
    equity_path = 'results/equity_curve.csv'
    if not os.path.exists(equity_path):
        print(f"Помилка: файл {equity_path} не знайдено!")
        print("Запустіть спочатку: python scripts/run_ai_backtest.py")
        sys.exit(1)
    
    equity_df = pd.read_csv(equity_path)
    print(f"Завантажено {len(equity_df)} точок equity curve")
    
    # Створення графіка
    plt.figure(figsize=(14, 7))
    
    plt.plot(equity_df.index, equity_df['balance'], linewidth=2, label='Portfolio Value')
    plt.axhline(y=10000, color='r', linestyle='--', linewidth=1, label='Initial Balance')
    
    plt.title('AI Strategy Equity Curve', fontsize=16, fontweight='bold')
    plt.xlabel('Time (Candles)', fontsize=12)
    plt.ylabel('Balance ($)', fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    # Збереження графіка
    output_path = 'results/equity_curve.png'
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"\nГрафік збережено: {output_path}")
    
    # Статистика
    initial_balance = equity_df['balance'].iloc[0]
    final_balance = equity_df['balance'].iloc[-1]
    max_balance = equity_df['balance'].max()
    min_balance = equity_df['balance'].min()
    
    print(f"\n=== Статистика ===")
    print(f"Початковий баланс: ${initial_balance:.2f}")
    print(f"Фінальний баланс: ${final_balance:.2f}")
    print(f"Максимальний баланс: ${max_balance:.2f}")
    print(f"Мінімальний баланс: ${min_balance:.2f}")
    print(f"ROI: {(final_balance / initial_balance - 1) * 100:.2f}%")
    
    # Максимальна просадка
    running_max = equity_df['balance'].expanding().max()
    drawdown = (equity_df['balance'] - running_max) / running_max
    max_drawdown = drawdown.min()
    
    print(f"Максимальна просадка: {max_drawdown * 100:.2f}%")
    
    print("\nВізуалізацію завершено!")
