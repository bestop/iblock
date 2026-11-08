#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按计划清单执行 TTS（Phase1 优先 comb/easy，再 med/hard），断点续跑"""
import json, os, subprocess, time, sys

RAW = '/home/z/my-project/gen_tts/raw'
plan = json.load(open('/home/z/my-project/scripts/basic77_tts_plan.json'))

def done(kind, wid):
    if kind == 'comb':
        p = f'{RAW}/{wid}__easycomb.wav'
        return os.path.exists(p) and os.path.getsize(p) > 10000
    return os.path.exists(f'{RAW}/{wid}__{kind}.wav') and os.path.getsize(f'{RAW}/{wid}__{kind}.wav') > 10000

# 排序：comb 优先，其次 easy，然后 med/hard
rank = {'comb': 0, 'tts': 1}
def prio(item):
    k, wid, cmd = item
    if k == 'comb': return (0, wid)
    f = cmd.split('__')[-1].split('.wav')[0]
    return ({'easy': 1, 'med': 2, 'hard': 3}.get(f, 4), wid)

tasks = [t for t in plan if not done(t[0], t[1])]
tasks.sort(key=prio)
print(f'queue: {len(tasks)}', flush=True)

t0 = time.time()
DEADLINE = 360
ok = fail = 0
for kind, wid, cmd in tasks:
    if time.time() - t0 > DEADLINE:
        print('SLICE END', flush=True); break
    label = f'{kind}:{wid}'
    good = False
    err = ''
    for attempt in range(3):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            out = (r.stdout or '') + (r.stderr or '')
            if r.returncode == 0 and 'TTS_OK' in out:
                good = True; break
            err = (out.strip().splitlines() or ['?'])[-1][:80]
        except subprocess.TimeoutExpired:
            err = 'TIMEOUT'
        if '429' in str(err):
            time.sleep(100)
            if time.time() - t0 > DEADLINE: break
        else:
            time.sleep(5)
    if good:
        ok += 1
        print(f'[{round(time.time()-t0)}s] OK {label} ({ok})', flush=True)
        time.sleep(7)
    else:
        fail += 1
        print(f'GIVEUP {label}: {err}', flush=True)
print(f'SLICE DONE ok={ok} fail={fail} elapsed={round(time.time()-t0)}s', flush=True)
