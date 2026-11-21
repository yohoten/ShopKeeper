"""
日志工具模块
提供统一的日志记录功能，支持文件轮转
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT


# 存储已创建的 logger，避免重复配置
_loggers = {}


def get_logger(name: str = __name__) -> logging.Logger:
    """
    获取或创建日志记录器

    Args:
        name: 日志器名称，通常传入 __name__

    Returns:
        logging.Logger 实例
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 创建日志目录
    os.makedirs(LOG_DIR, exist_ok=True)

    # 文件 Handler（带轮转）
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    _loggers[name] = logger
    return logger
