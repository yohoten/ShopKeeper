"""
销售页面模块 v2 — 精美卡片式购物车
"""
import streamlit as st
import pandas as pd
from services.sale_service import SaleService
from ui.components import page_header, barcode_input, section_card, empty_state
from ui.components import error_message, toast_success, focus_barcode
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("🛒 商品销售", "扫描条码添加至购物车 · 一键结算")

    if 'cart' not in st.session_state:
        st.session_state.cart = {}
    if 'sale_barcode_input' not in st.session_state:
        st.session_state.sale_barcode_input = ""

    def on_scan():
        barcode = st.session_state.sale_barcode_input.strip()
        if not barcode:
            return
        product = SaleService.scan_barcode(barcode)
        if not product:
            error_message(f"未找到条码 [{barcode}] 对应的商品")
            st.session_state.sale_barcode_input = ""
            return

        stock = product['stock']
        cart_qty = st.session_state.cart.get(barcode, {}).get('quantity', 0)

        if cart_qty + 1 > stock:
            error_message(f"库存不足！{product['name']} 仅剩 {stock} 件")
            st.session_state.sale_barcode_input = ""
            return

        st.session_state.cart[barcode] = {'quantity': cart_qty + 1, 'info': product}
        st.session_state.sale_barcode_input = ""
        focus_barcode("sale_barcode_input")  # 连续扫码无需点击输入框
        st.rerun()

    # 扫码区域（卡片式）
    with section_card("📷 扫描商品", ""):
        barcode_input(
            "请扫描商品条码",
            key="sale_barcode_input",
            on_change=on_scan
        )

    # 购物车
    if not st.session_state.cart:
        empty_state("购物车为空", icon="🛒", suggestion="扫描条码开始添加商品")
        return

    # 购物车汇总卡片
    cart = st.session_state.cart
    total_amt = 0
    total_items = 0
    cart_data = []

    for barcode, item in cart.items():
        p = item['info']
        qty = item['quantity']
        price = float(p.get('sale_price') or 0)
        subtotal = price * qty
        total_amt += subtotal
        total_items += qty
        cart_data.append([p.get('name', ''), barcode, price, qty, subtotal, p.get('stock', 0)])

    df_cart = pd.DataFrame(cart_data, columns=['商品', '条码', '单价', '数量', '小计', '库存'])
    
    st.markdown("---")
    st.markdown("##### 🛍️ 购物清单")
    st.dataframe(
        df_cart, width='stretch', hide_index=True,
        column_config={
            '单价': st.column_config.NumberColumn(format="¥%.2f"),
            '小计': st.column_config.NumberColumn(format="¥%.2f"),
        }
    )

    # 合计栏
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                background:linear-gradient(135deg,#4361ee,#3f37c9);color:#fff;
                border-radius:12px;padding:16px 24px;margin:12px 0;">
        <div>
            <div style="font-size:0.8rem;opacity:0.8;">{len(cart)} 种 · {total_items} 件</div>
            <div style="font-size:1.6rem;font-weight:700;">¥{total_amt:,.2f}</div>
        </div>
        <div style="display:flex;gap:8px;">
    """, unsafe_allow_html=True)

    col_clear, col_submit = st.columns([1, 1.5])
    with col_clear:
        if st.button("🧹 清空", width='stretch', type="secondary"):
            st.session_state.cart = {}
            st.rerun()
    with col_submit:
        if st.button("✅ 完成结算", width='stretch', type="primary"):
            _do_checkout()

    st.markdown("</div></div>", unsafe_allow_html=True)

    # 管理区域
    with st.expander("📝 修改数量 / 删除"):
        for barcode in list(cart.keys()):
            item = cart[barcode]
            p = item['info']
            c1, c2, c3, c4 = st.columns([3, 1.5, 1, 1])
            c1.markdown(f"**{p.get('name','')}**")
            new_qty = c2.number_input("数量", 0, int(p.get('stock', 999)),
                                      int(item['quantity']), key=f"q_{barcode}")
            c3.caption(f"库存: {p.get('stock',0)}")
            if c4.button("🗑️", key=f"rm_{barcode}"):
                del cart[barcode]
                st.rerun()
            if new_qty != item['quantity']:
                if new_qty == 0:
                    del cart[barcode]
                else:
                    cart[barcode]['quantity'] = new_qty
                st.rerun()


def _do_checkout():
    if not st.session_state.cart:
        error_message("购物车为空")
        return
    result = SaleService().checkout(st.session_state.cart)
    if result['success']:
        st.session_state.cart = {}
        st.balloons()
        toast_success(f"结算成功！共 {result['records_count']} 种商品")
        st.rerun()
    else:
        for err in result.get('errors', []):
            error_message(err)
