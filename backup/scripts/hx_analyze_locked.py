#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 基础方块世界 分类中锁定单词的现状：index 里有多少、reader 里数据完整度、本地资源是否在位"""
import json, os, collections

ROOT = '/home/z/my-project/henhaoxue-site/learning'
idx = json.load(open(f'{ROOT}/content/word-index.json'))
reader = json.load(open(f'{ROOT}/content/word-reader.json'))

words = idx['words']
print('== word-index.json 顶层 keys:', list(idx.keys()))
print('== 词总数:', len(words))

# 每个分类 locked 统计
by_cat = collections.OrderedDict()
for w in words:
    c = w.get('category', '?')
    by_cat.setdefault(c, {'total': 0, 'locked': 0, 'sample_locked': []})
    by_cat[c]['total'] += 1
    if w.get('locked'):
        by_cat[c]['locked'] += 1
        if len(by_cat[c]['sample_locked']) < 5:
            by_cat[c]['sample_locked'].append(w.get('word'))

print('\n== 各分类 locked 统计 ==')
for c, s in by_cat.items():
    mark = ' ★' if s['locked'] else ''
    print(f"  {c}: total={s['total']} locked={s['locked']}{mark}")

# 锁定分类下的锁定词样本
print('\n== 锁定词样本 ==')
for c, s in by_cat.items():
    if s['locked']:
        print(f"  [{c}] {s['sample_locked']}")

# 找出"基础方块世界"分类 id 对应关系（category 字段是 id 还是中文名?）
print('\n== category 字段样例:', list({w.get('category') for w in words})[:20])

# reader 数据结构
r_keys = list(reader.keys()) if isinstance(reader, dict) else None
print('\n== word-reader.json 顶层类型:', type(reader).__name__)
if isinstance(reader, dict):
    print('   keys 数量:', len(r_keys), '样例:', r_keys[:5])
elif isinstance(reader, list):
    print('   entries:', len(reader), '第一条 keys:', list(reader[0].keys()) if reader else None)
