"""看板组件：指标卡、Plotly图表、明细表。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st


def render_metric_cards(
    unwritten: int,
    card_configs: List[Dict[str, str]],
) -> None:
    """渲染汇总指标卡 — 默认仅展示「未回销总件数」。"""
    cols = st.columns(len(card_configs))
    for i, card_cfg in enumerate(card_configs):
        key = card_cfg["key"]
        label = card_cfg["label"]
        fmt = card_cfg.get("format", "number")

        if key == "unwritten_count":
            display = f"{unwritten:,}"
        else:
            display = "—"

        with cols[i]:
            st.metric(label=label, value=display)


def render_due_distribution_chart(
    df: pd.DataFrame,
    buckets: List[tuple[str, int, int]],
    chart_config: Dict[str, Any],
) -> None:
    """渲染未回销件数分布柱状图（按出单日期计算的到期天数分组）。

    Args:
        df: 全部数据（默认均为未回销）
        buckets: [(label, min, max), ...] 分组定义
        chart_config: config['dashboard']['chart']
    """
    if df.empty or "到期天数" not in df.columns:
        st.info("暂无数据")
        return

    def _bucket_label(days: float) -> str:
        for label, lo, hi in buckets:
            if lo <= days <= hi:
                return label
        return buckets[-1][0] if buckets else "未知"

    plot_df = df.copy()
    plot_df["到期分组"] = plot_df["到期天数"].apply(_bucket_label)

    if "业务员" in plot_df.columns:
        agg = plot_df.groupby(["到期分组", "业务员"]).size().reset_index(name="件数")
        color_col = "业务员"
    else:
        agg = plot_df.groupby("到期分组").size().reset_index(name="件数")
        color_col = None

    bucket_order = [b[0] for b in buckets]
    agg["到期分组"] = pd.Categorical(agg["到期分组"], categories=bucket_order, ordered=True)
    agg = agg.sort_values("到期分组")

    fig = px.bar(
        agg,
        x="到期分组",
        y="件数",
        color=color_col,
        title=chart_config.get("title", "未回销件数分布"),
        color_discrete_sequence=chart_config.get("color_sequence"),
        barmode="group" if color_col else "relative",
    )
    fig.update_layout(
        xaxis_title=chart_config.get("x_label", "到期天数区间"),
        yaxis_title=chart_config.get("y_label", "未回销件数"),
        legend_title_text="业务员" if color_col else None,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_detail_table(df: pd.DataFrame) -> None:
    """渲染未回销明细表（全部数据均为未回销）。"""
    if df.empty:
        st.info("暂无数据")
        return

    display_cols = [c for c in ["单号", "主号机构", "主号业务员", "业务员", "金额", "出单日期", "到期天数"] if c in df.columns]
    st.dataframe(
        df[display_cols].sort_values("到期天数", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
