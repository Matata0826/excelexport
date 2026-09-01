"""清洗管道引擎：按注册顺序串联执行所有清洗步骤。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from .audit import AuditLogger
from .steps import NormalizeColumns, CleanInvalid, ApplyMapping, CalcDueDays, FilterArchiveStatus  # noqa: F401
from .steps.base import get_steps_sorted


class Pipeline:
    """清洗管道引擎。

    Usage:
        pipeline = Pipeline(config)
        cleaned = pipeline.run(raw_df, mapping_df=mapping_df)
    """

    def __init__(self, config: Dict[str, Any], audit: Optional[AuditLogger] = None) -> None:
        self.config = config
        self.audit = audit

    def run(
        self, df: pd.DataFrame,
        mapping_df: Optional[pd.DataFrame] = None,
        base_date_col: Optional[str] = None,
        force_unarchived: bool = False,
    ) -> pd.DataFrame:
        """执行全部清洗步骤。

        Args:
            df: 原始数据
            mapping_df: 主号映射表（可选）
            base_date_col: 手动指定的基准日期列名（可选，优先级高于自动匹配）
            force_unarchived: 强制视为纯未归档数据（跳过归档状态筛选，可选）

        Returns:
            清洗后的 DataFrame，包含到期天数列
        """
        if df.empty:
            if self.audit:
                self.audit.warning("输入数据为空，跳过清洗")
            return df

        total_before = len(df)
        steps = get_steps_sorted()

        if self.audit:
            self.audit.info(f"初始行数: {total_before}, 步骤数: {len(steps)}")
            self.audit.set_stats(total_rows=total_before)

        for step in steps:
            rows_before = len(df)

            if self.audit:
                self.audit.start_step(step.name)

            if step.name == "apply_mapping":
                df = step.execute(df, self.config, mapping_df=mapping_df)  # type: ignore[call-arg]
                if self.audit and hasattr(step, "_mapping_stats"):
                    ms = step._mapping_stats  # type: ignore[attr-defined]
                    self.audit.record_mapping_result(
                        ms["total"], ms["success"], ms["unmatched"]
                    )
            elif step.name == "filter_archive_status":
                df = step.execute(df, self.config, force_unarchived=force_unarchived)  # type: ignore[call-arg]
                self._archive_status_result: dict = getattr(step, "result", {})
                self._data_type: str = self._archive_status_result.get("data_type", "pure_unarchived")
                if self.audit:
                    self._log_archive_status(self._archive_status_result)
            elif step.name == "calc_due_days":
                df = step.execute(df, self.config, base_date_col=base_date_col)  # type: ignore[call-arg]
                self._due_days_match_status: str = getattr(step, "match_status", "pending")
                self._due_days_matched_column: str = getattr(step, "matched_column", "")
            else:
                df = step.execute(df, self.config)

            rows_after = len(df)
            if self.audit:
                self.audit.end_step(step.name, rows_before, rows_after)

        if self.audit:
            self.audit.set_stats(unwritten_count=len(df))
            self.audit.info(self.audit.summary())

        return df

    def _log_archive_status(self, result: Dict[str, Any]) -> None:
        """将归档状态识别结果写入审计日志。"""
        if not self.audit:
            return
        r = result
        if r.get("force_unarchived"):
            self.audit.info(f"[归档状态] 强制覆盖：跳过状态筛选，保留全部 {r.get('total', 0)} 行")
        elif not r.get("has_status_column"):
            self.audit.info("[归档状态] 未找到归档状态列，判定为纯未归档数据，保留全部行")
        elif r.get("data_type") == "full":
            self.audit.info(
                f"[归档状态] 识别为全量数据（状态列「{r.get('status_column', '')}」），"
                f"过滤已归档 {r.get('filtered', 0)} 行，保留 {r.get('kept', 0)} 行"
            )
        else:
            self.audit.info("[归档状态] 状态列中未发现已归档值，判定为纯未归档数据，保留全部行")
