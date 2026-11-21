"""
入库页面模块 v2 — 卡片式双列表单
"""
import streamlit as st
from datetime import datetime, timedelta
from services.purchase_service import PurchaseService
from ui.components import page_header, barcode_input, section_card
from ui.components import error_message, toast_success, focus_barcode
from config import DEFAULT_CATEGORIES
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("📦 商品入库管理", "扫码入库 · 新商品登记 · 库存追加")

    if 'purchase_barcode_input' not in st.session_state:
        st.session_state.purchase_barcode_input = ""

    def on_scan():
        barcode = st.session_state.purchase_barcode_input.strip()
        if not barcode:
            return
        result = PurchaseService().scan_barcode(barcode)
        # 互斥状态：避免「新增商品」与「已有商品」两个表单同时出现
        st.session_state.pop('new_product_barcode', None)
        st.session_state.pop('existing_barcode', None)
        if result['is_new']:
            st.session_state['new_product_barcode'] = barcode
        else:
            st.session_state['existing_barcode'] = barcode
        st.session_state.purchase_barcode_input = ""
        focus_barcode("purchase_barcode_input")
        st.rerun()

    with section_card("📷 扫描条码", ""):
        barcode_input("请扫描商品条码（入库）", key="purchase_barcode_input",
                      on_change=on_scan)

    if 'new_product_barcode' in st.session_state:
        _new_product_form(st.session_state.new_product_barcode)

    if 'existing_barcode' in st.session_state:
        _existing_form(st.session_state.existing_barcode)


def _new_product_form(barcode: str):
    with section_card(f"🆕 新增商品 · 条码: {barcode}", ""):
        with st.form("new_product_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("商品名称（必填）", placeholder="如：康师傅红烧牛肉面")
            cat = c1.selectbox("分类", DEFAULT_CATEGORIES)
            buy_price = c1.number_input("进货价（必填）", 0.0, format="%.2f")
            sell_price = c1.number_input("销售价（必填）", 0.0, format="%.2f")
            qty = c2.number_input("入库数量", 1, value=1)
            prod_date = c2.date_input("生产日期", datetime.now())
            shelf = c2.number_input("保质期（天）", 1, value=365)
            expiry = prod_date + timedelta(days=shelf)
            c2.caption(f"📅 到期: {expiry.strftime('%Y-%m-%d')}")

            submitted = st.form_submit_button("✅ 确认添加并入库", type="primary",
                                              width='stretch')
            if submitted:
                if not name.strip():
                    error_message("商品名称不能为空")
                    return
                result = PurchaseService().add_new_product(
                    {'name': name.strip(), 'category': cat, 'barcode': barcode,
                     'purchase_price': buy_price, 'sale_price': sell_price},
                    qty, prod_date, shelf
                )
                if result['success']:
                    st.session_state.pop('new_product_barcode', None)
                    toast_success(f"「{name}」创建成功 · 入库 {qty} 件")
                    st.rerun()
                else:
                    for err in result.get('errors', []):
                        error_message(err)

    if st.button("取消", key="cancel_new"):
        st.session_state.pop('new_product_barcode', None)
        st.rerun()


def _existing_form(barcode: str):
    service = PurchaseService()
    r = service.scan_barcode(barcode)
    if r['is_new'] or not r['product']:
        error_message(f"条码 {barcode} 未找到，请用新商品登记")
        st.session_state.pop('existing_barcode', None)
        st.rerun()
        return

    p = r['product']
    with section_card(f"📦 已有商品入库 · {p.get('name','')}", ""):
        with st.form("existing_form"):
            c1, c2 = st.columns(2)
            c1.markdown(f"""
            <div style="padding:12px;background:#f8fafc;border-radius:8px;">
                <b>{p.get('name','')}</b><br>
                分类: {p.get('category','')} &nbsp;|&nbsp; 库存: {p.get('stock',0)} 件<br>
                售价: ¥{p.get('sale_price',0):.2f}
            </div>
            """, unsafe_allow_html=True)
            qty = c2.number_input("入库数量", 1, value=1)
            prod_date = c2.date_input("生产日期", datetime.now())
            shelf = c2.number_input("保质期（天）", 1, value=365)

            if st.form_submit_button("✅ 确认入库", type="primary", width='stretch'):
                result = service.add_stock_existing(barcode, qty, prod_date, shelf)
                if result['success']:
                    st.session_state.pop('existing_barcode', None)
                    toast_success(f"「{p['name']}」入库 {qty} 件")
                    st.rerun()
                else:
                    for err in result.get('errors', []):
                        error_message(err)

    if st.button("取消", key="cancel_existing"):
        st.session_state.pop('existing_barcode', None)
        st.rerun()
