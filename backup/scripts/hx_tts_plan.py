#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘点每词音频覆盖，输出 Phase-1（easy 级补齐）所需的最小 TTS 任务清单"""
import os, json, sys
sys.path.insert(0, '/home/z/my-project/scripts')
from hx_content_basic77 import C

RAW = '/home/z/my-project/gen_tts/raw'
def has(wid, kind):
    p = f'{RAW}/{wid}__{kind}.wav'
    return os.path.exists(p) and os.path.getsize(p) > 10000

need_word = need_easy = need_med = need_hard = 0
plan = []
for wid, d in C.items():
    w, e = has(wid, 'word'), has(wid, 'easy')
    m, h = has(wid, 'med'), has(wid, 'hard')
    if not w: need_word += 1
    if not e:
        need_easy += 1
        # 词与例句都缺 → 合成一条 combined
        if not w:
            plan.append(('comb', wid, f'node scripts/zai_one.mjs {RAW}/{wid}__easycomb.wav jam 0.9 "{d["word"]}. {d["easy"][0]}"'))
        # 词在句缺 → 只补 easy 句
        else:
            plan.append(('tts', wid, f'node scripts/zai_one.mjs {RAW}/{wid}__easy.wav jam 0.9 "{d["easy"][0]}"'))
    if not m:
        need_med += 1
        plan.append(('tts', wid, f'node scripts/zai_one.mjs {RAW}/{wid}__med.wav jam 0.9 "{d["med"][0]}"'))
    if not h:
        need_hard += 1
        plan.append(('tts', wid, f'node scripts/zai_one.mjs {RAW}/{wid}__hard.wav jam 0.9 "{d["hard"][0]}"'))

print(f'缺词音频: {need_word}  缺easy: {need_easy}  缺med: {need_med}  缺hard: {need_hard}')
print(f'Phase1(easy+combined) 调用数: {sum(1 for p in plan if p[0]=="comb")}')
print(f'总剩余调用: {len(plan)}')
json.dump(plan, open('/home/z/my-project/scripts/basic77_tts_plan.json', 'w'), ensure_ascii=False, indent=1)
