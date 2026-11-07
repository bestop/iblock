#!/usr/bin/env python3
"""Fetch wave-3 missing assets: catalog thumbs (both dirs), scene covers,
guide screenshots, word-summaries.json. 403/404 -> origin-absent whitelist."""
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SITE = "https://henhaoxue.com"
ROOT = Path("/home/z/my-project/henhaoxue-site")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/126 Safari/537.36")

cat = json.loads((ROOT / "learning/home-assets/catalog.json").read_text())
ids = [e["id"] for e in cat]
SCENES = ["greetings", "meetup", "directions", "supplies", "building",
          "survival", "exploring", "rescue", "teamwork", "connection"]

items = []
for i in ids:
    items.append(f"/learning/home-assets/thumbs/{i}.webp")
    items.append(f"/learning/thumbs/{i}.webp")
items += [f"/learning/scene-covers/{s}-thumb.webp" for s in SCENES]
items += [f"/learning/guide-{b}/step-{n}.jpg"
          for b in ("safari", "chrome") for n in (1, 2, 3, 4)]
items.append("/learning/content/word-summaries.json")

todo = []
for p in items:
    loc = ROOT / p.lstrip("/")
    if not (loc.exists() and loc.stat().st_size > 0):
        todo.append((p, loc))
# batch mode: single-run cap + soft deadline so each invocation stays well
# inside the sandbox command timeout; re-run until "to fetch: 0"
import os
DEADLINE = time.time() + float(os.environ.get("WAVE3_SECS", "420"))
todo = todo[:int(os.environ.get("WAVE3_LIM", "100000"))]
print(f"total candidates: {len(items)}   to fetch: {len(todo)}", flush=True)

ok, absent, failed = [], [], []


def fetch_one(item):
    url_path, loc = item
    for i in range(3):
        try:
            req = urllib.request.Request(SITE + url_path, headers={
                "User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if not data:
                raise RuntimeError("empty body")
            return url_path, loc, data, None
        except urllib.error.HTTPError as e:
            return url_path, loc, None, f"HTTP {e.code}"
        except Exception as e:
            err = str(e)
            if i == 2:
                return url_path, loc, None, err[:90]
            time.sleep(0.8 + 0.8 * i)


results = []
ex = ThreadPoolExecutor(max_workers=10)
fmap = {ex.submit(fetch_one, it): it[0] for it in todo}
try:
    for n, fu in enumerate(as_completed(fmap), 1):
        url_path, loc, data, err = fu.result()
        results.append((url_path, loc, data, err))
        if n % 100 == 0 or n == len(todo):
            print(f"  {n}/{len(todo)}  ok={sum(1 for r in results if r[2])}", flush=True)
        if time.time() > DEADLINE:
            cancelled = 0
            for f, p in fmap.items():
                if f.cancel():
                    cancelled += 1
            print(f"  soft deadline hit, cancelled {cancelled} pending", flush=True)
            break
finally:
    ex.shutdown(wait=False, cancel_futures=True)

ok = [r[0] for r in results if r[2] is not None]
absent = [r[0] for r in results if r[2] is None and r[3] and r[3].startswith(("HTTP 403", "HTTP 404"))]
failed = [(r[0], r[3]) for r in results if r[2] is None and not (r[3] or "").startswith(("HTTP 403", "HTTP 404"))]
for url_path, loc, data, err in results:
    if data is not None:
        loc.parent.mkdir(parents=True, exist_ok=True)
        loc.write_bytes(data)

# retry transient failures once, serially (capped by the same deadline)
still = []
for url_path, err in failed:
    if time.time() > DEADLINE + 60:
        still.append((url_path, err))
        continue
    _u, loc, data, err2 = fetch_one((url_path, ROOT / url_path.lstrip("/")))
    if data is not None:
        loc.parent.mkdir(parents=True, exist_ok=True)
        loc.write_bytes(data)
        ok.append(url_path)
    elif err2 and err2.startswith(("HTTP 403", "HTTP 404")):
        absent.append(url_path)
    else:
        still.append((url_path, err2))
print(f"\ndownloaded: {len(ok)}")
print(f"absent on origin (403/404): {len(absent)}")
print(f"unresolved: {len(still)}")
for u, e in still[:10]:
    print("  FAIL", u, e)
Path("/tmp/wave3_ok.json").write_text(json.dumps(sorted(ok)))
Path("/tmp/wave3_absent.json").write_text(json.dumps(sorted(absent)))
Path("/tmp/wave3_failed.json").write_text(json.dumps(still))
