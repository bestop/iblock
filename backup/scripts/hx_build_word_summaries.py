#!/usr/bin/env python3
"""Build a static /learning/content/word-summaries.json by querying the origin
dynamic endpoint in 50-id chunks. The app fetches it with ?ids=<subset> and
filters locally, so a superset static file is fully compatible."""
import json
import time
import urllib.request
from pathlib import Path

SITE = "https://henhaoxue.com"
ROOT = Path("/home/z/my-project/henhaoxue-site")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/126 Safari/537.36")

cat = json.loads((ROOT / "learning/home-assets/catalog.json").read_text())
ids = [e["id"] for e in cat]
print("catalog ids:", len(ids))

words = {}
CACHE = Path("/tmp/wordsumm_cache.json")
if CACHE.exists():
    words = json.loads(CACHE.read_text())
    print("resume from cache:", len(words), "words")
todo = [ids[i:i + 50] for i in range(0, len(ids), 50)]
for n, chunk in enumerate(todo, 1):
    if all(i in words for i in chunk):
        continue
    url = f"{SITE}/learning/content/word-summaries.json?ids=" + ",".join(chunk)
    for attempt in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": UA}), timeout=45)
            data = json.loads(r.read().decode())
            for w in data.get("words", []):
                words[w["id"]] = w
            CACHE.write_text(json.dumps(words, ensure_ascii=False))
            break
        except Exception as e:
            if attempt == 2:
                print(f"  chunk {n} FAILED: {str(e)[:80]}", flush=True)
            time.sleep(1 + attempt)
    if n % 3 == 0 or n == len(todo):
        print(f"  {n}/{len(todo)} chunks, unique words: {len(words)}", flush=True)

out = ROOT / "learning/content/word-summaries.json"
missing = [i for i in ids if i not in words]
print("collected:", len(words), " missing ids:", len(missing))
payload = {"words": [words[i] for i in ids if i in words]}
out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
               encoding="utf-8")
print(f"written {out} ({out.stat().st_size/1024:.0f} KB)")
if missing:
    Path("/tmp/wordsumm_missing.json").write_text(json.dumps(missing))
