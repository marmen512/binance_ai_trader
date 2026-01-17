from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk  # type: ignore
    from tkinter import ttk  # type: ignore

    _HAS_TK = True
except Exception:
    tk = None  # type: ignore
    ttk = None  # type: ignore
    _HAS_TK = False

from core.config import load_config
from core.exceptions import BinanceAITraderError
from core.logger import setup_logger
from training.pipeline import train_offline
from trading.paper_trading import paper_trade_once
from trading.pipeline import run_decision_engine
from trading.paper_broker import PaperState, save_state


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="binance_ai_trader_gui")
    p.add_argument(
        "--config",
        default=str(Path("config") / "config.yaml"),
        help="Path to config.yaml",
    )
    return p


def _to_jsonable(x):
    if x is None:
        return None
    if hasattr(x, "__dict__"):
        d = dict(x.__dict__)
        if "fill" in d and d["fill"] is not None and hasattr(d["fill"], "__dict__"):
            d["fill"] = dict(d["fill"].__dict__)
        return d
    return x


class App:
    def __init__(self, *, config_path: str) -> None:
        self.config_path = config_path

        self.root = tk.Tk()
        self.root.title("Binance AI Trader (Desktop GUI)")
        self.root.geometry("980x720")

        self._last_action = tk.StringVar(value="idle")

        self._inputs_var = tk.StringVar(value="ai_data/my_datasets/sample_targets.parquet")
        self._model_id_var = tk.StringVar(value="")

        self._to_target_var = tk.StringVar(value="future_log_return")
        self._to_alpha_var = tk.StringVar(value="1.0")
        self._to_train_frac_var = tk.StringVar(value="0.70")
        self._to_val_frac_var = tk.StringVar(value="0.15")

        self._de_out_path_var = tk.StringVar(value="ai_data/reports/decision_engine_out.parquet")
        self._de_report_path_var = tk.StringVar(value="ai_data/reports/decision_engine_report.json")

        self._pt_fee_bps_var = tk.StringVar(value="1.0")
        self._pt_slip_bps_var = tk.StringVar(value="1.0")
        self._pt_lookback_var = tk.StringVar(value="200")
        self._pt_enforce_tv_var = tk.StringVar(value="false")
        self._pt_pos_mode_var = tk.StringVar(value="sign")
        self._pt_max_lev_var = tk.StringVar(value="1.0")

        self._build_ui()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x")

        ttk.Label(top, text="config_path").pack(side="left")
        cfg_entry = ttk.Entry(top)
        cfg_entry.insert(0, self.config_path)
        cfg_entry.configure(state="disabled")
        cfg_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))

        ttk.Label(top, textvariable=self._last_action).pack(side="right")

        grid = ttk.Frame(frm)
        grid.pack(fill="x", pady=(12, 8))

        ttk.Label(grid, text="inputs (comma/newline separated)").grid(row=0, column=0, sticky="w")
        self.inputs_entry = ttk.Entry(grid, textvariable=self._inputs_var)
        self.inputs_entry.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(grid, text="model_id").grid(row=2, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self._model_id_var).grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(0, 8))

        ttk.Button(btns, text="train-offline", command=self._run_train_offline).pack(side="left")
        ttk.Button(btns, text="run-decision-engine", command=self._run_decision_engine).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="paper-trade-once", command=self._run_paper_trade_once).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="reset paper state", command=self._reset_paper_state).pack(side="left", padx=(8, 0))

        opts = ttk.Notebook(frm)
        opts.pack(fill="x", pady=(8, 8))

        tab_to = ttk.Frame(opts, padding=10)
        tab_de = ttk.Frame(opts, padding=10)
        tab_pt = ttk.Frame(opts, padding=10)
        opts.add(tab_to, text="train-offline")
        opts.add(tab_de, text="decision-engine")
        opts.add(tab_pt, text="paper-trade")

        ttk.Label(tab_to, text="target_col").grid(row=0, column=0, sticky="w")
        ttk.Entry(tab_to, textvariable=self._to_target_var).grid(row=1, column=0, sticky="ew")
        ttk.Label(tab_to, text="alpha").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Entry(tab_to, textvariable=self._to_alpha_var).grid(row=1, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(tab_to, text="train_frac").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(tab_to, textvariable=self._to_train_frac_var).grid(row=3, column=0, sticky="ew")
        ttk.Label(tab_to, text="val_frac").grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        ttk.Entry(tab_to, textvariable=self._to_val_frac_var).grid(row=3, column=1, sticky="ew", padx=(10, 0))
        tab_to.columnconfigure(0, weight=1)
        tab_to.columnconfigure(1, weight=1)

        ttk.Label(tab_de, text="output_path").grid(row=0, column=0, sticky="w")
        ttk.Entry(tab_de, textvariable=self._de_out_path_var).grid(row=1, column=0, sticky="ew")
        ttk.Label(tab_de, text="report_path").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(tab_de, textvariable=self._de_report_path_var).grid(row=3, column=0, sticky="ew")
        tab_de.columnconfigure(0, weight=1)

        ttk.Label(tab_pt, text="fee_bps").grid(row=0, column=0, sticky="w")
        ttk.Entry(tab_pt, textvariable=self._pt_fee_bps_var).grid(row=1, column=0, sticky="ew")
        ttk.Label(tab_pt, text="slippage_bps").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Entry(tab_pt, textvariable=self._pt_slip_bps_var).grid(row=1, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(tab_pt, text="lookback").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(tab_pt, textvariable=self._pt_lookback_var).grid(row=3, column=0, sticky="ew")
        ttk.Label(tab_pt, text="enforce_trade_validity (true/false)").grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        ttk.Entry(tab_pt, textvariable=self._pt_enforce_tv_var).grid(row=3, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(tab_pt, text="position_mode (risk_scaled/sign)").grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(tab_pt, textvariable=self._pt_pos_mode_var).grid(row=5, column=0, sticky="ew")
        ttk.Label(tab_pt, text="max_leverage").grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        ttk.Entry(tab_pt, textvariable=self._pt_max_lev_var).grid(row=5, column=1, sticky="ew", padx=(10, 0))
        tab_pt.columnconfigure(0, weight=1)
        tab_pt.columnconfigure(1, weight=1)

        outfrm = ttk.Frame(frm)
        outfrm.pack(fill="both", expand=True)

        self.out = tk.Text(outfrm, wrap="none")
        self.out.pack(fill="both", expand=True)

    def _set_output(self, obj) -> None:
        self.out.delete("1.0", tk.END)
        self.out.insert("1.0", json.dumps(_to_jsonable(obj), ensure_ascii=False, indent=2))

    def _parse_inputs(self) -> list[str]:
        raw = self._inputs_var.get()
        items = [p.strip() for p in raw.replace("\n", ",").split(",")]
        return [p for p in items if p]

    def _run_in_thread(self, label: str, fn) -> None:
        self._last_action.set(label)

        def runner():
            try:
                res = fn()
                self.root.after(0, lambda: self._set_output(res))
            except Exception as e:
                self.root.after(0, lambda: self._set_output({"ok": False, "error": str(e)}))
            finally:
                self.root.after(0, lambda: self._last_action.set("idle"))

        threading.Thread(target=runner, daemon=True).start()

    def _run_train_offline(self) -> None:
        def fn():
            paths = self._parse_inputs()
            model_id = self._model_id_var.get().strip()
            alpha = float(self._to_alpha_var.get())
            train_frac = float(self._to_train_frac_var.get())
            val_frac = float(self._to_val_frac_var.get())
            target_col = self._to_target_var.get().strip()
            return train_offline(
                paths,
                target_col=target_col,
                alpha=alpha,
                train_frac=train_frac,
                val_frac=val_frac,
                model_id=model_id if model_id else None,
            )

        self._run_in_thread("train-offline", fn)

    def _run_decision_engine(self) -> None:
        def fn():
            paths = self._parse_inputs()
            model_id = self._model_id_var.get().strip()
            if not model_id:
                raise ValueError("model_id is required")
            return run_decision_engine(
                paths,
                model_id=model_id,
                output_path=self._de_out_path_var.get().strip(),
                report_path=self._de_report_path_var.get().strip(),
            )

        self._run_in_thread("run-decision-engine", fn)

    def _run_paper_trade_once(self) -> None:
        def fn():
            paths = self._parse_inputs()
            model_id = self._model_id_var.get().strip()
            if not model_id:
                raise ValueError("model_id is required")

            enforce_tv = self._pt_enforce_tv_var.get().strip().lower() == "true"
            return paper_trade_once(
                paths,
                model_id=model_id,
                fee_bps=float(self._pt_fee_bps_var.get()),
                slippage_bps=float(self._pt_slip_bps_var.get()),
                lookback=int(self._pt_lookback_var.get()),
                enforce_trade_validity=enforce_tv,
                position_mode=self._pt_pos_mode_var.get().strip(),
                max_leverage=float(self._pt_max_lev_var.get()),
            )

        self._run_in_thread("paper-trade-once", fn)

    def _reset_paper_state(self) -> None:
        def fn():
            save_state(Path("ai_data") / "paper" / "state.json", PaperState.default())
            return {"ok": True, "state_path": "ai_data/paper/state.json"}

        self._run_in_thread("reset-paper-state", fn)

    def run(self) -> None:
        self.root.mainloop()


def _run_textual_tui(config_path: str) -> None:
    from textual.app import App as TextualApp
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Button, Footer, Header, Input, Label, TextArea

    class TraderTUI(TextualApp):
        CSS = """
        Screen { padding: 1; }
        #top { height: auto; }
        #out { height: 1fr; }
        """

        def compose(self):
            yield Header()
            with Vertical(id="top"):
                yield Label(f"config_path: {config_path}")
                yield Label("inputs")
                yield Input(value="ai_data/my_datasets/sample_targets.parquet", id="inputs")
                yield Label("model_id")
                yield Input(value="", id="model_id")
                with Horizontal():
                    yield Button("train-offline", id="btn_to")
                    yield Button("run-decision-engine", id="btn_de")
                    yield Button("paper-trade-once", id="btn_pt")
                    yield Button("reset paper state", id="btn_reset")
            yield TextArea("{}", id="out")
            yield Footer()

        def _set_out(self, obj) -> None:
            ta = self.query_one("#out", TextArea)
            ta.load_text(json.dumps(_to_jsonable(obj), ensure_ascii=False, indent=2))

        def _parse_inputs(self) -> list[str]:
            raw = self.query_one("#inputs", Input).value
            items = [p.strip() for p in raw.replace("\n", ",").split(",")]
            return [p for p in items if p]

        def _model_id(self) -> str:
            return self.query_one("#model_id", Input).value.strip()

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            bid = event.button.id
            if bid is None:
                return

            def work():
                if bid == "btn_to":
                    return train_offline(self._parse_inputs(), target_col="future_log_return", alpha=1.0)
                if bid == "btn_de":
                    mid = self._model_id()
                    if not mid:
                        raise ValueError("model_id is required")
                    return run_decision_engine(
                        self._parse_inputs(),
                        model_id=mid,
                        output_path="ai_data/reports/decision_engine_out.parquet",
                        report_path="ai_data/reports/decision_engine_report.json",
                    )
                if bid == "btn_pt":
                    mid = self._model_id()
                    if not mid:
                        raise ValueError("model_id is required")
                    return paper_trade_once(
                        self._parse_inputs(),
                        model_id=mid,
                        enforce_trade_validity=False,
                        position_mode="sign",
                        max_leverage=1.0,
                    )
                if bid == "btn_reset":
                    save_state(Path("ai_data") / "paper" / "state.json", PaperState.default())
                    return {"ok": True, "state_path": "ai_data/paper/state.json"}
                return {"ok": False, "error": f"unknown action {bid}"}

            try:
                res = await self.run_worker(work, thread=True)
                self._set_out(res)
            except Exception as e:
                self._set_out({"ok": False, "error": str(e)})

    TraderTUI().run()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        cfg = load_config(args.config)
        logger = setup_logger(cfg)
        logger.info("GUI launcher started. env=%s", cfg.env)

        if _HAS_TK:
            App(config_path=args.config).run()
        else:
            logger.warning("tkinter is not available; falling back to Textual TUI")
            _run_textual_tui(args.config)

        return 0
    except BinanceAITraderError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
