"""
辅助函数模块
"""
from xpinyin import Pinyin

# 拼音转换器实例（复用）
_pinyin_converter = Pinyin()


def generate_pinyin(name: str) -> str:
    """
    生成商品名称的拼音码（首字母缩写）

    Args:
        name: 商品名称（中文）

    Returns:
        拼音首字母缩写，最多10个字符
    """
    if not name or not name.strip():
        return ""
    try:
        return _pinyin_converter.get_initials(name, '')[:10].lower()
    except Exception:
        return ""


def format_currency(value: float) -> str:
    """格式化金额"""
    return f"¥{value:,.2f}"


def format_date(date_str: str, fmt: str = "%Y-%m-%d") -> str:
    """格式化日期字符串"""
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.strptime(str(date_str)[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime(fmt)
    except ValueError:
        try:
            from datetime import datetime
            dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            return dt.strftime(fmt)
        except ValueError:
            return str(date_str)[:10]


def calculate_expiry(production_date, shelf_life_days: int):
    """
    计算到期时间

    Args:
        production_date: 生产日期（date 或 str）
        shelf_life_days: 保质期（天）

    Returns:
        到期日期字符串
    """
    from datetime import datetime, timedelta
    if isinstance(production_date, str):
        try:
            prod = datetime.strptime(production_date, "%Y-%m-%d")
        except ValueError:
            return ""
    else:
        prod = datetime.combine(production_date, datetime.min.time())
    expiry = prod + timedelta(days=int(shelf_life_days))
    return expiry.strftime("%Y-%m-%d")
