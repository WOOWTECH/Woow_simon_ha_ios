# fork-divergence.md — woow_ha_ios / Woow_simon_ha_ios

**Fork point**: `home-assistant/iOS` tag `release/2026.7.3/2026.2546`
(commit `70e675a8aabfe8740c98aed26d4c03c6c1b8b3d9`, 2026-07-28)

**上游策略**:pin 死、不滾動 merge;安全性修正每月＋每次品牌 release 前檢視、手動 pick。

## 與計畫文件的事實出入(執行時發現)

| 日期 | 項目 | 計畫寫的 | 實際 |
|---|---|---|---|
| 2026-08-15 | Entitlements 檔數 | 7 檔(含 WatchApp/WatchWidgets) | pin tag 只有 **5 檔**(App/Extension 各 ios+catalyst、Launcher)。WatchApp/WatchWidgets.entitlements 是 master 後續新增。rebrand 腳本按 5 檔處理 |
| 2026-08-15 | Repo 建立方式 | `gh repo fork` | claude.ai GitHub MCP 無 repo 建立權限、gh CLI 未登入 → 待 `gh auth login` 後以 `gh repo create` + push 完整歷史替代(非 GitHub fork 關係,純 hosting,功能等同) |
| 2026-08-15 | 模擬器機型 | iPhone 16 | Xcode 26.6 只有 iPhone 17 系列;所有 destination 用 `iPhone 17` |
| 2026-08-15 | scheme 名 | `App` | 實際為 `App-Debug` / `App-Release` |
| 2026-08-15 | 依賴管理 | 「已不用 Tuist,SPM 自動 resolve,無 Podfile」 | **pin tag 仍用 CocoaPods + SPM 雙軌**:有 Podfile/Podfile.lock/Gemfile(Ruby 3.1.2)、要開 `HomeAssistant.xcworkspace`;SwiftGen 由 `Pods/SwiftGen` build phase 執行。「純 SPM、開 xcodeproj」是 master 之後的狀態。編譯前置:`rbenv install 3.1.2` + `bundle install` + `bundle exec pod install` |
| 2026-08-15 | watchOS runtime | (未提及) | 本機只裝 watchOS SDK、無 simulator runtime → `-destination 'platform=iOS Simulator,name=iPhone 17'` 會被 scheme 驗證擋下(App 內嵌 WatchApp)。**Workaround:CLI 編譯用 `-destination 'generic/platform=iOS Simulator'`**;要在 Xcode GUI ⌘R 跑模擬器仍需下載 watchOS runtime(約 4GB)或暫時關 scheme 裡的 watch 相關 target |
| 2026-08-15 | Podfile.lock / pbxproj | — | 本機 CocoaPods 1.17.0(brew,vendored ruby;rbenv ruby 3.1.2 在 Xcode 26 clang 下編不出 socket ext 已棄用)重跑 pod install 造成 lock 版本欄與 pbxproj 正規化 diff(去重複 MacToolbarConfigTable、補 Domain.test.swift 進 Sources);以此狀態編譯綠 |

## Divergence 清單(逐項記錄,持續更新)

| # | 變更 | commit | 說明 |
|---|---|---|---|
| 1 | (待補)停用 `.github/workflows` | — | 決策 13;Lokalise sync 最優先 |
| 2 | (待補)`Configuration/Brand.xcconfig` 品牌參數層 | — | §6.4;拼接規則 `.HomeAssistant` → `.$(BRAND_BUNDLE_BASE)` |
| 3 | (待補)entitlements 雙軌(dev 精簡/release 完整) | — | 決策 15 |
| 4 | (待補)OnboardingAuthDetails OAuth 常數 | — | §7.2-3 |
| 5 | (待補)rebrand 字串/assets | — | §7.2 |

