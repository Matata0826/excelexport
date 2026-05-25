"""清洗步骤基类与注册表机制。

新增清洗规则：创建类，用 @register_step 装饰，实现 execute() 方法。
管道引擎自动发现并排序执行。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Type

import pandas as pd


class CleaningStep:
    """清洗步骤基类。子类需实现 execute(df, config) -> DataFrame。"""

    name: str = ""
    order: int = 999

    def execute(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        raise NotImplementedError


_registry: Dict[str, Type[CleaningStep]] = {}


def register_step(name: str, order: int) -> Callable[[Type[CleaningStep]], Type[CleaningStep]]:
    """装饰器：注册清洗步骤到全局注册表。

    Usage:
        @register_step("normalize_columns", order=1)
        class NormalizeColumns(CleaningStep):
            ...
    """
    def decorator(cls: Type[CleaningStep]) -> Type[CleaningStep]:
        cls.name = name
        cls.order = order
        _registry[name] = cls
        return cls
    return decorator


def get_steps_sorted() -> List[CleaningStep]:
    """按 order 升序返回所有已注册步骤的实例。"""
    return [cls() for cls in sorted(_registry.values(), key=lambda c: c.order)]


def list_registered_steps() -> List[str]:
    """列出已注册的步骤名称（按执行顺序）。"""
    return [c.name for c in sorted(_registry.values(), key=lambda c: c.order)]
