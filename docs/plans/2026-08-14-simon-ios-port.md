> **執行狀態(2026-08-15)**:Phase 0–4(模擬器)已完成,偏離與環境勘誤見
> `docs/fork-divergence.md`;Bundle ID 矩陣見 `docs/bundle-id-matrix.md`;
> rebrand 工具與逐行清查見 `Tools/brand/`。待辦:模擬器 OAuth 全鏈路人工測試、
> Phase 5 實機(需 Xcode Apple ID)、GitHub push(需 gh auth)。
> 原計畫全文如下(v2,未改動)。

# Simon SmartHome iOS 移植計畫(home-assistant/iOS 白牌)

**日期**:2026-08-14(v2:經反方紅隊審查修訂)
**狀態**:已 grill 定案 ×2(初版 10 決策 + 紅隊 5 決策),執行中
**上游 pin 目標**:`home-assistant/iOS` tag `release/2026.7.3/2026.2546`

(完整計畫內容存於 Android repo `Woow_simon_ha_app/docs/plans/`;本檔為 iOS repo
副本的節錄版——決策表與驗收清單為執行時實際依據,全文請見 Android repo 或
會話紀錄。關鍵決策 15 條與 §6.5 矩陣、§7.2 置換清單已分別落地為
`Tools/brand/rebrand-inventory.md` 與 preflight 檢查,那兩份才是可執行的 ground truth。)

## 驗收清單(§9.2,實機期用)

| # | 分類 | iOS 驗收動作 | 預期 |
|---|---|---|---|
| 1 | Onboarding / 連線 | 全新安裝 → 輸入 server → OAuth → Dashboard | 全程品牌字樣,無 HA 殘留 |
| 2 | WebView 主體 | Dashboard 操作實體、切頁、下拉刷新 | 與 Android WebView 行為等同 |
| 3 | 感測器 | Settings → Companion App → Sensors | 資料回報到 HA |
| 4 | 深連結 | Safari 開 simonhome://navigate/lovelace/0 | 直接開 app 對應頁 |
| 5 | Widgets | 加桌面 widget(簽章允許時) | 品牌名+可用;免費帳號裝不了則延後 |
| 6 | 外觀 | icon、splash、AccentColor、深淺色 | 全 #0060A6,無 HA 藍/房子(限原生 UI) |
| 7 | 設定頁 | 逐頁瀏覽 Settings | 無品牌殘留、無 home-assistant.io 入口連結 |
| 8 | 穩定性 | 冷啟 ×10、背景切換、斷網重連 | 無 crash |

## 實機簽章備忘(§9.1)

1. overrides.xcconfig 填 Personal Team;Debug 已自動走 dev 精簡 entitlements
2. 免費帳號 App ID 配額 10 個/7 天 → 實機期主 app 優先,extensions 從 scheme 拿掉
3. PushProvider 免費 Team 完全不可簽,必須排除
4. 免費 profile 7 天過期,驗收週期內重簽
