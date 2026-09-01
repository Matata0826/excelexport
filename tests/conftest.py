"""pytest 共享 fixtures。"""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def config() -> dict:
    """返回最小可用的配置字典（与 config.yaml 结构一致）。"""
    return {
        "paths": {"exports_dir": "exports", "logs_dir": "logs"},
        "column_mapping": {
            "业务员": ["业务员", "sales"],
            "出单日期": ["出单日期", "order_date"],
            "金额": ["金额", "amount"],
            "单号": ["单号", "编号"],
        },
        "cleaning": {
            "amount": {"strategy": "coerce", "remove_nulls": True},
            "date": {"strategy": "coerce", "date_format": None},
            "global": {"drop_all_null": False},
        },
        "mapping": {
            "template_columns": {"A": "主号机构", "B": "主号业务员", "C": "原始业务员名称"},
            "on_unmatched": "keep_original",
            "log_unmatched": True,
        },
        "due_days": {
            "reference_date": "2025-06-15",
            "base_date_aliases": ["出单日期", "签单日期", "保单日期", "OrderDate", "IssueDate"],
            "buckets": [
                {"label": "0-15天", "min": 0, "max": 15},
                {"label": "15-30天", "min": 16, "max": 30},
                {"label": "30-60天", "min": 31, "max": 60},
                {"label": "60-90天", "min": 61, "max": 90},
                {"label": "超90天", "min": 91, "max": 9999},
            ],
        },
        "export": {
            "filename_format": "{timestamp}_{description}_{salesperson}.xlsx",
            "timestamp_format": "%Y%m%d_%H%M%S",
            "description": "未回销清单",
            "sheet_name": "未回销明细",
        },
        "dashboard": {
            "page_title": "测试",
            "sidebar_title": "控制面板",
            "metric_cards": [
                {"key": "unwritten_count", "label": "未回销总件数"},
            ],
            "chart": {
                "title": "分布图",
                "x_label": "天数",
                "y_label": "件数",
                "color_sequence": ["#5470c6"],
            },
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "per_run_file": False,
            "console_output": False,
        },
    }


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """模拟原始业务数据（3行，全部为未回销）。"""
    return pd.DataFrame({
        "编号": ["A001", "A002", "A003"],
        "sales": ["张三小号", "李四", "王五小号"],
        "amount": ["1000.00", "2000.00", "invalid"],
        "order_date": ["2025-05-01", "2025-06-10", "2025-07-01"],
    })


@pytest.fixture
def sample_mapping_df() -> pd.DataFrame:
    """模拟主号映射表。"""
    return pd.DataFrame({
        "主号机构": ["机构A", "机构B"],
        "主号业务员": ["张三", "王五"],
        "原始业务员名称": ["张三小号", "王五小号"],
    })
