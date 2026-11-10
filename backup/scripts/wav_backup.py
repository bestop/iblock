#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Off-sandbox persistent backup for the animals pipeline (GitHub branch
`wav-backup`, orphan tree containing only backup/* paths).

 WHY: sandbox recycles roll back /home/z/my-project and have twice wiped
 hours of TTS wav output. This keeps raw_animals wav, gen_art PNGs, scripts
 and the SDK tarball safe on GitHub; `pull` restores them after any rollback.

 Usage: python3 wav_backup.py push | pull
 Token from env GH_TOKEN. NEVER backs up: .deploy_env, scripts with
 hardcoded tokens (hx_discover_ids.py, hx_verify_remote.py)."""
import base64, hashlib, json, os, sys, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "https://api.github.com"
REPO = "bestop/iblock"
BR = "wav-backup"
TOKEN = os.environ["GH_TOKEN"]
P = "/home/z/my-project"
MAPS = [  # (remote_prefix, local_dir, local_glob relative)
    ("backup/raw_animals/", f"{P}/gen_tts/raw_animals", "*.wav"),
    ("backup/gen_art/",     f"{P}/gen_art",             "*"),
    ("backup/scripts/",     f"{P}/scripts",             "*"),
    ("backup/sdk/",         f"{P}/gen_tts/sdk_backup",  "*.tgz"),
]
INCLUDE_EXT = {".py", ".sh", ".mjs", ".json", ".png", ".tgz", ".wav"}
EXCLUDE = {".deploy_env", "hx_discover_ids.py", "hx_verify_remote.py"}

def req(method, url, payload=None, tries=5, raw=False):
    data = json.dumps(payload).encode() if payload is not None else None
    last = None
    for i in range(tries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", f"token {TOKEN}")
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("Content-Type", "application/json")
        r.add_header("User-Agent", "iblock-backup")
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                b = resp.read()
                return resp.status, (b if raw else json.loads(b.decode() or "{}"))
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 404:
                return 404, {}
            if e.code < 500 and e.code != 403:
                return e.code, {"message": body}
            last = f"HTTP {e.code} {body[:120]}"
        except Exception as e:
            last = str(e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"{method} {url}: {last}")

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()

def collect():
    files = {}
    for prefix, local_dir, pat in MAPS:
        ld = Path(local_dir)
        if not ld.exists():
            continue
        for f in sorted(ld.iterdir()):
            if not f.is_file() or f.name in EXCLUDE:
                continue
            if f.suffix.lower() not in INCLUDE_EXT:
                continue
            files[prefix + f.name] = f
    return files

def branch_head():
    s, r = req("GET", f"{API}/repos/{REPO}/git/ref/heads/{BR}")
    return r["object"]["sha"] if s == 200 else None

def tree_of(sha):
    s, t = req("GET", f"{API}/repos/{REPO}/git/trees/{sha}?recursive=1")
    return {e["path"]: e["sha"] for e in t.get("tree", []) if e["type"] == "blob"}

def to_local(remote_path):
    for prefix, local_dir, _ in MAPS:
        if remote_path.startswith(prefix):
            return Path(local_dir) / remote_path[len(prefix):]
    return None

def push():
    files = collect()
    print(f"local candidates: {len(files)}")
    head = branch_head()
    existing = tree_of(head) if head else {}
    todo = {p: f for p, f in files.items()
            if p not in existing or existing[p] != blob_sha(f.read_bytes())}
    print(f"to upload: {len(todo)}  (unchanged: {len(files) - len(todo)})")
    entries = []
    def up(item):
        path, f = item
        s, b = req("POST", f"{API}/repos/{REPO}/git/blobs",
                   {"content": base64.b64encode(f.read_bytes()).decode(), "encoding": "base64"})
        if s not in (200, 201):
            raise RuntimeError(f"blob {path}: {b}")
        return path, b["sha"]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fu in as_completed([ex.submit(up, it) for it in todo.items()]):
            path, sha = fu.result()
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
            if len(entries) % 40 == 0:
                print(f"  blobs {len(entries)}/{len(todo)}")
    if entries:
        s, t = req("POST", f"{API}/repos/{REPO}/git/trees", {"tree": entries})
        if s not in (200, 201):
            raise RuntimeError(f"tree: {t}")
        tree_sha = t["sha"]
        s, c = req("POST", f"{API}/repos/{REPO}/git/commits",
                   {"message": "backup: tts/art/scripts snapshot", "tree": tree_sha,
                    "parents": [head] if head else []})
        if s not in (200, 201):
            raise RuntimeError(f"commit: {c}")
        csha = c["sha"]
        if head:
            s, _ = req("PATCH", f"{API}/repos/{REPO}/git/refs/heads/{BR}", {"sha": csha, "force": True})
        else:
            s, _ = req("POST", f"{API}/repos/{REPO}/git/refs",
                       {"ref": f"refs/heads/{BR}", "sha": csha})
        if s not in (200, 201):
            raise RuntimeError("ref update failed")
        print(f"PUSH_OK commit={csha} uploaded={len(entries)}")
    else:
        print("PUSH_OK nothing-new")

def pull():
    head = branch_head()
    if not head:
        print("PULL_NOBACKUP branch missing")
        return
    remote = tree_of(head)
    backup_paths = {p: sha for p, sha in remote.items() if p.startswith("backup/")}
    print(f"backup branch files: {len(backup_paths)}")
    need = {}
    for p, sha in backup_paths.items():
        local = to_local(p)
        if local is None:
            continue
        if not local.exists() or blob_sha(local.read_bytes()) != sha:
            need[p] = (sha, local)
    print(f"to restore: {len(need)}")
    def dl(item):
        p, (sha, local) = item
        s, b = req("GET", f"{API}/repos/{REPO}/git/blobs/{sha}")
        data = base64.b64decode(b["content"])
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        return p
    ok = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for fu in as_completed([ex.submit(dl, it) for it in need.items()]):
            fu.result(); ok += 1
    print(f"PULL_OK restored={ok}/{len(need)}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "push"
    push() if mode == "push" else pull()
