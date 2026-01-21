import ccxt
from app.core.config import settings

class CCXTAdapter:
    def __init__(self):
        self.exchange_name = settings.CCXT_EXCHANGE
        self._client = getattr(ccxt, self.exchange_name)()
        # only set keys if provided (we won't use live by default)
        if settings.CCXT_API_KEY and settings.CCXT_API_SECRET:
            self._client = getattr(ccxt, self.exchange_name)({
                "apiKey": settings.CCXT_API_KEY,
                "secret": settings.CCXT_API_SECRET
            })

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=1000):
        try:
            return self._client.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        except Exception:
            return []

    def create_order_live(self, *args, **kwargs):
        if not settings.ALLOW_LIVE_EXECUTION:
            raise RuntimeError("Live execution disabled by config")
        return self._client.create_order(*args, **kwargs)

    def simulate_order_execution(self, symbol, side, qty, price=None):
        # very simple simulation: use last ticker midpoint if available
        try:
            ticker = self._client.fetch_ticker(symbol)
            mid = (ticker.get("bid", 0) + ticker.get("ask", 0)) / 2.0
            executed_price = price or mid
        except Exception:
            executed_price = price or 0.0
        return {"executed_price": executed_price, "qty": qty}
