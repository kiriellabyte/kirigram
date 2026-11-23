#!/bin/sh
# build libkiriproxy.so for both telegram ABIs
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VENDOR="$ROOT/vendor/proxy"
UPSTREAM=${1:-"$ROOT/upstream"}
OUT="$UPSTREAM/TMessagesProj/src/main/libs"

if [ ! -f "$VENDOR/Cargo.toml" ]; then
  python3 "$ROOT/build/fetch-vendor.py"
fi

cargo install cargo-ndk --locked >/dev/null 2>&1 || true
rustup target add aarch64-linux-android armv7-linux-androideabi

mkdir -p "$OUT/arm64-v8a" "$OUT/armeabi-v7a"

cd "$VENDOR"
cargo ndk \
  -t arm64-v8a \
  -t armeabi-v7a \
  -p 21 \
  -o "$OUT" \
  build --release

find "$OUT" -name 'libkiriproxy.so' -print
