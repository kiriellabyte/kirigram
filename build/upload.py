#!/usr/bin/env python3
"""Upload the kiriellagram source tree to an empty GitHub repo via the API."""
import base64
import json
import os
import sys
import urllib.request
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = "kiriellabyte"
REPO = "kirigram"
BRANCH = "main"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

SKIP_DIRS = {".git", "vendor", "upstream", "buildtree", "artifacts", "__pycache__"}
SKIP_FILES = {".probe.txt", "_probe.txt"}


def api(path, payload=None, method=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("PUT" if data else "GET"))
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "kirigram-upload")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode())


def main():
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN not set")

    # verify token against /user
    req = urllib.request.Request("https://api.github.com/user")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("User-Agent", "kirigram-upload")
    with urllib.request.urlopen(req, timeout=30) as r:
        me = json.loads(r.read().decode())
    print("authenticated as", me.get("login"))

    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_FILES or name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            files.append((rel, full))

    print(f"uploading {len(files)} files")
    for rel, full in sorted(files):
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        path = "contents/" + "/".join(quote(p) for p in rel.split("/"))
        api(path, {
            "message": f"add {rel}",
            "content": content,
            "branch": BRANCH,
        })
        print("ok", rel)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print("github error", exc.code, body[:600], file=sys.stderr)
        sys.exit(1)
