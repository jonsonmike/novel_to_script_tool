"""
角色面板组件 — 全剧角色库浏览、搜索、筛选
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from ..config import ROLE_TYPES


def render_characters_panel(characters: list[dict[str, Any]]) -> None:
    """渲染角色库面板"""
    st.header("🎭 角色库")

    if not characters:
        st.info("暂无角色数据。请先完成 AI 转换生成角色库。")
        return

    # ── 筛选栏 ────────────────────────────────────────────
    col_search, col_filter = st.columns([2, 1])

    with col_search:
        search_term = st.text_input(
            "🔍 搜索角色",
            placeholder="输入角色名、ID 或别名…",
            label_visibility="collapsed",
        ).strip().lower()

    with col_filter:
        role_filter = st.selectbox(
            "角色类型",
            options=["全部"] + ROLE_TYPES,
            label_visibility="collapsed",
        )

    # ── 过滤 ──────────────────────────────────────────────
    filtered: list[dict[str, Any]] = []
    for ch in characters:
        name = str(ch.get("name", "")).lower()
        cid = str(ch.get("id", "")).lower()
        aliases_lower = [str(a).lower() for a in ch.get("aliases", [])]
        role = ch.get("role_type", "")

        # 类型筛选
        if role_filter != "全部" and role != role_filter:
            continue

        # 关键词搜索
        if search_term:
            if (
                search_term not in name
                and search_term not in cid
                and not any(search_term in a for a in aliases_lower)
            ):
                continue

        filtered.append(ch)

    # ── 统计 ──────────────────────────────────────────────
    st.caption(f"共 {len(characters)} 个角色 · 当前显示 {len(filtered)} 个")
    st.divider()

    # ── 角色卡片 ──────────────────────────────────────────
    if not filtered:
        st.info("没有匹配的角色。")
        return

    for ch in filtered:
        with st.container(border=True):
            cid = ch.get("id", "?")
            name = ch.get("name", "未命名")
            role_type = ch.get("role_type", "")
            traits = ch.get("traits", [])
            physical = ch.get("physical_description", "")
            aliases = ch.get("aliases", [])

            # 标题行
            title_cols = st.columns([3, 1])
            with title_cols[0]:
                st.markdown(f"### {name}")
                st.caption(f"`{cid}`")
            with title_cols[1]:
                if role_type:
                    role_color_map = {"主角": "red", "配角": "blue", "龙套": "gray"}
                    color = role_color_map.get(role_type, "gray")
                    st.markdown(
                        f"<span style='color:{color};font-weight:bold'>{role_type}</span>",
                        unsafe_allow_html=True,
                    )

            # 性格标签
            if traits:
                tags = " ".join(
                    [f"`{t}`" for t in traits]
                )
                st.markdown(f"**性格**: {tags}")

            # 别名
            if aliases:
                st.markdown(f"**别名**: {' / '.join(aliases)}")

            # 外貌描述
            if physical:
                st.markdown(f"**外貌**: {physical}")
