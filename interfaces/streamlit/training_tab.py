from __future__ import annotations

from pathlib import Path

import streamlit as st

from interfaces.streamlit.loaders import find_tb_runs, load_tb_scalars


def render_training_tab(*, default_log_root: Path = Path("logs") / "training") -> None:
    st.subheader("Training (read-only)")

    with st.sidebar:
        st.header("Training")
        log_root_str = st.text_input("TensorBoard log root", value=str(default_log_root))

    log_root = Path(log_root_str)
    runs = find_tb_runs(log_root)

    if not runs:
        st.warning("No TensorBoard event files found under the selected log root.")
        st.caption("Expected pattern: logs/training/<run_name>/<run_id>/events.out.tfevents*")
        return

    run_labels = [str(r.run_dir) for r in runs]
    selected = st.selectbox("Run", options=run_labels, index=len(run_labels) - 1)
    run = next(r for r in runs if str(r.run_dir) == selected)

    df = load_tb_scalars(run)
    if df.empty:
        st.warning("No scalar tags found in this run.")
        return

    tags = [c for c in df.columns if c != "step"]

    preferred = [
        "train/loss",
        "val/loss",
        "val/f1",
        "val/precision",
        "val/recall",
        "train/lr",
        "train/grad_norm",
        "train/grad_var",
        "train/loss_volatility",
        "val/pred_entropy",
    ]

    default_tags = [t for t in preferred if t in tags]
    selected_tags = st.multiselect("Metrics", options=tags, default=default_tags)

    if not selected_tags:
        st.info("Select at least one metric to plot.")
        return

    plot_df = df[["step", *selected_tags]].set_index("step")
    st.line_chart(plot_df)
