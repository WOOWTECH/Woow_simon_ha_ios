#!/usr/bin/env python3
"""品牌 icon / logo 資產產生器。

用法: gen_icons.py --logo <1024.png> --bg RRGGBB --repo-root <root>

- 所有 *.appiconset(AppIcon / .dev / .beta / WatchIcon* / AlternateIcons/*):
  依 Contents.json 逐項以壓平(不透明)品牌 icon 覆寫,尺寸 = size × scale
- AlternateIconsPreview 的 icon-*.imageset 一併覆寫(不透明,否則 picker 殘留 HA 預覽)
- 品牌 logo imagesets(透明背景,1024px):launchScreen-logo、Logo、logo-in-circle、
  logo-horizontal-text、casita、casita-dark、statusItemIcon、RoundLogo、
  TemplateLogo、Complication 下的 imageset
- 非 PNG 項目(pdf/jpg)改為 PNG 並改寫 Contents.json filename
- 保留(第三方標誌): improv-logo、thread、ha-cloud-logo
- 已知降級(記錄於 inventory): dark/tinted appearance 一律同一張壓平圖
渲染引擎: Tools/brand/icon_tool.swift(CoreGraphics,無外部依賴)
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

KEEP = {"improv-logo.imageset", "thread.imageset", "ha-cloud-logo.imageset"}
LOGO_IMAGESETS = {
    "launchScreen-logo.imageset", "Logo.imageset", "logo-in-circle.imageset",
    "logo-horizontal-text.imageset", "casita.imageset", "casita-dark.imageset",
    "statusItemIcon.imageset", "RoundLogo.imageset", "TemplateLogo.imageset",
}
TOOL = "Tools/brand/icon_tool.swift"
_cache_dir = tempfile.mkdtemp(prefix="brandicons-")
_cache: dict = {}


def render(logo: str, bg: str, size: int, out: str) -> None:
    """每種 (bg,size) 只渲染一次到快取目錄,再複製到目的地(絕不 cp 同檔)。"""
    key = (bg, size)
    if key not in _cache:
        cached = os.path.join(_cache_dir, f"{bg}-{size}.png")
        subprocess.run(["swift", TOOL, logo, bg, str(size), cached],
                       check=True, capture_output=True)
        _cache[key] = cached
    if os.path.abspath(_cache[key]) != os.path.abspath(out):
        shutil.copyfile(_cache[key], out)


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
    seen_out = set()
    for entry in data.get("images", []):
        fn = entry.get("filename")
        if not fn:
            continue
        stem, ext = os.path.splitext(fn)
        if ext.lower() != ".png":
            newfn = stem + ".png"
            old = os.path.join(path, fn)
            if os.path.exists(old):
                os.remove(old)
            entry["filename"] = newfn
            fn = newfn
        target = os.path.join(path, fn)
        if target in seen_out:
            continue  # 同檔被多個 appearance 條目引用,渲染一次即可
        seen_out.add(target)
        render(logo, bg, px(entry), target)
        n += 1
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
    # 2) icon picker 預覽圖(不透明)
    for path in sorted(glob.glob("Sources/**/AlternateIconsPreview/*.imageset", recursive=True)):
        files += do_iconset(path, args.logo, args.bg)
        sets += 1
    # 3) 品牌 logo imagesets(保留透明度)
    for path in sorted(glob.glob("Sources/**/*.imageset", recursive=True)):
        base = os.path.basename(path)
        if base in KEEP or "/AlternateIconsPreview/" in path:
            continue
        if base in LOGO_IMAGESETS or "/Complication.complicationset/" in path:
            files += do_iconset(path, args.logo, "none")
            sets += 1
    if sets == 0:
        raise SystemExit("沒有命中任何 iconset — glob 失效?")
    print(f"  ✓ 資產覆寫 {sets} 組 / {files} 檔(渲染 {len(_cache)} 種尺寸)")


if __name__ == "__main__":
    main()
