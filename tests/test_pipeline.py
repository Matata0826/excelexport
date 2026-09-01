"""端到端管道集成测试。"""

import pandas as pd
from src.pipeline import Pipeline


class TestPipelineEndToEnd:
    def test_full_pipeline_smoke(self, config, sample_raw_df, sample_mapping_df):
        pipeline = Pipeline(config)
        result = pipeline.run(sample_raw_df, mapping_df=sample_mapping_df)

        # 列名已标准化
        assert "业务员" in result.columns
        assert "金额" in result.columns
        assert "基准日期" in result.columns  # calc_due_days 自动匹配后重命名

        # 映射成功：业务员小号已替换为主号
        salespeople = result["业务员"].tolist()
        assert "张三" in salespeople  # 张三小号→张三
        assert "李四" in salespeople  # 无映射，保留原值

        # 无效金额行被移除（第3行 amount='invalid' → NaN → 在步骤2中被删除）
        assert len(result) == 2
        assert "王五" not in salespeople

        # 到期天数已计算（基于出单日期）
        assert "到期天数" in result.columns

        # 机构和主号列已补全
        assert "主号机构" in result.columns
        assert "主号业务员" in result.columns
        assert result.loc[0, "主号机构"] == "机构A"
        assert result.loc[0, "主号业务员"] == "张三"

    def test_empty_df_returns_empty(self, config):
        pipeline = Pipeline(config)
        result = pipeline.run(pd.DataFrame())
        assert result.empty

    def test_without_mapping(self, config):
        pipeline = Pipeline(config)
        df = pd.DataFrame({
            "业务员": ["张三小号"],
            "金额": ["100"],
            "出单日期": ["2025-06-10"],
        })
        result = pipeline.run(df, mapping_df=None)
        assert len(result) > 0
        assert result.loc[0, "业务员"] == "张三小号"  # 无映射时保留原值
