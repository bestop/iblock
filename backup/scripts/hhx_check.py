#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成产物自检:TDK/OG/JSON-LD/canonical/内链一致性"""
import json, re, sys
from pathlib import Path
from urllib.parse import urlparse, unquote

SITE = Path("/home/z/my-project/henhaoxue-optimization-kit/03-SEO内容页/site")
pages = sorted(SITE.rglob("index.html"))
print(f"index.html 总数: {len(pages)}")

problems = []
paths_exist = set()
for p in pages:
    rel = "/" + p.parent.relative_to(SITE).as_posix().rstrip("/") + "/"
    # URL 编码的路径(中文/特殊字符目录)按 unquote 还原
    paths_exist.add(unquote(rel))
    html_text = p.read_text(encoding="utf-8")

    checks = {
        "title": "<title>" in html_text and "</title>" in html_text,
        "description": 'name="description"' in html_text,
        "canonical": 'rel="canonical"' in html_text,
        "og:title": 'property="og:title"' in html_text,
        "og:image": 'property="og:image"' in html_text,
        "twitter:card": 'name="twitter:card"' in html_text,
        "ld+json": 'application/ld+json' in html_text,
        "h1": html_text.count("<h1") == 1,
        "viewport": 'name="viewport"' in html_text,
        "lang": '<html lang="zh-CN">' in html_text,
    }
    for k, ok in checks.items():
        if not ok:
            problems.append(f"{rel}: 缺少 {k}")

    # JSON-LD 可解析
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S)
    if m:
        try:
            ld = json.loads(m.group(1))
            if "@graph" not in ld:
                problems.append(f"{rel}: JSON-LD 无 @graph")
        except Exception as e:
            problems.append(f"{rel}: JSON-LD 解析失败 {e}")

    # 残留模板占位
    for bad in ("{esc(", "{p[", "None", "undefined", "NaN", "TODO"):
        if bad in html_text:
            problems.append(f"{rel}: 残留 {bad}")

    # 收集本地内链
    for href in re.findall(r'href="(/[^"]*)"', html_text):
        href = unquote(href.split("#")[0])
        if href in ("/", "/learning/", "/learning/account/") or href.startswith("/learning/") or href.startswith("/app-icons/"):
            continue
        if not href.startswith("/library/"):
            problems.append(f"{rel}: 意外内链 {href}")
        elif not href.endswith("/library/assets/library.css"):
            # 记录路径,稍后验证存在性
            if href not in paths_exist:
                paths_exist.add(("CHECK", href))

# 验证内链目标存在
for item in paths_exist:
    if isinstance(item, tuple) and item[0] == "CHECK":
        target = item[1].rstrip("/") + "/index.html"
        if not (SITE / target.lstrip("/")).exists():
            problems.append(f"死链: {item[1]}")

# sitemap 与实际页面对齐
sm = (SITE / "sitemap.xml").read_text(encoding="utf-8")
sm_urls = re.findall(r"<loc>(.*?)</loc>", sm)
real_urls = {"https://henhaoxue.com/"} | {
    "https://henhaoxue.com" + unquote("/" + p.parent.relative_to(SITE).as_posix().rstrip("/") + "/")
    for p in pages if "library" in str(p)}
sm_set = set(sm_urls)
only_sm = sm_set - real_urls
only_real = real_urls - sm_set
for u in sorted(only_sm):
    problems.append(f"sitemap 多出: {u}")
for u in sorted(only_real):
    problems.append(f"sitemap 缺少: {u}")

# 图片引用全部为线上绝对地址
bad_img = []
for p in pages:
    html_text = p.read_text(encoding="utf-8")
    for src in re.findall(r'<img[^>]*src="([^"]+)"', html_text):
        if not src.startswith("https://henhaoxue.com/"):
            bad_img.append(f"{p.name}: {src}")
print("非线上绝对地址图片:", len(bad_img))
for b in bad_img[:5]:
    problems.append("图片地址: " + b)

print()
if problems:
    print(f"发现 {len(problems)} 个问题(前 30 个):")
    for x in problems[:30]:
        print(" -", x)
    sys.exit(1)
print("全部通过:TDK/OG/Twitter/JSON-LD/canonical/h1 唯一/内链无死链/sitemap 对齐")
