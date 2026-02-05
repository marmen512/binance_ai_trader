"""
Download BTC/USDT 5-minute data from Binance.
"""
import pandas as pd
import requests
import time
import os


def download_btc_5m(days=90):
    """
    Download BTC/USDT 5m data from Binance.
    
    Args:
        days: Number of days of historical data to download
    """
    print(f"[Download] Downloading {days} days of BTC/USDT 5m data...")
    
    symbol = 'BTCUSDT'
    interval = '5m'
    
    # Calculate timestamps
    end_time = int(time.time() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)
    
    all_data = []
    current_start = start_time
    
    while current_start < end_time:
        # Binance API endpoint
        url = 'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_time,
            'limit': 1000  # Max 1000 candles per request
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if len(data) == 0:
                break
            
            all_data.extend(data)
            
            # Update start time for next batch
            current_start = data[-1][0] + 1
            
            print(f"[Download] Downloaded {len(all_data)} candles...")
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[Download] Error: {e}")
            break
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Convert types
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # Select relevant columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Save to file
    os.makedirs('data', exist_ok=True)
    output_path = 'data/btcusdt_5m.csv'
    df.to_csv(output_path, index=False)
    
    print(f"[Download] Saved {len(df)} rows to {output_path}")
    print(f"[Download] Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")


if __name__ == '__main__':
    download_btc_5m(days=90)
