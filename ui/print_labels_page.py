"""
打印标签页面 v2
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, section_card
from services.inventory_service import InventoryService
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("🏷️ 打印标签", "商品价签 · 批量打印 · 条码标签")
    svc = InventoryService()
    tab1, tab2 = st.tabs(["🏷️ 单件价签", "📋 批量标签"])
    with tab1: _single(svc)
    with tab2: _batch(svc)


def _single(svc):
    kw = st.text_input("🔍 搜索", key="ls_s", placeholder="名称或条码...")
    products = svc.search(kw)
    if not products:
        from ui.components import empty_state
        empty_state("未找到", icon="🔍")
        return

    sel = st.selectbox("选择商品", [p['id'] for p in products],
                        format_func=lambda x: next(f"{p['name']} ¥{p.get('sale_price',0):.2f}" for p in products if p['id'] == x))
    p = svc.get_by_id(sel)
    if not p: return

    html = _label_html(p)
    st.markdown("##### 预览")
    st.components.v1.html(html, height=200, scrolling=False)

    c1, c2 = st.columns(2)
    c1.download_button("⬇️ 下载 HTML", html, f"label_{p.get('barcode','')}.html", "text/html", width='stretch')
    if c2.button("🖨️ 打印", width='stretch'):
        st.components.v1.html(f"<script>var w=window.open('','','width=400,height=300');w.document.write(`{html}`);w.print();</script>")


def _batch(svc):
    products = svc.get_all()
    if not products:
        from ui.components import empty_state
        empty_state("暂无商品", icon="📦")
        return

    df = pd.DataFrame(products)[['name', 'barcode', 'sale_price']]
    df.columns = ['商品', '条码', '售价']; df['选'] = False
    ed = st.data_editor(df, hide_index=True, key="bl",
                        column_config={'选': st.column_config.CheckboxColumn()})
    sel = ed[ed['选']]
    if sel.empty:
        return
    st.caption(f"已选 {len(sel)} 种")

    cols = st.number_input("每行标签数", 1, 5, 3)

    if st.button("🖨️ 生成并打印", type="primary", width='stretch'):
        labels = ""
        for i, (_, r) in enumerate(sel.iterrows()):
            p = svc.get_by_barcode(r['条码'])
            if p:
                labels += _label_html(p, True)
                if (i + 1) % cols == 0:
                    labels += '<div style="page-break-after:always;"></div>'
        batch = f'<html><head><meta charset="utf-8"><style>@media print{{@page{{margin:5mm}}}}.lc{{display:flex;flex-wrap:wrap;gap:4px}}</style></head><body><div class="lc">{labels}</div><script>window.print()</script></body></html>'
        st.download_button("⬇️ 下载批量", batch, "batch_labels.html", "text/html", width='stretch')


def _label_html(p, compact=False):
    n, pr, bc, mp = p.get('name', ''), p.get('sale_price', 0), p.get('barcode', ''), p.get('member_price', 0)
    member_html = f'<div style="font-size:9px;color:#666;">会员价 ¥{mp:.2f}</div>' if mp else ''
    member_html2 = f'<div style="color:#27ae60;">会员价 ¥{mp:.2f}</div>' if mp else ''
    if compact:
        return (
            '<div style="border:1px solid #ddd;padding:6px;margin:2px;width:200px;'
            'display:inline-block;text-align:center;font-size:11px;border-radius:6px;">'
            f'<b style="font-size:12px;">{n}</b>'
            f'<div style="font-size:18px;color:#e74c3c;font-weight:bold;">¥{pr:.2f}</div>'
            f'{member_html}'
            f'<div style="font-size:14px;font-family:monospace;letter-spacing:2px;margin-top:4px;">{bc}</div>'
            '</div>'
        )
    return (
        '<div style="border:2px solid #333;border-radius:10px;padding:16px;max-width:300px;'
        'margin:0 auto;text-align:center;font-family:sans-serif;">'
        f'<div style="font-size:16px;font-weight:bold;">{n}</div>'
        f'<div style="font-size:28px;color:#e74c3c;font-weight:bold;margin:10px 0;">¥{pr:.2f}</div>'
        f'{member_html2}'
        '<div style="border-top:1px dashed #ccc;margin-top:10px;padding-top:8px;font-size:12px;color:#999;">'
        f'{bc}</div>'
        f'<div style="font-size:16px;font-family:monospace;letter-spacing:3px;">{bc}</div>'
        '</div>'
    )
