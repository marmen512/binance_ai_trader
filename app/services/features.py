def build_features_from_signal(signal_dict: dict, trader_metrics: dict = None, market_context: dict = None):
    trader_metrics = trader_metrics or {}
    market_context = market_context or {}
    f = {}
    side = (signal_dict.get("side") or "").lower()
    f["side_buy"] = 1 if side == "buy" else 0
    f["side_sell"] = 1 if side == "sell" else 0
    f["quantity"] = float(signal_dict.get("quantity", 0) or 0)
    f["leverage"] = float(signal_dict.get("leverage", 1.0) or 1.0)
    f["price"] = float(signal_dict.get("price") or 0.0)
    f["trader_winrate"] = float(trader_metrics.get("winrate", 0.5))
    f["trader_avg_pnl"] = float(trader_metrics.get("avg_pnl", 0.0))
    f["vol_1h"] = float(market_context.get("vol_1h", 0.0))
    return f
