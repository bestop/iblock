#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锁定词 vs 解锁词的 card 字段差异 + 前端锁定逻辑定位"""
import json, collections

ROOT = '/home/z/my-project/henhaoxue-site/learning'
idx = json.load(open(f'{ROOT}/content/word-index.json'))
reader = json.load(open(f'{ROOT}/content/word-reader.json'))
by_id = {c['id']: c for c in reader['cards']}

locked_ids = {w['id'] for w in idx['words'] if w['category'] == '基础方块世界' and w.get('locked')}

# 对比锁定/解锁卡的字段填充情况
for group, ids in [('锁定', locked_ids), ('解锁', {c['id'] for c in reader['cards']} - locked_ids)]:
    n = len(ids)
    st = collections.Counter()
    lvl_src = collections.Counter()
    for i in ids:
        c = by_id[i]
        for f in ['phonetic', 'sentence', 'translation', 'image']:
            if c.get(f): st[f] += 1
        for lv, lvdata in (c.get('levels') or {}).items():
            if (lvdata.get('audio') or {}).get('src'): lvl_src[lv] += 1
            if lvdata.get('sentence'): st[f'lvl_{lv}_sentence'] += 1
    print(f'== {group}组 ({n}卡) ==')
    print('  字段非空:', dict(st))
    print('  levels 音频src非空:', dict(lvl_src))
    print()

# 锁定卡样例
lk = by_id[[i for i in sorted(locked_ids)][0]]
print('锁定卡样例:', json.dumps(lk, ensure_ascii=False)[:900])
