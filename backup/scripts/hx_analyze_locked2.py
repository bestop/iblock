#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深入分析：锁定词的 reader 数据完整度 + 本地资源在位情况"""
import json, os, collections

ROOT = '/home/z/my-project/henhaoxue-site/learning'
idx = json.load(open(f'{ROOT}/content/word-index.json'))
reader = json.load(open(f'{ROOT}/content/word-reader.json'))

words = idx['words']
basic_locked = [w for w in words if w['category'] == '基础方块世界' and w.get('locked')]
basic_open  = [w for w in words if w['category'] == '基础方块世界' and not w.get('locked')]
print('基础方块世界: locked=%d open=%d' % (len(basic_locked), len(basic_open)))
print('index 词字段:', list(words[0].keys()))
print('锁定词样例:', json.dumps(basic_locked[0], ensure_ascii=False))
print('解锁词样例:', json.dumps(basic_open[0], ensure_ascii=False))

# reader.cards 结构
cards = reader['cards']
print('\nreader.index 类型:', type(reader['index']).__name__, '长度:', len(reader['index']))
print('reader.category:', json.dumps(reader['category'], ensure_ascii=False)[:300])
c0 = cards[0]
print('card 字段:', list(c0.keys()))
print('\ncard 样例(第一个):', json.dumps(c0, ensure_ascii=False)[:800])

# cards 按 id 索引
by_id = {}
for c in cards:
    by_id[c.get('id')] = c
print('\ncards 总数:', len(cards), '唯一 id:', len(by_id))

# 检查锁定词在 reader 里的覆盖
have, miss = 0, []
for w in basic_locked:
    wid = w['id']
    if wid in by_id:
        have += 1
    else:
        miss.append(wid)
print('锁定词在 reader.cards 中: 有=%d 缺=%d' % (have, len(miss)))
if miss: print('缺失样例:', miss[:10])
