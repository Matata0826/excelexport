# 业务数据清洗与未回销看板

配置驱动、模块化的业务数据清洗系统，支持上传 Excel → 自动清洗 → 看板展示 → 筛选导出。

## 快速开始

```bash
cd ~/Desktop/CC\ Project

# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动看板
streamlit run app.py

# 3. 浏览器访问 http://localhost:8501
```

## 部署步骤

1. **Python 版本**: 要求 Python 3.10+
2. **安装依赖**: `pip install -r requirements.txt`
3. **启动服务**: `streamlit run app.py --server.port=8501`
4. **生产部署**: 可使用 `nohup streamlit run app.py --server.port=8501 &` 后台运行，或配置 systemd/supervisor

## 项目结构

```
CC Project/
├── app.py                 # Streamlit 主入口
├── config.yaml            # 全局配置（列映射、阈值、分组规则）
├── requirements.txt       # 依赖
├── pyproject.toml         # 项目元数据 + pytest 配置
├── logs/                  # 审计日志（每次运行自动生成）
├── exports/               # 导出 Excel 目录
├── templates/
│   └── mapping_template.xlsx  # 主号映射模板
├── src/
│   ├── config_loader.py   # YAML 配置加载与校验
│   ├── audit.py           # 审计日志模块
│   ├── pipeline.py        # 清洗管道引擎
│   ├── steps/             # 可插拔清洗步骤
│   │   ├── base.py        # 步骤基类 + @register_step 装饰器
│   │   ├── normalize_columns.py
│   │   ├── clean_invalid.py
│   │   ├── apply_mapping.py
│   │   ├── calc_due_days.py
│   │   └── mark_unwritten.py
│   ├── dashboard.py       # 看板组件（指标卡/图表/明细表）
│   └── exporter.py        # 导出 Excel
└── tests/                 # pytest 测试
```

## 核心流程

1. **上传原始业务 Excel** — 系统自动识别列名（容错空格/大小写/别名）
2. **上传主号映射模板** — A列主号机构、B列主号业务员、C列原始业务员名称
3. **清洗管道执行** — 5步依次处理：列名标准化 → 异常值清理 → 主号映射 → 到期天数 → 未回销标记
4. **看板展示** — 指标卡、分布图、明细表
5. **筛选导出** — 按业务员筛选后生成带时间戳的 Excel

## 如何修改配置

编辑 `config.yaml`：

### 添加/修改列名别名

```yaml
column_mapping:
  业务员: ["业务员", "销售人员", "sales", "你的别名"]
```

### 调整到期分组区间

```yaml
due_days:
  buckets:
    - label: "0-3天"
      min: 0
      max: 3
    - label: "4-7天"
      min: 4
      max: 7
    # 新增区间
    - label: "8-15天"
      min: 8
      max: 15
    - label: ">15天"
      min: 16
      max: 9999
```

### 修改未回销判定规则

```yaml
unwritten_off:
  rules:
    - type: "status_not_equal"
      column: "状态"
      value: "已回销"
    - type: "due_days_exceed"
      column: "到期天数"
      threshold: 0     # 到期天数 > 0 即为未回销
```

## 如何新增清洗规则

在 `src/steps/` 下创建新文件，使用 `@register_step` 装饰器：

```python
# src/steps/my_new_step.py
from .base import CleaningStep, register_step

@register_step("my_new_step", order=6)
class MyNewStep(CleaningStep):
    def execute(self, df, config):
        # 你的清洗逻辑
        return df
```

然后在 `src/steps/__init__.py` 中添加一行导入：

```python
from .my_new_step import MyNewStep  # noqa: F401
```

管道引擎会自动按 `order` 排序执行，无需修改主流程。

## 运行测试

```bash
cd ~/Desktop/CC\ Project
python -m pytest tests/ -v
```

## 审计日志

每次执行清洗后，`logs/` 目录下会自动生成以时间戳命名的日志文件（如 `run_20250525_143022.log`），包含：

- 初始行数与最终行数
- 每步耗时
- 映射成功/失败明细
- 跳过行原因
- 未回销总数
