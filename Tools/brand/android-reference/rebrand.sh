#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 白牌換裝腳本 — 以 main 為基準，把整個專案改成指定品牌
#
#   bash tools/brand/rebrand.sh tools/brand/acme.conf
#
# 建議流程：
#   git checkout main && git pull
#   git checkout -b brand/acme
#   bash tools/brand/rebrand.sh tools/brand/acme.conf
#   git add -A && git commit -m "Rebrand to ACME Home"
#
# 腳本設計為「對 main 的乾淨 checkout 執行一次」。在已換裝過的分支上重跑不會有效果
# （關鍵字已被換掉），要改品牌設定請從 main 重開分支再跑。
# ---------------------------------------------------------------------------
set -euo pipefail

CONF="${1:-}"
if [[ -z "$CONF" || ! -f "$CONF" ]]; then
  echo "用法: bash tools/brand/rebrand.sh <品牌設定檔>" >&2
  echo "範本: tools/brand/brand.conf.example" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$CONF"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

: "${BRAND_ID:?brand.conf 缺少 BRAND_ID}"
: "${APP_NAME:?brand.conf 缺少 APP_NAME}"
: "${APPLICATION_ID:?brand.conf 缺少 APPLICATION_ID}"
: "${BRAND_HOST:?brand.conf 缺少 BRAND_HOST}"
: "${PRIMARY_COLOR:?brand.conf 缺少 PRIMARY_COLOR}"
URL_SCHEME="${URL_SCHEME:-}"
LOGO_SRC="${LOGO_SRC:-}"
LOGO_SCALE="${LOGO_SCALE:-0.60}"
LAUNCHER_BG="${LAUNCHER_BG:-}"
HA_APP_ID="${HA_APP_ID:-$APPLICATION_ID}"
HA_APP_NAME="${HA_APP_NAME:-$APP_NAME}"
FASTLANE_PACKAGE="${FASTLANE_PACKAGE:-$APPLICATION_ID}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:-}"
# 文案中單獨出現的品牌名（預設取 APP_NAME 的第一個詞，例如 "ACME Home" → "ACME"）
BRAND_DISPLAY="${BRAND_DISPLAY:-${APP_NAME%% *}}"

OLD_HOST="aiot.woowtech.io"
OLD_APPID="com.woowtech.home"
OLD_BRAND="woowtech"
OLD_APP_NAME="woowtech Home"
NAMESPACE="io.homeassistant.companion.android"

say() { printf '\n\033[1;36m▸ %s\033[0m\n' "$*"; }
ok()  { printf '  ✓ %s\n' "$*"; }

# 只在原始碼與設定檔上做取代：避開 .git、build 產物、二進位檔，
# 並過濾掉符號連結（CLAUDE.md / GEMINI.md / .junie/guidelines.md 都是 symlink，
# 其中 .junie/guidelines.md 是壞的連結；sed -i 也會把 symlink 變成一般檔案）
src_files() {
  git ls-files -z -- \
    '*.kt' '*.kts' '*.xml' '*.md' '*.json' '*.properties' '*.yml' '*.yaml' '*.txt' '*.pro' 'fastlane/Appfile' \
    | while IFS= read -r -d '' f; do
        if [[ -f "$f" && ! -L "$f" ]]; then printf '%s\0' "$f"; fi
      done
}

say "品牌換裝：$OLD_APP_NAME → $APP_NAME"
echo "  applicationId : $OLD_APPID → $APPLICATION_ID"
echo "  伺服器網域    : $OLD_HOST → $BRAND_HOST"
echo "  主色          : #6183FC → $PRIMARY_COLOR"
echo "  URL scheme    : homeassistant → ${URL_SCHEME:-（不變）}"

# ---------------------------------------------------------------------------
say "1/12 產生色階與圖形資產"
RAMP_FILE="$(mktemp)"
python3 tools/brand/gen_brand_assets.py \
  --brand-id "$BRAND_ID" \
  --primary "$PRIMARY_COLOR" \
  --logo "$LOGO_SRC" \
  --logo-scale "$LOGO_SCALE" \
  --launcher-bg "$LAUNCHER_BG" \
  --repo "$REPO_ROOT" \
  --emit-ramp "$RAMP_FILE"

declare -A RAMP
while read -r step hexv; do RAMP["$step"]="$hexv"; done < "$RAMP_FILE"
rm -f "$RAMP_FILE"
PRIMARY_HEX="${PRIMARY_COLOR#\#}"
PRIMARY_HEX="${PRIMARY_HEX^^}"
DARK_HEX="${RAMP[DARK]}"

# ---------------------------------------------------------------------------
say "2/12 替換品牌色（colors.xml / Compose 主題 / vector drawable）"
# 舊色階 → 新色階。這些 hex 在專案中專屬於品牌色，全域取代是安全的。
declare -A COLOR_MAP=(
  ["6183FC"]="$PRIMARY_HEX"
  ["4A6BD9"]="$DARK_HEX"
  ["0D164D"]="${RAMP[05]}" ["172570"]="${RAMP[10]}" ["283B93"]="${RAMP[20]}"
  ["3A52B6"]="${RAMP[30]}" ["4D6AD9"]="${RAMP[40]}" ["879FFC"]="${RAMP[60]}"
  ["A5B7FF"]="${RAMP[70]}" ["C3CFFF"]="${RAMP[80]}" ["E1E7FF"]="${RAMP[90]}"
  ["F0F3FF"]="${RAMP[95]}"
)
for old in "${!COLOR_MAP[@]}"; do
  new="${COLOR_MAP[$old]}"
  src_files | xargs -0 sed -i "s/${old}/${new}/g; s/${old,,}/${new}/g"
done
ok "11 階色階 + colorPrimaryDark 已替換"

# 更新註解中的品牌色說明，避免留下 woowtech 字樣
src_files | xargs -0 sed -i "s|// woowtech Brand Blue|// ${APP_NAME} Brand Color|g; s|woowtech Brand Blue (#[0-9A-Fa-f]\{6\})|${APP_NAME} brand color (${PRIMARY_COLOR})|g"

# ---------------------------------------------------------------------------
say "3/12 替換 applicationId"
sed -i "s|private const val APPLICATION_ID = \"${OLD_APPID}\"|private const val APPLICATION_ID = \"${APPLICATION_ID}\"|" \
  build-logic/convention/src/main/kotlin/AndroidApplicationConventionPlugin.kt
grep -q "\"${APPLICATION_ID}\"" build-logic/convention/src/main/kotlin/AndroidApplicationConventionPlugin.kt \
  || { echo "!! applicationId 替換失敗" >&2; exit 1; }
ok "AndroidApplicationConventionPlugin.kt"

# ---------------------------------------------------------------------------
say "4/12 替換 App 名稱"
for f in common/src/main/res/values/strings.xml common/src/main/res/values-zh-rTW/strings.xml; do
  sed -i "s|<string name=\"app_name\">${OLD_APP_NAME}</string>|<string name=\"app_name\">${APP_NAME}</string>|" "$f"
  ok "$f"
done
# 歡迎頁大標是「woowtech\nHome」的兩行排版，換成品牌名的兩行版本
WELCOME_TITLE="${APP_NAME// /\\\\n}"
src_files | xargs -0 sed -i "s|woowtech\\\\nHome|${WELCOME_TITLE}|g"

# 其餘含品牌名的文案（公司名、隱私權連結說明、圖示 content description、版權標示）
src_files | xargs -0 sed -i "s|woowtech Smart Home Solutions|${APP_NAME}|g; s|${OLD_APP_NAME}|${APP_NAME}|g"

# 資源 key 也帶了品牌名（woowtech_company），資源名稱只能小寫英數底線
src_files | xargs -0 sed -i "s|woowtech_company|${BRAND_ID}_company|g"
ok "app_name / 歡迎頁標題 / 公司名 / 資源 key"

# ---------------------------------------------------------------------------
say "5/12 替換伺服器網域（deep link / 推播 / 文件連結 / NFC tag）"
src_files | xargs -0 sed -i "s|${OLD_HOST}|${BRAND_HOST}|g"
ok "所有 ${OLD_HOST} → ${BRAND_HOST}"
grep -n "$BRAND_HOST" gradle.properties | sed 's/^/  /'

# ---------------------------------------------------------------------------
say "6/12 更名品牌圖檔資源"
git rm -q --cached "app/src/main/res/drawable-"*"/ic_${OLD_BRAND}_branding.png" 2>/dev/null || true
rm -f app/src/main/res/drawable-*/ic_${OLD_BRAND}_branding.png
git rm -q --cached "common/src/main/res/drawable-"*"/ic_${OLD_BRAND}_logo.png" 2>/dev/null || true
rm -f common/src/main/res/drawable-*/ic_${OLD_BRAND}_logo.png
src_files | xargs -0 sed -i "s|ic_${OLD_BRAND}_branding|ic_${BRAND_ID}_branding|g; s|ic_${OLD_BRAND}_logo|ic_${BRAND_ID}_logo|g"
ok "ic_${OLD_BRAND}_branding → ic_${BRAND_ID}_branding（6 處引用）"
ok "ic_${OLD_BRAND}_logo → ic_${BRAND_ID}_logo（1 處引用）"
# 未被任何 XML 引用的殘留檔案
rm -f app/src/main/res/drawable/ic_home_assistant_branding.xml
rm -f app/src/main/res/drawable-*/ic_launcher_foreground_round.png
ok "移除孤兒資產 ic_home_assistant_branding.xml / ic_launcher_foreground_round.png"

# 掃掉剩下的裸 woowtech：設計系統註解（HASize / HAGlassmorphism / HAButtons…）、
# 圖示 content description、zh-rTW 文案。務必排在網域與檔名替換之後，
# 否則會先把 aiot.woowtech.io 的 woowtech 也吃掉。
src_files | xargs -0 sed -i "s|woowtech|${BRAND_DISPLAY}|g; s|WoowTech|${BRAND_DISPLAY}|g; s|Woowtech|${BRAND_DISPLAY}|g"
ok "設計系統註解與其餘 woowtech 字樣 → ${BRAND_DISPLAY}"

# ---------------------------------------------------------------------------
if [[ -n "$URL_SCHEME" ]]; then
  say "7/12 替換自訂 URL scheme（多品牌並存必要）"
  src_files | xargs -0 sed -i \
    "s|android:scheme=\"homeassistant\"|android:scheme=\"${URL_SCHEME}\"|g; \
     s|AUTH_CALLBACK_SCHEME = \"homeassistant\"|AUTH_CALLBACK_SCHEME = \"${URL_SCHEME}\"|; \
     s|DEEP_LINK_SCHEME = \"homeassistant\"|DEEP_LINK_SCHEME = \"${URL_SCHEME}\"|; \
     s|homeassistant://|${URL_SCHEME}://|g; \
     s|it.scheme == \"homeassistant\"|it.scheme == \"${URL_SCHEME}\"|g; \
     s|scheme = \"homeassistant\"|scheme = \"${URL_SCHEME}\"|g"
  ok "manifest scheme + AUTH_CALLBACK_SCHEME + DEEP_LINK_SCHEME + 測試"
else
  say "7/12 跳過 URL scheme（設定為沿用 homeassistant）"
  echo "  ⚠ 與其他品牌 App 同時安裝時，homeassistant:// 連結會跳出選擇對話框"
fi

# ---------------------------------------------------------------------------
say "8/12 taskAffinity 改用 \${applicationId}（避免多品牌 task 混用）"
src_files | xargs -0 sed -i \
  "s|android:taskAffinity=\"${NAMESPACE}.controls\"|android:taskAffinity=\"\${applicationId}.controls\"|g; \
   s|android:taskAffinity=\"${NAMESPACE}.assist\"|android:taskAffinity=\"\${applicationId}.assist\"|g"
ok "app + automotive manifest"

# ---------------------------------------------------------------------------
say "9/12 修正 main 分支既有的 package name 缺陷"
# (a) PowerSensorManager 硬編舊 package 做「是否忽略電池最佳化」查詢，rebrand 後永遠查不到自己。
#     :common 是 library module，BuildConfig 沒有 APPLICATION_ID，因此改用 runtime 的 context.packageName。
PSM=common/src/main/kotlin/io/homeassistant/companion/android/common/sensors/PowerSensorManager.kt
sed -i "/private const val PACKAGE_NAME = \"${NAMESPACE}\"/d" "$PSM"
sed -i "s|^\( *\)PACKAGE_NAME,$|\1context.packageName,|" "$PSM"
if grep -q "PACKAGE_NAME" "$PSM"; then
  echo "  ⚠ $PSM 仍有 PACKAGE_NAME 參照，請手動檢查"
else
  ok "PowerSensorManager 改用 context.packageName"
fi

# (b) debug 捷徑指向舊 package，長按圖示的 DevPlayground 捷徑目前是壞的
sed -i "s|android:targetPackage=\"${NAMESPACE}.debug\"|android:targetPackage=\"${APPLICATION_ID}.debug\"|" \
  app/src/debug/res/xml/shortcuts.xml
ok "app/src/debug/res/xml/shortcuts.xml"

# (c) fastlane 上架 package
sed -i "s|package_name(\"${NAMESPACE}\")|package_name(\"${FASTLANE_PACKAGE}\")|" fastlane/Appfile
ok "fastlane/Appfile"

# (d) 回報給 HA 伺服器的 App 身分
sed -i "s|private const val APP_ID = \"${NAMESPACE}\"|private const val APP_ID = \"${HA_APP_ID}\"|; \
        s|private const val APP_NAME = \"Home Assistant\"|private const val APP_NAME = \"${HA_APP_NAME}\"|" \
  common/src/main/kotlin/io/homeassistant/companion/android/common/data/integration/impl/IntegrationRepositoryImpl.kt
ok "IntegrationRepositoryImpl APP_ID / APP_NAME"

# (e) OAuth client_id（預設不動：HA 伺服器會驗證 client_id 可達性，改錯會登不進去）
if [[ -n "$OAUTH_CLIENT_ID" ]]; then
  sed -i "s|const val CLIENT_ID = \"https://home-assistant.io/android\"|const val CLIENT_ID = \"${OAUTH_CLIENT_ID}\"|" \
    common/src/main/kotlin/io/homeassistant/companion/android/common/data/authentication/impl/AuthenticationService.kt
  ok "AuthenticationService.CLIENT_ID = $OAUTH_CLIENT_ID"
else
  echo "  ⓘ OAuth CLIENT_ID 保持 https://home-assistant.io/android（未設定 OAUTH_CLIENT_ID）"
fi

# ---------------------------------------------------------------------------
say "10/12 更新 mock google-services.json（debug/minimal 建置必要）"
python3 - "$APPLICATION_ID" <<'PY'
import json, sys, pathlib
appid = sys.argv[1]
p = pathlib.Path(".github/mock-google-services.json")
data = json.loads(p.read_text())
wanted = [appid, f"{appid}.debug", f"{appid}.minimal", f"{appid}.minimal.debug"]
have = {c["client_info"]["android_client_info"]["package_name"] for c in data["client"]}
template = data["client"][0]
added = 0
for name in wanted:
    if name in have:
        continue
    c = json.loads(json.dumps(template))
    c["client_info"]["android_client_info"]["package_name"] = name
    c["client_info"]["mobilesdk_app_id"] = f"1:000000000000:android:{abs(hash(name)) % (10**16):016x}"
    data["client"].append(c)
    added += 1
p.write_text(json.dumps(data, indent=2) + "\n")
print(f"  ✓ 新增 {added} 個 package：{', '.join(wanted)}")
PY

# ---------------------------------------------------------------------------
say "11/12 重寫 README"
cat > README.md <<EOF
# ${APP_NAME}

${APP_NAME} is the official Android smart home control app.

## Overview

${APP_NAME} connects to your smart home server at \`https://${BRAND_HOST}\`.
It provides local control and privacy-first home automation, built on Home Assistant open source technology.

## Features

- **Remote access** — control your smart home from anywhere
- **Local control** — connect directly to the home server on the same network
- **Sensors** — background sensor collection for automation triggers
- **Notifications** — push notifications for alerts and automations
- **Widgets** — home screen widgets for quick device control
- **Wear OS** — smartwatch support
- **Android Auto** — in-car control

## Brand

| Property | Value |
|---|---|
| Primary color | ${PRIMARY_COLOR} |
| App name | ${APP_NAME} |
| Package ID | ${APPLICATION_ID} |
| Server URL | https://${BRAND_HOST} |
| URL scheme | ${URL_SCHEME:-homeassistant}:// |

## Build

Requirements: JDK 17+, Android SDK, Gradle.

\`\`\`bash
./gradlew assembleFullDebug     # debug
./gradlew assembleFullRelease   # release
\`\`\`

Output: \`app/build/outputs/apk/full/debug/app-full-debug.apk\`

## Rebranding

This branch was generated from \`main\` with:

\`\`\`bash
git checkout -b brand/${BRAND_ID} main
bash tools/brand/rebrand.sh tools/brand/${BRAND_ID}.conf
\`\`\`

See \`docs/brand/WHITE_LABEL_SOP.md\`.

## License

Based on Home Assistant Companion for Android (Apache 2.0).

---

**${APP_NAME}**
EOF
rm -f README.zh-TW.md
ok "README.md"

# ---------------------------------------------------------------------------
say "12/12 檢查殘留"
LEFT=$(git grep -In -i -e "$OLD_BRAND" -e "$OLD_HOST" -e "$OLD_APPID" -- \
  ':!tools/brand' ':!docs/brand' ':!docs/plans' ':!*lint-baseline.xml' 2>/dev/null | wc -l)
if [[ "$LEFT" -gt 0 ]]; then
  echo "  ⚠ 仍有 $LEFT 行含舊品牌關鍵字（不含 tools/docs/lint-baseline）："
  git grep -In -i -e "$OLD_BRAND" -e "$OLD_HOST" -e "$OLD_APPID" -- \
    ':!tools/brand' ':!docs/brand' ':!docs/plans' ':!*lint-baseline.xml' | head -20 | sed 's/^/    /'
else
  ok "無殘留"
fi

echo
printf '\033[1;32m換裝完成。\033[0m 接下來：\n'
cat <<EOF
  1. 檢視 git diff，特別是 app/src/main/res/mipmap-* 的 icon 是否正確
  2. ./gradlew assembleFullDebug 驗證編譯
  3. ./gradlew ktlintFormat && ./gradlew lint（lint-baseline 可能需重生：./gradlew updateLintBaseline）
  4. 準備該品牌的 google-services.json / keystore / assetlinks.json（見 docs/brand/WHITE_LABEL_SOP.md）
  5. git add -A && git commit -m "Rebrand to ${APP_NAME}"
EOF
