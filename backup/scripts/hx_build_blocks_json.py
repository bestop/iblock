#!/usr/bin/env python3
"""构建 word-reader-build.json（方块与建造 267 卡）
- 词库/缩略图来自 word-index.json（真实数据）
- 例句来自 plan.json（生成内容）
- 音频：仅当 trial-audio/<id>-easy-g1.mp3 存在时挂载 easy.audio
- image 用 thumbs（artwork 哈希不可知）
"""
import json, os

SITE = '/home/z/my-project/henhaoxue-site'
plan = json.load(open('/tmp/build_blocks/plan.json'))
wi = json.load(open(f'{SITE}/learning/content/word-index.json'))
by_id = {w['id']: w for w in wi['words']}
timings_path = '/tmp/build_blocks/timings.json'
timings = json.load(open(timings_path)) if os.path.exists(timings_path) else {}

cards, index, missing_thumb = [], [], []
for p in plan:
    w = by_id[p['id']]
    thumb = w['thumbnail']  # ../thumbs/<id>.webp
    if not os.path.isfile(f'{SITE}/learning/content/{thumb}'):
        missing_thumb.append(p['id'])
    card = {
        'id': p['id'], 'word': w['word'], 'phonetic': '',
        'meaning': w['meaning'],
        'sentence': p['levels']['easy']['sentence'],
        'translation': p['levels']['easy']['translation'],
        'category': '方块与建造',
        'audio': {'src': '', 'wordStart': 0, 'sentenceStart': 0, 'end': 0},
        'image': thumb, 'thumbnail': thumb,
        'levels': {},
    }
    for lv in ('easy', 'medium', 'hard'):
        lvdata = {'sentence': p['levels'][lv]['sentence'], 'translation': p['levels'][lv]['translation']}
        if lv == 'easy' and p['id'] in timings:
            t = timings[p['id']]
            lvdata['audio'] = {'src': f'../../learn/audio/zero-gap-v1/{t["file"]}',
                               'wordStart': t['wordStart'], 'readingStart': t['readingStart'],
                               'sentenceStart': t['sentenceStart'], 'end': t['end']}
        card['levels'][lv] = lvdata
    cards.append(card)
    index.append({'id': p['id'], 'word': w['word'], 'meaning': w['meaning'],
                  'category': '方块与建造', 'thumbnail': thumb})

out = {'category': '方块与建造', 'index': index, 'cards': cards}
path = f'{SITE}/learning/content/word-reader-build.json'
json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
audio_n = sum(1 for c in cards if 'audio' in c['levels']['easy'])
print(f'written {path}: {len(cards)} cards, {os.path.getsize(path)} bytes, audio attached: {audio_n}, missing thumbs: {len(missing_thumb)}')
