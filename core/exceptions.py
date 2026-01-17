from __future__ import annotations


class BinanceAITraderError(Exception):
    pass


class ConfigError(BinanceAITraderError):
    pass


class DependencyError(BinanceAITraderError):
    pass
