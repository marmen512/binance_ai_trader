from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class BinanceClientConfig:
    base_url: str = "https://fapi.binance.com"
    timeout_s: int = 30
    max_retries: int = 3
    backoff_s: float = 0.8
    min_request_interval_s: float = 0.2


class BinanceFuturesClient:
    def __init__(self, cfg: BinanceClientConfig | None = None) -> None:
        self.cfg = cfg or BinanceClientConfig()
        self._last_request_ts = 0.0

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        qs = ""
        if params:
            qs = "?" + urlencode({k: v for k, v in params.items() if v is not None})
        url = self.cfg.base_url.rstrip("/") + path + qs

        # Simple rate limiting.
        now = time.time()
        wait_s = (self._last_request_ts + self.cfg.min_request_interval_s) - now
        if wait_s > 0:
            time.sleep(wait_s)

        last_err: Exception | None = None
        for attempt in range(1, int(self.cfg.max_retries) + 1):
            try:
                req = Request(url, headers={"User-Agent": "binance_ai_trader/1.0"})
                with urlopen(req, timeout=self.cfg.timeout_s) as resp:
                    raw = resp.read().decode("utf-8")
                self._last_request_ts = time.time()
                return json.loads(raw)
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
                last_err = e
                if attempt >= int(self.cfg.max_retries):
                    break
                time.sleep(self.cfg.backoff_s * (2 ** (attempt - 1)))

        raise BinanceAITraderError(f"Binance API request failed: {url} err={last_err}")
