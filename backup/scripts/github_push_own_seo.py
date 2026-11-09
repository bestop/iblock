#!/usr/bin/env python3
"""Incremental GitHub push: commit the 60 fixed library/readings pages
(root-level image URLs -> /learning/reading-scenes/). Changed + new paths
become new blobs; unchanged paths reuse remote SHAs; remote-only paths kept.
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
MSG = ("fix: 补齐 reader/首页动态引用资源（147 文件）——修复 #words/#scenes 图片与 reader 内容加载\n\n"
       "- reader SPA 数据源：learning/content/word-reader.json（1245 词 / 10 主题）、\n"
       "  dialogues.json、readings.json（此前缺失导致 reader 内容无法加载）\n"
       "- #words 分类封面：learning/category-covers/v1/ 20 张（400/800 双尺寸）\n"
       "- #scenes 场景封面：learning/scene-covers/ 10 张全尺寸（1200x675，此前仅有 -thumb）\n"
       "- 访客试听音频：learning/trial-audio/ 62 个（reader 访客模式音频兜底）\n"
       "- 免费层音频补全：audio/heart-v1/ 30/30、audio/heart-readings-v1/ 2、artwork/ 10 张词卡插画\n"
       "- learning/community.js（社群入口脚本，此前 404）+ api/community.js\n"
       "  （返回 {\"enabled\":false}，与原站行为一致，浮动按钮保持隐藏）\n"
       "- 原站 401 会员门控的 learn/audio/zero-gap-v1/ 30 个音频不镜像（访客走 trial-audio，\n"
       "  与原站访客视图一致）；hx_check_mirror.py 增加该白名单与全尺寸封面动态规则\n"
       "- 全部 webp 经 PIL 解码校验（修复 6 个截断损坏文件）；本地检查 3124 文件 0 缺失")


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

changed = sorted(p for p in local if p in remote and remote[p]["sha"] != local[p][1])
new_paths = sorted(p for p in local if p not in remote)
print(f"changed: {len(changed)}, new: {len(new_paths)}")
if not changed and not new_paths:
    print("nothing to push")
    raise SystemExit(0)
print("changed sample:", changed[:3])

# --- 3. upload blobs ------------------------------------------------------------------
todo = changed + new_paths


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


with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(create_blob, p) for p in todo]
    for i, fu in enumerate(as_completed(futs), 1):
        fu.result()
        if i % 10 == 0 or i == len(todo):
            print(f"  blobs created: {i}/{len(todo)}")

# --- 4. tree + commit (base_tree incremental: only changed entries) --------------------
base_tree = t["sha"]  # root tree sha of current main
print(f"base_tree: {base_tree[:12]}")
tree_payload = {"base_tree": base_tree,
                "tree": [{"path": p, "mode": local[p][0], "type": "blob", "sha": local[p][1]}
                         for p in todo]}
status, tree = req("POST", f"/repos/{REPO}/git/trees", tree_payload)
if status != 201:
    raise RuntimeError(f"tree failed: {status} {tree}")
print(f"tree created: {tree['sha'][:12]} truncated={tree.get('truncated')}")

status, cur = req("GET", f"/repos/{REPO}/git/refs/heads/main")
parent = cur["object"]["sha"]
status, commit = req("POST", f"/repos/{REPO}/git/commits", {
    "message": MSG, "tree": tree["sha"], "parents": [parent],
    "author": AUTHOR, "committer": AUTHOR,
})
if status != 201:
    raise RuntimeError(f"commit failed: {status} {commit}")
status, _ = req("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": commit["sha"]})
if status != 200:
    raise RuntimeError(f"ref update failed: {status}")
print(f"pushed commit {commit['sha'][:12]} (parent {parent[:12]})")

# --- 5. verify -------------------------------------------------------------------------
status, vt = req("GET", f"/repos/{REPO}/git/trees/main?recursive=1")
vb = {e["path"]: e["sha"] for e in vt["tree"] if e["type"] == "blob"}
miss = [p for p in local if p not in vb]
wrong = [p for p in local if p in vb and vb[p] != local[p][1]]
KEEP_REMOTE = [p for p in remote if p not in local]
gone = [p for p in KEEP_REMOTE if p not in vb]
print(f"verify: missing={len(miss)} wrong={len(wrong)} lost-docs={len(gone)} remote-total={len(vb)}")
if miss or wrong or gone:
    raise RuntimeError("verification FAILED")
print("SUCCESS")
