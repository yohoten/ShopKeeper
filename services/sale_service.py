"""
销售业务服务
封装销售流程的业务逻辑
"""
from typing import List, Dict, Optional
from datetime import datetime
from models.product import get_product_by_barcode
from models.transaction import add_sale_records
from services.inventory_service import InventoryService
from utils.logger import get_logger

logger = get_logger(__name__)


def _to_float(value, default: float = 0.0) -> float:
    """安全转浮点数：兼容 None / 空串 / 中文数字。"""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_product(product: Optional[Dict]) -> Optional[Dict]:
    """把商品信息归一化为数据库列名。

    历史版本购物车曾使用 Excel 中文表头（名称（必填）/销售价（必填）等）作键，
    迁移到 SQLite 后这些键全部取不到值，导致售价 0、商品名空、利润失真。
    这里统一兜底，兼容旧数据形态。
    """
    if not product:
        return None
    result = dict(product)
    result['name'] = result.get('name') or result.get('名称（必填）') or ''
    for canonical, legacy in (('sale_price', '销售价（必填）'),
                              ('purchase_price', '进货价（必填）')):
        result[canonical] = _to_float(
            result.get(canonical, result.get(legacy, 0)))
    result['stock'] = int(result.get('stock') or 0)
    return result


class SaleService:
    """销售服务"""

    @staticmethod
    def scan_barcode(barcode: str) -> Optional[Dict]:
        """
        扫描商品条码

        Args:
            barcode: 商品条码

        Returns:
            商品信息字典，None 表示未找到
        """
        if not barcode:
            return None
        product = get_product_by_barcode(barcode.strip())
        return normalize_product(product)

    @staticmethod
    def check_stock(barcode: str, requested_qty: int) -> tuple:
        """
        检查库存是否充足

        Returns:
            (is_available: bool, current_stock: int, message: str)
        """
        product = get_product_by_barcode(barcode)
        if not product:
            return False, 0, "未找到商品信息"

        stock = product['stock']
        if requested_qty > stock:
            return False, stock, f"库存不足！当前库存：{stock}，需求：{requested_qty}"

        return True, stock, ""

    @staticmethod
    def checkout(cart_items: Dict[str, Dict]) -> Dict:
        """
        结算购物车

        Args:
            cart_items: 购物车数据 {barcode: {quantity, info}}

        Returns:
            {'success': bool, 'records_count': int, 'errors': [str]}
        """
        errors = []
        sales_records = []
        sale_time = datetime.now()

        # 第一步：验证所有商品库存
        for barcode, item in cart_items.items():
            product_info = item.get('info', {})
            quantity = item.get('quantity', 0)

            available, stock, msg = SaleService.check_stock(barcode, quantity)
            if not available:
                errors.append(f"{product_info.get('name') or '未知商品'}: {msg}")
                continue

        if errors:
            return {'success': False, 'records_count': 0, 'errors': errors}

        # 第二步：生成销售记录
        for barcode, item in cart_items.items():
            product_info = item.get('info', {})
            quantity = item.get('quantity', 0)
            product_info = normalize_product(product_info)
            sale_price = product_info['sale_price']
            purchase_price = product_info['purchase_price']

            record = {
                'barcode': barcode,
                'name': product_info['name'],
                'quantity': quantity,
                'purchase_price': purchase_price,
                'sale_price': sale_price,
                'revenue': sale_price * quantity,
                'profit': (sale_price - purchase_price) * quantity
            }
            sales_records.append(record)

        # 第三步：在事务中执行（库存扣减 + 记录保存）
        from database.connection import get_db
        db = get_db()

        with db.transaction() as conn:
            # 保存销售记录
            for record in sales_records:
                conn.execute("""
                    INSERT INTO sales
                        (sale_time, barcode, name, quantity,
                         purchase_price, sale_price, revenue, profit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sale_time.strftime("%Y-%m-%d %H:%M:%S"),
                    record['barcode'],
                    record['name'],
                    record['quantity'],
                    record['purchase_price'],
                    record['sale_price'],
                    record['revenue'],
                    record['profit']
                ))

            # 扣减库存
            for barcode, item in cart_items.items():
                conn.execute(
                    "UPDATE products SET stock = stock - ?, updated_at = datetime('now','localtime') WHERE barcode = ?",
                    (item['quantity'], barcode)
                )

        count = len(sales_records)
        logger.info(f"结算成功：共 {count} 种商品，{sum(r['quantity'] for r in sales_records)} 件")
        return {'success': True, 'records_count': count, 'errors': []}
