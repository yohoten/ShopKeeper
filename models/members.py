"""
会员管理数据模型
"""
from typing import List, Dict, Optional
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_members() -> List[Dict]:
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute("SELECT * FROM members ORDER BY total_consumption DESC").fetchall()
    return [dict(row) for row in rows]


def get_member_by_id(member_id: int) -> Optional[Dict]:
    db = get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    return dict(row) if row else None


def search_members(keyword: str) -> List[Dict]:
    db = get_db()
    conn = db.get_connection()
    pattern = f"%{keyword}%"
    rows = conn.execute("""
        SELECT * FROM members
        WHERE name LIKE ? OR phone LIKE ?
        ORDER BY total_consumption DESC
    """, (pattern, pattern)).fetchall()
    return [dict(row) for row in rows]


def add_member(data: Dict) -> int:
    db = get_db()
    with db.transaction() as conn:
        cursor = conn.execute("""
            INSERT INTO members (name, phone, level, points, total_consumption, discount, remark)
            VALUES (?, ?, ?, 0, 0, ?, ?)
        """, (
            data.get('name', ''),
            data.get('phone', None),
            data.get('level', '普通会员'),
            float(data.get('discount', 1.0)),
            data.get('remark', '')
        ))
        new_id = cursor.lastrowid
    logger.info(f"新增会员: {data.get('name','')} (ID={new_id})")
    return new_id


def update_member(member_id: int, data: Dict) -> bool:
    allowed = {'name', 'phone', 'level', 'points', 'discount', 'remark'}
    fields = []
    vals = []
    for k, v in data.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            vals.append(v)
    if not fields:
        return False
    vals.append(member_id)
    db = get_db()
    with db.transaction() as conn:
        conn.execute(f"UPDATE members SET {', '.join(fields)} WHERE id = ?", vals)
    logger.info(f"更新会员 ID={member_id}")
    return True


def add_points(member_id: int, points: int) -> bool:
    db = get_db()
    with db.transaction() as conn:
        conn.execute("UPDATE members SET points = points + ? WHERE id = ?", (points, member_id))
    return True


def deduct_points(member_id: int, points: int) -> bool:
    db = get_db()
    with db.transaction() as conn:
        cur = conn.execute("SELECT points FROM members WHERE id = ?", (member_id,)).fetchone()
        if not cur or cur['points'] < points:
            return False
        conn.execute("UPDATE members SET points = points - ? WHERE id = ?", (points, member_id))
    return True


def add_consumption(member_id: int, amount: float) -> bool:
    """累加消费金额"""
    db = get_db()
    with db.transaction() as conn:
        conn.execute(
            "UPDATE members SET total_consumption = total_consumption + ? WHERE id = ?",
            (amount, member_id)
        )
    return True


def get_member_count() -> int:
    db = get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM members").fetchone()
    return row['cnt'] if row else 0
