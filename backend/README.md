# 后端 — AI 小说转剧本工具

将 3 章以上的小说文本自动转换为结构化剧本（YAML 格式），降低改编门槛，提升效率。

---

## 技术栈

- **框架**: FastAPI 0.115 (Python 3.9+)
- **数据校验**: Pydantic v2，完整实现 `script_schema.yaml v1.2.0`
- **LLM**: DeepSeek API（OpenAI 兼容 SDK），支持 JSON 模式 + 解析失败重试
- **存储**: JSON 文件存储（MVP），项目数据存于 `data/{project_id}.json`
- **服务器**: Uvicorn
- **测试**: pytest，116 个测试用例

---

## 快速启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置 API Key

创建 `.env` 文件（参考 `.env.example`）：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-your-api-key-here
```

> 前往 https://platform.deepseek.com 注册并获取 Key。`.env` 已加入 `.gitignore`，不会被提交。

### 3. 启动服务

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

验证：访问 `http://127.0.0.1:8000/api/health`，返回 `{"status":"ok","version":"0.1.0"}`。

### 4. 启动前端（配合使用）

另开终端：

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

浏览器访问 `http://127.0.0.1:8501`，右上角应显示 "✅ 后端在线 0.1.0"。

---

## 项目结构

```
backend/
├── src/
│   ├── main.py                    # FastAPI 入口（CORS + 路由注册）
│   ├── api/
│   │   ├── __init__.py            # 导出 projects_router
│   │   └── projects.py            # 10 个 API 接口实现
│   ├── core/
│   │   ├── config.py              # Settings 类（.env 加载 + 环境变量）
│   │   └── storage.py             # JSON 文件存储（线程安全）
│   ├── models/
│   │   ├── __init__.py            # 导出全部模型
│   │   └── script.py              # Pydantic 模型（8 类 + 3 枚举 + 交叉校验）
│   └── pipeline/
│       ├── __init__.py            # 导出 run_pipeline / PipelineResult
│       ├── llm_client.py          # LLM 客户端（chat / chat_json + 重试）
│       ├── orchestrator.py        # 4 阶段流水线编排 + 辅助函数
│       └── prompts/
│           ├── extraction.py      # 阶段 1: 角色实体提取
│           ├── splitting.py       # 阶段 2: 场景拆分
│           ├── generation.py      # 阶段 3: 剧本内容生成
│           └── assembly.py        # 阶段 4: 格式组装
├── tests/
│   ├── test_models.py             # Pydantic 模型测试（60 个）
│   ├── test_api.py                # API 接口测试（23 个）
│   └── test_pipeline.py           # Pipeline 测试（33 个，含 mock 重试）
├── data/                          # 项目数据存储目录（.gitignore 排除）
├── .env.example                   # API Key 配置模板
├── requirements.txt
└── README.md
```

---

## API 接口

完整规范见 `docs/api_spec.md`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/projects` | 创建项目（上传小说文本） |
| GET | `/api/projects` | 项目列表 |
| GET | `/api/projects/{id}` | 项目详情 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/{id}/convert` | 触发 AI 转换（异步，返回 task_id） |
| GET | `/api/projects/{id}/tasks/{task_id}` | 查询转换进度 |
| GET | `/api/projects/{id}/script` | 获取剧本 |
| PUT | `/api/projects/{id}/script` | 保存编辑后的剧本（Pydantic 校验） |
| GET | `/api/projects/{id}/export?format=yaml` | 导出 YAML / JSON |

---

## AI Pipeline 流程

```
小说文本
  → 阶段 1: 角色提取（LLM JSON 模式）→ characters[]
  → 阶段 2: 场景拆分（LLM JSON 模式）→ scenes[] 骨架
  → 阶段 3: 内容生成（逐场调用 LLM）→ content[] 填充
  → 阶段 4: 格式组装（LLM 文本模式）→ 完整 YAML
  → Pydantic 校验（ScriptOutput 模型）
  → 保存到存储层
```

- 阶段 1-3 使用 `chat_json()`，内置 JSON 提取修复 + 解析失败重试
- 阶段 4 使用 `chat()`，输出 YAML 文本
- 进度通过 `on_progress(0-100, message)` 回调实时更新
- 用户输入中的 `{}` 花括号自动转义，不会导致模板注入崩溃

---

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

116 个测试，覆盖：
- **test_models.py** (60): Pydantic 模型校验、必填字段、格式约束、交叉引用
- **test_api.py** (23): 10 个 API 接口的集成测试（FastAPI TestClient）
- **test_pipeline.py** (33): JSON 提取、章节解析、YAML 清理、角色 ID 生成、chat_json 重试 mock

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | (空) | DeepSeek API 密钥（**必填**） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `LLM_MAX_TOKENS` | `16000` | 单次调用最大输出 token |

所有变量可在 `.env` 文件中配置，也可直接设系统环境变量。
