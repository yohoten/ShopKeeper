"""
退货管理数据模型
"""
from typing import List, Dict, Optional
from datetime import datetime
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


def add_return_record(data: Dict) -> int:
    """
    添加退货记录，同时回滚库存
    
    Args:
        data: {original_sale_id, barcode, name, quantity, return_price, 
               refund_amount, reason, operator}
    Returns:
        退货记录 ID
    """
    db = get_db()
    with db.transaction() as conn:
        cursor = conn.execute("""
            INSERT INTO returns
                (return_time, original_sale_id, barcode, name, quantity,
                 return_price, refund_amount, reason, operator)
            VALUES (datetime('now','localtime'), ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('original_sale_id'),
            data.get('barcode', ''),
            data.get('name', ''),
            int(data.get('quantity', 0)),
            float(data.get('return_price', 0)),
            float(data.get('refund_amount', 0)),
            data.get('reason', ''),
            data.get('operator', '')
        ))
        new_id = cursor.lastrowid

        # 回滚库存：商品库存 + 退货数量
        barcode = data.get('barcode', '')
        qty = int(data.get('quantity', 0))
        if barcode and qty > 0:
            conn.execute(
                "UPDATE products SET stock = stock + ?, updated_at = datetime('now','localtime') WHERE barcode = ?",
                (qty, barcode)
            )

    logger.info(f"退货记录 ID={new_id}, 商品={data.get('name','')}, 数量={qty}, 退款={data.get('refund_amount',0)}")
    return new_id


def get_returns(start_date: str = None, end_date: str = None) -> List[Dict]:
    """获取退货记录"""
    db = get_db()
    conn = db.get_connection()
    query = "SELECT * FROM returns WHERE 1=1"
    params = []
    if start_date:
        query += " AND date(return_time) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date(return_time) <= ?"
        params.append(end_date)
    query += " ORDER BY return_time DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_return_summary(start_date: str, end_date: str) -> Dict:
    """获取退货汇总"""
    db = get_db()
    conn = db.get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0) as total_qty,
               COALESCE(SUM(refund_amount), 0) as total_refund,
               COUNT(*) as return_count
        FROM returns
        WHERE date(return_time) >= ? AND date(return_time) <= ?
    """, (start_date, end_date)).fetchone()
    return dict(row) if row else {'total_qty': 0, 'total_refund': 0, 'return_count': 0}
