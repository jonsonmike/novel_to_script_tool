"""
FastAPI 应用入口
AI 小说转剧本工具 — 后端服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import projects_router

app = FastAPI(
    title="Novel-to-Script API",
    description="AI 辅助小说改编剧本 — 后端服务",
    version="0.1.0",
)

# CORS 配置 — 允许前端开发时跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8501",   # Streamlit 默认端口
        "http://localhost:8502",

    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ─────────────────────────────────────────────
app.include_router(projects_router)


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "version": "0.1.0"}
