"""
Binance Data Downloader
Downloads historical klines data from Binance API
"""
import requests
import pandas as pd
import time
from datetime import datetime, timedelta


def download_btc_5m(days=90):
    """
    Download BTC/USDT 5-minute klines data from Binance
    
    Args:
        days: Number of days of historical data to download
    """
    symbol = "BTCUSDT"
    interval = "5m"
    
    print(f"Downloading {symbol} {interval} data for last {days} days...")
    
    # Calculate start time
    end_time = int(time.time() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)
    
    all_klines = []
    current_start = start_time
    
    while current_start < end_time:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "limit": 1000
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            klines = response.json()
            
            if not klines:
                break
            
            all_klines.extend(klines)
            current_start = klines[-1][0] + 1
            
            print(f"Downloaded {len(all_klines)} candles...", end='\r')
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            print(f"\nError downloading data: {e}")
            break
    
    print(f"\nTotal candles downloaded: {len(all_klines)}")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Convert types
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # Keep only necessary columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Save to CSV
    output_path = 'data/btcusdt_5m.csv'
    df.to_csv(output_path, index=False)
    print(f"Saved to: {output_path}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")


if __name__ == '__main__':
    download_btc_5m(days=90)
