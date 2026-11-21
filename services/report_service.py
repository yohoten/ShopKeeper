"""
报表与分析服务
提供销售分析、趋势统计和报表生成
"""
from typing import List, Dict
from datetime import datetime, timedelta
from models.transaction import (
    get_sales, get_daily_sales, get_top_products, get_sales_summary
)
from models.product import get_all_products
from utils.logger import get_logger
from config import DEFAULT_DATE_RANGE_DAYS

logger = get_logger(__name__)


class ReportService:
    """报表服务"""

    @staticmethod
    def get_default_date_range() -> tuple:
        """获取默认日期范围（最近 N 天）"""
        end = datetime.now()
        start = end - timedelta(days=DEFAULT_DATE_RANGE_DAYS)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    @staticmethod
    def get_sales_summary(start_date: str, end_date: str) -> Dict:
        """获取销售汇总"""
        return get_sales_summary(start_date, end_date)

    @staticmethod
    def get_daily_trend(start_date: str, end_date: str) -> List[Dict]:
        """获取每日趋势数据"""
        return get_daily_sales(start_date, end_date)

    @staticmethod
    def get_top_products(start_date: str, end_date: str, limit: int = 10) -> List[Dict]:
        """获取热销商品排行"""
        return get_top_products(start_date, end_date, limit)

    @staticmethod
    def get_sales_detail(start_date: str, end_date: str) -> List[Dict]:
        """获取销售明细"""
        return get_sales(start_date, end_date)

    @staticmethod
    def get_inventory_stats() -> Dict:
        """获取库存统计"""
        from services.inventory_service import InventoryService
        return InventoryService.get_inventory_stats()

    @staticmethod
    def get_dashboard_data() -> Dict:
        """
        获取数据看板所需的所有汇总数据

        Returns:
            {
                'today_summary': {...},
                'month_summary': {...},
                'daily_trend': [...],
                'top_products': [...],
                'inventory_stats': {...}
            }
        """
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        return {
            'today_summary': get_sales_summary(today, today),
            'week_summary': get_sales_summary(week_start, today),
            'month_summary': get_sales_summary(month_start, today),
            'daily_trend': get_daily_sales(week_start, today),
            'top_products': get_top_products(week_start, today, 10),
            'inventory_stats': ReportService.get_inventory_stats()
        }
