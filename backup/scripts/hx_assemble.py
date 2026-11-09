#!/usr/bin/env python3
"""Assemble the deployable full site from the mirror + optimization kit.

Steps: inject homepage SEO head -> robots.txt Sitemap line -> copy generated
/library pages + sitemap.xml -> brand 404.html -> vercel.json cache headers.
"""
import re
import shutil
from pathlib import Path

MIRROR = Path("/home/z/my-project/henhaoxue-site")
KIT = Path("/home/z/my-project/henhaoxue-optimization-kit")

# --- 1. inject SEO head snippet into homepage ------------------------------------
snippet = (KIT / "02-SEO基建" / "head-meta-homepage.html").read_text(encoding="utf-8")
# drop the leading usage-comment block
snippet = re.sub(r"\A<!--.*?-->\s*", "", snippet, count=1, flags=re.S)

idx_path = MIRROR / "index.html"
html = idx_path.read_text(encoding="utf-8")
if "og:site_name" not in html:
    m = re.search(r'<link rel="canonical"[^>]*>', html)
    anchor = m.group(0) if m else "<title>"
    html = html.replace(anchor, anchor + "\n" + snippet, 1)
    idx_path.write_text(html, encoding="utf-8")
    print(f"index.html: injected SEO snippet after {anchor[:40]}... (now {len(html)} B)")
else:
    print("index.html: snippet already present, skipped")

# --- 2. robots.txt: append Sitemap line -------------------------------------------
robots = MIRROR / "robots.txt"
txt = robots.read_text(encoding="utf-8")
if "Sitemap:" not in txt:
    txt = txt.rstrip() + "\n\nSitemap: https://henhaoxue.com/sitemap.xml\n"
    robots.write_text(txt, encoding="utf-8")
    print("robots.txt: Sitemap line appended")
else:
    print("robots.txt: Sitemap already present")

# --- 3. copy generated /library pages + sitemap.xml --------------------------------
site_src = KIT / "03-SEO内容页" / "site"
n = 0
for f in site_src.rglob("*"):
    if f.is_file():
        rel = f.relative_to(site_src)
        dest = MIRROR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        n += 1
print(f"copied generated pages: {n} files (library/ + sitemap.xml)")

# --- 4. 404.html --------------------------------------------------------------------
shutil.copy2(KIT / "02-SEO基建" / "404.html", MIRROR / "404.html")
print("404.html: copied (Vercel serves it automatically for static 404s)")

# --- 5. vercel.json cache headers ----------------------------------------------------
vercel = {
    "headers": [
        {
            "source": "/(.*)\\.(png|jpg|jpeg|webp|svg|ico|mp3|woff2?)",
            "headers": [{"key": "Cache-Control",
                         "value": "public, max-age=31536000, immutable"}],
        },
        {
            "source": "/(.*)\\.(js|css)",
            "headers": [{"key": "Cache-Control",
                         "value": "public, max-age=31536000, immutable"}],
        },
        {
            "source": "/learning/content/directory.json",
            "headers": [{"key": "Cache-Control",
                         "value": "public, max-age=600, stale-while-revalidate=86400"}],
        },
        {
            "source": "/library/(.*)",
            "headers": [{"key": "Cache-Control",
                         "value": "public, max-age=86400"}],
        },
        {
            "source": "/(.*)",
            "headers": [
                {"key": "X-Content-Type-Options", "value": "nosniff"},
                {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
            ],
        },
    ]
}
import json
(MIRROR / "vercel.json").write_text(
    json.dumps(vercel, ensure_ascii=False, indent=2), encoding="utf-8")
print("vercel.json: written (cache + security headers)")

# --- report ----------------------------------------------------------------------------
total = sum(1 for f in MIRROR.rglob("*") if f.is_file())
size = sum(f.stat().st_size for f in MIRROR.rglob("*") if f.is_file())
print(f"\nfull site ready: {total} files, {size/1024/1024:.2f} MB")
