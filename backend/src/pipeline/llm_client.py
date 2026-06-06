"""
LLM 客户端 — 封装 DeepSeek API 调用（OpenAI 兼容）

提供：
- 非流式调用（chat）
- JSON 模式调用（chat_json，用于阶段 1-3）
- 重试逻辑 + JSON 提取修复
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from ..core.config import settings


def _client() -> OpenAI:
    """创建 OpenAI 客户端实例（连接 DeepSeek）"""
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )


def chat(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int | None = None,
) -> str:
    """
    调用 LLM，返回文本响应。

    Args:
        system_prompt: 系统指令
        user_prompt: 用户消息
        max_tokens: 最大输出 token 数，默认使用配置值

    Returns:
        LLM 返回的文本内容

    Raises:
        RuntimeError: API 调用失败
    """
    client = _client()
    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            temperature=0.7,
        )
    except Exception as exc:
        raise RuntimeError(f"LLM API 调用失败: {exc}") from exc

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM 返回空响应")
    return content


def chat_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    调用 LLM，返回解析后的 JSON 对象。

    内置 JSON 修复逻辑：
    - 去除 ```json ... ``` 包裹
    - 截取到最后一个 } 为止
    - 失败时重试

    Args:
        system_prompt: 系统指令
        user_prompt: 用户消息
        max_tokens: 最大输出 token 数
        max_retries: JSON 解析失败时的最大重试次数

    Returns:
        解析后的 JSON 字典

    Raises:
        RuntimeError: 多次重试后仍无法解析
    """
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        raw = chat(system_prompt, user_prompt, max_tokens=max_tokens)
        try:
            return _extract_json(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
            # 重试时在 prompt 末尾追加错误提示
            if attempt < max_retries:
                user_prompt = _append_retry_hint(user_prompt, raw, last_error)
                continue

    raise RuntimeError(f"LLM JSON 解析失败（重试 {max_retries} 次后）: {last_error}")


def _extract_json(text: str) -> dict[str, Any]:
    """
    从 LLM 输出中提取 JSON 对象。

    处理常见情况：
    - ```json { ... } ```
    - ``` { ... } ```
    - { ... }
    - 末尾有多余字符
    """
    # 去除 Markdown 代码块包裹
    text = text.strip()
    code_block_pattern = r"^```(?:json)?\s*\n(.*?)\n```\s*$"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # 找到第一个 { 和最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1:
        raise ValueError(f"响应中未找到 JSON 对象: {text[:200]}...")
    text = text[start:end + 1]

    return json.loads(text)


def _append_retry_hint(
    original_prompt: str,
    failed_output: str,
    error_msg: str,
) -> str:
    """在重试时追加错误提示"""
    hint = (
        f"\n\n---\n⚠️ 上一次输出格式错误（{error_msg}），请修正。\n"
        f"上一次的输出（已截断）: {failed_output[-300:]}\n"
        f"请确保返回**纯 JSON**，不要包裹在 ```json 代码块中，不要添加解释文字。"
    )
    return original_prompt + hint
