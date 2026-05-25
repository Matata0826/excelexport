"""步骤2：空值/异常值处理 — 金额列转numeric、日期列转datetime。"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import CleaningStep, register_step


@register_step("clean_invalid", order=2)
class CleanInvalid(CleaningStep):
    """处理金额和日期列的异常值。

    金额：pd.to_numeric(..., errors='coerce')，配置决定是否删除 NaN 行。
    日期：pd.to_datetime(..., errors='coerce')，配置决定格式。
    """

    def execute(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        cleaning_cfg = config.get("cleaning", {})

        # 金额列清洗
        if "金额" in df.columns:
            strat = cleaning_cfg.get("amount", {}).get("strategy", "coerce")
            if strat == "coerce":
                df["金额"] = pd.to_numeric(df["金额"], errors="coerce")
            if cleaning_cfg.get("amount", {}).get("remove_nulls", True):
                df = df[df["金额"].notna()].copy()

        # 日期列清洗（出单日期）
        if "出单日期" in df.columns:
            date_cfg = cleaning_cfg.get("date", {})
            fmt = date_cfg.get("date_format", None)
            df["出单日期"] = pd.to_datetime(df["出单日期"], format=fmt, errors="coerce")

        # 全局空行处理
        if cleaning_cfg.get("global", {}).get("drop_all_null", False):
            df = df.dropna(how="all")

        return df.reset_index(drop=True)
