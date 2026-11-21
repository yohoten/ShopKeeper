"""
会员管理服务
"""
from typing import List, Dict, Optional
from models.members import (
    get_all_members, get_member_by_id, search_members,
    add_member, update_member, add_points, deduct_points, add_consumption,
    get_member_count
)
from utils.logger import get_logger
from config import MEMBER_DEFAULT_POINTS, MEMBER_POINTS_PER_YUAN

logger = get_logger(__name__)


class MemberService:
    """会员管理服务"""

    @staticmethod
    def get_all() -> List[Dict]:
        return get_all_members()

    @staticmethod
    def search(keyword: str = "") -> List[Dict]:
        if keyword.strip():
            return search_members(keyword.strip())
        return get_all_members()

    @staticmethod
    def get_by_id(member_id: int) -> Optional[Dict]:
        return get_member_by_id(member_id)

    @staticmethod
    def add(data: Dict) -> Dict:
        """添加会员"""
        if not data.get('name', '').strip():
            return {'success': False, 'member_id': None, 'message': '会员姓名不能为空'}
        try:
            member_id = add_member(data)
            return {'success': True, 'member_id': member_id, 'message': '添加成功'}
        except Exception as e:
            logger.error(f"添加会员失败: {e}")
            return {'success': False, 'member_id': None, 'message': str(e)}

    @staticmethod
    def update(member_id: int, data: Dict) -> bool:
        return update_member(member_id, data)

    @staticmethod
    def record_consumption(member_id: int, amount: float):
        """记录消费并增加积分"""
        add_consumption(member_id, amount)
        points = int(amount * MEMBER_POINTS_PER_YUAN)
        add_points(member_id, points)

    @staticmethod
    def get_stats() -> Dict:
        """会员统计"""
        members = get_all_members()
        total = len(members)
        total_points = sum(m.get('points', 0) for m in members)
        total_consumption = sum(m.get('total_consumption', 0) for m in members)
        levels = {}
        for m in members:
            lv = m.get('level', '普通会员')
            levels[lv] = levels.get(lv, 0) + 1
        return {
            'total': total,
            'total_points': total_points,
            'total_consumption': total_consumption,
            'levels': levels
        }
