"""清洗管道引擎：按注册顺序串联执行所有清洗步骤。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from .audit import AuditLogger
from .steps import NormalizeColumns, CleanInvalid, ApplyMapping, CalcDueDays  # noqa: F401
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
    ) -> pd.DataFrame:
        """执行全部清洗步骤。

        Args:
            df: 原始数据
            mapping_df: 主号映射表（可选）

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
            else:
                df = step.execute(df, self.config)

            rows_after = len(df)
            if self.audit:
                self.audit.end_step(step.name, rows_before, rows_after)

        if self.audit:
            self.audit.set_stats(unwritten_count=len(df))
            self.audit.info(self.audit.summary())

        return df
