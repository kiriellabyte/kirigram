# architecture

## the three layers

### 1. upstream client

pinned at `01994b23a8684432490d7a28b6d12c7628d65a10`. it already brings:

- telegram's mtproto stack and proxy settings (`SharedConfig`, `ConnectionsManager`)
- upstream fork customizations
- a kotlin `WebProxyManager` (removed by our overlay) and `ProxyRotationController`
- material/customization features we'd otherwise have to write

the overlay edits the manifest, `ApplicationLoader.java`, `build.gradle`, `google-services.json` and `proguard-rules.pro`, then strips the fork-only webproxy code from `ConnectionsManager.java`, `ProxySettingsActivity.java`, `ProxyListActivity.java`, `AndroidUtilities.java` and native `ConnectionsManager.cpp`, and deletes `WebProxyManager.kt`. every edit is asserted, so upstream drift fails the build instead of silently producing a broken apk.

### 2. proxy engine (Rust)

vendored at build time from the archived `amurcanov/tg-ws-proxy-android` repo, revision `540e588d15fbdf806f694fbe0b952ff044d39a07`.

it is a `cdylib` exporting C functions:

- `StartProxy(host, port, dc_ips, secret, verbose)`
- `StopProxy()`
- setters for pool size, buffer size, cfproxy domains, fake-tls, secure mode
- `GetSecretWithPrefix()` -> `dd<hex>` or `ee<hex><domain_hex>`
- `GetStats()`, `FreeString()`

`build/build-proxy.sh` cross-compiles it with `cargo-ndk` for `arm64-v8a` and `armeabi-v7a` into `TMessagesProj/src/main/libs/<abi>/`.

### 3. glue (Kotlin, in `app/`)

injected into `org.telegram.messenger.kirigram`:

- `KiriNative` — JNA mapping of the C exports
- `KiriPrefs` — settings in `kirigram_proxy` shared prefs
- `KiriProxyManager` — lifecycle + applying proxy to telegram
- `KiriProxyService` — foreground service and notification
- `KiriBootReceiver` — start after boot
- `KiriSettingsActivity` — resource-free settings screen

## startup flow

```
ApplicationLoader.onCreate()
  -> KiriProxyManager.init(ctx)
     -> if enabled -> KiriProxyManager.startService(ctx)
        -> KiriProxyService.onStartCommand()
           -> startForeground(notification)
           -> KiriProxyManager.start(ctx)
              -> generate/load 16-byte secret
              -> KiriNative.start(...) -> libkiriproxy.so
              -> fullSecret = GetSecretWithPrefix()
              -> on UI thread: applyTelegramProxy()
                 -> SharedConfig.addProxy(127.0.0.1, port, secret)
                 -> write proxy_* prefs
                 -> NotificationCenter.proxySettingsChanged
                 -> ConnectionsManager.setProxySettings(...)
```

## stop flow

`KiriProxyManager.stop()` stops the native engine, then restores whatever proxy telegram had before kirigram touched it (saved in prefs at first apply), and posts `proxySettingsChanged` again.

## app identity

the application id is `com.kirigram` and the launcher label is `kirigram`. the overlay rewrites upstream's `defaultConfig.applicationId` and the `package_name` inside the bundled `google-services.json` together, so the google-services plugin still validates. firebase push registration may not work with the upstream project credentials, but telegram's own push path is unaffected.

## license note

telegram is GPL-2.0-or-later, the rust engine is GPLv3, so the combined work ships as GPLv3. the MIT-licensed flowseal proxy is the conceptual origin of the rust engine, credited in the README and `NOTICE.rust`.
