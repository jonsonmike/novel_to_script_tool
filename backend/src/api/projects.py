"""
项目管理 API 路由

端点：
- POST   /api/projects                       创建项目
- GET    /api/projects                       项目列表
- GET    /api/projects/{project_id}          项目详情
- DELETE /api/projects/{project_id}          删除项目
- POST   /api/projects/{project_id}/convert  触发 AI 转换
- GET    /api/projects/{project_id}/tasks/{task_id}  查询进度
- GET    /api/projects/{project_id}/script   获取剧本
- PUT    /api/projects/{project_id}/script   保存剧本
- GET    /api/projects/{project_id}/export   导出剧本
"""

from __future__ import annotations

import threading
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Query

from ..core import storage
from ..models.script import ScriptOutput
from ..pipeline.orchestrator import run_pipeline

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ═══════════════════════════════════════════════════════════
# 请求 / 响应模型（简单 dict，后续可用 Pydantic 强类型化）
# ═══════════════════════════════════════════════════════════

# ── POST /api/projects ───────────────────────────────────

@router.post("", status_code=201)
def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    """创建新项目，接收小说正文和改编参数"""
    novel_title = payload.get("novel_title", "").strip()
    novel_text = payload.get("novel_text", "").strip()
    user_instructions = payload.get("user_instructions", {})

    if not novel_text:
        raise HTTPException(status_code=422, detail="novel_text 不能为空")

    project = storage.create_project(
        novel_title=novel_title or "未命名项目",
        novel_text=novel_text,
        user_instructions=user_instructions,
    )

    # 返回精简信息（不含小说全文，避免前端数据过大）
    return {
        "project_id": project["project_id"],
        "novel_title": project["novel_title"],
        "status": project["status"],
        "created_at": project["created_at"],
    }


# ── GET /api/projects ────────────────────────────────────

@router.get("")
def list_projects() -> list[dict[str, Any]]:
    """列出所有项目（摘要信息，不含小说全文和剧本数据）"""
    projects = storage.list_projects()
    return [
        {
            "project_id": p["project_id"],
            "novel_title": p["novel_title"],
            "status": p["status"],
            "created_at": p["created_at"],
        }
        for p in projects
    ]


# ── GET /api/projects/{project_id} ───────────────────────

@router.get("/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    """获取项目详情（含小说全文和用户指令）"""
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


# ── DELETE /api/projects/{project_id} ─────────────────────

@router.delete("/{project_id}")
def delete_project(project_id: str) -> dict[str, str]:
    """删除项目及其所有关联数据"""
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    storage.delete_project(project_id)
    return {"status": "ok", "message": f"项目 {project_id} 已删除"}


# ── POST /api/projects/{project_id}/convert ──────────────

@router.post("/{project_id}/convert", status_code=202)
def trigger_convert(project_id: str) -> dict[str, Any]:
    """触发 AI 小说→剧本转换（异步）"""
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    task = storage.create_task(project_id)
    if task is None:
        raise HTTPException(status_code=500, detail="创建任务失败")

    task_id = task["task_id"]

    # ── 启动后台异步转换 ────────────────────────────────────
    def _run_conversion() -> None:
        """在后台线程中执行 AI Pipeline"""
        try:
            def on_progress(progress: int, message: str) -> None:
                storage.update_task(project_id, task_id, {
                    "status": "running",
                    "progress": progress,
                    "message": message,
                })

            storage.update_task(project_id, task_id, {"status": "running", "message": "正在初始化…"})

            result = run_pipeline(
                novel_text=project["novel_text"],
                novel_title=project["novel_title"],
                user_instructions=project.get("user_instructions", {}),
                on_progress=on_progress,
            )

            storage.save_script(project_id, result.script)
            storage.update_task(project_id, task_id, {
                "status": "completed",
                "progress": 100,
                "completed_at": result.script.get("meta", {}).get("generated_at", ""),
            })

        except Exception as exc:
            storage.update_task(project_id, task_id, {
                "status": "failed",
                "error": str(exc),
            })
            storage.update_project(project_id, {"status": "draft"})

    thread = threading.Thread(target=_run_conversion, daemon=True)
    thread.start()
    # ────────────────────────────────────────────────────────

    return {
        "task_id": task_id,
        "status": task["status"],
        "message": "转换任务已提交，请轮询 GET /api/projects/{id}/tasks/{task_id} 查询进度",
    }


# ── GET /api/projects/{project_id}/tasks/{task_id} ───────

@router.get("/{project_id}/tasks/{task_id}")
def query_task(project_id: str, task_id: str) -> dict[str, Any]:
    """查询 AI 转换任务的进度"""
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    task = storage.get_task(project_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": task["progress"],
        "created_at": task["created_at"],
        "completed_at": task.get("completed_at"),
        "error": task.get("error"),
    }


# ── GET /api/projects/{project_id}/script ────────────────

@router.get("/{project_id}/script")
def get_script(project_id: str) -> dict[str, Any]:
    """获取项目的完整剧本数据"""
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    script = project.get("script")
    if script is None:
        raise HTTPException(status_code=404, detail="尚未生成剧本，请先触发 AI 转换")

    return script


# ── PUT /api/projects/{project_id}/script ────────────────

@router.put("/{project_id}/script")
def save_script(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    保存用户编辑后的剧本。
    接收完整的剧本数据（meta + characters + scenes）。
    """
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 补全缺失的 scene_id（兼容 AI 管线未生成 scene_id 的历史数据）
    scenes = payload.get("scenes", [])
    for i, scene in enumerate(scenes):
        if "scene_id" not in scene:
            sn = scene.get("scene_number", i + 1)
            scene["scene_id"] = f"S{sn:04d}"
    print("DEBUG save_script: scenes[0] keys =", list(scenes[0].keys()) if scenes else "EMPTY")

    # Pydantic 完整校验（格式、角色引用、必填字段）
    try:
        validated = ScriptOutput(**payload)
        storage.save_script(project_id, validated.model_dump())
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"剧本数据格式错误: {exc}",
        ) from exc
    return {"status": "ok", "message": "剧本已保存"}


# ── GET /api/projects/{project_id}/export ────────────────

@router.get("/{project_id}/export")
def export_script(
    project_id: str,
    format: str = Query("yaml", description="导出格式：yaml 或 json"),
) -> Any:
    """导出剧本为 YAML 或 JSON 格式"""
    project = storage.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    script = project.get("script")
    if script is None:
        raise HTTPException(status_code=404, detail="尚未生成剧本")

    from fastapi.responses import PlainTextResponse

    if format == "json":
        import json
        return PlainTextResponse(
            json.dumps(script, ensure_ascii=False, indent=2),
            media_type="application/json",
        )
    else:
        yaml_text = yaml.dump(
            script,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
        return PlainTextResponse(
            yaml_text,
            media_type="application/x-yaml",
        )
