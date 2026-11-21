"""
销售分析页面 v2 — 精美图表
"""
import streamlit as st
import pandas as pd
from services.report_service import ReportService
from ui.components import page_header, date_range_picker, section_card
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("📈 销售分析", "趋势洞察 · 热销排行 · 数据导出")

    sd, ed = date_range_picker(start_key="sa_s", end_key="sa_e", default_days=30)
    s, e = sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d")
    svc = ReportService()

    try:
        summary = svc.get_sales_summary(s, e)
        daily = svc.get_daily_trend(s, e)
        top = svc.get_top_products(s, e, 10)
        detail = svc.get_sales_detail(s, e)
    except Exception as e:
        st.error(f"加载失败: {e}")
        return

    # 指标
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("总销售额", f"¥{summary['total_revenue']:,.2f}")
    c2.metric("总利润", f"¥{summary['total_profit']:,.2f}")
    c3.metric("总销量", f"{summary['total_quantity']} 件")
    c4.metric("商品数", str(summary['product_count']))
    c5.metric("交易笔数", str(summary['transaction_count']))
    rev = summary['total_revenue']
    margin = summary['total_profit'] / max(rev, 1) * 100
    st.caption(f"综合利润率: {margin:.1f}%")

    # 趋势
    st.markdown("---")
    if daily:
        df_t = pd.DataFrame(daily)
        df_t['sale_date'] = pd.to_datetime(df_t['sale_date'])
        tab1, tab2 = st.tabs(["💰 销售额趋势", "📊 利润趋势"])
        tab1.area_chart(df_t.set_index('sale_date')['total_revenue'], width='stretch', color="#4361ee")
        tab2.area_chart(df_t.set_index('sale_date')['total_profit'], width='stretch', color="#06d6a0")
    else:
        from ui.components import empty_state
        empty_state("暂无趋势", "📉")

    # 排行 + 明细
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.markdown("##### 🔥 热销 TOP 10")
        if top:
            df_p = pd.DataFrame(top)
            rename = {'name': '商品', 'total_quantity': '销量', 'total_revenue': '销售额'}
            df_p = df_p.rename(columns=rename)
            st.dataframe(df_p[['商品', '销量', '销售额']], width='stretch', hide_index=True)
        else:
            from ui.components import empty_state
            empty_state("暂无", "🏆")

    with c2:
        st.markdown("##### 📋 销售明细")
        if detail:
            df_d = pd.DataFrame(detail)
            rename = {'sale_time': '时间', 'name': '商品', 'quantity': '数量',
                      'revenue': '金额', 'profit': '利润'}
            df_d = df_d.rename(columns=rename)
            st.dataframe(df_d[['时间', '商品', '数量', '金额', '利润']][:20],
                         width='stretch', hide_index=True)
            csv = df_d.to_csv(index=False).encode('utf-8-sig')
            st.download_button("⬇️ 下载 CSV", csv, f"sales_{s}_{e}.csv", "text/csv")
        else:
            from ui.components import empty_state
            empty_state("暂无明细", "📋")
