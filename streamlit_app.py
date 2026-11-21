"""
铺掌柜 ShopKeeper — 主入口
零售进销存解决方案 · 扫码收银 · 库存管家
架构：config → database → models → services → ui → app (入口)
"""
import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# config 负责把 database/ 的可能位置（根目录或 data/）加入导入路径，
# 因此必须先于 database 相关模块导入。
from config import (APP_NAME, APP_NAME_EN, APP_VERSION, APP_ICON,
                    APP_TAGLINE, DB_PATH)
from database.migrations import initialize_database, migrate_from_excel
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)

# 侧边栏导航分组：分组名 -> 页面列表（页面名同时作为路由键）
NAV_GROUPS = {
    "📌 核心业务": ["📊 数据看板", "🛒 销售模式", "📦 入库模式", "🔄 退货管理"],
    "📋 数据管理": ["📝 商品管理", "📋 进货管理", "📈 销售分析"],
    "🔧 扩展功能": ["👤 会员管理", "🏭 供应商管理", "📋 库存盘点", "📦 批量操作"],
    "⚙️ 系统管理": ["🏷️ 打印标签", "💾 数据备份"],
}


def init_app():
    """应用初始化"""
    initialize_database()

    db = get_db()
    conn = db.get_connection()
    product_count = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()['cnt']

    if product_count == 0:
        from config import EXCEL_PRODUCT_PATH
        if os.path.exists(EXCEL_PRODUCT_PATH):
            logger.info("检测到 Excel 数据，开始自动迁移...")
            with st.spinner("正在从 Excel 迁移数据到 SQLite..."):
                result = migrate_from_excel()
                if result['total'] > 0:
                    st.toast(f"✅ 数据迁移完成！共 {result['total']} 条", icon="✅")

    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        st.session_state.cart = {}
        for key in ['new_product_barcode', 'existing_barcode',
                     'purchase_barcode_input', 'sale_barcode_input']:
            st.session_state.pop(key, None)

    if 'backup_on_start' not in st.session_state:
        st.session_state.backup_on_start = True
        try:
            from services.backup_service import BackupService
            svc = BackupService()
            svc.create_backup()
        except Exception as e:
            logger.warning(f"启动备份跳过: {e}")


def apply_custom_css():
    """专业级 UI 主题：渐变 + 玻璃态 + 微交互 + 动画"""
    st.markdown("""
    <style>
    /* ===== CSS 变量 ===== */
    :root {
        --c-primary: #4361ee;
        --c-primary-l: #4895ef;
        --c-primary-d: #3f37c9;
        --c-success: #06d6a0;
        --c-warning: #ffd166;
        --c-danger: #ef476f;
        --c-bg: #f0f4f8;
        --c-surface: #ffffff;
        --c-text: #1e293b;
        --c-text-2: #64748b;
        --c-border: #e2e8f0;
        --r-sm: 8px;
        --r-md: 12px;
        --r-lg: 16px;
        --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,.07), 0 2px 4px -2px rgba(0,0,0,.05);
        --shadow-lg: 0 10px 15px -3px rgba(0,0,0,.08), 0 4px 6px -4px rgba(0,0,0,.04);
        --transition: 0.2s cubic-bezier(.4,0,.2,1);
    }

    .stApp { background: var(--c-bg); }

    /* ===== 侧边栏 ===== */
    section[data-testid="stSidebar"] {
        width: 280px !important;
        background: linear-gradient(175deg, #0f172a 0%, #1e293b 40%, #1a1a2e 100%);
        border-right: none;
    }
    section[data-testid="stSidebar"] * {
        color: #cbd5e1 !important;
        border-color: rgba(255,255,255,.06) !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label {
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
        color: #94a3b8 !important; font-weight: 600; margin-bottom: 4px;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
        border-radius: var(--r-sm);
        transition: var(--transition);
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
        background: rgba(255,255,255,.1); border-color: rgba(255,255,255,.2);
    }
    section[data-testid="stSidebar"] div[data-baseweb="popover"] {
        background: #1e293b; border: 1px solid rgba(255,255,255,.1);
        border-radius: var(--r-sm);
    }

    /* ===== 侧边栏指标 ===== */
    section[data-testid="stSidebar"] div[data-testid="stMetric"] {
        background: rgba(255,255,255,.05) !important;
        border: 1px solid rgba(255,255,255,.08) !important;
        border-radius: var(--r-sm) !important;
        padding: 12px !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {
        color: #f1f5f9 !important; font-size: 1.3rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important; font-size: 0.7rem !important;
    }

    /* ===== 指标卡片 ===== */
    div[data-testid="stMetric"] {
        background: var(--c-surface) !important;
        padding: 18px 16px !important;
        border-radius: var(--r-md) !important;
        box-shadow: var(--shadow-sm) !important;
        border: 1px solid var(--c-border) !important;
        transition: transform var(--transition), box-shadow var(--transition) !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: var(--shadow-lg) !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.75rem !important; font-weight: 700 !important;
        color: var(--c-primary) !important; letter-spacing: -0.02em !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.78rem !important; color: var(--c-text-2) !important;
        font-weight: 500 !important; text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }

    /* ===== 按钮 ===== */
    .stButton button {
        border-radius: var(--r-sm) !important; font-weight: 600 !important;
        transition: all var(--transition) !important;
        letter-spacing: 0.01em !important; border: none !important;
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, var(--c-primary) 0%, var(--c-primary-d) 100%) !important;
        color: #fff !important; box-shadow: 0 2px 8px rgba(67,97,238,.3) !important;
    }
    .stButton button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(67,97,238,.4) !important;
    }
    .stButton button[kind="secondary"] {
        background: var(--c-surface) !important; color: var(--c-text) !important;
        border: 1px solid var(--c-border) !important; box-shadow: var(--shadow-sm) !important;
    }
    .stButton button[kind="secondary"]:hover {
        border-color: var(--c-primary-l) !important; color: var(--c-primary) !important;
    }

    /* ===== 输入框 ===== */
    .stTextInput input, .stSelectbox [data-baseweb="select"] > div,
    .stNumberInput input, .stTextArea textarea {
        border-radius: var(--r-sm) !important;
        border: 1px solid var(--c-border) !important;
        transition: var(--transition) !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: var(--c-primary) !important;
        box-shadow: 0 0 0 3px rgba(67,97,238,.12) !important;
    }

    /* ===== 数据框 ===== */
    div[data-testid="stDataFrame"] {
        border-radius: var(--r-md) !important; overflow: hidden !important;
        box-shadow: var(--shadow-sm) !important; border: 1px solid var(--c-border) !important;
    }

    /* ===== Tabs ===== */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--c-surface); border-radius: var(--r-md);
        padding: 4px; gap: 4px; box-shadow: var(--shadow-sm);
        border: 1px solid var(--c-border); margin-bottom: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--r-sm) !important; padding: 8px 20px !important;
        font-weight: 500 !important; transition: var(--transition) !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--c-primary), var(--c-primary-d)) !important;
        color: #fff !important;
    }

    /* ===== 展开面板 ===== */
    .streamlit-expanderHeader {
        border-radius: var(--r-md) !important; border: 1px solid var(--c-border) !important;
        font-weight: 600 !important; transition: var(--transition) !important;
    }
    .streamlit-expanderHeader:hover { border-color: var(--c-primary-l) !important; }

    /* ===== 通知 ===== */
    .stAlert {
        border-radius: var(--r-md) !important; border: none !important;
        box-shadow: var(--shadow-md) !important; font-weight: 500 !important;
    }

    /* ===== 分割线 ===== */
    hr { margin: 0.75rem 0; border-color: var(--c-border); opacity: 0.6; }

    /* ===== Form 卡片容器 ===== */
    div[data-testid="stForm"] {
        background: var(--c-surface); border-radius: var(--r-lg);
        border: 1px solid var(--c-border); padding: 20px !important;
        box-shadow: var(--shadow-md);
    }

    /* ===== 进度条 ===== */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--c-primary), var(--c-primary-l)) !important;
    }

    /* ===== Toast ===== */
    div[data-testid="stToast"] {
        background: var(--c-surface) !important; border-radius: var(--r-md) !important;
        box-shadow: var(--shadow-lg) !important; border: 1px solid var(--c-border) !important;
    }

    /* ===== Chart 容器 ===== */
    div[data-testid="stLineChart"] {
        background: var(--c-surface); border-radius: var(--r-md);
        padding: 12px; border: 1px solid var(--c-border);
    }

    /* ===== 响应式 ===== */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] { width: 100% !important; }
        div[data-testid="stMetric"] { padding: 12px !important; }
        div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """侧边栏：分组导航 + 实时库存概览 + 快捷操作"""
    with st.sidebar:
        # Logo 区域
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
            <div style="width:42px;height:42px;background:linear-gradient(135deg,#4361ee,#3f37c9);
                 border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:22px;">
                {APP_ICON}
            </div>
            <div>
                <div style="font-size:1.15rem;font-weight:700;color:#f1f5f9;">{APP_NAME}</div>
                <div style="font-size:0.68rem;color:#94a3b8;">{APP_NAME_EN} v{APP_VERSION}</div>
            </div>
        </div>
        <div style="font-size:0.68rem;color:#64748b;margin-top:2px;">{APP_TAGLINE}</div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # === 分组导航 ===
        # 修复：原实现用 4 个永远非空 selectbox 做三元判断，结果恒等于最后一组，
        # 导致其余 12 个页面不可达。改为「分组 + 页面」两级导航。
        group = st.radio(
            "功能模块", list(NAV_GROUPS.keys()),
            label_visibility="collapsed", key="nav_group",
            horizontal=False,
        )
        current_mode = st.selectbox(
            "页面", NAV_GROUPS[group],
            label_visibility="collapsed", key="nav_page",
        )

        # 仅在真正切换页面时清理录入态；购物车有意保留，方便临时查资料后返回
        last_page = st.session_state.get("_last_page")
        if last_page and last_page != current_mode:
            for k in ('new_product_barcode', 'existing_barcode'):
                st.session_state.pop(k, None)
        st.session_state._last_page = current_mode

        st.markdown("---")

        # === 库存概览 ===
        st.caption("📦 库存状态")
        try:
            from services.inventory_service import InventoryService
            inv = InventoryService()
            stats = inv.get_inventory_stats()

            col1, col2 = st.columns(2)
            col1.metric("商品数", stats.get('total_products', 0))
            col2.metric("库存量", f"{stats.get('total_stock', 0)}")

            # 低库存进度条
            low_count = stats.get('low_stock_count', 0)
            total = stats.get('total_products', 1)
            healthy = max(total - low_count, 0)
            pct = healthy / total if total > 0 else 1

            if low_count > 0:
                st.progress(pct, text=f"健康率 {pct*100:.0f}%")
                st.warning(f"⚠️ {low_count} 种商品库存不足")
                with st.expander(f"查看详情 ({low_count})"):
                    low_items = stats.get('low_stock_items', [])
                    if low_items:
                        df_low = pd.DataFrame(low_items)
                        rename = {'name': '商品', 'stock': '库存', 'min_stock': '警戒'}
                        df_low = df_low.rename(columns=rename)
                        avail = [c for c in ['商品', '库存', '警戒'] if c in df_low.columns]
                        st.dataframe(df_low[avail], width='stretch', hide_index=True)
            else:
                st.progress(1.0, text="库存健康率 100%")
                st.success("✅ 所有商品库存正常")
        except Exception as e:
            logger.error(f"侧边栏加载失败: {e}")

        return current_mode


def route_page(mode: str):
    """页面路由"""
    routes = {
        "📊 数据看板": ("ui.dashboard", "show"),
        "🛒 销售模式": ("ui.sale_page", "show"),
        "📦 入库模式": ("ui.purchase_page", "show"),
        "🔄 退货管理": ("ui.returns_page", "show"),
        "📝 商品管理": ("ui.product_edit", "show"),
        "📋 进货管理": ("ui.purchase_mgmt", "show"),
        "📈 销售分析": ("ui.analysis_page", "show"),
        "👤 会员管理": ("ui.member_page", "show"),
        "🏭 供应商管理": ("ui.supplier_page", "show"),
        "📋 库存盘点": ("ui.stock_count_page", "show"),
        "📦 批量操作": ("ui.batch_ops_page", "show"),
        "🏷️ 打印标签": ("ui.print_labels_page", "show"),
        "💾 数据备份": ("ui.backup_page", "show"),
    }

    if mode in routes:
        module_path, func_name = routes[mode]
        import importlib
        module = importlib.import_module(module_path)
        getattr(module, func_name)()
    else:
        st.error(f"未知页面: {mode}")


def main():
    st.set_page_config(
        page_title=f"{APP_NAME} · {APP_NAME_EN}",
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": f"{APP_NAME} v{APP_VERSION} · {APP_TAGLINE}",
        },
    )

    apply_custom_css()
    init_app()

    current_mode = render_sidebar()
    route_page(current_mode)

    # 底部
    st.markdown(f"""<div style="text-align:center;padding:16px;color:#94a3b8;font-size:0.78rem;">
        {APP_NAME} · {APP_NAME_EN} v{APP_VERSION} · Streamlit + SQLite · {APP_TAGLINE}
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
