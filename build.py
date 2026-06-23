#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPGEO-Query  跨平台一键打包脚本
================================
自动检测当前操作系统, 用 PyInstaller 打包为单文件可执行程序。

支持平台:
  - Windows → .exe   (GUI, 无控制台)
  - Linux   → ELF    (GUI, 无控制台)
  - macOS   → .app   (GUI, 无控制台) + 命令行二进制

用法:
  python3 build.py            # 自动检测平台并打包
  python3 build.py --cli      # 打包 CLI 模式 (有控制台输出, 用于调试)
  python3 build.py --clean    # 清理旧产物后打包
"""
import os
import shutil
import subprocess
import sys

APP_NAME = "IPGEO-Query"
SCRIPT   = "ip_geo_query.py"
ICON     = "icon.ico"  # 如果有图标文件则使用

IS_WINDOWS = sys.platform == "win32"
IS_MACOS   = sys.platform == "darwin"
IS_LINUX   = sys.platform.startswith("linux")
PLATFORM   = "Windows" if IS_WINDOWS else "macOS" if IS_MACOS else "Linux"

# 排除不必要的大模块, 减小体积
EXCLUDE_MODULES = [
    "matplotlib", "numpy", "pandas", "scipy", "PIL",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
    "pytest", "unittest", "test", "pydoc",
]


def run(cmd, **kw):
    print(f"\n>>> {' '.join(cmd)}\n", flush=True)
    return subprocess.run(cmd, check=True, **kw)


def clean_artifacts():
    """清理旧的构建产物"""
    for d in ("build", "dist", "__pycache__"):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"  清理: {d}/")
    spec = f"{APP_NAME}.spec"
    if os.path.isfile(spec):
        os.remove(spec)
        print(f"  清理: {spec}")


def find_tcltk_libs():
    """查找 Tcl/Tk 共享库 (PyInstaller 有时无法自动发现)"""
    import sysconfig
    found = []
    seen_names = set()

    # 收集搜索路径
    search_dirs = []
    # 1) Python 的 LIBDIR (最可靠, uv/pyenv 等都能覆盖)
    libdir = sysconfig.get_config_var('LIBDIR')
    if libdir:
        search_dirs.append(libdir)
    # 2) sys.prefix/lib
    search_dirs.append(os.path.join(sys.prefix, "lib"))
    # 3) sys.executable 上级 lib
    search_dirs.append(os.path.join(os.path.dirname(sys.executable), "..", "lib"))
    # 4) 系统标准路径
    search_dirs.extend([
        "/usr/lib", "/usr/lib/x86_64-linux-gnu",
        "/usr/local/lib", "/opt/homebrew/lib",
        "/usr/lib/aarch64-linux-gnu",  # ARM Linux
    ])

    for search_dir in search_dirs:
        search_dir = os.path.abspath(search_dir)
        if not os.path.isdir(search_dir):
            continue
        for f in sorted(os.listdir(search_dir)):
            if (f.startswith("libtcl") or f.startswith("libtk")) and f.endswith(".so"):
                if f not in seen_names:
                    seen_names.add(f)
                    found.append(os.path.join(search_dir, f))
    return found


def build(cli_mode=False):
    # 1) 检查 PyInstaller
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__}  已安装")
    except ImportError:
        print("未安装 PyInstaller, 正在安装 ...")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])

    # 2) 清理旧产物
    clean_artifacts()

    # 3) 构建命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile",            # 单文件
        f"--name={APP_NAME}",
    ]

    # --windowed: GUI 模式无控制台 / --console: CLI 模式有控制台
    if not cli_mode:
        cmd.append("--windowed")

    # 排除模块
    for mod in EXCLUDE_MODULES:
        cmd += ["--exclude-module", mod]

    # 查找并添加 Tcl/Tk 共享库 (解决某些环境下找不到 libtcl/libtk 的问题)
    tcltk_libs = find_tcltk_libs()
    if tcltk_libs:
        print(f"  发现 Tcl/Tk 库: {len(tcltk_libs)} 个")
        for lib in tcltk_libs:
            print(f"    {lib}")
            cmd += ["--add-binary", f"{lib}:."]

    # 平台特定参数
    if IS_MACOS:
        cmd += [
            "--osx-bundle-identifier",
            "com.samsepik9.ipgeo-query",
        ]

    # 图标 (如果存在)
    if os.path.isfile(ICON):
        if IS_WINDOWS:
            cmd += ["--icon", ICON]
        elif IS_MACOS:
            # macOS 用 .icns 格式, 如果只有 .ico 则跳过
            icns = ICON.replace(".ico", ".icns")
            if os.path.isfile(icns):
                cmd += ["--icon", icns]
            else:
                print(f"  跳过图标: macOS 需要 .icns 格式 (当前只有 {ICON})")

    cmd.append(SCRIPT)

    # 4) 执行打包
    run(cmd)

    # 5) 验证产物
    if IS_WINDOWS:
        out = os.path.join("dist", f"{APP_NAME}.exe")
    elif IS_MACOS:
        out = os.path.join("dist", f"{APP_NAME}.app")
        # macOS 还会有一个命令行二进制
        bin_out = os.path.join("dist", APP_NAME)
        if os.path.isfile(bin_out):
            os.chmod(bin_out, 0o755)
            sz = os.path.getsize(bin_out) / 1024 / 1024
            print(f"✓ CLI 二进制: {bin_out}  ({sz:.1f} MB)")
    else:
        out = os.path.join("dist", APP_NAME)
        # Linux 需要设置可执行权限
        if os.path.isfile(out):
            os.chmod(out, 0o755)

    if os.path.exists(out):
        sz = os.path.getsize(out) / 1024 / 1024
        print(f"\n{'='*50}")
        print(f"  ✓ 打包完成 ({PLATFORM})")
        print(f"  产物: {out}")
        print(f"  大小: {sz:.1f} MB")
        print(f"{'='*50}")
    else:
        sys.exit(f"✗ 打包失败, 未生成产物: {out}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"{APP_NAME} 跨平台打包脚本")
    parser.add_argument("--cli", action="store_true",
                        help="打包 CLI 模式 (保留控制台输出)")
    parser.add_argument("--clean-only", action="store_true",
                        help="仅清理旧产物, 不打包")
    args = parser.parse_args()

    print(f"当前平台: {PLATFORM}  (sys.platform={sys.platform})")

    if args.clean_only:
        clean_artifacts()
        print("✓ 清理完成")
        return

    build(cli_mode=args.cli)


if __name__ == "__main__":
    main()
