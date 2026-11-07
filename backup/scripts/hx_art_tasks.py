#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成图像任务清单（out|prompt），跳过已完成"""
import json, os, hashlib, sys
sys.path.insert(0, '/home/z/my-project/scripts')
from hx_content_basic77 import C, STYLE

OUT = '/home/z/my-project/gen_art'
os.makedirs(OUT, exist_ok=True)
lines = []
for wid, d in C.items():
    p = f'{OUT}/{wid}.png'
    if os.path.exists(p) and os.path.getsize(p) > 20000:
        continue
    prompt = f'{d["prompt"]}, {STYLE}'
    lines.append(f'{p}|{prompt}')
open('/home/z/my-project/gen_art/_tasks.txt', 'w').write('\n'.join(lines))
print(f'tasks: {len(lines)}')

# 与批量脚本一致的 hash 表（md5(id+word)[:10]）
hashes = {wid: hashlib.md5(f'{wid}{d["word"]}'.encode()).hexdigest()[:10] for wid, d in C.items()}
json.dump(hashes, open('/home/z/my-project/gen_art/_hashes.json', 'w'), indent=1)
print('hashes written')
