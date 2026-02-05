"""
Завантаження історичних даних BTC/USDT 5m з Binance.
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta


def main():
    print("Підключення до Binance...")
    exchange = ccxt.binance()
    
    symbol = 'BTC/USDT'
    timeframe = '5m'
    
    # Завантажуємо останні 30 днів даних
    since = exchange.parse8601((datetime.now() - timedelta(days=30)).isoformat())
    
    print(f"Завантаження {symbol} {timeframe} свічок...")
    all_candles = []
    
    while True:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not candles:
                break
            
            all_candles.extend(candles)
            since = candles[-1][0] + 1
            
            print(f"Завантажено {len(all_candles)} свічок...")
            
            if len(candles) < 1000:
                break
        except Exception as e:
            print(f"Помилка: {e}")
            break
    
    # Конвертуємо в DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Зберігаємо
    df.to_csv('data/btcusdt_5m.csv', index=False)
    print(f"Збережено {len(df)} свічок в data/btcusdt_5m.csv")


if __name__ == '__main__':
    main()
