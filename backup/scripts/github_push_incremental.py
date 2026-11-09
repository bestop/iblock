#!/usr/bin/env python3
"""Incremental GitHub push: add the 94 newly-mirrored assets to bestop/iblock.

Reuses existing remote blob SHAs for unchanged paths (all 410 verified identical),
creates blobs only for new files, then commits with parent = current main.
Token from env GH_TOKEN.
"""
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


# --- 1. remote tree ----------------------------------------------------------------
status, t = req("GET", f"/repos/{REPO}/git/trees/main?recursive=1")
if status != 200:
    raise RuntimeError(f"tree read failed: {status}")
remote = {e["path"]: e for e in t["tree"] if e["type"] == "blob"}
print(f"remote blobs: {len(remote)}")

# --- 2. local inventory -------------------------------------------------------------
local = {}
for f in SITE.rglob("*"):
    if f.is_file():
        rel = f.relative_to(SITE).as_posix()
        mode = "100755" if f.stat().st_mode & stat.S_IXUSR else "100644"
        local[rel] = (mode, git_blob_sha(f))
print(f"local files: {len(local)}")

# sanity: every local path already on remote must have identical sha
drift = [p for p in local if p in remote and remote[p]["sha"] != local[p][1]]
if drift:
    raise RuntimeError(f"local/remote drift on: {drift}")
print(f"drift check OK ({len(local) & len(remote) if False else sum(1 for p in local if p in remote)} shared paths identical)")

# --- 3. decide what to upload -------------------------------------------------------
new_paths = sorted(p for p in local if p not in remote)
print(f"new blobs needed: {len(new_paths)}")


def create_blob(rel):
    mode, sha = local[rel]
    data = (SITE / rel).read_bytes()
    status, resp = req("POST", f"/repos/{REPO}/git/blobs",
                       {"content": base64.b64encode(data).decode(), "encoding": "base64"})
    if status != 201:
        raise RuntimeError(f"blob failed {rel}: {status} {resp}")
    if resp["sha"] != sha:
        raise RuntimeError(f"remote blob sha mismatch for {rel}")
    return rel, mode, resp["sha"]


blobs = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(create_blob, p) for p in new_paths]
    for i, fu in enumerate(as_completed(futs), 1):
        rel, mode, sha = fu.result()
        blobs[rel] = (mode, sha)
        if i % 20 == 0 or i == len(new_paths):
            print(f"  blobs created: {i}/{len(new_paths)}")

# --- 4. build tree -------------------------------------------------------------------
KEEP_REMOTE = [p for p in remote if p not in local]  # docs/, README.md, .gitignore
print(f"keeping remote-only paths: {len(KEEP_REMOTE)}")
tree_payload = {"tree": []}
for rel, (mode, sha) in local.items():
    tree_payload["tree"].append({"path": rel, "mode": mode, "type": "blob", "sha": sha})
for rel in KEEP_REMOTE:
    tree_payload["tree"].append({"path": rel, "mode": remote[rel]["mode"],
                                 "type": "blob", "sha": remote[rel]["sha"]})
status, tree = req("POST", f"/repos/{REPO}/git/trees", tree_payload)
if status != 201:
    raise RuntimeError(f"tree failed: {status} {tree}")
print(f"tree created: {tree['sha'][:12]} truncated={tree.get('truncated')}")

# --- 5. commit + push -----------------------------------------------------------------
status, cur = req("GET", f"/repos/{REPO}/git/refs/heads/main")
parent = cur["object"]["sha"]
status, commit = req("POST", f"/repos/{REPO}/git/commits", {
    "message": "fix: 补全镜像缺失资源 —— 94 个文件\n\n"
               "- learning/phrase-images：+28 张真实短语配图（170 张空占位短语图片原站即无，保持一致）\n"
               "- learning/reading-scenes：+60 张 -400- 阅读场景小图\n"
               "- learning/audio/heart-v1：+4 个对话发音 mp3\n"
               "- app-icons：+ diamond-192 / diamond-512（site.webmanifest 引用）\n"
               "- 完整性复检：555 个资源引用，0 真实缺失（170 个为原站本身 403/404，忠实镜像）",
    "tree": tree["sha"], "parents": [parent],
    "author": AUTHOR, "committer": AUTHOR,
})
if status != 201:
    raise RuntimeError(f"commit failed: {status} {commit}")
status, _ = req("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": commit["sha"]})
if status != 200:
    raise RuntimeError(f"ref update failed: {status}")
print(f"pushed commit {commit['sha'][:12]} (parent {parent[:12]})")

# --- 6. verify -------------------------------------------------------------------------
status, vt = req("GET", f"/repos/{REPO}/git/trees/main?recursive=1")
vb = {e["path"]: e["sha"] for e in vt["tree"] if e["type"] == "blob"}
miss = [p for p in local if p not in vb]
wrong = [p for p in local if p in vb and vb[p] != local[p][1]]
gone = [p for p in KEEP_REMOTE if p not in vb]
print(f"verify: missing={len(miss)} wrong={len(wrong)} lost-docs={len(gone)} remote-total={len(vb)}")
if miss or wrong or gone:
    raise RuntimeError("verification FAILED")
print("SUCCESS")
