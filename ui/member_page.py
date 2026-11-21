"""
会员管理页面 v2
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, section_card, toast_success, error_message
from services.member_service import MemberService
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("👤 会员管理", "注册 · 积分 · 等级 · 统计")
    svc = MemberService()
    tab1, tab2, tab3 = st.tabs(["📋 会员列表", "➕ 新增会员", "📊 统计"])
    with tab1: _list(svc)
    with tab2: _add(svc)
    with tab3: _stats(svc)


def _list(svc):
    kw = st.text_input("🔍 搜索", key="mem_s", placeholder="姓名或手机号...")
    members = svc.search(kw)
    if not members:
        from ui.components import empty_state
        empty_state("暂无会员", icon="👤", suggestion="去「新增会员」标签页添加")
        return
    df = pd.DataFrame(members)
    rename = {'id': 'ID', 'name': '姓名', 'phone': '手机', 'level': '等级',
              'points': '积分', 'total_consumption': '消费', 'discount': '折扣'}
    df = df.rename(columns=rename)
    st.caption(f"共 {len(members)} 位")
    st.dataframe(df[['ID', '姓名', '手机', '等级', '积分', '消费', '折扣']],
                 width='stretch',
                 column_config={'消费': st.column_config.NumberColumn(format="¥%.2f")})

    st.markdown("---")
    with section_card("✏️ 编辑会员", ""):
        sel = st.selectbox("选择", [m['id'] for m in members],
                           format_func=lambda x: next(m['name'] for m in members if m['id'] == x))
        m = svc.get_by_id(sel)
        if m:
            with st.form("edit_mem"):
                c1, c2 = st.columns(2)
                n = c1.text_input("姓名", m['name'])
                ph = c1.text_input("手机", m.get('phone', ''))
                lv = c1.selectbox("等级", ["普通会员", "银卡会员", "金卡会员", "钻石会员"],
                                  index=max(0, ["普通会员", "银卡会员", "金卡会员", "钻石会员"].index(m.get('level', '普通会员')) if m.get('level') in ["普通会员", "银卡会员", "金卡会员", "钻石会员"] else 0))
                pts = c2.number_input("积分", 0, int(m.get('points', 0)))
                disc = c2.number_input("折扣", 0.0, 1.0, float(m.get('discount', 1.0)), format="%.2f")
                rm = c2.text_area("备注", m.get('remark', ''))
                if st.form_submit_button("💾 保存", type="primary", width='stretch'):
                    svc.update(sel, {'name': n, 'phone': ph, 'level': lv, 'points': pts, 'discount': disc, 'remark': rm})
                    toast_success("✅ 已更新")
                    st.rerun()


def _add(svc):
    with section_card("新增会员", ""):
        with st.form("add_mem"):
            c1, c2 = st.columns(2)
            n = c1.text_input("姓名（必填）")
            ph = c1.text_input("手机号")
            lv = c1.selectbox("等级", ["普通会员", "银卡会员", "金卡会员", "钻石会员"])
            disc = c2.number_input("折扣", 0.0, 1.0, 1.0, format="%.2f")
            rm = c2.text_area("备注")
            if st.form_submit_button("✅ 添加", type="primary", width='stretch'):
                r = svc.add({'name': n, 'phone': ph, 'level': lv, 'discount': disc, 'remark': rm})
                if r['success']: toast_success(f"✅ {r['message']}"); st.rerun()
                else: error_message(r['message'])


def _stats(svc):
    s = svc.get_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("会员数", s['total'])
    c2.metric("总积分", f"{s['total_points']:,}")
    c3.metric("总消费", f"¥{s['total_consumption']:,.2f}")
    c4.metric("人均消费", f"¥{s['total_consumption']/max(s['total'],1):,.2f}")
    if s['levels']:
        df = pd.DataFrame([{'等级': k, '人数': v} for k, v in s['levels'].items()])
        st.bar_chart(df.set_index('等级'), horizontal=True)
