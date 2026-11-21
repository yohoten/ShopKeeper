"""
全局配置模块
------------
集中管理应用品牌、路径、默认值与环境参数。

设计要点：
1. 兼容源码目录结构：database/ 既可能位于项目根目录，也可能已迁入 data/；
2. 兼容打包运行：PyInstaller 产物可通过 SHOPKEEPER_DATA_DIR / SHOPKEEPER_DB_PATH
   把数据写到 exe 外部，避免写入只读的 _MEIPASS 目录；
3. 所有业务阈值集中在此处，UI 不再硬编码。
"""
import os
import sys

# ========== 应用品牌 ==========
APP_NAME = "铺掌柜"
APP_NAME_EN = "ShopKeeper"
APP_VERSION = "4.1.0"
APP_TAGLINE = "零售进销存 · 扫码收银 · 库存管家"
APP_ICON = "📦"

# ========== 基础路径 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _first_existing(*paths):
    """返回第一个真实存在的路径；都不存在时返回最后一个作为默认落点。"""
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]


# 数据目录：打包时由环境变量指定；源码运行时优先使用 data/（若存在）
_env_data_dir = os.environ.get("SHOPKEEPER_DATA_DIR")
if _env_data_dir:
    DATA_DIR = os.path.abspath(_env_data_dir)
elif os.path.isdir(os.path.join(BASE_DIR, "data")):
    DATA_DIR = os.path.join(BASE_DIR, "data")
else:
    DATA_DIR = BASE_DIR

os.makedirs(DATA_DIR, exist_ok=True)

# database 包可能位于根目录或源码 data/ 下；即使 DATA_DIR 被环境变量覆盖，
# 源码 data/ 也必须保留在导入路径中，否则打包/外部数据模式下会 ModuleNotFoundError
for _path in (BASE_DIR, os.path.join(BASE_DIR, "data"), DATA_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ========== 数据库配置 ==========
DB_NAME = "shop_management.db"
DB_PATH = os.environ.get("SHOPKEEPER_DB_PATH") or _first_existing(
    os.path.join(BASE_DIR, DB_NAME),
    os.path.join(DATA_DIR, DB_NAME),
)

# Excel 路径（向后兼容 & 数据迁移）
EXCEL_PRODUCT_PATH = _first_existing(
    os.path.join(DATA_DIR, "商品资料.xlsx"),
    os.path.join(BASE_DIR, "商品资料.xlsx"),
)
EXCEL_SALES_PATH = os.path.join(DATA_DIR, "销售历史.xlsx")
EXCEL_PURCHASE_PATH = os.path.join(DATA_DIR, "进货管理.xlsx")

# ========== 日志与备份 ==========
LOG_DIR = os.environ.get("SHOPKEEPER_LOG_DIR") or os.path.join(DATA_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3

BACKUP_DIR = os.environ.get("SHOPKEEPER_BACKUP_DIR") or os.path.join(DATA_DIR, "backups")

# ========== 业务默认值 ==========
DEFAULT_CATEGORIES = ["零食", "饮料", "日用品", "生鲜", "干货", "调味品", "酒水", "个护", "文具"]
DEFAULT_PAGE_SIZE = 50
DEFAULT_DATE_RANGE_DAYS = 30  # 默认显示最近 30 天

# 保质期预警阈值（天）
SHELF_LIFE_WARNING_DAYS = 90  # 少于 90 天标黄
SHELF_LIFE_CRITICAL_DAYS = 30  # 少于 30 天标红

# 库存预警默认阈值
DEFAULT_MIN_STOCK = 10

# 会员积分默认值
MEMBER_DEFAULT_POINTS = 0
MEMBER_POINTS_PER_YUAN = 1  # 每消费 1 元获得 1 积分
MEMBER_POINTS_EXCHANGE_RATE = 100  # 100 积分 = 1 元

# 文件编码
ENCODING = "utf-8"
