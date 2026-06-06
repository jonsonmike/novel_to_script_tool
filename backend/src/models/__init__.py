"""数据模型层 — Script Schema 的 Pydantic 实现"""

from .script import (
    # 顶层
    ScriptOutput,
    # meta
    Meta,
    UserInstructions,
    # characters
    Character,
    RoleType,
    # scenes
    Scene,
    ContentItem,
    ContentType,
    TimeOfDay,
    # 正则
    CHAR_ID_PATTERN,
    SCENE_ID_PATTERN,
)

__all__ = [
    "ScriptOutput",
    "Meta",
    "UserInstructions",
    "Character",
    "RoleType",
    "Scene",
    "ContentItem",
    "ContentType",
    "TimeOfDay",
    "CHAR_ID_PATTERN",
    "SCENE_ID_PATTERN",
]
