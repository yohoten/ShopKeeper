"""
库存盘点页面 v2
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, date_range_picker, section_card
from ui.components import toast_success, error_message
from services.stock_count_service import StockCountService
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("📋 库存盘点", "实物盘点 · 盈亏调整 · 历史")
    svc = StockCountService()
    tab1, tab2, tab3 = st.tabs(["➕ 新建盘点", "⏳ 待确认", "📋 历史"])
    with tab1: _new(svc)
    with tab2: _pending(svc)
    with tab3: _history(svc)


def _new(svc):
    products = svc.get_all_products_for_count()
    if not products:
        from ui.components import empty_state
        empty_state("无商品可盘点", icon="📦")
        return
    kw = st.text_input("🔍 搜索", key="sc_s", placeholder="名称或条码...")
    cat = st.selectbox("分类", ["全部"] + list(set(p.get('category', '') for p in products)))
    filtered = [p for p in products if (not kw or kw.lower() in p.get('name', '').lower() or kw in str(p.get('barcode', ''))) and (cat == "全部" or p.get('category') == cat)]

    if not filtered:
        from ui.components import empty_state
        empty_state("无匹配", icon="🔍")
        return

    df = pd.DataFrame(filtered)
    rename = {'name': '商品', 'barcode': '条码', 'stock': '账面', 'purchase_price': '成本'}
    df = df.rename(columns=rename)
    st.dataframe(df[['商品', '条码', '账面', '成本']], width='stretch')

    with section_card("录入盘点", ""):
        sel = st.selectbox("选择商品", [p['id'] for p in filtered],
                           format_func=lambda x: next(f"{p['name']} (账面:{p['stock']})" for p in filtered if p['id'] == x))
        p = next(pp for pp in filtered if pp['id'] == sel)
        c1, c2 = st.columns(2)
        c1.metric("账面库存", p['stock'])
        actual = c2.number_input("实盘数量", 0, value=int(p['stock']))
        diff = actual - p['stock']
        if diff != 0:
            st.warning(f"差异: {diff:+d}")
        reason = st.text_area("原因（差异时填写）")
        if st.button("📝 提交盘点", type="primary", width='stretch'):
            r = svc.create_count(sel, actual, reason, "admin")
            if r['success']: toast_success("✅ 已提交"); st.rerun()
            else: error_message(r['message'])


def _pending(svc):
    items = svc.get_pending()
    if not items:
        from ui.components import empty_state
        empty_state("无待确认盘点", icon="✅")
        return
    for item in items:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
        c1.write(f"**{item.get('name','')}**")
        c2.caption(f"账面: {item['book_stock']}")
        c3.caption(f"实盘: {item['actual_stock']}")
        d = item.get('diff_stock', 0)
        c4.caption(f"差异: {d:+d}")
        if c5.button("✅ 确认", key=f"cf_{item['id']}"):
            svc.confirm(item['id'])
            toast_success("✅ 已确认，库存已调整")
            st.rerun()
        st.divider()


def _history(svc):
    sd, ed = date_range_picker(start_key="sc_sd", end_key="sc_ed", default_days=90)
    stf = st.selectbox("状态", ["全部", "待确认", "已确认"])
    records = svc.get_records(sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"),
                              None if stf == "全部" else stf)
    sts = svc.get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("总数", sts['total'])
    c2.metric("待确认", sts['pending'])
    c3.metric("盈亏", f"¥{sts['total_diff_amount']:,.2f}")
    if not records:
        from ui.components import empty_state
        empty_state("暂无记录", icon="📋")
        return
    df = pd.DataFrame(records)
    rename = {'count_time': '时间', 'name': '商品', 'book_stock': '账面',
              'actual_stock': '实盘', 'diff_stock': '差异', 'status': '状态'}
    df = df.rename(columns=rename)
    st.dataframe(df[['时间', '商品', '账面', '实盘', '差异', '状态']], width='stretch')
