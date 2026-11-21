"""
批量操作页面 v2
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, section_card, toast_success, error_message
from models.product import get_all_products
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("📦 批量操作", "批量入库 · 调价 · CSV导入")
    tab1, tab2, tab3 = st.tabs(["📥 批量入库", "💰 批量调价", "📄 CSV导入"])
    with tab1: _batch_in()
    with tab2: _batch_price()
    with tab3: _batch_import()


def _batch_in():
    products = get_all_products()
    if not products:
        from ui.components import empty_state; empty_state("暂无商品", "📦"); return

    df = pd.DataFrame(products)[['name', 'barcode', 'stock']]
    df.columns = ['商品', '条码', '库存']
    df['入库数'] = 0
    edited = st.data_editor(df, width='stretch',
                            column_config={'入库数': st.column_config.NumberColumn(min_value=0, default=0)},
                            hide_index=True, key="bi")
    if st.button("✅ 批量入库", type="primary", width='stretch'):
        from database.connection import get_db
        db = get_db(); cnt = 0
        with db.transaction() as conn:
            for _, r in edited.iterrows():
                q = int(r['入库数'])
                if q <= 0: continue
                conn.execute("UPDATE products SET stock=stock+? WHERE barcode=?", (q, r['条码']))
                conn.execute("INSERT INTO purchases (barcode,name,quantity,入库_time) VALUES (?,?,?,datetime('now'))",
                             (r['条码'], r['商品'], q))
                cnt += 1
        toast_success(f"✅ {cnt} 种商品入库完成"); st.rerun()


def _batch_price():
    products = get_all_products()
    if not products:
        from ui.components import empty_state; empty_state("暂无商品", "📦"); return

    cats = list(set(p.get('category', '') for p in products))
    meth = st.radio("方式", ["按分类", "按商品"], horizontal=True)

    if meth == "按分类":
        sc = st.multiselect("选择分类", cats)
        if not sc:
            return
        target = [p for p in products if p['category'] in sc]
    else:
        df = pd.DataFrame(products)[['name', 'sale_price']]
        df.columns = ['商品', '售价']; df['选'] = False
        ed = st.data_editor(df, hide_index=True, key="bps",
                            column_config={'选': st.column_config.CheckboxColumn()})
        target = [p for p in products if p['name'] in ed[ed['选']]['商品'].tolist()]
        if not target:
            return

    st.caption(f"影响 {len(target)} 种商品")
    field_sel = st.selectbox("调价字段", ["销售价", "进货价", "批发价", "会员价"])
    atype = st.radio("方式", ["固定值", "百分比(%)", "增减值(¥)"], horizontal=True)
    val = st.number_input("调整值", value=0.0, format="%.2f")
    field_map = {"销售价": "sale_price", "进货价": "purchase_price", "批发价": "wholesale_price", "会员价": "member_price"}
    field = field_map[field_sel]

    if st.button("💰 执行调价", type="primary", width='stretch'):
        from database.connection import get_db
        db = get_db(); cnt = 0
        with db.transaction() as conn:
            for p in target:
                cur = float(p.get(field, 0))
                new = val if atype == "固定值" else (cur * (1 + val / 100) if atype == "百分比(%)" else cur + val)
                conn.execute(f"UPDATE products SET {field}=?,updated_at=datetime('now') WHERE id=?",
                             (max(0, round(new, 2)), p['id']))
                cnt += 1
        toast_success(f"✅ {cnt} 种商品调价完成"); st.rerun()


def _batch_import():
    with section_card("上传文件批量导入", ""):
        f = st.file_uploader("CSV 或 Excel", type=['csv', 'xlsx'],
                             help="必填列: name, sale_price。可选: barcode, category, purchase_price, stock, min_stock")
        if f:
            try:
                df = pd.read_csv(f, dtype={'barcode': str}) if f.name.endswith('.csv') else pd.read_excel(f, dtype={'barcode': str})
                st.dataframe(df.head(8), width='stretch')
                st.caption(f"共 {len(df)} 行")
                missing = [c for c in ['name', 'sale_price'] if c not in df.columns]
                if missing: error_message(f"缺少列: {missing}"); return
                if st.button("📥 确认导入", type="primary", width='stretch'):
                    from database.connection import get_db
                    from utils.helpers import generate_pinyin
                    db = get_db(); cnt = 0
                    with db.transaction() as conn:
                        for _, r in df.iterrows():
                            n = str(r.get('name', '')).strip()
                            if not n: continue
                            bc = str(r.get('barcode', '')).strip() if pd.notna(r.get('barcode')) else ''
                            conn.execute("INSERT INTO products (name,category,barcode,stock,purchase_price,sale_price,min_stock,pinyin_code,created_at) VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
                                         (n, str(r.get('category', '未分类')), bc or None, int(r.get('stock', 0)),
                                          float(r.get('purchase_price', 0)), float(r.get('sale_price', 0)),
                                          int(r.get('min_stock', 10)), generate_pinyin(n)))
                            cnt += 1
                    toast_success(f"✅ 导入 {cnt} 种商品"); st.rerun()
            except Exception as e:
                error_message(f"读取失败: {e}")
