"""Streamlit 主入口：业务数据清洗与未回销看板。

Usage:
    cd ~/Desktop/CC\ Project
    python3 -m streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from src.config_loader import get_bucket_boundaries, load_config
from src.audit import AuditLogger
from src.pipeline import Pipeline
from src.dashboard import render_detail_table, render_due_distribution_chart, render_metric_cards
from src.exporter import export_batch

# ---- 页面配置 ----
st.set_page_config(page_title="业务数据清洗与未回销看板", page_icon="📊", layout="wide")

# ---- 加载配置 ----
CONFIG_PATH = Path(__file__).parent / "config.yaml"

if "config" not in st.session_state:
    st.session_state.config = load_config(str(CONFIG_PATH))

if "audit" not in st.session_state:
    st.session_state.audit = AuditLogger(st.session_state.config)

config = st.session_state.config
audit: AuditLogger = st.session_state.audit


# ---- 辅助函数 ----
@st.cache_data(show_spinner=False)
def read_uploaded_excel(uploaded_file) -> Optional[pd.DataFrame]:
    if uploaded_file is None:
        return None
    return pd.read_excel(uploaded_file)


def run_pipeline(
    raw_df: pd.DataFrame,
    mapping_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    pipeline = Pipeline(config, audit)
    return pipeline.run(raw_df, mapping_df=mapping_df)


# ---- 侧边栏 ----
dash_cfg = config.get("dashboard", {})
with st.sidebar:
    st.title(dash_cfg.get("sidebar_title", "控制面板"))

    st.subheader("📤 数据上传")
    raw_file = st.file_uploader(
        "上传业务数据 Excel",
        type=["xlsx", "xls"],
        key="raw_file",
        help="原始业务数据（默认全部视为未回销清单），列名自动识别",
    )
    mapping_file = st.file_uploader(
        "上传主号映射模板 Excel",
        type=["xlsx", "xls"],
        key="mapping_file",
        help="A列：主号机构 | B列：主号业务员 | C列：原始业务员名称",
    )

    st.divider()

    with st.expander("📋 运行状态与日志", expanded=False):
        st.text_area(
            "审计日志",
            value=audit.summary(),
            height=200,
            label_visibility="collapsed",
            disabled=True,
        )

    st.divider()

    # -- 业务员筛选 --
    all_salespeople: list[str] = []
    if "cleaned_df" in st.session_state and st.session_state.cleaned_df is not None:
        df = st.session_state.cleaned_df
        if "业务员" in df.columns:
            all_salespeople = sorted(df["业务员"].dropna().unique().tolist())

    selected_people = st.multiselect(
        "🔍 业务员筛选",
        options=all_salespeople,
        default=all_salespeople,
        placeholder="选择业务员（默认全选）",
    )

    st.divider()

    # -- 触发清洗 --
    if st.button("🚀 执行清洗", type="primary", use_container_width=True):
        if raw_file is None:
            st.error("请先上传业务数据 Excel")
        else:
            with st.spinner("正在执行清洗管道..."):
                raw_df = read_uploaded_excel(raw_file)
                if raw_df is None:
                    st.error("无法读取上传文件")
                else:
                    mapping_df = None
                    if mapping_file is not None:
                        mapping_df = read_uploaded_excel(mapping_file)

                    cleaned = run_pipeline(raw_df, mapping_df)
                    st.session_state.cleaned_df = cleaned
                    audit.info(f"清洗完成，总件数: {len(cleaned)}（全部视为未回销）")
                    st.success(f"清洗完成！共 {len(cleaned)} 条未回销记录")
                    st.rerun()

    # -- 导出 --
    if "cleaned_df" in st.session_state and st.session_state.cleaned_df is not None:
        st.divider()
        st.subheader("📥 导出清单")

        df = st.session_state.cleaned_df
        selected_for_export = selected_people if selected_people else all_salespeople

        if not selected_for_export:
            st.info("暂无可导出的业务员")
        else:
            export_label = (
                f"一键导出 {len(selected_for_export)} 人"
                if len(selected_for_export) > 1
                else f"导出 {selected_for_export[0]}"
            )

            if st.button(f"📦 {export_label}", type="secondary", use_container_width=True):
                try:
                    with st.spinner(f"正在导出 {len(selected_for_export)} 位业务员..."):
                        zip_path, filepaths = export_batch(
                            df, config, selected_for_export,
                        )

                    # 提供 zip 一键下载
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ 下载批量 zip（{len(filepaths)} 个文件）",
                            data=f,
                            file_name=Path(zip_path).name,
                            mime="application/zip",
                            use_container_width=True,
                        )

                    # 列出全部导出文件路径
                    st.success(f"导出完成，共生成 {len(filepaths)} 个文件：")
                    for fp in filepaths:
                        st.caption(f"  • `{fp}`")

                except ValueError as e:
                    st.warning(str(e))

# ---- 主区域 ----
st.title(dash_cfg.get("page_title", "业务数据清洗与未回销看板"))

if "cleaned_df" not in st.session_state or st.session_state.cleaned_df is None:
    st.info("👈 请从左侧上传数据并点击「执行清洗」")
else:
    df: pd.DataFrame = st.session_state.cleaned_df

    if selected_people and "业务员" in df.columns:
        df_filtered = df[df["业务员"].isin(selected_people)]
    else:
        df_filtered = df

    unwritten_count = len(df_filtered)

    st.subheader("📊 汇总指标")
    card_configs = dash_cfg.get("metric_cards", [])
    render_metric_cards(unwritten_count, card_configs)

    st.divider()

    st.subheader("📈 未回销分布")
    buckets = get_bucket_boundaries(config)
    chart_config = dash_cfg.get("chart", {})
    render_due_distribution_chart(df_filtered, buckets, chart_config)

    st.divider()

    st.subheader("📋 未回销明细")
    render_detail_table(df_filtered)
