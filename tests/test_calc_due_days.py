"""测试到期天数计算步骤（基于基准日期列智能匹配）。"""

import pandas as pd
import pytest
from src.steps.calc_due_days import CalcDueDays


class TestCalcDueDays:
    """基础计算逻辑测试 — 使用「出单日期」列（别名列表首个匹配项）。"""

    def test_calculates_days_from_order_date(self, config):
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-10")]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == 5  # 2025-06-15 - 2025-06-10
        assert "基准日期" in result.columns

    def test_negative_for_future_date(self, config):
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-20")]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == -5

    def test_zero_for_reference_date(self, config):
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-15")]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == 0

    def test_no_matching_column(self, config):
        """无任何匹配列时，到期天数填充 0 且 match_status='failed'。"""
        df = pd.DataFrame({"其他列": [1, 2, 3]})
        step = CalcDueDays()
        result = step.execute(df, config)
        assert "到期天数" in result.columns
        assert (result["到期天数"] == 0).all()
        assert step.match_status == "failed"
        assert step.matched_column == ""


class TestAutoMatchAliases:
    """智能匹配测试 — 验证别名自动识别流程。"""

    def test_matches_qian_dan_date(self, config):
        """「签单日期」在别名列表中，应被自动识别为基准日期列。"""
        df = pd.DataFrame({"签单日期": [pd.Timestamp("2025-06-01")]})
        step = CalcDueDays()
        result = step.execute(df, config)
        assert step.match_status == "success"
        assert step.matched_column == "签单日期"
        assert "基准日期" in result.columns
        assert result.loc[0, "到期天数"] == 14  # 2025-06-15 - 2025-06-01

    def test_matches_english_alias(self, config):
        """英文别名 OrderDate 应被自动识别。"""
        df = pd.DataFrame({"OrderDate": [pd.Timestamp("2025-06-10")]})
        step = CalcDueDays()
        result = step.execute(df, config)
        assert step.match_status == "success"
        assert step.matched_column == "OrderDate"
        assert "基准日期" in result.columns

    def test_case_insensitive_match(self, config):
        """别名匹配应忽略大小写。"""
        df = pd.DataFrame({"orderdate": [pd.Timestamp("2025-06-12")]})
        step = CalcDueDays()
        result = step.execute(df, config)
        assert step.match_status == "success"
        assert step.matched_column == "orderdate"

    def test_stripped_match(self, config):
        """别名匹配应忽略首尾空格。"""
        df = pd.DataFrame({"  出单日期  ": [pd.Timestamp("2025-06-12")]})
        step = CalcDueDays()
        result = step.execute(df, config)
        assert step.match_status == "success"
        assert step.matched_column == "  出单日期  "

    def test_first_alias_wins(self, config):
        """同时存在多个匹配列时，取别名列表中最靠前的一个。"""
        df = pd.DataFrame({
            "签单日期": [pd.Timestamp("2025-06-01")],
            "出单日期": [pd.Timestamp("2025-06-10")],
        })
        step = CalcDueDays()
        result = step.execute(df, config)
        # 「出单日期」在别表中的顺序先于「签单日期」，应优先匹配
        assert step.matched_column == "出单日期"


class TestManualOverride:
    """手动指定基准日期列测试。"""

    def test_manual_base_date_col(self, config):
        """手动指定列名应覆盖自动匹配。"""
        df = pd.DataFrame({
            "自定义日期列": [pd.Timestamp("2025-05-01")],
            "出单日期": [pd.Timestamp("2025-06-10")],
        })
        step = CalcDueDays()
        result = step.execute(df, config, base_date_col="自定义日期列")
        assert step.match_status == "success"
        assert step.matched_column == "自定义日期列"
        assert "基准日期" in result.columns
        assert result.loc[0, "到期天数"] == 45  # 2025-06-15 - 2025-05-01

    def test_manual_col_not_found_falls_back(self, config):
        """手动指定的列不存在时，回退到自动匹配。"""
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-10")]})
        step = CalcDueDays()
        result = step.execute(df, config, base_date_col="不存在的列")
        assert step.match_status == "success"
        assert step.matched_column == "出单日期"
        assert result.loc[0, "到期天数"] == 5

    def test_string_column_coerced_to_datetime(self, config):
        """手动指定的字符串列自动转为 datetime。"""
        df = pd.DataFrame({"字符串日期": ["2025-05-20"]})
        step = CalcDueDays()
        result = step.execute(df, config, base_date_col="字符串日期")
        assert step.match_status == "success"
        assert pd.api.types.is_datetime64_any_dtype(result["基准日期"])
        assert result.loc[0, "到期天数"] == 26  # 2025-06-15 - 2025-05-20


class TestEmptyAndEdgeCases:
    """边界情况测试。"""

    def test_empty_df(self, config):
        df = pd.DataFrame()
        step = CalcDueDays()
        result = step.execute(df, config)
        assert "到期天数" in result.columns
        assert step.match_status == "failed"

    def test_nat_values(self, config):
        """NaT 单元格到期天数填充 0。"""
        df = pd.DataFrame({"出单日期": [pd.NaT]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == 0

    def test_mixed_valid_and_nat(self, config):
        """混合有效日期与 NaT。"""
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-10"), pd.NaT]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == 5
        assert result.loc[1, "到期天数"] == 0
