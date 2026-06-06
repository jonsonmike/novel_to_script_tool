"""
项目持久化存储 — MVP 阶段使用 JSON 文件存储

数据结构：每个项目一个 JSON 文件，存放在 backend/data/{project_id}.json
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 数据目录
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# 模块级锁，保护文件读写操作
_lock = threading.Lock()


def _ensure_data_dir() -> None:
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _project_path(project_id: str) -> Path:
    """获取项目文件的路径"""
    return DATA_DIR / f"{project_id}.json"


def _now_iso() -> str:
    """返回当前 ISO 8601 时间字符串"""
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════
# Project CRUD
# ═══════════════════════════════════════════════════════════

def create_project(
    novel_title: str,
    novel_text: str,
    user_instructions: dict | None = None,
) -> dict:
    """
    创建新项目，保存到 JSON 文件。
    返回完整的 project 对象。
    """
    _ensure_data_dir()

    project_id = uuid.uuid4().hex[:12]  # 短 ID，便于前端显示
    now = _now_iso()

    project = {
        "project_id": project_id,
        "novel_title": novel_title,
        "novel_text": novel_text,
        "user_instructions": user_instructions or {},
        "status": "draft",
        "script": None,       # 剧本数据（转换完成后填充）
        "tasks": [],           # 转换任务历史
        "created_at": now,
        "updated_at": now,
    }

    _write_project(project_id, project)
    return project


def get_project(project_id: str) -> dict | None:
    """获取单个项目，不存在则返回 None"""
    path = _project_path(project_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_projects() -> list[dict]:
    """列出所有项目（按创建时间倒序）"""
    _ensure_data_dir()
    projects: list[dict] = []
    for path in sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            projects.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return projects


def update_project(project_id: str, updates: dict) -> dict | None:
    """部分更新项目字段。返回更新后的项目。（线程安全）"""
    with _lock:
        project = get_project(project_id)
        if project is None:
            return None

        # 合并更新（顶层字段覆盖）
        project.update(updates)
        project["updated_at"] = _now_iso()
        _write_project(project_id, project)
    return project


def delete_project(project_id: str) -> bool:
    """删除项目文件。成功返回 True。（线程安全）"""
    with _lock:
        path = _project_path(project_id)
        if path.exists():
            path.unlink()
            return True
    return False


# ═══════════════════════════════════════════════════════════
# Script 操作
# ═══════════════════════════════════════════════════════════

def save_script(project_id: str, script_data: dict) -> dict | None:
    """
    保存剧本数据到项目。
    script_data 应该是符合 ScriptOutput Schema 的字典。
    """
    return update_project(project_id, {
        "script": script_data,
        "status": "completed",
    })


def get_script(project_id: str) -> dict | None:
    """获取项目的剧本数据"""
    project = get_project(project_id)
    if project is None:
        return None
    return project.get("script")


# ═══════════════════════════════════════════════════════════
# Task 操作（转换任务）
# ═══════════════════════════════════════════════════════════

def create_task(project_id: str) -> dict | None:
    """
    为项目创建一个新的转换任务。
    返回 task 对象（含 task_id）。（线程安全）
    """
    with _lock:
        project = get_project(project_id)
        if project is None:
            return None

        task_id = uuid.uuid4().hex[:8]
        task = {
            "task_id": task_id,
            "status": "pending",   # pending → running → completed / failed
            "progress": 0,         # 0–100
            "created_at": _now_iso(),
            "completed_at": None,
            "error": None,
        }

        tasks: list = project.get("tasks", [])
        tasks.append(task)
        project["tasks"] = tasks
        project["status"] = "converting"
        project["updated_at"] = _now_iso()
        _write_project(project_id, project)

    # 清理旧任务（只保留最近 10 个）
    _trim_tasks(project_id, keep=10)
    return task


def get_task(project_id: str, task_id: str) -> dict | None:
    """获取项目的指定任务"""
    project = get_project(project_id)
    if project is None:
        return None
    for task in project.get("tasks", []):
        if task["task_id"] == task_id:
            return task
    return None


def update_task(project_id: str, task_id: str, updates: dict) -> dict | None:
    """更新任务状态（线程安全）"""
    with _lock:
        project = get_project(project_id)
        if project is None:
            return None

        tasks: list = project.get("tasks", [])
        for task in tasks:
            if task["task_id"] == task_id:
                task.update(updates)
                project["updated_at"] = _now_iso()
                _write_project(project_id, project)
                return task

    return None


def _trim_tasks(project_id: str, keep: int = 10) -> None:
    """只保留最近 N 个任务，防止项目文件无限增长"""
    with _lock:
        project = get_project(project_id)
        if project is None:
            return
        tasks: list = project.get("tasks", [])
        if len(tasks) > keep:
            project["tasks"] = tasks[-keep:]
            project["updated_at"] = _now_iso()
            _write_project(project_id, project)


# ═══════════════════════════════════════════════════════════
# 内部工具
# ═══════════════════════════════════════════════════════════

def _write_project(project_id: str, project: dict) -> None:
    """写入项目 JSON 文件"""
    _ensure_data_dir()
    path = _project_path(project_id)
    path.write_text(
        json.dumps(project, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
