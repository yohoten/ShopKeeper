"""
供应商管理服务
"""
from typing import List, Dict, Optional
from models.suppliers import (
    get_all_suppliers, get_supplier_by_id, search_suppliers,
    add_supplier, update_supplier, delete_supplier, get_supplier_count
)
from utils.logger import get_logger

logger = get_logger(__name__)


class SupplierService:
    """供应商管理服务"""

    @staticmethod
    def get_all() -> List[Dict]:
        return get_all_suppliers()

    @staticmethod
    def search(keyword: str = "") -> List[Dict]:
        if keyword.strip():
            return search_suppliers(keyword.strip())
        return get_all_suppliers()

    @staticmethod
    def get_by_id(supplier_id: int) -> Optional[Dict]:
        return get_supplier_by_id(supplier_id)

    @staticmethod
    def add(data: Dict) -> Dict:
        if not data.get('name', '').strip():
            return {'success': False, 'supplier_id': None, 'message': '供应商名称不能为空'}
        try:
            sid = add_supplier(data)
            return {'success': True, 'supplier_id': sid, 'message': '添加成功'}
        except Exception as e:
            return {'success': False, 'supplier_id': None, 'message': str(e)}

    @staticmethod
    def update(supplier_id: int, data: Dict) -> bool:
        return update_supplier(supplier_id, data)

    @staticmethod
    def delete(supplier_id: int) -> bool:
        return delete_supplier(supplier_id)

    @staticmethod
    def get_stats() -> Dict:
        suppliers = get_all_suppliers()
        return {
            'total': len(suppliers)
        }
