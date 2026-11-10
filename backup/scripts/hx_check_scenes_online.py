#!/usr/bin/env python3
"""核对 #scenes 场景图等 learning 静态目录在线上状态"""
import subprocess, os, glob
from concurrent.futures import ThreadPoolExecutor

ROOT = 'https://bk.hijoe.net'
LOCAL = '/home/z/my-project/henhaoxue-site/learning'

targets = []
for pat in ['reading-scenes/*.webp', 'scene-covers/*.webp', 'thumbs/*.webp', 'artwork/*.webp', 'category-covers/v1/*.webp', 'home-dialogue-images/*', 'phrase-images/*']:
    for p in glob.glob(os.path.join(LOCAL, pat)):
        targets.append('/learning/' + os.path.relpath(p, LOCAL))

targets = sorted(set(targets))
print('local files to check:', len(targets))

def check(u):
    try:
        out = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '20', '-I', ROOT + u],
                             capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        out = 'TIMEOUT'
    return u, out

bad = []
with ThreadPoolExecutor(max_workers=12) as ex:
    for u, code in ex.map(check, targets):
        if code != '200':
            bad.append((u, code))

print('bad:', len(bad))
for u, c in bad[:60]:
    print(c, u)
if not bad:
    print('ALL 200 ONLINE')
