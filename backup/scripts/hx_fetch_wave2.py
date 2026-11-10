#!/usr/bin/env python3
"""Fetch the last wave of missing assets: audio files + manifest icons.
Also patches extract_refs blind spot coverage is already done; this completes disk."""
import time
import urllib.request
from pathlib import Path

SITE = "https://henhaoxue.com"
ROOT = Path("/home/z/my-project/henhaoxue-site")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/126 Safari/537.36")

ITEMS = [
    "/learning/audio/heart-v1/heart-dialogue-5-c93b8d4075c2.mp3",
    "/learning/audio/heart-v1/heart-dialogue-6-ad7d69ddafab.mp3",
    "/learning/audio/heart-v1/heart-dialogue-17-682abf18110c.mp3",
    "/learning/audio/heart-v1/heart-dialogue-18-bc07637b1355.mp3",
    "/demo/audio/zero-gap-v1/basic_block_world_things-p01-c01-easy-6f094ef19c80.mp3",
    "/demo/audio/zero-gap-v1/basic_block_world_things-p01-c01-medium-df7d01c420f1.mp3",
    "/demo/audio/zero-gap-v1/basic_block_world_things-p01-c01-hard-531d63cfd4f2.mp3",
    "/app-icons/diamond-192-v2.png",
    "/app-icons/diamond-512-v2.png",
]

for path in ITEMS:
    loc = ROOT / path.lstrip("/")
    if loc.exists() and loc.stat().st_size > 0:
        print("skip (have)", path)
        continue
    got = False
    for i in range(3):
        try:
            req = urllib.request.Request(SITE + path, headers={
                "User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            loc.parent.mkdir(parents=True, exist_ok=True)
            loc.write_bytes(data)
            print(f"OK  {path}  ({len(data)/1024:.0f} KB)")
            got = True
            break
        except Exception as e:
            code = getattr(e, "code", None)
            if code in (403, 404):
                print(f"ABSENT-ON-ORIGIN {path}  (HTTP {code})")
                break
            time.sleep(1 + i)
    if not got:
        print(f"FAILED {path}")
