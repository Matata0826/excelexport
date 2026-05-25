"""测试列名标准化步骤。"""

import pandas as pd
from src.steps.normalize_columns import NormalizeColumns


class TestNormalizeColumns:
    def test_strips_and_lowercases(self, config):
        df = pd.DataFrame({"  业务员 ": [1], " AMOUNT ": [2], " 出单日期  ": [3]})
        result = NormalizeColumns().execute(df, config)
        assert "业务员" in result.columns
        assert "AMOUNT" not in result.columns  # 容错仅匹配已知别名
        assert "出单日期" in result.columns

    def test_alias_matching(self, config):
        df = pd.DataFrame({"sales": ["张三"], "amount": [100]})
        result = NormalizeColumns().execute(df, config)
        assert "业务员" in result.columns
        assert "金额" in result.columns

    def test_unmatched_columns_preserved(self, config):
        df = pd.DataFrame({"未知列": ["x"], "业务员": ["张三"]})
        result = NormalizeColumns().execute(df, config)
        assert "未知列" in result.columns
        assert "业务员" in result.columns
