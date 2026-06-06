# AI 小说转剧本工具 — API 接口规范

版本: v1.0
最后更新: 2025-06-06

---

## 概述

- 基础 URL: `http://127.0.0.1:8000`
- 请求体格式: `application/json`
- 响应体格式: `application/json`（导出接口可选 `text/yaml`）
- 字符编码: UTF-8

---

## 接口清单

### 1. 健康检查

```
GET /api/health
```

**响应 200:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### 2. 创建项目

```
POST /api/projects
```

**请求体:**
```json
{
  "novel_title": "剑影夜雨",
  "novel_text": "第一章 夜雨客栈\n夜幕低垂，暴雨如注。...",
  "user_instructions": {
    "selected_chapters": ["第1章 初遇", "第2章 离别"],
    "tone": "悬疑",
    "focus_characters": ["林墨", "苏晚"],
    "custom_prompt": "增加男主角的心理活动描写"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| novel_title | string | 是 | 小说标题 |
| novel_text | string | 是 | 小说正文（支持 3 章以上） |
| user_instructions | object | 否 | 改编参数，见下表 |
| user_instructions.selected_chapters | string[] | 否 | 指定改编章节，空则全文 |
| user_instructions.tone | string | 否 | 剧本基调（如 悬疑、正剧、喜剧） |
| user_instructions.focus_characters | string[] | 否 | 重点刻画的人物名 |
| user_instructions.custom_prompt | string | 否 | 自由文本的额外改编要求 |

**响应 201:**
```json
{
  "project_id": "a1b2c3d4e5f6",
  "novel_title": "剑影夜雨",
  "status": "draft",
  "created_at": "2025-06-06T12:00:00Z"
}
```

---

### 3. 项目列表

```
GET /api/projects
```

**响应 200:**
```json
[
  {
    "project_id": "a1b2c3d4e5f6",
    "novel_title": "剑影夜雨",
    "status": "completed",
    "created_at": "2025-06-06T12:00:00Z"
  }
]
```

---

### 4. 项目详情

```
GET /api/projects/{project_id}
```

**响应 200:**
```json
{
  "project_id": "a1b2c3d4e5f6",
  "novel_title": "剑影夜雨",
  "novel_text": "第一章 夜雨客栈\n...",
  "user_instructions": { "tone": "悬疑" },
  "status": "draft",
  "script": null,
  "tasks": [],
  "created_at": "2025-06-06T12:00:00Z",
  "updated_at": "2025-06-06T12:00:00Z"
}
```

**错误:**
| 状态码 | 说明 |
|--------|------|
| 404 | 项目不存在 |

---

### 5. 删除项目

```
DELETE /api/projects/{project_id}
```

**响应 200:**
```json
{
  "status": "ok",
  "message": "项目 a1b2c3d4e5f6 已删除"
}
```

**错误:**
| 状态码 | 说明 |
|--------|------|
| 404 | 项目不存在 |

---

### 6. 触发 AI 转换

```
POST /api/projects/{project_id}/convert
```

无请求体。

**响应 202:**
```json
{
  "task_id": "b7c8d9e0",
  "status": "pending",
  "message": "转换任务已提交，请轮询 GET /api/projects/{id}/tasks/{task_id} 查询进度"
}
```

转换在后台异步执行，分为 4 个阶段：
1. 角色实体提取（进度 5%–25%）
2. 场景拆分（进度 30%–50%）
3. 内容生成 — 逐场生成对白和动作（进度 55%–90%）
4. 格式组装 — 拼成完整 YAML（进度 95%–100%）

**错误:**
| 状态码 | 说明 |
|--------|------|
| 404 | 项目不存在 |
| 409 | 项目正在转换中 |

---

### 7. 查询转换进度

```
GET /api/projects/{project_id}/tasks/{task_id}
```

**响应 200:**
```json
{
  "task_id": "b7c8d9e0",
  "status": "running",
  "progress": 55,
  "message": "正在生成第 3/10 场…",
  "created_at": "2025-06-06T12:01:00Z",
  "completed_at": null,
  "error": null
}
```

**status 枚举:**
| 值 | 说明 |
|------|------|
| pending | 排队等待 |
| running | 执行中（progress 递增） |
| completed | 成功完成（progress = 100） |
| failed | 失败（error 字段有错误信息） |

**错误:**
| 状态码 | 说明 |
|--------|------|
| 404 | 项目或任务不存在 |

---

### 8. 获取剧本

```
GET /api/projects/{project_id}/script
```

**响应 200:**
```json
{
  "meta": {
    "novel_title": "剑影夜雨",
    "script_title": "剑影夜雨（剧本版）",
    "adapted_range": "第1章 - 第3章",
    "user_instructions": { "tone": "悬疑" },
    "generated_at": "2025-06-06T12:02:00Z",
    "schema_version": "1.2.0"
  },
  "characters": [
    {
      "id": "CHAR_LIN_MO",
      "name": "林墨",
      "role_type": "主角",
      "traits": ["冷静", "武艺高强"],
      "physical_description": "身着青衫，腰佩长剑",
      "aliases": ["墨儿", "林公子"]
    }
  ],
  "scenes": [
    {
      "scene_id": "S0001",
      "scene_number": 1,
      "chapter_origin": "第1章 夜雨客栈",
      "location": "内景 清风客栈大堂 — 夜",
      "time": "夜晚",
      "characters_present": ["CHAR_LIN_MO"],
      "content": [
        {
          "type": "action",
          "text": "林墨推开门，湿透的青衫紧贴在身上。",
          "ai_confidence": 0.95
        },
        {
          "type": "dialogue",
          "text": "住店。",
          "speaker_id": "CHAR_LIN_MO",
          "emotion": "平静",
          "ai_confidence": 0.92
        }
      ]
    }
  ]
}
```

**错误:**
| 状态码 | 说明 |
|--------|------|
| 404 | 项目不存在或尚未生成剧本 |

---

### 9. 保存剧本

```
PUT /api/projects/{project_id}/script
```

**请求体:** 与"获取剧本"的响应格式相同（meta + characters + scenes 三层结构）。
保存前会用 Pydantic 模型做完整校验（角色 ID 格式、speaker_id 引用一致性、extra="forbid" 等）。

**响应 200:**
```json
{
  "status": "ok",
  "message": "剧本已保存"
}
```

**错误:**
| 状态码 | 说明 |
|--------|------|
| 404 | 项目不存在 |
| 422 | 剧本数据格式校验失败（detail 包含具体错误） |

---

### 10. 导出剧本

```
GET /api/projects/{project_id}/export?format=yaml
```

**查询参数:**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| format | string | yaml | yaml 或 json |

**响应 200 (format=yaml):**
```yaml
meta:
  novel_title: "剑影夜雨"
  script_title: "剑影夜雨（剧本版）"
  ...
characters:
  - id: CHAR_LIN_MO
    name: "林墨"
    ...
scenes:
  - scene_id: S0001
    ...
```

Content-Type: `text/yaml; charset=utf-8`

**响应 200 (format=json):**
Content-Type: `application/json`

返回完整剧本 JSON，格式与"获取剧本"一致。

**错误:**
| 状态码 | 说明 |
|--------|------|
| 404 | 项目不存在或尚未生成剧本 |

---

## 数据模型

完整的数据结构定义见 `docs/script_schema.yaml` v1.2.0。

**内容块类型（content[].type）:**
| 值 | 说明 | speaker_id |
|------|------|------------|
| action | 动作/舞台指示 | 不需要 |
| dialogue | 角色对白 | 必填 |
| voiceover | 旁白/内心独白/画外音 | 可选 |
| transition | 转场效果（FADE IN 等） | 不需要 |
| sound | 音效提示 | 不需要 |
| note | 编剧注释 | 不需要 |

**角色类型（characters[].role_type）:** 主角 / 配角 / 龙套

**时段（scenes[].time）:** 清晨 / 上午 / 下午 / 傍晚 / 夜晚 / 深夜 / 黎明

**置信度（content[].ai_confidence）:** 0–1 之间的小数。建议: ≥0.9 可直接采用，0.7–0.9 建议审阅，0.5–0.7 可能需修改，<0.5 建议重写。

---

## 转换流程

```
前端                          后端
 |                             |
 |-- POST /projects ---------->|  创建项目
 |<--- 201 project_id ---------|
 |                             |
 |-- POST /projects/{id}/convert ->|  触发转换
 |<--- 202 task_id ------------|     (返回立即)
 |                             |     (后台线程启动)
 |                             |     → 阶段 1: 提取角色
 |-- GET /tasks/{task_id} ---->|     → 阶段 2: 拆分场景
 |<--- { progress: 25% } ------|     → 阶段 3: 生成内容
 |                             |     → 阶段 4: 组装 YAML
 |-- GET /tasks/{task_id} ---->|
 |<--- { progress: 100% } -----|     保存剧本
 |                             |
 |-- GET /projects/{id}/script ->|  获取剧本
 |<--- 剧本 JSON --------------|
 |                             |
 |-- PUT /projects/{id}/script ->|  保存编辑
 |<--- 200 ok -----------------|
 |                             |
 |-- GET /projects/{id}/export?format=yaml ->|  导出
 |<--- YAML 文件 --------------|
```
