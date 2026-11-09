#!/usr/bin/env python3
"""Fetch missing mirror assets discovered by the deep completeness audit.

Builds the true missing list (fixing the content/reading-scenes -> reading-scenes
path mismatch), probes each URL with GET, and saves every 200 body to disk.
Origin returns 403 for objects that do not exist, so 403 == "not on origin".
"""
import json
import posixpath
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SITE = "https://henhaoxue.com"
ROOT = Path("/home/z/my-project/henhaoxue-site")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/126 Safari/537.36")

live = json.loads(Path("/tmp/dir_live.json").read_bytes())
base = "/learning/content/"          # directory.json lives here
refs = set()


def walk(o):
    if isinstance(o, dict):
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
    elif isinstance(o, str):
        for m in __import__("re").findall(
                r"[A-Za-z0-9_\-./]+\.(?:png|jpg|jpeg|webp|svg|gif|mp3|m4a)", o):
            if m.startswith("/"):
                refs.add(posixpath.normpath(m))
            else:
                refs.add(posixpath.normpath(posixpath.join(base, m)))


walk(live)

# --- build candidate list with correct local paths --------------------------------
candidates = []  # (url_path, local_path)
for r in sorted(refs):
    name = r.rsplit("/", 1)[1]
    if "/learning/content/reading-scenes/" in r:
        # server actually hosts these at /learning/reading-scenes/
        url_path = "/learning/reading-scenes/" + name
    else:
        url_path = r
    loc = ROOT / url_path.lstrip("/")
    if loc.exists() and loc.stat().st_size > 0:
        continue
    candidates.append((url_path, loc))

print(f"candidates to probe: {len(candidates)}", flush=True)

ok, fail = [], []


def fetch_one(item):
    url_path, loc = item
    url = SITE + url_path
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "image/webp,image/*,*/*;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if not data:
                raise RuntimeError("empty body")
            return url_path, loc, data, None
        except urllib.error.HTTPError as e:
            return url_path, loc, None, f"HTTP {e.code}"
        except Exception as e:
            last = str(e)[:100]
            time.sleep(0.8 + 0.8 * i)
    return url_path, loc, None, last


with ThreadPoolExecutor(max_workers=5) as ex:
    futs = {ex.submit(fetch_one, it): it for it in candidates}
    for n, fu in enumerate(as_completed(futs), 1):
        url_path, loc, data, err = fu.result()
        if data is not None:
            loc.parent.mkdir(parents=True, exist_ok=True)
            loc.write_bytes(data)
            ok.append(url_path)
        else:
            fail.append((url_path, err))
        if n % 25 == 0 or n == len(candidates):
            print(f"  {n}/{len(candidates)}  ok={len(ok)}  fail={len(fail)}", flush=True)

print(f"\ndownloaded: {len(ok)}")
print(f"not on origin: {len(fail)}")
from collections import Counter
print(Counter(e for _, e in fail))
Path("/tmp/fetch_ok.json").write_text(json.dumps(sorted(ok), indent=1))
Path("/tmp/fetch_fail.json").write_text(json.dumps(sorted(fail), indent=1))
