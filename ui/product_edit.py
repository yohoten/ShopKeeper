"""
商品管理页面 v2 — 卡片式编辑
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, search_box, section_card, toast_success, error_message
from services.inventory_service import InventoryService
from utils.helpers import generate_pinyin
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("📝 商品管理", "搜索 · 筛选 · 编辑商品信息")

    service = InventoryService()

    c1, c2, c3 = st.columns([2, 1, 1])
    kw = c1.text_input("🔍 搜索名称/条码/拼音", placeholder="输入关键词...", key="prod_s")
    cat_filter = c2.selectbox("分类", ["全部"] + service.get_categories())
    sort_by = c3.selectbox("排序", ["名称↑", "库存↓", "售价↓", "最近更新"])

    products = [p for p in service.search(kw) if cat_filter == "全部" or p.get('category') == cat_filter]
    if sort_by == "库存↓": products.sort(key=lambda x: x.get('stock', 0), reverse=True)
    elif sort_by == "售价↓": products.sort(key=lambda x: x.get('sale_price', 0), reverse=True)

    st.caption(f"共 {len(products)} 种商品")

    if not products:
        from ui.components import empty_state
        empty_state("无匹配商品", icon="🔍", suggestion="尝试其他搜索词")
        return

    df = pd.DataFrame(products)
    rename = {'name': '名称', 'barcode': '条码', 'category': '分类',
              'stock': '库存', 'purchase_price': '进价', 'sale_price': '售价',
              'min_stock': '警戒', 'pinyin_code': '拼音'}
    df = df.rename(columns=rename)
    avail = [c for c in ['名称', '条码', '分类', '库存', '进价', '售价', '警戒'] if c in df.columns]
    st.dataframe(df[avail], width='stretch',
                 column_config={'进价': st.column_config.NumberColumn(format="¥%.2f"),
                                '售价': st.column_config.NumberColumn(format="¥%.2f")})

    # 编辑
    st.markdown("---")
    with section_card("✏️ 编辑商品", ""):
        ids = [p['id'] for p in products]
        sel = st.selectbox("选择商品", ids, format_func=lambda x: next(
            f"{p['name']} (¥{p.get('sale_price',0):.2f})" for p in products if p['id'] == x))
        p = service.get_by_id(sel)
        if not p: return

        with st.form("edit_prod"):
            c1, c2 = st.columns(2)
            n = c1.text_input("商品名称", p.get('name', ''))
            cat = c1.selectbox("分类", service.get_categories(),
                               index=max(0, service.get_categories().index(p.get('category','未分类')) if p.get('category') in service.get_categories() else 0))
            bc = c1.text_input("条码", p.get('barcode', ''))
            bp = c1.number_input("进价", 0.0, float(p.get('purchase_price', 0)), format="%.2f")
            sp = c1.number_input("售价", 0.0, float(p.get('sale_price', 0)), format="%.2f")
            stk = c2.number_input("库存量", 0, int(p.get('stock', 0)))
            ms = c2.number_input("警戒库存", 0, int(p.get('min_stock', 10)))
            wp = c2.number_input("批发价", 0.0, float(p.get('wholesale_price', 0)), format="%.2f")
            mp = c2.number_input("会员价", 0.0, float(p.get('member_price', 0)), format="%.2f")
            rm = c2.text_area("备注", p.get('remark', ''))

            if st.form_submit_button("💾 保存修改", type="primary", width='stretch'):
                data = {'name': n, 'category': cat, 'barcode': bc, 'purchase_price': bp,
                        'sale_price': sp, 'wholesale_price': wp, 'member_price': mp,
                        'min_stock': ms, 'pinyin_code': generate_pinyin(n), 'remark': rm}
                ok = service.edit(sel, data)['success']
                stock_ok = True
                if stk != p['stock']:
                    from models.product import update_stock
                    stock_ok = update_stock(sel, stk - p['stock'])
                if ok and stock_ok:
                    toast_success("商品信息已更新")
                    st.rerun()
                else:
                    error_message("保存失败，请检查库存是否充足或数据是否合法")
