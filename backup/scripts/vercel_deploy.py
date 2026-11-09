#!/usr/bin/env python3
"""Deploy the iblock optimization kit to Vercel as a new project `iblock`.

Flow: verify scope -> collect files (repo files + preview index) -> upload via
POST /v2/files -> create production deployment via POST /v13/deployments
(auto-creates the project) -> poll until READY -> report URLs.
Token is read from env VERCEL_TOKEN (never written to any file).
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "https://api.vercel.com"
TOKEN = os.environ["VERCEL_TOKEN"]
KIT = Path("/home/z/my-project/henhaoxue-optimization-kit")

PREVIEW_INDEX = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>iblock · 很好学 henhaoxue.com 优化部署包</title>
<style>
  :root { --brand:#287f70; --ink:#1a2b28; --sub:#5b6f6a; --line:#e3eae8; --bg:#f6f9f8; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
         line-height:1.6; }
  .wrap { max-width:860px; margin:0 auto; padding:48px 20px 64px; }
  header h1 { margin:0 0 6px; font-size:28px; }
  header .tag { display:inline-block; background:var(--brand); color:#fff; border-radius:999px;
                padding:2px 12px; font-size:13px; margin-bottom:14px; }
  header p { margin:0 0 28px; color:var(--sub); font-size:14px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:14px; }
  section { background:#fff; border:1px solid var(--line); border-radius:12px; padding:18px 20px; }
  section h2 { margin:0 0 10px; font-size:15px; color:var(--brand); }
  section ul { margin:0; padding-left:18px; }
  section li { margin:4px 0; font-size:14px; }
  a { color:#1a6ea0; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .note { margin-top:26px; font-size:13px; color:var(--sub); background:#fff;
          border:1px dashed var(--line); border-radius:12px; padding:14px 18px; }
  code { background:#eef3f2; border-radius:4px; padding:1px 6px; font-size:13px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="tag">Vercel 预览部署</span>
    <h1>iblock · 很好学 henhaoxue.com 优化部署包</h1>
    <p>缓存与压缩 · SEO 基建 · SEO 内容页（176 页静态站）— 发布于 2026-11-02</p>
  </header>
  <div class="grid">
    <section>
      <h2>🎯 SEO 内容页预览</h2>
      <ul>
        <li><a href="03-SEO内容页/site/library/phrases/hello/">短语页示例 · Hello</a></li>
        <li><a href="03-SEO内容页/site/library/readings/first-night/">阅读页示例 · 第一夜</a></li>
        <li><a href="03-SEO内容页/site/library/words/creeper/">单词页示例 · Creeper</a></li>
        <li><a href="03-SEO内容页/site/library/scenes/scene-01/">场景页示例 · Scene 01</a></li>
        <li><a href="03-SEO内容页/site/sitemap.xml">sitemap.xml（177 条 URL）</a></li>
      </ul>
    </section>
    <section>
      <h2>🚀 缓存与压缩</h2>
      <ul>
        <li><a href="01-缓存与压缩/cloudflare-cache-rules.md">Cloudflare 缓存规则指南</a></li>
        <li><a href="01-缓存与压缩/_headers">_headers（Pages/Netlify）</a></li>
        <li><a href="01-缓存与压缩/nginx-cache.conf">nginx 缓存配置</a></li>
        <li><a href="01-缓存与压缩/node-cache.js">Node 缓存中间件</a></li>
      </ul>
    </section>
    <section>
      <h2>🔍 SEO 基建</h2>
      <ul>
        <li><a href="02-SEO基建/head-meta-homepage.html">首页 meta / JSON-LD 片段</a></li>
        <li><a href="02-SEO基建/robots.txt">robots.txt</a></li>
        <li><a href="02-SEO基建/404.html">品牌化 404 页</a></li>
      </ul>
    </section>
    <section>
      <h2>🛠 生成器与数据</h2>
      <ul>
        <li><a href="README.md">README 部署总说明</a></li>
        <li><a href="03-SEO内容页/generator.py">generator.py 生成器</a></li>
        <li><a href="03-SEO内容页/data/directory.json">directory.json 内容数据</a></li>
        <li><a href="03-SEO内容页/data/home-words.json">home-words.json 图鉴单词</a></li>
      </ul>
    </section>
  </div>
  <p class="note">说明：所有 SEO 内容页的 <code>canonical</code> 均指向生产域名 <code>henhaoxue.com</code>，
  本部署仅用于上线前预览验证；正式发布请将 <code>03-SEO内容页/site/</code> 内容复制到源站根目录。
  本页已设置 <code>noindex</code>。</p>
</div>
</body>
</html>
"""


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
            with urllib.request.urlopen(r, timeout=60) as resp:
                body = resp.read().decode()
                return resp.status, json.loads(body) if body.strip().startswith(("{", "[")) else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                err = json.loads(body).get("error", {})
            except Exception:
                err = {"message": body[:200]}
            code = err.get("code", "")
            if code == "file_already_exists":
                return e.code, err  # duplicate upload == already there, fine
            if e.code < 500 and e.code != 429:
                return e.code, err
            last = (e.code, err)
        except Exception as e:
            last = (0, str(e))
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"request failed: {method} {url}: {last}")


# --- 1. scope: resolve team id --------------------------------------------------
status, tdata = req("GET", "/v2/teams")
teams = tdata.get("teams", [])
if not teams:
    raise SystemExit("no team found under this account")
TEAM = teams[0]["id"]
print(f"team: {teams[0].get('slug')} ({TEAM})")
QS = f"?teamId={TEAM}"

# --- 2. file list: git-tracked files (site root), docs/ excluded from serving ----
files_raw = subprocess.check_output(
    ["git", "-c", "core.quotePath=false", "ls-files", "-z"], cwd=KIT
).decode()
paths = [p for p in files_raw.split("\0") if p.strip()]
paths = [p for p in paths if not p.startswith("docs/")]  # guides stay in repo only
assert "index.html" in paths, "site root index.html missing"
contents = {}
for p in paths:
    contents[p] = (KIT / p).read_bytes()
print(f"files to deploy: {len(contents)} (site root; docs/ excluded)")

digests = {p: hashlib.sha1(b).hexdigest() for p, b in contents.items()}

# --- 3. upload files --------------------------------------------------------------
def upload(p):
    status, err = req("POST", f"/v2/files{QS}", raw=contents[p],
                      headers={"x-vercel-digest": digests[p],
                               "Content-Type": "application/octet-stream"})
    if status == 200 or (isinstance(err, dict) and err.get("code") == "file_already_exists"):
        return p
    raise RuntimeError(f"upload failed {p}: {status} {err}")

with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(upload, p) for p in contents]
    for i, fu in enumerate(as_completed(futs), 1):
        fu.result()
        if i % 50 == 0 or i == len(contents):
            print(f"  uploaded: {i}/{len(contents)}")

# --- 4. create production deployment (auto-creates project iblock) ----------------
payload = {
    "name": "iblock",
    "target": "production",
    "files": [{"file": p, "sha": digests[p], "size": len(contents[p])} for p in contents],
    "projectSettings": {
        "framework": None,
        "buildCommand": None,
        "installCommand": None,
        "outputDirectory": None,
        "devCommand": None,
    },
}
status, dep = req("POST", f"/v13/deployments{QS}", payload)
if status != 200:
    raise SystemExit(f"deployment create failed: {status} {dep}")
DEP_ID = dep["id"]
print(f"deployment created: {DEP_ID}  state={dep.get('readyState')}  url={dep.get('url')}")

# --- 5. poll until terminal --------------------------------------------------------
terminal = {"READY", "ERROR", "CANCELED"}
for _ in range(60):
    status, d = req("GET", f"/v13/deployments/{DEP_ID}{QS}")
    state = d.get("readyState")
    if state in terminal:
        break
    time.sleep(3)
print(f"final state: {state}")
if state != "READY":
    print("failureReason:", json.dumps(d.get("failureReason", {}), ensure_ascii=False))
    raise SystemExit(1)

# --- 6. report URLs -----------------------------------------------------------------
print("\n=== deployment aliases ===")
for a in d.get("alias", []):
    print("  ", a)
status, pd = req("GET", f"/v9/projects/iblock{QS}")
print(f"\nproject: {pd.get('name')} ({pd.get('id')})")
status, doms = req("GET", f"/v9/projects/iblock/domains{QS}")
for dom in doms.get("domains", []):
    print("project domain:", dom.get("name"), "| verified:", dom.get("verified"))
print("\nSUCCESS")
