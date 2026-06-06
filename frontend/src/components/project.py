"""
项目管理组件 — 创建项目、选择章节、配置改编参数
"""
from __future__ import annotations

import streamlit as st

from ..config import TONE_RECOMMENDATIONS
from .. import api


def render_create_project() -> None:
    """渲染「创建项目」页面"""
    st.header("📁 创建改编项目")

    # ── 项目基本信息 ──────────────────────────────────────
    st.subheader("1. 项目信息")

    novel_title = st.text_input(
        "原著小说名称",
        placeholder="例如：《剑影》",
        help="输入小说原著名，用于生成剧本元信息",
    )

    novel_text = st.text_area(
        "小说正文",
        placeholder="在此粘贴或输入小说原文…\n\n支持多章节文本，建议用「第X章」或「Chapter X」标记章节分界。",
        height=300,
        help="粘贴需要改编的小说文本。AI 将自动识别章节边界。",
    )

    # ── 章节选择 ──────────────────────────────────────────
    st.subheader("2. 章节选择（可选）")

    selected_chapters_raw = st.text_area(
        "指定改编章节",
        placeholder="每行一个章节，例如：\n第3章 初遇\n第4章 离别\n第5章 重逢\n\n留空则改编全部内容。",
        height=120,
        help="指定要改编的具体章节名称，每行一个。留空表示改编全部。",
    )

    selected_chapters: list[str] = []
    if selected_chapters_raw.strip():
        selected_chapters = [
            ch.strip() for ch in selected_chapters_raw.split("\n") if ch.strip()
        ]

    # ── 改编参数 ──────────────────────────────────────────
    st.subheader("3. 改编参数")

    col1, col2 = st.columns(2)

    with col1:
        tone = st.selectbox(
            "剧本基调",
            options=[""] + TONE_RECOMMENDATIONS,
            format_func=lambda x: "— 不指定 —" if x == "" else x,
            help="选择剧本的整体风格基调，也可留空由 AI 自动判断。",
        )

    with col2:
        focus_characters_raw = st.text_input(
            "重点刻画人物",
            placeholder="用逗号分隔，如：林墨, 苏晚",
            help="输入希望 AI 重点描写的人物名称。留空则由 AI 自动识别主要角色。",
        )

    focus_characters: list[str] = []
    if focus_characters_raw.strip():
        focus_characters = [
            n.strip() for n in focus_characters_raw.split(",") if n.strip()
        ]

    custom_prompt = st.text_area(
        "自定义改编指令",
        placeholder="例如：把打斗场面写得更加激烈，增加男主角的心理活动。\n或用自然语言描述你对改编的任何特殊要求…",
        height=100,
        help="自由输入的额外改编要求，将直接注入 AI prompt。",
    )

    # ── 提交 ──────────────────────────────────────────────
    st.divider()

    if st.button("🚀 创建项目并开始转换", type="primary", use_container_width=True):
        # 校验
        if not novel_text.strip():
            st.error("请粘贴小说正文。")
            return
        if not novel_title.strip():
            st.warning("建议填写小说名称，将用作默认剧本标题。")

        with st.spinner("正在创建项目…"):
            ok, data, err = api.create_project(
                novel_text=novel_text,
                novel_title=novel_title.strip(),
                selected_chapters=selected_chapters,
                tone=tone,
                focus_characters=focus_characters,
                custom_prompt=custom_prompt.strip(),
            )

        if ok and data:
            st.session_state["current_project_id"] = data.get("project_id", "")
            st.success(f"✅ 项目创建成功！ID: {data.get('project_id', 'N/A')}")
            st.info("项目已创建，可在「转换管理」页面触发 AI 转换。")
            st.rerun()
        else:
            st.error(f"创建失败：{err}")


def render_project_list() -> None:
    """渲染项目列表"""
    st.header("📋 项目列表")

    ok, projects, err = api.list_projects()
    if not ok:
        st.error(f"无法获取项目列表：{err}")
        return

    if not projects:
        st.info("暂无项目，请先创建项目。")
        return

    # ── 删除确认状态 ──────────────────────────────────────
    confirm_delete = st.session_state.get("confirm_delete", "")

    for proj in projects:
        pid = proj.get("project_id", proj.get("id", ""))
        title = proj.get("novel_title", "未命名项目")
        status = proj.get("status", "unknown")
        created = proj.get("created_at", "")

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"**{title}**")
                st.caption(f"ID: {pid}  |  创建: {created}")
            with cols[1]:
                st.code(status, language=None)
            with cols[2]:
                if st.button("📂 打开", key=f"open_{pid}"):
                    st.session_state["current_project_id"] = pid
                    st.rerun()
            with cols[3]:
                if st.button("🗑️ 删除", key=f"del_{pid}"):
                    st.session_state["confirm_delete"] = pid
                    st.rerun()

        # 当前项目需要二次确认
        if confirm_delete == pid:
            with st.container(border=True):
                st.warning(f"⚠️ 确定删除「**{title}**」？此操作不可撤销。")
                cc1, cc2, _ = st.columns([1, 1, 4])
                with cc1:
                    if st.button("✅ 确认删除", key=f"confirm_{pid}", type="primary"):
                        with st.spinner("删除中…"):
                            ok, data, err = api.delete_project(pid)
                        if ok:
                            st.success(f"✅ 项目「{title}」已删除")
                            # 如果删除的是当前打开的项目，清除状态
                            if st.session_state.get("current_project_id") == pid:
                                st.session_state["current_project_id"] = ""
                                st.session_state["script_data"] = None
                                st.session_state["characters"] = []
                                st.session_state["scenes"] = []
                                st.session_state["meta"] = {}
                            st.session_state["confirm_delete"] = ""
                            st.rerun()
                        else:
                            st.error(f"删除失败：{err}")
                with cc2:
                    if st.button("❌ 取消", key=f"cancel_{pid}"):
                        st.session_state["confirm_delete"] = ""
                        st.rerun()
