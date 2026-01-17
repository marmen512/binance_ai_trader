from __future__ import annotations

import streamlit as st

from interfaces.streamlit.paper_tab import render_paper_tab
from interfaces.streamlit.training_tab import render_training_tab


def main() -> None:
    st.set_page_config(page_title="Binance AI Trader", layout="wide")
    st.title("Binance AI Trader (read-only)")

    tab_training, tab_paper = st.tabs(["Training", "Paper Trading"])

    with tab_training:
        render_training_tab()

    with tab_paper:
        render_paper_tab()


if __name__ == "__main__":
    main()
