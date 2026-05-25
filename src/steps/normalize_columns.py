"""步骤1：列名标准化 — 去空格、统一小写、别名映射。"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import CleaningStep, register_step


@register_step("normalize_columns", order=1)
class NormalizeColumns(CleaningStep):
    """根据 config['column_mapping'] 将原始列名映射为标准列名。

    规则：原始列名 → strip + lower → 查别名表 → 标准名。未匹配的列保留原名。
    """

    def execute(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        alias_map = self._build_alias_map(config)
        rename_map: Dict[str, str] = {}
        for col in df.columns:
            key = str(col).strip().lower()
            if key in alias_map:
                rename_map[col] = alias_map[key]
        return df.rename(columns=rename_map)

    @staticmethod
    def _build_alias_map(config: Dict[str, Any]) -> Dict[str, str]:
        column_mapping: Dict[str, list[str]] = config.get("column_mapping", {})
        alias_map: Dict[str, str] = {}
        for standard, aliases in column_mapping.items():
            for alias in aliases:
                alias_map[alias.strip().lower()] = standard
        return alias_map
