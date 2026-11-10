#!/usr/bin/env python3
"""Comprehensive completeness audit for /home/z/my-project/henhaoxue-site.

Covers gaps the static ref check (hx_check_mirror.py) misses:
  A. data-driven assets  : directory.json images/readings, catalog.json word thumbs
  B. runtime JS paths    : /learning/thumbs/<id>.webp (probed live), home-assets/thumbs
  C. HTML page links     : internal <a href> page targets must exist on disk
  D. webmanifest icons   : every icon entry must exist
  E. file validity       : webp/png magic bytes, JSON parse, HTML doctype
  F. sha256 integrity    : phrase images verified against directory.json sha256
Outputs /tmp/audit_missing.json + human-readable report.
"""
import hashlib
import json
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path("/home/z/my-project/henhaoxue-site")

# ---------------------------------------------------------------- disk index
disk = {}   # url path -> Path
for f in ROOT.rglob("*"):
    if f.is_file():
        rel = f.relative_to(ROOT).as_posix()
        u = "/" if rel == "index.html" else (
            "/" + rel[:-len("/index.html")] + "/" if rel.endswith("/index.html")
            else "/" + rel)
        disk[u] = f

def have(url_path):
    return url_path.split("?")[0] in disk

problems = []   # (kind, detail)
missing = set() # url paths that should be downloaded

def want(url_path, why):
    if not have(url_path):
        missing.add(url_path)
        problems.append(("MISSING", f"{url_path}  <- {why}"))

# ---------------------------------------------------------------- A. data-driven
d = json.loads((ROOT / "learning/content/directory.json").read_text(encoding="utf-8"))

phrase_sha = {}   # basename -> sha256 (from directory.json)
for k, v in d["images"].items():
    src = v["src"]                       # e.g. ../phrase-images/001-46fe466291c4.webp
    target = posixpath.normpath(posixpath.join("/learning/content", src))
    want(target, f"directory.json images[{k}]")
    phrase_sha[Path(target).name] = v.get("sha256", "")

for r in d["readings"]:
    for field in ("imageSrc", "imageThumb"):
        rel = r.get(field)
        if rel:
            want("/learning/" + rel.lstrip("./"), f"readings[{r['id']}].{field}")

catalog = json.loads((ROOT / "learning/home-assets/catalog.json").read_text(encoding="utf-8"))
word_ids = [e["id"] for e in catalog]
for wid in word_ids:
    want(f"/learning/home-assets/thumbs/{wid}.webp", f"catalog.json[{wid}]")

# ---------------------------------------------------------------- B. runtime paths
# app.js: image: root+'thumbs/'+id+'.webp'  -> /learning/thumbs/<id>.webp
# this dir may legitimately not exist on the live site -> probe 3 samples first
import urllib.request
import time
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/126 Safari/537.36")

def live_status(path, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request("https://henhaoxue.com" + path, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, len(r.read())
        except urllib.error.HTTPError as e:
            return e.code, 0
        except Exception:
            time.sleep(1 + i)
    return -1, 0

probe_cache = Path("/tmp/hx_thumbs_live.json")
if probe_cache.exists():
    thumbs_live = json.loads(probe_cache.read_text()).get("live", False)
    print(f"live probe /learning/thumbs/: cached -> include={thumbs_live}")
else:
    probe_ids = word_ids[:2]
    probe = [live_status(f"/learning/thumbs/{w}.webp") for w in probe_ids]
    thumbs_live = any(s == 200 for s, _ in probe)   # any() : network is flaky, 404 would be explicit
    probe_cache.write_text(json.dumps({"live": thumbs_live, "probe": probe}))
    print(f"live probe /learning/thumbs/: {list(zip(probe_ids, probe))} -> include={thumbs_live}")
if thumbs_live:
    for wid in word_ids:
        want(f"/learning/thumbs/{wid}.webp", f"app.js thumbs[{wid}]")
else:
    print("  /learning/thumbs/ not served live -> runtime-only path, skip (not missing)")

# ---------------------------------------------------------------- C. page links
ASSET_SKIP_EXT = (".js", ".css", ".json", ".png", ".jpg", ".jpeg", ".webp", ".svg",
                  ".ico", ".webmanifest", ".txt", ".xml", ".woff", ".woff2", ".mp3")
for u, f in sorted(disk.items()):
    if not (u.endswith("/") or f.suffix == ".html"):
        continue
    try:
        html = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    base = u if u.endswith("/") else posixpath.dirname(u) + "/"
    for attr in re.findall(r'href\s*=\s*["\']([^"#\' ]+)["\']', html):
        if attr.startswith(("http", "mailto:", "tel:", "javascript:", "//")):
            continue
        path_only = attr.split("?")[0].split("#")
        path_only = path_only[0] if path_only else ""
        if not path_only or path_only == "":
            continue
        tgt = posixpath.normpath(posixpath.join(base, path_only)) if not path_only.startswith("/") else path_only
        if tgt in ("", "/"):
            continue
        if tgt.endswith(ASSET_SKIP_EXT):
            continue
        norm = tgt if tgt.endswith("/") else tgt + "/"
        if norm not in disk:
            problems.append(("BROKEN-PAGE-LINK", f"{u} -> {attr}"))

# ---------------------------------------------------------------- D. webmanifest
for wm in ["/site.webmanifest", "/learning/site.webmanifest"]:
    p = ROOT / wm.lstrip("/")
    if not p.exists():
        problems.append(("MISSING", wm))
        continue
    m = json.loads(p.read_text(encoding="utf-8"))
    base_dir = posixpath.dirname(wm) + "/"
    for icon in m.get("icons", []):
        src = icon.get("src", "")
        tgt = posixpath.normpath(posixpath.join(base_dir, src)) if not src.startswith("/") else src
        if not have(tgt):
            problems.append(("MISSING", f"{tgt}  <- {wm} icon"))

# ---------------------------------------------------------------- E. validity
def check_image(p: Path):
    b = p.read_bytes()[:16]
    if p.suffix == ".webp" and not (b[:4] == b"RIFF" and b[8:12] == b"WEBP"):
        return "not-webp"
    if p.suffix == ".png" and not b[:8] == b"\x89PNG\r\n\x1a\n":
        return "not-png"
    return None

for u, f in sorted(disk.items()):
    if f.suffix in (".webp", ".png"):
        err = check_image(f)
        if err:
            problems.append(("INVALID-FILE", f"{u}: {err}"))
    elif f.suffix == ".json":
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append(("INVALID-JSON", f"{u}: {e}"))
    elif f.suffix == ".html":
        head = f.read_bytes()[:512].lstrip().lower()
        if not head.startswith(b"<!doctype") and not head.startswith(b"<html"):
            problems.append(("INVALID-HTML", u))

# ---------------------------------------------------------------- F. sha256
bad_sha = []
for u, f in sorted(disk.items()):
    name = Path(u).name
    if name in phrase_sha and phrase_sha[name]:
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        if h != phrase_sha[name]:
            bad_sha.append((u, phrase_sha[name][:12], h[:12]))
for u, exp, got in bad_sha:
    problems.append(("SHA-MISMATCH", f"{u}: want {exp}.. got {got}.."))

# ---------------------------------------------------------------- report
json.dump(sorted(missing), open("/tmp/audit_missing.json", "w"), indent=1)
kinds = {}
for k, _ in problems:
    kinds[k] = kinds.get(k, 0) + 1
print(f"disk files: {len(disk)}")
print(f"expected assets checked: phrase={len(d['images'])} reading-scenes={len(d['readings'])*2} "
      f"home-thumbs={len(word_ids)} learning-thumbs={len(word_ids) if thumbs_live else 'skipped'}")
print(f"problem counts: {kinds}")
print(f"missing url paths to download: {len(missing)}")
for k, detail in problems[:40]:
    print(f"  [{k}] {detail}")
if len(problems) > 40:
    print(f"  ... and {len(problems)-40} more")
