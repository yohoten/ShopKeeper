"""
SQLite 数据库连接管理
提供单例模式的连接池和事务上下文管理器
"""
import sqlite3
import threading
from contextlib import contextmanager
from config import DB_PATH


class DatabaseManager:
    """数据库管理器（线程安全单例）"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._local = threading.local()
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.connection = conn
        return self._local.connection

    def close(self):
        """关闭当前线程的连接"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    @contextmanager
    def transaction(self):
        """事务上下文管理器，自动提交或回滚"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# 全局数据库管理器实例
_db_manager = DatabaseManager()


def get_db() -> DatabaseManager:
    """获取数据库管理器实例"""
    return _db_manager


@contextmanager
def get_conn():
    """便捷的数据库连接上下文管理器"""
    db = get_db()
    conn = db.get_connection()
    try:
        yield conn
    finally:
        pass  # 连接复用，不关闭


@contextmanager
def get_transaction():
    """便捷的事务上下文管理器"""
    db = get_db()
    with db.transaction() as conn:
        yield conn
