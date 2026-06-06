"""
应用配置

环境变量优先级：系统环境变量 > .env 文件 > 默认值
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件（项目根目录）
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_ENV_FILE)


class Settings:
    """全局配置，支持环境变量覆盖"""

    # 项目路径
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

    # 服务
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # LLM — DeepSeek (OpenAI 兼容接口)
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "16000"))

    # 存储
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'projects.db'}"
    )

    # Schema
    SCHEMA_PATH: Path = PROJECT_ROOT / "docs" / "script_schema.yaml"


settings = Settings()
