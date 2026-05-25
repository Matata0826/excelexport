"""步骤4：到期天数计算 — today - 出单日期。"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import CleaningStep, register_step


@register_step("calc_due_days", order=4)
class CalcDueDays(CleaningStep):
    """计算 到期天数 = reference_date - 出单日期。"""

    def execute(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        date_col = "出单日期"
        if date_col not in df.columns:
            df["到期天数"] = 0
            return df

        ref_str = config.get("due_days", {}).get("reference_date", "today")
        if ref_str == "today":
            ref_date = pd.Timestamp.now().normalize()
        else:
            ref_date = pd.Timestamp(ref_str)

        df["到期天数"] = (ref_date - df[date_col]).dt.days
        return df
