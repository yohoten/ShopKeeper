"""
数据看板页面 v2
精美仪表盘：渐变色指标卡、进度条、趋势图、热销排行、关联预警
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, metric_card, section_card, empty_state, progress_bar
from services.report_service import ReportService
from services.inventory_service import InventoryService
from utils.helpers import format_currency
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("📊 数据看板", "实时经营概览与关键指标监控")

    try:
        data = ReportService.get_dashboard_data()
    except Exception as e:
        logger.error(f"看板加载失败: {e}")
        st.error("获取数据失败，请检查数据库连接")
        return

    today = data['today_summary']
    week = data['week_summary']
    month = data['month_summary']
    inv = data['inventory_stats']

    # ===== 第一行：今日看板 =====
    st.markdown("##### 💰 今日经营概览")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("今日销售额", format_currency(today.get('total_revenue', 0)),
              delta=f"{today.get('transaction_count',0)} 笔")
    c2.metric("今日利润", format_currency(today.get('total_profit', 0)))
    c3.metric("毛利率",
              f"{today.get('total_profit',0)/max(today.get('total_revenue',1),1)*100:.1f}%"
              if today.get('total_revenue', 0) > 0 else "0%")
    c4.metric("今日销量", f"{today.get('total_quantity', 0)} 件")
    c5.metric("交易笔数", str(today.get('transaction_count', 0)))

    # ===== 第二行：本月概览 =====
    st.markdown("##### 📅 本月累计")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("本月销售额", format_currency(month.get('total_revenue', 0)))
    c2.metric("本月利润", format_currency(month.get('total_profit', 0)))
    c3.metric("本月订单", str(month.get('transaction_count', 0)))
    c4.metric("本月销量", f"{month.get('total_quantity', 0)} 件")

    # ===== 第三行：库存健康度 =====
    st.markdown("---")
    st.markdown("##### 📦 库存健康度")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("商品种类", str(inv.get('total_products', 0)))
    c2.metric("总库存量", f"{inv.get('total_stock', 0)} 件")
    c3.metric("库存总值", format_currency(inv.get('total_value', 0)))

    low_count = inv.get('low_stock_count', 0)
    total = max(inv.get('total_products', 1), 1)
    health_pct = (total - low_count) / total
    with c4:
        if low_count > 0:
            st.metric("低库存预警", str(low_count),
                      delta=f"{health_pct*100:.0f}% 健康率")
        else:
            st.metric("低库存预警", "0", delta="✅ 全部正常")

    # 库存健康进度条
    st.progress(health_pct, text=f"库存健康率 {health_pct*100:.0f}%"
                if low_count == 0 else f"⚠️ {low_count} 种商品需补货")

    # 低库存列表
    low_items = inv.get('low_stock_items', [])
    if low_items:
        with st.expander(f"⚠️ 低库存详情 ({len(low_items)} 种)", expanded=True):
            df_low = pd.DataFrame(low_items)
            rename = {'name': '商品名称', 'stock': '库存量',
                      'min_stock': '安全库存', 'sale_price': '售价'}
            df_low = df_low.rename(columns=rename)
            cols = [c for c in ['商品名称', '库存量', '安全库存', '售价'] if c in df_low.columns]
            st.dataframe(df_low[cols], width='stretch', hide_index=True)

    # ===== 第四行：趋势 + 排行 =====
    st.markdown("---")
    c1, c2 = st.columns([1.5, 1])

    with c1:
        st.markdown("##### 📈 近 7 天销售趋势")
        daily = data.get('daily_trend', [])
        if daily:
            df_trend = pd.DataFrame(daily)
            df_trend['sale_date'] = pd.to_datetime(df_trend['sale_date'])
            rename = {'total_revenue': '销售额', 'total_profit': '利润'}
            df_trend = df_trend.rename(columns=rename)

            tab1, tab2 = st.tabs(["💰 销售额", "📊 利润"])
            with tab1:
                st.area_chart(
                    df_trend.set_index('sale_date')['销售额'],
                    width='stretch', color="#4361ee"
                )
            with tab2:
                st.area_chart(
                    df_trend.set_index('sale_date')['利润'],
                    width='stretch', color="#06d6a0"
                )
        else:
            from ui.components import empty_state
            empty_state("暂无趋势数据", icon="📉")

    with c2:
        st.markdown("##### 🔥 本周热销 TOP 8")
        top = data.get('top_products', [])
        if top:
            df_top = pd.DataFrame(top[:8])
            rename = {'name': '商品', 'total_quantity': '销量', 'total_revenue': '销售额'}
            df_top = df_top.rename(columns=rename)
            df_top['排名'] = range(1, len(df_top) + 1)
            df_top = df_top.sort_values('销量', ascending=True)

            # 水平条形图
            st.bar_chart(
                df_top.set_index('商品')['销量'],
                width='stretch', horizontal=True,
                color="#4361ee"
            )
        else:
            from ui.components import empty_state
            empty_state("暂无排行数据", icon="🏆")
