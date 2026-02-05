"""
Скрипт завантаження історичних даних BTC/USDT 5m з Binance.
"""
import requests
import pandas as pd
import os
from datetime import datetime, timedelta


def download_binance_klines(symbol='BTCUSDT', interval='5m', days=90):
    """
    Завантажує історичні klines (свічки) з Binance.
    
    Args:
        symbol: Торгова пара (напр., 'BTCUSDT')
        interval: Інтервал (напр., '5m', '1h')
        days: Кількість днів історії
        
    Returns:
        DataFrame з колонками: timestamp, open, high, low, close, volume
    """
    print(f"Завантаження {symbol} {interval} за останні {days} днів...")
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    url = 'https://api.binance.com/api/v3/klines'
    
    all_data = []
    current_start = start_ms
    
    while current_start < end_ms:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_ms,
            'limit': 1000
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Помилка API: {response.status_code}")
            break
        
        data = response.json()
        
        if not data:
            break
        
        all_data.extend(data)
        current_start = data[-1][0] + 1
        
        print(f"Завантажено {len(all_data)} свічок...")
    
    # Конвертація в DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Вибираємо потрібні колонки та конвертуємо типи
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df


if __name__ == '__main__':
    # Завантаження BTC/USDT 5m
    df = download_binance_klines(symbol='BTCUSDT', interval='5m', days=90)
    
    print(f"\nЗавантажено всього: {len(df)} записів")
    print(f"Період: {df['timestamp'].min()} - {df['timestamp'].max()}")
    
    # Збереження
    os.makedirs('data', exist_ok=True)
    output_path = 'data/btcusdt_5m.csv'
    df.to_csv(output_path, index=False)
    
    print(f"\nДані збережено: {output_path}")
    print(f"Перші записи:")
    print(df.head())
