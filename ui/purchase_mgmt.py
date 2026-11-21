"""
进货管理页面 v2 — 卡片式列表
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from services.purchase_service import PurchaseService
from ui.components import page_header, date_range_picker, section_card
from ui.components import error_message, toast_success
from config import SHELF_LIFE_WARNING_DAYS, SHELF_LIFE_CRITICAL_DAYS
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("📋 进货管理", "审查进货历史 · 保质期监控 · 售空管理")

    c1, c2, c3 = st.columns(3)
    with c1:
        sd, ed = date_range_picker(start_key="pm_s", end_key="pm_e", default_days=90)
    with c2:
        shelf_f = st.selectbox("保质期筛选", ["全部", "少于3个月", "少于1个月"])
    with c3:
        sold = st.checkbox("显示已售空")

    service = PurchaseService()
    try:
        records = service.get_purchase_list(
            sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"), sold, shelf_f)
    except Exception as e:
        error_message(f"加载失败: {e}")
        return

    if not records:
        from ui.components import empty_state
        empty_state("无进货记录", icon="📭", suggestion="调整筛选条件试试")
        return

    df = pd.DataFrame(records)
    rename = {'name': '商品', 'barcode': '条码', 'quantity': '数量',
              '入库_time': '入库时间', 'expiry_date': '到期时间', 'is_sold_out': '售空'}
    df = df.rename(columns=rename)

    # 剩余天数
    def rem_days(v):
        if not v: return None
        try: return max(0, (datetime.strptime(str(v)[:10], "%Y-%m-%d") - datetime.now()).days)
        except: return None
    df['剩余天'] = df['到期时间'].apply(rem_days)

    # 高亮
    def hl(row):
        d = row.get('剩余天', None)
        if d is not None and d <= SHELF_LIFE_CRITICAL_DAYS:
            return ['background:#ffe0e6;font-weight:bold'] * len(row)
        if d is not None and d <= SHELF_LIFE_WARNING_DAYS:
            return ['background:#fff8e1'] * len(row)
        return [''] * len(row)

    df['售空'] = df['售空'].apply(lambda x: '✅ 是' if x == 1 else '否')
    st.caption(f"共 {len(records)} 条 · 累计入库 {df['数量'].sum()} 件")
    
    cols = [c for c in ['商品', '条码', '数量', '入库时间', '到期时间', '剩余天', '售空'] if c in df.columns]
    st.dataframe(df[cols].style.apply(hl, axis=1), width='stretch')

    # 操作
    st.markdown("---")
    with section_card("🔧 进货单操作", ""):
        if 'id' in df.columns:
            sel = st.selectbox("选择进货单", df['id'].tolist(), format_func=lambda x: f"ID {x}")
            cur = df[df['id'] == sel].iloc[0]
            # 注意：原始列名 is_sold_out 已在上面 rename 为「售空」，
            # 用旧键取值会永远得到 0，导致按钮文案与动作相反。
            is_sold = str(cur.get('售空', '否')).startswith('✅')
            c1, c2 = st.columns(2)
            if c1.button("恢复未售空" if is_sold else "标记售空",
                          width='stretch'):
                service.toggle_sold_out(sel)
                toast_success("状态已更新")
                st.rerun()
            if c2.button("🗑️ 删除", type="secondary", width='stretch'):
                service.delete(sel)
                toast_success("已删除")
                st.rerun()

    st.info(f"🟡 黄色 = 少于 {SHELF_LIFE_WARNING_DAYS} 天 ｜ 🔴 红色 = 少于 "
            f"{SHELF_LIFE_CRITICAL_DAYS} 天")
