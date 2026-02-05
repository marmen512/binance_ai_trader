"""
download_btc_5m.py — завантажує 5-хвилинні дані BTC з Binance.
"""

import requests
import pandas as pd
from datetime import datetime


def download_btc_5m():
    """Завантажує історичні дані BTC/USDT 5m з Binance."""
    print("Завантаження даних BTC/USDT 5m з Binance...")

    url = "https://api.binance.com/api/v3/klines"
    symbol = "BTCUSDT"
    interval = "5m"
    limit = 1000

    all_data = []

    # Отримуємо останні 1000 свічок
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Помилка: {response.status_code}")
        return

    klines = response.json()

    for kline in klines:
        all_data.append({
            'timestamp': kline[0],
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5])
        })

    df = pd.DataFrame(all_data)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Зберігаємо у CSV
    df.to_csv('data/btcusdt_5m.csv', index=False)
    print(f"Завантажено {len(df)} рядків")
    print("Дані збережено у data/btcusdt_5m.csv")


if __name__ == '__main__':
    download_btc_5m()
