#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""铺掌柜 ShopKeeper — 一键打包脚本

把 Streamlit 应用打包为 Windows 免安装程序。默认生成「目录版」
（启动快、升级方便）；加 --onefile 可生成单文件 exe。

数据设计
--------
程序本体与数据分离：exe 同级 data/ 存放数据库、备份与日志。
升级时直接替换程序目录即可，data/ 不会被动过。

UPX 策略
--------
不让 PyInstaller 逐个压缩上百个 DLL/.pyd（受限环境中会触发批量删除保护），
而是在构建完成后对最终 exe 执行一次 UPX 压缩，效果稳定且可回退（--no-upx）。

用法
----
    python build.py                 # 目录版 + UPX 压缩 + 生成 zip 分发包
    python build.py --onefile       # 单文件 exe
    python build.py --no-upx        # 关闭 UPX 压缩
    python build.py --upx-dir DIR   # 指定 UPX 所在目录（默认 H:\\UPX）
    python build.py --no-zip        # 只要构建产物，不打 zip
    python build.py --no-clean      # 保留 build/ 以增量加速
    python build.py --check         # 只做环境自检，不打包
    python build.py --no-icon       # 不使用任何图标

图标
----
优先使用项目根目录的 icon.ico；缺失时回退到自动生成的 app.ico。

退出码
------
0 成功；1 环境/源文件检查失败；2 依赖缺失；3 PyInstaller 失败；
4 产物校验失败；5 zip 打包失败。
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
APP_NAME_EN = "ShopKeeper"
APP_NAME_CN = "铺掌柜"
APP_VERSION = "4.1.0"

ENTRY = APP_DIR / "launcher.py"
ICON = APP_DIR / "icon.ico"          # 用户提供的正式图标，优先使用
GENERATED_ICON = APP_DIR / "app.ico"  # 仅当 icon.ico 缺失时生成
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
BUILD_LOG = BUILD_DIR / "pyinstaller.log"

# 每次构建使用独立的输出目录：避免 PyInstaller 批量删除旧产物时被系统安全策略拦截
BUILD_TAG = time.strftime("%Y%m%d_%H%M%S")
BUILD_START = time.time()  # 用于区分本次产物与历史残留
OUTPUT_DIR = DIST_DIR / f"{APP_NAME_EN}_{BUILD_TAG}"
ONEDIR_EXE = OUTPUT_DIR / APP_NAME_EN / f"{APP_NAME_EN}.exe"
ONEFILE_EXE = OUTPUT_DIR / f"{APP_NAME_EN}.exe"

# UPX 压缩：默认使用本机 H:\UPX\upx.exe；可用 --upx-dir 覆盖，--no-upx 关闭
UPX_DEFAULT_DIR = Path(r"H:\UPX")
UPX_EXE_NAME = "upx.exe"

MIN_PYTHON = (3, 9)

# 动态加载的业务模块必须由 add-data 显式带入（PyInstaller 静态分析看不到 importlib）
SOURCE_FILES = ["streamlit_app.py", "config.py"]
SOURCE_DIRS = ["ui", "models", "services", "utils"]

# 运行时依赖：import 名 -> pip 安装名
RUNTIME_DEPS = {
    "streamlit": "streamlit>=1.30",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "openpyxl": "openpyxl",
    "xpinyin": "xpinyin",
    "PIL": "Pillow",
    "altair": "altair",
}

HIDDEN_IMPORTS = [
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.script_runner",
    "streamlit.runtime.scriptrunner.magic_funcs",  # magic 模式会动态导入
    "streamlit.components.v1",
    "pandas", "pyarrow", "numpy", "openpyxl", "xpinyin",
    "altair", "PIL", "watchdog", "tornado", "click",
]


# --------------------------------------------------------------------------- #
# 控制台输出（兼容 GBK 代码页）
# --------------------------------------------------------------------------- #
def _echo(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(text.encode(enc, "replace"))
        sys.stdout.buffer.flush()


def log(msg: str = "") -> None:
    _echo(f"[{time.strftime('%H:%M:%S')}] {msg}\n")


def step(msg: str) -> None:
    _echo(f"\n[{time.strftime('%H:%M:%S')}] === {msg} ===\n")


def warn(msg: str) -> None:
    _echo(f"[{time.strftime('%H:%M:%S')}] [警告] {msg}\n")


def fail(msg: str) -> None:
    _echo(f"[{time.strftime('%H:%M:%S')}] [错误] {msg}\n")


# --------------------------------------------------------------------------- #
# 环境自检
# --------------------------------------------------------------------------- #
def check_python() -> bool:
    if sys.version_info < MIN_PYTHON:
        fail(f"Python 需要 >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}，"
             f"当前为 {sys.version.split()[0]}")
        return False
    log(f"Python {sys.version.split()[0]}  ({sys.executable})")
    return True


def resolve_seed_excel() -> Path | None:
    """商品资料.xlsx 可能在根目录或 data/ 下。"""
    for p in (APP_DIR / "商品资料.xlsx", APP_DIR / "data" / "商品资料.xlsx"):
        if p.is_file():
            return p
    return None


def check_sources() -> bool:
    ok = True
    if ENTRY.is_file():
        log(f"入口就绪：{ENTRY.name}")
    else:
        fail(f"缺少入口文件：{ENTRY}")
        ok = False

    for name in SOURCE_FILES:
        p = APP_DIR / name
        if p.is_file():
            log(f"源码就绪：{name}")
        else:
            fail(f"缺少源码：{p}")
            ok = False

    for name in SOURCE_DIRS:
        p = APP_DIR / name
        if p.is_dir():
            log(f"模块目录就绪：{name}/")
        else:
            fail(f"缺少模块目录：{p}")
            ok = False

    # database 包的新旧两种位置
    db_pkg = APP_DIR / "database"
    if not db_pkg.is_dir():
        db_pkg = APP_DIR / "data" / "database"
    if db_pkg.is_dir() and (db_pkg / "connection.py").is_file():
        log(f"数据库模块就绪：{db_pkg.relative_to(APP_DIR)}/")
    else:
        fail("缺少 database 包（根目录或 data/ 下均应存在）")
        ok = False

    seed = resolve_seed_excel()
    if seed:
        log(f"种子数据就绪：{seed.relative_to(APP_DIR)}")
    else:
        warn("未找到 商品资料.xlsx，打包后首次启动将没有初始商品数据")

    return ok


def module_available(name: str) -> bool:
    try:
        if importlib.util.find_spec(name) is None:
            return False
        if name == "PIL":
            import PIL  # noqa: F401
        elif name == "openpyxl":
            import openpyxl  # noqa: F401
        elif name == "xpinyin":
            import xpinyin  # noqa: F401
        return True
    except (ImportError, ValueError):
        return False


def check_deps(skip: bool) -> bool:
    if skip:
        log("已跳过依赖检查（--skip-deps）")
        return True
    missing = [pip_name for mod, pip_name in RUNTIME_DEPS.items()
               if not module_available(mod)]
    if not importlib.util.find_spec("PyInstaller"):
        missing.append("pyinstaller")
    if missing:
        fail("以下依赖缺失，请先安装：")
        _echo("        " + sys.executable + " -m pip install -r requirements.txt\n")
        return False
    log("运行依赖与 PyInstaller 均已就绪")
    return True


# --------------------------------------------------------------------------- #
# 图标
# --------------------------------------------------------------------------- #
def resolve_icon(use_icon: bool) -> Path | None:
    """确定打包图标：优先用户提供的 icon.ico，缺失时生成 app.ico。"""
    if not use_icon:
        log("已按 --no-icon 禁用程序图标")
        return None
    if ICON.is_file():
        log(f"使用正式图标：{ICON.name}")
        return ICON
    if GENERATED_ICON.is_file():
        log(f"icon.ico 缺失，使用已有图标：{GENERATED_ICON.name}")
        return GENERATED_ICON
    return _generate_icon()


def _generate_icon() -> Path | None:
    """用 Pillow 生成简洁的蓝色图标；失败时允许无图标继续打包。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        warn("Pillow 不可用，跳过图标生成")
        return None

    try:
        size = 256
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((8, 8, 248, 248), radius=56,
                               fill=(67, 97, 238, 255))
        draw.rounded_rectangle((44, 74, 212, 196), radius=20,
                               outline=(255, 255, 255, 235), width=8)
        draw.line((130, 74, 130, 196), fill=(255, 255, 255, 200), width=7)

        font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyh.ttc"
        if font_path.is_file():
            try:
                font = ImageFont.truetype(str(font_path), 64)
                draw.text((128, 135), "铺", font=font,
                          fill=(255, 255, 255, 255), anchor="mm")
            except OSError:
                pass
        img.save(GENERATED_ICON, format="ICO",
                 sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        log(f"已生成备用图标：{GENERATED_ICON.name}")
        return GENERATED_ICON
    except Exception as exc:
        warn(f"图标生成失败（不影响打包）：{exc}")
        return None


# --------------------------------------------------------------------------- #
# UPX 压缩
# --------------------------------------------------------------------------- #
def resolve_upx(spec_dir: str | None, disabled: bool) -> tuple[Path | None, bool]:
    """定位 UPX 目录，返回 (目录或 None, 是否显式指定却不可用)。"""
    if disabled:
        log("已按 --no-upx 关闭 UPX 压缩")
        return None, False

    explicit = bool(spec_dir)
    cand = Path(spec_dir) if explicit else UPX_DEFAULT_DIR
    if cand.is_file() and cand.name.lower() == UPX_EXE_NAME:
        cand = cand.parent
    upx_exe = cand / UPX_EXE_NAME
    if not upx_exe.is_file():
        if explicit:
            return None, True
        warn(f"未找到 UPX：{upx_exe}")
        warn("本次打包不做 UPX 压缩；可用 --upx-dir 指定目录。")
        return None, False

    try:
        out = subprocess.run(
            [str(upx_exe), "--version"], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=20,
        )
        version = next((ln.strip() for ln in (out.stdout or "").splitlines()
                        if ln.strip().lower().startswith("upx")), "")
        log(f"UPX 就绪：{version or upx_exe}  ({upx_exe})")
    except (OSError, subprocess.SubprocessError):
        log(f"UPX 就绪：{upx_exe}")
    return cand, False


# --------------------------------------------------------------------------- #
# 打包
# --------------------------------------------------------------------------- #
def add_data_args(seed: Path | None) -> list[str]:
    args: list[str] = []
    for name in SOURCE_FILES:
        args += ["--add-data", f"{APP_DIR / name}{os.pathsep}."]
    for name in SOURCE_DIRS:
        args += ["--add-data", f"{APP_DIR / name}{os.pathsep}{name}"]

    db_pkg = APP_DIR / "database"
    if not db_pkg.is_dir():
        db_pkg = APP_DIR / "data" / "database"
    args += ["--add-data", f"{db_pkg}{os.pathsep}database"]

    if seed:
        args += ["--add-data", f"{seed}{os.pathsep}."]
    return args


def clean_outputs(no_clean: bool) -> None:
    step("清理旧产物")
    if not no_clean and BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        log("已删除 build/")
    # 不删除 dist/：产物文件数量很多，批量删除可能被系统安全策略拦截。
    # 每次构建输出到带时间戳的新目录，天然避免覆盖与删除冲突。
    if DIST_DIR.exists():
        log("检测到已有 dist/，本次输出至独立子目录，历史产物保留")


def run_pyinstaller(onefile: bool, no_clean: bool, seed: Path | None,
                    icon: Path | None) -> bool:
    step("调用 PyInstaller")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile" if onefile else "--onedir",
        "--windowed",
        f"--name={APP_NAME_EN}",
        f"--distpath={OUTPUT_DIR}",
        "--noconfirm",
    ]
    if icon and icon.is_file():
        cmd.append(f"--icon={icon}")
    # 不让 PyInstaller 逐个调用 UPX：它会重写上百个 DLL/.pyd，
    # 在受限环境中会触发批量删除保护。改为构建完成后只压缩最终 exe。
    cmd.append("--noupx")
    for mod in HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={mod}")
    # xpinyin 运行时读取 Mandarin.dat，必须随包携带，否则首次导入即 FileNotFoundError
    cmd += ["--collect-data", "streamlit", "--collect-data", "altair",
            "--collect-data", "xpinyin"]
    cmd += ["--copy-metadata", "streamlit", "--copy-metadata", "altair"]
    cmd += add_data_args(seed)
    cmd.append(str(ENTRY))

    log("执行：" + " ".join(cmd))
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    with open(BUILD_LOG, "w", encoding="utf-8", errors="replace") as logf:
        proc = subprocess.Popen(
            cmd, cwd=str(APP_DIR), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            _echo(line)
            logf.write(line)
        rc = proc.wait()

    if rc != 0:
        fail(f"PyInstaller 退出码 {rc}（完整日志：{BUILD_LOG}）")
        return False
    return True


def compress_with_upx(exe: Path, upx_dir: Path | None) -> bool:
    """构建完成后压缩最终 exe（单文件操作，不会触发批量删除保护）。"""
    if upx_dir is None:
        log("UPX 压缩：未启用")
        return True
    upx_exe = upx_dir / UPX_EXE_NAME
    if not upx_exe.is_file():
        warn(f"未找到 {upx_exe}，跳过 UPX 压缩")
        return True

    before = exe.stat().st_size
    step("UPX 压缩最终可执行文件")
    # PyInstaller 6 的 bootloader 默认开启 CFG，UPX 5 需要 --force 才会压缩
    # （该参数会关闭 PE 的 CFG 标记），构建日志中会明确提示这一点。
    warn("exe 启用了 CFG，UPX 将使用 --force（关闭 CFG 标记）进行压缩")
    cmd = [str(upx_exe), "--force", "--best", "-q", str(exe)]
    log("执行：" + " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        warn(f"UPX 调用失败（保留未压缩 exe）：{exc}")
        return True
    if proc.returncode != 0:
        detail = (proc.stdout or "").strip().replace("\n", " ")[:200]
        warn(f"UPX 压缩失败（保留未压缩 exe）：{detail}")
        return True

    after = exe.stat().st_size
    log(f"UPX 完成：{before / 1024 / 1024:.1f} MB → {after / 1024 / 1024:.1f} MB "
        f"（减少 {(1 - after / before) * 100:.0f}%）")
    return True


def verify_output(onefile: bool) -> Path | None:
    step("校验产物")
    exe = ONEFILE_EXE if onefile else ONEDIR_EXE
    if not exe.is_file():
        fail(f"未找到预期产物：{exe}")
        return None
    if exe.stat().st_mtime < BUILD_START - 2:
        fail(f"产物时间戳早于本次构建，疑似旧文件：{exe}")
        return None
    size_mb = exe.stat().st_size / (1024 * 1024)
    log(f"可执行文件：{exe}")
    log(f"体积：{size_mb:.1f} MB")
    if onefile:
        warn("单文件版首次启动需要解压，速度慢于目录版；数据仍写在同级 data/")
    return exe


def verify_after_upx(exe: Path) -> bool:
    """UPX 压缩后再确认产物完好。"""
    if not exe.is_file() or exe.stat().st_size == 0:
        fail(f"UPX 压缩后产物异常：{exe}")
        return False
    return True


def make_zip(exe: Path, onefile: bool) -> Path | None:
    step("生成分发包")
    zip_path = DIST_DIR / f"{APP_NAME_EN}_v{APP_VERSION}_win_x64.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            if onefile:
                zf.write(exe, exe.name)
            else:
                root = exe.parent
                for f in root.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(root.parent))
            for name in ("README.md", "LICENSE"):
                p = APP_DIR / name
                if p.is_file():
                    zf.write(p, name)
    except OSError as exc:
        fail(f"zip 生成失败：{exc}")
        return None
    log(f"分发包：{zip_path}  ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return zip_path


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=f"{APP_NAME_CN} {APP_NAME_EN} v{APP_VERSION} 打包脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--onefile", action="store_true", help="生成单文件 exe（默认目录版）")
    p.add_argument("--no-zip", action="store_true", help="不生成 zip 分发包")
    p.add_argument("--no-clean", action="store_true", help="保留 build/ 以增量加速")
    p.add_argument("--no-icon", action="store_true", help="不使用程序图标")
    p.add_argument("--upx-dir", default=None, metavar="DIR",
                   help=f"UPX 所在目录（默认：{UPX_DEFAULT_DIR}，可传 upx.exe 路径）")
    p.add_argument("--no-upx", action="store_true", help="关闭 UPX 压缩（默认开启）")
    p.add_argument("--skip-deps", action="store_true", help="跳过依赖检查")
    p.add_argument("--check", action="store_true", help="只做环境自检，不打包")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    log(f"{APP_NAME_CN} {APP_NAME_EN} v{APP_VERSION} · 打包开始")

    step("环境自检")
    if not (check_python() and check_sources()):
        return 1
    step("依赖检查")
    if not check_deps(args.skip_deps):
        return 2
    step("程序图标")
    icon = resolve_icon(not args.no_icon)

    step("UPX 压缩")
    upx_dir, explicit_bad = resolve_upx(args.upx_dir, args.no_upx)
    if explicit_bad:
        fail(f"--upx-dir 下没有 {UPX_EXE_NAME}：{args.upx_dir}")
        return 1
    if args.check:
        log("自检完成，未执行打包。")
        return 0

    clean_outputs(args.no_clean)
    seed = resolve_seed_excel()
    if not run_pyinstaller(args.onefile, args.no_clean, seed, icon):
        return 3
    exe = verify_output(args.onefile)
    if exe is None:
        return 4
    compress_with_upx(exe, upx_dir)
    if not verify_after_upx(exe):
        return 4
    if not args.no_zip and make_zip(exe, args.onefile) is None:
        return 5

    log("\n打包完成 ✔")
    log("运行方式：双击 exe；首次启动后会在同级 data/ 生成数据库与备份。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
