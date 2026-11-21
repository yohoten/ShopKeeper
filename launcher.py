"""
铺掌柜 ShopKeeper — 免安装版启动器
----------------------------------
职责：
1. 把数据目录固定到 exe 同级的 data/，与程序本体分离（升级不丢数据）；
2. 首次启动时把内置的商品资料 Excel 释放到数据目录，由主程序自动迁移建库；
3. 选择本机空闲端口，以 headless 模式启动 Streamlit 并自动打开浏览器。

源码运行：python launcher.py
打包运行：由 build.py 作为 PyInstaller 入口
"""
from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_NAME = "铺掌柜"
APP_NAME_EN = "ShopKeeper"


def bundle_dir() -> Path:
    """返回随包资源的根目录（onefile 为 _MEIPASS，onedir/源码为项目目录）。"""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def exe_dir() -> Path:
    """返回可执行文件所在目录；源码运行时为项目目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def prepare_data() -> Path:
    """准备外部数据目录并设置环境变量；返回数据目录。"""
    data_dir = exe_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    bundled = bundle_dir()

    # 种子商品资料：首次运行释放一次，之后绝不覆盖用户数据
    seed_excel = bundled / "商品资料.xlsx"
    target_excel = data_dir / "商品资料.xlsx"
    if seed_excel.is_file() and not target_excel.exists():
        shutil.copy2(seed_excel, target_excel)

    os.environ["SHOPKEEPER_DATA_DIR"] = str(data_dir)
    os.environ["SHOPKEEPER_DB_PATH"] = str(data_dir / "shop_management.db")
    os.environ["SHOPKEEPER_LOG_DIR"] = str(data_dir / "logs")
    os.environ["SHOPKEEPER_BACKUP_DIR"] = str(data_dir / "backups")
    return data_dir


def free_port() -> int:
    """向系统申请一个当前空闲端口，避免与其他实例冲突。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> int:
    data_dir = prepare_data()
    bundle = bundle_dir()

    # 动态导入的业务模块以数据文件形式随包发布，需要显式加入导入路径
    for path in (str(bundle), str(exe_dir())):
        if path not in sys.path:
            sys.path.insert(0, path)

    app_file = bundle / "streamlit_app.py"
    if not app_file.is_file():
        print(f"[错误] 找不到主程序：{app_file}", file=sys.stderr)
        return 1

    port = free_port()
    url = f"http://127.0.0.1:{port}"

    sys.argv = [
        "streamlit", "run", str(app_file),
        # 冻结环境里 Streamlit 会误判为开发模式，进而拒绝自定义端口
        "--global.developmentMode=false",
        # 关闭 magic 模式：它会向脚本 AST 注入 magic_funcs 导入，
        # 冻结环境中该模块未被静态分析收集时会直接 ModuleNotFoundError。
        "--runner.magicEnabled=false",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
        "--logger.level=warning",
    ]

    # Streamlit headless 模式不会自动打开浏览器，延迟打开以等待服务就绪
    threading.Timer(2.0, webbrowser.open, args=(url,)).start()

    print(f"{APP_NAME} {APP_NAME_EN} 正在启动：{url}")
    print(f"数据目录：{data_dir}")
    print("关闭此窗口即可退出程序。")

    from streamlit.web import cli as stcli
    return int(stcli.main() or 0)


if __name__ == "__main__":
    sys.exit(main())
