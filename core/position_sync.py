from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    side: str
    qty: float


class PositionSyncEngine:

    def __init__(self, risk_manager, execution_adapter):
        self.risk = risk_manager
        self.exec = execution_adapter
        self.my_positions = {}

    # ---------------------

    def sync_position(
        self,
        leader_id,
        symbol,
        side,
        leader_qty,
        leader_balance,
        my_balance,
    ):

        key = f"{leader_id}:{symbol}"

        risk_ratio = my_balance / leader_balance
        my_target_qty = leader_qty * risk_ratio

        current = self.my_positions.get(key)

        # OPEN
        if leader_qty > 0 and current is None:

            allowed, reason = self.risk.can_open_trade(my_target_qty)

            if not allowed:
                return "SKIP", reason

            self.exec.open_position(symbol, side, my_target_qty)

            self.my_positions[key] = Position(symbol, side, my_target_qty)
            return "OPEN", my_target_qty

        # CLOSE
        if leader_qty == 0 and current:

            self.exec.close_position(symbol)

            del self.my_positions[key]
            return "CLOSE", 0

        # ADJUST
        if current:

            delta = my_target_qty - current.qty

            if abs(delta) > 1e-6:
                self.exec.adjust_position(symbol, delta)

            current.qty = my_target_qty
            return "ADJUST", delta

        return "HOLD", 0
