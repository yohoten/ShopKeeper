"""
进货（入库）业务服务
封装入库流程的业务逻辑
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from models.product import get_product_by_barcode, add_product
from models.transaction import add_purchase_record, get_purchases, update_purchase_sold_out, delete_purchase
from services.inventory_service import InventoryService
from utils.helpers import generate_pinyin, calculate_expiry
from utils.validators import validate_product_data
from utils.logger import get_logger
from config import DEFAULT_CATEGORIES

logger = get_logger(__name__)


class PurchaseService:
    """进货服务"""

    @staticmethod
    def scan_barcode(barcode: str) -> Dict:
        """
        扫描条码，判断是已有商品还是新商品

        Args:
            barcode: 条码

        Returns:
            {'is_new': bool, 'product': Dict|None}
        """
        if not barcode:
            return {'is_new': True, 'product': None}

        product = get_product_by_barcode(barcode.strip())
        if product:
            return {'is_new': False, 'product': product}
        else:
            return {'is_new': True, 'product': None}

    @staticmethod
    def add_new_product(data: Dict, purchase_quantity: int,
                        production_date, shelf_life: int) -> Dict:
        """
        添加新商品并入库

        Args:
            data: 商品信息 {name, category, purchase_price, sale_price, ...}
            purchase_quantity: 入库数量
            production_date: 生产日期
            shelf_life: 保质期（天）

        Returns:
            {'success': bool, 'product_id': int|None, 'errors': [str]}
        """
        # 验证商品数据
        errors = validate_product_data(data)
        if errors:
            return {'success': False, 'product_id': None, 'errors': errors}

        # 验证数量
        if purchase_quantity <= 0:
            return {'success': False, 'product_id': None, 'errors': ['入库数量必须大于 0']}

        # 计算到期时间
        expiry = calculate_expiry(production_date, shelf_life) if production_date and shelf_life else ""

        # 生成拼音码
        pinyin = generate_pinyin(data.get('name', ''))

        from database.connection import get_db
        db = get_db()

        with db.transaction() as conn:
            # 1. 添加商品
            cursor = conn.execute("""
                INSERT INTO products
                    (name, category, barcode, stock, purchase_price, sale_price,
                     pinyin_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """, (
                data.get('name', ''),
                data.get('category', '未分类'),
                data.get('barcode', None),
                purchase_quantity,
                float(data.get('purchase_price', 0)),
                float(data.get('sale_price', 0)),
                pinyin
            ))
            product_id = cursor.lastrowid

            # 2. 添加入库记录
            conn.execute("""
                INSERT INTO purchases
                    (product_id, barcode, name, shelf_life,
                     production_date, expiry_date, 入库_time,
                     quantity, is_sold_out)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'), ?, 0)
            """, (
                product_id,
                data.get('barcode', None),
                data.get('name', ''),
                shelf_life,
                production_date.strftime("%Y-%m-%d") if production_date else None,
                expiry,
                purchase_quantity
            ))

        logger.info(f"新增商品并入库: {data.get('name', '')} x{purchase_quantity}")
        return {'success': True, 'product_id': product_id, 'errors': []}

    @staticmethod
    def add_stock_existing(barcode: str, quantity: int,
                           production_date, shelf_life: int) -> Dict:
        """
        已有商品追加入库

        Args:
            barcode: 商品条码
            quantity: 入库数量
            production_date: 生产日期
            shelf_life: 保质期（天）

        Returns:
            {'success': bool, 'errors': [str]}
        """
        product = get_product_by_barcode(barcode)
        if not product:
            return {'success': False, 'errors': [f"条码 {barcode} 对应的商品不存在"]}

        if quantity <= 0:
            return {'success': False, 'errors': ['入库数量必须大于 0']}

        expiry = calculate_expiry(production_date, shelf_life) if production_date and shelf_life else ""

        from database.connection import get_db
        db = get_db()

        with db.transaction() as conn:
            # 1. 增加库存
            conn.execute(
                "UPDATE products SET stock = stock + ?, updated_at = datetime('now','localtime') WHERE barcode = ?",
                (quantity, barcode)
            )

            # 2. 添加入库记录
            conn.execute("""
                INSERT INTO purchases
                    (product_id, barcode, name, shelf_life,
                     production_date, expiry_date, 入库_time,
                     quantity, is_sold_out)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'), ?, 0)
            """, (
                product['id'],
                barcode,
                product['name'],
                shelf_life,
                production_date.strftime("%Y-%m-%d") if production_date else None,
                expiry,
                quantity
            ))

        logger.info(f"已有商品入库: {product['name']} x{quantity}")
        return {'success': True, 'errors': []}

    @staticmethod
    def get_purchase_list(start_date: str = None, end_date: str = None,
                          show_sold_out: bool = False,
                          shelf_life_filter: str = "全部") -> List[Dict]:
        """
        获取进货列表（带筛选）

        Args:
            start_date: 开始日期
            end_date: 结束日期
            show_sold_out: 是否显示已售空
            shelf_life_filter: 保质期筛选 ("全部", "少于3个月", "少于1个月")

        Returns:
            进货记录列表
        """
        is_sold_out = None if show_sold_out else False
        records = get_purchases(start_date, end_date, is_sold_out)

        # 保质期筛选（在应用层过滤）
        if shelf_life_filter == "少于3个月":
            cutoff = datetime.now() + timedelta(days=90)
            records = [r for r in records if r.get('expiry_date') and
                       datetime.strptime(r['expiry_date'], "%Y-%m-%d") <= cutoff]
        elif shelf_life_filter == "少于1个月":
            cutoff = datetime.now() + timedelta(days=30)
            records = [r for r in records if r.get('expiry_date') and
                       datetime.strptime(r['expiry_date'], "%Y-%m-%d") <= cutoff]

        return records

    @staticmethod
    def toggle_sold_out(purchase_id: int) -> bool:
        """切换售空状态"""
        from models.transaction import get_purchases
        db = __import__('database.connection', fromlist=['get_db']).get_db()
        conn = db.get_connection()
        row = conn.execute(
            "SELECT is_sold_out FROM purchases WHERE id = ?", (purchase_id,)
        ).fetchone()
        if not row:
            return False
        return update_purchase_sold_out(purchase_id, not row['is_sold_out'])

    @staticmethod
    def delete(purchase_id: int) -> bool:
        """删除进货记录"""
        return delete_purchase(purchase_id)
