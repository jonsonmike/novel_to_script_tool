"""
导出与脚本查看组件 — YAML 导出、脚本预览
"""
from __future__ import annotations

import json
from typing import Any

import streamlit as st
import yaml

from .. import api


def render_export_panel(project_id: str) -> None:
    """渲染导出页面"""
    st.header("📤 导出剧本")

    if not project_id:
        st.info("请先在「项目管理」中打开一个项目。")
        return

    # ── 获取剧本数据 ──────────────────────────────────────
    ok, script_data, err = api.get_script(project_id)

    if not ok:
        st.error(f"获取剧本失败：{err}")
        return

    if not script_data:
        st.info("该项目尚未生成剧本。请先在「转换管理」中触发 AI 转换。")
        return

    # ── 导出格式选择 ──────────────────────────────────────
    st.subheader("选择导出格式")

    export_format = st.radio(
        "格式",
        options=["yaml", "json"],
        format_func=lambda f: {"yaml": "📄 YAML（推荐 — 可读性最好）", "json": "📋 JSON（程序消费）"}[f],
        horizontal=True,
    )

    # ── 预览 ──────────────────────────────────────────────
    st.divider()
    st.subheader("👁️ 预览")

    if export_format == "yaml":
        # YAML 预览
        yaml_text = yaml.dump(
            script_data,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
        st.code(yaml_text, language="yaml", line_numbers=True)
    else:
        # JSON 预览
        json_text = json.dumps(script_data, ensure_ascii=False, indent=2)
        st.code(json_text, language="json", line_numbers=True)

    # ── 下载按钮 ──────────────────────────────────────────
    st.divider()
    st.subheader("💾 下载")

    col1, col2 = st.columns(2)

    with col1:
        if export_format == "yaml":
            yaml_content = yaml.dump(
                script_data,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )
            st.download_button(
                label="⬇️ 下载 YAML 剧本",
                data=yaml_content,
                file_name=f"{script_data.get('meta', {}).get('script_title', 'script')}.yaml",
                mime="application/x-yaml",
                use_container_width=True,
            )
        else:
            json_content = json.dumps(script_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="⬇️ 下载 JSON 剧本",
                data=json_content,
                file_name=f"{script_data.get('meta', {}).get('script_title', 'script')}.json",
                mime="application/json",
                use_container_width=True,
            )

    with col2:
        # 也尝试从后端直接导出
        ok2, raw, err2 = api.export_script(project_id, format=export_format)
        if ok2 and raw:
            ext = "yaml" if export_format == "yaml" else "json"
            st.download_button(
                label=f"⬇️ 从后端导出（原始 {export_format.upper()}）",
                data=raw,
                file_name=f"{script_data.get('meta', {}).get('script_title', 'script')}_server.{ext}",
                mime="application/x-yaml" if export_format == "yaml" else "application/json",
                use_container_width=True,
            )


def render_script_overview(script_data: dict[str, Any]) -> None:
    """渲染剧本摘要视图（meta 信息 + 统计）"""
    meta = script_data.get("meta", {})
    characters = script_data.get("characters", [])
    scenes = script_data.get("scenes", [])

    # ── 元信息 ────────────────────────────────────────────
    st.subheader("📋 剧本信息")

    info_cols = st.columns(3)
    with info_cols[0]:
        st.metric("原著", meta.get("novel_title", "—"))
    with info_cols[1]:
        st.metric("剧本标题", meta.get("script_title", "—"))
    with info_cols[2]:
        st.metric("改编范围", meta.get("adapted_range", "—"))

    # ── 用户指令回显 ──────────────────────────────────────
    user_instr = meta.get("user_instructions", {})
    if user_instr:
        with st.expander("📝 改编指令", expanded=False):
            if user_instr.get("tone"):
                st.markdown(f"**基调**: {user_instr['tone']}")
            if user_instr.get("focus_characters"):
                st.markdown(f"**重点人物**: {'、'.join(user_instr['focus_characters'])}")
            if user_instr.get("custom_prompt"):
                st.markdown(f"**自定义指令**: {user_instr['custom_prompt']}")
            if user_instr.get("selected_chapters"):
                st.markdown(f"**选择章节**: {'、'.join(user_instr['selected_chapters'])}")

    # ── 统计卡片 ──────────────────────────────────────────
    st.divider()
    st.subheader("📊 剧本统计")

    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.metric("角色数", len(characters))
    with stat_cols[1]:
        st.metric("场景数", len(scenes))
    with stat_cols[2]:
        total_content = sum(len(s.get("content", [])) for s in scenes)
        st.metric("内容块总数", total_content)
    with stat_cols[3]:
        dialogue_count = sum(
            1 for s in scenes for b in s.get("content", []) if b.get("type") == "dialogue"
        )
        st.metric("对白数", dialogue_count)

    # ── 生成时间 ──────────────────────────────────────────
    generated_at = meta.get("generated_at", "")
    schema_ver = meta.get("schema_version", "")
    if generated_at or schema_ver:
        st.caption(f"生成时间: {generated_at or '—'}  |  Schema 版本: {schema_ver or '—'}")
