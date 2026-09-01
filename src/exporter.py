"""导出模块：按业务员拆分，一人一表，保留全部原始字段，可选打包 zip。"""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


def export_single(
    df: pd.DataFrame,
    config: Dict[str, Any],
    salesperson: str,
    timestamp: str | None = None,
) -> str:
    """导出单个业务员的未回销清单（保留全部原始列 + 新增计算列）。

    Args:
        df: 该业务员的数据（全部列）
        config: 全局配置
        salesperson: 业务员姓名
        timestamp: 可选时间戳（用于批量导出时统一命名）

    Returns:
        导出文件的绝对路径
    """
    if df.empty:
        raise ValueError(f"业务员「{salesperson}」无数据可导出")

    export_cfg = config.get("export", {})
    paths_cfg = config.get("paths", {})

    exports_dir = Path(paths_cfg.get("exports_dir", "exports"))
    exports_dir.mkdir(parents=True, exist_ok=True)

    if timestamp is None:
        timestamp = datetime.now().strftime(export_cfg.get("timestamp_format", "%Y%m%d_%H%M%S"))

    desc = export_cfg.get("description", "未回销清单")
    safe_name = salesperson.replace("/", "_").replace("\\", "_").strip()

    filename = f"{timestamp}_{desc}_{safe_name}.xlsx"
    filepath = exports_dir / filename

    sheet_name = export_cfg.get("sheet_name", "未回销明细")

    # 保留全部原始列，仅调整列顺序：优先展示关键列，其余紧随其后
    priority_cols = ["单号", "主号机构", "主号业务员", "业务员", "金额", "基准日期", "出单日期", "到期天数"]
    other_cols = [c for c in df.columns if c not in priority_cols]
    ordered_cols = [c for c in priority_cols if c in df.columns] + other_cols

    export_df = df[ordered_cols].sort_values("到期天数", ascending=False)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        export_df.to_excel(writer, sheet_name=sheet_name, index=False)

    return str(filepath.resolve())


def export_batch(
    df: pd.DataFrame,
    config: Dict[str, Any],
    selected_people: List[str],
) -> Tuple[str, List[str]]:
    """按业务员拆分导出，一人一表，同时生成 zip 包。

    Args:
        df: 全部清洗后数据
        config: 全局配置
        selected_people: 需要导出的业务员列表

    Returns:
        (zip_filepath, [individual_filepaths, ...])
    """
    if df.empty or not selected_people:
        raise ValueError("无数据或未选择业务员")

    export_cfg = config.get("export", {})
    paths_cfg = config.get("paths", {})

    exports_dir = Path(paths_cfg.get("exports_dir", "exports"))
    exports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(export_cfg.get("timestamp_format", "%Y%m%d_%H%M%S"))
    desc = export_cfg.get("description", "未回销清单")

    filepaths: List[str] = []

    for person in selected_people:
        person_df = df[df["业务员"] == person] if "业务员" in df.columns else df
        if person_df.empty:
            continue
        fp = export_single(person_df, config, person, timestamp=timestamp)
        filepaths.append(fp)

    if not filepaths:
        raise ValueError("所选业务员均无数据")

    # 生成 zip 包
    zip_name = f"{timestamp}_{desc}_批量.zip"
    zip_path = str((exports_dir / zip_name).resolve())

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in filepaths:
            zf.write(fp, arcname=Path(fp).name)

    return zip_path, filepaths
