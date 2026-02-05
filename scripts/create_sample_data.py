"""
Create Sample BTC Data
Creates synthetic OHLCV data for testing when Binance API is unavailable
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_sample_data():
    """Create sample BTC 5m data"""
    
    # Generate 90 days of 5-minute data
    periods = 90 * 24 * 12  # 25920 candles
    
    # Start date
    start_date = datetime.now() - timedelta(days=90)
    
    # Generate timestamps
    timestamps = [start_date + timedelta(minutes=5*i) for i in range(periods)]
    
    # Generate realistic price data with trend and volatility
    np.random.seed(42)
    
    # Start at a realistic BTC price
    initial_price = 45000
    
    # Generate returns with trend and volatility
    returns = np.random.normal(0.0001, 0.015, periods)  # Slight upward bias
    prices = initial_price * np.exp(np.cumsum(returns))
    
    # Generate OHLCV data
    data = []
    for i in range(periods):
        close = prices[i]
        # Add intrabar volatility
        range_pct = abs(np.random.normal(0.003, 0.002))
        high = close * (1 + range_pct * np.random.uniform(0.3, 1))
        low = close * (1 - range_pct * np.random.uniform(0.3, 1))
        open_price = close * (1 + np.random.normal(0, 0.001))
        
        # Volume
        volume = abs(np.random.normal(50, 20))
        
        data.append({
            'timestamp': timestamps[i],
            'open': open_price,
            'high': max(open_price, close, high),
            'low': min(open_price, close, low),
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    
    # Save to CSV
    output_path = 'data/btcusdt_5m.csv'
    df.to_csv(output_path, index=False)
    print(f"Created sample data: {output_path}")
    print(f"Periods: {len(df)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")


if __name__ == '__main__':
    create_sample_data()
