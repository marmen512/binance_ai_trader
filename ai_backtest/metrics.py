import numpy as np


def compute_metrics(trades):

    if not trades:
        return {}

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]

    winrate = len(wins) / len(trades)

    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    expectancy = winrate * avg_win + (1-winrate) * avg_loss

    return {
        "trades": len(trades),
        "winrate": round(winrate, 3),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2)
    }
