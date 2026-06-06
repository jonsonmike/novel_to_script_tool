"""
AI 转换流水线编排器

将 4 个阶段串联执行，实现小说文本 → 结构化剧本的完整流程。

流程：
  小说文本
    → 阶段 1: 角色实体提取 → characters[]
    → 阶段 2: 场景拆分       → scenes[] 骨架
    → 阶段 3: 内容生成（按场景）→ scenes[] 填充 content
    → 阶段 4: 格式组装       → 最终 YAML
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import yaml

from . import llm_client
from .prompts import extraction, splitting, generation, assembly
from ..models.script import ScriptOutput


def _safe_fmt(text: str) -> str:
    """转义花括号，防止用户输入中的 {} 被 str.format() 当作占位符"""
    return text.replace("{", "{{").replace("}", "}}")


# ── 进度回调类型 ──────────────────────────────────────────
ProgressCallback = Callable[[int, str], None]
# (progress: 0-100, message: str)


@dataclass
class PipelineResult:
    """Pipeline 执行结果"""
    script: dict[str, Any]   # 完整的剧本数据（符合 ScriptOutput Schema）
    yaml_text: str            # YAML 格式的剧本
    total_tokens_used: int    # 消耗的 token 总数（估算）


def run_pipeline(
    novel_text: str,
    novel_title: str,
    user_instructions: dict[str, Any] | None = None,
    *,
    on_progress: ProgressCallback | None = None,
) -> PipelineResult:
    """
    执行完整的 AI 转换流水线。

    Args:
        novel_text: 小说原文（完整文本，含章节标记）
        novel_title: 原著标题
        user_instructions: 用户的改编指令（tone, focus_characters, custom_prompt 等）
        on_progress: 进度回调 (0-100, message)

    Returns:
        PipelineResult（剧本 dict + YAML 文本 + token 估算）

    Raises:
        RuntimeError: 任何阶段失败
    """
    instructions = user_instructions or {}
    instructions_str = _format_user_instructions(instructions)
    total_tokens = 0

    def _pct(pct: int, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    # ── 阶段 1: 角色提取 ──────────────────────────────────
    _pct(5, "正在提取角色信息…")
    user_prompt_1 = extraction.USER_PROMPT_TEMPLATE.format(
        novel_text=_safe_fmt(novel_text),
        user_instructions=_safe_fmt(instructions_str),
    )
    characters_data = llm_client.chat_json(
        extraction.SYSTEM_PROMPT,
        user_prompt_1,
        max_tokens=4000,
    )
    characters: list[dict[str, Any]] = characters_data.get("characters", [])
    total_tokens += _estimate_tokens(extraction.SYSTEM_PROMPT + user_prompt_1, 4000)

    # 校验角色 ID 格式
    for ch in characters:
        if not re.match(r"^CHAR_[A-Z0-9_]+$", ch.get("id", "")):
            ch["id"] = _generate_char_id(ch.get("name", "UNKNOWN"))

    _pct(25, f"已提取 {len(characters)} 个角色")

    # ── 阶段 2: 场景拆分 ──────────────────────────────────
    _pct(30, "正在拆分场景…")
    user_prompt_2 = splitting.USER_PROMPT_TEMPLATE.format(
        novel_text=_safe_fmt(novel_text),
        characters_json=_safe_fmt(json.dumps(characters, ensure_ascii=False, indent=2)),
        user_instructions=_safe_fmt(instructions_str),
    )
    scenes_data = llm_client.chat_json(
        splitting.SYSTEM_PROMPT,
        user_prompt_2,
        max_tokens=6000,
    )
    scenes: list[dict[str, Any]] = scenes_data.get("scenes", [])
    total_tokens += _estimate_tokens(splitting.SYSTEM_PROMPT + user_prompt_2, 6000)

    _pct(50, f"已拆分出 {len(scenes)} 个场景")

    # ── 阶段 3: 内容生成（每个场景独立调用） ──────────────
    _pct(55, "正在生成剧本内容…")
    chapters = _extract_chapter_map(novel_text)

    for i, scene in enumerate(scenes):
        scene_pct = 55 + int(35 * (i + 1) / max(len(scenes), 1))
        _pct(scene_pct, f"正在生成第 {i + 1}/{len(scenes)} 场…")

        # 找到相关原文片段
        chapter_ref = scene.get("chapter_origin", "")
        novel_excerpt = _find_relevant_excerpt(novel_text, chapter_ref, chapters)

        scene_info = json.dumps({
            "scene_number": scene.get("scene_number", i + 1),
            "chapter_origin": chapter_ref,
            "location": scene.get("location", ""),
            "time": scene.get("time", ""),
            "characters_present": scene.get("characters_present", []),
        }, ensure_ascii=False, indent=2)

        user_prompt_3 = generation.USER_PROMPT_TEMPLATE.format(
            novel_excerpt=_safe_fmt(novel_excerpt),
            scene_info=_safe_fmt(scene_info),
            characters_json=_safe_fmt(json.dumps(characters, ensure_ascii=False, indent=2)),
            user_instructions=_safe_fmt(instructions_str),
        )
        content_data = llm_client.chat_json(
            generation.SYSTEM_PROMPT,
            user_prompt_3,
            max_tokens=4000,
        )
        total_tokens += _estimate_tokens(generation.SYSTEM_PROMPT + user_prompt_3, 4000)

        # 填入 content，移除临时的 summary 字段
        scene["content"] = content_data.get("content", [])
        scene.pop("summary", None)

        # 校验 content 块
        for block in scene["content"]:
            if block.get("type") == "dialogue" and not block.get("speaker_id"):
                block["type"] = "voiceover"

    _pct(90, "内容生成完毕，正在组装剧本…")

    # ── 阶段 4: 格式组装 ──────────────────────────────────
    meta = _build_meta(novel_title, novel_text, instructions)
    user_prompt_4 = assembly.USER_PROMPT_TEMPLATE.format(
        meta_json=_safe_fmt(json.dumps(meta, ensure_ascii=False, indent=2)),
        characters_json=_safe_fmt(json.dumps(characters, ensure_ascii=False, indent=2)),
        scenes_json=_safe_fmt(json.dumps(scenes, ensure_ascii=False, indent=2)),
    )
    yaml_text = llm_client.chat(
        assembly.SYSTEM_PROMPT,
        user_prompt_4,
        max_tokens=8000,
    )
    total_tokens += _estimate_tokens(assembly.SYSTEM_PROMPT + user_prompt_4, 8000)

    # 清理 YAML（去除可能的 Markdown 包裹）
    yaml_text = _clean_yaml(yaml_text)

    # 解析 YAML → dict
    try:
        script_dict = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        # 如果 LLM 输出的 YAML 有格式问题，手工组装
        script_dict = {
            "meta": meta,
            "characters": characters,
            "scenes": scenes,
        }

    # 以代码组装的数据为准（assembly 阶段的 YAML 可能被 LLM 修改）
    if isinstance(script_dict, dict):
        script_dict["meta"] = meta
        script_dict["characters"] = characters
        script_dict["scenes"] = scenes
    else:
        script_dict = {"meta": meta, "characters": characters, "scenes": scenes}

    _pct(95, "正在校验剧本格式…")

    # ── Pydantic 校验 ───────────────────────────────────
    try:
        validated = ScriptOutput(**script_dict)
        script_dict = validated.model_dump()
    except Exception as exc:
        # 校验失败时仍返回原始数据，但记录错误
        import sys
        print(f"[WARNING] Pipeline 输出校验未通过: {exc}", file=sys.stderr)

    _pct(100, "剧本生成完成")

    # 重新生成干净 YAML
    final_yaml = yaml.dump(
        script_dict,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )

    return PipelineResult(
        script=script_dict,
        yaml_text=final_yaml,
        total_tokens_used=total_tokens,
    )


# ── 辅助函数 ──────────────────────────────────────────────

def _format_user_instructions(ui: dict[str, Any]) -> str:
    """将 user_instructions dict 转为可读文本"""
    parts: list[str] = []
    chapters = ui.get("selected_chapters", [])
    if chapters:
        parts.append(f"- 改编章节: {', '.join(chapters)}")
    tone = ui.get("tone", "")
    if tone:
        parts.append(f"- 剧本基调: {tone}")
    focus = ui.get("focus_characters", [])
    if focus:
        parts.append(f"- 重点刻画人物: {', '.join(focus)}")
    custom = ui.get("custom_prompt", "")
    if custom:
        parts.append(f"- 额外要求: {custom}")
    return "\n".join(parts) if parts else "无特殊指令"


def _estimate_tokens(prompt_text: str, output_token_estimate: int) -> int:
    """粗略估算输入+输出 token 数（约 1 中文 ≈ 2 chars ≈ 0.6 token）"""
    input_tokens = len(prompt_text) * 2 // 3  # 中英混合粗略估算
    return input_tokens + output_token_estimate


def _build_meta(
    novel_title: str,
    novel_text: str,
    instructions: dict[str, Any],
) -> dict[str, Any]:
    """构建 meta 信息"""
    # 自动检测改编范围
    chapters_found = re.findall(r"第[一二三四五六七八九十百千\d]+章", novel_text)
    adapted_range = ""
    if chapters_found:
        adapted_range = f"{chapters_found[0]} - {chapters_found[-1]}"
    else:
        adapted_range = "全文"

    return {
        "novel_title": novel_title,
        "script_title": f"{novel_title}（剧本版）",
        "adapted_range": adapted_range,
        "user_instructions": instructions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.2.0",
    }


def _extract_chapter_map(novel_text: str) -> dict[str, str]:
    """
    将小说按章节拆分，返回 {章节名: 章节文本} 的映射。
    支持中文和英文章节标记。
    """
    pattern = r"(第[一二三四五六七八九十百千\d]+章[^\n]*)"
    parts = re.split(pattern, novel_text)
    chapters: dict[str, str] = {}

    # parts[0] 是第一个章节标题之前的内容（可能是引子/楔子）
    # 之后的偶数索引是章节标题，奇数索引是章节正文
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()
        content = parts[i + 1] if i + 1 < len(parts) else ""
        chapters[title] = content

    return chapters


def _find_relevant_excerpt(
    novel_text: str,
    chapter_ref: str,
    chapters: dict[str, str],
) -> str:
    """
    找到场景对应的原文片段。

    优先精确匹配章节，其次是模糊匹配，最后返回全文开头部分。
    """
    # 精确匹配
    for title in chapters:
        if title in chapter_ref or chapter_ref in title:
            return f"【{title}】\n{chapters[title][:3000]}"

    # 模糊匹配：找包含章节号的
    for title in chapters:
        # 提取章节标题中的数字
        title_nums = re.findall(r"\d+", title)
        ref_nums = re.findall(r"\d+", chapter_ref)
        if title_nums and ref_nums and title_nums[0] == ref_nums[0]:
            return f"【{title}】\n{chapters[title][:3000]}"

    # 兜底：返回全文前 2000 字符
    return novel_text[:2000]


def _generate_char_id(name: str) -> str:
    """用中文名生成合法角色 ID（符合 ^CHAR_[A-Z0-9_]+$ 格式）"""
    import unicodedata

    clean = name.strip()

    # 1. 尝试提取已有的 ASCII 字符（英文名、拼音等）
    normalized = unicodedata.normalize("NFKD", clean)
    ascii_part = normalized.encode("ascii", "ignore").decode("ascii").strip()
    if ascii_part and len(ascii_part) >= 2:
        return f"CHAR_{ascii_part.upper().replace(' ', '_')}"

    # 2. 纯中文名：用 Unicode 码位映射到字母，生成可读的短 ID
    #    每个中文字符映射为 A-Z 的一个字母
    letters = []
    for ch in clean:
        if "一" <= ch <= "鿿":
            letters.append(chr(ord("A") + (ord(ch) % 26)))
        elif ch.isascii() and ch.isalpha():
            letters.append(ch.upper())

    if letters:
        return f"CHAR_{''.join(letters[:6])}"

    # 3. 绝对兜底（名字全为空或无法识别）
    return f"CHAR_UNKNOWN_{abs(hash(clean)) % 10000:04d}"


def _clean_yaml(yaml_text: str) -> str:
    """清理 LLM 输出的 YAML（去除 Markdown 代码块包裹）"""
    text = yaml_text.strip()
    pattern = r"^```(?:yaml)?\s*\n(.*?)\n```\s*$"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return text
