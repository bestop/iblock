#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
很好学 henhaoxue.com —— SEO 内容页静态生成器
================================================
输入 : data/directory.json(抓取自 https://henhaoxue.com/learning/content/directory.json)
输出 : site/library/ 下静态内容页
       - library/scenes/scene-NN/   10 个短语专题页
       - library/phrases/<slug>/    200 条短语详情页(去重后)
       - library/readings/<id>/     60 篇阅读详情页
       - library/readings/          阅读总览页(按 10 类分组)
       另生成 site/sitemap.xml(含全部页面)

用法:
    python3 hhx_gen.py --data data/directory.json --out site \
        --base-url https://henhaoxue.com \
        [--reading-img-base "/learning/reading-scenes/"]

说明:
    - 阅读页图片目录线上未能确认,默认留空(页面用品牌图标),
      确认可用后传 --reading-img-base "/learning/reading-scenes/" 重跑即可。
    - 完全重复的短语(英文+中文+场景提示均相同)只生成一页,避免内容自相竞争。
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import quote

# ---------------------------------------------------------------- 常量
SITE_NAME = "很好学"
SITE_TAGLINE = "方块世界英语学习"
BRAND_URL = "/"                      # 站点首页
LEARN_URL = "/learning/"             # 学习主页(线上 noindex,仅做人流入口)
FAVICON = "/learning/diamond.webp"   # 已验证 200
OG_FALLBACK = "/app-icons/diamond-180-v2.png"  # 已验证 200,建议后续换 1200x630 分享图
PHRASE_IMG_BASE = "/learning/phrase-images/"   # 已验证 200
TODAY = date.today().isoformat()

CSS_HREF = "/library/assets/library.css"

def esc(s):
    return html.escape(str(s), quote=True)

def slugify(text):
    s = str(text).lower()
    s = re.sub(r"[\u2019'\"!.,?!:;()\[\]\u2026]+", "", s)  # 去撇号/标点
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "phrase"

def abs_url(base, path):
    return base.rstrip("/") + "/" + path.lstrip("/")

# ---------------------------------------------------------------- 头部与公共块
def head_block(cfg, title, desc, page_path, og_image, og_type, ld_list):
    """page_path 以 / 开头,以 / 结尾(canonical 与 og:url 用)。"""
    canonical = abs_url(cfg.base_url, page_path)
    og_img = abs_url(cfg.base_url, og_image)
    ld = {"@context": "https://schema.org", "@graph": ld_list}
    return f"""  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="theme-color" content="#ffffff">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="icon" href="{esc(FAVICON)}">
  <link rel="stylesheet" href="{esc(CSS_HREF)}">
  <meta property="og:site_name" content="{esc(SITE_NAME)}">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:type" content="{esc(og_type)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(og_img)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{esc(og_img)}">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>"""

def breadcrumb_ld(items):
    """items: [(name, path_or_None 终点)]"""
    out = []
    for i, (name, path) in enumerate(items, 1):
        li = {"@type": "ListItem", "position": i, "name": name}
        if path:
            li["item"] = abs_url(G_BASE, path)
        out.append(li)
    return {"@type": "BreadcrumbList", "itemListElement": out}

def breadcrumb_nav(items):
    parts = []
    for i, (name, path) in enumerate(items):
        if path:
            parts.append(f'<a href="{esc(path)}">{esc(name)}</a>')
        else:
            parts.append(f'<span aria-current="page">{esc(name)}</span>')
    return '<nav class="crumbs" aria-label="面包屑">' + '<span class="sep">›</span>'.join(parts) + "</nav>"

def shell(cfg, head, body_main):
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
{head}
</head>
<body>
<a class="skip" href="#main">跳到主要内容</a>
<header class="site-head">
  <a class="brand" href="{esc(BRAND_URL)}"><span class="gem" aria-hidden="true"></span>{esc(SITE_NAME)}</a>
  <span class="brand-sub">{esc(SITE_TAGLINE)}</span>
</header>
<main id="main">
{body_main}
</main>
<footer class="site-foot">
  <p class="foot-brand"><span class="gem" aria-hidden="true"></span>{esc(SITE_NAME)} · {esc(SITE_TAGLINE)}</p>
  <nav aria-label="站内导航">
    <a href="{esc(BRAND_URL)}">网站首页</a>
    <a href="{esc(LEARN_URL)}">免费体验学习</a>
    <a href="/library/readings/">阅读图鉴</a>
    <a href="/library/words/">单词图鉴</a>
    <a href="/library/scenes/">短语专题</a>
  </nav>
  <p class="foot-note">把游戏里的每一句话,变成开口就说的英语。</p>
</footer>
</body>
</html>
"""

# ---------------------------------------------------------------- 数据装配
def load_data(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    scenes, phrases, readings, images = d["scenes"], d["phrases"], d["readings"], d["images"]
    # scenes: [名称, 短语数, 图标, 描述]
    scenes = [{"idx": i, "name": s[0], "count": int(s[1]), "icon": s[2], "desc": s[3]}
              for i, s in enumerate(scenes)]
    # phrases: [p1, imgnum, en, zh, hint, sceneIdx(1起)]
    # 预览数据里存在大量空占位记录(整条为空字符串),必须过滤,避免生成空页
    phrases = [{"p1": p[0], "imgnum": p[1], "en": p[2], "zh": p[3], "hint": p[4],
                "scene": int(p[5]) - 1} for p in phrases if str(p[2] or "").strip()]
    return scenes, phrases, readings, images

def load_words(path):
    """首页内联的图鉴单词数据:[{id, word, meaning, category}]"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data

def phrase_image(images, imgnum):
    info = images.get(str(imgnum))
    if not info:
        return None
    base = info["src"].split("/")[-1]
    return {"src": PHRASE_IMG_BASE + quote(base), "width": info["width"], "height": info["height"]}

# ---------------------------------------------------------------- 页面生成
def page_scene(cfg, sc, phrases_of_scene, scenes_nav):
    path = f"/library/scenes/scene-{sc['idx']+1:02d}/"
    real = len(phrases_of_scene)
    title = f"{sc['name']} · 游戏英语短语 {real} 句 | {SITE_NAME}"
    desc = (f"{sc['desc']}。收录 {real} 条方块世界联机沟通英语短语,"
            f"每句带中文释义和使用场景,适合边玩边学。")
    items = [{"@type": "CollectionPage", "name": sc["name"], "url": abs_url(G_BASE, path),
              "description": desc, "inLanguage": "zh-CN"},
             {"@type": "ItemList", "name": f"{sc['name']}短语列表",
              "numberOfItems": real,
              "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                   "name": p["en"], "url": abs_url(G_BASE, p["path"])}
                                  for i, p in enumerate(phrases_of_scene)]},
             breadcrumb_ld([(SITE_NAME, "/"), ("短语专题", "/library/scenes/"), (sc["name"], None)])]
    head = head_block(cfg, title, desc, path, OG_FALLBACK, "website", items)

    cards = []
    for p in phrases_of_scene:
        img = p["img"]
        img_html = ""
        if img:
            img_html = (f'<img src="{esc(abs_url(G_BASE, img["src"]))}" alt="{esc(p["zh"])},方块世界场景插画" '
                        f'width="{img["width"]}" height="{img["height"]}" loading="lazy">')
        cards.append(f"""    <li class="phrase-item">
      <a class="phrase-link" href="{esc(p["path"])}">
        <span class="phrase-en">{esc(p["en"])}</span>
        <span class="phrase-zh">{esc(p["zh"])}</span>
        <span class="phrase-hint">{esc(p["hint"])}</span>
      </a>
    </li>""")
    others = "".join(
        f'<a class="chip" href="/library/scenes/scene-{o["idx"]+1:02d}/">{esc(o["name"])}</a>'
        for o in scenes_nav if o["idx"] != sc["idx"])
    body = f"""  {breadcrumb_nav([(SITE_NAME, "/"), ("短语专题", "/library/scenes/"), (sc["name"], None)])}
  <article class="card">
    <p class="badges"><span class="badge">{real} 句</span><span class="badge badge-soft">联机沟通</span></p>
    <h1>{esc(sc["name"])}</h1>
    <p class="lead">{esc(sc["desc"])}。下面 {real} 句都是和队友一起玩方块世界时最常用的英语,点开任意一句可以看到中文释义、使用场景和场景插画。</p>
    <ol class="phrase-list">
{chr(10).join(cards)}
    </ol>
  </article>
  <section class="related">
    <h2>换个专题继续学</h2>
    <div class="chips">{others}</div>
  </section>"""
    return path, shell(cfg, head, body)

def page_phrase(cfg, p, sc, siblings):
    title = f"{p['en']} {p['zh']} | {SITE_NAME}{SITE_TAGLINE}"
    desc = f"“{p['en']}”的中文意思是“{p['zh']}”。{p['hint']}在方块世界里和队友这样说英语,沟通更快一步。"
    path = p["path"]
    og = p["img"]["src"] if p["img"] else OG_FALLBACK
    ld = [{"@type": "DefinedTerm", "name": p["en"], "alternateName": p["zh"],
           "description": p["hint"], "url": abs_url(G_BASE, path), "inDefinedTermSet": {
               "@type": "DefinedTermSet", "name": f"{sc['name']}·方块世界英语短语",
               "url": abs_url(G_BASE, f"/library/scenes/scene-{sc['idx']+1:02d}/")}},
          breadcrumb_ld([(SITE_NAME, "/"), ("短语专题", "/library/scenes/"),
                         (sc["name"], f"/library/scenes/scene-{sc['idx']+1:02d}/"), (p["en"], None)])]
    head = head_block(cfg, title, desc, path, og, "article", ld)

    img_html = ""
    if p["img"]:
        img_html = (f'<img class="phrase-img" src="{esc(abs_url(G_BASE, p["img"]["src"]))}" '
                    f'alt="{esc(p["zh"])},方块世界场景插画" '
                    f'width="{p["img"]["width"]}" height="{p["img"]["height"]}" loading="lazy">')
    sib = "".join(
        f'<li><a href="{esc(s["path"])}"><span class="phrase-en">{esc(s["en"])}</span>'
        f'<span class="phrase-zh">{esc(s["zh"])}</span></a></li>'
        for s in siblings[:11])
    back = f"/library/scenes/scene-{sc['idx']+1:02d}/"
    n_all = len(siblings) + 1
    body = f"""  {breadcrumb_nav([(SITE_NAME, "/"), ("短语专题", "/library/scenes/"),
                       (sc["name"], back), (p["en"], None)])}
  <article class="card phrase-card">
    <p class="badges"><a class="badge" href="{esc(back)}">{esc(sc["name"])}</a><span class="badge badge-soft">{esc(sc["desc"])}</span></p>
    <h1 class="phrase-en">{esc(p["en"])}</h1>
    <p class="phrase-zh-big">{esc(p["zh"])}</p>
{img_html}
    <section>
      <h2>什么时候用</h2>
      <p>{esc(p["hint"])}</p>
    </section>
    <section>
      <h2>这样开口练</h2>
      <p>下次联机遇到类似情境,先在心里默念一遍 <strong>{esc(p["en"])}</strong>,再打字或开麦对队友说出来;说过三次,这句就归你了。</p>
    </section>
  </article>
  <section class="related">
    <h2>{esc(sc["name"])}的其他短语</h2>
    <ul class="mini-list">{sib}</ul>
    <p><a class="more" href="{esc(back)}">查看全部 {n_all} 句 →</a></p>
  </section>"""
    return path, shell(cfg, head, body)

def page_reading(cfg, r, cat_mates, categories):
    path = f"/library/readings/{quote(r['id'])}/"
    sentence = (r.get("sentence") or "").strip()
    desc = (f"{r['meaning']}。{r.get('description') or ''}"
            + (f"核心句:{sentence}" if sentence else "")
            + f"(难度:{r['level']},约 {r.get('wordCount') or '—'} 词)")
    title = f"{r['word']} {r['meaning']} | {SITE_NAME}{SITE_TAGLINE}"
    og = OG_FALLBACK
    img_html = ""
    if G_READING_IMG_BASE:
        for key in ("imageThumb", "imageSrc"):
            f = (r.get(key) or "").split("/")[-1]
            if f:
                og = G_READING_IMG_BASE + quote(f)
                if key == "imageThumb":
                    img_html = (f'<img class="reading-img" src="{esc(abs_url(G_BASE, og))}" alt="{esc(r.get("imageAlt") or r["meaning"])}" '
                                f'width="400" height="320" loading="lazy">')
                break
    ld = [{"@type": "Article", "headline": r["word"], "alternativeHeadline": r["meaning"],
           "description": r.get("description") or r["meaning"], "image": abs_url(G_BASE, og),
           "articleSection": r["category"], "inLanguage": "zh-CN",
           "wordCount": r.get("wordCount"),
           "isPartOf": {"@type": "CollectionPage", "name": f"{r['category']}·方块世界英语阅读"}},
          breadcrumb_ld([(SITE_NAME, "/"), ("阅读图鉴", "/library/readings/"),
                         (r["category"], None), (r["word"], None)])]
    head = head_block(cfg, title, desc, path, og, "article", ld)

    sentence_html = ""
    if sentence:
        sentence_html = f"""    <blockquote class="sentence">
      <p class="sentence-en">{esc(sentence)}</p>
      <p class="sentence-note">游戏里会用到的一句,读两遍再抄一次。</p>
    </blockquote>"""
    mates = "".join(
        f'<li><a href="{esc(m["path"])}"><span class="phrase-en">{esc(m["word"])}</span>'
        f'<span class="phrase-zh">{esc(m["meaning"])}</span></a></li>'
        for m in cat_mates[:5])
    body = f"""  {breadcrumb_nav([(SITE_NAME, "/"), ("阅读图鉴", "/library/readings/"),
                       (r["category"], None), (r["word"], None)])}
  <article class="card reading-card">
    <p class="badges"><span class="badge">{esc(r["category"])}</span>
       <span class="badge badge-soft">难度 · {esc(r["level"])}</span>
       <span class="badge badge-soft">约 {esc(r.get("wordCount") or "—")} 词</span></p>
    <h1>{esc(r["word"])}</h1>
    <p class="lead">{esc(r["meaning"])}</p>
{img_html}
    <section>
      <h2>这篇讲什么</h2>
      <p>{esc(r.get("description") or r["meaning"])}</p>
      <p class="word-tip">核心词:<strong>{esc(r.get("imageWord") or "")}</strong> —— 在画面里找到它,再把单词念出来。</p>
    </section>
{sentence_html}
  </article>
  <section class="related">
    <h2>「{esc(r["category"])}」的其他阅读</h2>
    <ul class="mini-list">{mates}</ul>
    <p><a class="more" href="/library/readings/">查看全部 60 篇阅读 →</a></p>
  </section>"""
    return path, shell(cfg, head, body)

def page_readings_hub(cfg, readings, categories):
    path = "/library/readings/"
    title = f"方块世界英语阅读 60 篇(图解分级) | {SITE_NAME}"
    desc = ("60 篇方块世界主题英语小阅读,按「" + "、".join(categories[:5]) + "」等 10 个主题分类,"
            "入门/进阶/挑战三个难度分级,每篇配方块场景插画和核心例句。")
    ld = [{"@type": "CollectionPage", "name": "方块世界英语阅读图鉴", "url": abs_url(G_BASE, path),
           "description": desc, "inLanguage": "zh-CN"},
          {"@type": "ItemList", "numberOfItems": len(readings),
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": r["word"],
                                "url": abs_url(G_BASE, r["path"])} for i, r in enumerate(readings)]},
          breadcrumb_ld([(SITE_NAME, "/"), ("阅读图鉴", None)])]
    head = head_block(cfg, title, desc, path, OG_FALLBACK, "website", ld)

    groups = []
    for cat in categories:
        rs = [r for r in readings if r["category"] == cat]
        lis = "".join(
            f'<li><a href="{esc(r["path"])}"><span class="phrase-en">{esc(r["word"])}</span>'
            f'<span class="phrase-zh">{esc(r["meaning"])}</span>'
            f'<span class="badge badge-soft">{esc(r["level"])}</span></a></li>'
            for r in rs)
        groups.append(f"""    <section class="hub-group">
      <h2>{esc(cat)}</h2>
      <ul class="mini-list">{lis}</ul>
    </section>""")
    body = f"""  {breadcrumb_nav([(SITE_NAME, "/"), ("阅读图鉴", None)])}
  <article class="card">
    <h1>方块世界英语阅读 · 60 篇</h1>
    <p class="lead">每一篇对应方块世界里一个真实的小物件或小场景:箱子、熔岩、羊、床……先看图认词,再读一句英文,最后玩的时候遇到它就会想起来。全部内容按难度分为入门 / 进阶 / 挑战三档。</p>
    <p class="badges"><span class="badge">10 大主题</span><span class="badge badge-soft">60 篇</span><span class="badge badge-soft">三档难度</span></p>
  </article>
{chr(10).join(groups)}
  <section class="related">
    <h2>也想去和队友练对话?</h2>
    <p><a class="more" href="/library/scenes/scene-01/">去看 10 个短语专题 →</a></p>
  </section>"""
    return path, shell(cfg, head, body)

# ---------------------------------------------------------------- 单词页
def page_word(cfg, w, cat_mates, categories):
    path = w["path"]
    title = f"{w['word']} {w['meaning']} | {SITE_NAME}{SITE_TAGLINE}"
    desc = (f"{w['meaning']}的英语是 {w['word']}。「{w['category']}」主题图解单词,"
            f"看图认词、开口跟读,在方块世界里边玩边记。")
    ld = [{"@type": "DefinedTerm", "name": w["word"], "alternateName": w["meaning"],
           "description": f"方块世界主题英语单词,{w['meaning']}",
           "url": abs_url(G_BASE, path), "inDefinedTermSet": {
               "@type": "DefinedTermSet", "name": f"{w['category']}·方块世界英语单词图鉴",
               "url": abs_url(G_BASE, "/library/words/")}},
          breadcrumb_ld([(SITE_NAME, "/"), ("单词图鉴", "/library/words/"),
                         (w["category"], None), (w["word"], None)])]
    head = head_block(cfg, title, desc, path, OG_FALLBACK, "article", ld)
    mates = "".join(
        f'<li><a href="{esc(m["path"])}"><span class="phrase-en">{esc(m["word"])}</span>'
        f'<span class="phrase-zh">{esc(m["meaning"])}</span></a></li>'
        for m in cat_mates[:7])
    body = f"""  {breadcrumb_nav([(SITE_NAME, "/"), ("单词图鉴", "/library/words/"),
                       (w["category"], None), (w["word"], None)])}
  <article class="card phrase-card">
    <p class="badges"><a class="badge" href="/library/words/">{esc(w["category"])}</a><span class="badge badge-soft">图解单词</span></p>
    <h1 class="phrase-en">{esc(w["word"])}</h1>
    <p class="phrase-zh-big">{esc(w["meaning"])}</p>
    <section>
      <h2>怎么记住它</h2>
      <p>在方块世界里,{esc(w["meaning"])}就是 <strong>{esc(w["word"])}</strong>。先用眼睛认:游戏画面里看到它,就小声念一遍它的英文名;再动手记:连写三遍,或截一张它出现的游戏图,标上单词。</p>
    </section>
    <section>
      <h2>开口练一练</h2>
      <p>和队友联机时,试着用这个词造一句：<em>This is my favorite {esc(w["word"].lower())}.</em>(这是我最喜欢的{esc(w["meaning"])}。)说出来,这个词就是你的了。</p>
    </section>
  </article>
  <section class="related">
    <h2>「{esc(w["category"])}」的其他单词</h2>
    <ul class="mini-list">{mates}</ul>
    <p><a class="more" href="/library/words/">查看全部 80 个图解单词 →</a></p>
  </section>"""
    return path, shell(cfg, head, body)

def words_hub(cfg, words, categories):
    path = "/library/words/"
    title = f"方块世界英语单词图鉴 · 80 个图解单词 | {SITE_NAME}"
    desc = ("80 个方块世界主题英语单词,按基础方块、动物伙伴、工具装备、食物耕作等 10 个主题分类,"
            "每个词配中文释义,看图认词,边玩边记。")
    ld = [{"@type": "CollectionPage", "name": "方块世界英语单词图鉴", "url": abs_url(G_BASE, path),
           "description": desc, "inLanguage": "zh-CN"},
          {"@type": "ItemList", "numberOfItems": len(words),
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": w["word"],
                                "url": abs_url(G_BASE, w["path"])} for i, w in enumerate(words)]},
          breadcrumb_ld([(SITE_NAME, "/"), ("单词图鉴", None)])]
    head = head_block(cfg, title, desc, path, OG_FALLBACK, "website", ld)
    groups = []
    for cat in categories:
        ws = [w for w in words if w["category"] == cat]
        lis = "".join(
            f'<li><a href="{esc(w["path"])}"><span class="phrase-en">{esc(w["word"])}</span>'
            f'<span class="phrase-zh">{esc(w["meaning"])}</span></a></li>'
            for w in ws)
        groups.append(f"""    <section class="hub-group">
      <h2>{esc(cat)}</h2>
      <ul class="mini-list">{lis}</ul>
    </section>""")
    body = f"""  {breadcrumb_nav([(SITE_NAME, "/"), ("单词图鉴", None)])}
  <article class="card">
    <h1>方块世界英语单词图鉴</h1>
    <p class="lead">把游戏里最常见的 80 个东西变成 80 个英语单词:玩家、方块、箱子、羊、熔岩……按主题分类,每个词都有中文释义。孩子在游戏里看到实物,大人报出单词,认过三轮就再也忘不掉。</p>
    <p class="badges"><span class="badge">10 大主题</span><span class="badge badge-soft">80 词</span></p>
  </article>
{chr(10).join(groups)}
  <section class="related">
    <h2>单词认识了,来读点小故事?</h2>
    <p><a class="more" href="/library/readings/">去看 60 篇图解阅读 →</a> <a class="more" href="/library/scenes/">或 10 个短语专题 →</a></p>
  </section>"""
    return path, shell(cfg, head, body)

def scenes_index(cfg, scenes_with, total_planned=200):
    path = "/library/scenes/"
    total = sum(s["n"] for s in scenes_with)
    title = f"联机英语短语 · 方块世界沟通句库 | {SITE_NAME}"
    desc = ("按情境整理的方块世界联机英语短语:见面打招呼、邀请队友、报方向、分物资、"
            f"建基地、防怪物、解决联机小问题,已整理 {total} 句,全部带中文释义和使用场景。")
    ld = [{"@type": "CollectionPage", "name": "方块世界英语短语专题", "url": abs_url(G_BASE, path),
           "description": desc, "inLanguage": "zh-CN"},
          {"@type": "ItemList", "numberOfItems": len(scenes_with),
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": s["name"],
                                "url": abs_url(G_BASE, f"/library/scenes/scene-{s['idx']+1:02d}/")}
                               for i, s in enumerate(scenes_with)]},
          breadcrumb_ld([(SITE_NAME, "/"), ("短语专题", None)])]
    head = head_block(cfg, title, desc, path, OG_FALLBACK, "website", ld)
    lis = "".join(
        f'<li><a href="/library/scenes/scene-{s["idx"]+1:02d}/"><span class="phrase-en">{esc(s["name"])}</span>'
        f'<span class="phrase-zh">{esc(s["desc"])}</span><span class="badge badge-soft">{s["n"]} 句</span></a></li>'
        for s in scenes_with)
    body = f"""  {breadcrumb_nav([(SITE_NAME, "/"), ("短语专题", None)])}
  <article class="card">
    <h1>联机英语短语 · 沟通句库</h1>
    <p class="lead">和朋友一起玩方块世界时,沟通不外乎这几类事:打招呼、集合、找路、分装备、盖房子、防怪。每个专题点进去,都是一整套当下就能用的句子。</p>
    <p class="badges"><span class="badge">{len(scenes_with)} 个专题</span><span class="badge badge-soft">{total} 句</span></p>
  </article>
  <section class="related"><h2>选择一个专题</h2><ul class="mini-list big">{lis}</ul></section>"""
    return path, shell(cfg, head, body)

# ---------------------------------------------------------------- sitemap
def write_sitemap(cfg, out, pages):
    urls = [("/", "1.0")] + [(p, "0.7") for p in pages]
    rows = []
    for loc, pri in urls:
        rows.append(f"  <url><loc>{esc(abs_url(cfg.base_url, loc))}</loc>"
                    f"<lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq>"
                    f"<priority>{pri}</priority></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    (out / "sitemap.xml").write_text(xml, encoding="utf-8")

# ---------------------------------------------------------------- 主流程
G_BASE = "https://henhaoxue.com"
G_READING_IMG_BASE = ""

def main():
    global G_BASE, G_READING_IMG_BASE
    ap = argparse.ArgumentParser(description="很好学 SEO 内容页生成器")
    ap.add_argument("--data", default="data/directory.json")
    ap.add_argument("--words", default="data/home-words.json",
                    help="首页内联图鉴单词 JSON;传空字符串则跳过单词页")
    ap.add_argument("--out", default="site")
    ap.add_argument("--base-url", default="https://henhaoxue.com")
    ap.add_argument("--reading-img-base", default="",
                    help='阅读页图片前缀,如 "/learning/reading-scenes/";留空则用品牌图标')
    cfg = ap.parse_args()
    G_BASE = cfg.base_url
    G_READING_IMG_BASE = (cfg.reading_img_base or "").rstrip("/") + "/"

    out = Path(cfg.out)
    for sub in ("library/scenes", "library/phrases", "library/readings", "library/words", "library/assets"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    scenes, phrases, readings, images = load_data(cfg.data)

    # ---- 短语去重 + slug 分配
    seen, uniq, dropped = {}, [], 0
    slug_used = Counter()
    for p in phrases:
        key = (p["en"].strip(), p["zh"].strip(), p["hint"].strip())
        if key in seen:
            dropped += 1
            continue
        seen[key] = True
        slug = slugify(p["en"])
        slug_used[slug] += 1
        s = slug if slug_used[slug] == 1 else f"{slug}-{slug_used[slug]}"
        p["path"] = f"/library/phrases/{s}/"
        p["img"] = phrase_image(images, p["imgnum"])
        uniq.append(p)

    # ---- 专题页(只生成有短语数据的场景)+ 短语页
    pages, n_scene, n_phrase = [], 0, 0
    scenes_with = []
    for sc in scenes:
        sc_phrases = [p for p in uniq if p["scene"] == sc["idx"]]
        if not sc_phrases:
            continue
        scenes_with.append({"idx": sc["idx"], "name": sc["name"], "desc": sc["desc"],
                            "count": sc["count"], "n": len(sc_phrases)})
        path, html_text = page_scene(cfg, sc, sc_phrases, scenes_with[:-1] + scenes_with[1:])
        (out / path.strip("/") / "index.html").parent.mkdir(parents=True, exist_ok=True)
        (out / path.strip("/") / "index.html").write_text(html_text, encoding="utf-8")
        pages.append(path)
        n_scene += 1
    for p in uniq:
        sc = scenes[p["scene"]]
        sib = [q for q in uniq if q["scene"] == p["scene"] and q is not p]
        path, html_text = page_phrase(cfg, p, sc, sib)
        fp = out / path.strip("/") / "index.html"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(html_text, encoding="utf-8")
        pages.append(path)
        n_phrase += 1

    # ---- 阅读页 + 总览 + 专题索引
    categories = sorted({r["category"] for r in readings})
    for r in readings:
        r["path"] = f"/library/readings/{quote(r['id'])}/"
    n_read = 0
    for r in readings:
        mates = [m for m in readings if m["category"] == r["category"] and m is not r]
        path, html_text = page_reading(cfg, r, mates, categories)
        fp = out / path.strip("/") / "index.html"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(html_text, encoding="utf-8")
        pages.append(path)
        n_read += 1

    path, hub_html = page_readings_hub(cfg, readings, categories)
    (out / path.strip("/") / "index.html").write_text(hub_html, encoding="utf-8")
    pages.append(path)
    path, idx_html = scenes_index(cfg, scenes_with)
    (out / path.strip("/") / "index.html").write_text(idx_html, encoding="utf-8")
    pages.append(path)

    # ---- 图鉴单词页(数据来自首页内联)
    n_word = 0
    if getattr(cfg, "words", None):
        words = load_words(cfg.words)
        wcats = sorted({w["category"] for w in words})
        wslug = Counter()
        for w in words:
            s = slugify(w["word"])
            wslug[s] += 1
            w["path"] = f"/library/words/{s if wslug[s] == 1 else str(s) + '-' + str(wslug[s])}/"
        for w in words:
            mates = [m for m in words if m["category"] == w["category"] and m is not w]
            path, html_text = page_word(cfg, w, mates, wcats)
            fp = out / path.strip("/") / "index.html"
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(html_text, encoding="utf-8")
            pages.append(path)
            n_word += 1
        path, whub_html = words_hub(cfg, words, wcats)
        (out / path.strip("/") / "index.html").write_text(whub_html, encoding="utf-8")
        pages.append(path)

    write_sitemap(cfg, out, pages)
    print(f"完成:专题 {n_scene} 页,短语 {n_phrase} 页(过滤空占位 {len(phrases)}→{n_phrase}),"
          f"阅读 {n_read} 页,单词 {n_word} 页,总览/索引 3 页,"
          f"sitemap 共 {len(pages) + 1} URL")
    return 0

if __name__ == "__main__":
    sys.exit(main())
