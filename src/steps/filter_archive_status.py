"""步骤2：归档状态识别与过滤 — 区分「全量数据」与「纯未归档数据」。

读取 Excel 后自动扫描表头，定位归档状态列；若该列含「已归档/已完成」等值，
判定为全量数据并过滤掉已归档行；否则判定为纯未归档数据，保留全部行。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .base import CleaningStep, register_step


def _normalize(value: Any) -> str:
    """归一化单个值：空值→空串，其余去空格并转小写。"""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _find_status_column(
    df: pd.DataFrame,
    aliases: List[str],
    keywords: List[str],
    exclude_keywords: Optional[List[str]] = None,
) -> Optional[str]:
    """定位状态列：先按别名精确匹配，再按表头关键字模糊匹配。

    关键字按配置列表顺序赋予优先级（越靠前越优先）。
    模糊匹配时跳过日期/时间等无关列（如「归档时间」）；
    「是否」为弱关键字，须与「归档/回销/状态」共现，避免误匹配「是否借出」。
    """
    normalized: Dict[str, str] = {str(c).strip().lower(): c for c in df.columns}

    # 1. 别名精确匹配（忽略大小写与首尾空格）
    for alias in aliases:
        key = str(alias).strip().lower()
        if key and key in normalized:
            return normalized[key]

    # 2. 关键字模糊匹配（按关键字优先级遍历，列名包含任一关键字即命中）
    exclude = [str(k).strip().lower() for k in (exclude_keywords or []) if str(k).strip()]
    for kw in keywords:
        key = str(kw).strip().lower()
        if not key:
            continue
        for col in df.columns:
            col_key = str(col).strip().lower()
            # 跳过日期/时间等无关列
            if any(e in col_key for e in exclude):
                continue
            # 「是否」为弱关键字：须与「归档/回销/状态」共现
            if key == "是否" and not any(s in col_key for s in ("归档", "回销", "状态")):
                continue
            if key in col_key:
                return col

    return None


def detect_and_filter_archive_status(
    df: pd.DataFrame,
    config: Dict[str, Any],
    force_unarchived: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """智能识别归档状态并过滤已归档件（纯函数，可独立复用）。

    识别逻辑：
    - 找到状态列且含 archived_values 中的值 → 「全量数据」，过滤掉已归档行。
    - 未找到状态列 / 状态列无已归档值 / force_unarchived=True → 「纯未归档数据」，保留全部行。

    Args:
        df: 原始数据
        config: 全局配置（读取 config['archive_status']）
        force_unarchived: 强制视为纯未归档数据（跳过状态筛选）

    Returns:
        (过滤后的 DataFrame, 识别结果 dict)，结果含 data_type 标识：
        - "full": 全量数据（已过滤已归档行）
        - "pure_unarchived": 纯未归档数据（保留全部行）
    """
    cfg = config.get("archive_status", {}) or {}
    aliases = cfg.get("column_aliases") or ["归档状态", "是否归档", "状态", "Status"]
    keywords = cfg.get("column_keywords") or ["归档", "状态", "是否"]
    exclude_keywords = cfg.get("column_exclude_keywords") or ["时间", "日期", "date", "time", "月份"]
    keep_values = cfg.get("keep_values") or ["未归档", "归档不齐"]
    archived_values = cfg.get("archived_values") or ["归档齐全", "已归档", "已完成"]

    keep_set = {_normalize(v) for v in keep_values}
    archived_set = {_normalize(v) for v in archived_values}

    total = len(df)
    status_col = _find_status_column(df, aliases, keywords, exclude_keywords)

    result: Dict[str, Any] = {
        "data_type": "pure_unarchived",
        "status_column": status_col or "",
        "has_status_column": status_col is not None,
        "force_unarchived": bool(force_unarchived),
        "total": total,
        "kept": total,
        "filtered": 0,
        "unarchived_count": 0,
        "archived_values_found": [],
    }

    # 强制覆盖 / 未找到状态列 → 保留全部
    if force_unarchived or status_col is None:
        return df, result

    # 向量化归一化状态列，避免逐行 apply
    values = df[status_col].fillna("").astype(str).str.strip().str.lower()
    is_archived = values.isin(archived_set)
    is_unarchived = values.isin(keep_set)
    found = sorted({v for v in values[is_archived].unique() if v})

    result["unarchived_count"] = int(is_unarchived.sum())

    if is_archived.any():
        result["data_type"] = "full"
        result["archived_values_found"] = found
        result["filtered"] = int(is_archived.sum())
        df = df.loc[~is_archived].reset_index(drop=True)
        result["kept"] = len(df)
    else:
        result["data_type"] = "pure_unarchived"

    return df, result


@register_step("filter_archive_status", order=2)
class FilterArchiveStatus(CleaningStep):
    """归档状态识别与过滤步骤（在列名标准化后、异常值处理前执行）。"""

    def __init__(self) -> None:
        super().__init__()
        self.data_type: str = "pure_unarchived"
        self.result: Dict[str, Any] = {}

    def execute(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
        force_unarchived: bool = False,
    ) -> pd.DataFrame:
        df, result = detect_and_filter_archive_status(df, config, force_unarchived)
        self.result = result
        self.data_type = result["data_type"]
        return df
