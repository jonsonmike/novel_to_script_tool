"""
AI 小说转剧本工具 — Streamlit 前端

启动方式:
    cd frontend
    streamlit run app.py

后端需先启动:
    cd backend
    uvicorn src.main:app --reload --port 8000
"""
from __future__ import annotations

import streamlit as st

from src import api
from src.components.project import render_create_project, render_project_list
from src.components.characters import render_characters_panel
from src.components.scenes import render_scene_editor
from src.components.export import render_export_panel, render_script_overview


# ═══════════════════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI 小说转剧本工具",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════════
# 初始化 Session State
# ═══════════════════════════════════════════════════════════
def init_session_state() -> None:
    """初始化会话状态"""
    defaults: dict[str, object] = {
        "current_project_id": "",
        "current_page": "dashboard",
        "backend_online": None,  # None = 未检测, True/False
        "script_data": None,     # 当前剧本数据缓存
        "characters": [],
        "scenes": [],
        "meta": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ═══════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════
def render_sidebar() -> None:
    """渲染侧边栏导航和系统状态"""
    with st.sidebar:
        st.image(
            "https://img.icons8.com/color/96/film-reel--v1.png",
            width=64,
        )
        st.title("🎬 小说转剧本")
        st.caption("AI Novel → Script Tool")

        st.divider()

        # ── 导航菜单 ──────────────────────────────────────
        page_map = {
            "🏠 系统概览": "dashboard",
            "📁 创建项目": "create",
            "📋 项目列表": "list",
            "⚙️ 转换管理": "convert",
            "🎭 角色库": "characters",
            "🎬 场景编辑": "scenes",
            "📤 导出剧本": "export",
        }
        reverse_page_map = {v: k for k, v in page_map.items()}
        labels = list(page_map.keys())

        # 程序跳转时同步 radio 显示
        current = st.session_state.get("current_page", "dashboard")
        expected_label = reverse_page_map.get(current, labels[0])
        if st.session_state.get("nav_radio", "") != expected_label:
            st.session_state["nav_radio"] = expected_label

        def on_nav_change():
            """仅在用户手动切换导航时更新页面"""
            st.session_state["current_page"] = page_map[st.session_state.nav_radio]

        st.radio(
            "📌 导航",
            options=labels,
            key="nav_radio",
            on_change=on_nav_change,
        )

        st.divider()

        # ── 后端状态指示 ──────────────────────────────────
        if st.button("🔌 检测后端连接", use_container_width=True):
            with st.spinner("检测中…"):
                ok, data, err = api.health_check()
                st.session_state["backend_online"] = ok
                if ok:
                    st.session_state["backend_version"] = (
                        data.get("version", "") if data else ""
                    )

        online = st.session_state.get("backend_online")
        if online is True:
            ver = st.session_state.get("backend_version", "")
            st.success(f"✅ 后端在线 {ver}")
        elif online is False:
            st.error("❌ 后端离线")
            st.caption("请执行: uvicorn src.main:app --port 8000")
        else:
            st.info("⚪ 尚未检测后端")

        st.divider()

        # ── 当前项目 ──────────────────────────────────────
        pid = st.session_state.get("current_project_id", "")
        if pid:
            st.markdown(f"**📂 当前项目**")
            st.code(pid, language=None)
            if st.button("✖️ 关闭项目", use_container_width=True):
                st.session_state["current_project_id"] = ""
                st.session_state["script_data"] = None
                st.session_state["characters"] = []
                st.session_state["scenes"] = []
                st.session_state["meta"] = {}
                st.rerun()
        else:
            st.caption("未打开项目")


# ═══════════════════════════════════════════════════════════
# 页面路由
# ═══════════════════════════════════════════════════════════
def main() -> None:
    """主入口"""

    render_sidebar()

    page = st.session_state.get("current_page", "dashboard")
    project_id = st.session_state.get("current_project_id", "")

    # ── Dashboard / 系统概览 ───────────────────────────────
    if page == "dashboard":
        st.header("🏠 系统概览")

        # 自动检测后端
        if st.session_state.get("backend_online") is None:
            with st.spinner("正在检测后端服务…"):
                ok, data, err = api.health_check()
                st.session_state["backend_online"] = ok
                if ok and data:
                    st.session_state["backend_version"] = data.get("version", "")

        online = st.session_state.get("backend_online")
        if online:
            st.success("✅ 后端服务运行正常")
        else:
            st.error("❌ 无法连接后端服务")
            st.info(
                "请先启动后端服务:\n\n"
                "```bash\n"
                "cd backend\n"
                "pip install -r requirements.txt\n"
                "uvicorn src.main:app --reload --port 8000\n"
                "```"
            )
            st.info(
                "启动前端:\n\n"
                "```bash\n"
                "cd frontend\n"
                "pip install -r requirements.txt\n"
                "streamlit run app.py\n"
                "```"
            )

        # ── 使用流程 ──────────────────────────────────────
        st.divider()
        st.subheader("📖 使用流程")
        st.markdown(
            """
            1. **创建项目** — 粘贴小说正文，设置改编参数
            2. **触发转换** — AI 自动分析小说，生成角色库和剧本
            3. **编辑剧本** — 在场景编辑器中审阅和修改内容块
            4. **导出剧本** — 下载 YAML / JSON 格式的完整剧本
            """
        )

        # ── Schema 信息 ────────────────────────────────────
        with st.expander("📐 数据 Schema 说明", expanded=False):
            st.markdown(
                """
                **剧本输出结构**（v1.2.0）：
                - **meta** — 元信息（标题、改编范围、用户指令、生成时间）
                - **characters[]** — 全剧角色库
                  - id (CHAR_xxx)、name、role_type (主角/配角/龙套)
                  - traits、physical_description、aliases
                - **scenes[]** — 按时间线排列的场景
                  - scene_id (S0001)、scene_number、location、time
                  - characters_present (引用角色 ID)
                  - **content[]** — 混合类型内容块:
                    - 🎬 action — 动作/舞台指示
                    - 💬 dialogue — 角色对白（绑定 speaker_id）
                    - 🎙️ voiceover — 旁白/内心独白
                    - ⏭️ transition — 转场效果
                    - 🔊 sound — 音效提示
                    - 📝 note — 编剧注释
                """
            )

    # ── 创建项目 ───────────────────────────────────────────
    elif page == "create":
        render_create_project()

    # ── 项目列表 ───────────────────────────────────────────
    elif page == "list":
        render_project_list()

    # ── 转换管理 ───────────────────────────────────────────
    elif page == "convert":
        st.header("⚙️ 转换管理")

        if not project_id:
            st.info("请先在「项目列表」中打开一个项目。")
        else:
            st.markdown(f"**当前项目**: `{project_id}`")

            # 触发转换
            st.subheader("🚀 触发 AI 转换")
            st.caption("将小说文本发送给 DeepSeek AI，生成结构化剧本。")

            if st.button("🤖 开始 AI 转换", type="primary"):
                with st.spinner("正在提交转换任务…"):
                    ok, data, err = api.trigger_convert(project_id)

                if ok and data:
                    task_id = data.get("task_id", "")
                    st.success(f"✅ 转换任务已提交！任务 ID: {task_id}")
                    st.session_state["convert_task_id"] = task_id
                    st.info("转换正在后台进行。请点击下方「刷新进度」查看状态。")
                else:
                    st.error(f"提交失败：{err}")

            # 查询进度
            task_id = st.session_state.get("convert_task_id", "")
            if task_id:
                st.divider()
                st.subheader("📊 转换进度")

                if st.button("🔄 刷新进度"):
                    with st.spinner("查询中…"):
                        ok, data, err = api.query_task(project_id, task_id)
                        if ok and data:
                            status = data.get("status", "unknown")
                            progress_val = data.get("progress", 0)
                            st.progress(progress_val / 100 if progress_val else 0)
                            st.markdown(f"**状态**: {status}")
                            st.markdown(f"**进度**: {progress_val}%")
                            if status == "completed":
                                st.success("🎉 转换完成！请前往「场景编辑」查看结果。")
                                # 自动加载剧本
                                ok2, script, _ = api.get_script(project_id)
                                if ok2 and script:
                                    st.session_state["script_data"] = script
                                    st.session_state["characters"] = script.get("characters", [])
                                    st.session_state["scenes"] = script.get("scenes", [])
                                    st.session_state["meta"] = script.get("meta", {})
                        else:
                            st.warning(f"查询失败：{err}")

            # 手动加载剧本
            st.divider()
            st.subheader("📥 加载已有剧本")
            if st.button("📥 从后端加载剧本数据"):
                with st.spinner("加载中…"):
                    ok, script, err = api.get_script(project_id)
                    if ok and script:
                        st.session_state["script_data"] = script
                        st.session_state["characters"] = script.get("characters", [])
                        st.session_state["scenes"] = script.get("scenes", [])
                        st.session_state["meta"] = script.get("meta", {})
                        st.success("✅ 剧本数据已加载")
                        st.rerun()
                    else:
                        st.warning(f"加载失败：{err or '尚未生成剧本'}")

    # ── 角色库 ─────────────────────────────────────────────
    elif page == "characters":
        characters = st.session_state.get("characters", [])
        if not characters and project_id:
            # 尝试从后端加载
            with st.spinner("正在加载角色数据…"):
                ok, script, _ = api.get_script(project_id)
                if ok and script:
                    st.session_state["script_data"] = script
                    st.session_state["characters"] = script.get("characters", [])
                    st.session_state["scenes"] = script.get("scenes", [])
                    st.session_state["meta"] = script.get("meta", {})
                    characters = st.session_state["characters"]

        render_characters_panel(characters)

    # ── 场景编辑 ──────────────────────────────────────────
    elif page == "scenes":
        st.header("🎬 场景编辑")

        characters = st.session_state.get("characters", [])
        scenes = st.session_state.get("scenes", [])

        if not scenes and project_id:
            with st.spinner("正在加载剧本数据…"):
                ok, script, _ = api.get_script(project_id)
                if ok and script:
                    st.session_state["script_data"] = script
                    st.session_state["characters"] = script.get("characters", [])
                    st.session_state["scenes"] = script.get("scenes", [])
                    st.session_state["meta"] = script.get("meta", {})
                    characters = st.session_state["characters"]
                    scenes = st.session_state["scenes"]

        if not scenes:
            st.info("暂无场景数据。请先在「转换管理」中触发 AI 转换或加载已有剧本。")
        else:
            # 剧本概览
            script_data = st.session_state.get("script_data", {})
            if script_data:
                render_script_overview(script_data)

            st.divider()

            # 场景编辑器
            modified_scenes = render_scene_editor(scenes, characters)

            # 保存按钮
            st.divider()
            col_save, col_reset = st.columns(2)
            with col_save:
                if st.button("💾 保存剧本到后端", type="primary", use_container_width=True):
                    if project_id:
                        script_data = {
                            "meta": st.session_state.get("meta", {}),
                            "characters": characters,
                            "scenes": modified_scenes,
                        }
                        ok, data, err = api.save_script(project_id, script_data)
                        if ok:
                            st.session_state["scenes"] = modified_scenes
                            st.session_state["script_data"] = script_data
                            st.success("✅ 剧本已保存")
                        else:
                            st.error(f"保存失败：{err}")
                    else:
                        st.warning("请先打开一个项目")
            with col_reset:
                if st.button("🔄 重新加载", use_container_width=True):
                    st.session_state["script_data"] = None
                    st.session_state["characters"] = []
                    st.session_state["scenes"] = []
                    st.rerun()

    # ── 导出 ───────────────────────────────────────────────
    elif page == "export":
        if project_id:
            # 确保有数据
            script_data = st.session_state.get("script_data")
            if not script_data:
                with st.spinner("正在加载剧本…"):
                    ok, script, _ = api.get_script(project_id)
                    if ok and script:
                        st.session_state["script_data"] = script
                        st.session_state["characters"] = script.get("characters", [])
                        st.session_state["scenes"] = script.get("scenes", [])
                        st.session_state["meta"] = script.get("meta", {})

            render_export_panel(project_id)
        else:
            st.info("请先在「项目列表」中打开一个项目。")


# ═══════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
