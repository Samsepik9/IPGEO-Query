# IPGEO-Query

> 专业的 **IP / 域名 / URL 地理位置 & 威胁情报** 查询 GUI 工具
> 数据源: [ihmily/ip-info-api](https://github.com/ihmily/ip-info-api) 汇总的免费 API

![python](https://img.shields.io/badge/python-3.10+-blue)
![pyinstaller](https://img.shields.io/badge/pyinstaller-6.x-green)
![license](https://img.shields.io/badge/license-MIT-orange)
![platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

## ✨ 特性

- **多 API 源可勾选对比**:
  - `ip-api.com` (主源, 支持中文 `lang=zh-CN`)
  - `api.ipapi.is` (含 VPN / 代理 / Tor / Datacenter 威胁情报)
  - `ipwhois.app` (英文备用)
  - `pconline` (国内源, 国内 IP 较准)
- **智能输入识别**: IPv4 / IPv6 / 完整 URL / 域名, 自动 DNS 解析
- **四 Tab 布局**:
  1. **🔍 单查询** - 摘要 + 多源结果表
  2. **📋 批量查询** - 一行一个目标, 文件导入
  3. **🕓 历史记录** - SQLite 本地存储, 可导出 CSV
  4. **{ } 原始 JSON** - 完整 API 响应, 可复制 / 保存
- **查询本机出口 IP**
- **跨平台快捷键**: Windows/Linux 用 `Ctrl`, macOS 自动适配 `⌘`
  - `Enter` 查询 / `Ctrl/⌘+L` 清空 / `Ctrl/⌘+C` 复制 / `Ctrl/⌘+E` 导出 / `Ctrl/⌘+Q` 退出
- **零第三方依赖** (纯 Python3 stdlib), `requests` 可选

## 📦 文件清单

```
IPGEO-Query/
├── ip_geo_query.py          # 主程序 (GUI + CLI 入口)
├── build.py                 # 跨平台打包脚本 (自动检测 OS)
├── build.sh                 # Linux/macOS 一键构建 (Shell)
├── build_windows.py         # Windows 打包脚本 (Python)
├── build_windows.bat        # Windows 一键打包 (cmd)
├── requirements.txt         # Python 依赖 (可选)
├── LICENSE                  # MIT 许可证
├── README.md                # 本文档
├── .github/workflows/
│   └── build.yml            # GitHub Actions 多平台自动构建
└── dist/                    # 构建产物 (gitignore)
    ├── IPGEO-Query.exe       # Windows
    ├── IPGEO-Query           # Linux
    └── IPGEO-Query.app       # macOS
```

## 🚀 快速使用

### 方式 1: 下载预编译二进制

前往 [Releases](../../releases) 页面下载对应平台的可执行文件:

| 平台 | 文件 | 说明 |
|---|---|---|
| Windows | `IPGEO-Query-windows-x64.exe` | 双击运行 |
| Linux | `IPGEO-Query-linux-x64` | `chmod +x` 后运行 |
| macOS | `IPGEO-Query-macos-x64.app` | 双击或 `open` 运行 |

> macOS 首次运行可能需要: 系统偏好设置 → 安全性与隐私 → 允许运行

### 方式 2: 源码运行 (任何平台)

```bash
python3 ip_geo_query.py
```

需要 Python 3.10+ (tkinter 来自标准库).

**Linux 需额外安装 tkinter:**
```bash
# Debian/Ubuntu
sudo apt install python3-tk
# Fedora
sudo dnf install python3-tkinter
# Arch
sudo pacman -S tk
```

**macOS:** 使用 [python.org](https://python.org) 官方安装包即可 (自带 tkinter). 如果用 Homebrew Python, 需 `brew install python-tk`.

可选安装 `requests` (更稳健的 HTTP 客户端, 不装也能跑):
```bash
pip install -r requirements.txt
```

### 方式 3: 自行编译打包

#### Windows
```cmd
build_windows.bat
:: 或
python build.py
:: 或
python -m PyInstaller --clean --noconfirm --onefile --windowed --name IPGEO-Query ip_geo_query.py
```

#### Linux
```bash
chmod +x build.sh
./build.sh
```

#### macOS
```bash
chmod +x build.sh
./build.sh
```

#### 通用 (跨平台 Python 脚本)
```bash
python3 build.py            # 自动检测平台并打包
python3 build.py --cli      # CLI 模式 (保留终端输出, 用于调试)
python3 build.py --clean-only  # 仅清理旧产物
```

### 方式 4: GitHub Actions 自动构建 (维护者)

推送 `v*` 格式的 tag 即可触发三平台自动构建并发布 Release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

也可在 GitHub 仓库 → Actions → "Build Cross-Platform Binaries" → Run workflow 手动触发.

## 📋 使用示例

| 输入 | 期望结果 |
|---|---|
| `196.189.234.67` | `埃塞俄比亚 奧羅米亞州 Nazrēt` (Ethio Telecom) |
| `www.google.com` | 自动 DNS → `142.250.x.x` 美国 加州 |
| `https://github.com/ihmily/ip-info-api` | 解析为 `github.com` → Microsoft Azure 新加坡节点 |
| `api.ipify.org` | 自动解析 → 查 IP 信息 |
| `192.168.1.1` | 提示: 内网/私有地址, 无公网信息 |
| `本机 IP` 按钮 | 自动检测出口 IP |

## 🔌 API 来源

| 源 | URL | 特点 |
|---|---|---|
| ip-api.com | `http://ip-api.com/json/{ip}?lang=zh-CN` | 中文, 免费, 无 key, **主源** |
| api.ipapi.is | `https://api.ipapi.is/?ip={ip}` | 含威胁情报 (VPN/Proxy/Tor) |
| ipwhois.app | `https://ipwhois.app/json/{ip}` | 英文, 含货币信息 |
| pconline | `https://whois.pconline.com.cn/ipJson.jsp` | 国内 IP 较准 |
| api.ip.sb | `https://api.ip.sb/geoip/` | 本机出口 IP |

> 所有 API 均为免费, 部分有速率限制 (约 45 req/min for ip-api.com).
> 数据精度有差异, 建议同时勾选 2-3 个源对比.

## 📂 数据存储

历史记录存于:
- Windows: `C:\Users\<你>\.IPGEO-Query\history.db` (SQLite)
- Linux/Mac: `~/.IPGEO-Query/history.db`

导出 CSV 用「历史记录 Tab → 导出 CSV」按钮.

## 🛠 故障排查

| 现象 | 排查 |
|---|---|
| 双击 exe 闪退 | 在 cmd 里运行 exe 看错误; 装 VC++ 运行时 [vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| 提示 "无法连接" | 检查网络; 部分源境外 IP 较慢; 勾选其它源重试 |
| Linux 提示 `No module named tkinter` | `sudo apt install python3-tk` |
| macOS 提示 `No module named tkinter` | 用 python.org 官方包, 或 `brew install python-tk` |
| macOS "无法验证开发者" | 系统偏好设置 → 安全性与隐私 → 允许运行 |
| API 返回 "RateLimited" | 等待 1-2 分钟, 减少勾选源数 |
| 国内 IP 信息不准 | 勾选「pconline (中文)」源 |
| 历史记录丢失 | SQLite 文件在用户目录, 重装不会丢 |

## 🔨 开发

### 项目结构

- 单文件架构: `ip_geo_query.py` (~900 行) 包含全部逻辑
- 无第三方依赖: 纯 stdlib (tkinter + urllib + sqlite3)
- 可选依赖: `requests` (更稳健 HTTP 客户端)
- 打包工具: PyInstaller (`--onefile` 单文件模式)

### 本地开发

```bash
# 克隆
git clone https://github.com/Samsepik9/IPGEO-Query.git
cd IPGEO-Query

# 直接运行 (无需安装依赖)
python3 ip_geo_query.py

# 可选: 安装 requests
pip install -r requirements.txt

# 打包
python3 build.py
```

## 📜 许可证

MIT — 见 [LICENSE](LICENSE)

## 🙏 致谢

- API 来源: [ihmily/ip-info-api](https://github.com/ihmily/ip-info-api)
- 打包: [PyInstaller](https://www.pyinstaller.org/)
