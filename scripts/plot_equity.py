"""
Скрипт для візуалізації кривої капіталу з бектесту.

Створює графік зміни капіталу протягом періоду торгівлі
на основі результатів бектесту.
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# Додаємо кореневу директорію до PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def plot_equity_curve(equity_path='data/equity_curve.csv', 
                     trades_path='data/trades.csv',
                     save_path='data/equity_plot.png'):
    """
    Створює та зберігає графік кривої капіталу.
    
    Параметри:
        equity_path (str): шлях до CSV файлу з кривою капіталу
        trades_path (str): шлях до CSV файлу з угодами
        save_path (str): шлях для збереження графіку
    """
    print("=" * 60)
    print("ВІЗУАЛІЗАЦІЯ КРИВОЇ КАПІТАЛУ")
    print("=" * 60)
    
    # Перевіряємо наявність файлів
    if not os.path.exists(equity_path):
        print(f"\nПомилка: файл {equity_path} не знайдено!")
        print("Спочатку запустіть бектест: python scripts/run_ai_backtest.py")
        return
    
    # Завантажуємо дані
    print(f"\n1. Завантаження кривої капіталу з {equity_path}...")
    equity_df = pd.read_csv(equity_path)
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
    print(f"   Завантажено {len(equity_df)} точок")
    
    # Створюємо фігуру з двома підграфіками
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])
    
    # Графік кривої капіталу
    print(f"\n2. Побудова графіку кривої капіталу...")
    ax1.plot(equity_df['timestamp'], equity_df['equity'], 
             linewidth=2, color='#2E86AB', label='Капітал')
    
    # Додаємо горизонтальну лінію початкового капіталу
    initial_capital = equity_df['equity'].iloc[0]
    ax1.axhline(y=initial_capital, color='gray', linestyle='--', 
                linewidth=1, alpha=0.7, label=f'Початковий капітал: {initial_capital:.0f} USDT')
    
    ax1.set_xlabel('Час', fontsize=12)
    ax1.set_ylabel('Капітал (USDT)', fontsize=12)
    ax1.set_title('Крива капіталу AI торгової стратегії', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Графік просадки (drawdown)
    print(f"\n3. Побудова графіку просадки...")
    running_max = equity_df['equity'].cummax()
    drawdown = (equity_df['equity'] - running_max) / running_max * 100
    
    ax2.fill_between(equity_df['timestamp'], drawdown, 0, 
                     color='#A23B72', alpha=0.5, label='Просадка')
    ax2.set_xlabel('Час', fontsize=12)
    ax2.set_ylabel('Просадка (%)', fontsize=12)
    ax2.set_title('Просадка капіталу', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # Форматуємо дати на осі X
    fig.autofmt_xdate()
    
    # Додаємо статистику на графік
    final_capital = equity_df['equity'].iloc[-1]
    total_return = (final_capital / initial_capital - 1) * 100
    max_drawdown = drawdown.min()
    
    stats_text = f'Фінальний капітал: {final_capital:.2f} USDT\n'
    stats_text += f'Прибуток/Збиток: {total_return:.2f}%\n'
    stats_text += f'Макс. просадка: {max_drawdown:.2f}%'
    
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
             fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Якщо є дані про угоди, відмічаємо їх на графіку
    if os.path.exists(trades_path):
        print(f"\n4. Додавання міток угод...")
        trades_df = pd.read_csv(trades_path)
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        
        # Відмічаємо входи
        entries = trades_df[trades_df['action'].str.contains('ENTRY')]
        for _, trade in entries.iterrows():
            color = 'green' if 'LONG' in trade['action'] else 'red'
            marker = '^' if 'LONG' in trade['action'] else 'v'
            ax1.scatter(trade['timestamp'], trade['capital'], 
                       color=color, marker=marker, s=100, alpha=0.7, zorder=5)
        
        print(f"   Відмічено {len(entries)} входів у позиції")
    
    # Зберігаємо графік
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\n5. Графік збережено: {save_path}")
    
    # Показуємо графік (якщо запущено інтерактивно)
    print(f"\n{'=' * 60}")
    print("ВІЗУАЛІЗАЦІЯ ЗАВЕРШЕНА")
    print(f"{'=' * 60}")
    print(f"\nГрафік збережено у файл: {save_path}")
    
    # Спроба показати графік
    try:
        plt.show()
    except:
        print("(Графік не може бути відображений в неінтерактивному режимі)")


if __name__ == '__main__':
    plot_equity_curve()
