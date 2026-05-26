"""步骤3：主号映射替换 — 将原始小号业务员替换为主号业务员，同时标注机构。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from .base import CleaningStep, register_step


@register_step("apply_mapping", order=3)
class ApplyMapping(CleaningStep):
    """根据映射模板将原始业务员名替换为主号业务员，并补全主号机构/主号业务员列。

    映射模板格式：A列=主号机构, B列=主号业务员, C列=原始业务员名称。
    """

    def execute(
        self, df: pd.DataFrame, config: Dict[str, Any],
        mapping_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        if "业务员" not in df.columns:
            return df

        if mapping_df is None or mapping_df.empty:
            # 无映射表时仍补全空列，保证列结构一致
            if "主号机构" not in df.columns:
                df["主号机构"] = ""
            if "主号业务员" not in df.columns:
                df["主号业务员"] = df["业务员"]
            return df

        # 容错：识别映射表的列
        cols = [str(c).strip() for c in mapping_df.columns]
        inst_col = mapping_df.columns[0] if len(mapping_df.columns) >= 1 else None
        master_col = mapping_df.columns[1] if len(mapping_df.columns) >= 2 else None
        raw_col = mapping_df.columns[2] if len(mapping_df.columns) >= 3 else None

        if inst_col is None or master_col is None or raw_col is None:
            return df

        # 构建 小号 → (主号机构, 主号业务员)
        lookup: Dict[str, tuple[str, str]] = {}
        for _, row in mapping_df.iterrows():
            alias = str(row[raw_col]).strip()
            inst = str(row[inst_col]).strip()
            master = str(row[master_col]).strip()
            if alias and master:
                lookup[alias] = (inst, master)

        total = len(df)
        original_names = df["业务员"].astype(str).str.strip()

        # 替换业务员列，同时记录机构和主号
        mapped_names = original_names.apply(lambda n: lookup.get(n, (n, n))[1])
        mapped_insts = original_names.apply(lambda n: lookup.get(n, ("", n))[0])

        df["业务员"] = mapped_names
        df["主号机构"] = mapped_insts
        df["主号业务员"] = mapped_names

        # 统计匹配结果
        matched = original_names.isin(lookup.keys()).sum()
        unmatched_names = original_names[~original_names.isin(lookup.keys())].unique().tolist()

        self._mapping_stats = {
            "total": total,
            "success": matched,
            "unmatched": unmatched_names,
        }

        return df
