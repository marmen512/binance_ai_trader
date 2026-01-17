from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.dataset_downloader import DatasetDownloader
from data_pipeline.sentiment_aggregation import aggregate_sentiment


def load_tweets_sentiment(*, ai_data_root: str | Path = Path("ai_data")) -> pd.DataFrame:
    dl = DatasetDownloader(ai_data_root=ai_data_root)
    rp = Path(dl.sentiment_raw_path)
    if not rp.exists():
        raise BinanceAITraderError(f"Sentiment raw missing: {rp}. Run: python main.py download-datasets --sentiment tweets")
    return pd.read_parquet(rp)


def load_news_sentiment(*, ai_data_root: str | Path = Path("ai_data")) -> pd.DataFrame:
    dl = DatasetDownloader(ai_data_root=ai_data_root)
    rp = Path(dl.sentiment_raw_path)
    if not rp.exists():
        raise BinanceAITraderError(f"Sentiment raw missing: {rp}. Run: python main.py download-datasets --sentiment news")
    return pd.read_parquet(rp)


def aggregate_sentiment_1h(*, ai_data_root: str | Path = Path("ai_data")) -> Path:
    dl = DatasetDownloader(ai_data_root=ai_data_root)
    res = aggregate_sentiment(raw_path=Path(dl.sentiment_raw_path), out_path=Path(dl.sentiment_1h_path), freq="1h")
    return Path(res.output_path)
