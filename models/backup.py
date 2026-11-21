"""
数据备份与恢复模型
"""
from typing import List, Dict, Optional
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


def log_backup(file_path: str, file_size: int, status: str = '成功', remark: str = ''):
    """记录备份日志"""
    db = get_db()
    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO backup_logs (backup_time, file_path, file_size, status, remark)
            VALUES (datetime('now','localtime'), ?, ?, ?, ?)
        """, (file_path, file_size, status, remark))
        conn.execute(
            "UPDATE settings SET value = datetime('now','localtime') WHERE key = 'last_backup_time'"
        )
    logger.info(f"备份日志记录: {file_path} ({file_size} bytes)")


def get_backup_logs(limit: int = 20) -> List[Dict]:
    """获取备份历史"""
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM backup_logs ORDER BY backup_time DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_last_backup_time() -> Optional[str]:
    """获取最近一次备份时间"""
    db = get_db()
    conn = db.get_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'last_backup_time'"
    ).fetchone()
    return row['value'] if row else None
