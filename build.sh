#!/usr/bin/env bash
# ==========================================================
#  IPGEO-Query  Linux / macOS 一键构建脚本
#  用法:  ./build.sh        # GUI 模式
#         ./build.sh --cli  # CLI 模式 (保留终端输出)
# ==========================================================
set -euo pipefail

cd "$(dirname "$0")"
APP_NAME="IPGEO-Query"
SCRIPT="ip_geo_query.py"

echo "=========================================="
echo "  IPGEO-Query  跨平台构建"
echo "  平台: $(uname -s) $(uname -m)"
echo "=========================================="

# 1) 检查 Python3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[ERR] 未找到 python3, 请先安装 Python 3.10+"
    exit 1
fi
echo "Python: $($PYTHON --version)"
PYTHON_PREFIX=$($PYTHON -c "import sys; print(sys.prefix)")

# 2) Linux 检查 tkinter
if [[ "$(uname -s)" == "Linux" ]]; then
    if ! $PYTHON -c "import tkinter" 2>/dev/null; then
        echo "[ERR] tkinter 不可用, 请安装:"
        echo "  Debian/Ubuntu: sudo apt install python3-tk"
        echo "  Fedora:        sudo dnf install python3-tkinter"
        echo "  Arch:          sudo pacman -S tk"
        exit 1
    fi
fi

# 3) 安装 PyInstaller
$PYTHON -m pip install --upgrade pyinstaller 2>/dev/null || {
    echo "[WARN] pip install 失败, 尝试使用已安装的 PyInstaller"
}

# 4) 清理旧产物
echo "[1/3] 清理旧产物 ..."
rm -rf build dist __pycache__ "${APP_NAME}.spec"

# 5) 构建
echo "[2/3] 开始构建 ..."
CLI_MODE="${1:-}"
BUILD_ARGS=(
    "$PYTHON" -m PyInstaller
    --clean --noconfirm
    --onefile
    --name="$APP_NAME"
    --exclude-module matplotlib
    --exclude-module numpy
    --exclude-module pandas
    --exclude-module scipy
    --exclude-module PIL
    --exclude-module PyQt5 --exclude-module PyQt6
    --exclude-module PySide2 --exclude-module PySide6
    --exclude-module wx
)

# 查找 Tcl/Tk 共享库 (解决某些环境下 PyInstaller 找不到 libtcl/libtk 的问题)
TCLTK_LIBS=$(find "$PYTHON_PREFIX/lib" /usr/lib /usr/lib/x86_64-linux-gnu /usr/local/lib -maxdepth 1 \( -name 'libtcl*.so' -o -name 'libtk*.so' \) 2>/dev/null | sort -u || true)
if [[ -n "$TCLTK_LIBS" ]]; then
    echo "  发现 Tcl/Tk 库:"
    while IFS= read -r lib; do
        [[ -z "$lib" ]] && continue
        echo "    $lib"
        BUILD_ARGS+=(--add-binary "$lib:.")
    done <<< "$TCLTK_LIBS"
fi

if [[ "$CLI_MODE" == "--cli" ]]; then
    echo "  (CLI 模式: 保留控制台)"
else
    BUILD_ARGS+=(--windowed)
fi

# macOS 特定参数
if [[ "$(uname -s)" == "Darwin" ]]; then
    BUILD_ARGS+=(--osx-bundle-identifier "com.samsepik9.ipgeo-query")
fi

BUILD_ARGS+=("$SCRIPT")
"${BUILD_ARGS[@]}"

# 6) 设置权限 & 验证
echo "[3/3] 验证产物 ..."
if [[ "$(uname -s)" == "Darwin" ]]; then
    OUT="dist/${APP_NAME}.app"
    BIN_OUT="dist/${APP_NAME}"
    if [[ -f "$BIN_OUT" ]]; then
        chmod +x "$BIN_OUT"
        SZ=$(du -h "$BIN_OUT" | cut -f1)
        echo "  ✓ CLI 二进制: $BIN_OUT  ($SZ)"
    fi
else
    OUT="dist/${APP_NAME}"
fi

if [[ -e "$OUT" ]]; then
    chmod +x "$OUT" 2>/dev/null || true
    SZ=$(du -h "$OUT" | cut -f1)
    echo ""
    echo "=========================================="
    echo "  ✓ 构建完成!"
    echo "  产物: $OUT"
    echo "  大小: $SZ"
    echo "=========================================="
else
    echo "[ERR] 构建失败, 未生成产物"
    exit 1
fi
