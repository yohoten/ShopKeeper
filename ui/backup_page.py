"""
数据备份页面 v2
"""
import os
import streamlit as st
import pandas as pd
from ui.components import page_header, section_card, error_message, toast_success
from services.backup_service import BackupService
from config import BACKUP_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


def show():
    page_header("💾 数据备份与恢复", "数据安全保障 · 手动/自动备份 · 一键恢复")
    svc = BackupService()
    tab1, tab2 = st.tabs(["💾 备份管理", "📂 历史记录"])
    with tab1: _backup(svc)
    with tab2: _history(svc)


def _backup(svc):
    last = svc.get_last_backup()
    st.info(f"📅 最近备份: {last}")

    with section_card("创建设置", ""):
        keep = st.number_input("保留备份数", 5, 100, 30)

        c1, c2 = st.columns(2)
        if c1.button("📀 立即创建备份", type="primary", width='stretch'):
            with st.spinner("备份中..."):
                r = svc.create_backup()
                if r['success']:
                    svc.clean_old_backups(keep)
                    toast_success(r['message'])
                    st.rerun()
                else:
                    error_message(r['message'])
        if c2.button("📁 打开备份目录", width='stretch'):
            os.makedirs(BACKUP_DIR, exist_ok=True)
            os.startfile(BACKUP_DIR)

    st.markdown("---")
    st.warning("⚠️ **恢复操作将覆盖当前数据库且不可撤销**，请先创建备份。")
    backups = svc.list_backups(50)
    valid = [b for b in backups if os.path.exists(b.get('file_path', ''))]
    if valid:
        opts = {f"{b['backup_time']} - {b.get('file_size_str','')}": b['file_path'] for b in valid}
        sel = st.selectbox("选择备份", list(opts.keys()))
        # 二次确认：勾选后才允许恢复，避免误点直接覆盖生产数据
        confirmed = st.checkbox("我已备份当前数据，确认覆盖恢复", value=False,
                                key="restore_confirm")
        if st.button("🔄 恢复此备份", type="secondary", width='stretch',
                     disabled=not confirmed):
            import shutil
            from config import DB_PATH
            from database.connection import get_db
            db = get_db()
            try:
                # WAL 模式下先 checkpoint，避免未落盘事务在覆盖时丢失
                db.get_connection().execute("PRAGMA wal_checkpoint(FULL)")
            except Exception as exc:
                logger.warning(f"WAL checkpoint 失败: {exc}")
            db.close()
            shutil.copy2(opts[sel], DB_PATH)
            st.session_state.restore_confirm = False
            toast_success("恢复成功！请重新打开应用以加载新数据")
            st.rerun()
    else:
        from ui.components import empty_state
        empty_state("暂无备份文件", icon="💾")


def _history(svc):
    backups = svc.list_backups(50)
    if not backups:
        from ui.components import empty_state
        empty_state("暂无备份记录", icon="📂")
        return
    df = pd.DataFrame(backups)
    rename = {'backup_time': '时间', 'file_path': '文件', 'file_size_str': '大小', 'status': '状态'}
    df = df.rename(columns=rename)
    if '文件' in df.columns:
        df['文件'] = df['文件'].apply(lambda x: os.path.basename(x) if x else '')
    st.dataframe(df[['时间', '文件', '大小', '状态']], width='stretch')
    if st.button("🧹 清理旧备份（保留30个）", width='stretch'):
        svc.clean_old_backups(30)
        toast_success("清理完成")
        st.rerun()
