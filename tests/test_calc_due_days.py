"""测试到期天数计算步骤（基于出单日期）。"""

import pandas as pd
from src.steps.calc_due_days import CalcDueDays


class TestCalcDueDays:
    def test_calculates_days_from_order_date(self, config):
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-10")]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == 5  # 2025-06-15 - 2025-06-10

    def test_negative_for_future_date(self, config):
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-20")]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == -5

    def test_zero_for_reference_date(self, config):
        df = pd.DataFrame({"出单日期": [pd.Timestamp("2025-06-15")]})
        result = CalcDueDays().execute(df, config)
        assert result.loc[0, "到期天数"] == 0

    def test_no_order_date_column(self, config):
        df = pd.DataFrame({"其他列": [1, 2, 3]})
        result = CalcDueDays().execute(df, config)
        assert "到期天数" in result.columns
