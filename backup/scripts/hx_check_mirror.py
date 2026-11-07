#!/usr/bin/env python3
"""Check mirror completeness: every ref found in mirrored text files must exist
on disk (or be a known 404/non-asset). Prints missing list + failures."""
import json
import posixpath
import sys
from pathlib import Path

sys.path.insert(0, "/home/z/my-project/scripts")
ROOT = Path("/home/z/my-project/henhaoxue-site")
ASSET_EXT = ("js", "mjs", "css", "json", "png", "jpg", "jpeg", "webp", "svg",
             "ico", "webmanifest", "txt", "mp3", "m4a", "ogg", "wav", "woff", "woff2")
SKIP_PREFIX = ("/admin", "/api", "/cdn-cgi")
TEXT_EXT = {".html", ".css", ".js", ".mjs", ".json", ".webmanifest", ".txt"}

# load extract_refs WITHOUT executing hx_mirror's crawl driver: exec only the
# header (imports, constants, function defs, prefix_dirs init)
_src = open("/home/z/my-project/scripts/hx_mirror.py", encoding="utf-8").read()
_cut = _src.index("prefix_dirs = set()") + len("prefix_dirs = set()")
_ns = {"__name__": "hx_impl"}
exec(compile(_src[:_cut], "hx_mirror_header", "exec"), _ns)
extract_refs = _ns["extract_refs"]

disk = set()
for f in ROOT.rglob("*"):
    if f.is_file():
        rel = f.relative_to(ROOT).as_posix()
        if rel == "index.html":
            u = "/"
        elif rel.endswith("/index.html"):
            u = "/" + rel[:-len("/index.html")] + "/"
        else:
            u = "/" + rel
        disk.add(u)

refs = set()
import re as _re
# the mirror is now its own SEO origin: absolute refs must point at the mirror
# domain (https://bk.hijoe.net) and resolve locally. Any leftover origin-domain
# mention is a failure.
_own_url = _re.compile(r'https?://bk\.hijoe\.net(/[^"\'\s<>\\)\]]*)')
_origin_url = _re.compile(r'https?://henhaoxue\.com(/[^"\'\s<>\\)\]]*)')
origin_leftover = []
for u in sorted(disk):
    rel = u.lstrip("/")
    loc = ROOT / (rel + ("index.html" if u.endswith("/") else ""))
    if loc.suffix.lower() in TEXT_EXT or u.endswith("/"):
        try:
            data = loc.read_bytes()
        except Exception:
            continue
        for r in extract_refs(u, data):
            refs.add(r)
        text = data.decode("utf-8", errors="replace")
        for m in _own_url.finditer(text):
            p = m.group(1).split("#")[0].split("?")[0]
            if p and not p.endswith("/") and "/" in p[1:]:
                refs.add(p)
        for m in _origin_url.finditer(text):
            origin_leftover.append(u + " -> " + m.group(0)[:120])

raw_missing = sorted(r for r in refs
                     if r.split("?")[0] not in disk
                     and not any(r.startswith(s) for s in SKIP_PREFIX)
                     and "$" not in r)  # skip JS template-literal artifacts

# --- dynamic asset rules: paths built by JS string concat, invisible to the
# static regex extractor. Verified against the origin + app source 2026-11.
dyn = set()
CAT = ROOT / "learning/home-assets/catalog.json"
if CAT.exists():
    for e in json.loads(CAT.read_text()):
        dyn.add(f"/learning/home-assets/thumbs/{e['id']}.webp")
        dyn.add(f"/learning/thumbs/{e['id']}.webp")
for s in ("greetings", "meetup", "directions", "supplies", "building", "survival",
          "exploring", "rescue", "teamwork", "connection"):  # app.js scene covers
    dyn.add(f"/learning/scene-covers/{s}-thumb.webp")
    dyn.add(f"/learning/scene-covers/{s}.webp")  # full-size 1200x675 list-card art
for b in ("safari", "chrome"):  # tips.js guide screenshots (page: /learning/)
    for n in (1, 2, 3, 4):
        dyn.add(f"/learning/guide-{b}/step-{n}.jpg")
dyn.add("/learning/content/word-summaries.json")  # app.js fetch, ?ids= ignored statically
dyn.add("/learning/content/access.json")  # ui/preview-access.js: base+'content/access.json'
dyn.add("/learning/reader/index.html")  # SPA route linked as root+'reader/?topic=...'
dyn.add("/learn/")  # account.js redirects members to /learn/ (mirror: -> /learning/)
refs |= dyn

# --- own API: every /api/<name> endpoint referenced by frontend JS/HTML must
# have a serverless function file api/<name>.js on the mirror disk ---
api_refs = set()
for u in sorted(disk):
    rel = u.lstrip("/")
    loc = ROOT / (rel + ("index.html" if u.endswith("/") else ""))
    if loc.suffix.lower() in TEXT_EXT or u.endswith("/"):
        try:
            text = loc.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in _re.finditer(r'/api/([a-z0-9-]+)', text):
            api_refs.add(m.group(1))
api_missing = sorted(f"/api/{n}.js" for n in api_refs
                     if not (ROOT / f"api/{n}.js").is_file())


# alias: directory.json refs "reading-scenes/..." relative to /learning/content/
# but origin hosts them at /learning/reading-scenes/ (verified: content/ 404, real 200)
ALIAS = ("/learning/content/reading-scenes/", "/learning/reading-scenes/")

# origin-403 whitelist: objects absent from henhaoxue.com itself
ORIG = Path("/home/z/my-project/scripts/origin_403_assets.json")
origin403 = set(json.loads(ORIG.read_text())["paths"]) if ORIG.exists() else set()

# member-gated on origin (HTTP 401 "请登录并兑换互动版后访问"): full-mode audio
# referenced by word-reader.json. Guests never fetch these — the reader SPA
# rewrites them to /learning/trial-audio/<basename> when access.json.member is
# false, so the mirror ships only the trial copies. Verified on origin 2026-11-04.
member_gated = set()
for _name in ("word-reader.json", "word-reader-build.json"):
    WRD = ROOT / "learning/content" / _name
    if not WRD.exists():
        continue

    def _walk(o, acc):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("audio", "src") and isinstance(v, str) and ".mp3" in v:
                    acc.add(v)
                else:
                    _walk(v, acc)
        elif isinstance(o, list):
            for v in o:
                _walk(v, acc)
    _acc = set()
    _walk(json.loads(WRD.read_text()), _acc)
    for s in _acc:
        member_gated.add(posixpath.normpath(posixpath.join("/learning/content", s)))
# g1 = 自生成 TTS 音频：镜像以 /learning/trial-audio/<basename> 提供（reader 访客态改写），
# 原站无此文件，不算真缺失
member_gated = {p for p in member_gated if not p.endswith("-g1.mp3")} | {
    "/learning/trial-audio/" + p.rsplit("/", 1)[-1]
    for p in member_gated if p.endswith("-g1.mp3")
}

missing, origin_absent = [], []
for r in raw_missing:
    p = r.split("?")[0]
    if p.startswith(ALIAS[0]):
        p2 = ALIAS[1] + p[len(ALIAS[0]):]
        if p2 in disk:
            continue  # resolved via alias
    # 自生成 TTS 音频（-g1 后缀）：实际存放于 /learning/trial-audio/<basename>
    if p.endswith("-g1.mp3"):
        p = "/learning/trial-audio/" + p.rsplit("/", 1)[-1]
    if p in origin403 or r in origin403:
        origin_absent.append(r)
    elif p in member_gated or r in member_gated:
        origin_absent.append(r)  # member-only on origin (401); guests use trial-audio
    elif p.endswith(".mp3") and p.startswith("/learning/trial-audio/") and p in disk:
        pass  # g1 改写后命中磁盘
    else:
        missing.append(r)

print(f"disk files: {len(disk)}")
print(f"refs found in mirrored text files: {len(refs)}")
print(f"frontend /api endpoints referenced: {len(api_refs)} -> {sorted(api_refs)}")
print(f"api functions missing on disk: {len(api_missing)}")
for m in api_missing:
    print("  MISS", m)
print(f"origin-domain mentions left (must be 0): {len(origin_leftover)}")
for o in origin_leftover[:10]:
    print("  LEFT", o)
print(f"absent on origin as well (expected, faithful mirror): {len(origin_absent)}")
print(f"TRULY missing (ref'd, on origin, not on disk): {len(missing)}")
for m in missing:
    print("  MISS", m)
Path("/tmp/mirror_missing.json").write_text(
    json.dumps({"truly_missing": missing, "origin_absent": origin_absent,
                "api_missing": api_missing, "origin_leftover": origin_leftover},
               ensure_ascii=False, indent=1))
import sys as _sys
_sys.exit(1 if (missing or api_missing or origin_leftover) else 0)
