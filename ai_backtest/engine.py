import pandas as pd


class AIBacktester:

    def __init__(
        self,
        decision_engine,
        fee=0.0004,
        slippage=0.0002,
        risk_per_trade=0.01
    ):
        self.engine = decision_engine
        self.fee = fee
        self.slippage = slippage
        self.risk = risk_per_trade

    def run(self, df: pd.DataFrame):

        balance = 10000
        position = 0
        entry_price = 0

        equity_curve = []
        trades = []

        for i in range(200, len(df)-1):

            window = df.iloc[:i]
            price = df.iloc[i]["close"]

            signal, prob = self.engine.signal(window)

            # exit logic
            if position != 0:
                ret = (price - entry_price) / entry_price * position

                if abs(ret) > 0.006 or signal == "HOLD":
                    pnl = ret * balance
                    pnl -= balance * self.fee
                    balance += pnl

                    trades.append(pnl)
                    position = 0

            # entry logic
            if position == 0:
                if signal == "BUY":
                    position = 1
                    entry_price = price * (1 + self.slippage)

                elif signal == "SELL":
                    position = -1
                    entry_price = price * (1 - self.slippage)

            equity_curve.append(balance)

        return {
            "equity": equity_curve,
            "trades": trades,
            "final_balance": balance
        }
