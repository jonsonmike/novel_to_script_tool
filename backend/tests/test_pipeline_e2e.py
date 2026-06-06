"""
端到端集成测试 — 完整 Pipeline 流程

用 mock LLM 返回模拟数据，测试从小说文本到最终剧本的完整转换流程。
"""

from unittest.mock import patch

import pytest

from src.pipeline.orchestrator import run_pipeline


# ── mock LLM 返回的假数据 ──────────────────────────────

MOCK_CHARACTERS = {
    "characters": [
        {
            "id": "CHAR_LIN_MO",
            "name": "林墨",
            "role_type": "主角",
            "traits": ["冷静", "武艺高强"],
            "physical_description": "青衫剑客",
            "aliases": ["墨儿"],
        },
        {
            "id": "CHAR_SU_WAN",
            "name": "苏晚",
            "role_type": "主角",
            "traits": ["医术精湛", "沉稳"],
            "physical_description": "白衣女子",
            "aliases": ["苏姑娘"],
        },
    ],
}

MOCK_SCENES = {
    "scenes": [
        {
            "scene_id": "S0001",
            "scene_number": 1,
            "chapter_origin": "第1章 夜雨客栈",
            "location": "内景 清风客栈大堂 — 夜",
            "time": "夜晚",
            "characters_present": ["CHAR_LIN_MO"],
            "summary": "林墨在雨夜住进客栈，察觉到埋伏",
        },
        {
            "scene_id": "S0002",
            "scene_number": 2,
            "chapter_origin": "第2章 剑光破晓",
            "location": "内景 客栈柴房 — 夜",
            "time": "深夜",
            "characters_present": ["CHAR_LIN_MO"],
            "summary": "林墨击败三名杀手",
        },
    ],
}

MOCK_CONTENT_1 = {
    "content": [
        {"type": "action", "text": "林墨推开门，湿透的青衫紧贴在身上。", "ai_confidence": 0.95},
        {"type": "dialogue", "text": "住店。", "speaker_id": "CHAR_LIN_MO", "emotion": "平静", "ai_confidence": 0.92},
    ],
}

MOCK_CONTENT_2 = {
    "content": [
        {"type": "action", "text": "林墨坐在黑暗中，将长剑横放膝上。", "ai_confidence": 0.93},
        {"type": "dialogue", "text": "回去告诉你们主子，密函的事，我林墨自己会查清楚。", "speaker_id": "CHAR_LIN_MO", "emotion": "冷峻", "ai_confidence": 0.90},
    ],
}

MOCK_YAML = """meta:
  novel_title: "剑影夜雨"
  script_title: "剑影夜雨（剧本版）"
  adapted_range: "第1章 - 第2章"
  user_instructions: {}
  generated_at: "2025-01-01T00:00:00Z"
  schema_version: "1.2.0"

characters:
  - id: CHAR_LIN_MO
    name: "林墨"
    role_type: "主角"
    traits: ["冷静", "武艺高强"]
    physical_description: "青衫剑客"
    aliases: ["墨儿"]
  - id: CHAR_SU_WAN
    name: "苏晚"
    role_type: "主角"
    traits: ["医术精湛", "沉稳"]
    physical_description: "白衣女子"
    aliases: ["苏姑娘"]

scenes:
  - scene_id: S0001
    scene_number: 1
    chapter_origin: "第1章 夜雨客栈"
    location: "内景 清风客栈大堂 — 夜"
    time: "夜晚"
    characters_present: ["CHAR_LIN_MO"]
    content:
      - type: action
        text: "林墨推开门，湿透的青衫紧贴在身上。"
        ai_confidence: 0.95
      - type: dialogue
        text: "住店。"
        speaker_id: CHAR_LIN_MO
        emotion: "平静"
        ai_confidence: 0.92
  - scene_id: S0002
    scene_number: 2
    chapter_origin: "第2章 剑光破晓"
    location: "内景 客栈柴房 — 夜"
    time: "深夜"
    characters_present: ["CHAR_LIN_MO"]
    content:
      - type: action
        text: "林墨坐在黑暗中，将长剑横放膝上。"
        ai_confidence: 0.93
      - type: dialogue
        text: "回去告诉你们主子，密函的事，我林墨自己会查清楚。"
        speaker_id: CHAR_LIN_MO
        emotion: "冷峻"
        ai_confidence: 0.90
"""


# ── 测试 ──────────────────────────────────────────────


class TestPipelineE2E:
    """端到端测试：模拟 LLM 调用，测试完整 Pipeline"""

    NOVEL = "第1章 夜雨客栈\n夜幕低垂，暴雨如注。林墨推开门走了进去。\n第2章 剑光破晓\n林墨坐在黑暗中。"

    def _make_mock_chat(self):
        """创建模拟 LLM 调用的函数"""
        call_count = {"count": 0}

        def mock_chat_json(system_prompt, user_prompt, **kwargs):
            call_count["count"] += 1
            n = call_count["count"]
            if n == 1:
                return MOCK_CHARACTERS
            elif n == 2:
                return MOCK_SCENES
            elif n == 3:
                return MOCK_CONTENT_1
            elif n == 4:
                return MOCK_CONTENT_2
            else:
                return {"content": []}

        return mock_chat_json, call_count

    def test_full_pipeline_basic(self):
        """基本流程：小说 → 2 角色 + 2 场景 → 完整剧本"""
        mock_json, call_count = self._make_mock_chat()
        progress = []

        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=MOCK_YAML):
            result = run_pipeline(
                novel_text=self.NOVEL,
                novel_title="剑影夜雨",
                user_instructions={"tone": "正剧"},
                on_progress=lambda pct, msg: progress.append((pct, msg)),
            )

        # 验证 LLM 调用次数：阶段1 + 阶段2 + 阶段3(2场景) = 4次 JSON + 1次文本
        assert call_count["count"] == 4

        # 验证输出结构
        assert "meta" in result.script
        assert "characters" in result.script
        assert "scenes" in result.script
        assert result.script["meta"]["novel_title"] == "剑影夜雨"
        assert len(result.script["characters"]) == 2
        assert len(result.script["scenes"]) == 2
        assert result.total_tokens_used > 0

        # 验证 YAML 输出非空
        assert result.yaml_text
        assert "meta:" in result.yaml_text

        # 验证进度回调被调用
        assert len(progress) > 0
        assert progress[-1][0] == 100  # 最终进度是 100

    def test_pipeline_with_user_instructions(self):
        """带用户指令的转换"""
        mock_json, _ = self._make_mock_chat()

        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=MOCK_YAML):
            result = run_pipeline(
                novel_text=self.NOVEL,
                novel_title="测试",
                user_instructions={
                    "selected_chapters": ["第1章 夜雨客栈"],
                    "tone": "悬疑",
                    "focus_characters": ["林墨"],
                    "custom_prompt": "增加打斗场面",
                },
            )

        assert result.script["meta"]["user_instructions"]["tone"] == "悬疑"
        assert result.script["meta"]["user_instructions"]["focus_characters"] == ["林墨"]
        assert result.script["meta"]["user_instructions"]["custom_prompt"] == "增加打斗场面"

    def test_pipeline_pydantic_validation(self):
        """Pipeline 输出能通过 Pydantic 校验"""
        from src.models.script import ScriptOutput

        mock_json, _ = self._make_mock_chat()

        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=MOCK_YAML):
            result = run_pipeline(
                novel_text=self.NOVEL,
                novel_title="剑影夜雨",
            )

        # 应该能通过 Pydantic 校验
        validated = ScriptOutput(**result.script)
        assert validated.meta.novel_title == "剑影夜雨"
        assert len(validated.characters) == 2
        assert len(validated.scenes) == 2

    def test_pipeline_yaml_parse_fallback(self):
        """LLM 返回格式错误的 YAML 时，回退到手工组装"""
        mock_json, _ = self._make_mock_chat()
        import yaml

        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value="some text"), \
             patch("src.pipeline.orchestrator.yaml.safe_load", side_effect=yaml.YAMLError("解析失败")):
            result = run_pipeline(
                novel_text=self.NOVEL,
                novel_title="剑影夜雨",
            )

        # 应该回退到手工组装的 dict（用代码计算的数据）
        assert "meta" in result.script
        assert len(result.script["characters"]) == 2
        assert len(result.script["scenes"]) == 2

    def test_pipeline_cleans_summary_fields(self):
        """阶段 2 产生的临时 summary 字段在输出中被清除"""
        mock_json, _ = self._make_mock_chat()

        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=MOCK_YAML):
            result = run_pipeline(
                novel_text=self.NOVEL,
                novel_title="剑影夜雨",
            )

        for scene in result.script["scenes"]:
            assert "summary" not in scene, f"场景 {scene.get('scene_id')} 不应保留 summary 字段"

    def test_pipeline_single_character(self):
        """只有一个角色的场景也能正常处理"""
        single_char = {
            "characters": [
                {"id": "CHAR_X", "name": "神秘人", "role_type": "配角", "traits": [], "aliases": []},
            ],
        }
        single_scene = {
            "scenes": [
                {
                    "scene_id": "S0001",
                    "scene_number": 1,
                    "chapter_origin": "",
                    "location": "外景 荒野",
                    "time": "夜晚",
                    "characters_present": ["CHAR_X"],
                    "summary": "",
                },
            ],
        }
        single_content = {
            "content": [
                {"type": "action", "text": "神秘人独自站在荒野中。", "ai_confidence": 0.95},
            ],
        }

        def mock_json_call(_, __, **___):
            return single_char  # 只被调用一次

        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=[single_char, single_scene, single_content]), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=MOCK_YAML):
            result = run_pipeline(
                novel_text="一个短篇小说。",
                novel_title="短篇",
            )

        assert len(result.script["characters"]) == 1
        assert len(result.script["scenes"]) == 1


class TestPipelineEdgeCases:
    """边界情况测试"""

    NOVEL = "第1章 开始\n这是一个故事。"

    def test_pipeline_with_braces_in_text(self):
        """小说原文含花括号 {} 时不应崩溃"""
        novel_with_braces = '第1章 测试\n他说："{你好}"然后笑了笑。\n另一个角色回答："{再见}"。'

        mock_json = [{"characters": [{"id": "CHAR_TEST", "name": "测试", "role_type": "主角", "traits": [], "aliases": []}]},
                     {"scenes": [{"scene_id": "S0001", "scene_number": 1, "chapter_origin": "", "location": "测试", "time": "上午", "characters_present": ["CHAR_TEST"], "summary": ""}]},
                     {"content": [{"type": "action", "text": "发生了事情。", "ai_confidence": 0.9}]}]

        yaml_text = "meta:\n  novel_title: 测试\n"

        from src.pipeline.orchestrator import run_pipeline
        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=yaml_text):
            result = run_pipeline(
                novel_text=novel_with_braces,
                novel_title="测试",
            )

        assert result.script["meta"]["novel_title"] == "测试"

    def test_pipeline_empty_user_instructions(self):
        """user_instructions 为空时 Pydantic 填入默认空值，不应出错"""
        mock_json, _ = TestPipelineE2E()._make_mock_chat()

        from src.pipeline.orchestrator import run_pipeline
        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=MOCK_YAML):
            result = run_pipeline(
                novel_text=self.NOVEL,
                novel_title="测试",
                user_instructions={},
            )

        ui = result.script["meta"]["user_instructions"]
        assert ui["tone"] == ""
        assert ui["selected_chapters"] == []
        assert ui["focus_characters"] == []
        assert ui["custom_prompt"] == ""

    def test_pipeline_none_user_instructions(self):
        """user_instructions 为 None 时等同空 dict，不应出错"""
        mock_json, _ = TestPipelineE2E()._make_mock_chat()

        from src.pipeline.orchestrator import run_pipeline
        with patch("src.pipeline.orchestrator.llm_client.chat_json", side_effect=mock_json), \
             patch("src.pipeline.orchestrator.llm_client.chat", return_value=MOCK_YAML):
            result = run_pipeline(
                novel_text=self.NOVEL,
                novel_title="测试",
                user_instructions=None,
            )

        ui = result.script["meta"]["user_instructions"]
        assert ui["tone"] == ""
        assert ui["selected_chapters"] == []
        assert ui["focus_characters"] == []
        assert ui["custom_prompt"] == ""
