#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ip_geo_query.py  一键打包脚本 (Windows)
=========================================
在 Windows 命令行 (cmd / PowerShell) 中, 进入此目录运行:
    python build_windows.py
或者双击本文件 (需关联 python.exe)
"""
import os
import shutil
import subprocess
import sys

APP_NAME = "IPGEO-Query"
SCRIPT   = "ip_geo_query.py"
SPEC     = f"{APP_NAME}.spec"
ICON     = "icon.ico"

def run(cmd, **kw):
    print(f"\n>>> {cmd}\n", flush=True)
    return subprocess.run(cmd, check=True, **kw)

def main():
    # 1) 检查 PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__}  OK")
    except ImportError:
        print("未安装 PyInstaller, 正在安装 ...")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])

    # 2) 清理旧产物
    for d in ("build", "dist", "__pycache__"):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
    for f in (f"{APP_NAME}.spec",):
        if os.path.isfile(f):
            os.remove(f)

    # 3) 打包命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile",            # 单文件
        "--windowed",           # GUI 不开控制台
        f"--name={APP_NAME}",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "PIL",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
        "--exclude-module", "PySide2",
        "--exclude-module", "PySide6",
        "--exclude-module", "wx",
    ]
    if os.path.isfile(ICON):
        cmd += ["--icon", ICON]

    cmd.append(SCRIPT)
    run(cmd)

    out = os.path.join("dist", f"{APP_NAME}.exe")
    if os.path.isfile(out):
        sz = os.path.getsize(out) / 1024 / 1024
        print(f"\n✓ 打包完成: {out}  ({sz:.1f} MB)")
    else:
        sys.exit("✗ 打包失败, 未生成 exe")

if __name__ == "__main__":
    main()
