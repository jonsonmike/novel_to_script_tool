"""
Pydantic 数据模型单元测试
覆盖：合法数据 / 必填缺失 / 格式校验 / 交叉引用 / 序列化
"""

import pytest
from pydantic import ValidationError

from src.models.script import (
    ScriptOutput,
    Meta,
    UserInstructions,
    Character,
    Scene,
    ContentItem,
    RoleType,
    ContentType,
    TimeOfDay,
)


# ============================================================
# 辅助函数：构造最小的合法 ScriptOutput
# ============================================================

def make_valid_meta(**overrides) -> Meta:
    """构造合法的 Meta 对象"""
    data = {
        "novel_title": "测试原著",
        "script_title": "测试剧本",
        "adapted_range": "第1章 - 第3章",
    }
    data.update(overrides)
    return Meta(**data)


def make_valid_character(**overrides) -> Character:
    """构造合法的 Character 对象"""
    data = {
        "id": "CHAR_A",
        "name": "角色A",
    }
    data.update(overrides)
    return Character(**data)


def make_valid_scene(**overrides) -> Scene:
    """构造合法的 Scene 对象（自带一个 action 内容块）"""
    data = {
        "scene_id": "S0001",
        "scene_number": 1,
        "location": "测试地点",
        "content": [ContentItem(type=ContentType.ACTION, text="测试动作")],
    }
    data.update(overrides)
    return Scene(**data)


def make_valid_script(**overrides) -> ScriptOutput:
    """构造最小的合法 ScriptOutput"""
    data = {
        "meta": make_valid_meta(),
        "characters": [make_valid_character(id="CHAR_A", name="角色A")],
        "scenes": [make_valid_scene()],
    }
    data.update(overrides)
    return ScriptOutput(**data)


# ============================================================
# Meta 测试
# ============================================================

class TestMeta:
    """Meta 元信息模型测试"""

    def test_valid_meta_minimal(self):
        """最小合法 Meta"""
        m = make_valid_meta()
        assert m.novel_title == "测试原著"
        assert m.script_title == "测试剧本"
        assert m.adapted_range == "第1章 - 第3章"
        # 默认值
        assert m.user_instructions.tone == ""
        assert m.schema_version == "1.2.0"

    def test_valid_meta_full(self):
        """完整 Meta"""
        m = Meta(
            novel_title="剑影",
            script_title="剑影（舞台剧版）",
            adapted_range="第3章 - 第8章",
            user_instructions=UserInstructions(
                selected_chapters=["第3章 初遇", "第4章 离别"],
                tone="悬疑",
                focus_characters=["林墨"],
                custom_prompt="增加打斗场面",
            ),
        )
        assert m.user_instructions.tone == "悬疑"
        assert len(m.user_instructions.selected_chapters) == 2

    def test_missing_novel_title(self):
        """缺少 novel_title"""
        with pytest.raises(ValidationError):
            Meta(script_title="X", adapted_range="1-2")

    def test_missing_script_title(self):
        """缺少 script_title"""
        with pytest.raises(ValidationError):
            Meta(novel_title="X", adapted_range="1-2")

    def test_missing_adapted_range(self):
        """缺少 adapted_range"""
        with pytest.raises(ValidationError):
            Meta(novel_title="X", script_title="X")

    def test_empty_string_rejected(self):
        """空字符串被拒绝（min_length=1）"""
        with pytest.raises(ValidationError):
            Meta(novel_title="", script_title="X", adapted_range="1-2")

    def test_extra_field_forbidden(self):
        """不允许 Meta 中出现未定义字段"""
        with pytest.raises(ValidationError):
            Meta(novel_title="X", script_title="X", adapted_range="1-2", bogus_field=123)

    def test_default_user_instructions(self):
        """不传 user_instructions 时使用默认值"""
        m = Meta(novel_title="X", script_title="X", adapted_range="1-2")
        assert m.user_instructions.tone == ""
        assert m.user_instructions.selected_chapters == []


# ============================================================
# UserInstructions 测试
# ============================================================

class TestUserInstructions:
    """用户指令模型测试"""

    def test_defaults(self):
        """全部字段有默认值"""
        ui = UserInstructions()
        assert ui.selected_chapters == []
        assert ui.tone == ""
        assert ui.focus_characters == []
        assert ui.custom_prompt == ""

    def test_extra_field_forbidden(self):
        """不允许未定义字段"""
        with pytest.raises(ValidationError):
            UserInstructions(unknown=42)


# ============================================================
# Character 测试
# ============================================================

class TestCharacter:
    """角色模型测试"""

    def test_valid_character_minimal(self):
        """最小合法角色"""
        c = Character(id="CHAR_LIN_MO", name="林墨")
        assert c.id == "CHAR_LIN_MO"
        assert c.name == "林墨"
        assert c.role_type == RoleType.EXTRA  # 默认值

    def test_valid_character_full(self):
        """完整角色"""
        c = Character(
            id="CHAR_SU_WAN",
            name="苏晚",
            role_type=RoleType.PROTAGONIST,
            traits=["天真", "善良"],
            physical_description="白衣少女",
            aliases=["婉儿", "苏姑娘"],
        )
        assert c.role_type == RoleType.PROTAGONIST
        assert len(c.traits) == 2
        assert len(c.aliases) == 2

    def test_invalid_id_no_prefix(self):
        """ID 没有 CHAR_ 前缀"""
        with pytest.raises(ValidationError):
            Character(id="LIN_MO", name="林墨")

    def test_invalid_id_lowercase(self):
        """ID 含小写字母"""
        with pytest.raises(ValidationError):
            Character(id="CHAR_lin_mo", name="林墨")

    def test_invalid_id_special_chars(self):
        """ID 含特殊字符"""
        with pytest.raises(ValidationError):
            Character(id="CHAR_LIN-MO", name="林墨")

    def test_invalid_id_chinese(self):
        """ID 含中文"""
        with pytest.raises(ValidationError):
            Character(id="CHAR_林墨", name="林墨")

    def test_valid_id_with_underscore(self):
        """ID 含下划线"""
        c = Character(id="CHAR_LIN_MO", name="林墨")
        assert c.id == "CHAR_LIN_MO"

    def test_valid_id_with_numbers(self):
        """ID 含数字（如 CHAR_SOLDIER_01）"""
        c = Character(id="CHAR_SOLDIER_01", name="士兵1")
        assert c.id == "CHAR_SOLDIER_01"

    def test_missing_name(self):
        """缺少 name"""
        with pytest.raises(ValidationError):
            Character(id="CHAR_A")

    def test_extra_field_forbidden(self):
        """不允许未定义字段"""
        with pytest.raises(ValidationError):
            Character(id="CHAR_A", name="A", bogus=1)


# ============================================================
# ContentItem 测试
# ============================================================

class TestContentItem:
    """内容块模型测试"""

    def test_action(self):
        """action 类型"""
        ci = ContentItem(type=ContentType.ACTION, text="林墨拔剑")
        assert ci.type == ContentType.ACTION
        assert ci.speaker_id is None

    def test_dialogue_with_speaker(self):
        """dialogue 类型带 speaker_id"""
        ci = ContentItem(
            type=ContentType.DIALOGUE,
            text="小心！",
            speaker_id="CHAR_LIN_MO",
            emotion="紧张",
            ai_confidence=0.92,
        )
        assert ci.speaker_id == "CHAR_LIN_MO"
        assert ci.emotion == "紧张"
        assert ci.ai_confidence == 0.92

    def test_dialogue_missing_speaker_fails(self):
        """dialogue 类型缺少 speaker_id 应报错"""
        with pytest.raises(ValidationError):
            ContentItem(type=ContentType.DIALOGUE, text="你好")

    def test_voiceover_without_speaker(self):
        """voiceover 可以不填 speaker_id"""
        ci = ContentItem(type=ContentType.VOICEOVER, text="多年以后...")
        assert ci.speaker_id is None
        assert ci.type == ContentType.VOICEOVER

    def test_voiceover_with_speaker(self):
        """voiceover 也可以填 speaker_id"""
        ci = ContentItem(
            type=ContentType.VOICEOVER,
            text="我永远不会忘记那天...",
            speaker_id="CHAR_LIN_MO",
        )
        assert ci.speaker_id == "CHAR_LIN_MO"

    def test_transition(self):
        """transition 类型"""
        ci = ContentItem(type=ContentType.TRANSITION, text="淡入")
        assert ci.type == ContentType.TRANSITION
        assert ci.speaker_id is None

    def test_sound(self):
        """sound 类型"""
        ci = ContentItem(type=ContentType.SOUND, text="远处传来马蹄声")
        assert ci.type == ContentType.SOUND

    def test_note(self):
        """note 类型（编剧注释）"""
        ci = ContentItem(type=ContentType.NOTE, text="此处需要特效")
        assert ci.type == ContentType.NOTE

    def test_invalid_type(self):
        """非法的 content type"""
        with pytest.raises(ValidationError):
            ContentItem(type="monologue", text="独白")  # 不在 enum 中

    def test_confidence_below_zero(self):
        """置信度小于 0"""
        with pytest.raises(ValidationError):
            ContentItem(type=ContentType.ACTION, text="test", ai_confidence=-0.1)

    def test_confidence_above_one(self):
        """置信度大于 1"""
        with pytest.raises(ValidationError):
            ContentItem(type=ContentType.ACTION, text="test", ai_confidence=1.1)

    def test_confidence_boundary_values(self):
        """置信度边界值"""
        ci0 = ContentItem(type=ContentType.ACTION, text="t", ai_confidence=0.0)
        assert ci0.ai_confidence == 0.0
        ci1 = ContentItem(type=ContentType.ACTION, text="t", ai_confidence=1.0)
        assert ci1.ai_confidence == 1.0

    def test_invalid_speaker_id_pattern(self):
        """非法的 speaker_id 格式"""
        with pytest.raises(ValidationError):
            ContentItem(
                type=ContentType.DIALOGUE,
                text="你好",
                speaker_id="林墨",  # 缺少 CHAR_ 前缀
            )

    def test_empty_text_rejected(self):
        """空 text 被拒绝"""
        with pytest.raises(ValidationError):
            ContentItem(type=ContentType.ACTION, text="")

    def test_missing_text(self):
        """缺少 text"""
        with pytest.raises(ValidationError):
            ContentItem(type=ContentType.ACTION)

    def test_extra_field_forbidden(self):
        """不允许未定义字段"""
        with pytest.raises(ValidationError):
            ContentItem(type=ContentType.ACTION, text="test", duration=120)


# ============================================================
# Scene 测试
# ============================================================

class TestScene:
    """场景模型测试"""

    def test_valid_scene_minimal(self):
        """最小合法 Scene"""
        s = Scene(
            scene_id="S0001",
            scene_number=1,
            location="内景 大殿",
            content=[ContentItem(type=ContentType.ACTION, text="开场")],
        )
        assert s.scene_id == "S0001"
        assert s.scene_number == 1
        assert s.characters_present == []
        assert s.chapter_origin == ""
        assert s.time is None

    def test_valid_scene_full(self):
        """完整 Scene"""
        s = Scene(
            scene_id="S0012",
            scene_number=12,
            location="外景 校场 — 夜",
            chapter_origin="第5章",
            time=TimeOfDay.NIGHT,
            characters_present=["CHAR_LIN_MO", "CHAR_SU_WAN"],
            content=[
                ContentItem(type=ContentType.TRANSITION, text="切至校场"),
                ContentItem(type=ContentType.DIALOGUE, text="来吧。", speaker_id="CHAR_LIN_MO", emotion="冷静"),
            ],
        )
        assert s.time == TimeOfDay.NIGHT
        assert len(s.characters_present) == 2
        assert len(s.content) == 2

    def test_invalid_scene_id_format(self):
        """非法的 scene_id 格式"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="S001",  # 只有 3 位数字
                scene_number=1,
                location="Test",
                content=[ContentItem(type=ContentType.ACTION, text="test")],
            )

    def test_invalid_scene_id_no_prefix(self):
        """scene_id 缺少 S 前缀"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="0001",
                scene_number=1,
                location="Test",
                content=[ContentItem(type=ContentType.ACTION, text="test")],
            )

    def test_scene_number_zero_rejected(self):
        """scene_number 为 0 应报错"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="S0001",
                scene_number=0,
                location="Test",
                content=[ContentItem(type=ContentType.ACTION, text="test")],
            )

    def test_scene_number_negative_rejected(self):
        """scene_number 为负数应报错"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="S0001",
                scene_number=-1,
                location="Test",
                content=[ContentItem(type=ContentType.ACTION, text="test")],
            )

    def test_empty_content_rejected(self):
        """content 为空数组应报错"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="S0001",
                scene_number=1,
                location="Test",
                content=[],
            )

    def test_missing_location(self):
        """缺少 location"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="S0001",
                scene_number=1,
                content=[ContentItem(type=ContentType.ACTION, text="test")],
            )

    def test_invalid_characters_present_id(self):
        """characters_present 中的 ID 格式不合法"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="S0001",
                scene_number=1,
                location="Test",
                characters_present=["林墨"],  # 不是 CHAR_xxx 格式
                content=[ContentItem(type=ContentType.ACTION, text="test")],
            )

    def test_valid_scene_id_boundary(self):
        """scene_id 边界值 S0000 和 S9999"""
        s1 = Scene(scene_id="S0000", scene_number=1, location="T", content=[ContentItem(type=ContentType.ACTION, text="t")])
        assert s1.scene_id == "S0000"
        s2 = Scene(scene_id="S9999", scene_number=2, location="T", content=[ContentItem(type=ContentType.ACTION, text="t")])
        assert s2.scene_id == "S9999"

    def test_extra_field_forbidden(self):
        """不允许未定义字段"""
        with pytest.raises(ValidationError):
            Scene(
                scene_id="S0001",
                scene_number=1,
                location="Test",
                content=[ContentItem(type=ContentType.ACTION, text="test")],
                director_note="should not be here",
            )


# ============================================================
# ScriptOutput 顶层测试
# ============================================================

class TestScriptOutput:
    """顶层 ScriptOutput 模型测试"""

    def test_valid_script_minimal(self):
        """最小合法脚本"""
        s = make_valid_script()
        assert s.meta.novel_title == "测试原著"
        assert len(s.characters) == 1
        assert len(s.scenes) == 1

    def test_valid_script_full(self):
        """完整多角色多场景脚本"""
        s = ScriptOutput(
            meta=Meta(
                novel_title="剑影",
                script_title="剑影（舞台剧版）",
                adapted_range="第1章 - 第3章",
                user_instructions=UserInstructions(
                    selected_chapters=["第1章", "第2章", "第3章"],
                    tone="悬疑",
                    focus_characters=["林墨"],
                    custom_prompt="压缩支线",
                ),
            ),
            characters=[
                Character(id="CHAR_LIN_MO", name="林墨", role_type=RoleType.PROTAGONIST, traits=["冷静", "腹黑"]),
                Character(id="CHAR_SU_WAN", name="苏晚", role_type=RoleType.PROTAGONIST, traits=["天真"]),
            ],
            scenes=[
                Scene(
                    scene_id="S0001",
                    scene_number=1,
                    location="内景 王府书房",
                    chapter_origin="第1章",
                    time=TimeOfDay.NIGHT,
                    characters_present=["CHAR_LIN_MO"],
                    content=[
                        ContentItem(type=ContentType.ACTION, text="林墨推门而入"),
                        ContentItem(type=ContentType.DIALOGUE, text="有人来过。", speaker_id="CHAR_LIN_MO", emotion="警惕"),
                    ],
                ),
                Scene(
                    scene_id="S0002",
                    scene_number=2,
                    location="外景 花园",
                    chapter_origin="第2章",
                    time=TimeOfDay.MORNING,
                    characters_present=["CHAR_LIN_MO", "CHAR_SU_WAN"],
                    content=[
                        ContentItem(type=ContentType.DIALOGUE, text="你是谁？", speaker_id="CHAR_SU_WAN", emotion="好奇"),
                        ContentItem(type=ContentType.DIALOGUE, text="过路人。", speaker_id="CHAR_LIN_MO", emotion="冷淡"),
                    ],
                ),
            ],
        )
        assert len(s.scenes) == 2
        assert len(s.characters) == 2
        # 交叉引用应通过
        dict_data = s.model_dump()
        assert dict_data["meta"]["novel_title"] == "剑影"

    def test_empty_characters_rejected(self):
        """characters 为空数组应报错"""
        with pytest.raises(ValidationError):
            make_valid_script(characters=[])

    def test_empty_scenes_rejected(self):
        """scenes 为空数组应报错"""
        with pytest.raises(ValidationError):
            make_valid_script(scenes=[])

    def test_characters_present_refs_bogus_id(self):
        """characters_present 引用不存在的角色 ID"""
        with pytest.raises(ValidationError):
            ScriptOutput(
                meta=make_valid_meta(),
                characters=[make_valid_character(id="CHAR_A", name="A")],
                scenes=[
                    Scene(
                        scene_id="S0001",
                        scene_number=1,
                        location="Test",
                        characters_present=["CHAR_BOGUS"],
                        content=[ContentItem(type=ContentType.ACTION, text="test")],
                    ),
                ],
            )

    def test_speaker_id_refs_bogus_id(self):
        """speaker_id 引用不存在的角色 ID（dialogue 类型）"""
        with pytest.raises(ValidationError):
            ScriptOutput(
                meta=make_valid_meta(),
                characters=[make_valid_character(id="CHAR_A", name="A")],
                scenes=[
                    Scene(
                        scene_id="S0001",
                        scene_number=1,
                        location="Test",
                        content=[
                            ContentItem(
                                type=ContentType.DIALOGUE,
                                text="你好",
                                speaker_id="CHAR_BOGUS",
                            ),
                        ],
                    ),
                ],
            )

    def test_extra_field_forbidden_top_level(self):
        """顶层不允许未定义字段"""
        with pytest.raises(ValidationError):
            make_valid_script(extra_field="should not exist")

    def test_serialization_roundtrip(self):
        """model_dump 后重新构造应相等"""
        s1 = make_valid_script()
        data = s1.model_dump()
        s2 = ScriptOutput(**data)
        assert s2.meta.novel_title == s1.meta.novel_title
        assert s2.characters[0].id == s1.characters[0].id
        assert s2.scenes[0].scene_id == s1.scenes[0].scene_id

    def test_json_serialization(self):
        """model_dump_json 可正常序列化"""
        s = make_valid_script()
        json_str = s.model_dump_json()
        assert len(json_str) > 0
        assert '"novel_title"' in json_str

    def test_missing_meta(self):
        """缺少 meta"""
        with pytest.raises(ValidationError):
            ScriptOutput(
                characters=[make_valid_character()],
                scenes=[make_valid_scene()],
            )

    def test_missing_characters(self):
        """缺少 characters"""
        with pytest.raises(ValidationError):
            ScriptOutput(
                meta=make_valid_meta(),
                scenes=[make_valid_scene()],
            )

    def test_missing_scenes(self):
        """缺少 scenes"""
        with pytest.raises(ValidationError):
            ScriptOutput(
                meta=make_valid_meta(),
                characters=[make_valid_character()],
            )


# ============================================================
# 集成测试：用 YAML Schema 中的示例数据验证
# ============================================================

class TestSchemaExamples:
    """用 script_schema.yaml 文档中的示例数据验证"""

    def test_full_example(self):
        """构造一个接近真实使用的完整剧本并验证"""
        script = ScriptOutput(
            meta=Meta(
                novel_title="剑影",
                script_title="剑影（舞台剧改编版）",
                adapted_range="第3章 - 第8章",
                user_instructions=UserInstructions(
                    selected_chapters=["第3章 初遇", "第4章 离别"],
                    tone="悬疑",
                    focus_characters=["林墨"],
                    custom_prompt="把打斗场面写得更加激烈，增加男主角的心理活动。",
                ),
            ),
            characters=[
                Character(
                    id="CHAR_LIN_MO",
                    name="林墨",
                    role_type=RoleType.PROTAGONIST,
                    traits=["冷静", "腹黑", "武艺高强"],
                ),
                Character(
                    id="CHAR_SU_WAN",
                    name="苏晚",
                    role_type=RoleType.PROTAGONIST,
                    traits=["天真", "善良", "医术精湛"],
                ),
                Character(
                    id="CHAR_ZHANG_YUAN",
                    name="张远",
                    role_type=RoleType.SUPPORTING,
                    traits=["豪爽", "话多"],
                    aliases=["老张", "张大哥"],
                ),
            ],
            scenes=[
                Scene(
                    scene_id="S0001",
                    scene_number=1,
                    location="内景 王府书房 — 日",
                    chapter_origin="第3章 初遇",
                    time=TimeOfDay.AFTERNOON,
                    characters_present=["CHAR_LIN_MO", "CHAR_SU_WAN"],
                    content=[
                        ContentItem(
                            type=ContentType.TRANSITION,
                            text="淡入",
                            ai_confidence=0.99,
                        ),
                        ContentItem(
                            type=ContentType.ACTION,
                            text="林墨站在书架前，手指轻抚过一排古籍。",
                            ai_confidence=0.95,
                        ),
                        ContentItem(
                            type=ContentType.DIALOGUE,
                            text="小心，这里有东西。",
                            speaker_id="CHAR_LIN_MO",
                            emotion="紧张",
                            ai_confidence=0.88,
                        ),
                        ContentItem(
                            type=ContentType.SOUND,
                            text="窗外传来乌鸦的叫声",
                            ai_confidence=0.92,
                        ),
                    ],
                ),
            ],
        )
        # 验证结构
        assert script.meta.novel_title == "剑影"
        assert len(script.characters) == 3
        assert script.scenes[0].scene_id == "S0001"
        assert len(script.scenes[0].content) == 4
        # 验证序列化
        data = script.model_dump()
        assert data["characters"][1]["aliases"] == []
        assert data["scenes"][0]["content"][2]["emotion"] == "紧张"
