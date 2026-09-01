"""配置加载与校验模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(config_path: str | Path = "config.yaml") -> Dict[str, Any]:
    """加载 YAML 配置文件并执行基本校验。

    Args:
        config_path: 配置文件路径，默认为项目根目录的 config.yaml

    Returns:
        解析后的配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置格式不合法
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    _validate(config, path)
    return config


def _validate(config: Dict[str, Any], path: Path) -> None:
    """校验配置文件的必要字段。"""
    required_sections = ["paths", "column_mapping", "cleaning", "mapping",
                         "due_days", "archive_status", "export", "dashboard", "logging"]
    missing = [s for s in required_sections if s not in config]
    if missing:
        raise ValueError(f"[{path}] 缺少必要配置节: {missing}")

    # 确保路径目录存在
    exports_dir = Path(config["paths"].get("exports_dir", "exports"))
    logs_dir = Path(config["paths"].get("logs_dir", "logs"))
    exports_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)


def get_column_alias_map(config: Dict[str, Any]) -> Dict[str, str]:
    """构建 别名 → 标准名 的映射表，用于列名标准化。

    Returns:
        {"别名小写": "标准名", ...}
    """
    column_mapping: Dict[str, list[str]] = config.get("column_mapping", {})
    alias_map: Dict[str, str] = {}
    for standard, aliases in column_mapping.items():
        for alias in aliases:
            alias_map[alias.strip().lower()] = standard
    return alias_map


def get_bucket_boundaries(config: Dict[str, Any]) -> list[tuple[str, int, int]]:
    """获取到期天数分组区间。

    Returns:
        [(label, min, max), ...]
    """
    buckets = config.get("due_days", {}).get("buckets", [])
    return [(b["label"], b["min"], b["max"]) for b in buckets]
