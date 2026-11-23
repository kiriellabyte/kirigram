# building

you cannot build this on the phone. telegram needs android studio 2025.1.4, ndk 27.2.12479018, sdk 36, jdk 17, cmake and a lot of ram. use github actions (already wired) or a desktop.

## github actions (recommended)

1. make a new github repo and push this folder to `main`
2. in repo settings -> secrets and variables -> actions, add:
   - `TELEGRAM_APP_ID` — from https://my.telegram.org/apps
   - `TELEGRAM_APP_HASH` — same place
   
   if you skip them the upstream fallback ids are used, which may be restricted for new sessions
3. run the `build-kirigram` workflow manually or push a commit
4. download `kirigram-apks` from the run's artifacts

the workflow pins both upstream revisions, so builds are reproducible. a full build can take 40-90 minutes on github's runners.

## local desktop

needs linux, 16gb ram, jdk 17, android sdk 36, ndk 27.2.12479018, rust stable, python3 and `cargo-ndk`.

```sh
mkdir buildtree && cd buildtree
git init
git remote add origin https://github.com/NullCoreDeveloper/NullcoreGram.git
git fetch --depth 1 origin 01994b23a8684432490d7a28b6d12c7628d65a10
git checkout FETCH_HEAD
git submodule update --init --recursive --depth 1
cd ..

python3 build/fetch-vendor.py
./build/build-proxy.sh "$PWD/buildtree"
python3 build/overlay.py "$PWD/buildtree"

cd buildtree
./run init action ffmpeg
./run init libs libvpx
./run init libs dav1d
./run init libs ffmpeg
./run init action boringssl
(cd TMessagesProj/jni && ./patch_boringssl.sh)
./run libs native

echo "sdk.dir=$ANDROID_HOME" > local.properties
echo "ndk.dir=$ANDROID_HOME/ndk/27.2.12479018" >> local.properties
./gradlew TMessagesProj:assemblePublicRelease
```

apks land in `TMessagesProj/build/outputs/apk/`.

## using your own api id

set `TELEGRAM_APP_ID` / `TELEGRAM_APP_HASH` in `local.properties` (or github secrets). inline in `local.properties`:

```
TELEGRAM_APP_ID=123456
TELEGRAM_APP_HASH=abcdef...
```

the overlay passes those to gradle through the base64 `LOCAL_PROPERTIES` env in CI.

## changing the package name

not done by default because of `google-services.json`. to do it properly:

1. create a firebase android app with your new package id
2. download its `google-services.json` into `TMessagesProj/`
3. change `defaultConfig.applicationId` in `TMessagesProj/build.gradle`
4. update `applicationId` expectations in any manifest placeholders

until then the mod installs side-by-side only if the signature differs. our CI generates its own signing key, so it already installs next to the stock telegram.

## troubleshooting

- `overlay: missing anchor` — upstream revision drifted, pin a newer commit in `build.yml` and re-check the anchors
- `StartProxy failed: -3` — bind failed, usually port already taken; change port in the in-app settings
- proxy connects but nothing loads — try disabling cloudflare mode or set a custom cf domain in settings
- google services error — you changed the app id without replacing `google-services.json`
