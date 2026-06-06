"""
前端配置模块
"""
import os

# ── 后端服务地址 ──────────────────────────────────────────
BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT: str = os.getenv("BACKEND_PORT", "8000")
BACKEND_URL: str = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
API_PREFIX: str = "/api"

# ── 支持的剧本基调 ────────────────────────────────────────
TONE_RECOMMENDATIONS: list[str] = [
    "正剧", "喜剧", "悲剧", "悬疑", "爱情",
    "科幻", "武侠", "奇幻", "惊悚", "恐怖",
    "历史", "战争", "都市", "青春",
]

# ── 角色类型 ──────────────────────────────────────────────
ROLE_TYPES: list[str] = ["主角", "配角", "龙套"]

# ── 时段 ──────────────────────────────────────────────────
TIME_PERIODS: list[str] = ["清晨", "上午", "下午", "傍晚", "夜晚", "深夜", "黎明"]

# ── 内容块类型 ────────────────────────────────────────────
CONTENT_TYPES: list[str] = ["action", "dialogue", "voiceover", "transition", "sound", "note"]

CONTENT_TYPE_LABELS: dict[str, str] = {
    "action":     "🎬 动作 / 舞台指示",
    "dialogue":   "💬 角色对白",
    "voiceover":  "🎙️ 旁白 / 内心独白",
    "transition": "⏭️ 转场效果",
    "sound":      "🔊 音效",
    "note":       "📝 编剧注释",
}

# ── 置信度阈值 ────────────────────────────────────────────
CONFIDENCE_HIGH: float = 0.9
CONFIDENCE_MEDIUM: float = 0.7
CONFIDENCE_LOW: float = 0.5
