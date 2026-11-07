#!/usr/bin/env python3
"""Incremental GitHub push with resume: create blobs (cached by sha), tree,
commit. Re-runnable until SUCCESS. Token from env GH_TOKEN."""
import base64
import hashlib
import json
import os
import stat
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "https://api.github.com"
REPO = "bestop/iblock"
SITE = Path("/home/z/my-project/henhaoxue-site")
TOKEN = os.environ["GH_TOKEN"]
AUTHOR = {"name": "bestop", "email": "1335703+bestop@users.noreply.github.com"}
BLOB_CACHE = Path("/tmp/gh_blob_cache.json")


def req(method, path, payload=None, tries=5):
    url = f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    last = None
    for i in range(tries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", f"token {TOKEN}")
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("Content-Type", "application/json")
        r.add_header("User-Agent", "iblock-publisher")
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return resp.status, json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code < 500 and e.code != 403:
                return e.code, {"message": body}
            last = (e.code, body[:200])
        except Exception as e:
            last = (0, str(e))
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"request failed: {method} {url}: {last}")


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


status, t = req("GET", f"/repos/{REPO}/git/trees/main?recursive=1")
remote = {e["path"]: e["sha"] for e in t["tree"] if e["type"] == "blob"}
print(f"remote blobs: {len(remote)}")

local = {}
for f in SITE.rglob("*"):
    if f.is_file():
        rel = f.relative_to(SITE).as_posix()
        mode = "100755" if f.stat().st_mode & stat.S_IXUSR else "100644"
        local[rel] = (mode, git_blob_sha(f))
print(f"local files: {len(local)}")

drift = [p for p in local if p in remote and remote[p] != local[p][1]]
if drift:
    raise RuntimeError(f"drift: {drift}")

new_paths = sorted(p for p in local if p not in remote)
print(f"new blobs needed: {len(new_paths)}")

cache = json.loads(BLOB_CACHE.read_text()) if BLOB_CACHE.exists() else {}
todo = [p for p in new_paths if local[p][1] not in cache]
print(f"blobs to upload this run: {len(todo)} (cached: {len(cache)})")

DEADLINE = time.time() + float(os.environ.get("PUSH_SECS", "420"))


def create_blob(rel):
    mode, sha = local[rel]
    data = (SITE / rel).read_bytes()
    status, resp = req("POST", f"/repos/{REPO}/git/blobs",
                       {"content": base64.b64encode(data).decode(), "encoding": "base64"})
    if status != 201:
        raise RuntimeError(f"blob failed {rel}: {status} {resp}")
    if resp["sha"] != sha:
        raise RuntimeError(f"sha mismatch {rel}")
    return rel, sha


done = 0
ex = ThreadPoolExecutor(max_workers=8)
fmap = {ex.submit(create_blob, p): p for p in todo}
try:
    for fu in as_completed(fmap):
        rel, sha = fu.result()
        cache[sha] = True
        done += 1
        if done % 100 == 0 or done == len(todo):
            BLOB_CACHE.write_text(json.dumps(cache))
            print(f"  blobs: {done}/{len(todo)} (cache {len(cache)})", flush=True)
        if time.time() > DEADLINE:
            c = sum(1 for f in fmap if f.cancel())
            print(f"  deadline hit, cancelled {c}", flush=True)
            break
finally:
    BLOB_CACHE.write_text(json.dumps(cache))
    ex.shutdown(wait=False, cancel_futures=True)

still_needed = [p for p in new_paths if local[p][1] not in cache]
print(f"blobs still to upload: {len(still_needed)}")
if still_needed:
    print("NOT FINISHED - rerun this script")
    raise SystemExit(2)

# --- tree / commit -------------------------------------------------------------------
# flat tree of ~3000 entries exceeds the API input limit -> build incrementally
# on top of the current head tree using base_tree, in chunks of 800.
status, cur = req("GET", f"/repos/{REPO}/git/refs/heads/main")
parent = cur["object"]["sha"]
status, head_commit = req("GET", f"/repos/{REPO}/git/commits/{parent}")
base_tree = head_commit["tree"]["sha"]
print(f"base tree: {base_tree[:12]}")

entries = [{"path": p, "mode": local[p][0], "type": "blob", "sha": local[p][1]}
           for p in local if p not in remote]  # only new/changed paths
print(f"tree deltas: {len(entries)}")
CHUNK = 800
for i in range(0, len(entries), CHUNK):
    status, tree_resp = req("POST", f"/repos/{REPO}/git/trees",
                            {"base_tree": base_tree,
                             "tree": entries[i:i + CHUNK]})
    if status != 201:
        raise RuntimeError(f"tree chunk {i} failed: {status} {tree_resp}")
    base_tree = tree_resp["sha"]
    print(f"  tree chunk {i//CHUNK + 1}: {base_tree[:12]}")
status, commit = req("POST", f"/repos/{REPO}/git/commits", {
    "message": "fix: 补全 JS 动态拼接的图片资源 —— 2470 个文件\n\n"
               "- learning/home-assets/thumbs + learning/thumbs：各 1245 张单词卡缩略图\n"
               "  （首页 10 大主题图鉴与 app 恢复卡使用，路径由 JS 运行时拼接，静态爬取盲区）\n"
               "- learning/scene-covers：10 张场景封面\n"
               "- learning/guide-safari|chrome：8 张添加到主屏幕引导截图\n"
               "- learning/content/word-summaries.json：由原站 ?ids= 动态端点合成 1245 条静态数据\n"
               "- 完整性复检：3024 个资源引用 0 真实缺失",
    "tree": tree_resp["sha"], "parents": [parent],
    "author": AUTHOR, "committer": AUTHOR,
})
if status != 201:
    raise RuntimeError(f"commit failed: {status} {commit}")
status, _ = req("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": commit["sha"]})
if status != 200:
    raise RuntimeError(f"ref update failed: {status}")
print(f"pushed commit {commit['sha'][:12]}")

status, vt = req("GET", f"/repos/{REPO}/git/trees/main?recursive=1")
vb = {e["path"]: e["sha"] for e in vt["tree"] if e["type"] == "blob"}
miss = [p for p in local if vb.get(p) != local[p][1]]
print(f"verify: {len(vb)} remote blobs, mismatch/missing: {len(miss)}")
if miss:
    raise RuntimeError(f"verify failed: {miss[:5]}")
print("SUCCESS")
