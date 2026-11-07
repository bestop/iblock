#!/usr/bin/env python3
"""Mirror henhaoxue.com static site into /home/z/my-project/henhaoxue-site/

BFS crawl: seed pages -> extract refs (HTML/CSS/JS/JSON) -> download until closure.
Robust against the flaky Cloudflare origin: retries with backoff, gzip/br decode.
"""
import gzip
import json
import os
import posixpath
import re
import sys
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SITE = "https://henhaoxue.com"
ROOT = Path("/home/z/my-project/henhaoxue-site")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/126 Safari/537.36")

ASSET_EXT = ("js", "mjs", "css", "json", "png", "jpg", "jpeg", "webp", "svg",
             "ico", "webmanifest", "txt", "mp3", "m4a", "ogg", "wav", "woff", "woff2")
SKIP_PREFIX = ("/admin", "/api", "/cdn-cgi")
SKIP_PATHS = set()  # filled dynamically

downloaded = {}   # url_path -> local Path
failed = {}       # url_path -> reason


def fetch(path, tries=3, timeout=20):
    """Fetch SITE+path, return decoded bytes. Retries on failure/short body."""
    url = SITE + path
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept-Encoding": "gzip, br",
                "Accept": "*/*",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                enc = (r.headers.get("Content-Encoding") or "").lower()
                if enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "br":
                    import brotli
                    raw = brotli.decompress(raw)
                elif enc == "deflate":
                    try:
                        raw = zlib.decompress(raw)
                    except zlib.error:
                        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                if not raw:
                    raise RuntimeError("empty body")
                return raw
        except Exception as e:
            last = e
            time.sleep(1.0 + 1.0 * i)
    raise RuntimeError(f"{last}")


def url_to_local(path):
    """Map URL path (root-relative, with query) to local file path."""
    p = path.split("#")[0].split("?")[0]
    if not p.startswith("/"):
        return None
    p = posixpath.normpath(p)
    if p == "." or p.startswith("..") or p.startswith("/../"):
        return None
    if any(p.startswith(s) for s in SKIP_PREFIX):
        return None
    rel = p.lstrip("/")
    if rel == "":
        rel = "index.html"
    # dirs without extension -> index.html
    if "." not in posixpath.basename(rel):
        rel = rel.rstrip("/") + "/index.html"
    return ROOT / rel


def resolve(base_url_path, ref):
    """Resolve possibly-relative ref against the URL path of the containing file."""
    ref = ref.strip().replace("\\/", "/")
    if not ref or ref.startswith(("data:", "#", "mailto:", "javascript:", "http://", "https://")):
        return None
    if ref.startswith("//"):
        return None
    if ref.startswith("/"):
        return ref.split("#")[0]
    base = base_url_path.split("?")[0].split("#")[0]
    base_dir = posixpath.dirname(base)
    joined = posixpath.normpath(posixpath.join(base_dir, ref))
    if not joined.startswith("/"):
        joined = "/" + joined
    return joined.split("#")[0]


def extract_refs(url_path, data):
    """Extract candidate root-relative URLs from a file's bytes."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return set()
    refs = set()
    low = url_path.lower()
    base = low.split("?")[0]
    bn = posixpath.basename(base.rstrip("/"))
    is_html = base.endswith("/") or base.endswith(".html") or ("." not in bn)
    is_css = low.endswith(".css")
    is_js = low.endswith((".js", ".mjs"))

    if is_html:
        for m in re.findall(r'(?:src|href|poster|data-src)\s*=\s*["\']([^"\']+)["\']', text):
            refs.add(m)
        for m in re.findall(r'srcset\s*=\s*["\']([^"\']+)["\']', text):
            for part in m.split(","):
                refs.add(part.strip().split(" ")[0])
        for m in re.findall(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)', text):
            refs.add(m[1])
    if is_css:
        for m in re.findall(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)', text):
            refs.add(m[1])
        for m in re.findall(r'@import\s+["\']([^"\']+)["\']', text):
            refs.add(m)
    if is_js:
        # absolute-root paths with asset ext
        for m in re.findall(r'["\'](/[^"\'\s()<>\\]{2,200}?)["\']', text):
            if m.lower().endswith(ASSET_EXT):
                refs.add(m)
        # relative paths (module imports, fetches) resolved per-file
        for m in re.findall(r'["\'](\.{1,2}/[^"\'\s()<>\\]{2,200}?)["\']', text):
            if m.lower().endswith(ASSET_EXT):
                refs.add(m)
        # path-prefix concat patterns e.g. '/learning/img/x/' + y + '.png'
        for m in re.findall(r'["\'](/[^"\']{2,120}/)["\']', text):
            if "/img" in m or "images" in m or "scenes" in m or "content" in m:
                prefix_dirs.add(m)
    if low.endswith(".json") or low.endswith(".webmanifest"):
        # absolute AND relative refs (e.g. "../phrase-images/x.webp",
        # "reading-scenes/y.webp"); require at least one "/" to avoid
        # matching bare filenames inside prose strings
        for m in re.findall(
                r'["\']((?:\.{1,2}/)?[^"\'\s()<>\\]*?/[^"\'\s()<>\\]{1,200}?)["\']', text):
            if not m.lower().endswith(ASSET_EXT):
                continue
            # skip MIME types like "image/png" that also end in an asset ext
            if re.fullmatch(r"(?:\.{1,2}/)?(?:image|audio|video|text|font|application)/[\w.+-]+",
                            m, re.I):
                continue
            refs.add(m)
    out = set()
    for r in refs:
        u = resolve(url_path, r)
        if u and u.lower().split("?")[0].endswith(ASSET_EXT):
            out.add(u)
    return out


prefix_dirs = set()

# --- seed definitions ----------------------------------------------------------
seeds = {
    "/": open("/tmp/seed_home.html", "rb").read(),
    "/learning/": open("/tmp/seed_learning.html", "rb").read(),
    "/account/": open("/tmp/seed_account.html", "rb").read(),
    "/learning/account/": None,  # fetch during crawl
}
queue = []       # url paths to download
text_cache = {}  # url path -> bytes, for parsing

def local_for(url_path):
    return url_to_local(url_path)

def enqueue(path):
    if not path or failed.get(path):
        return
    if path in downloaded or path in queue or path in SKIP_PATHS:
        return
    loc = local_for(path)
    if loc is None:
        return
    if loc.exists() and loc.stat().st_size > 0:  # already mirrored
        downloaded[path] = loc
        if loc.suffix.lower() in TEXT_EXT:
            pending_parse.append((path, loc.read_bytes()))
        return
    if loc.suffix.lower() not in {".html"} and loc.suffix.lower() != "" and \
       loc.suffix.lower().lstrip(".") not in ASSET_EXT:
        return
    queue.append(path)

# --- main crawl loop ------------------------------------------------------------
ROOT.mkdir(parents=True, exist_ok=True)
pending_parse = []  # (url_path, bytes)

# resume: prepopulate from files already on disk (prior partial runs)
TEXT_EXT = {".html", ".css", ".js", ".mjs", ".json", ".webmanifest", ".txt"}
for f in ROOT.rglob("*"):
    if f.is_file() and f.stat().st_size > 0:
        rel = f.relative_to(ROOT).as_posix()
        if rel == "index.html":
            p = "/"
        elif rel.endswith("/index.html"):
            p = "/" + rel[:-len("/index.html")] + "/"
        else:
            p = "/" + rel
        downloaded[p] = f
        if f.suffix.lower() in TEXT_EXT:
            pending_parse.append((p, f.read_bytes()))
if downloaded:
    print(f"resume: {len(downloaded)} files already on disk")

def download_one(path):
    loc = local_for(path)
    if loc.exists() and loc.stat().st_size > 0:  # resumable: skip existing
        return path, loc.read_bytes(), loc
    global fetched_n
    fetched_n += 1
    data = fetch(path)
    loc.parent.mkdir(parents=True, exist_ok=True)
    loc.write_bytes(data)
    return path, data, loc

fetched_n = 0
LIMIT = int(os.environ.get("LIM", "0") or 0)

ROUND = 0
while True:
    ROUND += 1
    # seed refs from HTML cache
    if ROUND == 1:
        for sp, html in seeds.items():
            if html is not None:
                text_cache[sp] = html
                loc = local_for(sp)
                loc.parent.mkdir(parents=True, exist_ok=True)
                loc.write_bytes(html)
                downloaded[sp] = loc
                for u in extract_refs(sp, html):
                    enqueue(u)
        # known essentials (incl. the /learning/account/ page variant)
        for extra in ("/learning/account/", "/learning/content/directory.json",
                      "/robots.txt", "/site.webmanifest", "/learning/site.webmanifest",
                      "/release-notice.js", "/404.html"):
            enqueue(extra)

    batch = [p for p in queue]
    queue.clear()
    if not batch:
        break
    if LIMIT:
        batch = batch[:LIMIT - fetched_n]
        if not batch:
            print(f"LIMIT {LIMIT} reached, stopping this run")
            break
    print(f"[round {ROUND}] downloading {len(batch)} files...", flush=True)
    done_n = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(download_one, p): p for p in batch}
        for fu in as_completed(futs):
            p = futs[fu]
            try:
                path, data, loc = fu.result()
                downloaded[path] = loc
                low = path.lower().split("?")[0]
                if low.endswith(tuple(TEXT_EXT)):
                    pending_parse.append((path, data))
            except Exception as e:
                failed[p] = str(e)[:120]
            done_n += 1
            if done_n % 15 == 0 or done_n == len(batch):
                print(f"  {done_n}/{len(batch)} (ok={len(downloaded)}, fail={len(failed)})", flush=True)
    # parse downloaded text files for new refs
    for path, data in pending_parse:
        text_cache[path] = data
        for u in extract_refs(path, data):
            enqueue(u)
    pending_parse.clear()

# --- retry failures once more serially -------------------------------------------
retry = dict(failed)
failed.clear()
for p in list(retry)[:10]:
    try:
        path, data, loc = download_one(p)
        downloaded[path] = loc
        low = path.lower().split("?")[0]
        if low.endswith((".html", ".css", ".js", ".mjs", ".json", ".webmanifest", ".txt")):
            for u in extract_refs(path, data):
                enqueue(u)
    except Exception as e:
        failed[p] = str(e)[:120]
# flush any refs discovered by retry parse
while queue:
    batch = list(queue); queue.clear()
    for p in batch:
        try:
            path, data, loc = download_one(p)
            downloaded[path] = loc
        except Exception as e:
            failed[p] = str(e)[:120]

# --- report -----------------------------------------------------------------------
total_size = sum(f.stat().st_size for f in ROOT.rglob("*") if f.is_file())
print(f"\ndownloaded: {len(downloaded)} files, {total_size/1024/1024:.2f} MB")
print(f"failed: {len(failed)}")
for p, why in sorted(failed.items()):
    print("  FAIL", p, "->", why)
Path("/tmp/mirror_downloaded.json").write_text(json.dumps(sorted(downloaded), ensure_ascii=False, indent=1))
Path("/tmp/mirror_failed.json").write_text(json.dumps(failed, ensure_ascii=False, indent=1))
print("inventory -> /tmp/mirror_downloaded.json")
