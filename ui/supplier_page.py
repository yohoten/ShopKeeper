"""
供应商管理页面 v2
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, section_card, toast_success, error_message
from services.supplier_service import SupplierService
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("🏭 供应商管理", "管理供应商信息")
    svc = SupplierService()
    tab1, tab2 = st.tabs(["📋 列表", "➕ 新增"])
    with tab1: _list(svc)
    with tab2: _add(svc)


def _list(svc):
    kw = st.text_input("🔍 搜索", key="sup_s", placeholder="名称/联系人...")
    suppliers = svc.search(kw)
    if not suppliers:
        from ui.components import empty_state
        empty_state("暂无供应商", icon="🏭")
        return
    df = pd.DataFrame(suppliers)
    rename = {'id': 'ID', 'name': '名称', 'contact_person': '联系人',
              'phone': '电话', 'address': '地址'}
    df = df.rename(columns=rename)
    st.caption(f"共 {len(suppliers)} 家")
    st.dataframe(df[['ID', '名称', '联系人', '电话', '地址']], width='stretch')

    with section_card("✏️ 编辑", ""):
        sel = st.selectbox("选择", [s['id'] for s in suppliers],
                           format_func=lambda x: next(s['name'] for s in suppliers if s['id'] == x))
        sup = svc.get_by_id(sel)
        if sup:
            with st.form("edit_sup"):
                c1, c2 = st.columns(2)
                n = c1.text_input("名称", sup['name'])
                cp = c1.text_input("联系人", sup.get('contact_person', ''))
                ph = c1.text_input("电话", sup.get('phone', ''))
                addr = c2.text_area("地址", sup.get('address', ''))
                rm = c2.text_area("备注", sup.get('remark', ''))
                c1b, c2b = st.columns(2)
                if c1b.form_submit_button("💾 保存", type="primary", width='stretch'):
                    svc.update(sel, {'name': n, 'contact_person': cp, 'phone': ph, 'address': addr, 'remark': rm})
                    toast_success("✅ 已更新"); st.rerun()
                confirm_del = c2b.checkbox("确认删除", key=f"sup_del_{sel}")
                if c2b.form_submit_button("🗑️ 删除", type="secondary",
                                          width='stretch', disabled=not confirm_del):
                    svc.delete(sel)
                    toast_success("已删除")
                    st.rerun()


def _add(svc):
    with section_card("新增供应商", ""):
        with st.form("add_sup"):
            c1, c2 = st.columns(2)
            n = c1.text_input("名称（必填）")
            cp = c1.text_input("联系人")
            ph = c1.text_input("电话")
            addr = c2.text_area("地址")
            rm = c2.text_area("备注")
            if st.form_submit_button("✅ 添加", type="primary", width='stretch'):
                r = svc.add({'name': n, 'contact_person': cp, 'phone': ph, 'address': addr, 'remark': rm})
                if r['success']: toast_success(f"✅ {r['message']}"); st.rerun()
                else: error_message(r['message'])
