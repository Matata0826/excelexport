"""审计日志模块：每次运行生成独立日志，记录处理统计与异常明细。"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    """带上下文统计的审计日志器。"""

    def __init__(self, config: Dict[str, Any], run_id: Optional[str] = None) -> None:
        log_cfg = config.get("logging", {})
        self.logger = logging.getLogger(f"pipeline.{run_id or id(self)}")
        self.logger.setLevel(getattr(logging, log_cfg.get("level", "INFO")))
        self.logger.handlers.clear()

        fmt = log_cfg.get("format", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        datefmt = log_cfg.get("datefmt", "%Y-%m-%d %H:%M:%S")
        formatter = logging.Formatter(fmt, datefmt=datefmt)

        if log_cfg.get("console_output", True):
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        if log_cfg.get("per_run_file", True):
            logs_dir = Path(config["paths"].get("logs_dir", "logs"))
            logs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = logs_dir / f"run_{timestamp}.log"
            fh = logging.FileHandler(filepath, encoding="utf-8")
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        # 运行时统计
        self.stats: Dict[str, Any] = {
            "total_rows": 0,
            "skipped_rows": 0,
            "mapping_total": 0,
            "mapping_success": 0,
            "mapping_unmatched": 0,
            "unwritten_count": 0,
            "step_timings": {},
            "skip_reasons": [],
            "unmatched_names": [],
        }
        self._step_timer_start: float = 0.0

    # ---- public API ----

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)

    def start_step(self, step_name: str) -> None:
        self._step_timer_start = time.perf_counter()
        self.info(f"[步骤开始] {step_name}")

    def end_step(self, step_name: str, rows_before: int, rows_after: int) -> None:
        elapsed = time.perf_counter() - self._step_timer_start
        self.stats["step_timings"][step_name] = round(elapsed, 4)
        self.info(
            f"[步骤完成] {step_name} | 耗时 {elapsed:.4f}s "
            f"| 行数 {rows_before} → {rows_after}"
        )

    def record_skip(self, reason: str, count: int = 1) -> None:
        self.stats["skipped_rows"] += count
        self.stats["skip_reasons"].append(reason)
        self.warning(f"[跳过] {reason} (本批 {count} 行)")

    def record_mapping_result(self, total: int, success: int, unmatched: list[str]) -> None:
        self.stats["mapping_total"] = total
        self.stats["mapping_success"] = success
        self.stats["mapping_unmatched"] = total - success
        self.stats["unmatched_names"] = unmatched
        self.info(f"[映射] 总计 {total} 行, 成功 {success}, 未匹配 {total - success}")
        if unmatched:
            self.warning(f"[映射] 未匹配的业务员: {unmatched[:20]}{'...' if len(unmatched) > 20 else ''}")

    def set_stats(self, **kwargs: Any) -> None:
        self.stats.update(kwargs)

    def summary(self) -> str:
        """返回汇总字符串，用于看板展示。"""
        s = self.stats
        lines = [
            f"总行数: {s['total_rows']}",
            f"跳过行数: {s['skipped_rows']}",
            f"映射成功: {s['mapping_success']}/{s['mapping_total']}",
            f"未回销件数: {s['unwritten_count']}",
        ]
        if s.get("step_timings"):
            lines.append("各步骤耗时:")
            for name, dur in s["step_timings"].items():
                lines.append(f"  {name}: {dur:.3f}s")
        return "\n".join(lines)
