from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl(path: Path, *, limit: int | None = None) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if limit is not None:
        lines = lines[-int(max(1, limit)) :]
    out: list[dict] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def _to_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns and "ts" not in df.columns:
        df["ts"] = df["timestamp"]
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df


def _compute_drawdown(equity: pd.Series) -> pd.Series:
    if equity.empty:
        return equity
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    return dd


def render_paper_dashboard(
    *,
    paper_root: Path = Path("ai_data") / "paper",
    max_rows: int = 10000,
    show_last_trades: int = 50,
) -> None:
    root = Path(paper_root)
    if root.name == "paper":
        sess = _read_json(root / "session.json")
        try:
            sdir = sess.get("params", {}).get("session_dir") if isinstance(sess, dict) else None
        except Exception:
            sdir = None
        if sdir:
            root = Path(str(sdir))

    state_path = Path(root) / "state.json"
    metrics_path = Path(root) / "metrics.jsonl"
    trades_path = Path(root) / "trades.jsonl"

    st.caption(f"Reading: `{state_path}`, `{metrics_path}`, `{trades_path}`")

    state = _read_json(state_path) or {}
    metrics_rows = _read_jsonl(metrics_path, limit=int(max_rows))
    trades_rows = _read_jsonl(trades_path, limit=int(max_rows))

    mdf = _to_df(metrics_rows)
    tdf = _to_df(trades_rows)

    cash = float(state.get("cash", 0.0))
    pos_units = float(state.get("position_units", 0.0))
    fees = float(state.get("fees_paid", 0.0))

    last_mid = None
    if not mdf.empty and "price" in mdf.columns:
        try:
            last_mid = float(pd.to_numeric(mdf["price"], errors="coerce").dropna().iloc[-1])
        except Exception:
            last_mid = None
    elif not mdf.empty and "mid" in mdf.columns:
        try:
            last_mid = float(pd.to_numeric(mdf["mid"], errors="coerce").dropna().iloc[-1])
        except Exception:
            last_mid = None

    equity_now = None
    if last_mid is not None:
        equity_now = float(cash + pos_units * last_mid)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cash", f"{cash:,.2f}")
    c2.metric("Position (units)", f"{pos_units:,.6f}")
    c3.metric("Fees paid", f"{fees:,.2f}")
    c4.metric("Last mid", "—" if last_mid is None else f"{last_mid:,.2f}")
    c5.metric("Equity", "—" if equity_now is None else f"{equity_now:,.2f}")

    if mdf.empty:
        st.warning("No metrics yet. Run: `main.py paper-trade ...` to generate ai_data/paper/metrics.jsonl")
        return

    if "equity" in mdf.columns:
        mdf["equity"] = pd.to_numeric(mdf["equity"], errors="coerce")
    if "balance" in mdf.columns:
        mdf["balance"] = pd.to_numeric(mdf["balance"], errors="coerce")
    if "target_position" in mdf.columns:
        mdf["target_position"] = pd.to_numeric(mdf["target_position"], errors="coerce")
    if "confidence" in mdf.columns:
        mdf["confidence"] = pd.to_numeric(mdf["confidence"], errors="coerce")
    if "drawdown" in mdf.columns:
        mdf["drawdown"] = pd.to_numeric(mdf["drawdown"], errors="coerce")

    equity_series = mdf["equity"].dropna() if "equity" in mdf.columns else pd.Series(dtype="float64")
    if "drawdown" in mdf.columns and not mdf["drawdown"].dropna().empty:
        dd = mdf.set_index("ts")["drawdown"].dropna() if "ts" in mdf.columns else mdf["drawdown"].dropna()
    else:
        dd = _compute_drawdown(equity_series) if not equity_series.empty else pd.Series(dtype="float64")

    pnl = None
    if not equity_series.empty:
        pnl = float(equity_series.iloc[-1] - equity_series.iloc[0])

    left, right = st.columns(2)

    with left:
        st.subheader("Equity")
        if pnl is not None:
            st.caption(f"PnL (window): {pnl:,.2f}")
        chart_df = mdf[[c for c in ["ts", "equity", "balance"] if c in mdf.columns]].copy()
        if "ts" in chart_df.columns:
            chart_df = chart_df.set_index("ts")
        st.line_chart(chart_df[[c for c in ["equity", "balance"] if c in chart_df.columns]])

    with right:
        st.subheader("Drawdown")
        if not dd.empty:
            dd_df = dd.to_frame(name="drawdown")
            st.line_chart(dd_df)
            st.caption(f"Max drawdown: {float(dd.min()):.2%}")
        else:
            st.caption("Drawdown unavailable")

    st.subheader("Confidence")
    if "confidence" in mdf.columns:
        conf_df = mdf[[c for c in ["ts", "confidence"] if c in mdf.columns]].copy()
        if "ts" in conf_df.columns:
            conf_df = conf_df.set_index("ts")
        st.line_chart(conf_df)

    st.subheader("Recent trades/events")
    if tdf.empty:
        st.caption("No trades.jsonl entries yet.")
    else:
        view = tdf.tail(int(show_last_trades)).copy()
        if "timestamp" in view.columns and "ts" not in view.columns:
            view["ts"] = view["timestamp"]
        if "ts" in view.columns:
            view["ts"] = pd.to_datetime(view["ts"], utc=True, errors="coerce")
        cols = [
            c
            for c in [
                "trade_id",
                "ts",
                "pair",
                "side",
                "entry_price",
                "exit_price",
                "size",
                "pnl",
            ]
            if c in view.columns
        ]
        if not cols:
            cols = [c for c in ["ts", "mid", "target_position", "executed", "equity", "pre_ok", "post_ok"] if c in view.columns]
        st.dataframe(view[cols], use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Paper Trading Dashboard", layout="wide")
    st.title("Paper Trading Dashboard (read-only)")
    render_paper_dashboard()


if __name__ == "__main__":
    main()
