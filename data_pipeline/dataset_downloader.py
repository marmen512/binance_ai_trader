from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class DatasetSpec:
    hf_id: str
    card_name: str
    local_dir: Path
    parquet_path: Path
    role: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iso_date(ts: pd.Timestamp) -> str:
    return ts.date().isoformat()


def _infer_frequency_seconds(ts: pd.Series) -> float | None:
    s = pd.to_datetime(ts, utc=True, errors="coerce").dropna()
    if s.size < 3:
        return None
    s2 = s.sort_values().drop_duplicates()
    diffs = s2.diff().dropna().dt.total_seconds()
    diffs = diffs[(diffs > 0) & np.isfinite(diffs)]
    if diffs.empty:
        return None
    return float(diffs.median())


def _freq_label(freq_s: float | None) -> str:
    if freq_s is None or not np.isfinite(freq_s) or freq_s <= 0:
        return "unknown"
    if abs(freq_s - 60) < 2:
        return "1m"
    if abs(freq_s - 300) < 5:
        return "5m"
    if abs(freq_s - 900) < 10:
        return "15m"
    if abs(freq_s - 3600) < 15:
        return "1h"
    if abs(freq_s - 4 * 3600) < 30:
        return "4h"
    if abs(freq_s - 24 * 3600) < 120:
        return "1d"
    return "unknown"


def _coverage_ratio(ts: pd.Series) -> float:
    s = pd.to_datetime(ts, utc=True, errors="coerce").dropna()
    if s.size < 2:
        return 0.0
    s2 = s.sort_values().drop_duplicates()
    freq = _infer_frequency_seconds(s2)
    if freq is None or freq <= 0:
        return 0.0
    start = s2.iloc[0]
    end = s2.iloc[-1]
    span = float((end - start).total_seconds())
    if span <= 0:
        return 0.0
    expected = int(np.floor(span / freq)) + 1
    if expected <= 0:
        return 0.0
    return float(min(1.0, s2.size / expected))


def _write_dataset_card(
    *,
    card_path: Path,
    name: str,
    source: str,
    sha256: str,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    frequency: str,
    role: str,
) -> None:
    card_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "source": source,
        "hash": f"sha256:{sha256}",
        "date_range": f"{_iso_date(start_ts)} -> {_iso_date(end_ts)}",
        "frequency": frequency,
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    card_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_price_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]

    ts_candidates = [
        "timestamp",
        "time",
        "date",
        "datetime",
        "open_time",
        "close_time",
    ]
    ts_col = next((c for c in ts_candidates if c in out.columns), None)
    if ts_col is None:
        raise BinanceAITraderError("Price dataset missing timestamp column")

    ts = out[ts_col]
    if np.issubdtype(ts.dtype, np.number):
        v = pd.to_numeric(ts, errors="coerce")
        med = float(v.dropna().median()) if not v.dropna().empty else 0.0
        unit = "ms" if med > 10_000_000_000 else "s"
        out["timestamp"] = pd.to_datetime(v, unit=unit, utc=True, errors="coerce")
    else:
        out["timestamp"] = pd.to_datetime(ts, utc=True, errors="coerce")

    mapping = {
        "open": ["open"],
        "high": ["high"],
        "low": ["low"],
        "close": ["close", "adj_close", "price"],
        "volume": ["volume", "vol", "quote_volume", "base_volume"],
    }

    for target, candidates in mapping.items():
        col = next((c for c in candidates if c in out.columns), None)
        if col is None:
            raise BinanceAITraderError(f"Price dataset missing required column: {target}")
        out[target] = pd.to_numeric(out[col], errors="coerce")

    norm = out[["timestamp", "open", "high", "low", "close", "volume"]].dropna().copy()
    norm = norm.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    freq_s = _infer_frequency_seconds(norm["timestamp"])
    if freq_s is not None and np.isfinite(freq_s) and freq_s < 3500:
        norm = _resample_ohlcv_1h(norm)
        norm = _fill_missing_1h_candles(norm)

    return norm


def _resample_ohlcv_1h(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    tmp["timestamp"] = pd.to_datetime(tmp["timestamp"], utc=True, errors="coerce")
    tmp = tmp.dropna(subset=["timestamp"]).sort_values("timestamp")
    tmp = tmp.set_index("timestamp")

    r = tmp.resample("1h", label="right", closed="right")
    out = pd.DataFrame(
        {
            "open": r["open"].first(),
            "high": r["high"].max(),
            "low": r["low"].min(),
            "close": r["close"].last(),
            "volume": r["volume"].sum(),
        }
    )
    out = out.dropna().reset_index()
    return out[["timestamp", "open", "high", "low", "close", "volume"]]


def _fill_missing_1h_candles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    if out.empty:
        return out

    start = out["timestamp"].iloc[0]
    end = out["timestamp"].iloc[-1]
    full_idx = pd.date_range(start=start, end=end, freq="1h", tz="UTC")

    out = out.set_index("timestamp").reindex(full_idx)

    close = pd.to_numeric(out["close"], errors="coerce")
    close_ffill = close.ffill()

    out["close"] = close_ffill
    out["open"] = pd.to_numeric(out["open"], errors="coerce").fillna(close_ffill)
    out["high"] = pd.to_numeric(out["high"], errors="coerce").fillna(close_ffill)
    out["low"] = pd.to_numeric(out["low"], errors="coerce").fillna(close_ffill)
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0)

    out = out.dropna(subset=["close"]).reset_index().rename(columns={"index": "timestamp"})
    return out[["timestamp", "open", "high", "low", "close", "volume"]]


def _normalize_sentiment_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]

    ts_candidates = ["timestamp", "time", "date", "datetime", "created_at", "published_at"]
    ts_col = next((c for c in ts_candidates if c in out.columns), None)
    if ts_col is None:
        raise BinanceAITraderError("Sentiment dataset missing timestamp column")

    score_candidates = [
        "sentiment",
        "sentiment_score",
        "compound",
        "polarity",
        "score",
        "label",
    ]
    sc_col = next((c for c in score_candidates if c in out.columns), None)
    if sc_col is None:
        raise BinanceAITraderError("Sentiment dataset missing sentiment score column")

    ts = out[ts_col]
    if np.issubdtype(ts.dtype, np.number):
        v = pd.to_numeric(ts, errors="coerce")
        med = float(v.dropna().median()) if not v.dropna().empty else 0.0
        unit = "ms" if med > 10_000_000_000 else "s"
        out["timestamp"] = pd.to_datetime(v, unit=unit, utc=True, errors="coerce")
    else:
        out["timestamp"] = pd.to_datetime(ts, utc=True, errors="coerce")

    score_raw = out[sc_col]
    if score_raw.dtype == object:
        mapped = score_raw.astype("string").str.lower().map({"positive": 1.0, "negative": -1.0, "neutral": 0.0})
        score = pd.to_numeric(mapped, errors="coerce")
        score = score.fillna(pd.to_numeric(score_raw, errors="coerce"))
    else:
        score = pd.to_numeric(score_raw, errors="coerce")

    norm = pd.DataFrame({"timestamp": out["timestamp"], "sentiment": score}).dropna().copy()
    norm = norm.sort_values("timestamp").reset_index(drop=True)
    return norm


class DatasetDownloader:
    def __init__(self, *, ai_data_root: str | Path = Path("ai_data")) -> None:
        self.ai_data_root = Path(ai_data_root)

        self.price_train_1h_path = self.ai_data_root / "price" / "cryptolm_btcusdt_1h.parquet"
        self.price_val_1h_path = self.ai_data_root / "price" / "farmaanaa_btcusdt_1h.parquet"

        self.sentiment_1h_path = self.ai_data_root / "sentiment" / "sentiment_1h.parquet"

        self.price_1 = DatasetSpec(
            hf_id="WinkingFace/CryptoLM-Bitcoin-BTC-USDT",
            card_name="CryptoLM-Bitcoin-BTC-USDT",
            local_dir=self.ai_data_root / "price" / "cryptolm_btc_usdt",
            parquet_path=self.price_train_1h_path,
            role="offline_training",
        )
        self.price_2 = DatasetSpec(
            hf_id="Farmaanaa/bitcoin_price_timeseries",
            card_name="bitcoin_price_timeseries",
            local_dir=self.ai_data_root / "price" / "farmaanaa_btc_timeseries",
            parquet_path=self.price_val_1h_path,
            role="validation",
        )

        self.sentiment_raw_path = self.ai_data_root / "sentiment" / "raw" / "sentiment_raw.parquet"
        self.sentiment_agg_dir = self.ai_data_root / "sentiment" / "aggregated"

    def download_price_datasets(self, *, overwrite: bool = False) -> None:
        """Downloads:
        - WinkingFace/CryptoLM-Bitcoin-BTC-USDT
        - Farmaanaa/bitcoin_price_timeseries
        """
        for spec in [self.price_1, self.price_2]:
            self._download_hf_dataset_to_parquet(spec, overwrite=bool(overwrite))

    def download_sentiment_dataset(self, source: str, *, overwrite: bool = False) -> None:
        """source: 'tweets' | 'news'"""
        src = str(source).strip().lower()
        if src not in {"tweets", "news"}:
            raise BinanceAITraderError("source must be 'tweets' or 'news'")

        hf_id = "ckandemir/bitcoin_tweets_sentiment_kaggle" if src == "tweets" else "edaschau/bitcoin_news"

        try:
            from datasets import load_dataset  # type: ignore
        except Exception as e:
            raise BinanceAITraderError(f"Missing dependency 'datasets' for HuggingFace download: {e}")

        ds = load_dataset(hf_id)
        if "train" in ds:
            split = ds["train"]
        else:
            split = next(iter(ds.values()))

        df = split.to_pandas()
        norm = _normalize_sentiment_df(df)

        self.sentiment_raw_path.parent.mkdir(parents=True, exist_ok=True)
        if self.sentiment_raw_path.exists() and not bool(overwrite):
            raise BinanceAITraderError(f"Refusing to overwrite existing sentiment raw: {self.sentiment_raw_path}")
        norm.to_parquet(self.sentiment_raw_path, index=False)

        sha = _sha256_file(self.sentiment_raw_path)
        start_ts = pd.to_datetime(norm["timestamp"], utc=True).min()
        end_ts = pd.to_datetime(norm["timestamp"], utc=True).max()

        card_path = self.ai_data_root / "sentiment" / "raw" / "dataset_card.json"
        _write_dataset_card(
            card_path=card_path,
            name=hf_id,
            source="huggingface",
            sha256=sha,
            start_ts=start_ts,
            end_ts=end_ts,
            frequency="unknown",
            role="sentiment_raw",
        )

    def verify_integrity(self) -> None:
        """Hard verification for mandatory datasets.

        - checks row count
        - checks timestamps
        - checks required columns
        """
        for spec in [self.price_1, self.price_2]:
            self._verify_price_parquet(spec)

        if self.sentiment_raw_path.exists():
            self._verify_sentiment_parquet(self.sentiment_raw_path)

    def mandatory_ready(self) -> bool:
        try:
            self.verify_integrity()
            return True
        except Exception:
            return False

    def _download_hf_dataset_to_parquet(self, spec: DatasetSpec, *, overwrite: bool = False) -> None:
        if spec.hf_id == "Farmaanaa/bitcoin_price_timeseries":
            df = self._download_farmaanaa_csv()
        else:
            try:
                from datasets import load_dataset  # type: ignore
            except Exception as e:
                raise BinanceAITraderError(f"Missing dependency 'datasets' for HuggingFace download: {e}")

            ds = load_dataset(spec.hf_id)
            if "train" in ds:
                split = ds["train"]
            else:
                split = next(iter(ds.values()))

            df = split.to_pandas()
        norm = _normalize_price_df(df)

        spec.parquet_path.parent.mkdir(parents=True, exist_ok=True)
        if spec.parquet_path.exists() and not bool(overwrite):
            raise BinanceAITraderError(f"Refusing to overwrite existing dataset parquet: {spec.parquet_path}")
        norm.to_parquet(spec.parquet_path, index=False)

        sha = _sha256_file(spec.parquet_path)
        start_ts = pd.to_datetime(norm["timestamp"], utc=True).min()
        end_ts = pd.to_datetime(norm["timestamp"], utc=True).max()

        freq_s = _infer_frequency_seconds(norm["timestamp"])
        freq = _freq_label(freq_s)

        card_path = spec.local_dir / "dataset_card.json"
        _write_dataset_card(
            card_path=card_path,
            name=spec.card_name,
            source="huggingface",
            sha256=sha,
            start_ts=start_ts,
            end_ts=end_ts,
            frequency=freq,
            role=spec.role,
        )

    def _download_farmaanaa_csv(self) -> pd.DataFrame:
        try:
            from huggingface_hub import hf_hub_download  # type: ignore
        except Exception as e:
            raise BinanceAITraderError(f"Missing dependency 'huggingface_hub' for HuggingFace download: {e}")

        p = Path(
            hf_hub_download(
                repo_id="Farmaanaa/bitcoin_price_timeseries",
                filename="bitcoin_price_timeseries.csv",
                repo_type="dataset",
            )
        )
        try:
            df = pd.read_csv(p)
        except Exception as e:
            raise BinanceAITraderError(f"Failed to read downloaded CSV {p}: {e}")
        return df

    def dataset_status(self) -> dict:
        def one(spec: DatasetSpec) -> dict:
            card_path = spec.local_dir / "dataset_card.json"
            return {
                "hf_id": spec.hf_id,
                "name": spec.card_name,
                "role": spec.role,
                "parquet_path": str(spec.parquet_path),
                "card_path": str(card_path),
                "exists": bool(spec.parquet_path.exists() and card_path.exists()),
            }

        raw_card = self.ai_data_root / "sentiment" / "raw" / "dataset_card.json"
        return {
            "price": {
                "cryptolm_btc_usdt": one(self.price_1),
                "farmaanaa_btc_timeseries": one(self.price_2),
            },
            "sentiment": {
                "raw_path": str(self.sentiment_raw_path),
                "raw_card": str(raw_card),
                "raw_exists": bool(self.sentiment_raw_path.exists() and raw_card.exists()),
                "aggregated_dir": str(self.sentiment_agg_dir),
            },
            "mandatory_ready": bool(self.mandatory_ready()),
        }

    def _verify_price_parquet(self, spec: DatasetSpec) -> None:
        if not spec.parquet_path.exists():
            raise BinanceAITraderError(f"Mandatory dataset is missing: {spec.parquet_path}")

        df = pd.read_parquet(spec.parquet_path)
        cols = set(df.columns)
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = sorted([c for c in required if c not in cols])
        if missing:
            raise BinanceAITraderError(f"Dataset {spec.parquet_path} missing columns: {missing}")

        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        if ts.isna().any():
            raise BinanceAITraderError(f"Dataset {spec.parquet_path} has invalid timestamps")

        if ts.duplicated().any():
            raise BinanceAITraderError(f"Dataset {spec.parquet_path} has duplicate timestamps")

        if not ts.is_monotonic_increasing:
            raise BinanceAITraderError(f"Dataset {spec.parquet_path} timestamps are not monotonic increasing")

        freq_s = _infer_frequency_seconds(ts)
        freq = _freq_label(freq_s)
        min_rows = 1000
        if freq == "1d":
            min_rows = 365
        if freq == "4h":
            min_rows = 500
        if int(df.shape[0]) < int(min_rows):
            raise BinanceAITraderError(f"Dataset {spec.parquet_path} row count too small: {df.shape[0]}")

        cov = _coverage_ratio(ts)
        if cov < 0.95:
            raise BinanceAITraderError(f"Dataset {spec.parquet_path} coverage < 95%: {cov:.3f}")

        card_path = spec.local_dir / "dataset_card.json"
        if not card_path.exists():
            raise BinanceAITraderError(f"Missing dataset card: {card_path}")

    def _verify_sentiment_parquet(self, path: Path) -> None:
        df = pd.read_parquet(path)
        cols = set(df.columns)
        required = {"timestamp", "sentiment"}
        missing = sorted([c for c in required if c not in cols])
        if missing:
            raise BinanceAITraderError(f"Sentiment raw missing columns: {missing}")

        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        if ts.isna().any():
            raise BinanceAITraderError("Sentiment raw has invalid timestamps")

        if int(df.shape[0]) < 50:
            raise BinanceAITraderError(f"Sentiment raw row count too small: {df.shape[0]}")

        card_path = self.ai_data_root / "sentiment" / "raw" / "dataset_card.json"
        if not card_path.exists():
            raise BinanceAITraderError(f"Missing dataset card: {card_path}")
