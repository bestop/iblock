#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核查基础方块世界 87 词引用的全部资源在位情况"""
import json, os, posixpath

ROOT = '/home/z/my-project/henhaoxue-site/learning'
reader = json.load(open(f'{ROOT}/content/word-reader.json'))
cards = reader['cards']

def resolve(base_dir, rel):
    if not rel: return None
    p = posixpath.normpath(posixpath.join(base_dir, rel))
    return os.path.join('/home/z/my-project/henhaoxue-site', p)

stats = {'audio': [0,0], 'image': [0,0], 'thumb': [0,0]}
miss_audio, miss_img = [], []
audio_srcs = set()

for c in cards:
    # thumbnail
    t = resolve('learning/content', c.get('thumbnail'))
    stats['thumb'][0 if (t and os.path.exists(t)) else 1] += 1
    # artwork image
    i = resolve('learning/content', c.get('image'))
    ok = i and os.path.exists(i)
    stats['image'][0 if ok else 1] += 1
    if not ok: miss_img.append((c['id'], c.get('image')))
    # levels audio
    for lv, lvdata in (c.get('levels') or {}).items():
        src = (lvdata.get('audio') or {}).get('src', '')
        if src:
            audio_srcs.add(src)
            a = resolve('learning/content', src)
            exists = a and os.path.exists(a)
            if lv == 'easy':
                stats['audio'][0 if exists else 1] += 1
            if not exists:
                miss_audio.append((c['id'], lv, src))

print('基础方块世界 87 卡资源在位统计（本地）:')
print(f"  thumbnail: 存在={stats['thumb'][0]} 缺失={stats['thumb'][1]}")
print(f"  artwork  : 存在={stats['image'][0]} 缺失={stats['image'][1]}")
print(f"  audio(easy级): 存在={stats['audio'][0]} 缺失={stats['audio'][1]}")
print(f"  音频文件引用总数(去重): {len(audio_srcs)}")

if miss_img:
    print('\n缺失 artwork 样例:')
    for x in miss_img[:5]: print('  ', x)
if miss_audio:
    print('\n缺失音频样例:')
    for x in miss_audio[:5]: print('  ', x)

# 音频目录里有什么
aud_dir = '/home/z/my-project/henhaoxue-site/learn/audio/zero-gap-v1'
if os.path.isdir(aud_dir):
    n = len(os.listdir(aud_dir))
    bb = [f for f in os.listdir(aud_dir) if f.startswith('basic_block_world')]
    print(f'\nlearn/audio/zero-gap-v1: 总文件={n}, basic_block_world 前缀={len(bb)}')
else:
    print('\nlearn/audio/zero-gap-v1 目录不存在')
    # 找音频实际位置
    for d in ['/home/z/my-project/henhaoxue-site/learning/audio',
              '/home/z/my-project/henhaoxue-site/learn']:
        if os.path.isdir(d):
            subs = []
            for root, dirs, files in os.walk(d):
                if files and len(subs) < 12:
                    mp3 = [f for f in files if f.endswith('.mp3')]
                    if mp3: subs.append((root.replace('/home/z/my-project/henhaoxue-site/',''), len(os.listdir(root))))
            print('  有 mp3 的目录:', subs[:10])
