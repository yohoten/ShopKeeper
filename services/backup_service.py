"""
数据备份与恢复服务
"""
import os
import shutil
from datetime import datetime
from typing import Dict, List
from config import DB_PATH, BACKUP_DIR, BASE_DIR
from models.backup import log_backup, get_backup_logs, get_last_backup_time
from utils.logger import get_logger

logger = get_logger(__name__)


class BackupService:
    """备份恢复服务"""

    @staticmethod
    def create_backup() -> Dict:
        """
        创建数据库备份
        
        Returns:
            {'success': bool, 'file_path': str, 'message': str}
        """
        os.makedirs(BACKUP_DIR, exist_ok=True)

        if not os.path.exists(DB_PATH):
            return {'success': False, 'file_path': '', 'message': '数据库文件不存在'}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        try:
            # 先执行 checkpoint 确保 WAL 数据写入主文件
            from database.connection import get_db
            db = get_db()
            conn = db.get_connection()
            conn.execute("PRAGMA wal_checkpoint(FULL)")

            # 复制文件
            shutil.copy2(DB_PATH, backup_path)
            file_size = os.path.getsize(backup_path)

            # 记录备份日志
            log_backup(backup_path, file_size)

            logger.info(f"备份成功: {backup_path} ({file_size} bytes)")
            return {
                'success': True,
                'file_path': backup_path,
                'file_size': file_size,
                'message': f'备份成功，文件大小: {file_size/1024:.1f} KB'
            }
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return {'success': False, 'file_path': '', 'message': str(e)}

    @staticmethod
    def list_backups(limit: int = 20) -> List[Dict]:
        """列出备份文件"""
        logs = get_backup_logs(limit)
        backups = []
        for log_entry in logs:
            path = log_entry.get('file_path', '')
            if os.path.exists(path):
                log_entry['file_size_str'] = f"{os.path.getsize(path)/1024:.1f} KB"
            else:
                log_entry['file_size_str'] = '文件已删除'
            backups.append(log_entry)
        return backups

    @staticmethod
    def get_last_backup() -> str:
        """获取最近备份时间"""
        return get_last_backup_time() or '从未备份'

    @staticmethod
    def clean_old_backups(keep_count: int = 30):
        """清理旧备份，保留最近 N 个"""
        logs = get_backup_logs(100)
        if len(logs) <= keep_count:
            return
        to_delete = logs[keep_count:]
        for log_entry in to_delete:
            path = log_entry.get('file_path', '')
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"删除旧备份: {path}")
                except Exception as e:
                    logger.warning(f"删除旧备份失败: {path} - {e}")
