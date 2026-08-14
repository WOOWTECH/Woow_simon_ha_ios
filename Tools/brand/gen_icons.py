#!/usr/bin/env python3
"""品牌 icon / logo 資產產生器。

用法: gen_icons.py --logo <1024.png> --bg RRGGBB --repo-root <root>

- 所有 *.appiconset(AppIcon / .dev / .beta / WatchIcon* / AlternateIcons/*):
  依 Contents.json 逐項以壓平(不透明)品牌 icon 覆寫,尺寸 = size × scale
- 品牌 logo imagesets(透明背景,1024px):launchScreen-logo、Logo、
  logo-horizontal-text、casita、casita-dark、statusItemIcon、RoundLogo、
  TemplateLogo、Complication 下的 imageset
- PDF 項目改為 PNG 並改寫 Contents.json filename
- 保留(第三方標誌): improv-logo、thread、ha-cloud-logo
渲染引擎: Tools/brand/icon_tool.swift(CoreGraphics,無外部依賴)
"""
import argparse
import glob
import json
import os
import subprocess
import sys

KEEP = {"improv-logo.imageset", "thread.imageset", "ha-cloud-logo.imageset"}
LOGO_IMAGESETS = {
    "launchScreen-logo.imageset", "Logo.imageset", "logo-horizontal-text.imageset",
    "casita.imageset", "casita-dark.imageset", "statusItemIcon.imageset",
    "RoundLogo.imageset", "TemplateLogo.imageset",
}
TOOL = "Tools/brand/icon_tool.swift"
_cache: dict = {}


def render(logo: str, bg: str, size: int, out: str) -> None:
    key = (bg, size)
    if key in _cache:
        subprocess.run(["cp", _cache[key], out], check=True)
        return
    subprocess.run(["swift", TOOL, logo, bg, str(size), out], check=True, capture_output=True)
    _cache[key] = out


def px(entry: dict) -> int:
    size = entry.get("size")
    scale = entry.get("scale", "1x")
    if not size:
        return 1024
    w = float(size.split("x")[0])
    s = int(scale.rstrip("x"))
    return int(w * s)


def do_iconset(path: str, logo: str, bg: str) -> int:
    cj = os.path.join(path, "Contents.json")
    with open(cj) as f:
        data = json.load(f)
    n = 0
    for entry in data.get("images", []):
        fn = entry.get("filename")
        if not fn:
            continue
        target = os.path.join(path, fn)
        if fn.lower().endswith(".pdf"):
            newfn = os.path.splitext(fn)[0] + ".png"
            entry["filename"] = newfn
            if os.path.exists(target):
                os.remove(target)
            target = os.path.join(path, newfn)
        render(logo, bg, px(entry), target)
        n += 1
    # PDF→PNG 後向量屬性失效
    if data.get("properties", {}).get("preserves-vector-representation"):
        del data["properties"]["preserves-vector-representation"]
    with open(cj, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logo", required=True)
    ap.add_argument("--bg", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()
    os.chdir(args.repo_root)

    files = 0
    sets = 0
    # 1) 全部 appiconset(壓平不透明)
    for path in sorted(glob.glob("Sources/**/*.appiconset", recursive=True) +
                       glob.glob("WatchApp/**/*.appiconset", recursive=True)):
        files += do_iconset(path, args.logo, args.bg)
        sets += 1
    # 2) 品牌 logo imagesets(保留透明度)
    for path in sorted(glob.glob("Sources/**/*.imageset", recursive=True)):
        base = os.path.basename(path)
        if base in KEEP:
            continue
        if base in LOGO_IMAGESETS or "/Complication.complicationset/" in path:
            files += do_iconset(path, args.logo, "none")
            sets += 1
    print(f"  ✓ 資產覆寫 {sets} 組 / {files} 檔(快取渲染 {len(_cache)} 種尺寸)")


if __name__ == "__main__":
    main()
