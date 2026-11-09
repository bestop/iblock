#!/usr/bin/env python3
"""Own-SEO rewrite: point canonical / og:* / twitter:* / JSON-LD / sitemap.xml /
robots.txt at the MIRROR's own domain (https://bk.hijoe.net) instead of the
origin henhaoxue.com.

Audit (hx_audit2_own_seo.py) showed the remaining 1355 origin refs are 100%
SEO metadata: 0 nav <a>, 0 resource hints, 0 JS/CSS/JSON refs -- so a uniform
host swap is safe. Every rewritten URL's path is asserted to exist on disk.
Idempotent.
"""
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path("/home/z/my-project/henhaoxue-site")
OLD = "https://henhaoxue.com"
NEW = "https://bk.hijoe.net"

disk = {f.relative_to(ROOT).as_posix() for f in ROOT.rglob("*") if f.is_file()}


def exists_for(url_tail: str) -> bool:
    p = unquote(url_tail.split("#")[0].split("?")[0])
    if p in ("", "/"):
        p = "/index.html"
    if p.endswith("/"):
        p += "index.html"
    return p.lstrip("/") in disk


pat = re.compile(re.escape(OLD) + r'(/[^\s"\'<>\\)\]]*)?')
bad, changed, total = [], [], 0

targets = [t for t in list(ROOT.rglob("*.html")) + [ROOT / "sitemap.xml", ROOT / "robots.txt"] if t.is_file()]
for f in targets:
    text = f.read_text(encoding="utf-8", errors="replace")
    if OLD not in text:
        continue
    rel = f.relative_to(ROOT).as_posix()
    my_bad = False
    for m in pat.finditer(text):
        tail = m.group(1) if m.group(1) else "/"
        if not exists_for(tail):
            bad.append((rel, OLD + tail))
            my_bad = True
    if my_bad:
        continue
    n = text.count(OLD)
    f.write_text(text.replace(OLD, NEW), encoding="utf-8")
    changed.append((rel, n))
    total += n

print(f"files changed: {len(changed)}, refs rewritten: {total}")
if bad:
    print("BAD TARGETS (path not on disk):")
    for b in bad[:20]:
        print("  ", b)
    raise SystemExit(1)

# any origin mention left anywhere text-ish?
leftover = {}
for f in ROOT.rglob("*"):
    if f.is_file() and f.suffix.lower() in {".html", ".js", ".css", ".json", ".xml", ".txt", ".webmanifest", ".svg", ".md"}:
        c = f.read_text(encoding="utf-8", errors="replace").count("henhaoxue.com")
        if c:
            leftover[f.relative_to(ROOT).as_posix()] = c
print("remaining henhaoxue.com mentions:", leftover if leftover else "none")
print("OK" if not leftover else "LEFTOVER")
