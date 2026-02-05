def risk_filter(signal, prob, volatility):

    if volatility > 0.03:
        return "HOLD"

    if prob < 0.6:
        return "HOLD"

    return signal
