"""
API 接口集成测试

使用 FastAPI TestClient，无需启动服务器。
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════════

def create_test_project(title: str = "测试原著", text: str = "第一章\n测试内容。") -> str:
    """创建项目并返回 project_id"""
    resp = client.post("/api/projects", json={
        "novel_title": title,
        "novel_text": text,
        "user_instructions": {"tone": "悬疑"},
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["project_id"]


# ═══════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════

class TestHealth:
    def test_health_ok(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ═══════════════════════════════════════════════════════════
# POST /api/projects — 创建项目
# ═══════════════════════════════════════════════════════════

class TestCreateProject:
    def test_create_minimal(self):
        """只提供 novel_text 即可创建"""
        resp = client.post("/api/projects", json={"novel_text": "测试正文"})
        assert resp.status_code == 201
        data = resp.json()
        assert "project_id" in data
        assert data["status"] == "draft"

    def test_create_full(self):
        """完整参数创建"""
        resp = client.post("/api/projects", json={
            "novel_title": "剑影",
            "novel_text": "第一章 初遇\n内容内容\n第二章 离别\n内容内容",
            "user_instructions": {
                "selected_chapters": ["第一章", "第二章"],
                "tone": "悬疑",
                "focus_characters": ["林墨"],
                "custom_prompt": "增加打斗",
            },
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["novel_title"] == "剑影"

    def test_missing_text_rejected(self):
        """novel_text 为空应报错"""
        resp = client.post("/api/projects", json={"novel_title": "test"})
        assert resp.status_code == 422

    def test_empty_text_rejected(self):
        """novel_text 为空字符串应报错"""
        resp = client.post("/api/projects", json={"novel_text": "", "novel_title": "test"})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════
# GET /api/projects — 项目列表
# ═══════════════════════════════════════════════════════════

class TestListProjects:
    def test_list_empty(self):
        """空列表返回 []"""
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ═══════════════════════════════════════════════════════════
# GET /api/projects/{id} — 项目详情
# ═══════════════════════════════════════════════════════════

class TestGetProject:
    def test_get_existing(self):
        pid = create_test_project()
        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["project_id"] == pid

    def test_get_nonexistent(self):
        resp = client.get("/api/projects/nonexistent")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# POST /api/projects/{id}/convert — 触发转换
# ═══════════════════════════════════════════════════════════

class TestConvert:
    def test_trigger_convert(self):
        pid = create_test_project()
        resp = client.post(f"/api/projects/{pid}/convert")
        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    def test_convert_nonexistent_project(self):
        resp = client.post("/api/projects/nonexistent/convert")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# GET /api/projects/{id}/tasks/{task_id} — 查询进度
# ═══════════════════════════════════════════════════════════

class TestQueryTask:
    def test_query_task(self):
        pid = create_test_project()
        conv_resp = client.post(f"/api/projects/{pid}/convert")
        task_id = conv_resp.json()["task_id"]
        resp = client.get(f"/api/projects/{pid}/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["status"] == "pending"
        assert data["progress"] == 0

    def test_query_nonexistent_task(self):
        pid = create_test_project()
        resp = client.get(f"/api/projects/{pid}/tasks/bogus")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# PUT /api/projects/{id}/script — 保存剧本
# ═══════════════════════════════════════════════════════════

VALID_SCRIPT = {
    "meta": {
        "novel_title": "剑影",
        "script_title": "剑影（舞台剧版）",
        "adapted_range": "第1章 - 第3章",
    },
    "characters": [
        {"id": "CHAR_LIN_MO", "name": "林墨", "role_type": "主角"},
        {"id": "CHAR_SU_WAN", "name": "苏晚", "role_type": "主角"},
    ],
    "scenes": [
        {
            "scene_id": "S0001",
            "scene_number": 1,
            "location": "内景 王府书房",
            "time": "夜晚",
            "characters_present": ["CHAR_LIN_MO", "CHAR_SU_WAN"],
            "content": [
                {"type": "action", "text": "林墨推门而入。"},
                {
                    "type": "dialogue",
                    "text": "小心，这里有机关。",
                    "speaker_id": "CHAR_LIN_MO",
                    "emotion": "紧张",
                },
            ],
        },
    ],
}


class TestSaveScript:
    def test_save_valid_script(self):
        pid = create_test_project()
        resp = client.put(f"/api/projects/{pid}/script", json=VALID_SCRIPT)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_save_missing_fields(self):
        """缺少 meta/characters/scenes 应报错"""
        pid = create_test_project()
        resp = client.put(f"/api/projects/{pid}/script", json={"meta": {}})
        assert resp.status_code == 422
        assert "characters" in resp.json()["detail"]

    def test_save_nonexistent_project(self):
        resp = client.put("/api/projects/nonexistent/script", json=VALID_SCRIPT)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# GET /api/projects/{id}/script — 获取剧本
# ═══════════════════════════════════════════════════════════

class TestGetScript:
    def test_get_script_after_save(self):
        pid = create_test_project()
        client.put(f"/api/projects/{pid}/script", json=VALID_SCRIPT)
        resp = client.get(f"/api/projects/{pid}/script")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["novel_title"] == "剑影"
        assert len(data["characters"]) == 2
        assert len(data["scenes"]) == 1

    def test_get_script_not_generated(self):
        pid = create_test_project()
        resp = client.get(f"/api/projects/{pid}/script")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# GET /api/projects/{id}/export — 导出
# ═══════════════════════════════════════════════════════════

class TestExport:
    def test_export_yaml(self):
        pid = create_test_project()
        client.put(f"/api/projects/{pid}/script", json=VALID_SCRIPT)
        resp = client.get(f"/api/projects/{pid}/export?format=yaml")
        assert resp.status_code == 200
        assert "meta:" in resp.text
        assert "CHAR_LIN_MO" in resp.text

    def test_export_json(self):
        pid = create_test_project()
        client.put(f"/api/projects/{pid}/script", json=VALID_SCRIPT)
        resp = client.get(f"/api/projects/{pid}/export?format=json")
        assert resp.status_code == 200
        import json
        data = json.loads(resp.text)
        assert data["meta"]["novel_title"] == "剑影"

    def test_export_no_script(self):
        pid = create_test_project()
        resp = client.get(f"/api/projects/{pid}/export")
        assert resp.status_code == 404


class TestDeleteProject:
    """DELETE /api/projects/{project_id}"""

    def test_delete_success(self):
        pid = create_test_project()
        resp = client.delete(f"/api/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_delete_not_found(self):
        resp = client.delete("/api/projects/nonexistent")
        assert resp.status_code == 404

    def test_delete_then_get_404(self):
        pid = create_test_project()
        client.delete(f"/api/projects/{pid}")
        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 404
