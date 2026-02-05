import requests
import pandas as pd
import time

SYMBOL = "BTCUSDT"
INTERVAL = "5m"
LIMIT = 1000

def get_klines(start=None):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": LIMIT
    }
    if start:
        params["startTime"] = start

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


all_rows = []
start = None

for _ in range(10):  # ~10k candles
    rows = get_klines(start)

    if not rows:
        break

    all_rows.extend(rows)
    start = rows[-1][0] + 1
    time.sleep(0.2)

df = pd.DataFrame(all_rows, columns=[
    "ts","open","high","low","close","volume",
    "_","_","_","_","_","_"
])

df = df[["ts","open","high","low","close","volume"]]
df = df.astype(float)

df.to_csv("data/btcusdt_5m.csv", index=False)

print("Saved:", len(df))
