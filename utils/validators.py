"""
数据验证工具模块
"""
import re


def validate_barcode(barcode: str) -> bool:
    """
    验证条码格式（EAN-13/8 或自定义条码）
    允许空的条码（新商品可以无条码）
    """
    if not barcode:
        return True
    # 一般条码为 8-13 位数字
    return bool(re.match(r'^\d{8,13}$', barcode.strip()))


def validate_required(value, field_name: str) -> str:
    """验证必填字段不为空"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return f"{field_name} 为必填项"
    return ""


def validate_positive_number(value, field_name: str) -> str:
    """验证正数"""
    try:
        num = float(value)
        if num <= 0:
            return f"{field_name} 必须大于 0"
    except (TypeError, ValueError):
        return f"{field_name} 必须是有效数字"
    return ""


def validate_non_negative_int(value, field_name: str) -> str:
    """验证非负整数"""
    try:
        num = int(value)
        if num < 0:
            return f"{field_name} 不能为负数"
    except (TypeError, ValueError):
        return f"{field_name} 必须是有效整数"
    return ""


def validate_product_data(data: dict) -> list:
    """
    验证商品数据的完整性

    Args:
        data: 商品数据字典

    Returns:
        错误消息列表，为空表示验证通过
    """
    errors = []

    name_err = validate_required(data.get('name'), '商品名称')
    if name_err:
        errors.append(name_err)

    price_err = validate_positive_number(data.get('sale_price', 0), '销售价')
    if price_err:
        errors.append(price_err)

    purchase_err = validate_positive_number(data.get('purchase_price', 0), '进货价')
    if purchase_err:
        errors.append(purchase_err)

    barcode = data.get('barcode', '')
    if barcode and not validate_barcode(barcode):
        errors.append("条码格式不正确")

    return errors


def validate_purchase_data(data: dict) -> list:
    """验证进货数据"""
    errors = []
    qty_err = validate_positive_number(data.get('quantity', 0), '入库数量')
    if qty_err:
        errors.append(qty_err)
    return errors
