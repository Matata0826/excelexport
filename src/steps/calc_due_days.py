"""步骤4：到期天数计算 — reference_date - 基准日期。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from .base import CleaningStep, register_step


@register_step("calc_due_days", order=4)
class CalcDueDays(CleaningStep):
    """计算 到期天数 = reference_date - 基准日期。

    自动从 base_date_aliases 中匹配第一个存在于 DataFrame 的列，
    匹配成功后重命名为统一内部字段「基准日期」。
    支持通过 base_date_col 参数手动指定。
    """

    def __init__(self) -> None:
        super().__init__()
        self.match_status: str = "pending"
        self.matched_column: str = ""
        self.base_date_aliases: list[str] = []

    def execute(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
        base_date_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """执行到期天数计算。

        Args:
            df: 输入数据
            config: 全局配置
            base_date_col: 手动指定的基准日期列名（优先级高于自动匹配）
        """
        due_cfg: Dict[str, Any] = config.get("due_days", {})
        aliases: list[str] = due_cfg.get("base_date_aliases", ["出单日期"])
        self.base_date_aliases = aliases

        resolved_col: Optional[str] = None

        # ---- 1. 确定基准日期列 ----
        if base_date_col is not None:
            # 手动指定：直接匹配原始列名
            if base_date_col in df.columns:
                resolved_col = base_date_col
                self.match_status = "success"
                self.matched_column = base_date_col
            else:
                # 手动指定的列不存在，回退到自动匹配
                resolved_col = self._auto_match(df, aliases)
        else:
            resolved_col = self._auto_match(df, aliases)

        # ---- 2. 未匹配：记录警告并返回 ----
        if resolved_col is None:
            self.match_status = "failed"
            self.matched_column = ""
            df["到期天数"] = 0
            return df

        # ---- 3. 重命名为统一内部字段 ----
        if resolved_col != "基准日期":
            df = df.rename(columns={resolved_col: "基准日期"})

        # ---- 4. 确保 datetime 类型 ----
        if not pd.api.types.is_datetime64_any_dtype(df["基准日期"]):
            df["基准日期"] = pd.to_datetime(df["基准日期"], errors="coerce")

        # ---- 5. 计算参考日期 ----
        ref_str = due_cfg.get("reference_date", "today")
        if ref_str == "today":
            ref_date = pd.Timestamp.now().normalize()
        else:
            ref_date = pd.Timestamp(ref_str)

        # ---- 6. 计算到期天数 ----
        delta = ref_date - df["基准日期"]
        df["到期天数"] = delta.dt.days.fillna(0).astype(int)

        return df

    # ------------------------------------------------------------------
    #  internal helpers
    # ------------------------------------------------------------------

    def _auto_match(self, df: pd.DataFrame, aliases: list[str]) -> Optional[str]:
        """遍历别名列表，返回第一个匹配的 DataFrame 列名（忽略大小写与空格）。"""
        df_cols_normalized: dict[str, str] = {
            str(c).strip().lower(): c for c in df.columns
        }
        for alias in aliases:
            key = alias.strip().lower()
            if key in df_cols_normalized:
                col = df_cols_normalized[key]
                self.match_status = "success"
                self.matched_column = col
                return col
        return None
