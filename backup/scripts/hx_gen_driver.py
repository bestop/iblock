#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一单队列生成驱动：图像(70) + TTS(288)，全局单并发、自适应退避、进程级超时"""
import json, os, subprocess, time, sys

sys.path.insert(0, '/home/z/my-project/scripts')
from hx_content_basic77 import C, STYLE

ART = '/home/z/my-project/gen_art'
RAW = '/home/z/my-project/gen_tts/raw'
os.makedirs(RAW, exist_ok=True)

def img_done(wid):
    p = f'{ART}/{wid}.png'
    return os.path.exists(p) and os.path.getsize(p) > 20000

def tts_done(wid, kind):
    p = f'{RAW}/{wid}__{kind}.wav'
    return os.path.exists(p) and os.path.getsize(p) > 10000

tasks = []
for wid, d in C.items():
    if not img_done(wid):
        tasks.append(('img', wid, None, f'node scripts/zai_test.mjs img {ART}/{wid}.png "{d["prompt"]}, {STYLE}"'))
for wid, d in C.items():
    if not tts_done(wid, 'word'):
        tasks.append(('tts', wid, 'word', f'node scripts/zai_one.mjs {RAW}/{wid}__word.wav jam 0.9 "{d["word"]}"'))
    for lv in ('easy', 'med', 'hard'):
        if not tts_done(wid, lv):
            tasks.append(('tts', wid, lv, f'node scripts/zai_one.mjs {RAW}/{wid}__{lv}.wav jam 0.9 "{d[lv][0]}"'))

print(f'queue: {len(tasks)} tasks (img {sum(1 for t in tasks if t[0]=="img")}, tts {sum(1 for t in tasks if t[0]=="tts")})', flush=True)

ok = fail = 0
backoff = 3.0
t0 = time.time()
DEADLINE = 330  # 单次前台运行 9 分钟后优雅收尾
for i, (kind, wid, lv, cmd) in enumerate(tasks):
    if time.time() - t0 > DEADLINE:
        print(f'TIME SLICE END at task {i}/{len(tasks)}', flush=True)
        break
    label = f'{kind}:{wid}' + (f'__{lv}' if lv else '')
    success = False
    for attempt in range(1, 4):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=150)
            out = (r.stdout or '') + (r.stderr or '')
            if r.returncode == 0 and ('IMG_OK' in out or 'TTS_OK' in out):
                success = True
                break
            err = out.strip().splitlines()[-1][:90] if out.strip() else 'empty'
        except subprocess.TimeoutExpired:
            err = 'TIMEOUT150'
        # 429 / 失败 → 退避
        if '429' in str(err):
            time.sleep(100)
            if time.time() - t0 > DEADLINE: break
        else:
            time.sleep(backoff)
        backoff = min(backoff * 1.6, 45)
    if success:
        ok += 1
        backoff = max(2.0, backoff * 0.7)
        el = round(time.time() - t0)
        print(f'[{el}s] OK {label} ({ok})', flush=True)
    else:
        fail += 1
        print(f'GIVEUP {label}: {err}', flush=True)
    time.sleep(1.5)

print(f'DRIVER SLICE DONE ok={ok} fail={fail} elapsed={round(time.time()-t0)}s', flush=True)
