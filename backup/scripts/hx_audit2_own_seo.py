#!/usr/bin/env python3
"""Audit every remaining henhaoxue.com reference in the mirror, categorized:

  A  <a href>            navigation (must become root-absolute or exist locally)
  B  SEO metadata        canonical / og:url / og:image / twitter:* / JSON-LD (-> mirror domain)
  C  resource hints      preload / prefetch / preconnect / dns-prefetch
  D  other attrs         img/source/link href in <link> styles etc.
  E  JS / CSS / JSON / XML / TXT / webmanifest / robots / sitemap
Output: /tmp/own_seo_audit.json + console summary of distinct targets per category.
"""
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path("/home/z/my-project/henhaoxue-site")
ORIGIN = "https://henhaoxue.com"

disk = {f.relative_to(ROOT).as_posix() for f in ROOT.rglob("*") if f.is_file()}


def local_path(url: str):
    """Map an origin URL to a path that should exist on the mirror. None if
    external (query/hash stripped, percent-decoded)."""
    p = urlparse(url)
    if p.netloc and p.netloc != "henhaoxue.com":
        return None, "external:" + p.netloc
    path = unquote(p.path) or "/"
    if path.endswith("/"):
        path += "index.html"
    return path.lstrip("/"), None


res = defaultdict(lambda: defaultdict(int))          # cat -> target -> count
files_by_cat = defaultdict(set)


def categorize_html(rel: str, text: str):
    # <a href>
    for m in re.finditer(r'<a\b[^>]*?href="(https://henhaoxue\.com[^"]*)"', text):
        res["A_a_href"][m.group(1)] += 1
        files_by_cat["A_a_href"].add(rel)
    # SEO metadata
    for m in re.finditer(r'<link\b[^>]*?rel="canonical"[^>]*?href="([^"]*henhaoxue[^"]*)"', text):
        res["B_canonical"][m.group(1)] += 1
        files_by_cat["B_canonical"].add(rel)
    for m in re.finditer(r'<meta\b[^>]*?property="(og:url|og:image|twitter:url|twitter:image|twitter:image:src)"[^>]*?content="([^"]*henhaoxue[^"]*)"', text):
        res["B_meta_" + m.group(1)][m.group(2)] += 1
        files_by_cat["B_meta"].add(rel)
    for m in re.finditer(r'"(?:url|image|@id|mainEntityOfPage|logo|contentUrl)":\s*"[^"]*henhaoxue[^"]*"', text):
        res["B_jsonld"][m.group(0)[:110]] += 1
        files_by_cat["B_jsonld"].add(rel)
    # resource hints
    for m in re.finditer(r'<link\b[^>]*?rel="(preload|prefetch|preconnect|dns-prefetch|modulepreload)"[^>]*?href="([^"]*henhaoxue[^"]*)"', text):
        res["C_hint_" + m.group(1)][m.group(2)] += 1
        files_by_cat["C_hint"].add(rel)
    # other henhaoxue occurrences in html (catch-all, skip already categorized lines)
    for line in text.splitlines():
        if "henhaoxue" not in line:
            continue
        if re.search(r'rel="canonical"|property="og:|property="twitter:|"url"|"image"|<a\b|rel="(?:preload|prefetch|preconnect|dns-prefetch|modulepreload)"', line):
            continue
        res["D_html_other"][line.strip()[:150]] += 1
        files_by_cat["D_html_other"].add(rel)


for f in ROOT.rglob("*"):
    if not f.is_file():
        continue
    rel = f.relative_to(ROOT).as_posix()
    suffix = f.suffix.lower()
    if suffix == ".html":
        categorize_html(rel, f.read_text(encoding="utf-8", errors="replace"))
    elif suffix in {".js", ".css", ".json", ".xml", ".txt", ".webmanifest", ".svg", ".md", ".webapp"} or f.name == "robots.txt":
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'https?://[a-z0-9.-]*henhaoxue\.com[^"\'\s\\)<>]*', text):
            res["E_" + suffix][m.group(0)[:150]] += 1
            files_by_cat["E_" + suffix].add(rel)

# ---- existence check for A targets ----
missing = {}
for tgt in res["A_a_href"]:
    p, why = local_path(tgt)
    if why:
        missing[tgt] = why
    elif p not in disk:
        missing[tgt] = p

out = {k: dict(v) for k, v in res.items()}
Path("/tmp/own_seo_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

total = 0
for cat in sorted(res):
    n = sum(res[cat].values())
    total += n
    print(f"\n== {cat}: {n} refs in {len(files_by_cat[cat])} files, {len(res[cat])} distinct")
    for tgt, c in sorted(res[cat].items(), key=lambda x: -x[1])[:12]:
        print(f"   {c:4d}x {tgt[:130]}")

print(f"\n<A> href targets MISSING on mirror: {len(missing)}")
for t, w in sorted(missing.items()):
    print("   MISS", t, "->", w)
print(f"\nTOTAL henhaoxue.com refs: {total}")
