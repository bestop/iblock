#!/usr/bin/env python3
"""Wave5 补缺：trial-audio / category-covers / community.js / heart-v1 缺失音频 / content JSON"""
import json, os, sys, time, urllib.request, pathlib

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
ORIGIN = "https://henhaoxue.com"
SITE = "/home/z/my-project/henhaoxue-site"

def fetch(url, dest, tries=7):
    dest = pathlib.Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return "skip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            dest.write_bytes(data)
            return f"ok {len(data)}"
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    print(f"FAIL {url}: {last}", flush=True)
    return "fail"

def main():
    results = {}
    # 1. trial-audio（62 个基名）
    def walk(o, acc):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("audio", "src") and isinstance(v, str) and ".mp3" in v:
                    acc.add(v)
                else:
                    walk(v, acc)
        elif isinstance(o, list):
            for v in o:
                walk(v, acc)
    names = set()
    for f in ["/tmp/dialogues.json", "/tmp/readings.json",
              f"{SITE}/learning/content/word-reader.json"]:
        acc = set()
        walk(json.load(open(f)), acc)
        for s in acc:
            names.add(s.split("/")[-1])
    for n in sorted(names):
        results[f"trial-audio/{n}"] = fetch(f"{ORIGIN}/learning/trial-audio/{n}",
                                            f"{SITE}/learning/trial-audio/{n}")
    # 2. category-covers（20 张）
    covers = [l.strip() for l in open("/tmp/covers.txt") if l.strip()]
    for c in covers:
        results[f"covers/{c}"] = fetch(f"{ORIGIN}/learning/{c}", f"{SITE}/learning/{c}")
    # 3. community.js
    results["community.js"] = fetch(f"{ORIGIN}/learning/community.js",
                                    f"{SITE}/learning/community.js")
    # 4. heart-v1 本地缺失音频（以 dialogues.json 引用为准）
    acc = set()
    walk(json.load(open("/tmp/dialogues.json")), acc)
    for s in sorted(acc):
        b = s.split("/")[-1]
        dest = f"{SITE}/learning/audio/heart-v1/{b}"
        if not os.path.exists(dest):
            results[f"heart-v1/{b}"] = fetch(f"{ORIGIN}/learning/audio/heart-v1/{b}", dest)
    # 5. content JSON
    for f in ("dialogues", "readings"):
        src = f"/tmp/{f}.json"
        if os.path.exists(src):
            pathlib.Path(f"{SITE}/learning/content/{f}.json").write_bytes(open(src, "rb").read())
            results[f"content/{f}.json"] = "copied"
    ok = sum(1 for v in results.values() if v != "fail")
    print(f"\n==== summary: {ok}/{len(results)} ok ====")
    for k, v in sorted(results.items()):
        if v == "fail":
            print("  FAIL:", k)
    sys.exit(1 if "fail" in results.values() else 0)

if __name__ == "__main__":
    main()
