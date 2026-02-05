"""
Скрипт для завантаження історичних даних BTCUSDT 5m з Binance.

Використовує публічне API Binance для завантаження klines (свічок)
та збереження їх у CSV форматі для подальшого аналізу.
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os


def download_binance_klines(symbol='BTCUSDT', interval='5m', days=90):
    """
    Завантажує історичні дані klines з Binance.
    
    Параметри:
        symbol (str): торгова пара (за замовчуванням 'BTCUSDT')
        interval (str): інтервал свічок ('1m', '5m', '15m', '1h' тощо)
        days (int): кількість днів історії для завантаження
        
    Повертає:
        pd.DataFrame: DataFrame з колонками timestamp, open, high, low, close, volume
    """
    print(f"Завантаження {symbol} {interval} за останні {days} днів...")
    
    # URL API Binance для klines
    url = 'https://api.binance.com/api/v3/klines'
    
    # Обчислюємо часові межі
    end_time = int(time.time() * 1000)  # Поточний час у мілісекундах
    start_time = end_time - (days * 24 * 60 * 60 * 1000)  # days днів назад
    
    all_data = []
    current_start = start_time
    
    # Завантажуємо дані порціями (максимум 1000 свічок за запит)
    while current_start < end_time:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_time,
            'limit': 1000  # Максимальна кількість записів за один запит
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            all_data.extend(data)
            
            # Оновлюємо початковий час для наступного запиту
            current_start = data[-1][0] + 1
            
            print(f"Завантажено {len(all_data)} свічок...")
            
            # Невелика затримка, щоб не перевантажувати API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Помилка при завантаженні: {e}")
            break
    
    # Перетворюємо у DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Залишаємо тільки необхідні колонки
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Конвертуємо типи даних
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    print(f"Завантажено {len(df)} свічок")
    print(f"Період: {df['timestamp'].min()} - {df['timestamp'].max()}")
    
    return df


if __name__ == '__main__':
    # Завантажуємо дані BTCUSDT 5m за останні 90 днів
    df = download_binance_klines(symbol='BTCUSDT', interval='5m', days=90)
    
    # Зберігаємо у CSV
    output_path = 'data/btcusdt_5m.csv'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"\nДані збережено у: {output_path}")
    print(f"Розмір: {len(df)} записів")
    print(f"\nПриклад даних:")
    print(df.head())
    print(f"\nСтатистика:")
    print(df.describe())
