#!/usr/bin/env python3
"""核对 word-reader.json 引用的所有图片在线上是否 200（批量并发 HEAD）"""
import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor

BASE = '/learning/content'
ROOT = 'https://bk.hijoe.net'
LOCAL = '/home/z/my-project/henhaoxue-site'

d = json.load(open(os.path.join(LOCAL, 'learning/content/word-reader.json')))

def norm(rel):
    # relative to /learning/content/
    parts = []
    for seg in (BASE + '/' + rel).split('/'):
        if seg == '..':
            if parts: parts.pop()
        elif seg not in ('', '.'):
            parts.append(seg)
    return '/' + '/'.join(parts)

refs = set()
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('thumbnail', 'image', 'imageLarge', 'cover', 'imageUrl') and isinstance(v, str) and v:
                refs.add(norm(v))
            else:
                walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
walk(d)
refs = sorted(refs)
print('unique image refs:', len(refs))

def check(u):
    try:
        out = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '20', '-I', ROOT + u],
                             capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        out = 'TIMEOUT'
    return u, out

bad = []
with ThreadPoolExecutor(max_workers=12) as ex:
    for u, code in ex.map(check, refs):
        if code != '200':
            bad.append((u, code))

print('checked:', len(refs), ' bad:', len(bad))
for u, c in bad:
    print(c, u)
if not bad:
    print('ALL IMAGES 200 ONLINE')
