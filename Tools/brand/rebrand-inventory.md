# Simon SmartHome — Rebrand Inventory

Source: home-assistant/iOS pinned at `release/2026.7.3/2026.2546`, repo `/Users/elmolin/Desktop/woow_ha_ios`.
Target brand: **Simon SmartHome** — bundle prefix `com.simon`, base segment `home` (=> `com.simon.home`), URL scheme `simonhome` (+ `simonhome-dev` for Debug), brand host `aiot.simon.io`, primary color `#0060A6`.

Merged from 8 scout reports (strings, infoplist, urlscheme, entitlements, weburls, colors-assets, bundlematrix, ci). Ordered by rebrand-script execution order.

> All line numbers are exact for this tag; the script should match by **pattern**, not line number.

---

## 1. Brand.xcconfig + bundle-ID concatenation

### 1.1 Before-matrix (current state)

`PRODUCT_BUNDLE_IDENTIFIER` is defined **exactly once**:
`Configuration/HomeAssistant.xcconfig:13` = `${BUNDLE_ID_PREFIX}.HomeAssistant${BUNDLE_ID_SUFFIX}${PROVISIONING_SUFFIX}`
with `BUNDLE_ID_PREFIX = io.robbie` (line 5). No target overrides it in `project.pbxproj`; targets only set `PROVISIONING_SUFFIX`. `BUNDLE_ID_SUFFIX = .dev` comes only from `Configuration/HomeAssistant.debug.xcconfig:13` (Release: empty).

| Target | PROVISIONING_SUFFIX | Release bundle ID (before) | Entitlements file |
|---|---|---|---|
| App | (none) | io.robbie.HomeAssistant | App-ios + App-catalyst[sdk=macosx*] |
| Extensions-Share | .ShareExtension | …HomeAssistant.ShareExtension | Extension-ios + Extension-catalyst |
| Extensions-Widgets | .Widgets | …Widgets | Extension-ios + Extension-catalyst |
| Extensions-Matter | .Matter | …Matter | Extension-ios + Extension-catalyst |
| Extensions-PushProvider | .PushProvider | …PushProvider | Extension-ios only |
| Extensions-NotificationContent | .NotificationContentExtension | …NotificationContentExtension | Extension-ios + Extension-catalyst |
| Extensions-NotificationService | .APNSAttachmentService | …APNSAttachmentService | Extension-ios + Extension-catalyst |
| Extensions-Intents | .Intents | …Intents | Extension-ios + Extension-catalyst |
| Launcher (mac) | .Launcher | …Launcher | Launcher.entitlements |
| MacBridge | .MacBridge | …MacBridge | none |
| WatchApp | .watchkitapp | …watchkitapp | none |
| WatchExtension-Watch | .watchkitapp.watchkitextension | …watchkitapp.watchkitextension | Extension-ios only |
| Shared-iOS / Shared-watchOS | .Shared | …Shared | none |
| SharedTesting | .SharedTesting | …SharedTesting | none |
| Tests-App / Tests-UI / Tests-Shared | .HomeAssistantTests / .HomeAssistantUITests / .SharedTests | … | none |

Debug builds insert `.dev` after the base: `io.robbie.HomeAssistant.dev<PROVISIONING_SUFFIX>`.

### 1.2 Edits

- `Configuration/HomeAssistant.xcconfig:5` — `BUNDLE_ID_PREFIX = io.robbie` → `com.simon`.
- `Configuration/HomeAssistant.xcconfig:13` — replace middle segment: `${BUNDLE_ID_PREFIX}.HomeAssistant${BUNDLE_ID_SUFFIX}${PROVISIONING_SUFFIX}` → `${BUNDLE_ID_PREFIX}.home${BUNDLE_ID_SUFFIX}${PROVISIONING_SUFFIX}`. Recommended: introduce `BRAND_BUNDLE_BASE = home` (a Brand.xcconfig or lines in this file) and reference `${BUNDLE_ID_PREFIX}.${BRAND_BUNDLE_BASE}…` so entitlements can reuse it.
- `Configuration/HomeAssistant.xcconfig:61` — `PRODUCT_NAME = HomeAssistant-$(TARGET_NAME)` → `SimonSmartHome-$(TARGET_NAME)` (global fallback product name).
- `Configuration/HomeAssistant.xcconfig:4` — `DEVELOPMENT_TEAM = QMQYCKL255` → new team (or override via git-ignored `Configuration/HomeAssistant.overrides.xcconfig`, included at line 26 — note: an override alone CANNOT change the `HomeAssistant` middle segment; tracked line 13 must be edited).
- Keep line 37 `CODE_SIGN_ALLOW_ENTITLEMENTS_MODIFICATION = YES` (needed by the entitlements mutation script).
- **Do NOT rename any `PROVISIONING_SUFFIX` values** — `Sources/Shared/Environment/AppConstants.swift:87-102` (`BundleID`) strips exactly these suffixes: `.APNSAttachmentService, .Intents, .NotificationContentExtension, .TodayWidget (legacy), .watchkitapp.watchkitextension, .watchkitapp, .Widgets, .ShareExtension, .PushProvider, .Matter`. Renaming any breaks AppGroupID derivation in extensions.

### 1.3 Downstream bundle-ID literals (same pass)

- `Sources/WatchApp/Info.plist:28-29` — `WKCompanionAppBundleIdentifier = $(BUNDLE_ID_PREFIX).HomeAssistant$(BUNDLE_ID_SUFFIX)` → `$(BUNDLE_ID_PREFIX).home$(BUNDLE_ID_SUFFIX)`.
- `Sources/Shared/Notifications/LocalPush/LocalPushEvent.swift:56` — hardcoded `"app_id": "io.robbie.HomeAssistant"` → `com.simon.home`.
- `Sources/PushServer/Sources/App/routes.swift:9` — default APNs topic `io.robbie.HomeAssistant` → `com.simon.home` (only matters when deploying own relay); tests at `Sources/PushServer/Tests/AppTests/PushControllerTests.swift:52-266` hardcode topics too.
- `Sources/Shared/Environment/CrashReporter.swift:21` — `guard AppConstants.BundleID.starts(with: "io.robbie.")` — Sentry silently disables under `com.simon.*`. **DECIDE**: keep disabled (recommended for fork) or repoint to own Sentry DSN + prefix.
- Runtime derivations stay coherent automatically: `AppConstants.AppGroupID = "group." + BundleID.lowercased()` → `group.com.simon.home[.dev]` ( `"home".lowercased() == "home"` ), `Keychain(service: BundleID)` (line 343), `UserDefaults(suiteName: AppGroupID)` (line 349).
- Pods-*.xcconfig: CocoaPods-generated, no bundle IDs — never text-substitute; re-run `pod install`.

---

## 2. Entitlements — dual-track (dev-minimal vs release)

Files in `Configuration/Entitlements/`. Brand literals: app groups use lowercase `homeassistant`, keychain groups use TitleCase `HomeAssistant` — both must become `home` (2 occurrences in each of 4 files, 8 total).

### 2.1 Brand substitutions (both tracks)

In `App-ios.entitlements`, `App-catalyst.entitlements`, `Extension-ios.entitlements`, `Extension-catalyst.entitlements`:
- `com.apple.security.application-groups`: `group.$(BUNDLE_ID_PREFIX).homeassistant$(BUNDLE_ID_SUFFIX)` → `group.$(BUNDLE_ID_PREFIX).home$(BUNDLE_ID_SUFFIX)` (must equal `BundleID.lowercased()`).
- `keychain-access-groups`: `$(AppIdentifierPrefix)$(BUNDLE_ID_PREFIX).HomeAssistant$(BUNDLE_ID_SUFFIX)` → `$(AppIdentifierPrefix)$(BUNDLE_ID_PREFIX).home$(BUNDLE_ID_SUFFIX)`.

`Launcher.entitlements`: only `com.apple.security.app-sandbox=true` — no change.

### 2.2 Dev-minimal track (free Personal Team) — keys to STRIP

- `App-ios.entitlements`: strip `aps-environment`, `com.apple.developer.associated-domains`, `com.apple.developer.nfc.readersession.formats`, `com.apple.developer.siri`, `com.apple.developer.usernotifications.communication`, `com.apple.developer.usernotifications.time-sensitive`, `com.apple.developer.networking.wifi-info`. Keep: `application-groups`, `keychain-access-groups`.
- `App-catalyst.entitlements`: strip `aps-environment`, `associated-domains`, `usernotifications.communication`. Keep all `com.apple.security.*` sandbox keys.
- `Extension-ios.entitlements`: strip `com.apple.developer.networking.wifi-info`. (This file is shared by all iOS extensions AND WatchExtension-Watch.)
- `Extension-catalyst.entitlements`: no paid-only keys — brand substitution only.
- Extensions-PushProvider (NEAppPushProvider) cannot be signed by a free team at all — the dev track should **exclude the target** from build/embed, not just strip entitlements.

### 2.3 Release track — keys to RETARGET

- `App-ios.entitlements` / `App-catalyst.entitlements` `com.apple.developer.associated-domains`: `[applinks:home-assistant.io, applinks:*.home-assistant.io, applinks:my.home-assistant.io]` → `[applinks:aiot.simon.io]` (requires paid team + AASA file on aiot.simon.io listing `com.simon.home` app IDs — including the `.dev` suffix variants if desired).
- `aps-environment` stays (value managed by signing).

### 2.4 Wiring caveats

- **CODE_SIGN_ENTITLEMENTS lives ONLY in `HomeAssistant.xcodeproj/project.pbxproj`**, per target, identical for Debug and Release (App: ln 11543-44 / 11584-85; extensions similar — see report pairs). An xcconfig-only override is shadowed. To switch dev/release variants: rewrite pbxproj values to `Configuration/Entitlements/$(ENTITLEMENTS_VARIANT)/App-ios.entitlements` with `ENTITLEMENTS_VARIANT` set in debug/release xcconfig, or sed only the Debug-block paths to stripped files.
- `Configuration/Entitlements/activate_special_entitlements.sh` (build phase on App + Extensions-PushProvider): injects critical-alerts / networkextension / thread-credentials / CarPlay / device-name into the .xcent when `ENABLE_*_$(DEVELOPMENT_TEAM)` flags = 1. Flags are keyed `_QMQYCKL255` (HomeAssistant.xcconfig lines 6-10/30-34) → with a new team the script is self-disabling. Keep the script verbatim; add `ENABLE_*_<NEWTEAM>=1` only for the paid release team if those capabilities are wanted.
- `Configuration/HomeAssistant.release.xcconfig` pins Manual signing (`iOS App Store - $(TARGET_NAME)` / `Mac Dev ID - $(TARGET_NAME)` profiles). **DECIDE**: create matching-named profiles in the Simon account or switch to Automatic.

---

## 3. OnboardingAuthDetails / OAuth constants

`Sources/App/Onboarding/API/OnboardingAuthDetails.swift:19-29`:

| Build | Constant | Before | After |
|---|---|---|---|
| Debug | clientID | `https://home-assistant.io/iOS/dev-auth` | see decision below |
| Debug | redirectURI | `homeassistant-dev://auth-callback` (L22) | `simonhome-dev://auth-callback` |
| Debug | scheme | `homeassistant-dev` (L23) | `simonhome-dev` |
| Release | clientID | `https://home-assistant.io/iOS` (L25) | see decision below |
| Release | redirectURI | `homeassistant://auth-callback` (L26) | `simonhome://auth-callback` |
| Release | scheme | `homeassistant` (L27) | `simonhome` |

Also `Sources/Shared/API/Authentication/AuthenticationRoutes.swift:32-36` uses the same clientID values.

**HIGHEST-RISK ITEM**: HA servers validate IndieAuth-style — the page at the clientID URL must declare the redirect URI via `<link rel="redirect_uri" href="simonhome://auth-callback">`. Changing redirectURI without (a) hosting e.g. `https://aiot.simon.io/iOS` with that link tag AND (b) changing clientID to that URL **breaks login against every standard HA server**. Keeping the old clientID shows "home-assistant.io" on the server consent screen. The script must treat clientID+redirectURI+hosted metadata page as one atomic decision; test login before/after.

Redirect interception: `Sources/App/Onboarding/API/OnboardingAuthLoginViewController.swift:171` — `url.scheme?.hasPrefix("homeassistant")` → `hasPrefix("simonhome")` (covers both prod and -dev).

---

## 4. URL scheme replacements (homeassistant → simonhome, homeassistant-dev → simonhome-dev)

Production sites (exact file:line):

| File:line | Before → After |
|---|---|
| `Sources/Shared/Environment/AppConstants.swift:107` | `homeassistant-dev://` → `simonhome-dev://` (deeplinkURL, Debug) |
| `Sources/Shared/Environment/AppConstants.swift:109` | `homeassistant://` → `simonhome://` (deeplinkURL — single source for ALL deep links: widgets/Siri/LiveActivity/assist/camera/todo at L138/164/173/185/193/198) |
| `Sources/App/Onboarding/API/OnboardingAuthDetails.swift:22-23,26-27` | see §3 |
| `Sources/App/Onboarding/API/OnboardingAuthLoginViewController.swift:171` | `hasPrefix("homeassistant")` → `hasPrefix("simonhome")` |
| `HomeAssistant.xcodeproj/project.pbxproj:11546` | `ENV_URL_HANDLER = "homeassistant-dev"` (Debug) → `"simonhome-dev"` |
| `HomeAssistant.xcodeproj/project.pbxproj:11587` | `ENV_URL_HANDLER = homeassistant` (Release) → `simonhome` |

Test fixtures (update in same pass):
- `Tests/App/AppConstants.test.swift:133-134`
- `Tests/App/Auth/OnboardingAuthLoginViewController.test.swift:22,49` (must change or the hasPrefix test fails)
- `Tests/App/Auth/OnboardingAuthLoginImpl.test.swift:39,46,54`
- `Tests/Shared/URLComponents+WidgetAuthenticity.test.swift:7-9,20-24,52`

Auto-follows (no edit): `Sources/App/Resources/Info.plist` CFBundleURLTypes uses `${ENV_URL_HANDLER}`; CallbackURLKit reads Info.plist at runtime (`IncomingURLHandler.swift:664`, `NotificationManager.swift:56`).

Cosmetic-only (optional): comments in `IncomingURLHandler.swift` L43/102/224/808/836/882, `HAApp.swift:52`, `AppConstants.swift:115`.

**MUST NOT touch** (`homeassistant` here is the push-payload dictionary key, a server protocol key): `userInfo["homeassistant"]` in NotificationManager.swift L136-522, KioskPushCommand.swift, HAAPI.swift, LocalPushManager.swift, NotificationAttachmentManager.swift, NotificationsCommandManager.swift, DebugView.swift, and the vendored PushServer copy. Also whitelist: `Tests/Shared/Models/deviceregistry.json` (~50 server-generated `homeassistant://` configuration_url fixtures), `fastlane/metadata/{sv,fi}/release_notes.txt`.
Scheme-sweep patterns: match only `homeassistant://`, `homeassistant-dev`, `scheme = "homeassistant"`, `hasPrefix("homeassistant")` — never bare `homeassistant`.

---

## 5. Info.plist display names + CFBundleURLTypes

CFBundleURLTypes exists **only** in `Sources/App/Resources/Info.plist` (L23-33) and is fully variable-driven (`CFBundleURLName=$(PRODUCT_BUNDLE_IDENTIFIER)`, `CFBundleURLSchemes=[${ENV_URL_HANDLER}]`) — keep as-is. `LSApplicationQueriesSchemes` (L61+) lists third-party schemes only — keep.

Display names (no InfoPlist.strings localization exists for CFBundleDisplayName — names live here):

| Location | Before → After |
|---|---|
| `project.pbxproj:11612` (App Release) | PRODUCT_NAME `"Home Assistant"` → `"Simon SmartHome"` |
| `project.pbxproj:11571` (App Debug) | PRODUCT_NAME `"Home Assistant Δ"` → `"Simon SmartHome Δ"` (keep Δ convention for coexisting installs) |
| `project.pbxproj:11339/11351` (Launcher) | `"Home Assistant Launcher"` → `"Simon SmartHome Launcher"` |
| `project.pbxproj:11159/11167` | PRODUCT_NAME `HomeAssistant` → `SimonSmartHome` (verify target before edit) |
| `Sources/WatchApp/Info.plist` | hardcoded CFBundleDisplayName `Home Assistant` → `Simon SmartHome` |
| `Sources/Extensions/Share/Resources/Info.plist` | hardcoded CFBundleDisplayName `Home Assistant` → `Simon SmartHome` (share-sheet name) |

Keep unchanged (internal/generic names): NotificationService (`APNSAttachmentService`), NotificationContent, Matter, Watch extension, Intents, PushProvider, Widgets, Launcher plist, MacBridge, Shared, all Tests plists.
Note: PRODUCT_NAME rename ripples into product paths (`Simon SmartHome.app`) — check fastlane lanes referencing the .app name.

---

## 6. .strings replacements + whitelist patterns

Scope: 34 locales + Base (`bg ca-ES cs cy-GB da de el en en-GB es es-ES es-MX et fi fr he hu id it ja ko-KR ml nb nl pl-PL pt-BR ru sl sv tr uk vi zh-Hans zh-Hant`), 5 tables each under `Sources/App/Resources/*.lproj/`: `Localizable.strings`, `InfoPlist.strings`, `Core.strings`, `Frontend.strings`, `Intents.strings`; plus `Sources/Extensions/Intents/Resources/*.lproj/AppIntentVocabulary.plist`. No .stringsdict files. **Must run across every .lproj** (zh-Hant alone has 100 hits), value-side only.

Replace:
- en `Localizable.strings`: `Home Assistant Companion` x4 (`about.logo.app_title`, `assist.carplay.*` L150-151, `onboarding.welcome.header` L1028) → `Simon SmartHome`; `Home Assistant` x101 total → `Simon SmartHome` (preserve `%@` in `onboarding.welcome.title = "Welcome to Home Assistant %@!"`).
- `InfoPlist.strings` (permission usage descriptions, 5 en hits), `Intents.strings` (14 en hits — **values only, keys are Xcode hashes like `2KWKqM`**), `AppIntentVocabulary.plist` (1 en hit).
- `Core.strings` / `Frontend.strings`: 0 hits — skip.

Whitelist patterns (blind sed would break these):
- Keys `onboarding.manual_setup.text_field.placeholder`, `settings.connection_section.internal_base_url.placeholder`, `settings.connection_section.external_base_url.placeholder` — contain `http://homeassistant.local:8123` (real mDNS hostname of the HA server) and `https://homeassistant.myhouse.com`. **DECIDE** if placeholder should become Simon-branded, but never mechanical-replace.
- `connection.error.failed_connect.cloud.title` (nabucasa.com markdown URL) and `settings.connection_section.home_assistant_cloud.title` = "Home Assistant Cloud" — third-party Nabu Casa product name. **DECIDE** per-key; do not auto-rename.
- ~95 keys with `%@`/`%1$@`/`%d` — validate post-sed: `plutil -lint` every file + per-key format-specifier count diff.

Post-pass hygiene: SwiftGen output (`Sources/Shared/Resources/Swiftgen/{Strings,CoreStrings,FrontendStrings}.swift`) has no embedded fallbacks (lookupFunction `Current.localized.string`) — runtime is fixed by .strings alone; regenerate via `fastlane update_swiftgen_config` only to fix doc-comments. `ci.yml` check-unused-strings must still pass.

---

## 7. Assets

### 7.1 App icons (px sizes)

- `Sources/App/Resources/Assets.xcassets/AppIcon.appiconset/` — universal **1024x1024 in 3 appearances** (any / dark / tinted, iOS 18 style) + mac idiom sizes: **16, 32 (16@2x), 32, 64 (32@2x), 128, 256 (128@2x), 256, 512 (256@2x), 512, 1024 (512@2x)** → unique px files: **16, 32, 64, 128, 256, 512, 1024**.
- Repeat for `AppIcon.dev.appiconset` and `AppIcon.beta.appiconset` — selected via `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon${BUNDLE_ID_SUFFIX}` (Debug uses `AppIcon.dev`; missing sets break Debug builds).
- Watch icons: single universal **1024x1024** PNG per set, in **both** `Sources/WatchApp/Assets.xcassets/` AND duplicate catalog `WatchApp/Assets.xcassets/` (WatchIcon / WatchIcon.beta / WatchIcon.dev x2 locations, via `WatchIcon${BUNDLE_ID_SUFFIX}`).
- `AlternateIcons/` — 21 appiconsets, 1024x1024 each. **DECIDE**: delete folder + strip picker UI, or regenerate Simon variants.
- `icons/` dir — 1024px master art for tooling, not compiled; replace only if icon pipeline reused.

### 7.2 AccentColor / brand color (#009AC7 → #0060A6; note asset blue is NOT #03A9F4)

Edit Contents.json **values only — never rename colorset folders** (Xcode-generated `Color.haPrimary` symbols in 25+ files):
- `Sources/App/Resources/Assets.xcassets/accentColor.colorset/Contents.json` — #009AC7 (any+dark) → **#0060A6** (0x00/0x60/0xA6). Wired via `ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME=accentColor` (pbxproj 11541/11582).
- `Sources/Shared/Assets/Colors.xcassets/haPrimary.colorset/Contents.json` — #009AC7 → **#0060A6** (THE brand primary).
- `Sources/Shared/Assets/Colors.xcassets/ha-color-border-primary-quiet.colorset/Contents.json` — light #B9E6FC → ~#B3CFE4 tint, dark #009AC7 → #0060A6.
- Swift literals: `Sources/Shared/DesignSystem/BaseColors.swift:148` `brandBlue 0xFF18BCF2` → `0xFF0060A6`; `Sources/App/Settings/LiveActivity/LiveActivitySettingsView.swift:294` `#03A9F4` → `#0060A6`; `Sources/Extensions/Watch/Home/MagicItemRow/WatchFolderRow.swift:109,116` `#03A9F4` → `#0060A6`; `Sources/Extensions/Widgets/LiveActivity/HALockScreenView.swift:151` `haBlueHex "#03A9F4"` → `#0060A6`.
- Whitelist: `Tests/Shared/LocalPushManager.test.swift:453,461` `#03A9F4` is a server-color pass-through fixture — do not touch.
- Keep: `BaseColors.swift` brandBackground #F2F4F9 + state-color ramps; `Colors.xcassets/Domain/` entity colors (light #FEC008, fan #00BBD4, cover #916BC6 — functional, not brand).
- Widgets quirk: pbxproj 11247/11268 sets Widgets `GLOBAL_ACCENT_COLOR_NAME=AccentColor` (capital A) but **no AccentColor.colorset exists** — add one (#0060A6) in `Sources/Extensions/Widgets/Resources/Assets.xcassets/` or fix the setting, else widgets miss the tint.

### 7.3 Launch screen + brand imagery

- Mechanism: `UILaunchStoryboardName=LaunchScreen` (`Sources/App/Resources/Info.plist:215-216`) → `Sources/App/Resources/Base.lproj/LaunchScreen.storyboard` (no edit needed).
- `Assets.xcassets/LaunchScreen/launchScreen-logo.imageset/` — replace `home-assistant-wordmark-vertical-color-on-{light,dark}.pdf` with Simon vertical wordmark PDFs (vector, drawn 180x271pt); keep imageset name.
- `launchScreen-background.colorset` — neutral (250/250/250 light, 17/17/17 dark) — keep unless branded splash wanted.
- `Sources/Shared/Assets/SharedAssets.xcassets/` — replace `Logo.imageset`, `logo-horizontal-text.imageset`, `casita.imageset`, `casita-dark.imageset`, `statusItemIcon.imageset` (mac menu bar). Keep `improv-logo`, `thread` (third-party protocol marks). `ha-cloud-logo` depends on §8 HA Cloud decision.
- `Sources/Extensions/Watch/Resources/Assets.xcassets/` — replace `Complication.complicationset`, `RoundLogo.imageset`, `TemplateLogo.imageset`.

---

## 8. WebURLs keep/replace table

Primary file `Sources/Shared/Environment/AppConstants.swift` (WebURLs enum) plus scattered literals.

| URL / constant | Location | Verdict |
|---|---|---|
| www.home-assistant.io, /installation/ | AppConstants.swift:9-10 | **Replace** → aiot.simon.io |
| companion.home-assistant.io doc links (7 constants) | AppConstants.swift:11-15,27-34 | **Replace** → aiot.simon.io docs, or hide help buttons |
| beta/review/translate/forums/chat/twitter/facebook/repo/issues | AppConstants.swift:16-26 | **Replace/hide** — all point at HA project |
| ohf.to/ha/apple-drop-support | AppConstants.swift:35-36 | **Replace/hide** |
| stun.home-assistant.io:80/3478 | AppConstants.swift:44-48 | **DECIDE** — functional STUN for WebRTC cameras; keep, or swap to own/public STUN. Blind replace silently breaks camera streaming |
| mobile-apps.home-assistant.io/api/sendPushNotification | AppConstants.swift:52 | **Replace** — bound to HA APNs certs, will NOT deliver to com.simon.home; requires deploying Sources/PushServer with own APNs key |
| mobile-apps.home-assistant.io/api/checkRateLimits | NotificationRateLimitsAPI.swift:26 | **Replace** together with above |
| my.home-assistant.io/invite/# (invitationURL) | AppConstants.swift:123-129 | **DECIDE** — disable invite sharing or host redirect page |
| alerts.home-assistant.io/mobile.json | ServerAlerter.swift:104 | **Replace/disable** |
| api.github.com/repos/home-assistant/ios/releases | Updater.swift:59 | **Replace/disable** — mac self-updater would offer official-app updates |
| clientID home-assistant.io/iOS(+/dev-auth) | OnboardingAuthDetails.swift:21-25, AuthenticationRoutes.swift:32-36 | **DECIDE** — see §3, atomic with hosted metadata page |
| NFC tag host www.home-assistant.io (+next. in debug) | iOSTagManager.swift:53,79-81 | **Keep** — ecosystem tag format; changing breaks interop with tags written by stock HA apps |
| my.home-assistant.io universal-link handling | IncomingURLHandler.swift:38-45,285 | **Whitelist** — dead path once entitlement changes; harmless |
| Demo server companion.home-assistant.io/app/ios/demo | ConnectionInfo+WebView.swift:7 | **DECIDE** — own demo instance or remove entry point |
| ExternalLink.swift:4,12 duplicate doc constants | Sources/Shared/ExternalLink.swift | **Replace** with §8 doc links |
| 9 hardcoded companion.home-assistant.io literals outside constants | MainWindowGroupCommands.swift:35, AppDelegate.swift:367, SettingsView.swift:174, ComplicationEditView.swift:56, ComplicationListView.swift:44, NotificationCategoryListView.swift:152, NotificationSettingsView.swift:96, NotificationCategoryEditorView.swift:359, NotificationSoundsView.swift:71 | **Replace** — constants-only pass misses these |
| PushServer root redirect | Sources/PushServer/Sources/App/routes.swift:5 | **Replace** if relay deployed |
| developers.home-assistant.io etc. in comments | WebViewExternalBusMessage.swift:5, WhatsNewCatalog.swift:27,39 | **Keep** (attribution/comments) |
| Onboarding default server URL | none exists | Bonjour + manual entry; placeholder string handled in §6. InvitationView.swift:135 IP is SwiftUI preview only |

---

## 9. CI workflows to disable + commit-hook caveats

11 workflows in `.github/workflows/`. **No git hooks exist** (no husky/pre-commit/lefthook; only .sample files) — the rebrand script can commit freely. SwiftLint/SwiftFormat run only in CI and Xcode build phases (`swiftlint --strict` build phase; escape hatch `DISABLE_SWIFTLINT=1`; Pods/SwiftLint phase skipped when `CI=true`).

Disable/neuter before first push (auto-triggered):
- `download_localized_strings.yml` — **daily cron**; would overwrite rebranded strings with upstream Lokalise translations or fail noisily daily. **Delete/disable first.**
- `distribute.yml` — push(main) trigger; burns macos-26 minutes on signed-build attempts failing without HA secrets. Reduce to workflow_dispatch or rewrite for Simon signing.
- `restrict-task-creation.yml` — issues(opened); would auto-close the fork owner's own Task issues (checks home-assistant org membership). Delete/repoint.
- `ci.yml` — pull_request/push(main); lint jobs safe, test/size fail without secrets. **DECIDE** keep-lint-only vs disable.
- `auto_delete_unused_strings.yml`, `delete_lokalise_keys.yml` — manual-only but upstream-Lokalise oriented; delete.

Manual-only, decide later: `release_macos.yml`, `tag_macos_release.yml`, `push_deploy.yml` (ghcr image name), `set_version.yml` (HA bot identity). Keep: `push_ci.yml` (PushServer tests, secret-free), `.github/dependabot.yml`, `.github/move.yml` (inert).

Caveats:
- Do NOT blindly rebrand `HOMEASSISTANT_*` strings inside workflow files — they are secret names / fastlane env lookups; renaming silently breaks env wiring.
- `fastlane/lanes/localization.rb` (Lokalise API client) — whitelist from string replacement or delete with the workflows.
- Build gating: plain `xcodebuild` needs Ruby 3.1.2 + bundler + `pod install` (SwiftGen runs from `Pods/SwiftGen` build phase); fastlane lanes NOT required for local builds. swiftgen.yml + .file-list.in/.out must stay consistent with any renamed assets/strings.

---

## 10. Open risks / decisions needed

Decisions (blocking):
1. **OAuth clientID strategy** (§3): host `https://aiot.simon.io/iOS` with `<link rel="redirect_uri" href="simonhome://auth-callback">` and switch clientID, vs keep HA clientID (shows home-assistant.io on consent screen). Redirect URI change is unsafe without this.
2. **Push relay** (§8): ship with broken push, or deploy Sources/PushServer with own Firebase/APNs (`APNS_TOPIC=com.simon.home`) and repoint pushURLString + checkRateLimits.
3. **"Home Assistant Cloud" / Nabu Casa strings** (§6): third-party product name — keep, hide feature, or rename knowingly.
4. **STUN servers** (§8): keep HA's, run own, or public STUN.
5. **Release signing** (§2): Manual profiles named `iOS App Store - $(TARGET_NAME)` vs Automatic; new team's `ENABLE_*_<TEAM>` capability flags.
6. **CrashReporter** (§1): stays silently disabled under com.simon.* — intended?
7. Alternate icons (§7): delete vs regenerate 21 sets. Demo server, invite URL, mac Updater, placeholder example URL branding.

Top risks:
1. **OAuth login breakage** — redirectURI/clientID must change atomically with a hosted IndieAuth metadata page, or login against every standard HA server fails. Test before/after.
2. **Naive global sed of `homeassistant` corrupts the push protocol** (`userInfo["homeassistant"]` key in ~10 files), mDNS example URLs in all 34 locales, and deviceregistry.json fixtures — sweep must use the narrow patterns in §4/§6.
3. **Push is dead on day one** — HA relay only serves official bundle IDs; requires own relay + APNs before push works at all.
4. **Daily Lokalise cron overwrites rebranded strings** — download_localized_strings.yml must be disabled before Actions ever run on the fork.
5. **Coordination triple for the bundle base** — xcconfig line 13 (`HomeAssistant`→`home`), entitlements (`homeassistant`/`HomeAssistant`→`home`), WatchApp WKCompanionAppBundleIdentifier must change together, and PROVISIONING_SUFFIX values must NOT change, or app-group/keychain sharing and watch pairing break at runtime.
6. Format-specifier corruption in ~95 localized strings → String(format:) crashes; validate with plutil -lint + specifier-count diff.
7. Colorset folder names are compiled Swift symbols — value-only edits; also the real brand blue is #009AC7, not #03A9F4.
8. pbxproj line numbers drift — pattern-match all pbxproj edits (ENV_URL_HANDLER, PRODUCT_NAME, CODE_SIGN_ENTITLEMENTS).
9. Free-team dev track: PushProvider target must be excluded (not just stripped); stripped aps-environment/associated-domains disable push + universal links in dev builds by design.
10. Existing NFC tags / x-callback-url automations written with `homeassistant://` will not open the rebranded app — document for users.
