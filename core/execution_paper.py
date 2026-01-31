from core.execution_adapter import ExecutionAdapter


class PaperExecutionAdapter(ExecutionAdapter):

    def open_position(self, symbol, side, qty):
        print(f"[PAPER] OPEN {symbol} {side} {qty}")

    def close_position(self, symbol):
        print(f"[PAPER] CLOSE {symbol}")

    def adjust_position(self, symbol, delta_qty):
        print(f"[PAPER] ADJUST {symbol} delta={delta_qty}")
