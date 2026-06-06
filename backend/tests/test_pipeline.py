"""
Pipeline 辅助函数单元测试

测试不需要 LLM API 调用的纯函数：
- 章节拆分
- 角色 ID 生成
- JSON/YAML 清理
- 用户指令格式化
"""

import pytest

from src.pipeline.llm_client import _extract_json
from src.pipeline.orchestrator import (
    _extract_chapter_map,
    _generate_char_id,
    _clean_yaml,
    _format_user_instructions,
    _build_meta,
)


class TestExtractJSON:
    """_extract_json 测试"""

    def test_plain_json(self):
        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_code_block(self):
        result = _extract_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_plain_code_block(self):
        result = _extract_json('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_trailing_text(self):
        result = _extract_json('{"key": "value"} 一些多余的说明文字')
        assert result == {"key": "value"}

    def test_json_with_leading_text(self):
        result = _extract_json('这是解释：\n{"key": "value"}')
        assert result == {"key": "value"}

    def test_no_json_found(self):
        with pytest.raises(ValueError, match="未找到 JSON 对象"):
            _extract_json("纯文本，没有花括号")

    def test_nested_json(self):
        result = _extract_json('{"outer": {"inner": [1, 2, 3]}}')
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_chinese_in_json(self):
        result = _extract_json('{"name": "林墨", "role": "主角"}')
        assert result == {"name": "林墨", "role": "主角"}


class TestExtractChapterMap:
    """章节拆分测试"""

    def test_chinese_chapters(self):
        text = "第1章 初遇\n内容A\n第2章 离别\n内容B\n第3章 重逢\n内容C"
        chapters = _extract_chapter_map(text)
        assert len(chapters) == 3
        assert "第1章 初遇" in chapters
        assert chapters["第1章 初遇"].strip() == "内容A"

    def test_numbered_chapters(self):
        text = "第一章 雨夜\n雨下得很大。\n第二章 剑光\n他拔出了剑。"
        chapters = _extract_chapter_map(text)
        assert len(chapters) == 2

    def test_no_chapters(self):
        text = "这是一段没有章节标记的文本。"
        chapters = _extract_chapter_map(text)
        assert chapters == {}

    def test_prologue(self):
        text = "楔子\n在很久以前…\n第一章 开始\n故事开始了。"
        chapters = _extract_chapter_map(text)
        # 楔子之前的文本不被识别为章节
        assert "第一章 开始" in chapters

    def test_mixed_chinese_numbers(self):
        text = "第1章 初遇\n内容A\n第二章 离别\n内容B\n第3章 重逢\n内容C"
        chapters = _extract_chapter_map(text)
        assert len(chapters) == 3


class TestGenerateCharID:
    """角色 ID 生成测试"""

    def test_english_name(self):
        cid = _generate_char_id("Lin Mo")
        assert cid.startswith("CHAR_")
        assert "LIN" in cid

    def test_chinese_name(self):
        cid = _generate_char_id("林墨")
        assert cid.startswith("CHAR_Z")

    def test_mixed_name(self):
        cid = _generate_char_id("苏晚SuWan")
        assert "SU" in cid


class TestCleanYAML:
    """YAML 清理测试"""

    def test_plain_yaml(self):
        yaml_text = "meta:\n  title: test"
        assert _clean_yaml(yaml_text) == "meta:\n  title: test"

    def test_yaml_with_code_block(self):
        yaml_text = "```yaml\nmeta:\n  title: test\n```"
        result = _clean_yaml(yaml_text)
        assert "meta:" in result
        assert "```" not in result

    def test_yaml_with_plain_block(self):
        yaml_text = "```\nmeta:\n  title: test\n```"
        result = _clean_yaml(yaml_text)
        assert "meta:" in result
        assert "```" not in result


class TestFormatUserInstructions:
    """用户指令格式化测试"""

    def test_empty(self):
        result = _format_user_instructions({})
        assert "无特殊指令" in result

    def test_full(self):
        ui = {
            "selected_chapters": ["第1章", "第2章"],
            "tone": "悬疑",
            "focus_characters": ["林墨", "苏晚"],
            "custom_prompt": "增加打斗场面",
        }
        result = _format_user_instructions(ui)
        assert "第1章, 第2章" in result
        assert "悬疑" in result
        assert "林墨" in result
        assert "增加打斗场面" in result

    def test_partial(self):
        ui = {"tone": "喜剧"}
        result = _format_user_instructions(ui)
        assert "喜剧" in result
        assert "章节" not in result


class TestBuildMeta:
    """meta 构建测试"""

    def test_basic(self):
        novel_text = "第1章 初遇\n内容\n第3章 告别\n内容"
        ui = {"tone": "正剧"}
        meta = _build_meta("剑影", novel_text, ui)
        assert meta["novel_title"] == "剑影"
        assert "剧本版" in meta["script_title"]
        assert "第1章" in meta["adapted_range"]
        assert "第3章" in meta["adapted_range"]
        assert meta["schema_version"] == "1.2.0"
        assert meta["user_instructions"] == ui
        assert "generated_at" in meta

    def test_no_chapters(self):
        meta = _build_meta("短篇", "没有章节标记的文本", {})
        assert meta["adapted_range"] == "全文"
