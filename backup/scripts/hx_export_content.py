#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 77 词内容数据完整性，导出 JSON 供生成脚本使用"""
import json, sys
sys.path.insert(0, '/home/z/my-project/scripts')
from hx_content_basic77 import C, STYLE

ROOT = '/home/z/my-project/henhaoxue-site/learning'
idx = json.load(open(f'{ROOT}/content/word-index.json'))
locked = {w['id']: w for w in idx['words'] if w['category'] == '基础方块世界' and w.get('locked')}

errs = []
if set(C) != set(locked):
    errs.append(f'id 集合不一致: 缺{set(locked)-set(C)} 多{set(C)-set(locked)}')
for i, d in C.items():
    if d['word'] != locked[i]['word']:
        errs.append(f'{i}: word 不一致 {d["word"]} vs {locked[i]["word"]}')
    if d['meaning'] != locked[i]['meaning']:
        errs.append(f'{i}: meaning 不一致 {d["meaning"]} vs {locked[i]["meaning"]}')
    for k in ('ph', 'easy', 'med', 'hard', 'prompt'):
        if k not in d or not d[k]:
            errs.append(f'{i}: 缺字段 {k}')
    for k in ('easy', 'med', 'hard'):
        if len(d[k]) != 2 or not d[k][0] or not d[k][1]:
            errs.append(f'{i}: {k} 结构错误')

if errs:
    print('校验失败:'); [print(' ', e) for e in errs[:20]]; sys.exit(1)
print(f'校验通过: {len(C)} 条内容与锁定词一一对应')

out = {'style': STYLE, 'items': [
    dict(id=i, word=d['word'], meaning=d['meaning'], ph=d['ph'],
         easy=d['easy'], med=d['med'], hard=d['hard'], prompt=d['prompt'])
    for i, d in C.items()]}
json.dump(out, open('/home/z/my-project/scripts/basic77_content.json', 'w'), ensure_ascii=False, indent=1)
print('已导出 scripts/basic77_content.json')
