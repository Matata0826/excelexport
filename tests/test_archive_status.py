"""测试归档状态识别与过滤步骤。"""

import pandas as pd

from src.steps.filter_archive_status import (
    FilterArchiveStatus,
    detect_and_filter_archive_status,
)


class TestDetectAndFilter:
    def test_no_status_column_keeps_all(self, config):
        df = pd.DataFrame({"业务员": ["张三", "李四"], "金额": [100, 200]})
        out, info = detect_and_filter_archive_status(df, config)
        assert info["data_type"] == "pure_unarchived"
        assert info["has_status_column"] is False
        assert len(out) == 2

    def test_full_data_filters_archived(self, config):
        df = pd.DataFrame({
            "业务员": ["张三", "李四", "王五"],
            "归档状态": ["未归档", "已归档", "未归档"],
        })
        out, info = detect_and_filter_archive_status(df, config)
        assert info["data_type"] == "full"
        assert info["status_column"] == "归档状态"
        assert info["filtered"] == 1
        assert info["kept"] == 2
        assert set(out["业务员"]) == {"张三", "王五"}

    def test_all_unarchived_keeps_all(self, config):
        df = pd.DataFrame({"归档状态": ["未归档", "未归档"]})
        out, info = detect_and_filter_archive_status(df, config)
        assert info["data_type"] == "pure_unarchived"
        assert len(out) == 2

    def test_force_unarchived_skips_filter(self, config):
        df = pd.DataFrame({
            "归档状态": ["未归档", "已归档"],
            "业务员": ["张三", "李四"],
        })
        out, info = detect_and_filter_archive_status(df, config, force_unarchived=True)
        assert info["data_type"] == "pure_unarchived"
        assert info["force_unarchived"] is True
        assert len(out) == 2  # 已归档行保留

    def test_alias_match_english(self, config):
        df = pd.DataFrame({"Status": ["未归档", "已归档"]})
        out, info = detect_and_filter_archive_status(df, config)
        assert info["status_column"] == "Status"
        assert info["data_type"] == "full"
        assert len(out) == 1

    def test_keyword_fallback_match(self, config):
        df = pd.DataFrame({"车辆归档情况": ["未归档", "已归档"]})
        out, info = detect_and_filter_archive_status(df, config)
        assert info["status_column"] == "车辆归档情况"
        assert info["data_type"] == "full"

    def test_keyword_priority_prefers_archive(self, config):
        # 关键字按优先级：归档 > 状态 > 是否，避免误匹配「是否借出」
        df = pd.DataFrame({
            "是否借出": ["是", "否"],
            "归档标记": ["未归档", "已归档"],
        })
        out, info = detect_and_filter_archive_status(df, config)
        assert info["status_column"] == "归档标记"
        assert info["data_type"] == "full"

    def test_excludes_datetime_column_from_keyword(self, config):
        # 「归档时间」是日期列，不应被「归档」关键字误匹配
        df = pd.DataFrame({"归档时间": ["2025-06-01", "2025-06-02"]})
        out, info = detect_and_filter_archive_status(df, config)
        assert info["has_status_column"] is False
        assert info["data_type"] == "pure_unarchived"
        assert len(out) == 2

    def test_shi_fou_weak_keyword_requires_context(self, config):
        # 「是否借出」是普通布尔列，不应被「是否」关键字误匹配
        df = pd.DataFrame({"是否借出": ["是", "否"]})
        out, info = detect_and_filter_archive_status(df, config)
        assert info["has_status_column"] is False
        assert len(out) == 2

    def test_shi_fou_with_archive_context_matches(self, config):
        # 「是否回销」含「是否」+「回销」，应被识别为归档状态列
        df = pd.DataFrame({"是否回销": ["否", "是"]})
        out, info = detect_and_filter_archive_status(df, config)
        assert info["status_column"] == "是否回销"
        assert info["data_type"] == "full"
        assert len(out) == 1

    def test_real_three_value_status(self, config):
        # 真实字段：归档齐全(过滤) / 归档不齐(保留) / 未归档(保留)
        df = pd.DataFrame({
            "归档状态": ["归档齐全", "归档不齐", "未归档", "归档齐全"],
            "业务员": ["张三", "李四", "王五", "赵六"],
        })
        out, info = detect_and_filter_archive_status(df, config)
        assert info["data_type"] == "full"
        assert info["filtered"] == 2
        assert set(out["业务员"]) == {"李四", "王五"}


class TestStepClass:
    def test_step_exposes_data_type(self, config):
        df = pd.DataFrame({"归档状态": ["未归档", "已归档"]})
        step = FilterArchiveStatus()
        out = step.execute(df, config)
        assert step.data_type == "full"
        assert step.result["filtered"] == 1
        assert len(out) == 1
