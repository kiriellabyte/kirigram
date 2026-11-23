#!/usr/bin/env python3
"""Fetch the pinned Rust proxy engine from the archived Android fork.

Pinned to an archived repo commit so the build is reproducible. The engine is
GPLv3; attribution lives in NOTICE.rust and in the README.
"""
import os
import sys
import urllib.request

REV = "540e588d15fbdf806f694fbe0b952ff044d39a07"
BASE = f"https://raw.githubusercontent.com/amurcanov/tg-ws-proxy-android/{REV}/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "vendor", "proxy")

FILES = [
    "Cargo.toml",
    "Cargo.lock",
    "src/balancer.rs",
    "src/cfproxy.rs",
    "src/config.rs",
    "src/crypto.rs",
    "src/faketls.rs",
    "src/lib.rs",
    "src/proxy.rs",
    "src/ws.rs",
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for rel in FILES:
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        url = BASE + rel
        print(f"fetch {url}")
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
        if rel == "Cargo.toml":
            text = data.decode("utf-8")
            text = text.replace('name = "tgwsproxy"', 'name = "kiriproxy"')
            data = text.encode("utf-8")
        with open(dst, "wb") as f:
            f.write(data)

    notice = (
        "proxy engine source: https://github.com/amurcanov/tg-ws-proxy-android\n"
        f"revision: {REV}\n"
        "license: GPL-3.0\n"
        "original design: https://github.com/Flowseal/tg-ws-proxy (MIT)\n"
        "changes in kiriellagram: crate renamed to kiriproxy, no logic changes\n"
    )
    with open(os.path.join(OUT, "NOTICE.rust"), "w", encoding="utf-8") as f:
        f.write(notice)
    print("vendor ready at", OUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("vendor fetch failed:", exc, file=sys.stderr)
        sys.exit(1)
