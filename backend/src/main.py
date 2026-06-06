"""
FastAPI 应用入口
AI 小说转剧本工具 — 后端服务
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import projects_router
from .core.config import settings

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时检查配置"""
    if not settings.DEEPSEEK_API_KEY:
        logger.warning(
            "⚠️  未设置 DEEPSEEK_API_KEY！"
            "请在 backend/.env 文件中配置，或设置环境变量。"
            "AI 转换功能将无法使用。"
        )
    yield


app = FastAPI(
    title="Novel-to-Script API",
    description="AI 辅助小说改编剧本 — 后端服务",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置 — 允许前端开发时跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8501",   # Streamlit 默认端口
        "http://localhost:8502",
        "http://localhost:8503",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8502",
        "http://127.0.0.1:8503",
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
    return {
        "status": "ok",
        "version": "0.1.0",
        "api_key_configured": bool(settings.DEEPSEEK_API_KEY),
    }

