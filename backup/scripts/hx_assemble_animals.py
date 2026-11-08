#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动物与伙伴（102 词）装配脚本（改造自 hx_assemble_basic77.py）：
1) gen_art PNG -> artwork 700x560 webp + thumbs 240x192 webp（原缩略图备份）
2) gen_tts/raw_animals wav -> 词+句拼接 mp3（zero-gap 风格）+ 真实时长时间戳
3) word-reader.json 追加 102 卡 / word-index.json 解锁 / access.json 白名单追加
幂等：已存在的输出自动跳过，可重复执行。
"""
import json, os, subprocess, hashlib, shutil, sys, glob

SITE = '/home/z/my-project/henhaoxue-site'
ART, THUMBS, TA = f'{SITE}/learning/artwork', f'{SITE}/learning/thumbs', f'{SITE}/learning/trial-audio'
BAK = '/home/z/my-project/backup_animals'
os.makedirs(BAK, exist_ok=True)

HASHES = json.load(open('/home/z/my-project/gen_art/_hashes_animals.json'))
_c = json.load(open('/home/z/my-project/scripts/animals102_content.json'))
C = {it['id']: it for it in _c['items']}

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'cmd failed: {cmd}\n{r.stderr[-400:]}')
    return r.stdout.strip()

def dur(p):
    return float(sh(f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{p}"'))

# ---------- 1) 图像 ----------
def process_images():
    from PIL import Image
    done = 0
    for wid, d in C.items():
        png = f'/home/z/my-project/gen_art/{wid}.png'
        if not os.path.exists(png) or os.path.getsize(png) < 20000:
            continue
        h = HASHES[wid]
        awp = f'{ART}/{wid}-{h}.webp'
        im = Image.open(png).convert('RGB')
        W, H = im.size
        cw = min(W, round(H * 5 / 4))
        left = (W - cw) // 2
        im2 = im.crop((left, 0, left + cw, H)).resize((700, 560), Image.LANCZOS)
        if not os.path.exists(awp):
            im2.save(awp, 'WEBP', quality=82)
        tb = f'{THUMBS}/{wid}.webp'
        bak = f'{BAK}/{wid}.webp'
        if not os.path.exists(bak):
            shutil.copy2(tb, bak)
        im2.resize((240, 192), Image.LANCZOS).save(tb, 'WEBP', quality=78)
        done += 1
    print(f'images processed: {done}')
    return done

# ---------- 2) 音频 ----------
GAP = 0.35
def est_word_dur(word):
    return round(0.45 + 0.12 * max(len(word), 1), 3)

def process_audio():
    sil = '/home/z/my-project/gen_tts/sil.wav'
    if not os.path.exists(sil):
        sh(f'ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t {GAP} "{sil}"')
    made = 0
    stamps = {}
    RAW = '/home/z/my-project/gen_tts/raw_animals'
    for wid, d in C.items():
        for lv, key in (('easy','easy'), ('medium','med'), ('hard','hard')):
            wwav = f'{RAW}/{wid}__word.wav'
            swav = f'{RAW}/{wid}__{key}.wav'
            ah = hashlib.md5(f'{wid}{lv}iblock'.encode()).hexdigest()[:10]
            out = f'{TA}/{wid}-{lv}-{ah}.mp3'
            if os.path.exists(wwav) and os.path.exists(swav):
                if not os.path.exists(out):
                    sh(f'ffmpeg -y -i "{wwav}" -i "{sil}" -i "{swav}" -filter_complex '
                       f'"[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]" -map "[out]" -ar 24000 -ac 1 -b:a 64k "{out}"')
                wd, sd = dur(wwav), dur(swav)
                ss = round(wd + GAP, 3)
                ed = round(wd + GAP + sd + 0.12, 3)
            else:
                continue
            stamps[f'{wid}#{lv}'] = dict(src=f'../../learn/audio/zero-gap-v1/{wid}-{lv}-{ah}.mp3',
                                         wordStart=0, readingStart=0, sentenceStart=ss, end=ed)
            made += 1
    print(f'audio built: {made}')
    return stamps

# ---------- 3) JSON 装配 ----------
def assemble(stamps):
    rp = f'{SITE}/learning/content/word-reader.json'
    reader = json.load(open(rp))
    cards = reader['cards']
    pos = {c['id']: i for i, c in enumerate(cards)}
    filled = 0
    for wid, d in C.items():
        lvls = {}
        for lv, key in (('easy','easy'), ('medium','med'), ('hard','hard')):
            s = stamps.get(f'{wid}#{lv}')
            if s:
                lvls[lv] = dict(sentence=d[key][0], translation=d[key][1],
                                audio=dict(src=s['src'], wordStart=0, readingStart=0,
                                           sentenceStart=s['sentenceStart'], end=s['end']))
            else:
                lvls[lv] = dict(sentence=d[key][0], translation=d[key][1])
        card = dict(
            id=wid, word=d['word'], phonetic=d['ph'], meaning=d['meaning'],
            sentence=d['easy'][0], translation=d['easy'][1], category='动物与伙伴',
            audio=dict(src='', wordStart=0, sentenceStart=0, end=0),
            image=f"../artwork/{wid}-{HASHES[wid]}.webp",
            thumbnail=f'../thumbs/{wid}.webp',
            levels=lvls)
        if wid in pos:
            cards[pos[wid]] = card
        else:
            cards.append(card)
        filled += 1
    json.dump(reader, open(rp, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'reader cards filled: {filled}')

    ip = f'{SITE}/learning/content/word-index.json'
    idx = json.load(open(ip))
    n = 0
    for w in idx['words']:
        if w['id'] in C and w.get('locked'):
            w['locked'] = False; n += 1
    json.dump(idx, open(ip, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'index unlocked: {n}')

    ap = f'{SITE}/learning/content/access.json'
    acc = json.load(open(ap))
    pol = acc.setdefault('policy', {}).setdefault('words', [])
    add = [w for w in C if w not in pol]
    pol.extend(add)
    json.dump(acc, open(ap, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'policy words added: {len(add)}, total={len(pol)}')

if __name__ == '__main__':
    n_img = process_images()
    stamps = process_audio()
    if n_img < 102 or len(stamps) < 306:
        print(f'!!! 资源未齐: images={n_img}/102 audio={len(stamps)}/306 —— 仅部分装配')
    assemble(stamps)
    print('ASSEMBLY DONE')
