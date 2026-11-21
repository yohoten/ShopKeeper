"""
退货管理页面 v2 — 卡片式布局
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, date_range_picker, section_card
from ui.components import error_message, toast_success
from services.returns_service import ReturnsService
from services.inventory_service import InventoryService
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("🔄 退货管理", "扫码退货 · 库存自动回滚 · 历史追踪")

    tab1, tab2 = st.tabs(["➕ 新增退货", "📋 退货历史"])
    with tab1:
        _return_form()
    with tab2:
        _return_history()


def _return_form():
    with section_card("退货录入", ""):
        bc = st.text_input("📷 扫描条码", key="ret_bc", placeholder="扫描或输入条码...")
        product = None
        if bc:
            product = InventoryService().get_by_barcode(bc.strip())
            if product:
                st.success(f"「{product['name']}」库存: {product['stock']}")
            else:
                error_message("未找到该商品")

        if product:
            st.caption(f"当前库存 {product['stock']} 件；退货数量请不超过实际退回件数。")

        with st.form("ret_form"):
            c1, c2 = st.columns(2)
            sid = c1.number_input("原始销售单 ID（可选）", 0)
            qty = c1.number_input("退货数量", 1, max(1, int(product['stock']) if product else 10000))
            rp = c1.number_input("退款单价", 0.0, format="%.2f",
                                  value=float(product['sale_price']) if product else 0.0)
            name = c2.text_input("商品名称", value=product['name'] if product else "")
            br = c2.text_input("条码", value=product['barcode'] if product else bc)
            reason = c2.selectbox("原因", ["质量问题", "客户不喜欢", "错发漏发", "过期", "其他"])
            confirmed = c2.checkbox("我已核对退货信息", value=False)
            refund = qty * rp
            st.caption(f"预计退款: ¥{refund:.2f} · 该操作将回滚库存，请确认无误")

            if st.form_submit_button("✅ 确认退货", type="primary",
                                     width='stretch', disabled=not confirmed):
                if not name or not br:
                    error_message("商品名称与条码不能为空")
                    return
                result = ReturnsService().process_return({
                    'original_sale_id': sid or None, 'barcode': br,
                    'name': name, 'quantity': qty, 'return_price': rp,
                    'refund_amount': refund, 'reason': reason, 'operator': 'admin'
                })
                if result['success']:
                    # 清空条码，防止 rerun 后重复提交造成二次入库/退款
                    st.session_state.ret_bc = ""
                    toast_success(result['message'])
                    st.rerun()
                else:
                    error_message(result['message'])


def _return_history():
    sd, ed = date_range_picker(start_key="ret_s", end_key="ret_e", default_days=30)
    svc = ReturnsService()
    records = svc.get_returns_list(sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))
    sm = svc.get_summary(sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))

    c1, c2, c3 = st.columns(3)
    c1.metric("笔数", sm['return_count'])
    c2.metric("数量", f"{sm['total_qty']} 件")
    c3.metric("退款", f"¥{sm['total_refund']:.2f}")

    if not records:
        from ui.components import empty_state
        empty_state("暂无退货记录", icon="📭")
        return
    df = pd.DataFrame(records)
    rename = {'return_time': '时间', 'name': '商品', 'quantity': '数量',
              'refund_amount': '退款', 'reason': '原因'}
    df = df.rename(columns=rename)
    st.dataframe(df[['时间', '商品', '数量', '退款', '原因']], width='stretch')
