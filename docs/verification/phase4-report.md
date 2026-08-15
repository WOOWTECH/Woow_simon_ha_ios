# Phase 4 模擬器驗證報告(2026-08-15)

環境:iPhone 17 Simulator(iOS 26.5)/ Debug build(`com.simon.home.dev`,dev 精簡 entitlements)
伺服器:`https://woowtech-ha.woowtech.io`(E&L house)

| # | 項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | Onboarding 品牌畫面 | ✅ simon icon、「Simon SmartHome App」、#0060A6 按鈕,無 HA 殘留 | `phase4-simon-onboarding.png` |
| 2 | 連線 + OAuth + 登入 | ✅ 使用者於 Simulator 手動完成:輸入 server → OAuth 授權頁 → admin 登入 → **redirect 回 app 成功**(client_id 頁 + `simonhome://auth-callback` 全鏈路驗證) | `phase4-settings-root.png`(Servers: E&L house / admin) |
| 3 | Dashboard WebView | ✅ 總覽載入、真實實體、捲動流暢、WebSocket 即時狀態更新(燈數 6→8 實時跳動) | `phase4-deeplink-dashboard.png` |
| 4 | 深連結 | ✅ `simctl openurl simonhome://navigate/lovelace/0` → 系統對話框顯示「Simon SmartHome Δ」→ app 解析 `/lovelace/0` → 導向總覽 | 同上 |
| 5 | 原生 Settings 品牌 | ✅ Settings 根頁無品牌殘留(WebView 內 HA 前端字樣屬 server 端,依決策 11 不計) | `phase4-settings-root.png` |

備註:
- 實體操作(開關燈)未在模擬器執行——會動到住家真實裝置,留待實機驗收時由使用者操作
- UI 自動化工具:`idb`(facebook/fb tap,免輔助使用權限);點位先 `idb ui describe-point` 確認再 tap
- 基準線對照:`phase1-baseline-onboarding.png`(官方 HA 畫面)
