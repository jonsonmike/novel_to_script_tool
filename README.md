# AI 小说转剧本工具

> 🎬 **项目讲解视频**：[点击观看 Bilibili 视频教程](https://www.bilibili.com/video/BV1mFEb66EQA/) — 了解项目背景、架构设计、核心功能演示与使用指南

将 3 章以上的小说文本自动转换为结构化剧本（YAML 格式），降低改编门槛，提升剧本创作效率。

---

## 项目简介

很多小说作者希望将自己的作品改编成剧本，但改编过程耗时费力、门槛较高。本工具利用 AI（DeepSeek LLM）自动完成从小说到剧本的转换，生成符合行业规范的 YAML 格式剧本，让作者可以快速获得可编辑、可进一步打磨的剧本初稿。

### 核心功能

- **小说导入** — 支持粘贴文本或上传文件，自动识别章节
- **AI 智能转换** — 4 阶段流水线：角色提取 → 场景拆分 → 内容生成 → 格式组装
- **结构化剧本** — 输出 YAML 格式，包含完整的 meta/characters/scenes 结构
- **可视化编辑** — 按场景编辑剧本内容，支持 6 种内容块类型（动作/对白/旁白/转场/音效/注释）
- **置信度标注** — AI 对每个内容块标注置信度，低置信度部分建议重点审核
- **剧本导出** — 支持下载 YAML / JSON 格式

---

## 系统架构

```
┌──────────────────────┐         ┌──────────────────────┐
│      前端 (Streamlit) │  HTTP  |     后端 (FastAPI)    │
│                      │◄───────►│                      │
│  • 项目管理界面       │  REST   │  • 10 个 API 接口     │
│  • 角色库展示         │  API    │  • Pydantic 数据校验  │
│  • 场景编辑器         │         │  • AI Pipeline 编排   │
│  • 剧本导出           │         │  • JSON 文件存储      │
└──────────────────────┘         └──────────┬───────────┘
                                            │
                                            │ HTTP (OpenAI 兼容)
                                            ▼
                                 ┌──────────────────────┐
                                 │     DeepSeek API     │
                                 │  • deepseek-chat 模型 │
                                 │  • JSON 模式输出      │
                                 └──────────────────────┘
```

---

## 快速开始

### 环境要求

- Python 3.9+
- DeepSeek API Key（[申请地址](https://platform.deepseek.com)）

### 1. 克隆项目

```bash
git clone https://github.com/jonsonmike/novel_to_script_tool.git
cd novel_to_script_tool
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

验证：访问 `http://127.0.0.1:8000/api/health`，返回 `{"status":"ok","version":"0.1.0","api_key_configured":true}`。

### 3. 启动前端

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

浏览器访问 `http://127.0.0.1:8501`，右上角显示 "✅ 后端在线 0.1.0" 即可使用。

### 4. 开始使用

1. 左侧点击 **📁 创建项目**，粘贴小说正文（需 3 章以上），设置改编参数
2. 点击 **⚙️ 转换管理** → **触发转换**，等待 AI 处理（通常 1-3 分钟）
3. 转换完成后在 **🎬 场景编辑** 查看和编辑生成的剧本
4. 在 **📤 导出剧本** 下载 YAML 或 JSON 格式

---

## 项目结构

```
novel_to_script_tool/
├── README.md                         # 项目总览（本文件）
├── .gitignore                        # Git 忽略规则
│
├── docs/                             # 文档
│   ├── api_spec.md                   # API 接口规范（10 个接口）
│   ├── script_schema.yaml            # 剧本 YAML Schema v1.2.0
│   └── yaml_constrain.txt            # Schema 设计说明文档
│
├── backend/                          # 后端（FastAPI）
│   ├── README.md                     # 后端详细说明
│   ├── requirements.txt              # Python 依赖
│   ├── .env.example                  # 环境变量模板
│   ├── src/
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── api/projects.py           # 10 个 API 接口
│   │   ├── core/
│   │   │   ├── config.py             # 配置管理
│   │   │   └── storage.py            # JSON 文件存储
│   │   ├── models/script.py          # Pydantic 数据模型
│   │   └── pipeline/
│   │       ├── orchestrator.py       # AI 4 阶段流水线
│   │       ├── llm_client.py         # LLM 客户端（JSON 修复 + 重试）
│   │       └── prompts/              # Prompt 模板
│   │           ├── extraction.py     # 阶段 1: 角色提取
│   │           ├── splitting.py      # 阶段 2: 场景拆分
│   │           ├── generation.py     # 阶段 3: 内容生成
│   │           └── assembly.py       # 阶段 4: 格式组装
│   └── tests/                        # 测试（125 个用例）
│       ├── test_models.py            # 数据模型测试（60 个）
│       ├── test_api.py               # API 接口测试（23 个）
│       ├── test_pipeline.py          # Pipeline 单元测试（33 个）
│       └── test_pipeline_e2e.py      # 端到端集成测试（9 个）
│
├── frontend/                         # 前端（Streamlit）
│   ├── app.py                        # Streamlit 主入口（7 页面）
│   ├── requirements.txt              # Python 依赖
│   └── src/
│       ├── api.py                    # 后端 API 调用封装
│       ├── config.py                 # 常量配置
│       └── components/
│           ├── project.py            # 创建项目 / 项目列表
│           ├── characters.py         # 角色库
│           ├── scenes.py             # 场景编辑器
│           └── export.py             # 剧本导出
│
├── examples/                         # 示例文件
└── tests/                            # 项目级测试
```

---

## API 接口总览

完整规范见 `docs/api_spec.md`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + API Key 状态 |
| POST | `/api/projects` | 创建项目（上传小说） |
| GET | `/api/projects` | 项目列表 |
| GET | `/api/projects/{id}` | 项目详情 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/{id}/convert` | 触发 AI 转换（异步） |
| GET | `/api/projects/{id}/tasks/{task_id}` | 查询转换进度 |
| GET | `/api/projects/{id}/script` | 获取剧本 |
| PUT | `/api/projects/{id}/script` | 保存编辑后的剧本 |
| GET | `/api/projects/{id}/export` | 导出 YAML / JSON |

---

## AI 转换流程

```
小说文本
  → 阶段 1: 角色实体提取 → characters[]
  → 阶段 2: 场景拆分       → scenes[] 骨架
  → 阶段 3: 内容生成       → content[] 填充（逐场生成 6 种内容块）
  → 阶段 4: 格式组装       → 完整 YAML（符合 script_schema.yaml v1.2.0）
  → Pydantic 校验          → 输出合法剧本
```

- JSON 模式调用（阶段 1-3），内置解析修复 + 失败重试
- 进度实时回调（0-100% + 文字描述）
- 用户输入中的特殊字符（`{}`）自动转义

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.115 |
| 数据校验 | Pydantic v2 |
| AI / LLM | DeepSeek API（OpenAI 兼容 SDK） |
| 存储 | JSON 文件存储（MVP） |
| 前端 | Streamlit |
| 测试 | pytest（125 个用例） |
| 语言 | Python 3.9+ |

---

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

125 个测试覆盖：数据模型校验、API 接口集成、Pipeline 单元测试、端到端流程。

---

## 团队分工

- **后端** — FastAPI API、AI Pipeline、数据模型与校验、存储层
- **前端** — Streamlit 界面、项目管理、角色库、场景编辑器、剧本导出

---

## 文档索引

- [API 接口规范](docs/api_spec.md) — 全部 10 个接口的请求/响应格式
- [剧本 Schema 定义](docs/script_schema.yaml) — YAML 输出格式 v1.2.0
- [Schema 设计说明](docs/yaml_constrain.txt) — 设计决策与取舍
- [后端 README](backend/README.md) — 后端架构与开发指南
