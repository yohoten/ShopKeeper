"""
库存管理服务
封装库存相关的业务逻辑，包括库存预警检查
"""
from typing import List, Dict, Optional
from models.product import (
    get_all_products, get_product_by_barcode, get_product_by_id,
    search_products, get_low_stock_products, add_product, update_product,
    update_stock, get_categories
)
from models.transaction import get_sales_summary
from utils.validators import validate_product_data, validate_barcode
from utils.logger import get_logger
from config import DEFAULT_MIN_STOCK

logger = get_logger(__name__)


class InventoryService:
    """库存管理服务"""

    @staticmethod
    def get_all() -> List[Dict]:
        """获取所有商品"""
        return get_all_products()

    @staticmethod
    def search(keyword: str = "") -> List[Dict]:
        """搜索商品"""
        return search_products(keyword.strip()) if keyword.strip() else get_all_products()

    @staticmethod
    def get_by_barcode(barcode: str) -> Optional[Dict]:
        """根据条码获取商品"""
        return get_product_by_barcode(barcode)

    @staticmethod
    def get_by_id(product_id: int) -> Optional[Dict]:
        """根据 ID 获取商品"""
        return get_product_by_id(product_id)

    @staticmethod
    def add_new(data: Dict) -> Dict:
        """
        添加新商品（带验证）

        Args:
            data: 商品数据

        Returns:
            {'success': bool, 'product_id': int|None, 'errors': [str]}

        Raises:
            ValueError: 验证失败时抛出
        """
        errors = validate_product_data(data)
        if errors:
            return {'success': False, 'product_id': None, 'errors': errors}

        # 检查条码是否已存在
        barcode = data.get('barcode', '')
        if barcode:
            existing = get_product_by_barcode(barcode)
            if existing:
                return {
                    'success': False,
                    'product_id': None,
                    'errors': [f"条码 {barcode} 已存在，对应商品: {existing['name']}"]
                }

        product_id = add_product(data)
        logger.info(f"新增商品成功: {data.get('name', '')} (ID={product_id})")
        return {'success': True, 'product_id': product_id, 'errors': []}

    @staticmethod
    def edit(product_id: int, data: Dict) -> Dict:
        """编辑商品信息"""
        success = update_product(product_id, data)
        if success:
            logger.info(f"编辑商品成功: ID={product_id}")
        return {'success': success}

    @staticmethod
    def add_stock(barcode: str, quantity: int) -> bool:
        """
        增加库存（入库）

        Args:
            barcode: 商品条码
            quantity: 增加数量

        Returns:
            是否成功
        """
        product = get_product_by_barcode(barcode)
        if not product:
            logger.warning(f"入库失败：条码 {barcode} 不存在")
            return False
        return update_stock(product['id'], quantity)

    @staticmethod
    def deduct_stock(barcode: str, quantity: int) -> bool:
        """
        扣减库存（销售）

        Args:
            barcode: 商品条码
            quantity: 扣减数量

        Returns:
            是否成功
        """
        product = get_product_by_barcode(barcode)
        if not product:
            logger.warning(f"扣库存失败：条码 {barcode} 不存在")
            return False

        if product['stock'] < quantity:
            logger.warning(f"扣库存失败：条码 {barcode} 库存不足 ({product['stock']} < {quantity})")
            return False

        return update_stock(product['id'], -quantity)

    @staticmethod
    def get_low_stock_products(threshold: int = None) -> List[Dict]:
        """获取低库存预警商品"""
        threshold = threshold or DEFAULT_MIN_STOCK
        return get_low_stock_products(threshold)

    @staticmethod
    def get_categories() -> List[str]:
        """获取分类列表"""
        return get_categories()

    @staticmethod
    def get_inventory_stats() -> Dict:
        """获取库存统计概览"""
        products = get_all_products()
        total_products = len(products)
        total_stock = sum(p['stock'] for p in products)
        low_stock = [p for p in products if p['stock'] <= (p.get('min_stock') or DEFAULT_MIN_STOCK)]
        total_value = sum(p['stock'] * p['purchase_price'] for p in products)
        categories = len(set(p['category'] for p in products))

        return {
            'total_products': total_products,
            'total_stock': total_stock,
            'low_stock_count': len(low_stock),
            'low_stock_items': low_stock[:20],  # 最多显示20个
            'total_value': total_value,
            'categories': categories
        }
