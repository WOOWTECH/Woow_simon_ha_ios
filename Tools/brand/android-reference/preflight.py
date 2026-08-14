#!/usr/bin/env python3
"""
品牌設定檔驗證器。

三種模式：

1) 驗證單一設定檔的格式與可用性
       python3 preflight.py tools/brand/apporo.conf

2) 同時驗證多個品牌，額外檢查跨品牌衝突（applicationId / scheme / brand_id 撞號）
       python3 preflight.py tools/brand/apporo.conf tools/brand/simon.conf

3) 換裝後（或合併上游後）驗證工作目錄裡的品牌值有沒有被蓋回去
       python3 preflight.py --verify-repo tools/brand/apporo.conf

離開碼 0 = 通過，1 = 有錯誤。警告不影響離開碼。
"""

from __future__ import annotations

import argparse
import colorsys
import os
import re
import shlex
import subprocess
import sys

REQUIRED = ["BRAND_ID", "APP_NAME", "APPLICATION_ID", "BRAND_HOST", "PRIMARY_COLOR"]

# Android package name 規則：至少兩段，每段字母開頭，只含小寫英數與底線
RE_APPID = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
RE_BRAND_ID = re.compile(r"^[a-z][a-z0-9]*$")          # 會變成資源檔名，只能小寫英數
RE_HOST = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
RE_HEX = re.compile(r"^#?[0-9A-Fa-f]{6}$")
RE_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*$")          # RFC 3986

# Android 保留字，不能當 package 的任何一段
JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class",
    "const", "continue", "default", "do", "double", "else", "enum", "extends", "final",
    "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
    "throw", "throws", "transient", "try", "void", "volatile", "while", "in", "is", "fun",
    "object", "val", "var", "when",
}

# 這些值屬於上游 woowtech，出現在品牌設定檔裡代表沒改到
UPSTREAM = {
    "APPLICATION_ID": "com.woowtech.home",
    "BRAND_HOST": "aiot.woowtech.io",
    "PRIMARY_COLOR": "#6183FC",
    "BRAND_ID": "woowtech",
}

errors: list[str] = []
warns: list[str] = []


def err(conf: str, msg: str) -> None:
    errors.append(f"[{conf}] {msg}")


def warn(conf: str, msg: str) -> None:
    warns.append(f"[{conf}] {msg}")


def load(path: str) -> dict[str, str]:
    """讀 shell 風格的 KEY="value" 設定檔。不執行它——設定檔可能來自他人，
    用 shlex 解析比 source 進 shell 安全。"""
    out: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", k):
                continue
            try:
                parts = shlex.split(v, comments=True)
            except ValueError:
                parts = [v.strip().strip("\"'")]
            out[k] = parts[0] if parts else ""
    return out


def contrast_on_white(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]

    def ch(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    lum = 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])
    return 1.05 / (lum + 0.05)


def check_one(path: str, cfg: dict[str, str]) -> None:
    name = os.path.basename(path)

    for key in REQUIRED:
        if not cfg.get(key):
            err(name, f"{key} 未填。這是必填欄位，開工前要先跟使用者確認。")

    bid = cfg.get("BRAND_ID", "")
    if bid and not RE_BRAND_ID.match(bid):
        err(name, f"BRAND_ID='{bid}' 不合法。它會變成資源檔名 ic_<id>_branding.png，"
                  f"只能小寫英文開頭 + 小寫英數（不能有底線、連字號、大寫）。")

    appid = cfg.get("APPLICATION_ID", "")
    if appid:
        if not RE_APPID.match(appid):
            err(name, f"APPLICATION_ID='{appid}' 不合法。Android package 需至少兩段、"
                      f"每段字母開頭、只含小寫英數與底線。")
        for seg in appid.split("."):
            if seg in JAVA_KEYWORDS:
                err(name, f"APPLICATION_ID 的 '{seg}' 是 Java/Kotlin 保留字，建置會失敗。")
        if appid != appid.lower():
            err(name, "APPLICATION_ID 含大寫字母。Play Store 與 Gradle 都要求全小寫。")

    host = cfg.get("BRAND_HOST", "")
    if host:
        if host.startswith(("http://", "https://")):
            err(name, f"BRAND_HOST='{host}' 不要含通訊協定，只填網域（例如 aiot.apporo.io）。")
        elif not RE_HOST.match(host):
            err(name, f"BRAND_HOST='{host}' 不像合法網域。")
        if host.endswith("/"):
            err(name, "BRAND_HOST 結尾不要有斜線。")

    color = cfg.get("PRIMARY_COLOR", "")
    if color:
        if not RE_HEX.match(color):
            err(name, f"PRIMARY_COLOR='{color}' 需為 6 碼 HEX（例如 #1E88E5），"
                      f"不支援 3 碼縮寫或 8 碼含 alpha。")
        else:
            ratio = contrast_on_white(color)
            if ratio < 3.0:
                err(name, f"PRIMARY_COLOR={color} 對白字對比僅 {ratio:.2f}:1，"
                          f"主色按鈕上的白字幾乎無法閱讀。請改用較深的主色，"
                          f"或與設計確認按鈕文字改用深色。")
            elif ratio < 4.5:
                warn(name, f"PRIMARY_COLOR={color} 對白字對比 {ratio:.2f}:1，"
                           f"低於 WCAG AA 的 4.5:1。深色模式與小字級會明顯吃力。")

    scheme = cfg.get("URL_SCHEME", "")
    if not scheme:
        warn(name, "URL_SCHEME 留空 = 沿用 homeassistant://。"
                   "只要使用者可能同時安裝兩個以上品牌的 App，點連結就會跳出「用哪個 App 開啟」選單。"
                   "強烈建議每個品牌各自設定。")
    else:
        if not RE_SCHEME.match(scheme):
            err(name, f"URL_SCHEME='{scheme}' 不合法。需小寫字母開頭，只含小寫英數與 + . -。")
        if scheme == "homeassistant":
            warn(name, "URL_SCHEME 明確設成 homeassistant，等同不換。確認這是刻意的。")

    logo = cfg.get("LOGO_SRC", "")
    if not logo:
        warn(name, "LOGO_SRC 留空，會產生首字母佔位圖。"
                   "可以先跑通流程，但正式版務必換成真 logo。")
    elif not os.path.exists(logo):
        warn(name, f"LOGO_SRC='{logo}' 目前不存在。若尚未取得素材，"
                   f"換裝時會退回佔位圖（腳本不會中斷）。")

    for key, upstream_value in UPSTREAM.items():
        if cfg.get(key, "").lower() == upstream_value.lower():
            err(name, f"{key} 還是上游 woowtech 的值（{upstream_value}），沒有改成品牌值。")

    if cfg.get("OAUTH_CLIENT_ID"):
        warn(name, f"OAUTH_CLIENT_ID 已設為 {cfg['OAUTH_CLIENT_ID']}。"
                   f"HA 伺服器會驗證這個網址可達，頁面沒架好會導致使用者登不進去。"
                   f"確認該網址已上線後再保留此設定。")

    scale = cfg.get("LOGO_SCALE", "")
    if scale:
        try:
            v = float(scale)
            if not 0.2 <= v <= 0.9:
                warn(name, f"LOGO_SCALE={v} 超出合理範圍。adaptive icon 的安全區是 66/108≈0.61，"
                           f"超過會被系統遮罩切到，太小則圖示看起來空洞。建議 0.5–0.7。")
        except ValueError:
            err(name, f"LOGO_SCALE='{scale}' 不是數字。")


def check_cross(configs: list[tuple[str, dict[str, str]]]) -> None:
    """跨品牌衝突。兩個品牌撞到同一個 applicationId 或 scheme，
    使用者裝上第二個 App 時會覆蓋第一個、或看到 App 選擇選單。"""
    for field, label in [
        ("APPLICATION_ID", "applicationId 相同代表兩個 App 無法並存安裝，後裝的會覆蓋先裝的"),
        ("URL_SCHEME", "scheme 相同代表點 deep link 會跳出「用哪個 App 開啟」選單"),
        ("BRAND_ID", "brand_id 相同代表資源檔名相同，不影響建置但會混淆"),
        ("BRAND_HOST", "網域相同代表兩個品牌連同一台伺服器，確認這是刻意的"),
    ]:
        seen: dict[str, list[str]] = {}
        for path, cfg in configs:
            v = cfg.get(field, "")
            if v:
                seen.setdefault(v.lower(), []).append(os.path.basename(path))
        for value, owners in seen.items():
            if len(owners) > 1:
                msg = f"{field}='{value}' 同時出現在 {', '.join(owners)} —— {label}"
                (warn if field == "BRAND_HOST" else err)("cross", msg)

    # 也要跟已上線的 woowtech Home 比對
    for path, cfg in configs:
        if not cfg.get("URL_SCHEME"):
            warn(os.path.basename(path),
                 "未設 URL_SCHEME，會與已上線的 woowtech Home 共用 homeassistant://。")


def verify_repo(path: str, cfg: dict[str, str]) -> None:
    """換裝後 / 合併上游後，確認工作目錄裡的品牌值還在。
    這比人工 review 300 個檔案的 merge diff 可靠得多。"""
    name = os.path.basename(path)
    checks = [
        ("applicationId",
         "build-logic/convention/src/main/kotlin/AndroidApplicationConventionPlugin.kt",
         f'APPLICATION_ID = "{cfg.get("APPLICATION_ID", "")}"'),
        ("app_name (en)",
         "common/src/main/res/values/strings.xml",
         f'<string name="app_name">{cfg.get("APP_NAME", "")}</string>'),
        ("app_name (zh-rTW)",
         "common/src/main/res/values-zh-rTW/strings.xml",
         f'<string name="app_name">{cfg.get("APP_NAME", "")}</string>'),
        ("colorPrimary",
         "common/src/main/res/values/colors.xml",
         f'<color name="colorPrimary">{cfg.get("PRIMARY_COLOR", "").upper()}</color>'),
        ("推播端點",
         "gradle.properties",
         cfg.get("BRAND_HOST", "")),
    ]
    for label, filename, needle in checks:
        if not needle.strip():
            continue
        if not os.path.exists(filename):
            err(name, f"{label}: 找不到 {filename}（是不是不在 repo 根目錄？）")
            continue
        content = open(filename, encoding="utf-8", errors="replace").read()
        if needle not in content:
            err(name, f"{label} 不是品牌值 —— 在 {filename} 找不到 `{needle}`。"
                      f"合併上游時可能被蓋回去了。")

    # 殘留的上游關鍵字
    try:
        res = subprocess.run(
            ["git", "grep", "-l", "-i", "-e", "woowtech", "-e", "aiot.woowtech.io",
             "--", ":!tools/brand", ":!docs/brand", ":!*lint-baseline.xml"],
            capture_output=True, text=True, timeout=60,
        )
        files = [x for x in res.stdout.split() if x]
        if files:
            warn(name, f"仍有 {len(files)} 個檔案含 woowtech 關鍵字："
                       f"{', '.join(files[:5])}{' …' if len(files) > 5 else ''}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="woow_ha_app 品牌設定檔驗證")
    ap.add_argument("conf", nargs="+", help="一個或多個品牌設定檔")
    ap.add_argument("--verify-repo", action="store_true",
                    help="改為驗證目前工作目錄的品牌值（換裝後 / 合併上游後使用）")
    a = ap.parse_args()

    configs = []
    for path in a.conf:
        if not os.path.exists(path):
            print(f"找不到設定檔：{path}", file=sys.stderr)
            return 1
        configs.append((path, load(path)))

    if a.verify_repo:
        for path, cfg in configs:
            verify_repo(path, cfg)
    else:
        for path, cfg in configs:
            check_one(path, cfg)
        if len(configs) > 1:
            check_cross(configs)

    print()
    if errors:
        print("\033[1;31m✗ 錯誤（必須修正）\033[0m")
        for e in errors:
            print(f"  {e}")
        print()
    if warns:
        print("\033[1;33m! 警告（請確認是刻意的）\033[0m")
        for w in warns:
            print(f"  {w}")
        print()
    if not errors and not warns:
        print("\033[1;32m✓ 全部通過\033[0m\n")
    elif not errors:
        print("\033[1;32m✓ 無阻斷性問題\033[0m\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
