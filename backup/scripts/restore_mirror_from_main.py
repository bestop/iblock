#!/usr/bin/env python3
"""Restore missing mirror files from GitHub main (bestop/iblock).
Local mirror rolls back when the sandbox recycles; the last deployed state
lives on main. This fills every missing file under learning/ (and warns on
sha mismatches without overwriting). Token from env GH_TOKEN (optional for
public repo raw fetches)."""
import base64, hashlib, json, os, sys, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = "bestop/iblock"
SITE = Path("/home/z/my-project/henhaoxue-site")
TOKEN = os.environ.get("GH_TOKEN", "")
PREFIX = sys.argv[1] if len(sys.argv) > 1 else "learning/"

def req(url, binary=False, tries=4):
    last = None
    for i in range(tries):
        r = urllib.request.Request(url)
        if TOKEN:
            r.add_header("Authorization", f"token {TOKEN}")
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("User-Agent", "iblock-restore")
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                data = resp.read()
                return json.loads(data) if not binary else data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = f"HTTP {e.code}"
        except Exception as e:
            last = str(e)
        time.sleep(1.2 * (i + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")

def git_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()

def fetch_blob(sha):
    d = req(f"https://api.github.com/repos/{REPO}/git/blobs/{sha}", binary=False)
    return base64.b64decode(d["content"])

# 1) main tree
t = req(f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1")
blobs = {e["path"]: e["sha"] for e in t["tree"] if e["type"] == "blob" and e["path"].startswith(PREFIX)}
print(f"main blobs under {PREFIX}: {len(blobs)}")

missing, mismatch = [], []
for path, sha in blobs.items():
    local = SITE / path
    if not local.exists():
        missing.append((path, sha))
    elif git_sha(local) != sha:
        mismatch.append(path)
print(f"missing locally: {len(missing)}  sha-mismatch: {len(mismatch)}")

# 2) download missing (binary-safe via blob API, base64)
def work(item):
    path, sha = item
    data = fetch_blob(sha)
    dest = SITE / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return path, len(data)

ok = fail = 0
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(work, it) for it in missing]
    for fu in as_completed(futs):
        try:
            p, n = fu.result(); ok += 1
            if ok % 40 == 0:
                print(f"  restored {ok}/{len(missing)} ...")
        except Exception as e:
            fail += 1
            print(f"  FAIL {p if 'p' in dir() else '?'}: {e}")
print(f"restored: {ok}/{len(missing)}  failed: {fail}")

if mismatch:
    print("SHA MISMATCH (not overwritten):")
    for p in mismatch[:20]:
        print("  ", p)

# 3) verify counts
for sub in ("learning/trial-audio", "learning/artwork", "learning/thumbs", "learning/content"):
    n = len(list((SITE / sub).glob("*"))) if (SITE / sub).exists() else 0
    m = sum(1 for p in blobs if p.startswith(sub + "/"))
    print(f"{sub}: local={n} main={m}")
print("RESTORE_DONE ok=%d fail=%d" % (ok, fail))
