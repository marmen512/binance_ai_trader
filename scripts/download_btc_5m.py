"""
Скрипт для завантаження даних BTC/USDT 5m з Binance.

Завантажує історичні дані свічок та зберігає у data/btcusdt_5m.csv
"""
import requests
import pandas as pd
import os
from datetime import datetime


def download_binance_klines(symbol='BTCUSDT', interval='5m', limit=1000):
    """
    Завантажує klines (свічкові дані) з Binance API.
    
    Args:
        symbol: торгова пара (наприклад, 'BTCUSDT')
        interval: інтервал свічок ('1m', '5m', '15m', '1h', тощо)
        limit: кількість свічок (макс. 1000)
        
    Returns:
        DataFrame з колонками: timestamp, open, high, low, close, volume
    """
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    print(f"Завантаження {limit} свічок {symbol} {interval}...")
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json()
    
    # Перетворюємо у DataFrame
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Вибираємо потрібні колонки
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Перетворюємо типи
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df


def main():
    # Завантажуємо дані
    df = download_binance_klines(symbol='BTCUSDT', interval='5m', limit=1000)
    
    print(f"Завантажено {len(df)} рядків")
    print(f"Період: з {df['timestamp'].min()} до {df['timestamp'].max()}")
    
    # Зберігаємо у файл
    os.makedirs('data', exist_ok=True)
    output_path = 'data/btcusdt_5m.csv'
    df.to_csv(output_path, index=False)
    print(f"Дані збережено в {output_path}")
    
    # Показуємо перші рядки
    print("\nПерші рядки:")
    print(df.head())


if __name__ == '__main__':
    main()
