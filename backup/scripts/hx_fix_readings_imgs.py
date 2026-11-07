#!/usr/bin/env python3
"""Fix library/readings SEO pages: root-level image URLs missing the
/learning/reading-scenes/ prefix.

  <img src="https://henhaoxue.com/<name>.webp">
    -> src="../../../learning/reading-scenes/<name>.webp"   (local mirror copy)

  og:image / twitter:image / JSON-LD "image"
    -> https://henhaoxue.com/learning/reading-scenes/<name>.webp  (absolute, correct path)

Idempotent: skips pages already fixed. Asserts every target exists on disk.
"""
import json
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/henhaoxue-site")
READINGS = ROOT / "library/readings"
SC = "https://henhaoxue.com/"

disk = {f.relative_to(ROOT).as_posix() for f in ROOT.rglob("*") if f.is_file()}
pat = re.compile(re.escape(SC) + r'([^"/\s<>\\)\]]+\.webp)')  # root-level only

fixed_pages, already, errors = [], [], []
total_sub = 0

for page in sorted(READINGS.glob("*/index.html")):
    rel = page.relative_to(ROOT).as_posix()
    text = page.read_text(encoding="utf-8")
    hits = pat.findall(text)
    if not hits:
        continue
    # verify availability
    for name in set(hits):
        if "learning/reading-scenes/" + name not in disk:
            errors.append((rel, name, "not on disk"))
    if errors and any(e[0] == rel for e in errors):
        continue
    n_sub = 0

    def sub_img(m):
        global n_sub
        name = m.group(1)
        n_sub += 1
        return f'src="../../../learning/reading-scenes/{name}"'

    # 1) <img src> -> local relative
    text = re.sub(r'src="' + re.escape(SC) + r'([^"/\s<>\\)\]]+\.webp)"', sub_img, text)

    # 2) meta og:image / twitter:image -> correct absolute path
    def sub_meta(m):
        global n_sub
        n_sub += 1
        return m.group(1) + SC + "learning/reading-scenes/" + m.group(2) + '"'

    text = re.sub(r'(content=")' + re.escape(SC) + r'([^"/\s<>\\)\]]+\.webp)"', sub_meta, text)

    # 3) JSON-LD "image": "https://henhaoxue.com/<name>" -> correct absolute path
    def sub_jsonld(m):
        global n_sub
        n_sub += 1
        return m.group(1) + SC + "learning/reading-scenes/" + m.group(2) + '"'

    text = re.sub(r'("image":\s*")' + re.escape(SC) + r'([^"/\s<>\\)\]]+\.webp)"', sub_jsonld, text)

    if n_sub:
        page.write_text(text, encoding="utf-8")
        fixed_pages.append((rel, n_sub))
        total_sub += n_sub
    else:
        already.append(rel)

print(f"pages fixed: {len(fixed_pages)}, substitutions: {total_sub}, already-ok: {len(already)}")
if errors:
    print("ERRORS:")
    for e in errors[:20]:
        print("  ", e)
    raise SystemExit(1)

# --- final assertion: zero root-level webp refs remain anywhere ---
left = []
for f in ROOT.rglob("*.html"):
    for m in pat.finditer(f.read_text(encoding="utf-8", errors="replace")):
        left.append((f.relative_to(ROOT).as_posix(), m.group(1)))
print("remaining root-level webp refs:", len(left))
for l in left[:5]:
    print("  LEFT", l)

Path("/tmp/readings_fix.json").write_text(json.dumps(
    {"fixed": fixed_pages, "remaining": left}, ensure_ascii=False, indent=1))
print("OK" if not left else "INCOMPLETE")
