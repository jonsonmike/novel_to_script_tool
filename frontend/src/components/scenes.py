"""
场景编辑器组件 — 场景导航、内容块渲染与编辑
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from ..config import (
    CONTENT_TYPES,
    CONTENT_TYPE_LABELS,
    TIME_PERIODS,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
)


def _confidence_indicator(confidence: float | None) -> str:
    """返回置信度 HTML 指示条"""
    if confidence is None:
        return ""
    if confidence >= CONFIDENCE_HIGH:
        color = "#22c55e"       # 绿 — 高可信
        label = "高"
    elif confidence >= CONFIDENCE_MEDIUM:
        color = "#eab308"       # 黄 — 建议审阅
        label = "中"
    elif confidence >= CONFIDENCE_LOW:
        color = "#f97316"       # 橙 — 可能需要修改
        label = "低"
    else:
        color = "#ef4444"       # 红 — 几乎需重写
        label = "极低"
    return (
        f"<span style='display:inline-block;width:60px;height:10px;"
        f"background:{color};border-radius:5px;margin-right:4px' title='AI置信度: {confidence:.0%}'></span>"
        f"<span style='font-size:0.75rem;color:{color}'>{label} ({confidence:.0%})</span>"
    )


def _render_content_block(
    block: dict[str, Any],
    idx: int,
    characters: list[dict[str, Any]],
    scene_index: int = 0,
    editing: bool = False,
) -> dict[str, Any] | None:
    """渲染单个内容块。返回编辑后的 block 或 None（未编辑）。"""
    btype = block.get("type", "action")
    text = block.get("text", "")
    speaker_id = block.get("speaker_id", "")
    emotion = block.get("emotion", "")
    confidence = block.get("ai_confidence")

    # 角色名称映射
    char_map: dict[str, str] = {ch.get("id", ""): ch.get("name", "") for ch in characters}

    # ── 根据类型选择渲染样式 ─────────────────────────────
    if btype == "action":
        # 灰色底、斜体
        st.markdown(
            f"<div style='background:#f3f4f6;padding:8px 12px;border-radius:6px;"
            f"font-style:italic;margin:4px 0'>{text}</div>",
            unsafe_allow_html=True,
        )

    elif btype == "dialogue":
        speaker_name = char_map.get(speaker_id, speaker_id)
        emoji = "💬"
        st.markdown(
            f"<div style='border-left:3px solid #3b82f6;padding:8px 12px;"
            f"margin:4px 0;background:#eff6ff;border-radius:0 6px 6px 0'>"
            f"<strong>{emoji} {speaker_name}</strong>"
            + (f" <span style='color:#6b7280'>[{emotion}]</span>" if emotion else "")
            + f"<br>{text}</div>",
            unsafe_allow_html=True,
        )

    elif btype == "voiceover":
        if speaker_id:
            speaker_name = char_map.get(speaker_id, speaker_id)
            header = f"🎙️ {speaker_name}（内心独白）"
        else:
            header = "🎙️ 第三人称旁白"
        st.markdown(
            f"<div style='border:1px dashed #a78bfa;padding:8px 12px;margin:4px 0;"
            f"border-radius:6px;background:#faf5ff;opacity:0.9'>"
            f"<em>{header}</em><br>{text}</div>",
            unsafe_allow_html=True,
        )

    elif btype == "transition":
        # 居中、加粗
        st.markdown(
            f"<div style='text-align:center;font-weight:bold;"
            f"text-transform:uppercase;letter-spacing:2px;"
            f"padding:8px;margin:8px 0;color:#6b7280'>{text}</div>",
            unsafe_allow_html=True,
        )

    elif btype == "sound":
        # 喇叭图标 + 蓝色文字
        st.markdown(
            f"<div style='color:#2563eb;padding:4px 12px;margin:4px 0'>"
            f"🔊 <em>{text}</em></div>",
            unsafe_allow_html=True,
        )

    elif btype == "note":
        # 黄色便签样式
        st.markdown(
            f"<div style='background:#fef9c3;padding:8px 12px;border-radius:4px;"
            f"margin:4px 0;border:1px solid #fde047;font-size:0.9rem'>"
            f"📝 <strong>编剧注:</strong> {text}</div>",
            unsafe_allow_html=True,
        )

    # ── 置信度指示 ────────────────────────────────────────
    if confidence is not None:
        st.markdown(_confidence_indicator(confidence), unsafe_allow_html=True)

    # ── 编辑模式 ──────────────────────────────────────────
    if editing:
        with st.expander(f"✏️ 编辑 #{idx+1} — {CONTENT_TYPE_LABELS.get(btype, btype)}", expanded=False):
            new_type = st.selectbox(
                "类型",
                options=CONTENT_TYPES,
                index=CONTENT_TYPES.index(btype) if btype in CONTENT_TYPES else 0,
                format_func=lambda t: CONTENT_TYPE_LABELS.get(t, t),
                key=f"ctype_s{scene_index}_b{idx}",
            )
            new_text = st.text_area(
                "内容",
                value=text,
                height=100,
                key=f"ctext_s{scene_index}_b{idx}",
            )
            new_speaker = ""
            if new_type in ("dialogue",):
                speaker_options = [""] + [
                    f"{ch.get('id', '')} — {ch.get('name', '')}"
                    for ch in characters
                ]
                current_speaker = (
                    f"{speaker_id} — {char_map.get(speaker_id, '')}"
                    if speaker_id
                    else ""
                )
                try:
                    sp_idx = speaker_options.index(current_speaker)
                except ValueError:
                    sp_idx = 0
                sp_sel = st.selectbox(
                    "说话人",
                    options=speaker_options,
                    index=sp_idx,
                    key=f"cspeaker_s{scene_index}_b{idx}",
                )
                if sp_sel:
                    new_speaker = sp_sel.split(" — ")[0]
            elif new_type == "voiceover":
                speaker_options = ["（无 — 第三人称叙述）"] + [
                    f"{ch.get('id', '')} — {ch.get('name', '')}"
                    for ch in characters
                ]
                current_speaker = (
                    f"{speaker_id} — {char_map.get(speaker_id, '')}"
                    if speaker_id
                    else "（无 — 第三人称叙述）"
                )
                try:
                    sp_idx = speaker_options.index(current_speaker)
                except ValueError:
                    sp_idx = 0
                sp_sel = st.selectbox(
                    "叙述者",
                    options=speaker_options,
                    index=sp_idx,
                    key=f"cspeaker_s{scene_index}_b{idx}",
                )
                if sp_sel and sp_sel != "（无 — 第三人称叙述）":
                    new_speaker = sp_sel.split(" — ")[0]

            new_emotion = st.text_input(
                "情绪标签",
                value=emotion,
                placeholder="例如：愤怒、平静中带着杀气…",
                key=f"cemotion_s{scene_index}_b{idx}",
            )

            new_confidence = st.slider(
                "AI 置信度",
                min_value=0.0,
                max_value=1.0,
                value=float(confidence) if confidence else 0.5,
                step=0.05,
                key=f"cconf_s{scene_index}_b{idx}",
            )

            if st.button("💾 应用修改", key=f"save_s{scene_index}_b{idx}"):
                return {
                    "type": new_type,
                    "text": new_text,
                    "speaker_id": new_speaker if new_speaker else None,
                    "emotion": new_emotion if new_emotion else None,
                    "ai_confidence": new_confidence,
                }

    return None


def render_scene_navigation(scenes: list[dict[str, Any]]) -> int | None:
    """渲染场景导航侧栏，返回选中的场景索引"""
    if not scenes:
        return None

    scene_options = [
        f"S{s.get('scene_number', i+1):04d} — {s.get('location', '未知地点')}"
        for i, s in enumerate(scenes)
    ]

    selected = st.radio(
        "📍 场景导航",
        options=range(len(scene_options)),
        format_func=lambda i: scene_options[i],
        key="scene_nav",
    )

    return selected


def render_scene_detail(
    scene: dict[str, Any],
    characters: list[dict[str, Any]],
    scene_index: int = 0,
) -> dict[str, Any] | None:
    """渲染单个场景详情，支持编辑。返回修改后的 scene 或 None。"""
    scene_id = scene.get("scene_id", f"S{scene.get('scene_number', 0):04d}")
    scene_number = scene.get("scene_number", 0)
    location = scene.get("location", "")
    time_period = scene.get("time", "")
    chapter_origin = scene.get("chapter_origin", "")
    characters_present = scene.get("characters_present", [])
    content = scene.get("content", [])

    # ── 场景标题 ──────────────────────────────────────────
    st.subheader(f"🎬 第 {scene_number} 场 — {location or '未指定地点'}")
    st.caption(f"ID: `{scene_id}`  |  来源章节: {chapter_origin or '—'}  |  时段: {time_period or '—'}")

    # ── 出场角色标签 ──────────────────────────────────────
    st.markdown("**出场角色**")
    if characters_present:
        char_map: dict[str, dict[str, Any]] = {
            ch.get("id", ""): ch for ch in characters
        }
        cols = st.columns(min(len(characters_present), 6))
        for i, cid in enumerate(characters_present):
            ch = char_map.get(cid, {})
            name = ch.get("name", cid)
            role_type = ch.get("role_type", "")
            emoji = {"主角": "⭐", "配角": "🔹", "龙套": "▪️"}.get(role_type, "👤")
            with cols[i % len(cols)]:
                st.markdown(f"{emoji} **{name}**")
    else:
        st.caption("（无角色信息）")

    # ── 内容块 ────────────────────────────────────────────
    st.divider()
    st.markdown("**📜 场景内容**")

    edit_mode = st.toggle("✏️ 编辑模式", key=f"edit_mode_{scene_index}")

    modified_blocks: list[dict[str, Any]] = []
    has_changes = False

    for i, block in enumerate(content):
        result = _render_content_block(block, i, characters, scene_index=scene_index, editing=edit_mode)
        if result is not None:
            modified_blocks.append(result)
            has_changes = True
        else:
            modified_blocks.append(block)

    # ── 添加新内容块 ──────────────────────────────────────
    if edit_mode:
        st.divider()
        st.markdown("**➕ 添加内容块**")
        with st.expander("新增内容块", expanded=False):
            new_type = st.selectbox(
                "类型",
                options=CONTENT_TYPES,
                format_func=lambda t: CONTENT_TYPE_LABELS.get(t, t),
                key=f"new_type_{scene_index}",
            )
            new_text = st.text_area(
                "内容",
                height=80,
                key=f"new_text_{scene_index}",
            )
            new_speaker = ""
            if new_type in ("dialogue", "voiceover"):
                speaker_opts = [""] + [
                    f"{ch.get('id', '')} — {ch.get('name', '')}"
                    for ch in characters
                ]
                sp_sel = st.selectbox(
                    "说话人/叙述者",
                    options=speaker_opts,
                    key=f"new_speaker_{scene_index}",
                )
                if sp_sel:
                    new_speaker = sp_sel.split(" — ")[0]

            if st.button("✅ 添加", key=f"add_block_{scene_index}"):
                if new_text.strip():
                    # 直接更新 session_state，避免 rerun 丢失
                    new_block = {
                        "type": new_type,
                        "text": new_text,
                        "speaker_id": new_speaker if new_speaker else None,
                        "emotion": None,
                        "ai_confidence": None,
                    }
                    modified_blocks.append(new_block)
                    # 立即持久化到 session state
                    st.session_state.scenes[scene_index]["content"] = modified_blocks
                    has_changes = True
                    st.rerun()

    # ── 返回 ──────────────────────────────────────────────
    if has_changes:
        new_scene = dict(scene)
        new_scene["content"] = modified_blocks
        return new_scene
    return None


def render_scene_editor(
    scenes: list[dict[str, Any]],
    characters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """完整的场景编辑器（导航 + 详情）"""
    if not scenes:
        st.info("暂无场景数据。请先完成 AI 转换生成剧本。")
        return scenes

    # 侧边栏：场景导航
    col_nav, col_detail = st.columns([1, 3])

    with col_nav:
        selected_idx = render_scene_navigation(scenes)

    with col_detail:
        if selected_idx is not None and 0 <= selected_idx < len(scenes):
            modified = render_scene_detail(
                scenes[selected_idx],
                characters,
                scene_index=selected_idx,
            )
            if modified is not None:
                scenes[selected_idx] = modified
                st.success("场景已修改（点击下方「保存剧本」持久化）")

    return scenes
