#!/usr/bin/env python3
"""Download all missing assets for henhaoxue-site (resumable, time-budgeted).

Missing set (from hx_audit.py logic, recomputed here):
  - /learning/phrase-images/*.webp       (directory.json images, sha256 verified)
  - /learning/reading-scenes/*.webp      (readings imageSrc+imageThumb)
  - /learning/home-assets/thumbs/*.webp  (catalog.json 1245 word cards)
  - /learning/thumbs/*.webp              (app.js runtime path, confirmed live)

Usage: python3 hx_download_missing.py [budget_seconds]
Skips files already on disk with valid webp magic. Writes progress to
/tmp/hx_download_state.json so runs can be resumed safely.
"""
import brotli
import gzip
import hashlib
import json
import posixpath
import sys
import threading
import time
import urllib.error
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/home/z/my-project/henhaoxue-site")
SITE = "https://henhaoxue.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/126 Safari/537.36")
BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 540.0
START = time.time()

# ---------------------------------------------------------------- build worklist
d = json.loads((ROOT / "learning/content/directory.json").read_text(encoding="utf-8"))
catalog = json.loads((ROOT / "learning/home-assets/catalog.json").read_text(encoding="utf-8"))

phrase_sha = {}
tasks = {}   # url_path -> local Path

for k, v in d["images"].items():
    target = posixpath.normpath(posixpath.join("/learning/content", v["src"]))
    tasks[target] = ROOT / target.lstrip("/")
    phrase_sha[Path(target).name] = v.get("sha256", "")

for r in d["readings"]:
    for field in ("imageSrc", "imageThumb"):
        rel = r.get(field)
        if rel:
            p = "/learning/" + rel.lstrip("./")
            tasks[p] = ROOT / p.lstrip("/")

for e in catalog:
    for prefix in ("/learning/home-assets/thumbs/", "/learning/thumbs/"):
        p = f"{prefix}{e['id']}.webp"
        tasks[p] = ROOT / p.lstrip("/")

def valid_webp(p: Path) -> bool:
    if not p.exists() or p.stat().st_size < 32:
        return False
    b = p.read_bytes()[:12]
    return b[:4] == b"RIFF" and b[8:12] == b"WEBP"

todo = [u for u, loc in sorted(tasks.items()) if not valid_webp(loc)]
print(f"worklist: {len(tasks)} expected, {len(todo)} to download", flush=True)

# ---------------------------------------------------------------- fetch
import socket
import requests
import urllib3.util.connection as _u3c
_u3c.allowed_gai_family = lambda: socket.AF_INET      # force IPv4 (IPv6 path times out)

_tls = threading.local()

def _session():
    if not hasattr(_tls, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept-Encoding": "gzip, br", "Accept": "*/*"})
        ad = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=4,
                                           max_retries=0)
        s.mount("https://", ad)
        _tls.s = s
    return _tls.s

def fetch(path, tries=5):
    url = SITE + path
    last = None
    for i in range(tries):
        if time.time() - START > BUDGET:
            raise TimeoutError("budget")
        try:
            r = _session().get(url, timeout=(8, 25))
            if r.status_code == 404:
                return None          # genuinely absent, do not retry
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            raw = r.content
            if not raw:
                raise RuntimeError("empty body")
            return raw
        except TimeoutError:
            raise
        except Exception as e:
            last = e
        time.sleep(min(1.0 * (i + 1), 4.0))
    raise RuntimeError(f"{last}")

lock = threading.Lock()
stats = {"ok": 0, "skip404": 0, "fail": 0, "sha_bad": 0}
fails, notfounds, shabads = [], [], []

def work(u):
    loc = tasks[u]
    try:
        data = fetch(u)
    except TimeoutError:
        raise
    except Exception as e:
        with lock:
            stats["fail"] += 1
            fails.append((u, str(e)[:80]))
        return
    if data is None:
        with lock:
            stats["skip404"] += 1
            notfounds.append(u)
        return
    loc.parent.mkdir(parents=True, exist_ok=True)
    loc.write_bytes(data)
    name = loc.name
    if name in phrase_sha and phrase_sha[name]:
        if hashlib.sha256(data).hexdigest() != phrase_sha[name]:
            with lock:
                stats["sha_bad"] += 1
                shabads.append(u)
            return
    with lock:
        stats["ok"] += 1
    if stats["ok"] % 50 == 0:
        print(f"  ... ok={stats['ok']} 404={stats['skip404']} fail={stats['fail']} "
              f"({time.time()-START:.0f}s)", flush=True)

done_flag = {"budget_exhausted": False}
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = {ex.submit(work, u): u for u in todo}
    for fu in as_completed(futs):
        try:
            fu.result()
        except TimeoutError:
            done_flag["budget_exhausted"] = True
            break

# ---------------------------------------------------------------- report
json.dump({"fails": fails, "notfounds": notfounds, "sha_bad": shabads,
           "budget_exhausted": done_flag["budget_exhausted"]},
          open("/tmp/hx_download_state.json", "w"), ensure_ascii=False, indent=1)
print(f"DONE ok={stats['ok']} 404={stats['skip404']} fail={stats['fail']} "
      f"sha_bad={stats['sha_bad']} budget_exhausted={done_flag['budget_exhausted']}", flush=True)
if notfounds:
    print("404 list (first 10):", notfounds[:10])
if fails:
    print("fail list (first 10):", fails[:10])
