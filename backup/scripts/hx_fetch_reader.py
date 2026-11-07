#!/usr/bin/env python3
"""Fetch the missing reader SPA (index.html + bundles) and access.json from origin,
then extract refs from the new text files and fetch anything still missing.
"""
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path("/home/z/my-project/henhaoxue-site")
ORIGIN = "https://henhaoxue.com"


def get(url, tries=7):
    err = None
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(r, timeout=25) as resp:
                data = resp.read()
                return data
        except Exception as e:
            err = e
            print(f"  retry {i+1}/{tries} {url.rsplit('/',1)[-1]}: {type(e).__name__}", flush=True)
            time.sleep(1.5 * (i + 1))
    raise err


def rel_of(url_path: str) -> Path:
    return ROOT / url_path.lstrip("/")


# --- 1. direct fetches -----------------------------------------------------------------
targets = {
    "/learning/reader/index.html": None,
    "/learning/reader/assets/index-BjbErrgc.js": None,
    "/learning/reader/assets/index-XPUi1VaI.css": None,
    "/learning/content/access.json": None,
}
for path in targets:
    dest = rel_of(path)
    if dest.exists():
        print("already on disk:", path)
        continue
    b = get(ORIGIN + path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b)
    targets[path] = len(b)
    print(f"fetched {path}: {len(b)} bytes")

# --- 2. ref closure over the new text files -------------------------------------------
ref_re = re.compile(r'["\'(=]((?:\.\./|/learning/|/app-icons/|/icons/|/demo/)[^"\'()\s<>\\;]{1,200}?)["\')]')
need = set()
for path in targets:
    dest = rel_of(path)
    if not dest.exists() or dest.suffix.lower() not in (".html", ".js", ".css", ".json"):
        continue
    t = dest.read_text(encoding="utf-8", errors="replace")
    for m in ref_re.finditer(t):
        u = m.group(1)
        if u.startswith("/learning/reader/assets/") or u.startswith("./"):
            # reader bundle sibling refs -> /learning/reader/assets/xxx ; ./ from index.html -> /learning/xxx
            if u.startswith("./") and "index.html" in path:
                u = "/learning/" + u[2:]
            elif u.startswith("./") :
                u = "/learning/reader/" + u[2:] if path.endswith("index.html") else "/learning/reader/assets/" + u[2:]
        if u.startswith("../") :
            u = "/learning/" + u[3:] if path.endswith("reader/index.html") else "/learning/reader/" + u[3:]
        u = u.split("?")[0].split("#")[0]
        if "." in u.rsplit("/", 1)[-1]:
            need.add(u)

print("\nrefs found in new files:")
disk_ok, missing = [], []
for u in sorted(need):
    p = rel_of(u)
    if p.exists() and p.stat().st_size > 0:
        disk_ok.append(u)
    else:
        missing.append(u)
print(f"  on disk: {len(disk_ok)}")
print(f"  missing: {len(missing)}")
for u in missing:
    print("   MISS", u)

# --- 3. fetch missing with path fallbacks (reader assets may sit elsewhere) ------------
for u in missing:
    candidates = [u]
    name = u.rsplit("/", 1)[-1]
    if "/reader/assets/" in u:
        candidates += ["/learning/" + name, "/learning/reader/" + name]
    got = None
    for c in candidates:
        try:
            got = get(ORIGIN + c)
            print(f"fetched {c}: {len(got)} bytes (via {c})")
            dest = rel_of(u)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(got)
            break
        except Exception:
            continue
    if got is None:
        print("STILL MISSING:", u)
