"""
商品数据模型
提供商品相关的数据库操作
"""
from typing import Optional, List, Dict
from database.connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_products() -> List[Dict]:
    """获取所有商品"""
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT * FROM products ORDER BY name
    """).fetchall()
    return [dict(row) for row in rows]


def get_product_by_barcode(barcode: str) -> Optional[Dict]:
    """根据条码获取商品"""
    if not barcode:
        return None
    db = get_db()
    conn = db.get_connection()
    row = conn.execute(
        "SELECT * FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()
    return dict(row) if row else None


def get_product_by_id(product_id: int) -> Optional[Dict]:
    """根据 ID 获取商品"""
    db = get_db()
    conn = db.get_connection()
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    return dict(row) if row else None


def search_products(keyword: str) -> List[Dict]:
    """
    搜索商品（按名称、条码、拼音码）

    Args:
        keyword: 搜索关键词

    Returns:
        匹配的商品列表
    """
    if not keyword:
        return get_all_products()

    pattern = f"%{keyword}%"
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT * FROM products
        WHERE name LIKE ?
           OR barcode LIKE ?
           OR pinyin_code LIKE ?
           OR category LIKE ?
        ORDER BY name
    """, (pattern, pattern, pattern, pattern)).fetchall()
    return [dict(row) for row in rows]


def get_low_stock_products(threshold: int = 10) -> List[Dict]:
    """获取库存低于阈值的商品"""
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT * FROM products
        WHERE stock <= ?
        ORDER BY stock ASC
    """, (threshold,)).fetchall()
    return [dict(row) for row in rows]


def add_product(data: Dict) -> int:
    """
    添加新商品

    Args:
        data: 商品数据字典

    Returns:
        新商品的 ID
    """
    from utils.helpers import generate_pinyin

    pinyin = data.get('pinyin_code', '') or generate_pinyin(data.get('name', ''))

    db = get_db()
    with db.transaction() as conn:
        cursor = conn.execute("""
            INSERT INTO products
                (name, category, barcode, stock, purchase_price, sale_price,
                 wholesale_price, member_price, member_discount,
                 points_product, production_date, shelf_life, pinyin_code,
                 min_stock, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    datetime('now','localtime'))
        """, (
            data.get('name', ''),
            data.get('category', '未分类'),
            data.get('barcode', None) or None,
            int(data.get('stock', 0)),
            float(data.get('purchase_price', 0)),
            float(data.get('sale_price', 0)),
            float(data.get('wholesale_price', 0)),
            float(data.get('member_price', 0)),
            float(data.get('member_discount', 0)),
            int(data.get('points_product', 0)),
            data.get('production_date', None),
            int(data.get('shelf_life', 0)),
            pinyin,
            int(data.get('min_stock', 10))
        ))
        new_id = cursor.lastrowid

    logger.info(f"新增商品: {data.get('name', '')} (ID={new_id})")
    return new_id


def update_product(product_id: int, data: Dict) -> bool:
    """
    更新商品信息

    Args:
        product_id: 商品 ID
        data: 要更新的字段字典

    Returns:
        是否更新成功
    """
    allowed_fields = {
        'name', 'category', 'barcode', 'purchase_price', 'sale_price',
        'wholesale_price', 'member_price', 'member_discount',
        'points_product', 'min_stock', 'production_date', 'shelf_life'
    }

    update_fields = []
    values = []
    for key, value in data.items():
        if key in allowed_fields:
            update_fields.append(f"{key} = ?")
            values.append(value)

    if not update_fields:
        return False

    update_fields.append("updated_at = datetime('now','localtime')")
    values.append(product_id)

    db = get_db()
    with db.transaction() as conn:
        conn.execute(
            f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?",
            values
        )
    logger.info(f"更新商品 ID={product_id}: 更新字段 {list(data.keys())}")
    return True


def update_stock(product_id: int, delta: int) -> bool:
    """
    更新库存（正数增加，负数减少）

    Args:
        product_id: 商品 ID
        delta: 库存变化量

    Returns:
        是否更新成功
    """
    db = get_db()
    with db.transaction() as conn:
        # 先获取当前库存
        current = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not current:
            logger.warning(f"更新库存失败：商品 ID={product_id} 不存在")
            return False

        new_stock = current['stock'] + delta
        if new_stock < 0:
            logger.warning(f"更新库存失败：商品 ID={product_id} 库存不足 (当前={current['stock']}, 变化={delta})")
            return False

        conn.execute(
            "UPDATE products SET stock = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (new_stock, product_id)
        )
    logger.info(f"更新库存: 商品ID={product_id}, 变化={delta:+d}, 新库存={new_stock}")
    return True


def get_categories() -> List[str]:
    """获取所有商品分类"""
    db = get_db()
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category"
    ).fetchall()
    categories = [row['category'] for row in rows]
    # 确保默认分类存在
    for c in ["零食", "饮料", "日用品"]:
        if c not in categories:
            categories.append(c)
    return categories


def get_product_count() -> int:
    """获取商品总数"""
    db = get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()
    return row['cnt'] if row else 0
