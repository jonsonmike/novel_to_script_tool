"""
Pipeline 辅助函数单元测试

测试不需要 LLM API 调用的纯函数：
- 章节拆分
- 角色 ID 生成
- JSON/YAML 清理
- 用户指令格式化
- chat_json 重试机制（mock LLM 调用）
"""

from unittest.mock import patch

import pytest

from src.pipeline.llm_client import _extract_json, _append_retry_hint, chat_json
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


class TestAppendRetryHint:
    """_append_retry_hint 格式测试"""

    def test_appends_error_info(self):
        """重试提示包含错误信息和修复指引"""
        original = "请提取角色"
        result = _append_retry_hint(
            original,
            failed_output="...这不是 JSON...",
            error_msg="Expecting value: line 1 column 1",
        )
        assert original in result
        assert "格式错误" in result
        assert "Expecting value" in result
        assert "纯 JSON" in result

    def test_truncates_long_output(self):
        """上次输出的内容被截断到 300 字符以内"""
        long_output = "x" * 1000
        result = _append_retry_hint("prompt", long_output, "error")
        assert result.count("x") < 500


class TestChatJsonRetry:
    """chat_json 重试机制测试（mock LLM 调用）"""

    VALID_JSON = '{"characters": [{"id": "CHAR_LIN_MO", "name": "林墨"}]}'
    BAD_JSON = "好的，以下是他角色的列表：林墨，苏晚。"

    def test_succeeds_on_first_attempt(self):
        """第一次就返回合法 JSON，不触发重试"""
        call_count = [0]

        def mock_chat(_sys, _usr, **__):
            call_count[0] += 1
            return self.VALID_JSON

        with patch("src.pipeline.llm_client.chat", side_effect=mock_chat):
            result = chat_json("sys", "user")
            assert call_count[0] == 1
            assert result == {"characters": [{"id": "CHAR_LIN_MO", "name": "林墨"}]}

    def test_retries_and_succeeds(self):
        """第一次返回非法 JSON，重试后返回合法 JSON → 成功"""
        call_count = [0]

        def mock_chat(_sys, _usr, **__):
            call_count[0] += 1
            if call_count[0] == 1:
                return self.BAD_JSON
            else:
                return self.VALID_JSON

        with patch("src.pipeline.llm_client.chat", side_effect=mock_chat):
            result = chat_json("sys", "user")
            assert call_count[0] == 2
            assert result == {"characters": [{"id": "CHAR_LIN_MO", "name": "林墨"}]}

    def test_retries_twice_then_succeeds(self):
        """前两次都失败，第三次成功 → 用完默认 2 次重试"""
        call_count = [0]

        def mock_chat(_sys, _usr, **__):
            call_count[0] += 1
            if call_count[0] <= 2:
                return self.BAD_JSON
            else:
                return self.VALID_JSON

        with patch("src.pipeline.llm_client.chat", side_effect=mock_chat):
            result = chat_json("sys", "user")
            assert call_count[0] == 3
            assert result == {"characters": [{"id": "CHAR_LIN_MO", "name": "林墨"}]}

    def test_raises_after_all_retries_exhausted(self):
        """所有尝试都返回非法 JSON → 抛出 RuntimeError"""
        call_count = [0]

        def mock_chat(_sys, _usr, **__):
            call_count[0] += 1
            return self.BAD_JSON

        with patch("src.pipeline.llm_client.chat", side_effect=mock_chat):
            with pytest.raises(RuntimeError, match="重试"):
                chat_json("sys", "user")
            assert call_count[0] == 3

    def test_custom_max_retries(self):
        """max_retries=5 时重试 5 次后才报错"""
        call_count = [0]

        def mock_chat(_sys, _usr, **__):
            call_count[0] += 1
            return self.BAD_JSON

        with patch("src.pipeline.llm_client.chat", side_effect=mock_chat):
            with pytest.raises(RuntimeError):
                chat_json("sys", "user", max_retries=5)
            assert call_count[0] == 6

    def test_retry_prompt_includes_error_info(self):
        """重试时 prompt 包含上一次的错误原因"""
        captured_prompts = []

        def mock_chat(_sys, usr, **__):
            captured_prompts.append(usr)
            if len(captured_prompts) == 1:
                return self.BAD_JSON
            else:
                return self.VALID_JSON

        with patch("src.pipeline.llm_client.chat", side_effect=mock_chat):
            chat_json("sys", "请提取角色")
            assert captured_prompts[0] == "请提取角色"
            assert "格式错误" in captured_prompts[1]
            assert "纯 JSON" in captured_prompts[1]

    def test_code_block_not_counted_as_retry(self):
        """LLM 返回 ```json {...} ``` 格式 → 第一次就解析成功，不浪费重试"""
        call_count = [0]

        def mock_chat(_sys, _usr, **__):
            call_count[0] += 1
            return '```json\n{"key": "value"}\n```'

        with patch("src.pipeline.llm_client.chat", side_effect=mock_chat):
            result = chat_json("sys", "user")
            assert call_count[0] == 1
            assert result == {"key": "value"}
