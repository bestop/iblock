#!/usr/bin/env python3
"""解锁「方块与建造」全部补丁：
1. trial-directory.js 白名单该分类
2. app.js import 加版本参数
3. learning/index.html app.js 版本刷新
4. reader bundle：_p 按分类/ID 路由到 word-reader-build.json + 门控白名单 + 重命名
5. word-index.json locked:false x267
6. access.json policy.words += 267 ids
"""
import json, shutil, os, sys

SITE = '/home/z/my-project/henhaoxue-site'
CAT = '方块与建造'
V = '20261104-unlock-blocks'

def patch(path, old, new, must=1):
    s = open(path, encoding='utf-8').read()
    n = s.count(old)
    assert n == must, f'{path}: pattern x{n} (expect {must}): {old[:80]}'
    open(path, 'w', encoding='utf-8').write(s.replace(old, new))
    print(f'patched {os.path.relpath(path, SITE)}')

# 1. trial-directory.js
patch(f'{SITE}/learning/trial-directory.js',
      "kind==='words'&&category===access.policy.wordCategory",
      f"kind==='words'&&(category===access.policy.wordCategory||category==='{CAT}')")

# 2. app.js import version bump
patch(f'{SITE}/learning/app.js',
      "import './trial-directory.js'",
      f"import './trial-directory.js?v={V}'")

# 3. learning/index.html app.js version bump
patch(f'{SITE}/learning/index.html',
      '?v=20261025-nav-search&rollback=20261025-original&return-cache=20261025-v2',
      f'?v={V}&rollback=20261025-original&return-cache=20261025-v2')

# 4. reader bundle
B = f'{SITE}/learning/reader/assets/index-BjbErrgc.js'
OLD_NAME = 'index-BjbErrgc.js'
NEW_NAME = 'index-BjbErrgc-b1.js'

# 4a. _p 路由
patch(B,
      'return Ve(gp+`content/word-reader.json?`+t)}',
      'return Ve(gp+`content/`+((e.get(`category`)===`' + CAT + '`||(e.get(`id`)||``).startsWith(`blocks_and_building-`))?`word-reader-build.json`:`word-reader.json`)+`?`+t)}')

# 4b. 门控白名单
patch(B,
      'Tp.get(`category`)&&r&&Tp.get(`category`)!==t.policy.wordCategory',
      'Tp.get(`category`)&&r&&Tp.get(`category`)!==t.policy.wordCategory&&Tp.get(`category`)!==`' + CAT + '`')

# 4c. 重命名 + 更新 reader/index.html
shutil.copy(B, f'{SITE}/learning/reader/assets/{NEW_NAME}')
patch(f'{SITE}/learning/reader/index.html', OLD_NAME, NEW_NAME)
print(f'bundle copied -> {NEW_NAME} (old kept for stale visitors)')

# 5. word-index.json locked flip
p5 = f'{SITE}/learning/content/word-index.json'
wi = json.load(open(p5))
n = 0
for w in wi['words']:
    if w['category'] == CAT and w['locked']:
        w['locked'] = False
        n += 1
json.dump(wi, open(p5, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'word-index: {n} words unlocked')

# 6. access.json policy.words append
p6 = f'{SITE}/learning/content/access.json'
ac = json.load(open(p6))
plan = json.load(open('/tmp/build_blocks/plan.json'))
ids = [p['id'] for p in plan]
before = len(ac['policy']['words'])
ac['policy']['words'] = sorted(set(ac['policy']['words'] + ids))
json.dump(ac, open(p6, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f"access.json policy.words: {before} -> {len(ac['policy']['words'])}")
print('ALL PATCHES OK')
