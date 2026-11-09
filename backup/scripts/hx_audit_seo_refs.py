#!/usr/bin/env python3
"""Audit every absolute https://henhaoxue.com/... reference inside the mirrored
SEO pages (and any other file). For each ref decide:
  - OK       : object exists on disk (mirror local path) -> should be rewritten to relative
  - ORIGIN403: object is in the origin-403 whitelist -> broken image on BOTH origin and mirror
  - REMOTE-OK: verified live on origin (200) earlier
Also audit ALL https://henhaoxue.com refs for cross-page links.
"""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path("/home/z/my-project/henhaoxue-site")
SITE_URL = "https://henhaoxue.com"

wl = json.loads(Path("/home/z/my-project/scripts/origin_403_assets.json").read_text())
whitelist = set(wl["paths"])

# disk set (mirror-local)
disk = set()
for f in ROOT.rglob("*"):
    if f.is_file():
        disk.add("/" + f.relative_to(ROOT).as_posix())

ref_re = re.compile(r'https://henhaoxue\.com(/[^"\'\s<>\\)\]]*)')
kinds = Counter()
broken_pages = {}   # page -> [refs that are whitelisted (origin-403)]
local_fixable = Counter()  # ref -> how many pages could use local copy

for f in ROOT.rglob("*"):
    if not f.is_file():
        continue
    if f.suffix.lower() not in (".html", ".js", ".css", ".json", ".webmanifest", ".txt", ".xml"):
        continue
    text = f.read_text(encoding="utf-8", errors="replace")
    for m in ref_re.finditer(text):
        path = m.group(1).split("#")[0].split("?")[0]
        kinds["total_refs"] += 1
        # URL-decode simple %XX? keep raw for whitelist compare
        if path in whitelist:
            kinds["whitelisted(origin-403)"] += 1
            broken_pages.setdefault(f.relative_to(ROOT).as_posix(), []).append(path)
        elif path in disk:
            kinds["available locally"] += 1
            local_fixable[path] += 1
        else:
            kinds["external (page/nav/audio etc.)"] += 1

print("== https://henhaoxue.com reference audit ==")
for k, v in kinds.items():
    print(f"  {k}: {v}")

print(f"\npages referencing whitelisted (origin-403) assets: {len(broken_pages)}")
by_kind = Counter()
for page, refs in broken_pages.items():
    for r in refs:
        by_kind["/learning/phrase-images/" in r and "phrase-img" or "other"] += 1
        by_kind["page:" + page.split("/")[0]] += 1
print("  by section:", dict(by_kind))

sample = list(broken_pages.items())[:6]
for page, refs in sample:
    print("  e.g.", page, "->", refs[:2])

Path("/tmp/seo_ref_audit.json").write_text(json.dumps(
    {"kinds": dict(kinds),
     "broken_pages": broken_pages,
     "local_fixable_top": dict(local_fixable.most_common(50))},
    ensure_ascii=False, indent=1))
print("\nreport -> /tmp/seo_ref_audit.json")
