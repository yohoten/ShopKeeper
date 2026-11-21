"""
交易记录数据模型（销售 + 进货）
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


# ========== 销售记录 ==========

def add_sale_records(records: List[Dict]) -> int:
    """
    批量添加销售记录

    Args:
        records: 销售记录列表，每条包含 barcode, name, quantity,
                 purchase_price, sale_price, revenue, profit

    Returns:
        添加的记录数
    """
    db = get_db()
    count = 0
    with db.transaction() as conn:
        sale_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for record in records:
            conn.execute("""
                INSERT INTO sales
                    (sale_time, barcode, name, quantity,
                     purchase_price, sale_price, revenue, profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sale_time,
                record.get('barcode', ''),
                record.get('name', ''),
                int(record.get('quantity', 0)),
                float(record.get('purchase_price', 0)),
                float(record.get('sale_price', 0)),
                float(record.get('revenue', 0)),
                float(record.get('profit', 0))
            ))
            count += 1
    logger.info(f"批量添加销售记录 {count} 条")
    return count


def get_sales(start_date: str = None, end_date: str = None) -> List[Dict]:
    """
    获取销售记录（按时间筛选）

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        销售记录列表
    """
    db = get_db()
    conn = db.get_connection()

    if start_date and end_date:
        rows = conn.execute("""
            SELECT * FROM sales
            WHERE date(sale_time) >= ? AND date(sale_time) <= ?
            ORDER BY sale_time DESC
        """, (start_date, end_date)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM sales ORDER BY sale_time DESC
        """).fetchall()

    return [dict(row) for row in rows]


def get_daily_sales(start_date: str, end_date: str) -> List[Dict]:
    """
    获取每日汇总销售数据

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        每日汇总列表
    """
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT date(sale_time) as sale_date,
               SUM(revenue) as total_revenue,
               SUM(profit) as total_profit,
               SUM(quantity) as total_quantity,
               COUNT(DISTINCT barcode) as product_count
        FROM sales
        WHERE date(sale_time) >= ? AND date(sale_time) <= ?
        GROUP BY date(sale_time)
        ORDER BY sale_date
    """, (start_date, end_date)).fetchall()
    return [dict(row) for row in rows]


def get_top_products(start_date: str, end_date: str, limit: int = 10) -> List[Dict]:
    """
    获取热销商品排行

    Args:
        start_date: 开始日期
        end_date: 结束日期
        limit: 返回条数

    Returns:
        热销商品列表
    """
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT barcode, name,
               SUM(quantity) as total_quantity,
               SUM(revenue) as total_revenue,
               SUM(profit) as total_profit
        FROM sales
        WHERE date(sale_time) >= ? AND date(sale_time) <= ?
        GROUP BY barcode, name
        ORDER BY total_quantity DESC
        LIMIT ?
    """, (start_date, end_date, limit)).fetchall()
    return [dict(row) for row in rows]


def get_sales_summary(start_date: str, end_date: str) -> Dict:
    """获取销售汇总数据"""
    db = get_db()
    conn = db.get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(revenue), 0) as total_revenue,
               COALESCE(SUM(profit), 0) as total_profit,
               COALESCE(SUM(quantity), 0) as total_quantity,
               COUNT(DISTINCT barcode) as product_count,
               COUNT(*) as transaction_count
        FROM sales
        WHERE date(sale_time) >= ? AND date(sale_time) <= ?
    """, (start_date, end_date)).fetchone()
    return dict(row) if row else {
        'total_revenue': 0, 'total_profit': 0, 'total_quantity': 0,
        'product_count': 0, 'transaction_count': 0
    }


# ========== 进货记录 ==========

def add_purchase_record(data: Dict) -> int:
    """
    添加进货记录

    Args:
        data: 进货数据字典

    Returns:
        进货记录 ID
    """
    db = get_db()
    with db.transaction() as conn:
        cursor = conn.execute("""
            INSERT INTO purchases
                (product_id, barcode, name, shelf_life,
                 production_date, expiry_date, 入库_time,
                 quantity, is_sold_out)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'), ?, 0)
        """, (
            data.get('product_id'),
            data.get('barcode', ''),
            data.get('name', ''),
            int(data.get('shelf_life', 0)),
            data.get('production_date'),
            data.get('expiry_date'),
            int(data.get('quantity', 0))
        ))
        new_id = cursor.lastrowid
    logger.info(f"添加进货记录 ID={new_id}, 商品={data.get('name', '')}, 数量={data.get('quantity', 0)}")
    return new_id


def get_purchases(start_date: str = None, end_date: str = None,
                  is_sold_out: Optional[bool] = None) -> List[Dict]:
    """
    获取进货记录

    Args:
        start_date: 开始日期
        end_date: 结束日期
        is_sold_out: 是否售空筛选

    Returns:
        进货记录列表
    """
    db = get_db()
    conn = db.get_connection()

    query = "SELECT * FROM purchases WHERE 1=1"
    params = []

    if start_date:
        query += " AND date(入库_time) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date(入库_time) <= ?"
        params.append(end_date)
    if is_sold_out is not None:
        query += " AND is_sold_out = ?"
        params.append(1 if is_sold_out else 0)

    query += " ORDER BY 入库_time DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def update_purchase_sold_out(purchase_id: int, is_sold_out: bool) -> bool:
    """更新进货单售空状态"""
    db = get_db()
    with db.transaction() as conn:
        conn.execute(
            "UPDATE purchases SET is_sold_out = ? WHERE id = ?",
            (1 if is_sold_out else 0, purchase_id)
        )
    logger.info(f"更新进货单 ID={purchase_id} 售空状态={'是' if is_sold_out else '否'}")
    return True


def delete_purchase(purchase_id: int) -> bool:
    """删除进货记录"""
    db = get_db()
    with db.transaction() as conn:
        conn.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
    logger.info(f"删除进货单 ID={purchase_id}")
    return True
