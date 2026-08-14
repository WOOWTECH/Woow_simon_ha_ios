#!/usr/bin/env python3
"""
產生單一品牌所需的全部圖形資產與色階。

被 tools/brand/rebrand.sh 呼叫，也可獨立執行：

    python3 tools/brand/gen_brand_assets.py \
        --brand-id acme --primary '#E8590C' \
        --logo tools/brand/assets/acme-logo.png --repo .

產出：
  app/src/main/res/mipmap-{5密度}/ic_launcher.png
  app/src/main/res/mipmap-{5密度}/ic_launcher_round.png
  app/src/main/res/drawable-{5密度}/ic_launcher_foreground.png
  app/src/main/res/drawable-{5密度}/app_icon_launch_screen.png
  app/src/main/res/drawable-{5密度}/ic_<brand>_branding.png
  app/src/debug/res/mipmap-{5密度}/ic_launcher{,_round}.png
  app/src/debug/res/drawable-{5密度}/ic_launcher_foreground.png
  common/src/main/res/drawable-{5密度}/ic_<brand>_logo.png
  app/src/main/ic_launcher-playstore.png
  fastlane/metadata/android/en-US/images/icon.png
並在 stdout 印出 Kotlin 色階（供 rebrand.sh 寫入 HAColors.kt）。
"""

from __future__ import annotations

import argparse
import colorsys
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 密度表
# ---------------------------------------------------------------------------
DENSITIES = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
SCALE = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}

# 原始專案各資產的 mdpi 基準尺寸（px），乘上密度倍率即為實際尺寸
BASE_SIZE = {
    "launcher": 48,          # mipmap-*/ic_launcher.png
    "foreground": 108,       # drawable-*/ic_launcher_foreground.png（adaptive 前景）
    "splash": 288,           # drawable-*/app_icon_launch_screen.png
    "branding": 48,          # drawable-*/ic_<brand>_branding.png（onboarding 品牌圖）
    "logo": 24,              # common drawable-*/ic_<brand>_logo.png（HABanner 小 logo）
}

# 原始 woowtech 色階（#6183FC 為 50）的 HSL 結構，換品牌時沿用同一組明度/彩度骨架
REF_RAMP_HEX = [
    ("05", "0D164D"), ("10", "172570"), ("20", "283B93"), ("30", "3A52B6"),
    ("40", "4D6AD9"), ("50", "6183FC"), ("60", "879FFC"), ("70", "A5B7FF"),
    ("80", "C3CFFF"), ("90", "E1E7FF"), ("95", "F0F3FF"),
]
REF_BASE_HEX = "6183FC"


# ---------------------------------------------------------------------------
# 色彩工具
# ---------------------------------------------------------------------------
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 8:  # AARRGGBB
        h = h[2:]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "".join(f"{max(0, min(255, int(round(c)))):02X}" for c in rgb)


def build_ramp(primary_hex: str) -> list[tuple[str, str]]:
    """以參考色階的 (S, L) 骨架 + 新品牌的 H，推導完整 11 階色階。"""
    pr, pg, pb = [c / 255 for c in hex_to_rgb(primary_hex)]
    p_h, p_l, p_s = colorsys.rgb_to_hls(pr, pg, pb)

    br, bg, bb = [c / 255 for c in hex_to_rgb(REF_BASE_HEX)]
    _, _, ref_base_s = colorsys.rgb_to_hls(br, bg, bb)
    # 彩度縮放比：品牌色若比參考色更灰，整條色階一起變灰
    s_ratio = (p_s / ref_base_s) if ref_base_s > 0 else 1.0

    out = []
    for step, ref_hex in REF_RAMP_HEX:
        rr, rg, rb = [c / 255 for c in hex_to_rgb(ref_hex)]
        _, ref_l, ref_s = colorsys.rgb_to_hls(rr, rg, rb)
        if step == "50":
            out.append((step, primary_hex.lstrip("#").upper()))
            continue
        new_s = max(0.0, min(1.0, ref_s * s_ratio))
        r, g, b = colorsys.hls_to_rgb(p_h, ref_l, new_s)
        out.append((step, rgb_to_hex((r * 255, g * 255, b * 255))))
    return out


def darken(primary_hex: str, factor: float = 0.80) -> str:
    r, g, b = [c / 255 for c in hex_to_rgb(primary_hex)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, l * factor), s)
    return rgb_to_hex((r * 255, g * 255, b * 255))


def relative_luminance(rgb) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------------------------------------------------------------------------
# 圖形工具
# ---------------------------------------------------------------------------
def load_logo(path: str | None, primary_hex: str, brand_id: str) -> Image.Image:
    """載入 logo；SVG 會先用 rsvg-convert / inkscape / ImageMagick 轉成 PNG。
    未提供時產生首字母佔位圖，讓整條流程在素材到位前就能先跑通。"""
    if not path:
        return placeholder_logo(primary_hex, brand_id)
    if not os.path.exists(path):
        print(f"[warn] 找不到 logo：{path}，改用佔位圖", file=sys.stderr)
        return placeholder_logo(primary_hex, brand_id)

    if path.lower().endswith(".svg"):
        tmp = tempfile.mktemp(suffix=".png")
        for cmd in (
            ["rsvg-convert", "-w", "1024", "-h", "1024", path, "-o", tmp],
            ["inkscape", path, "--export-type=png", "--export-width=1024", f"--export-filename={tmp}"],
            ["convert", "-background", "none", "-density", "600", "-resize", "1024x1024", path, tmp],
        ):
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                if os.path.exists(tmp):
                    return Image.open(tmp).convert("RGBA")
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        print("[warn] SVG 轉檔失敗（需 rsvg-convert / inkscape / ImageMagick），改用佔位圖", file=sys.stderr)
        return placeholder_logo(primary_hex, brand_id)

    return Image.open(path).convert("RGBA")


def placeholder_logo(primary_hex: str, brand_id: str) -> Image.Image:
    """白色圓底 + 品牌主色首字母，僅供流程驗證，正式版務必換成真 logo。"""
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, size, size), fill=(255, 255, 255, 255))
    letter = (brand_id[:1] or "A").upper()
    font = None
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if os.path.exists(p):
            font = ImageFont.truetype(p, int(size * 0.55))
            break
    if font is None:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), letter, font=font)
    d.text(
        ((size - (bbox[2] - bbox[0])) / 2 - bbox[0], (size - (bbox[3] - bbox[1])) / 2 - bbox[1]),
        letter, font=font, fill=hex_to_rgb(primary_hex) + (255,),
    )
    return img


def fit(logo: Image.Image, box: int, scale: float) -> Image.Image:
    """把 logo 等比縮到 box*scale 內，置中貼在透明的 box×box 畫布上。"""
    target = max(1, int(box * scale))
    w, h = logo.size
    ratio = min(target / w, target / h)
    resized = logo.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)
    canvas = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    canvas.paste(resized, ((box - resized.width) // 2, (box - resized.height) // 2), resized)
    return canvas


def circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4, size * 4), fill=255)
    return m.resize((size, size), Image.LANCZOS)


def rounded_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        (0, 0, size * 4, size * 4), radius=int(size * 4 * radius_ratio), fill=255
    )
    return m.resize((size, size), Image.LANCZOS)


def legacy_icon(logo: Image.Image, size: int, bg: tuple[int, int, int], round_: bool, scale: float) -> Image.Image:
    """API 26 以下用的傳統 icon：品牌底色 + 置中 logo + 圓形/圓角遮罩。"""
    base = Image.new("RGBA", (size, size), bg + (255,))
    base.alpha_composite(fit(logo, size, scale * 1.05))
    mask = circle_mask(size) if round_ else rounded_mask(size)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def write(img: Image.Image, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"  ✓ {path}  {img.size[0]}x{img.size[1]}")


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand-id", required=True)
    ap.add_argument("--primary", required=True, help="品牌主色 #RRGGBB")
    ap.add_argument("--logo", default="", help="正方形去背 logo（PNG/SVG）")
    ap.add_argument("--logo-scale", type=float, default=0.60)
    ap.add_argument("--launcher-bg", default="", help="adaptive icon 背景色，預設同主色")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--emit-ramp", default="", help="把 Kotlin 色階寫到這個檔案")
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    primary = a.primary if a.primary.startswith("#") else "#" + a.primary
    bg_hex = a.launcher_bg or primary
    bg = hex_to_rgb(bg_hex)
    logo = load_logo(a.logo or None, primary, a.brand_id)

    def p(*parts: str) -> str:
        return os.path.join(repo, *parts)

    print(f"[assets] 品牌={a.brand_id} 主色={primary} 底色={bg_hex}")

    for d in DENSITIES:
        k = SCALE[d]

        # 1) adaptive icon 前景（透明底，logo 置於安全區內）
        fg = fit(logo, int(BASE_SIZE["foreground"] * k), a.logo_scale)
        write(fg, p("app/src/main/res", f"drawable-{d}", "ic_launcher_foreground.png"))
        write(fg, p("app/src/debug/res", f"drawable-{d}", "ic_launcher_foreground.png"))

        # 2) 傳統 launcher icon（API < 26）
        sz = int(BASE_SIZE["launcher"] * k)
        write(legacy_icon(logo, sz, bg, False, a.logo_scale), p("app/src/main/res", f"mipmap-{d}", "ic_launcher.png"))
        write(legacy_icon(logo, sz, bg, True, a.logo_scale), p("app/src/main/res", f"mipmap-{d}", "ic_launcher_round.png"))
        write(legacy_icon(logo, sz, bg, False, a.logo_scale), p("app/src/debug/res", f"mipmap-{d}", "ic_launcher.png"))
        write(legacy_icon(logo, sz, bg, True, a.logo_scale), p("app/src/debug/res", f"mipmap-{d}", "ic_launcher_round.png"))

        # 3) 啟動畫面圖示（Android 12 splash 會再套自己的遮罩，故留大量留白）
        write(fit(logo, int(BASE_SIZE["splash"] * k), 0.42),
              p("app/src/main/res", f"drawable-{d}", "app_icon_launch_screen.png"))

        # 4) onboarding 品牌圖 + HABanner 小 logo（不加底色，畫面自己有背景）
        write(fit(logo, int(BASE_SIZE["branding"] * k), 1.0),
              p("app/src/main/res", f"drawable-{d}", f"ic_{a.brand_id}_branding.png"))
        write(fit(logo, int(BASE_SIZE["logo"] * k), 1.0),
              p("common/src/main/res", f"drawable-{d}", f"ic_{a.brand_id}_logo.png"))

    # 5) Play Store 512x512（不可透明）
    store = Image.new("RGBA", (512, 512), bg + (255,))
    store.alpha_composite(fit(logo, 512, a.logo_scale))
    write(store.convert("RGB").convert("RGBA"), p("app/src/main/ic_launcher-playstore.png"))
    fastlane_icon = p("fastlane/metadata/android/en-US/images/icon.png")
    if os.path.isdir(os.path.dirname(fastlane_icon)):
        write(store.convert("RGBA"), fastlane_icon)

    # 6) 色階 + 對比檢查
    ramp = build_ramp(primary)
    lum = relative_luminance(hex_to_rgb(primary))
    contrast_white = (1.05) / (lum + 0.05)
    print(f"[color] 主色對白字對比 = {contrast_white:.2f}:1 "
          f"({'OK（白字可讀）' if contrast_white >= 4.5 else '⚠ 低於 WCAG AA 4.5:1，主色上的白字會不好讀'})")

    if a.emit_ramp:
        with open(a.emit_ramp, "w") as f:
            for step, hexv in ramp:
                f.write(f"{step} {hexv}\n")
            f.write(f"DARK {darken(primary)}\n")
        print(f"  ✓ {a.emit_ramp}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
