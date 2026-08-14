#!/usr/bin/env python3
"""本地化字串品牌替換 — 只動 value、白名單保護、格式符驗證。

用法: replace_strings.py --app-name "Simon SmartHome" --repo-root <root>

規則(依 rebrand-inventory.md §6 + 紅隊修訂):
- 範圍: Sources/**/*.lproj/{Localizable,InfoPlist,Intents,Core,Frontend}.strings
  + AppIntentVocabulary.plist
- 全文 regex 解析 "key" = "value"; (value 可跨多行),只動 value
- 先長詞後短詞: "Home Assistant Companion" → APP_NAME, 再 "Home Assistant" → APP_NAME
- 白名單 key(整條不動): server URL placeholder(homeassistant.local)、
  Nabu Casa「Home Assistant Cloud」產品名相關
- 替換後驗證: 每條 %@/%d 等格式符數量不變; 全檔(含 plist)plutil -lint
"""
import argparse
import glob
import os
import re
import subprocess
import sys

WHITELIST_KEYS = {
    "onboarding.manual_setup.text_field.placeholder",
    "settings.connection_section.internal_base_url.placeholder",
    "settings.connection_section.external_base_url.placeholder",
    "connection.error.failed_connect.cloud.title",
    "settings.connection_section.home_assistant_cloud.title",
}
# 值裡含這些片段的整條跳過（第三方服務/技術網址）
WHITELIST_VALUE_SUBSTR = ("nabucasa.com", "homeassistant.local", "homeassistant.myhouse")

# 全文解析: "key" = "value"; value 內可含 \" 與換行（[^"\\] 天然涵蓋 \n）
# DOTALL: 讓 \\. 也吃「反斜線+換行」的續行(多行 value)
ENTRY_RE = re.compile(
    r'("(?P<key>(?:[^"\\]|\\.)*)")(\s*=\s*")(?P<val>(?:[^"\\]|\\.)*)("\s*;)',
    re.DOTALL,
)
SPEC_RE = re.compile(r'%(?:\d+\$)?[@dDuUxXoOfeEgGcCsSpaAF]')


def process_strings(path: str, app_name: str) -> int:
    for enc in ("utf-8", "utf-16"):
        try:
            with open(path, encoding=enc) as f:
                text = f.read()
            encoding = enc
            break
        except UnicodeError:
            continue
    else:
        raise SystemExit(f"無法判斷編碼: {path}")

    count = 0

    def sub(m: "re.Match[str]") -> str:
        nonlocal count
        key, val = m.group("key"), m.group("val")
        if "Home Assistant" not in val:
            return m.group(0)
        if key in WHITELIST_KEYS or any(s in val for s in WHITELIST_VALUE_SUBSTR):
            return m.group(0)
        new_val = val.replace("Home Assistant Companion", app_name).replace("Home Assistant", app_name)
        if SPEC_RE.findall(val) != SPEC_RE.findall(new_val):
            raise SystemExit(f"格式符數量改變: {path} key={key}")
        count += 1
        return m.group(1) + m.group(3) + new_val + m.group(5)

    new_text = ENTRY_RE.sub(sub, text)
    if count:
        with open(path, "w", encoding=encoding) as f:
            f.write(new_text)
    return count


def process_plist(path: str, app_name: str) -> int:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if "Home Assistant" not in text:
        return 0
    n = text.count("Home Assistant")
    new = text.replace("Home Assistant Companion", app_name).replace("Home Assistant", app_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-name", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()
    os.chdir(args.repo_root)

    total_files, total_entries = 0, 0
    targets = []
    for table in ("Localizable", "InfoPlist", "Intents", "Core", "Frontend"):
        targets += glob.glob(f"Sources/**/*.lproj/{table}.strings", recursive=True)
    plists = sorted(glob.glob("Sources/**/*.lproj/AppIntentVocabulary.plist", recursive=True))
    for path in sorted(targets):
        n = process_strings(path, args.app_name)
        if n:
            total_files += 1
            total_entries += n
    for path in plists:
        n = process_plist(path, args.app_name)
        if n:
            total_files += 1
            total_entries += n

    bad = []
    for path in sorted(set(targets)) + plists:
        r = subprocess.run(["plutil", "-lint", path], capture_output=True)
        if r.returncode != 0:
            bad.append(path)
    if bad:
        raise SystemExit(f"plutil -lint 失敗: {bad}")
    print(f"  ✓ 字串替換 {total_files} 檔 / {total_entries} 條;plutil -lint 全過(含 plist)")


if __name__ == "__main__":
    main()
