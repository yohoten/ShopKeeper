"""
库存盘点服务
"""
from typing import List, Dict
from datetime import datetime
from models.stock_count import (
    add_stock_count_record, confirm_stock_count,
    get_stock_counts, get_pending_count_items
)
from models.product import get_all_products, get_product_by_id
from utils.logger import get_logger

logger = get_logger(__name__)


class StockCountService:
    """库存盘点服务"""

    @staticmethod
    def get_all_products_for_count() -> List[Dict]:
        """获取所有商品用于盘点"""
        return get_all_products()

    @staticmethod
    def create_count(product_id: int, actual_stock: int, reason: str = "",
                     operator: str = "") -> Dict:
        """创建盘点记录"""
        product = get_product_by_id(product_id)
        if not product:
            return {'success': False, 'count_id': None, 'message': '商品不存在'}

        book_stock = product['stock']
        diff = actual_stock - book_stock

        data = {
            'product_id': product_id,
            'barcode': product.get('barcode', ''),
            'name': product['name'],
            'book_stock': book_stock,
            'actual_stock': actual_stock,
            'diff_stock': diff,
            'unit_cost': product.get('purchase_price', 0),
            'diff_amount': diff * product.get('purchase_price', 0),
            'reason': reason,
            'operator': operator
        }
        try:
            count_id = add_stock_count_record(data)
            return {'success': True, 'count_id': count_id, 'message': '盘点记录已创建'}
        except Exception as e:
            return {'success': False, 'count_id': None, 'message': str(e)}

    @staticmethod
    def confirm(count_id: int, actual_stock: int = None) -> bool:
        """确认盘点"""
        return confirm_stock_count(count_id, actual_stock)

    @staticmethod
    def get_records(start_date: str = None, end_date: str = None,
                    status: str = None) -> List[Dict]:
        return get_stock_counts(start_date, end_date, status)

    @staticmethod
    def get_pending() -> List[Dict]:
        return get_pending_count_items()

    @staticmethod
    def get_stats() -> Dict:
        """盘点统计"""
        all_records = get_stock_counts()
        pending = [r for r in all_records if r.get('status') == '待确认']
        confirmed = [r for r in all_records if r.get('status') == '已确认']
        total_diff_amount = sum(r.get('diff_amount', 0) for r in confirmed)
        return {
            'total': len(all_records),
            'pending': len(pending),
            'confirmed': len(confirmed),
            'total_diff_amount': total_diff_amount
        }
