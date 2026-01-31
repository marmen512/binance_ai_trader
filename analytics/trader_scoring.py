from analytics.trader_stats import TraderAnalytics


class TraderScoring:

    def __init__(self, db_path="storage/trades.db"):
        self.analytics = TraderAnalytics(db_path)

        # --- HARD FILTERS ---
        self.min_trades = 5
        self.max_drawdown = 50   # %
        self.min_roi = -50       # reject if worse

    def passes_filters(self, stats):

        if stats["trades"] < self.min_trades:
            return False

        if stats.get("max_dd", 0) > self.max_drawdown:
            return False

        if stats["roi"] < self.min_roi:
            return False

        return True

    def score(self, stats):

        if not self.passes_filters(stats):
            return -999

        score = (
            stats["roi"] * 0.4 +
            stats["winrate"] * 0.4 +
            stats["avg_pnl"] * 0.2
        )

        return score

    def top_leaders(self, top_n=5):

        leaders = self.analytics.all_leaders()

        ranked = []
        for l in leaders:
            s = self.score(l)
            if s > -999:
                ranked.append((s, l))

        ranked.sort(reverse=True, key=lambda x: x[0])

        return ranked[:top_n]
