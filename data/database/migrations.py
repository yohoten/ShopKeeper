"""
数据库初始化和数据迁移模块
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from config import (
    DB_PATH, EXCEL_PRODUCT_PATH, EXCEL_SALES_PATH, EXCEL_PURCHASE_PATH,
    DEFAULT_CATEGORIES
)
from .connection import get_db
from utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '未分类',
    barcode TEXT UNIQUE,
    stock INTEGER DEFAULT 0,
    purchase_price REAL NOT NULL DEFAULT 0,
    sale_price REAL NOT NULL DEFAULT 0,
    wholesale_price REAL DEFAULT 0,
    member_price REAL DEFAULT 0,
    member_discount REAL DEFAULT 0,
    points_product INTEGER DEFAULT 0,
    production_date TEXT,
    shelf_life INTEGER DEFAULT 0,
    pinyin_code TEXT,
    supplier_id INTEGER,
    min_stock INTEGER DEFAULT 10,
    image_url TEXT,
    remark TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    supplier_id INTEGER,
    barcode TEXT,
    name TEXT,
    shelf_life INTEGER DEFAULT 0,
    production_date TEXT,
    expiry_date TEXT,
    入库_time TEXT DEFAULT (datetime('now','localtime')),
    quantity INTEGER NOT NULL,
    purchase_price REAL DEFAULT 0,
    is_sold_out INTEGER DEFAULT 0,
    remark TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_time TEXT DEFAULT (datetime('now','localtime')),
    member_id INTEGER,
    barcode TEXT,
    name TEXT,
    quantity INTEGER NOT NULL,
    purchase_price REAL,
    sale_price REAL,
    revenue REAL,
    profit REAL,
    FOREIGN KEY (member_id) REFERENCES members(id)
);

-- ===== Phase 2: 退货管理 =====
CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_time TEXT DEFAULT (datetime('now','localtime')),
    original_sale_id INTEGER,
    barcode TEXT,
    name TEXT,
    quantity INTEGER NOT NULL,
    return_price REAL DEFAULT 0,
    refund_amount REAL DEFAULT 0,
    reason TEXT,
    operator TEXT,
    FOREIGN KEY (original_sale_id) REFERENCES sales(id)
);

-- ===== Phase 3: 会员管理 =====
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE,
    level TEXT DEFAULT '普通会员',
    points INTEGER DEFAULT 0,
    total_consumption REAL DEFAULT 0,
    discount REAL DEFAULT 1.0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    remark TEXT
);

-- ===== Phase 3: 供应商管理 =====
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_person TEXT,
    phone TEXT,
    address TEXT,
    remark TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ===== Phase 3: 库存盘点 =====
CREATE TABLE IF NOT EXISTS stock_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    count_time TEXT DEFAULT (datetime('now','localtime')),
    product_id INTEGER,
    barcode TEXT,
    name TEXT,
    book_stock INTEGER DEFAULT 0,
    actual_stock INTEGER DEFAULT 0,
    diff_stock INTEGER DEFAULT 0,
    unit_cost REAL DEFAULT 0,
    diff_amount REAL DEFAULT 0,
    reason TEXT,
    status TEXT DEFAULT '待确认',
    operator TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- ===== Phase 4: 数据备份日志 =====
CREATE TABLE IF NOT EXISTS backup_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_time TEXT DEFAULT (datetime('now','localtime')),
    file_path TEXT,
    file_size INTEGER DEFAULT 0,
    status TEXT DEFAULT '成功',
    remark TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 初始化默认设置
INSERT OR IGNORE INTO settings (key, value) VALUES ('db_version', '4');
INSERT OR IGNORE INTO settings (key, value) VALUES ('min_stock_warning', '10');
INSERT OR IGNORE INTO settings (key, value) VALUES ('shelf_life_warning_days', '90');
INSERT OR IGNORE INTO settings (key, value) VALUES ('last_backup_time', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('shop_name', '我的小店');
"""


def initialize_database():
    """初始化数据库，创建所有表"""
    db = get_db()
    with db.transaction() as conn:
        conn.executescript(SCHEMA_SQL)
    logger.info("数据库初始化完成")


def _safe_str(val):
    """安全转换为字符串"""
    if val is None or pd.isna(val):
        return ""
    return str(val)


def _safe_float(val):
    """安全转换为浮点数"""
    if val is None or pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val):
    """安全转换为整数"""
    if val is None or pd.isna(val):
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def migrate_products_from_excel():
    """从商品资料.xlsx 迁移商品数据到 SQLite"""
    if not os.path.exists(EXCEL_PRODUCT_PATH):
        logger.warning("商品资料.xlsx 不存在，跳过商品迁移")
        return 0

    df = pd.read_excel(EXCEL_PRODUCT_PATH, dtype={'条码': str})
    if df.empty:
        return 0

    db = get_db()
    count = 0
    with db.transaction() as conn:
        for _, row in df.iterrows():
            try:
                barcode = _safe_str(row.get('条码', ''))
                name = _safe_str(row.get('名称（必填）', ''))
                if not name:
                    continue

                # 检查是否已存在
                existing = conn.execute(
                    "SELECT id FROM products WHERE barcode = ?", (barcode,)
                ).fetchone() if barcode else None

                if existing:
                    # 更新
                    conn.execute("""
                        UPDATE products SET
                            name=?, category=?, stock=?, purchase_price=?,
                            sale_price=?, wholesale_price=?, member_price=?,
                            updated_at=datetime('now','localtime')
                        WHERE id=?
                    """, (
                        name,
                        _safe_str(row.get('分类（必填）', '未分类')),
                        _safe_int(row.get('库存量', 0)),
                        _safe_float(row.get('进货价（必填）', 0)),
                        _safe_float(row.get('销售价（必填）', 0)),
                        _safe_float(row.get('批发价', 0)),
                        _safe_float(row.get('会员价', 0)),
                        existing['id']
                    ))
                else:
                    conn.execute("""
                        INSERT INTO products
                            (name, category, barcode, stock, purchase_price,
                             sale_price, wholesale_price, member_price,
                             member_discount, points_product, pinyin_code, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                COALESCE(?, datetime('now','localtime')))
                    """, (
                        name,
                        _safe_str(row.get('分类（必填）', '未分类')),
                        barcode if barcode else None,
                        _safe_int(row.get('库存量', 0)),
                        _safe_float(row.get('进货价（必填）', 0)),
                        _safe_float(row.get('销售价（必填）', 0)),
                        _safe_float(row.get('批发价', 0)),
                        _safe_float(row.get('会员价', 0)),
                        _safe_float(row.get('会员折扣', 0)),
                        _safe_int(row.get('积分商品', 0)),
                        _safe_str(row.get('拼音码', '')),
                        _safe_str(row.get('创建日期', None))
                    ))
                count += 1
            except Exception as e:
                logger.error(f"迁移商品记录失败: {e}")

    logger.info(f"商品数据迁移完成，共处理 {count} 条记录")
    return count


def migrate_sales_from_excel():
    """从销售历史.xlsx 迁移销售数据"""
    if not os.path.exists(EXCEL_SALES_PATH):
        logger.warning("销售历史.xlsx 不存在，跳过销售数据迁移")
        return 0

    df = pd.read_excel(EXCEL_SALES_PATH, dtype={'条码': str})
    if df.empty:
        return 0

    db = get_db()
    count = 0
    with db.transaction() as conn:
        for _, row in df.iterrows():
            try:
                sale_time = row.get('销售时间', None)
                if pd.notna(sale_time):
                    if hasattr(sale_time, 'strftime'):
                        sale_time = sale_time.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        sale_time = str(sale_time)
                else:
                    sale_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                conn.execute("""
                    INSERT INTO sales
                        (sale_time, barcode, name, quantity,
                         purchase_price, sale_price, revenue, profit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sale_time,
                    _safe_str(row.get('条码', '')),
                    _safe_str(row.get('名称', '')),
                    _safe_int(row.get('数量', 0)),
                    _safe_float(row.get('进货价', 0)),
                    _safe_float(row.get('销售价', 0)),
                    _safe_float(row.get('销售额', 0)),
                    _safe_float(row.get('利润', 0))
                ))
                count += 1
            except Exception as e:
                logger.error(f"迁移销售记录失败: {e}")

    logger.info(f"销售数据迁移完成，共处理 {count} 条记录")
    return count


def migrate_purchases_from_excel():
    """从进货管理.xlsx 迁移进货数据"""
    if not os.path.exists(EXCEL_PURCHASE_PATH):
        logger.warning("进货管理.xlsx 不存在，跳过进货数据迁移")
        return 0

    df = pd.read_excel(EXCEL_PURCHASE_PATH, dtype={'条码': str},
                       parse_dates=['入库时间', '生产日期', '到期时间'])
    if df.empty:
        return 0

    db = get_db()
    count = 0
    with db.transaction() as conn:
        for _, row in df.iterrows():
            try:
                def safe_date(val):
                    if pd.isna(val) or val is None:
                        return None
                    if hasattr(val, 'strftime'):
                        return val.strftime("%Y-%m-%d")
                    return str(val)[:10]

                barcode = _safe_str(row.get('条码', ''))
                product_id = None
                if barcode:
                    prod = conn.execute(
                        "SELECT id FROM products WHERE barcode = ?", (barcode,)
                    ).fetchone()
                    if prod:
                        product_id = prod['id']

                conn.execute("""
                    INSERT INTO purchases
                        (product_id, barcode, name, shelf_life,
                         production_date, expiry_date, 入库_time,
                         quantity, is_sold_out)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product_id,
                    barcode if barcode else None,
                    _safe_str(row.get('名称', '')),
                    _safe_int(row.get('保质期', 0)),
                    safe_date(row.get('生产日期', None)),
                    safe_date(row.get('到期时间', None)),
                    safe_date(row.get('入库时间', None)),
                    _safe_int(row.get('入库数量', 0)),
                    1 if _safe_str(row.get('是否售空', '否')) == '是' else 0
                ))
                count += 1
            except Exception as e:
                logger.error(f"迁移进货记录失败: {e}")

    logger.info(f"进货数据迁移完成，共处理 {count} 条记录")
    return count


def migrate_from_excel():
    """一键迁移所有 Excel 数据到 SQLite"""
    logger.info("开始从 Excel 迁移数据到 SQLite...")

    # 先初始化数据库
    initialize_database()

    # 按顺序迁移
    p_count = migrate_products_from_excel()
    s_count = migrate_sales_from_excel()
    pr_count = migrate_purchases_from_excel()

    total = p_count + s_count + pr_count
    logger.info(f"数据迁移完成！总计迁移 {total} 条记录（商品 {p_count} + 销售 {s_count} + 进货 {pr_count}）")

    return {
        'products': p_count,
        'sales': s_count,
        'purchases': pr_count,
        'total': total
    }
