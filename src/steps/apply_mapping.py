"""步骤3：主号映射替换 — 将原始小号业务员替换为主号业务员。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from .base import CleaningStep, register_step


@register_step("apply_mapping", order=3)
class ApplyMapping(CleaningStep):
    """根据映射模板将原始业务员名替换为主号业务员。

    映射模板格式：A列=主号机构, B列=主号业务员, C列=原始业务员名称。
    """

    def execute(
        self, df: pd.DataFrame, config: Dict[str, Any],
        mapping_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        if "业务员" not in df.columns:
            return df

        if mapping_df is None or mapping_df.empty:
            return df

        # 构建小号→主号映射
        raw_col = "原始业务员名称"
        master_col = "主号业务员"

        # 容错：识别映射表的列
        cols = [str(c).strip() for c in mapping_df.columns]
        if raw_col not in cols and len(mapping_df.columns) >= 3:
            raw_col = mapping_df.columns[2]
        if master_col not in cols and len(mapping_df.columns) >= 2:
            master_col = mapping_df.columns[1]

        name_map: Dict[str, str] = {}
        for _, row in mapping_df.iterrows():
            alias = str(row[raw_col]).strip()
            master = str(row[master_col]).strip()
            if alias and master:
                name_map[alias] = master

        total = len(df)
        original_names = df["业务员"].astype(str).str.strip()

        def _map_name(name: str) -> str:
            return name_map.get(name, name)

        df["业务员"] = original_names.apply(_map_name)

        # 统计匹配结果
        matched = original_names.isin(name_map.keys()).sum()
        unmatched_names = original_names[~original_names.isin(name_map.keys())].unique().tolist()

        # 存储统计信息供 pipeline 使用
        self._mapping_stats = {
            "total": total,
            "success": matched,
            "unmatched": unmatched_names,
        }

        return df
