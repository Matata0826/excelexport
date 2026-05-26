"""测试主号映射替换步骤。"""

import pandas as pd
from src.steps.apply_mapping import ApplyMapping


class TestApplyMapping:
    def test_maps_known_names(self, config, sample_mapping_df):
        df = pd.DataFrame({"业务员": ["张三小号", "李四", "王五小号"]})
        result = ApplyMapping().execute(df, config, mapping_df=sample_mapping_df)
        assert result.loc[0, "业务员"] == "张三"
        assert result.loc[1, "业务员"] == "李四"  # 未匹配保留原值
        assert result.loc[2, "业务员"] == "王五"

        # 验证新增列
        assert "主号机构" in result.columns
        assert "主号业务员" in result.columns
        assert result.loc[0, "主号机构"] == "机构A"
        assert result.loc[0, "主号业务员"] == "张三"
        assert result.loc[1, "主号机构"] == ""  # 未匹配
        assert result.loc[1, "主号业务员"] == "李四"  # 保留原业务员名

    def test_keeps_original_on_unmatched(self, config, sample_mapping_df):
        df = pd.DataFrame({"业务员": ["不存在的名字"]})
        result = ApplyMapping().execute(df, config, mapping_df=sample_mapping_df)
        assert result.loc[0, "业务员"] == "不存在的名字"
        assert result.loc[0, "主号机构"] == ""
        assert result.loc[0, "主号业务员"] == "不存在的名字"

    def test_no_mapping_df_returns_unchanged(self, config):
        df = pd.DataFrame({"业务员": ["张三小号"]})
        result = ApplyMapping().execute(df, config, mapping_df=None)
        assert result.loc[0, "业务员"] == "张三小号"
        # 无映射表时仍补全空列
        assert "主号机构" in result.columns
        assert "主号业务员" in result.columns

    def test_empty_df(self, config, sample_mapping_df):
        df = pd.DataFrame({"业务员": []})
        result = ApplyMapping().execute(df, config, mapping_df=sample_mapping_df)
        assert result.empty
