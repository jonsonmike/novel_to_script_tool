"""AI 转换流水线

将小说文本转换为结构化剧本的完整流程。

主要入口：run_pipeline()
"""

from .orchestrator import run_pipeline, PipelineResult

__all__ = ["run_pipeline", "PipelineResult"]
