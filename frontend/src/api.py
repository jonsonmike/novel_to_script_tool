"""
API 客户端 — 封装对后端 FastAPI 服务的 HTTP 调用

所有函数返回 (success: bool, data: dict | None, error: str | None)
"""
from __future__ import annotations

from typing import Any

import requests

from .config import BACKEND_URL, API_PREFIX


def _url(path: str) -> str:
    """拼接完整 API URL"""
    return f"{BACKEND_URL}{API_PREFIX}{path}"


# ═══════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════

def health_check() -> tuple[bool, dict[str, Any] | None, str | None]:
    """GET /api/health — 检查后端服务是否在线"""
    try:
        resp = requests.get(_url("/health"), timeout=5)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务，请确认已启动: uvicorn src.main:app --port 8000"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


# ═══════════════════════════════════════════════════════════
# 项目管理
# ═══════════════════════════════════════════════════════════

def create_project(
    novel_text: str,
    novel_title: str = "",
    selected_chapters: list[str] | None = None,
    tone: str = "",
    focus_characters: list[str] | None = None,
    custom_prompt: str = "",
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """POST /api/projects — 创建改编项目"""
    payload: dict[str, Any] = {
        "novel_text": novel_text,
        "novel_title": novel_title,
        "user_instructions": {
            "selected_chapters": selected_chapters or [],
            "tone": tone,
            "focus_characters": focus_characters or [],
            "custom_prompt": custom_prompt,
        },
    }
    try:
        resp = requests.post(_url("/projects"), json=payload, timeout=30)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


def get_project(project_id: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """GET /api/projects/{id} — 获取项目详情"""
    try:
        resp = requests.get(_url(f"/projects/{project_id}"), timeout=10)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


def list_projects() -> tuple[bool, list[dict[str, Any]] | None, str | None]:
    """GET /api/projects — 列出所有项目"""
    try:
        resp = requests.get(_url("/projects"), timeout=10)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


def delete_project(project_id: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """DELETE /api/projects/{id} — 删除项目"""
    try:
        resp = requests.delete(_url(f"/projects/{project_id}"), timeout=10)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


# ═══════════════════════════════════════════════════════════
# AI 转换
# ═══════════════════════════════════════════════════════════

def trigger_convert(project_id: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """POST /api/projects/{id}/convert — 触发 AI 转换"""
    try:
        resp = requests.post(_url(f"/projects/{project_id}/convert"), timeout=10)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


def query_task(project_id: str, task_id: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """GET /api/projects/{id}/tasks/{task_id} — 查询转换进度"""
    try:
        resp = requests.get(_url(f"/projects/{project_id}/tasks/{task_id}"), timeout=10)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


# ═══════════════════════════════════════════════════════════
# 剧本操作
# ═══════════════════════════════════════════════════════════

def get_script(project_id: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """GET /api/projects/{id}/script — 获取生成的剧本"""
    try:
        resp = requests.get(_url(f"/projects/{project_id}/script"), timeout=10)
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


def save_script(project_id: str, script_data: dict[str, Any]) -> tuple[bool, dict[str, Any] | None, str | None]:
    """PUT /api/projects/{id}/script — 保存剧本编辑"""
    try:
        resp = requests.put(
            _url(f"/projects/{project_id}/script"),
            json=script_data,
            timeout=15,
        )
        resp.raise_for_status()
        return True, resp.json(), None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)


def export_script(project_id: str, format: str = "yaml") -> tuple[bool, str | None, str | None]:
    """GET /api/projects/{id}/export — 导出剧本（返回文本内容）"""
    try:
        resp = requests.get(
            _url(f"/projects/{project_id}/export"),
            params={"format": format},
            timeout=15,
        )
        resp.raise_for_status()
        return True, resp.text, None
    except requests.ConnectionError:
        return False, None, "无法连接后端服务"
    except requests.Timeout:
        return False, None, "后端服务响应超时"
    except Exception as exc:
        return False, None, str(exc)
