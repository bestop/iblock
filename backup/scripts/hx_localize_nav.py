#!/usr/bin/env python3
"""Localize origin-absolute navigation & asset refs so the mirror is self-contained:

1. index.html: <a href="https://henhaoxue.com/learning/"> -> href="/learning/"  (4 CTA links)
2. All *.html: <img|source src/srcset="https://henhaoxue.com/x"> -> "/x"  (30 asset refs)
3. learning/home-account.js: selector 'a[href="https://henhaoxue.com/learning/"]'
   -> 'a[href="/learning/"]' so the member/guest render() logic keeps working.

Kept absolute on purpose (SEO metadata, resolves on origin): canonical, og:*,
twitter:*, JSON-LD, sitemap.xml, robots.txt.
"""
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/henhaoxue-site")
ORIGIN = "https://henhaoxue.com"

changed = []

# --- 1. homepage nav links -------------------------------------------------------------
hp = ROOT / "index.html"
t = hp.read_text(encoding="utf-8")
n_before = t.count(f'href="{ORIGIN}/learning/"')
t = t.replace(f'href="{ORIGIN}/learning/"', 'href="/learning/"')
hp.write_text(t, encoding="utf-8")
changed.append(("index.html", f"{n_before} nav links"))
print(f"index.html: {n_before} <a> hrefs localized")

# --- 2. img/source asset refs site-wide ------------------------------------------------
tag_re = re.compile(r"<(?:img|source)\b[^>]*>")
total_assets = 0
for f in ROOT.rglob("*.html"):
    t = f.read_text(encoding="utf-8")
    if ORIGIN not in t:
        continue
    n = 0

    def fix_tag(m):
        global total_assets
        tag = m.group(0)
        if ORIGIN not in tag:
            return tag
        c = tag.count(ORIGIN)
        total_assets += c
        return tag.replace(ORIGIN, "")

    t2 = tag_re.sub(fix_tag, t)
    if t2 != t:
        f.write_text(t2, encoding="utf-8")
        changed.append((f.as_posix(), "asset refs"))
print(f"img/source asset refs localized: {total_assets} across {sum(1 for c in changed[1:])} pages")

# --- 3. home-account.js selector ---------------------------------------------------------
js = ROOT / "learning/home-account.js"
t = js.read_text(encoding="utf-8")
old = f'a[href="{ORIGIN}/learning/"]'
if old in t:
    t = t.replace(old, 'a[href="/learning/"]')
    js.write_text(t, encoding="utf-8")
    print("home-account.js: selector updated")
else:
    print("home-account.js: selector already localized")

# --- 4. verification ----------------------------------------------------------------------
left_a = left_img = 0
for f in ROOT.rglob("*.html"):
    t = f.read_text(encoding="utf-8")
    left_a += len(re.findall(r"<a\b[^>]*?href=[\"\\']" + ORIGIN, t))
    left_img += len(re.findall(r"<(?:img|source)\b[^>]*?\b(?:src|srcset)=[\"\\']" + ORIGIN, t))
print(f"REMAINING <a> origin nav: {left_a} | <img/source> origin src: {left_img}")
print("OK" if not left_a and not left_img else "INCOMPLETE")
