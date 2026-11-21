"""
可复用 UI 组件模块 v2
现代化组件：卡片容器、加载骨架、空状态、Toast、动画徽章
"""
import json
import time
from datetime import datetime, timedelta

import streamlit as st

from config import DEFAULT_DATE_RANGE_DAYS, DEFAULT_PAGE_SIZE


# ========== 页面头部 ==========

def page_header(title: str, subtitle: str = ""):
    """页面标题（带分隔线）"""
    st.markdown(f"""
    <div style="margin-bottom: 16px;">
        <h2 style="margin:0;font-weight:700;color:#1e293b;font-size:1.5rem;">{title}</h2>
        <p style="margin:4px 0 0 0;color:#64748b;font-size:0.85rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")


# ========== 卡片容器 ==========

def card_container(key: str = None):
    """卡片容器上下文管理器"""
    return st.container(border=True, key=key)


def section_card(title: str = "", icon: str = ""):
    """带标题的卡片区域"""
    if title:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;
                    padding:12px 16px;background:#f8fafc;border-radius:10px;
                    border:1px solid #e2e8f0;">
            <span style="font-size:1.2rem;">{icon}</span>
            <span style="font-weight:600;color:#1e293b;font-size:0.95rem;">{title}</span>
        </div>
        """, unsafe_allow_html=True)
    return st.container(border=False)


# ========== 指标卡片 ==========

def metric_card(label: str, value, delta: str = None, help_text: str = None,
                color: str = None, icon: str = ""):
    """增强版指标卡片（可选颜色和图标）"""
    display_value = f"{icon} {value}" if icon else value
    st.metric(label=label, value=display_value, delta=delta, help=help_text)


def stat_row(items: list, columns_per_row: int = 4):
    """一行多个统计指标"""
    cols = st.columns(columns_per_row)
    for i, (label, value, delta, help_text) in enumerate(items):
        with cols[i % columns_per_row]:
            metric_card(label, value, delta, help_text)


# ========== 搜索与输入 ==========

def search_box(key: str = "search", placeholder: str = "搜索...",
               label: str = "🔍 搜索", on_change=None) -> str:
    """搜索框"""
    return st.text_input(label, placeholder=placeholder, key=key, on_change=on_change)


def focus_barcode(key: str):
    """请求下一次 rerun 后自动聚焦指定扫码框（扫码枪场景免点击）。"""
    st.session_state[f"_focus_{key}"] = True


def barcode_input(label: str, key: str, on_change=None, autofocus: bool = True,
                  placeholder: str = "请扫描或输入条码...") -> str:
    """条码扫描输入：在需要时自动聚焦，扫码枪可连续扫码。

    Streamlit 的 text_input 没有 autofocus 参数，这里用一次性 JS 注入实现；
    只有在 focus_barcode() 请求过、或首次渲染时才聚焦，避免抢走其他控件的焦点。
    """
    widget = st.text_input(label, placeholder=placeholder, key=key, on_change=on_change)

    focus_key = f"_focus_{key}"
    if autofocus and st.session_state.get(focus_key, True):
        st.session_state[focus_key] = False
        ph = json.dumps(placeholder)
        st.components.v1.html(f"""
        <script>
        (function() {{
            var doc = (window.parent && window.parent.document) ? window.parent.document : document;
            var inp = doc.querySelector('input[placeholder={ph}]');
            if (inp) {{ inp.focus(); inp.select(); }}
        }})();
        </script>
        """, height=0)
    return widget


def date_range_picker(start_label: str = "开始日期",
                      end_label: str = "结束日期",
                      start_key: str = "start_date",
                      end_key: str = "end_date",
                      default_days: int = DEFAULT_DATE_RANGE_DAYS):
    """日期范围选择器"""
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input(
            start_label, datetime.now() - timedelta(days=default_days), key=start_key
        )
    with col2:
        end = st.date_input(end_label, datetime.now(), key=end_key)
    return start, end


# ========== 表格 ==========

def table_with_pagination(df, page_size: int = DEFAULT_PAGE_SIZE, key: str = "table",
                          column_config: dict = None):
    """带分页和空状态的数据表格"""
    if df.empty:
        empty_state("暂无数据", icon="📭")
        return

    total_rows = len(df)
    total_pages = (total_rows + page_size - 1) // page_size

    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            current = st.number_input(
                "页码", 1, total_pages, 1, key=f"page_{key}"
            )
        with col3:
            st.caption(f"共 {total_pages} 页")

        start = (current - 1) * page_size
        end = min(start + page_size, total_rows)
        st.dataframe(
            df.iloc[start:end],
            width='stretch', column_config=column_config
        )
        st.caption(f"第 {start+1}-{end} 条 · 共 {total_rows} 条")
    else:
        st.dataframe(df, width='stretch', column_config=column_config)


# ========== 空状态 & 加载 ==========

def empty_state(message: str = "暂无数据", icon: str = "📭",
                suggestion: str = ""):
    """空状态占位图"""
    html = f"""
    <div style="text-align:center;padding:48px 24px;">
        <div style="font-size:3rem;margin-bottom:12px;">{icon}</div>
        <div style="font-size:1rem;font-weight:500;color:#64748b;margin-bottom:4px;">{message}</div>
        {f'<div style="font-size:0.85rem;color:#94a3b8;">{suggestion}</div>' if suggestion else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def loading_spinner(message: str = "加载中..."):
    """加载旋转器"""
    return st.spinner(message)


def skeleton_card(lines: int = 3):
    """骨架屏"""
    html = '<div style="padding:16px;background:#f8fafc;border-radius:12px;animation:pulse 1.5s infinite;">'
    for i in range(lines):
        w = [80, 95, 60, 75, 50][i % 5]
        html += f'<div style="height:12px;width:{w}%;background:#e2e8f0;border-radius:6px;margin:8px 0;"></div>'
    html += '</div><style>@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}</style>'
    st.markdown(html, unsafe_allow_html=True)


# ========== 通知 ==========

def success_message(msg: str):
    st.success(msg)


def error_message(msg: str):
    st.error(msg)


def warning_message(msg: str):
    st.warning(msg)


def info_message(msg: str):
    st.info(msg)


def toast_success(msg: str):
    """Toast 通知"""
    st.toast(msg, icon="✅")


def toast_error(msg: str):
    st.toast(msg, icon="❌")


# ========== 按钮 ==========

def action_button(label: str, key: str, type: str = "secondary",
                  on_click=None, disabled: bool = False,
                  use_container_width: bool = False) -> bool:
    return st.button(
        label, key=key, type=type, on_click=on_click, disabled=disabled,
        width='stretch' if use_container_width else 'content',
    )


# ========== 徽章 ==========

def badge(text: str, color: str = "primary"):
    """小型徽章标签"""
    colors = {
        "primary": ("#4361ee", "#eef2ff"),
        "success": ("#06d6a0", "#ecfdf5"),
        "warning": ("#f59e0b", "#fffbeb"),
        "danger": ("#ef476f", "#fef2f2"),
        "info": ("#64748b", "#f8fafc"),
    }
    c = colors.get(color, colors["info"])
    st.markdown(f"""
    <span style="display:inline-block;padding:2px 10px;border-radius:99px;
                 background:{c[1]};color:{c[0]};font-size:0.75rem;font-weight:600;">
        {text}
    </span>
    """, unsafe_allow_html=True)


# ========== 进度条增强 ==========

def progress_bar(value: float, label: str = "", show_percentage: bool = True):
    """带标签的进度条"""
    pct = f" {value*100:.0f}%" if show_percentage else ""
    st.progress(value, text=f"{label}{pct}" if label or pct else None)
