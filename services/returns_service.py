"""
退货管理服务
"""
from typing import List, Dict, Optional
from datetime import datetime
from models.returns import add_return_record, get_returns, get_return_summary
from models.transaction import get_sales
from utils.logger import get_logger

logger = get_logger(__name__)


class ReturnsService:
    """退货管理服务"""

    @staticmethod
    def get_sales_for_return(keyword: str = "") -> List[Dict]:
        """获取可退货的销售记录"""
        from models.transaction import get_sales
        sales = get_sales()
        if keyword:
            pattern = keyword.lower()
            sales = [s for s in sales if pattern in str(s.get('name','')).lower()
                     or pattern in str(s.get('barcode',''))]
        return sales[:100]

    @staticmethod
    def process_return(data: Dict) -> Dict:
        """
        处理退货
        
        Args:
            data: {original_sale_id, barcode, name, quantity, return_price,
                   refund_amount, reason, operator}
        Returns:
            {'success': bool, 'return_id': int|None, 'message': str}
        """
        qty = int(data.get('quantity', 0))
        if qty <= 0:
            return {'success': False, 'return_id': None, 'message': '退货数量必须大于0'}
        
        try:
            return_id = add_return_record(data)
            return {'success': True, 'return_id': return_id, 'message': '退货成功'}
        except Exception as e:
            logger.error(f"退货处理失败: {e}")
            return {'success': False, 'return_id': None, 'message': f'退货失败: {str(e)}'}

    @staticmethod
    def get_returns_list(start_date: str = None, end_date: str = None) -> List[Dict]:
        return get_returns(start_date, end_date)

    @staticmethod
    def get_summary(start_date: str, end_date: str) -> Dict:
        return get_return_summary(start_date, end_date)
