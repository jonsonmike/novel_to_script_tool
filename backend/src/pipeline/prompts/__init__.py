"""AI Pipeline 多阶段 Prompt 模板

四个阶段：
1. extraction  — 角色实体提取
2. splitting   — 场景拆分
3. generation  — 剧本内容生成
4. assembly    — 格式组装为完整 YAML
"""

from . import extraction
from . import splitting
from . import generation
from . import assembly

__all__ = ["extraction", "splitting", "generation", "assembly"]
