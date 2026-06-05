# 后端 — AI 小说转剧本工具

## 技术栈

- **框架**: FastAPI (Python)
- **数据校验**: Pydantic v2
- **LLM**: DeepSeek API (OpenAI 兼容)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **服务器**: Uvicorn

## 快速启动

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 设置 API Key
set DEEPSEEK_API_KEY=your-api-key      # Windows CMD
# 或
export DEEPSEEK_API_KEY="your-api-key"  # Git Bash / Linux

# 3. 启动服务
uvicorn src.main:app --reload --port 8000
```

## 项目结构

```
backend/
├── src/
│   ├── main.py              # FastAPI 入口
│   ├── api/                 # 路由处理
│   ├── core/                # 配置、工具
│   ├── models/              # Pydantic 数据模型
│   └── pipeline/            # AI 转换流水线
├── tests/
├── requirements.txt
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects/{id}` | 获取项目 |
| POST | `/api/projects/{id}/convert` | 触发转换 |
| GET | `/api/projects/{id}/tasks/{task_id}` | 查询进度 |
| GET | `/api/projects/{id}/script` | 获取剧本 |
| PUT | `/api/projects/{id}/script` | 保存编辑 |
| GET | `/api/projects/{id}/export` | 导出 YAML |
