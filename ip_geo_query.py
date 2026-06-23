#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author:  samsepi0l  @  https://github.com/Samsepik9
"""
IPGEO-Query  ▸  IP / 域名 / URL 地理位置 & 威胁情报查询工具
============================================================

数据源来自 https://github.com/ihmily/ip-info-api  收集的免费 API
特性：
  - 单查询 / 批量查询 / 历史记录 / 原始 JSON 四个 Tab
  - 4 个数据源可选，支持同时查询并对比 (主中文源 + 英文备用 + 威胁情报)
  - 输入智能识别 IPv4 / IPv6 / URL / 域名
  - URL/域名 自动 DNS 解析到 IP
  - 表格化展示，列可排序，可导出 CSV
  - 历史记录本地保存 (SQLite)
  - 查询本机出口 IP
  - 全部 stdlib (tkinter + urllib + sqlite3), 无第三方依赖即可运行
  - 额外: pip install requests 即可获得更稳健的 HTTP 客户端

运行:   python3 ip_geo_query.py
打包:   pyinstaller --onefile --windowed --name IPGEO-Query ip_geo_query.py
"""

import csv
import datetime
import json
import os
import platform
import queue
import re
import socket
import sqlite3
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import filedialog, messagebox, ttk

# ─────────────────────────────────────────────────────────────────────────────
# 平台检测
# ─────────────────────────────────────────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"
IS_MACOS   = sys.platform == "darwin"
IS_LINUX   = sys.platform.startswith("linux")
PLATFORM   = "Windows" if IS_WINDOWS else "macOS" if IS_MACOS else "Linux"

# macOS 用 Command (⌘) 键, Windows/Linux 用 Control 键
MOD_KEY = "Command" if IS_MACOS else "Control"
MOD_LABEL = "⌘" if IS_MACOS else "Ctrl"

# ─────────────────────────────────────────────────────────────────────────────
# 常量 / API 端点
# ─────────────────────────────────────────────────────────────────────────────
APP_NAME    = "IPGEO-Query"
APP_VERSION = "1.0.0"

API_ZHCN    = "ip-api.com (中文)"   # 主源, 支持 lang=zh-CN
API_IPAPI   = "ipapi.is"            # 备用1, 威胁情报
API_WHOIS   = "ipwhois.app"         # 备用2, 英文
API_PCON    = "pconline (中文)"     # 国内源, 国内IP较准

URL_ZHCN    = "http://ip-api.com/json/{ip}?lang=zh-CN"
URL_IPAPI   = "https://api.ipapi.is/?ip={ip}"
URL_WHOIS   = "https://ipwhois.app/json/{ip}"
URL_PCON    = "https://whois.pconline.com.cn/ipJson.jsp?ip={ip}&json=true"
URL_SELF    = "https://api.ip.sb/geoip/"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
PRIVATE_PREFIX = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                  "172.20.", "172.21.", "172.22.", "172.23.",
                  "172.24.", "172.25.", "172.26.", "172.27.",
                  "172.28.", "172.29.", "172.30.", "172.31.",
                  "192.168.", "169.254.", "127.", "0.", "255.")
LOOPBACK = {"127.0.0.1", "0.0.0.0", "255.255.255.255"}

# ─────────────────────────────────────────────────────────────────────────────
# HTTP 客户端 (优先 requests, 降级 urllib)
# ─────────────────────────────────────────────────────────────────────────────
def _http_get_json(url: str, timeout: int = 10) -> dict:
    """GET URL -> dict, 失败抛异常. 优先 requests, 降级 urllib."""
    try:
        import requests  # type: ignore
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except ImportError:
        pass
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    text = raw.decode("utf-8", errors="replace").strip()
    if not text or text[0] not in "{[":
        raise ValueError(f"非 JSON 响应: {text[:120]!r}")
    return json.loads(text)

def _http_get_text(url: str, timeout: int = 10) -> str:
    try:
        import requests  # type: ignore
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        r.raise_for_status()
        return r.text
    except ImportError:
        pass
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# 输入解析 / DNS
# ─────────────────────────────────────────────────────────────────────────────
def parse_input(text: str) -> tuple[str, str]:
    """
    返回 (host, kind), kind ∈ {'ip','domain','url','empty','invalid'}.
    """
    s = (text or "").strip()
    if not s:
        return "", "empty"

    # 1) 完整 URL (含 scheme://) 先剥壳, 避免被 :端口 误判
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", s):
        m = re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://([^/:?#]+)", s)
        host = (m.group(1) if m else s).rstrip(".")
        return host, "url"

    # 2) host:port 形式 (没有 scheme)  -> 走 host
    if re.match(r"^[^/]+\.[^/]+:\d+($|/)", s):
        m = re.match(r"^([^/:]+)", s)
        host = m.group(1).rstrip(".") if m else s
        return host, "url"

    # 3) 纯 IP / IPv6
    if IPV4_RE.match(s) or (":" in s and s.count(":") >= 2):
        return s, "ip"

    # 4) 含路径/参数的 domain
    if "/" in s or "?" in s or "#" in s:
        m = re.match(r"^([^/:?#]+)", s)
        host = (m.group(1) if m else s).rstrip(".")
        return host, "url"

    # 5) 纯 host
    host = s.rstrip(".")

    if re.match(r"^(?=.{1,253}$)([A-Za-z0-9-]+\.)+[A-Za-z]{2,}$", host):
        kind = "url" if "://" in s or "/" in s else "domain"
        return host, kind
    if re.match(r"^[A-Za-z0-9-]+$", host):
        return host, "domain"
    return s, "invalid"

def resolve_host(host: str) -> str:
    if IPV4_RE.match(host) or (":" in host):
        return host
    name = host.rstrip(".")
    try:
        infos = socket.getaddrinfo(name, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError(f"DNS 解析失败: {name} ({e})") from e
    for fam, *_ , sa in infos:
        if fam == socket.AF_INET:
            return sa[0]
    for fam, *_ , sa in infos:
        if fam == socket.AF_INET6:
            return sa[0]
    raise ValueError(f"DNS 解析无结果: {name}")

def is_private_ip(ip: str) -> bool:
    return IPV4_RE.match(ip) is not None and (
        ip in LOOPBACK or any(ip.startswith(p) for p in PRIVATE_PREFIX))

# ─────────────────────────────────────────────────────────────────────────────
# 各 API 适配器 -> 统一记录
# ─────────────────────────────────────────────────────────────────────────────
def _row(ip, host, src, status, country="", region="", city="", isp="",
         org="", asn="", lat="", lon="", tz="", cc="", threat="", raw=None,
         err="") -> dict:
    return {
        "ip": ip, "host": host, "src": src, "status": status,
        "country": country, "region": region, "city": city,
        "isp": isp, "org": org, "asn": asn,
        "lat": lat, "lon": lon, "tz": tz, "cc": cc,
        "threat": threat, "raw": raw or {}, "err": err,
    }

def call_zhcn(ip: str, host: str) -> dict:
    try:
        d = _http_get_json(URL_ZHCN.format(ip=ip), timeout=10)
        if d.get("status") == "success":
            return _row(ip, host, API_ZHCN, "OK",
                        country=d.get("country", ""),
                        region=d.get("regionName", ""),
                        city=d.get("city", ""),
                        isp=d.get("isp", ""),
                        org=d.get("org", ""),
                        asn=d.get("as", ""),
                        lat=d.get("lat", ""),
                        lon=d.get("lon", ""),
                        tz=d.get("timezone", ""),
                        cc=d.get("countryCode", ""),
                        raw=d)
        return _row(ip, host, API_ZHCN, "FAIL", err=d.get("message", ""))
    except Exception as e:
        return _row(ip, host, API_ZHCN, "FAIL", err=str(e))

def call_ipapi(ip: str, host: str) -> dict:
    try:
        d = _http_get_json(URL_IPAPI.format(ip=ip), timeout=10)
        loc = d.get("location", {}) or {}
        asn = d.get("asn", {}) or {}
        co  = d.get("company", {}) or {}
        flags = [k.replace("is_", "").upper()
                 for k in ("is_datacenter","is_tor","is_proxy","is_vpn",
                           "is_abuser","is_mobile","is_satellite","is_crawler")
                 if d.get(k)]
        return _row(ip, host, API_IPAPI, "OK",
                    country=loc.get("country",""),
                    region=loc.get("state",""),
                    city=loc.get("city",""),
                    isp=co.get("name",""),
                    org=co.get("domain",""),
                    asn=f"AS{asn.get('asn','')} {asn.get('descr','')}".strip(),
                    lat=loc.get("latitude",""),
                    lon=loc.get("longitude",""),
                    tz=loc.get("timezone",""),
                    cc=loc.get("country_code",""),
                    threat=" / ".join(flags),
                    raw=d)
    except Exception as e:
        return _row(ip, host, API_IPAPI, "FAIL", err=str(e))

def call_whois(ip: str, host: str) -> dict:
    try:
        d = _http_get_json(URL_WHOIS.format(ip=ip), timeout=10)
        if d.get("success"):
            return _row(ip, host, API_WHOIS, "OK",
                        country=d.get("country",""),
                        region=d.get("region",""),
                        city=d.get("city",""),
                        isp=d.get("isp",""),
                        org=d.get("org",""),
                        asn=d.get("asn",""),
                        lat=d.get("latitude",""),
                        lon=d.get("longitude",""),
                        tz=d.get("timezone",""),
                        cc=d.get("country_code",""),
                        raw=d)
        return _row(ip, host, API_WHOIS, "FAIL", err=d.get("message",""))
    except Exception as e:
        return _row(ip, host, API_WHOIS, "FAIL", err=str(e))

def call_pconline(ip: str, host: str) -> dict:
    try:
        text = _http_get_text(URL_PCON.format(ip=ip), timeout=10)
        # pconline 偶有 BOM/编码问题
        text = text.encode("utf-8").decode("gbk", errors="replace")
        d = json.loads(text)
        if d.get("err") == "":
            return _row(ip, host, API_PCON, "OK",
                        country=d.get("pro",""),
                        region="",
                        city=d.get("city",""),
                        isp=d.get("addr","").split()[-1] if d.get("addr") else "",
                        org="",
                        asn="",
                        raw=d)
        return _row(ip, host, API_PCON, "FAIL", err=d.get("err",""))
    except Exception as e:
        return _row(ip, host, API_PCON, "FAIL", err=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 编排: 一次输入走多个源
# ─────────────────────────────────────────────────────────────────────────────
def query_all(target: str, sources: list[str]) -> list[dict]:
    """
    target: 用户原始输入
    sources: 选中的 API 源名 (subset of {API_ZHCN, API_IPAPI, API_WHOIS, API_PCON})
    返回: 适配后记录列表 (按 sources 顺序)
    """
    host, kind = parse_input(target)
    if kind == "empty":
        raise ValueError("输入为空")
    if kind == "invalid":
        raise ValueError(f"无法识别为 IP / 域名 / URL: {target!r}")
    try:
        ip = resolve_host(host)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"解析失败: {e}") from e

    if is_private_ip(ip):
        return [_row(ip, host, "system", "PRIVATE",
                     err="内网/私有地址, 公网 API 无结果")]

    funcs = {API_ZHCN: call_zhcn, API_IPAPI: call_ipapi,
             API_WHOIS: call_whois, API_PCON: call_pconline}
    out: list[dict] = []
    for s in sources:
        fn = funcs.get(s)
        if fn:
            out.append(fn(ip, host))
    if not out:
        raise ValueError("未选择任何 API 源")
    return out

def query_self_ip() -> dict:
    try:
        d = _http_get_json(URL_ZHCN.format(ip=""), timeout=10)
        if d.get("status") == "success":
            return _row(d.get("query",""), "", API_ZHCN, "OK",
                        country=d.get("country",""),
                        region=d.get("regionName",""),
                        city=d.get("city",""),
                        isp=d.get("isp",""),
                        org=d.get("org",""),
                        asn=d.get("as",""),
                        lat=d.get("lat",""),
                        lon=d.get("lon",""),
                        tz=d.get("timezone",""),
                        cc=d.get("countryCode",""),
                        raw=d)
    except Exception:
        pass
    try:
        d = _http_get_json(URL_SELF, timeout=10)
        return _row(d.get("ip",""), "", "ip.sb", "OK",
                    country=d.get("country",""),
                    region=d.get("region",""),
                    city=d.get("city",""),
                    isp=d.get("isp",""),
                    org=d.get("organization",""),
                    lat=d.get("latitude",""),
                    lon=d.get("longitude",""),
                    raw=d)
    except Exception as e:
        return _row("?", "", "system", "FAIL", err=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 历史记录 (SQLite)
# ─────────────────────────────────────────────────────────────────────────────
class HistoryDB:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, target TEXT, host TEXT, ip TEXT,
                src TEXT, status TEXT,
                country TEXT, region TEXT, city TEXT,
                isp TEXT, asn TEXT, cc TEXT
            )""")
        self.conn.commit()

    def add(self, row: dict, target: str):
        self.conn.execute(
            "INSERT INTO history "
            "(ts,target,host,ip,src,status,country,region,city,isp,asn,cc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (datetime.datetime.now().isoformat(timespec="seconds"),
             target, row.get("host",""), row.get("ip",""),
             row.get("src",""), row.get("status",""),
             row.get("country",""), row.get("region",""),
             row.get("city",""), row.get("isp",""), row.get("asn",""),
             row.get("cc","")))
        self.conn.commit()

    def fetch(self, limit: int = 500) -> list[dict]:
        cur = self.conn.execute(
            "SELECT id,ts,target,ip,src,status,country,region,city,isp,asn,cc "
            "FROM history ORDER BY id DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def clear(self):
        self.conn.execute("DELETE FROM history")
        self.conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────
COLUMNS = ("ip","host","src","status","country","region","city",
           "isp","asn","cc","threat")
COLUMN_LABELS = {
    "ip":"IP","host":"域名/Host","src":"数据源","status":"状态",
    "country":"国家","region":"省/州","city":"城市",
    "isp":"运营商","asn":"ASN","cc":"代码","threat":"威胁标签",
}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("1100x680")
        self.minsize(960, 600)

        # 字体自适应
        self.font_ui, self.font_mono, self.font_title = self._pick_fonts()

        # 历史库
        db_dir = os.path.join(os.path.expanduser("~"), f".{APP_NAME}")
        self.db = HistoryDB(os.path.join(db_dir, "history.db"))

        # 跨线程 UI 通信队列
        self._ui_queue: queue.Queue = queue.Queue()

        # 当前数据源勾选
        self.src_vars: dict[str, tk.BooleanVar] = {
            API_ZHCN:  tk.BooleanVar(value=True),
            API_IPAPI: tk.BooleanVar(value=True),
            API_WHOIS: tk.BooleanVar(value=False),
            API_PCON:  tk.BooleanVar(value=False),
        }

        self._build_ui()
        self._bind_keys()
        self._set_status("就绪。")

        # 启动主线程轮询 (在 mainloop 内)
        self.after(100, self._poll_ui_queue)

    # ── 字体 ──
    def _pick_fonts(self):
        from tkinter import font as tkfont
        families = set(tkfont.families())
        def first(*names, default=("TkDefaultFont", 10)):
            for n in names:
                if n in families: return n
            return default[0]
        ui   = (first("Microsoft YaHei UI","PingFang SC","Noto Sans CJK SC",
                      "Source Han Sans SC","WenQuanYi Micro Hei"), 10)
        mono = (first("Consolas","Menlo","DejaVu Sans Mono","Courier New"), 10)
        return ui, mono, (ui[0], 12, "bold")

    # ── UI 构造 ──
    def _build_ui(self):
        try: ttk.Style(self).theme_use("clam")
        except tk.TclError: pass
        s = ttk.Style(self)
        s.configure("Treeview", font=self.font_mono, rowheight=22)
        s.configure("Treeview.Heading", font=(self.font_ui[0], 10, "bold"))

        # 顶部
        top = ttk.Frame(self, padding=(10,8,10,4))
        top.pack(fill="x")
        ttk.Label(top, text=f"🌐  {APP_NAME}",
                  font=self.font_title).pack(side="left")
        ttk.Label(top, text="IP / 域名 / URL  地理位置 & 威胁情报",
                  foreground="#888").pack(side="left", padx=10)

        # 数据源勾选
        sf = ttk.Frame(self, padding=(10,0,10,4))
        sf.pack(fill="x")
        ttk.Label(sf, text="数据源:").pack(side="left")
        for name, var in self.src_vars.items():
            ttk.Checkbutton(sf, text=name, variable=var).pack(side="left", padx=4)

        # Notebook (Tab)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=4)

        self._tab_single()
        self._tab_batch()
        self._tab_history()
        self._tab_raw()

        # 底部状态
        self.var_status = tk.StringVar()
        bar = ttk.Frame(self, padding=(10,4,10,8))
        bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.var_status,
                  foreground="#666",
                  font=(self.font_ui[0], 9)).pack(side="left")
        ttk.Label(bar, text=f"Enter 查询 │ {MOD_LABEL}+L 清空 │ {MOD_LABEL}+C 复制 │ {MOD_LABEL}+E 导出 CSV",
                  foreground="#888",
                  font=(self.font_ui[0], 9)).pack(side="right")

    # ── Tab 1: 单查询 ──
    def _tab_single(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="🔍  单查询")

        row = ttk.Frame(f); row.pack(fill="x")
        ttk.Label(row, text="输入 IP / 域名 / URL:", font=self.font_ui)\
            .pack(side="left")
        self.var_single = tk.StringVar()
        e = ttk.Entry(row, textvariable=self.var_single, font=self.font_ui)
        e.pack(side="left", fill="x", expand=True, padx=6)
        e.bind("<Return>", lambda _evt: self._do_single())
        ttk.Button(row, text="查询", command=self._do_single)\
            .pack(side="left")
        ttk.Button(row, text="本机 IP", command=self._do_self)\
            .pack(side="left", padx=4)
        ttk.Button(row, text="复制结果", command=self._do_copy)\
            .pack(side="left")
        ttk.Button(row, text="清空", command=lambda: self._clear_single())\
            .pack(side="left", padx=4)

        # 摘要文本
        sumf = ttk.LabelFrame(f, text="摘要", padding=4)
        sumf.pack(fill="x", pady=(8,4))
        self.txt_single = tk.Text(sumf, height=3, font=self.font_mono,
                                  borderwidth=0, background="#fafafa")
        self.txt_single.pack(fill="x")

        # 表格
        tblf = ttk.LabelFrame(f, text="结果表格 (可排序, 选中行查看原始 JSON)",
                              padding=4)
        tblf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tblf, columns=COLUMNS, show="headings",
                                 selectmode="browse")
        for c in COLUMNS:
            self.tree.heading(c, text=COLUMN_LABELS[c],
                              command=lambda _c=c: self._sort_tree(_c))
            w = 100
            if c in ("ip","src","cc","status"): w = 90
            elif c in ("host","country","region","city","isp","asn","threat"):
                w = 140
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tblf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    # ── Tab 2: 批量 ──
    def _tab_batch(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="📋  批量查询")

        bar = ttk.Frame(f); bar.pack(fill="x")
        ttk.Label(bar, text="每行一个 (IP / 域名 / URL):",
                  font=self.font_ui).pack(side="left")
        ttk.Button(bar, text="开始批量",
                  command=self._do_batch).pack(side="right")
        ttk.Button(bar, text="从文件导入",
                  command=self._batch_import).pack(side="right", padx=4)
        ttk.Button(bar, text="清空",
                  command=lambda: self.txt_batch.delete("1.0","end"))\
            .pack(side="right", padx=4)

        self.txt_batch = tk.Text(f, height=6, font=self.font_mono)
        self.txt_batch.pack(fill="x", pady=(4,6))

        tbf = ttk.LabelFrame(f, text="结果", padding=4)
        tbf.pack(fill="both", expand=True)
        self.tree_batch = ttk.Treeview(tbf, columns=COLUMNS, show="headings")
        for c in COLUMNS:
            self.tree_batch.heading(c, text=COLUMN_LABELS[c])
            self.tree_batch.column(c, width=120, anchor="w")
        self.tree_batch.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tbf, orient="vertical",
                           command=self.tree_batch.yview)
        self.tree_batch.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")

    # ── Tab 3: 历史 ──
    def _tab_history(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="🕓  历史记录")

        bar = ttk.Frame(f); bar.pack(fill="x")
        ttk.Button(bar, text="刷新",
                  command=self._refresh_history).pack(side="left")
        ttk.Button(bar, text="清空历史",
                  command=self._clear_history).pack(side="left", padx=4)
        ttk.Button(bar, text="导出 CSV",
                  command=self._export_history).pack(side="left", padx=4)
        ttk.Button(bar, text="把所选填入单查询",
                  command=self._history_to_single).pack(side="right")

        cols = ("id","ts","target","ip","src","status",
                "country","region","city","isp","asn","cc")
        labels = {"id":"#","ts":"时间","target":"原始输入","ip":"IP",
                  "src":"源","status":"状态",
                  "country":"国家","region":"省","city":"城市",
                  "isp":"ISP","asn":"ASN","cc":"代码"}
        self.tree_hist = ttk.Treeview(f, columns=cols, show="headings")
        for c in cols:
            self.tree_hist.heading(c, text=labels.get(c,c))
            w = 80 if c in ("id","cc","status") else 130
            self.tree_hist.column(c, width=w, anchor="w")
        self.tree_hist.pack(fill="both", expand=True, pady=6)
        self._refresh_history()

    # ── Tab 4: 原始 JSON ──
    def _tab_raw(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="{ }  原始 JSON")
        bar = ttk.Frame(f); bar.pack(fill="x")
        ttk.Button(bar, text="复制",
                  command=lambda: self._copy_text(self.txt_raw)).pack(side="left")
        ttk.Button(bar, text="保存为 .json",
                  command=self._save_raw).pack(side="left", padx=4)
        ttk.Button(bar, text="清空",
                  command=lambda: self.txt_raw.delete("1.0","end")).pack(side="left")
        self.txt_raw = tk.Text(f, font=self.font_mono,
                               background="#fafafa")
        self.txt_raw.pack(fill="both", expand=True, pady=4)

    # ── 快捷键 ──
    def _bind_keys(self):
        # Windows/Linux: Control-l / macOS: Command-l
        self.bind(f"<{MOD_KEY}-l>", lambda e: self._clear_single())
        self.bind(f"<{MOD_KEY}-c>", lambda e: self._do_copy())
        self.bind(f"<{MOD_KEY}-e>", lambda e: self._export_history())
        self.bind(f"<{MOD_KEY}-q>", lambda e: self.destroy())
        # macOS 上额外兼容 Control 键 (部分用户习惯)
        if IS_MACOS:
            self.bind("<Control-l>", lambda e: self._clear_single())
            self.bind("<Control-c>", lambda e: self._do_copy())
            self.bind("<Control-e>", lambda e: self._export_history())
            self.bind("<Control-q>", lambda e: self.destroy())

    # ── 行为: 单查询 ──
    def _do_single(self):
        target = self.var_single.get().strip()
        if not target:
            messagebox.showinfo(APP_NAME, "请输入 IP / 域名 / URL")
            return
        sources = [n for n,v in self.src_vars.items() if v.get()]
        if not sources:
            messagebox.showwarning(APP_NAME, "请至少勾选一个数据源")
            return
        self._set_status(f"查询中: {target}  ({len(sources)} 个源) …")
        self._run_thread(lambda: (target, sources))

    def _do_self(self):
        self._set_status("查询本机 IP …")
        self._run_thread(lambda: ("__SELF__", [API_ZHCN]))

    def _render_rows(self, target: str, rows: list[dict]):
        # 清空单查询表格
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.txt_single.delete("1.0","end")

        if target == "__SELF__":
            row = rows[0]
            ip = row.get("ip","?")
            summary = f"[本机 IP]  {ip}  {row.get('country','')}  " \
                      f"{row.get('region','')}  {row.get('city','')}  " \
                      f"{row.get('isp','')}"
            self.txt_single.insert("1.0", summary)
            for k,v in row.items():
                if k in ("raw",) or v in (None,"","null"): continue
                self.txt_raw.insert("end", f"{k}: {v}\n")
            self.txt_raw.insert("end", "\n" + json.dumps(
                row.get("raw", {}), ensure_ascii=False, indent=2))
            return

        # 第一条 OK 作摘要
        primary = next((r for r in rows if r["status"] == "OK"), None)
        if primary:
            ip = primary["ip"]; host = primary.get("host","")
            head = "  ".join(x for x in
                             [ip, primary["country"], primary["region"],
                              primary["city"]] if x)
            if host and host != ip:
                head = f"{host}  →  {head}"
            self.txt_single.insert("1.0", head)
        else:
            self.txt_single.insert("1.0", "全部数据源查询失败, 详见下方与 历史 标签")

        # 入表
        for r in rows:
            self.tree.insert("", "end", values=(
                r["ip"], r.get("host",""), r["src"], r["status"],
                r["country"], r["region"], r["city"],
                r["isp"], r["asn"], r["cc"], r["threat"]))
            # 入库
            self.db.add(r, target)

        # 写原始 JSON
        self.txt_raw.delete("1.0","end")
        self.txt_raw.insert("1.0",
                            json.dumps([{k:v for k,v in r.items() if k!="raw"}
                                        for r in rows],
                                       ensure_ascii=False, indent=2))
        for r in rows:
            self.txt_raw.insert("end",
                                f"\n\n--- {r['src']} ---\n"
                                + json.dumps(r.get("raw", {}),
                                             ensure_ascii=False, indent=2))

    def _on_row_select(self, _evt):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        # 选中的行 -> 把原始 JSON 切到该项
        # (简化: 已经全部展示, 这里不做复杂切换)
        # 切换到原始 JSON Tab
        self.nb.select(3)

    # ── 行为: 批量 ──
    def _do_batch(self):
        lines = [ln.strip() for ln in self.txt_batch.get("1.0","end").splitlines()
                 if ln.strip()]
        if not lines:
            messagebox.showinfo(APP_NAME, "请输入要批量查询的内容")
            return
        sources = [n for n,v in self.src_vars.items() if v.get()]
        if not sources:
            messagebox.showwarning(APP_NAME, "请至少勾选一个数据源")
            return

        for iid in self.tree_batch.get_children():
            self.tree_batch.delete(iid)
        self._set_status(f"批量查询 {len(lines)} 个目标 …")

        def work():
            for i, t in enumerate(lines, 1):
                self._ui_queue.put(("batch_progress", i, len(lines), t))
                try:
                    rows = query_all(t, sources)
                    primary = next((r for r in rows if r["status"]=="OK"),
                                   rows[0])
                    self._ui_queue.put(("batch_row", primary, t))
                except Exception as e:
                    err_row = _row("?","","|".join(sources),"FAIL",
                                     err=f"ERR: {e}")
                    self._ui_queue.put(("batch_row", err_row, t))
            self._ui_queue.put(("batch_done", len(lines)))

        threading.Thread(target=work, daemon=True).start()

    def _batch_import(self):
        path = filedialog.askopenfilename(
            title="选择文本文件 (每行一个目标)",
            filetypes=[("文本", "*.txt"), ("所有", "*.*")])
        if not path: return
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            self.txt_batch.delete("1.0","end")
            self.txt_batch.insert("1.0", f.read())
        self._set_status(f"已导入: {path}")

    # ── 行为: 历史 ──
    def _refresh_history(self):
        for iid in self.tree_hist.get_children():
            self.tree_hist.delete(iid)
        for r in self.db.fetch(1000):
            self.tree_hist.insert("", "end", values=(
                r["id"], r["ts"], r["target"], r["ip"], r["src"],
                r["status"], r["country"], r["region"], r["city"],
                r["isp"], r["asn"], r["cc"]))

    def _clear_history(self):
        if messagebox.askyesno(APP_NAME, "确认清空所有历史记录?"):
            self.db.clear()
            self._refresh_history()
            self._set_status("历史已清空")

    def _export_history(self):
        path = filedialog.asksaveasfilename(
            title="导出历史为 CSV",
            defaultextension=".csv",
            initialfile=f"{APP_NAME}-history-{int(time.time())}.csv",
            filetypes=[("CSV", "*.csv")])
        if not path: return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id","ts","target","ip","src","status",
                        "country","region","city","isp","asn","cc"])
            for r in self.db.fetch(10000):
                w.writerow([r["id"],r["ts"],r["target"],r["ip"],
                            r["src"],r["status"],r["country"],
                            r["region"],r["city"],r["isp"],r["asn"],r["cc"]])
        self._set_status(f"已导出: {path}")

    def _history_to_single(self):
        sel = self.tree_hist.selection()
        if not sel: return
        vals = self.tree_hist.item(sel[0])["values"]
        target = vals[2] if len(vals) > 2 else ""
        if target:
            self.var_single.set(target)
            self.nb.select(0)
            self._do_single()

    # ── 行为: 杂项 ──
    def _do_copy(self):
        # 优先复制摘要, 否则复制原始 JSON
        s = self.txt_single.get("1.0","end-1c").strip()
        if not s:
            s = self.txt_raw.get("1.0","end-1c").strip()
        if not s:
            self._set_status("没有可复制内容")
            return
        self.clipboard_clear(); self.clipboard_append(s)
        self._set_status("✓ 已复制到剪贴板")

    def _clear_single(self):
        self.var_single.set("")
        self.txt_single.delete("1.0","end")
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.txt_raw.delete("1.0","end")

    def _copy_text(self, widget: tk.Text):
        s = widget.get("1.0","end-1c").strip()
        if s:
            self.clipboard_clear(); self.clipboard_append(s)
            self._set_status("✓ 已复制")

    def _save_raw(self):
        s = self.txt_raw.get("1.0","end-1c").strip()
        if not s:
            self._set_status("原始 JSON 为空")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("文本","*.txt")])
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            f.write(s)
        self._set_status(f"已保存: {path}")

    def _sort_tree(self, col):
        items = [(self.tree.set(iid, col), iid)
                 for iid in self.tree.get_children("")]
        try:
            items.sort(key=lambda x: float(x[0]))
        except Exception:
            items.sort()
        for _v, iid in reversed(items):
            self.tree.move(iid, "", "end")

    # ── 后台线程 (用 queue 跨线程通信, 避免 after() 跨线程不可靠) ──
    def _run_thread(self, fn):
        self._set_status("查询中 …")
        def work():
            try:
                target, sources = fn()
                if target == "__SELF__":
                    rows = [query_self_ip()]
                else:
                    rows = query_all(target, sources)
                # 成功 -> 把结果放进队列, 主线程轮询取出
                self._ui_queue.put(("ok", target, rows))
            except Exception as e:
                self._ui_queue.put(("err", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def _poll_ui_queue(self):
        """主线程定时器: 从队列取出结果并更新 UI"""
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]
                if kind == "ok":
                    _, target, rows = item
                    self._render_rows(target, rows)
                    self._set_status("✓ 完成")
                elif kind == "err":
                    err = item[1]
                    self._set_status(f"✗ 失败: {err}")
                    messagebox.showerror(APP_NAME, f"查询失败:\n{err}")
                elif kind == "batch_done":
                    self._set_status(f"✓ 批量完成: {item[1]} 个")
                elif kind == "batch_progress":
                    _, i, n, t = item
                    self._set_status(f"批量 {i}/{n}: {t}")
                elif kind == "batch_row":
                    _, primary_row, target = item
                    self.tree_batch.insert("", "end", values=(
                        primary_row["ip"], primary_row.get("host",""),
                        primary_row["src"], primary_row["status"],
                        primary_row["country"], primary_row["region"],
                        primary_row["city"], primary_row["isp"],
                        primary_row["asn"], primary_row["cc"],
                        primary_row["threat"]))
                    self.db.add(primary_row, target)
        except queue.Empty:
            pass
        # 每 100ms 轮询一次
        self.after(100, self._poll_ui_queue)

    def _set_status(self, msg: str):
        self.var_status.set(msg)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    try:
        app = App()
    except tk.TclError as e:
        # 无 GUI -> CLI fallback
        print(f"[GUI 不可用: {e}] 进入 CLI 模式", file=sys.stderr)
        _cli_loop()
        return
    app.mainloop()

def _cli_loop():
    print("="*60)
    print(f"{APP_NAME} v{APP_VERSION}  ({PLATFORM} CLI 模式)")
    print(f"输入:  IP / 域名 / URL      命令: q 退出 | self 本机 IP")
    print("="*60)
    while True:
        try:
            q = input("\n>>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("q","quit","exit"): break
        if not q: continue
        if q.lower() in ("self","me"):
            r = query_self_ip()
            print(f"[本机]  {r.get('ip')}  {r.get('country')}  "
                  f"{r.get('region')}  {r.get('city')}  {r.get('isp')}")
            continue
        for r in query_all(q, [API_ZHCN, API_IPAPI]):
            print(f"[{r['src']}] {r['status']:4s}  {r['ip']}  "
                  f"{r['country']}  {r['region']}  {r['city']}  "
                  f"{r['isp']}  {r.get('threat','')}")
            if r.get("err"): print(f"     err: {r['err']}")

if __name__ == "__main__":
    main()
