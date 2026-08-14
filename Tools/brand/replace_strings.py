#!/usr/bin/env python3
"""本地化字串品牌替換 — 只動 value、白名單保護、格式符驗證。

用法: replace_strings.py --app-name "Simon SmartHome" --repo-root <root>

規則(依 rebrand-inventory.md §6):
- 範圍: Sources/**/*.lproj/{Localizable,InfoPlist,Intents}.strings + AppIntentVocabulary.plist
- 先長詞後短詞: "Home Assistant Companion" → APP_NAME, 再 "Home Assistant" → APP_NAME
- 白名單 key(整條不動): server URL placeholder(homeassistant.local)、
  Nabu Casa「Home Assistant Cloud」產品名相關
- Intents.strings 的 key 是 Xcode hash,只動 value(本腳本天生只動 value)
- 替換後驗證: 每條 %@/%d 等格式符數量不變; 全檔 plutil -lint
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

LINE_RE = re.compile(r'^(\s*"(?P<key>(?:[^"\\]|\\.)*)"\s*=\s*")(?P<val>(?:[^"\\]|\\.)*)("\s*;.*)$')
SPEC_RE = re.compile(r'%(?:\d+\$)?[@dDuUxXoOfeEgGcCsSpaAF]')


def replace_value(val: str, app_name: str) -> str:
    val = val.replace("Home Assistant Companion", app_name)
    val = val.replace("Home Assistant", app_name)
    return val


def process_strings(path: str, app_name: str) -> int:
    for enc in ("utf-8", "utf-16"):
        try:
            with open(path, encoding=enc) as f:
                lines = f.readlines()
            encoding = enc
            break
        except UnicodeError:
            continue
    else:
        raise SystemExit(f"無法判斷編碼: {path}")

    changed = 0
    out = []
    for line in lines:
        m = LINE_RE.match(line)
        if not m or "Home Assistant" not in m.group("val"):
            out.append(line)
            continue
        key, val = m.group("key"), m.group("val")
        if key in WHITELIST_KEYS or any(s in val for s in WHITELIST_VALUE_SUBSTR):
            out.append(line)
            continue
        new_val = replace_value(val, app_name)
        if SPEC_RE.findall(val) != SPEC_RE.findall(new_val):
            raise SystemExit(f"格式符數量改變: {path} key={key}")
        out.append(m.group(1) + new_val + m.group(4) + ("\n" if not line.endswith("\n") else ""))
        changed += 1
    if changed:
        with open(path, "w", encoding=encoding) as f:
            f.writelines(out)
    return changed


def process_plist(path: str, app_name: str) -> int:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if "Home Assistant" not in text:
        return 0
    new = text.replace("Home Assistant Companion", app_name).replace("Home Assistant", app_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return text.count("Home Assistant")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-name", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()
    os.chdir(args.repo_root)

    total_files, total_lines = 0, 0
    targets = []
    for table in ("Localizable", "InfoPlist", "Intents"):
        targets += glob.glob(f"Sources/**/*.lproj/{table}.strings", recursive=True)
    for path in sorted(targets):
        n = process_strings(path, args.app_name)
        if n:
            total_files += 1
            total_lines += n
    for path in sorted(glob.glob("Sources/**/*.lproj/AppIntentVocabulary.plist", recursive=True)):
        n = process_plist(path, args.app_name)
        if n:
            total_files += 1
            total_lines += n

    # 全量 lint
    bad = []
    for path in sorted(set(targets)):
        r = subprocess.run(["plutil", "-lint", path], capture_output=True)
        if r.returncode != 0:
            bad.append(path)
    if bad:
        raise SystemExit(f"plutil -lint 失敗: {bad}")
    print(f"  ✓ 字串替換 {total_files} 檔 / {total_lines} 條;plutil -lint 全過")


if __name__ == "__main__":
    main()
