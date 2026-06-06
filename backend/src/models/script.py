"""
Pydantic 数据模型 — 对应 docs/script_schema.yaml v1.2.0

本模块定义了小说→剧本转换工具的核心数据结构。
所有 AI 输出必须通过 ScriptOutput 模型的校验后才能返回给前端。
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# 枚举类型
# ============================================================

class RoleType(str, Enum):
    """角色重要程度"""
    PROTAGONIST = "主角"
    SUPPORTING = "配角"
    EXTRA = "龙套"


class ContentType(str, Enum):
    """剧本内容块类型"""
    ACTION = "action"           # 动作 / 舞台指示
    DIALOGUE = "dialogue"       # 角色对白
    VOICEOVER = "voiceover"     # 旁白 / 内心独白 / 画外音
    TRANSITION = "transition"   # 转场效果
    SOUND = "sound"             # 音效提示
    NOTE = "note"               # 编剧注释


class TimeOfDay(str, Enum):
    """场景时段"""
    EARLY_MORNING = "清晨"
    MORNING = "上午"
    AFTERNOON = "下午"
    EVENING = "傍晚"
    NIGHT = "夜晚"
    LATE_NIGHT = "深夜"
    DAWN = "黎明"


# ============================================================
# 正则约束
# ============================================================

CHAR_ID_PATTERN = re.compile(r"^CHAR_[A-Z0-9_]+$")
SCENE_ID_PATTERN = re.compile(r"^S\d{4}$")


# ============================================================
# meta — 剧本元信息
# ============================================================

class UserInstructions(BaseModel):
    """用户在前端输入的个性化改编指令"""
    model_config = ConfigDict(extra="forbid")

    selected_chapters: list[str] = Field(
        default_factory=list,
        description="用户具体选择了哪些章节（原始章节名）",
    )
    tone: str = Field(
        default="",
        description="用户期望的剧本基调，如：悬疑、正剧、喜剧等",
    )
    focus_characters: list[str] = Field(
        default_factory=list,
        description="用户希望重点刻画的人物名称",
    )
    custom_prompt: str = Field(
        default="",
        description="用户自由输入的额外改编要求",
    )


class Meta(BaseModel):
    """剧本元信息"""
    model_config = ConfigDict(extra="forbid")

    novel_title: str = Field(..., description="原著小说名称", min_length=1)
    script_title: str = Field(..., description="改编后剧本的独立标题", min_length=1)
    adapted_range: str = Field(..., description="最终改编的章节范围", min_length=1)

    user_instructions: UserInstructions = Field(
        default_factory=UserInstructions,
        description="用户个性化改编指令",
    )
    generated_at: Optional[datetime] = Field(
        default=None,
        description="剧本生成时间（ISO 8601 格式）",
    )
    schema_version: str = Field(
        default="1.2.0",
        description="生成时使用的 Schema 版本号",
    )


# ============================================================
# characters — 角色库
# ============================================================

class Character(BaseModel):
    """单个角色定义"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        description="角色唯一标识符，格式：CHAR_前缀 + 大写拼音/英文",
        pattern=CHAR_ID_PATTERN,
    )
    name: str = Field(..., description="角色在原著中的姓名", min_length=1)
    role_type: RoleType = Field(
        default=RoleType.EXTRA,
        description="角色在剧本中的重要程度",
    )
    traits: list[str] = Field(
        default_factory=list,
        description="角色性格特征标签",
    )
    physical_description: str = Field(
        default="",
        description="角色外貌描述（可选）",
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="角色在原著中的其他称呼（绰号、化名等）",
    )

    # 确保 id 中的空格被正确替换为下划线
    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not CHAR_ID_PATTERN.match(v):
            raise ValueError(
                f"角色 ID '{v}' 格式不合法。"
                f"必须匹配 {CHAR_ID_PATTERN.pattern}"
            )
        return v


# ============================================================
# scenes — 剧本正文
# ============================================================

class ContentItem(BaseModel):
    """场景中的一个内容块"""
    model_config = ConfigDict(extra="forbid")

    type: ContentType = Field(..., description="内容块类型")
    text: str = Field(..., description="内容正文", min_length=1)
    speaker_id: Optional[str] = Field(
        default=None,
        description="说话人的 characters.id（dialogue 必填，voiceover 可选）",
        pattern=CHAR_ID_PATTERN,
    )
    emotion: str = Field(
        default="",
        description="台词的情绪标签",
    )
    ai_confidence: Optional[float] = Field(
        default=None,
        description="AI 对该内容块的生成置信度（0～1）",
        ge=0,
        le=1,
    )

    # dialogue 类型必须提供 speaker_id
    @model_validator(mode="after")
    def check_speaker_for_dialogue(self) -> "ContentItem":
        if self.type == ContentType.DIALOGUE and not self.speaker_id:
            raise ValueError(
                f"类型为 'dialogue' 的内容块必须提供 speaker_id。"
                f"当前 text: '{self.text[:30]}...'" if len(self.text) > 30
                else f"类型为 'dialogue' 的内容块必须提供 speaker_id。当前 text: '{self.text}'"
            )
        return self


class Scene(BaseModel):
    """单个场景"""
    model_config = ConfigDict(extra="forbid")

    scene_id: str = Field(
        ...,
        description="全局唯一场景编号，格式 S0001～S9999",
        pattern=SCENE_ID_PATTERN,
    )
    scene_number: int = Field(
        ...,
        description="场景播放序号（从 1 开始递增）",
        ge=1,
    )
    location: str = Field(..., description="场景地点标识", min_length=1)
    content: list[ContentItem] = Field(
        ...,
        description="场景内容流，按时间顺序排列",
        min_length=1,
    )

    chapter_origin: str = Field(
        default="",
        description="该场景改编自原著的哪个章节",
    )
    time: Optional[TimeOfDay] = Field(
        default=None,
        description="场景发生的大致时段",
    )
    characters_present: list[str] = Field(
        default_factory=list,
        description="本场景出场的角色 ID 列表",
    )

    # 校验 characters_present 中每个 ID 的格式
    @field_validator("characters_present")
    @classmethod
    def validate_character_ids(cls, v: list[str]) -> list[str]:
        for cid in v:
            if not CHAR_ID_PATTERN.match(cid):
                raise ValueError(
                    f"characters_present 中的 ID '{cid}' 格式不合法。"
                    f"必须匹配 {CHAR_ID_PATTERN.pattern}"
                )
        return v


# ============================================================
# 顶层结构
# ============================================================

class ScriptOutput(BaseModel):
    """
    AI 小说→剧本转换的最终输出。
    对应 script_schema.yaml 的顶层结构。
    """
    model_config = ConfigDict(extra="forbid")

    meta: Meta = Field(..., description="剧本元信息")
    characters: list[Character] = Field(
        ...,
        description="全剧角色库（去重合并）",
        min_length=1,
    )
    scenes: list[Scene] = Field(
        ...,
        description="线性剧本正文",
        min_length=1,
    )

    # 交叉校验：scenes 中引用的角色 ID 必须在 characters 库中存在
    @model_validator(mode="after")
    def check_character_references(self) -> "ScriptOutput":
        valid_ids = {c.id for c in self.characters}
        errors: list[str] = []

        for scene in self.scenes:
            # 检查 characters_present
            for cid in scene.characters_present:
                if cid not in valid_ids:
                    errors.append(
                        f"场景 {scene.scene_id} 的 characters_present "
                        f"引用了未定义的角色 ID: '{cid}'"
                    )
            # 检查 content 中的 speaker_id
            for item in scene.content:
                if item.speaker_id and item.speaker_id not in valid_ids:
                    errors.append(
                        f"场景 {scene.scene_id} 的 content 块 "
                        f"引用了未定义的角色 ID: '{item.speaker_id}'"
                    )

        if errors:
            raise ValueError("\n".join(errors))
        return self
