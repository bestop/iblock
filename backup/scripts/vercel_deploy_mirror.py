#!/usr/bin/env python3
"""Deploy the completed full-site mirror (henhaoxue-site) to Vercel production.

Same flow as vercel_deploy.py but source = the mirror root, no preview index.
The creation response's files[] gives the authoritative file count for verification.
Token from env VERCEL_TOKEN.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "https://api.vercel.com"
TOKEN = os.environ["VERCEL_TOKEN"]
TEAM = "team_zcYRsxCIETnpi5GMwbXG25dV"
PRJ = "prj_3cmLa0pwvpXRi1uRpk8159W5zdZI"
SITE = Path("/home/z/my-project/henhaoxue-site")
QS = f"?teamId={TEAM}"


def req(method, path, payload=None, raw=None, headers=None, tries=4):
    url = f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else raw
    last = None
    for i in range(tries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", f"Bearer {TOKEN}")
        r.add_header("User-Agent", "iblock-deployer")
        if payload is not None:
            r.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            r.add_header(k, v)
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
            if err.get("code") == "file_already_exists":
                return e.code, err
            if e.code < 500 and e.code != 429:
                return e.code, err
            last = (e.code, err)
        except Exception as e:
            last = (0, str(e))
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"request failed: {method} {url}: {last}")


# --- 1. collect files -----------------------------------------------------------------
contents = {}
for f in SITE.rglob("*"):
    if f.is_file():
        contents[f.relative_to(SITE).as_posix()] = f.read_bytes()
assert "index.html" in contents
digests = {p: hashlib.sha1(b).hexdigest() for p, b in contents.items()}
print(f"files to deploy: {len(contents)} ({sum(len(b) for b in contents.values())/1048576:.1f} MB)")

# --- 2. upload (deadline-aware, resumable via file_already_exists dedupe) ------------
def upload(p):
    status, err = req("POST", f"/v2/files{QS}", raw=contents[p],
                      headers={"x-vercel-digest": digests[p],
                               "Content-Type": "application/octet-stream"})
    if status == 200 or (isinstance(err, dict) and err.get("code") == "file_already_exists"):
        return p
    raise RuntimeError(f"upload failed {p}: {status} {err}")


uploads = {}
ex = ThreadPoolExecutor(max_workers=8)
fmap = {ex.submit(upload, p): p for p in contents}
import time as _t
DEADLINE = _t.time() + float(os.environ.get("DEPLOY_SECS", "420"))
n = 0
try:
    for fu in as_completed(fmap):
        uploads[fu.result()] = True
        n += 1
        if n % 100 == 0 or n == len(contents):
            print(f"  uploaded: {n}/{len(contents)}", flush=True)
        if _t.time() > DEADLINE:
            c = sum(1 for f in fmap if f.cancel())
            print(f"  deadline hit, cancelled {c}", flush=True)
            break
finally:
    ex.shutdown(wait=False, cancel_futures=True)

if len(uploads) < len(contents):
    print(f"NOT FINISHED: {len(uploads)}/{len(contents)} uploaded - rerun")
    raise SystemExit(2)

# --- 3. deployment -----------------------------------------------------------------------
payload = {
    "name": "iblock",
    "project": PRJ,
    "target": "production",
    "files": [{"file": p, "sha": digests[p], "size": len(contents[p])} for p in contents],
    "projectSettings": {"framework": None, "buildCommand": None, "installCommand": None,
                        "outputDirectory": None, "devCommand": None},
}
status, dep = req("POST", f"/v13/deployments{QS}", payload)
if status != 200:
    raise SystemExit(f"deployment create failed: {status} {dep}")
DEP_ID = dep["id"]
print(f"deployment created: {DEP_ID} state={dep.get('readyState')} files-in-payload={len(dep.get('files', []))}")

terminal = {"READY", "ERROR", "CANCELED"}
state = None
for _ in range(80):
    status, d = req("GET", f"/v13/deployments/{DEP_ID}{QS}")
    state = d.get("readyState")
    if state in terminal:
        break
    time.sleep(3)
print(f"final state: {state}")
if state != "READY":
    print("failureReason:", json.dumps(d.get("failureReason", {}), ensure_ascii=False))
    raise SystemExit(1)

print("aliases:", [a for a in d.get("alias", [])][:5])
print("\nSUCCESS", DEP_ID)
