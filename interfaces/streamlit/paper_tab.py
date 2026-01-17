from __future__ import annotations

from pathlib import Path

import streamlit as st

from interfaces.streamlit.paper_dashboard import render_paper_dashboard


def render_paper_tab(*, default_paper_root: Path = Path("ai_data") / "paper") -> None:
    st.subheader("Paper Trading (read-only)")

    with st.sidebar:
        st.header("Paper")
        paper_root_str = st.text_input("Paper data root", value=str(default_paper_root))

        refresh = st.toggle("Auto-refresh", value=False)
        refresh_s = st.number_input("Refresh seconds", min_value=2, max_value=60, value=5, step=1)
        max_rows = st.number_input("Max rows to read", min_value=200, max_value=200000, value=10000, step=200)
        show_last_trades = st.number_input("Last trades to show", min_value=10, max_value=2000, value=50, step=10)

    if refresh:
        st.autorefresh(interval=int(refresh_s) * 1000, key="paper_autorefresh")

    render_paper_dashboard(
        paper_root=Path(paper_root_str),
        max_rows=int(max_rows),
        show_last_trades=int(show_last_trades),
    )
