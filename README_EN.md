# IPGEO-Query

**[简体中文](README.md)** | **English**

> A professional **IP / Domain / URL Geolocation & Threat Intelligence** query GUI tool
> Data sources: free APIs aggregated by [ihmily/ip-info-api](https://github.com/ihmily/ip-info-api)

![python](https://img.shields.io/badge/python-3.10+-blue)
![pyinstaller](https://img.shields.io/badge/pyinstaller-6.x-green)
![license](https://img.shields.io/badge/license-MIT-orange)
![platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

## ✨ Features

- **Multi-source query with side-by-side comparison**:
  - `ip-api.com` (primary, supports `lang=zh-CN`)
  - `api.ipapi.is` (includes VPN / Proxy / Tor / Datacenter threat intel)
  - `ipwhois.app` (English fallback)
  - `pconline` (China-based source, more accurate for CN IPs)
- **Smart input recognition**: IPv4 / IPv6 / full URL / domain, with automatic DNS resolution
- **Four-tab layout**:
  1. **🔍 Single Query** — summary + multi-source result table
  2. **📋 Batch Query** — one target per line, file import supported
  3. **🕓 History** — local SQLite storage, CSV export
  4. **{ } Raw JSON** — full API responses, copy / save
- **Detect your own public IP**
- **Cross-platform keyboard shortcuts**: `Ctrl` on Windows/Linux, `⌘` on macOS
  - `Enter` query / `Ctrl/⌘+L` clear / `Ctrl/⌘+C` copy / `Ctrl/⌘+E` export / `Ctrl/⌘+Q` quit
- **Zero third-party dependencies** (pure Python 3 stdlib), `requests` optional

## 📦 Project Structure

```
IPGEO-Query/
├── ip_geo_query.py          # Main application (GUI + CLI entry)
├── build.py                 # Cross-platform build script (auto-detects OS)
├── build.sh                 # Linux/macOS one-click build (Shell)
├── build_windows.py         # Windows build script (Python)
├── build_windows.bat        # Windows one-click build (cmd)
├── requirements.txt         # Python dependencies (optional)
├── LICENSE                  # MIT License
├── README.md                # Chinese documentation
├── README_EN.md             # English documentation
├── .github/workflows/
│   └── build.yml            # GitHub Actions multi-platform CI/CD
└── dist/                    # Build artifacts (gitignored)
    ├── IPGEO-Query.exe       # Windows
    ├── IPGEO-Query           # Linux
    └── IPGEO-Query.app       # macOS
```

## 🚀 Quick Start

### Option 1: Download Pre-built Binaries

Go to the [Releases](../../releases) page and download the executable for your platform:

| Platform | File | Usage |
|---|---|---|
| Windows | `IPGEO-Query-windows-x64.exe` | Double-click to run |
| Linux | `IPGEO-Query-linux-x64` | `chmod +x` then run |
| macOS | `IPGEO-Query-macos-x64.zip` | Unzip, then double-click or `open` |

> macOS first run: System Settings → Privacy & Security → Allow anyway

### Option 2: Run from Source (any platform)

```bash
python3 ip_geo_query.py
```

Requires Python 3.10+ (tkinter is part of the standard library).

**Linux — install tkinter separately:**
```bash
# Debian/Ubuntu
sudo apt install python3-tk
# Fedora
sudo dnf install python3-tkinter
# Arch
sudo pacman -S tk
```

**macOS:** Use the official installer from [python.org](https://python.org) (includes tkinter). If using Homebrew Python, run `brew install python-tk`.

Optional: install `requests` for a more robust HTTP client (works without it too):
```bash
pip install -r requirements.txt
```

### Option 3: Build from Source

#### Windows
```cmd
build_windows.bat
:: or
python build.py
:: or
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

#### Universal (cross-platform Python script)
```bash
python3 build.py            # Auto-detect platform and build
python3 build.py --cli      # CLI mode (keep terminal output, for debugging)
python3 build.py --clean-only  # Clean build artifacts only
```

### Option 4: GitHub Actions Auto-Build (for maintainers)

Push a `v*` tag to trigger tri-platform builds and publish a Release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

You can also manually trigger it: GitHub repo → Actions → "Build Cross-Platform Binaries" → Run workflow.

## 📋 Usage Examples

| Input | Expected Result |
|---|---|
| `196.189.234.67` | `Ethiopia, Oromia, Nazrēt` (Ethio Telecom) |
| `www.google.com` | Auto DNS → `142.250.x.x` United States, CA |
| `https://github.com/ihmily/ip-info-api` | Parsed as `github.com` → Microsoft Azure Singapore |
| `api.ipify.org` | Auto-resolve → query IP info |
| `192.168.1.1` | Notice: private/internal address, no public info |
| `My IP` button | Auto-detect your public exit IP |

## 🔌 API Sources

| Source | URL | Notes |
|---|---|---|
| ip-api.com | `http://ip-api.com/json/{ip}?lang=zh-CN` | Chinese, free, no key, **primary** |
| api.ipapi.is | `https://api.ipapi.is/?ip={ip}` | Threat intelligence (VPN/Proxy/Tor) |
| ipwhois.app | `https://ipwhois.app/json/{ip}` | English, includes currency info |
| pconline | `https://whois.pconline.com.cn/ipJson.jsp` | More accurate for China IPs |
| api.ip.sb | `https://api.ip.sb/geoip/` | Self/public IP detection |

> All APIs are free. Some have rate limits (~45 req/min for ip-api.com).
> Data accuracy varies — recommended to select 2–3 sources for comparison.

## 📂 Data Storage

Query history is stored locally at:
- Windows: `C:\Users\<you>\.IPGEO-Query\history.db` (SQLite)
- Linux/macOS: `~/.IPGEO-Query/history.db`

Export to CSV via the History tab → "Export CSV" button.

## 🛠 Troubleshooting

| Issue | Fix |
|---|---|
| exe crashes on double-click | Run from cmd to see error; install [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| "Cannot connect" | Check network; some sources are slow for overseas IPs; try other sources |
| Linux: `No module named tkinter` | `sudo apt install python3-tk` |
| macOS: `No module named tkinter` | Use python.org installer, or `brew install python-tk` |
| macOS: "Cannot verify developer" | System Settings → Privacy & Security → Allow anyway |
| API returns "RateLimited" | Wait 1–2 minutes, reduce selected sources |
| Inaccurate CN IP info | Enable the "pconline" source |
| History lost | SQLite file is in user home dir — survives reinstall |

## 🔨 Development

### Architecture

- Single-file design: `ip_geo_query.py` (~900 lines) contains all logic
- No third-party dependencies: pure stdlib (tkinter + urllib + sqlite3)
- Optional dependency: `requests` (more robust HTTP client)
- Build tool: PyInstaller (`--onefile` mode)

### Local Development

```bash
# Clone
git clone https://github.com/Samsepik9/IPGEO-Query.git
cd IPGEO-Query

# Run directly (no dependencies needed)
python3 ip_geo_query.py

# Optional: install requests
pip install -r requirements.txt

# Build
python3 build.py
```

## 📜 License

MIT — see [LICENSE](LICENSE)

## 🙏 Acknowledgements

- API sources: [ihmily/ip-info-api](https://github.com/ihmily/ip-info-api)
- Packaging: [PyInstaller](https://www.pyinstaller.org/)
