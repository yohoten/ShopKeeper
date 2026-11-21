"""
供应商管理数据模型
"""
from typing import List, Dict, Optional
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_suppliers() -> List[Dict]:
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def get_supplier_by_id(supplier_id: int) -> Optional[Dict]:
    db = get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
    return dict(row) if row else None


def search_suppliers(keyword: str) -> List[Dict]:
    db = get_db()
    conn = db.get_connection()
    pattern = f"%{keyword}%"
    rows = conn.execute("""
        SELECT * FROM suppliers
        WHERE name LIKE ? OR contact_person LIKE ? OR phone LIKE ?
        ORDER BY name
    """, (pattern, pattern, pattern)).fetchall()
    return [dict(row) for row in rows]


def add_supplier(data: Dict) -> int:
    db = get_db()
    with db.transaction() as conn:
        cursor = conn.execute("""
            INSERT INTO suppliers (name, contact_person, phone, address, remark)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get('name', ''),
            data.get('contact_person', ''),
            data.get('phone', ''),
            data.get('address', ''),
            data.get('remark', '')
        ))
        new_id = cursor.lastrowid
    logger.info(f"新增供应商: {data.get('name','')} (ID={new_id})")
    return new_id


def update_supplier(supplier_id: int, data: Dict) -> bool:
    allowed = {'name', 'contact_person', 'phone', 'address', 'remark'}
    fields = []
    vals = []
    for k, v in data.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            vals.append(v)
    if not fields:
        return False
    vals.append(supplier_id)
    db = get_db()
    with db.transaction() as conn:
        conn.execute(f"UPDATE suppliers SET {', '.join(fields)} WHERE id = ?", vals)
    logger.info(f"更新供应商 ID={supplier_id}")
    return True


def delete_supplier(supplier_id: int) -> bool:
    db = get_db()
    with db.transaction() as conn:
        conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    logger.info(f"删除供应商 ID={supplier_id}")
    return True


def get_supplier_count() -> int:
    db = get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM suppliers").fetchone()
    return row['cnt'] if row else 0
