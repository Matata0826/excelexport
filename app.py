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

    filename: str = uploaded_file.name.lower() if hasattr(uploaded_file, "name") else ""

    if filename.endswith(".xls"):
        engine = "xlrd"
    else:
        engine = "openpyxl"

    try:
        return pd.read_excel(uploaded_file, engine=engine)
    except Exception as e:
        st.error(f"Excel 文件读取失败：{e}\n请检查文件是否损坏、加密或格式不正确。")
        return None


def run_pipeline(
    raw_df: pd.DataFrame,
    mapping_df: Optional[pd.DataFrame],
    base_date_col: Optional[str] = None,
) -> tuple[pd.DataFrame, dict]:
    """执行清洗管道，返回 (cleaned_df, match_info)。

    match_info = {"status": "success"|"failed"|"pending", "matched_column": str}
    """
    pipeline = Pipeline(config, audit)
    df = pipeline.run(raw_df, mapping_df=mapping_df, base_date_col=base_date_col)
    match_info: dict = {
        "status": getattr(pipeline, "_due_days_match_status", "pending"),
        "matched_column": getattr(pipeline, "_due_days_matched_column", ""),
    }
    return df, match_info


def _get_institutions(df: pd.DataFrame) -> list[str]:
    """从清洗后数据中提取机构列表（去重+排序）。"""
    if "主号机构" not in df.columns:
        return []
    vals = df["主号机构"].dropna().astype(str).str.strip()
    return sorted(v for v in vals.unique() if v)


def _get_salespeople_for_institution(df: pd.DataFrame, institution: str) -> list[str]:
    """获取指定机构下的业务员列表。institution="" 表示全部。"""
    if "业务员" not in df.columns:
        return []
    if not institution:
        return sorted(df["业务员"].dropna().astype(str).str.strip().unique().tolist())
    mask = df["主号机构"].astype(str).str.strip() == institution
    return sorted(df.loc[mask, "业务员"].dropna().astype(str).str.strip().unique().tolist())


def _get_date_columns(df: pd.DataFrame) -> list[str]:
    """返回 DataFrame 中所有日期/时间类型的列名，用于手动选择基准日期列。"""
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if not date_cols:
        # 回退：返回所有列
        date_cols = list(df.columns)
    return date_cols


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

    # -- 机构 & 业务员级联筛选 --
    all_institutions: list[str] = []
    all_salespeople: list[str] = []

    if "cleaned_df" in st.session_state and st.session_state.cleaned_df is not None:
        df = st.session_state.cleaned_df
        all_institutions = _get_institutions(df)
        all_salespeople = sorted(df["业务员"].dropna().astype(str).str.strip().unique().tolist()) if "业务员" in df.columns else []

    # 机构下拉
    institution_options = ["全部机构"] + all_institutions
    # 保持上次选值（若仍在选项中）
    prev_inst = st.session_state.get("_selected_institution", "全部机构")
    inst_default = prev_inst if prev_inst in institution_options else "全部机构"
    selected_institution = st.selectbox(
        "🏢 所属机构",
        options=institution_options,
        index=institution_options.index(inst_default),
        key="institution_selector",
    )
    st.session_state["_selected_institution"] = selected_institution

    # 级联：按机构过滤业务员列表
    if selected_institution == "全部机构":
        available_people = all_salespeople
    else:
        available_people = _get_salespeople_for_institution(
            st.session_state.cleaned_df, selected_institution,
        )

    # 清理上次多选中已不在可用列表中的选项
    prev_selected = st.session_state.get("_selected_people", [])
    valid_prev = [p for p in prev_selected if p in available_people]

    selected_people = st.multiselect(
        "🔍 业务员筛选",
        options=available_people,
        default=valid_prev if valid_prev else available_people,
        placeholder="选择业务员（默认全选）",
        key="people_multiselect",
    )
    st.session_state["_selected_people"] = selected_people

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
                    # 缓存原始数据供后续手动重跑使用
                    st.session_state["_raw_df"] = raw_df

                    mapping_df = None
                    if mapping_file is not None:
                        mapping_df = read_uploaded_excel(mapping_file)
                    st.session_state["_mapping_df"] = mapping_df

                    # 清除上次手动选择的基准日期列（新文件可能有不同的列名）
                    st.session_state.pop("_base_date_column", None)

                    cleaned, match_info = run_pipeline(
                        raw_df, mapping_df,
                        base_date_col=st.session_state.get("_base_date_column"),
                    )
                    st.session_state.cleaned_df = cleaned
                    st.session_state["_base_date_match_info"] = match_info

                    audit.info(f"清洗完成，总件数: {len(cleaned)}（全部视为未回销）")
                    st.success(f"清洗完成！共 {len(cleaned)} 条未回销记录")
                    st.rerun()

    # -- 基准日期列自动识别结果提示 --
    match_info = st.session_state.get("_base_date_match_info", {})
    if match_info.get("status") == "success":
        matched_col = match_info.get("matched_column", "")
        st.success(f"✓ 已自动识别基准日期列：{matched_col}")

    # -- 基准日期列手动兜底（自动匹配失败时显示）--
    if match_info.get("status") == "failed":
        st.divider()
        st.warning("⚠️ 未自动识别到基准日期列")

        raw_df: Optional[pd.DataFrame] = st.session_state.get("_raw_df")

        if raw_df is not None and not raw_df.empty:
            date_cols = _get_date_columns(raw_df)

            manual_col = st.selectbox(
                "请手动选择基准日期列：",
                options=date_cols,
                key="manual_date_col_selector",
                help="自动识别失败，请手动选择用于计算到期天数的日期列",
            )
            st.session_state["_base_date_column"] = manual_col

            if st.button("🔄 重新执行清洗", type="primary", use_container_width=True):
                with st.spinner("正在使用手动指定的日期列重新清洗..."):
                    mapping_df = st.session_state.get("_mapping_df")
                    cleaned, match_info = run_pipeline(
                        raw_df, mapping_df,
                        base_date_col=manual_col,
                    )
                    st.session_state.cleaned_df = cleaned
                    st.session_state["_base_date_match_info"] = match_info
                    st.rerun()

    # -- 导出 --
    if "cleaned_df" in st.session_state and st.session_state.cleaned_df is not None:
        st.divider()
        st.subheader("📥 导出清单")

        df = st.session_state.cleaned_df
        selected_for_export = selected_people if selected_people else available_people

        # 按钮 A：导出已选业务员（一人一表 + zip）
        if selected_for_export:
            export_label = (
                f"一键导出 {len(selected_for_export)} 人"
                if len(selected_for_export) > 1
                else f"导出 {selected_for_export[0]}"
            )
            if st.button(f"📦 {export_label}", type="secondary", use_container_width=True):
                try:
                    with st.spinner(f"正在导出 {len(selected_for_export)} 位业务员..."):
                        zip_path, filepaths = export_batch(df, config, selected_for_export)

                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ 下载批量 zip（{len(filepaths)} 个文件）",
                            data=f,
                            file_name=Path(zip_path).name,
                            mime="application/zip",
                            use_container_width=True,
                        )
                    st.success(f"导出完成，共生成 {len(filepaths)} 个文件：")
                    for fp in filepaths:
                        st.caption(f"  • `{fp}`")

                except ValueError as e:
                    st.warning(str(e))
        else:
            st.info("当前筛选下无业务员可导出")

        # 按钮 B：导出该机构全部业务员（仅当选中具体机构时显示）
        if selected_institution != "全部机构":
            inst_people = _get_salespeople_for_institution(df, selected_institution)
            if inst_people:
                if st.button(f"🏢 导出「{selected_institution}」全部 {len(inst_people)} 人", use_container_width=True):
                    try:
                        with st.spinner(f"正在导出「{selected_institution}」..."):
                            zip_path, filepaths = export_batch(df, config, inst_people)

                        with open(zip_path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ 下载 {selected_institution} zip（{len(filepaths)} 个文件）",
                                data=f,
                                file_name=Path(zip_path).name,
                                mime="application/zip",
                                use_container_width=True,
                            )
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

    # 多级筛选：机构 → 业务员
    if selected_institution != "全部机构" and "主号机构" in df.columns:
        df_filtered = df[df["主号机构"].astype(str).str.strip() == selected_institution]
    else:
        df_filtered = df

    if selected_people and "业务员" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["业务员"].isin(selected_people)]

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
