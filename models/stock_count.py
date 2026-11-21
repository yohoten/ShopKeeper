"""
库存盘点数据模型
"""
from typing import List, Dict
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


def add_stock_count_record(data: Dict) -> int:
    """
    添加盘点记录
    
    Args:
        data: {product_id, barcode, name, book_stock, actual_stock, 
               diff_stock, unit_cost, diff_amount, reason, operator}
    """
    db = get_db()
    with db.transaction() as conn:
        cursor = conn.execute("""
            INSERT INTO stock_counts
                (count_time, product_id, barcode, name, book_stock, actual_stock,
                 diff_stock, unit_cost, diff_amount, reason, status, operator)
            VALUES (datetime('now','localtime'), ?, ?, ?, ?, ?, ?, ?, ?, ?, '待确认', ?)
        """, (
            data.get('product_id'),
            data.get('barcode', ''),
            data.get('name', ''),
            int(data.get('book_stock', 0)),
            int(data.get('actual_stock', 0)),
            int(data.get('diff_stock', 0)),
            float(data.get('unit_cost', 0)),
            float(data.get('diff_amount', 0)),
            data.get('reason', ''),
            data.get('operator', '')
        ))
        new_id = cursor.lastrowid
    logger.info(f"新增盘点记录 ID={new_id}, 商品={data.get('name','')}, 差异={data.get('diff_stock',0)}")
    return new_id


def confirm_stock_count(count_id: int, actual_stock: int = None) -> bool:
    """确认盘点并调整库存"""
    db = get_db()
    with db.transaction() as conn:
        record = conn.execute("SELECT * FROM stock_counts WHERE id = ?", (count_id,)).fetchone()
        if not record:
            return False
        
        final_stock = actual_stock if actual_stock is not None else record['actual_stock']
        diff = final_stock - record['book_stock']
        
        # 更新盘点记录
        conn.execute("""
            UPDATE stock_counts SET actual_stock=?, diff_stock=?, diff_amount=?,
                status='已确认' WHERE id=?
        """, (final_stock, diff, diff * record['unit_cost'], count_id))
        
        # 调整实际库存
        if record['product_id']:
            conn.execute(
                "UPDATE products SET stock = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (final_stock, record['product_id'])
            )
    
    logger.info(f"盘点确认 ID={count_id}, 调整库存为 {final_stock}")
    return True


def get_stock_counts(start_date: str = None, end_date: str = None,
                     status: str = None) -> List[Dict]:
    """获取盘点记录"""
    db = get_db()
    conn = db.get_connection()
    query = "SELECT * FROM stock_counts WHERE 1=1"
    params = []
    if start_date:
        query += " AND date(count_time) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date(count_time) <= ?"
        params.append(end_date)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY count_time DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_pending_count_items() -> List[Dict]:
    """获取待确认的盘点项"""
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM stock_counts WHERE status = '待确认' ORDER BY count_time DESC"
    ).fetchall()
    return [dict(row) for row in rows]
