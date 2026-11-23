# kiriellagram

short name: **kirigram**

an unofficial telegram android mod. customization-focused base with a real built-in MTProto-over-WebSocket proxy for russian users. no second app, no manual `tg://proxy` link — the proxy starts with telegram and configures telegram's own proxy settings by itself.

## what it is

```
telegram (kirigram) -> local MTProto proxy 127.0.0.1:1443 -> WSS / Cloudflare / direct -> telegram DC
```

three upstreams are combined:

| part | source | license |
| --- | --- | --- |
| client base | [NullcoreGram](https://github.com/NullCoreDeveloper/NullcoreGram) @ `01994b23a8684432490d7a28b6d12c7628d65a10` | GPL-2.0-or-later |
| proxy engine | [tg-ws-proxy-android](https://github.com/amurcanov/tg-ws-proxy-android) @ `540e588d15fbdf806f694fbe0b952ff044d39a07` | GPL-3.0 |
| original proxy design | [Flowseal/tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy) | MIT |

telegram android is GPL v2 **or later**, so combining it with GPLv3 proxy code works. the whole fork is distributed under GPLv3.

## isn't there already a proxy in nullcoregram?

yes, and it's worth being clear about the difference, because they are not the same thing.

nullcoregram ships a `WebProxyManager`. it opens a local socket, but it is a **client**: it tunnels to a remote bridge server you have to supply yourself as a `wss://host/secret` link. that host runs someone else's bridge, so you still depend on a third-party server staying online and not getting blocked. it is basically a `tg://proxy` link with extra steps.

kirigram embeds the **proxy server itself** as `libkiriproxy.so`. it connects straight to telegram's own `kws{dc}.web.telegram.org` websocket endpoints, cloudflare workers, and falls back to the DC ips. there is no third-party bridge, no link to hunt down, and no second app. it generates its own secret and applies itself to telegram's proxy settings on boot.

so the difference is where the tunnel ends: nullcoregram's ends at a stranger's server, kirigram's ends at telegram. that is the point for users who want zero dependence on outside proxy servers.

if you already have a working webproxy link, nullcoregram's built-in client may be enough for you. kirigram earns its keep when you want the proxy to be the app, not something you connect to.

## status

code + ci scaffold. the apk is built by github actions (`build-kirigram`), which pulls the pinned upstreams, compiles the rust proxy and the telegram native libs, and uploads the apk as an artifact.

see [docs/build.md](docs/build.md) for the actual build steps and [docs/architecture.md](docs/architecture.md) for how the pieces fit.

## features planned / in this scaffold

- rust proxy engine compiled into the apk as `libkiriproxy.so`
- foreground service, boots with the app and after reboot
- auto-generates a 16-byte MTProto secret and applies it to telegram's built-in proxy
- cloudflare worker / cfproxy domains, fake-tls, pool size, custom DC IPs
- in-app settings screen reachable from the notification
- restore the previous proxy when stopped
- nullcoregram's existing customization, webproxy, proxy rotation and ayugram/nagram features stay intact

## quick start

1. create a github repo from this folder
2. add `TELEGRAM_APP_ID` and `TELEGRAM_APP_HASH` as repo secrets (get them at https://my.telegram.org/apps)
3. push, wait for the `build-kirigram` workflow
4. download the apk from the workflow artifact or the release

the app id in the upstream build.gradle is kept as-is on purpose: changing it breaks the bundled `google-services.json`. renaming to a fully own package is a separate step documented in [docs/build.md](docs/build.md).

## repo layout

```
build/                  overlay + vendor fetch + CI workflow
proxy/                  our JNI-facing glue config notes (engine is fetched at build time)
app/                    kotlin/java sources injected into telegram
docs/                   architecture and build notes
```

## credits

- nikolai kudashov / telegram
- nullcore developer and the ayugram / nagram people
- flowseal for the original ws proxy idea
- amurcanov for the android rust port

## license

GPLv3. see [LICENSE](LICENSE). upstream notices stay in their files.
