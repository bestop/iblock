#!/usr/bin/env python3
"""Deploy ONLY the 4 new files to Vercel using the legacy v2 inlined-files format,
avoiding POST /v2/files (rate-limited). Existing 2973 files are referenced by
digest (blobs already in Vercel's store from today's earlier deploys).
"""
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.vercel.com"
TOKEN = os.environ["VERCEL_TOKEN"]
TEAM = "team_zcYRsxCIETnpi5GMwbXG25dV"
PRJ = "prj_3cmLa0pwvpXRi1uRpk8159W5zdZI"
SITE = Path("/home/z/my-project/henhaoxue-site")
QS = f"?teamId={TEAM}"

NEW = None  # computed dynamically: files differing from the previous production deployment


def latest_ready_production():
    st, d = req("GET", f"/v6/deployments{QS}&projectId={PRJ}&target=production&state=READY&limit=1")
    if st != 200 or not d.get("deployments"):
        raise SystemExit(f"cannot find latest production deployment: {st} {json.dumps(d)[:200]}")
    dep = d["deployments"][0]
    dep_id = dep.get("id") or dep.get("uid")
    print(f"prev production deployment: {dep_id} ({dep.get('url')})", flush=True)
    return dep_id


PREV_DEP = None  # resolved after req() is defined (latest READY production deploy)


def req(method, path, payload=None, tries=4):
    url = f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    last = None
    for i in range(tries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", f"Bearer {TOKEN}")
        r.add_header("User-Agent", "iblock-deployer")
        if payload is not None:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                body = resp.read().decode()
                return resp.status, json.loads(body) if body.strip().startswith(("{", "[")) else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                err = json.loads(body).get("error", {})
            except Exception:
                err = {"message": body[:200]}
            if e.code < 500 and e.code != 429:
                return e.code, err
            last = (e.code, err)
            print(f"  http {e.code}: {err.get('code') or err.get('message','')[:80]}", flush=True)
        except Exception as e:
            last = (0, str(e))
            print(f"  net: {type(e).__name__}", flush=True)
        time.sleep(2 * (i + 1))
    return last[0], last[1]


# inventory all files
PREV_DEP = latest_ready_production()
contents = {}
for f in SITE.rglob("*"):
    if f.is_file():
        contents[f.relative_to(SITE).as_posix()] = f.read_bytes()
digests = {p: hashlib.sha1(b).hexdigest() for p, b in contents.items()}
print(f"total files: {len(contents)}", flush=True)

# diff against previous deployment's uid (sha1) tree under its src/ root
status, prev_tree = req("GET", f"/v2/deployments/{PREV_DEP}/files{QS}")
if status != 200:
    raise SystemExit(f"prev tree failed: {status} {prev_tree}")


def flatten(nodes, prefix=""):
    out = {}
    for n in nodes:
        if n.get("type") == "file":
            out[prefix + n["name"]] = n.get("uid")
        elif n.get("children"):
            out.update(flatten(n["children"], prefix + n["name"] + "/"))
    return out


prev = flatten(prev_tree)
NEW = sorted(p for p in contents if prev.get("src/" + p) != digests[p])
print(f"changed vs previous deployment: {len(NEW)}", flush=True)
for p in NEW[:10]:
    print("   CHG", p, flush=True)

assert NEW, "nothing changed - no deploy needed"

# 新增:二进制大文件先经 /v2/files 预上传（避免部署体超过 10MB 限制）
BINARY_EXT = (".webp", ".mp3", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2")
pre_up = [p for p in NEW if p.endswith(BINARY_EXT)]
if pre_up:
    print(f"pre-uploading {len(pre_up)} binary files via /v2/files ...", flush=True)
    done_up = 0
    for p in pre_up:
        b = contents[p]
        # 上传用原始字节而非 JSON
        ok2 = False
        dg = digests[p]
        for i in range(4):
            try:
                rq = urllib.request.Request(f"{API}/v2/files{QS}&filename={urllib.parse.quote(p)}",
                                            data=b, method="POST")
                rq.add_header("Authorization", f"Bearer {TOKEN}")
                rq.add_header("User-Agent", "iblock-deployer")
                rq.add_header("Content-Type", "application/octet-stream")
                rq.add_header("x-vercel-digest", dg)
                rq.add_header("Content-Length", str(len(b)))
                with urllib.request.urlopen(rq, timeout=90) as resp:
                    resp.read()
                ok2 = True
                break
            except urllib.error.HTTPError as e2:
                if e2.code == 409:  # 已存在同 sha
                    ok2 = True
                    break
                msg2 = e2.read().decode(errors="replace")[:100]
                print(f"  up http {e2.code}: {msg2}", flush=True)
                if e2.code not in (429, 500, 502, 503):
                    break
            except Exception as e2:
                print(f"  up net: {type(e2).__name__}", flush=True)
            time.sleep(2 * (i + 1))
        if not ok2:
            raise SystemExit(f"pre-upload failed: {p}")
        done_up += 1
        if done_up % 50 == 0:
            print(f"  uploaded {done_up}/{len(pre_up)}", flush=True)
        time.sleep(0.25)
    print(f"pre-upload done: {done_up}", flush=True)

# legacy v2 deployment with inlined new files + digest refs for existing ones
files = []
for p, b in contents.items():
    if p in NEW and not p.endswith(BINARY_EXT):
        files.append({"file": p, "data": base64.b64encode(b).decode(),
                      "encoding": "base64"})
    else:
        files.append({"file": p, "sha": digests[p], "size": len(b)})
payload = {
    "name": "iblock",
    "project": PRJ,
    "target": "production",
    "files": files,
    "projectSettings": {"framework": None, "buildCommand": None, "installCommand": None,
                        "outputDirectory": None, "devCommand": None},
}
status, dep = req("POST", "/v13/deployments" + QS, payload)
print("deploy status:", status, flush=True)
if status != 200:
    print(json.dumps(dep, ensure_ascii=False)[:600])
    raise SystemExit(1)
DEP_ID = dep["id"]
print("deployment:", DEP_ID, dep.get("readyState"), flush=True)

terminal = {"READY", "ERROR", "CANCELED"}
state = None
for _ in range(80):
    status, d = req("GET", f"/v13/deployments/{DEP_ID}{QS}")
    state = d.get("readyState")
    if state in terminal:
        break
    time.sleep(3)
print("final state:", state)
if state != "READY":
    print("failureReason:", json.dumps(d.get("failureReason", {}), ensure_ascii=False)[:400])
    raise SystemExit(1)
print("aliases:", [a for a in d.get("alias", [])][:5])
print("SUCCESS", DEP_ID)
