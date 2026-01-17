from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.dataset_downloader import DatasetDownloader


def _load_price_parquet(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        raise BinanceAITraderError(f"Price dataset missing: {path}")
    df = pd.read_parquet(Path(path))
    if "timestamp" not in df.columns:
        raise BinanceAITraderError(f"Price dataset missing timestamp: {path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BinanceAITraderError(f"Price dataset missing columns {missing}: {path}")
    return df[required].copy()


def load_train_price_data(*, ai_data_root: str | Path = Path("ai_data")) -> pd.DataFrame:
    """CryptoLM (TRAIN). Contract: 1H UTC, deduped, sorted."""
    dl = DatasetDownloader(ai_data_root=ai_data_root)
    return _load_price_parquet(Path(dl.price_train_1h_path))


def load_validation_price_data(*, ai_data_root: str | Path = Path("ai_data")) -> pd.DataFrame:
    """Farmaanaa (VALIDATION). Contract: 1H UTC, deduped, sorted."""
    dl = DatasetDownloader(ai_data_root=ai_data_root)
    return _load_price_parquet(Path(dl.price_val_1h_path))
