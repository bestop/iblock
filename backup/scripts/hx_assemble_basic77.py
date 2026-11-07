#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""装配脚本：
1) gen_art PNG -> artwork 700x560 webp + thumbs 240x192 webp（原缩略图备份）
2) gen_tts wav -> 词+句拼接 mp3（zero-gap 风格）+ 真实时长时间戳
3) word-reader.json 填充 77 卡 / word-index.json 解锁 / access.json 白名单追加
"""
import json, os, subprocess, hashlib, shutil, sys, glob

sys.path.insert(0, '/home/z/my-project/scripts')
from hx_content_basic77 import C

SITE = '/home/z/my-project/henhaoxue-site'
ART, THUMBS, TA = f'{SITE}/learning/artwork', f'{SITE}/learning/thumbs', f'{SITE}/learning/trial-audio'
BAK = '/home/z/my-project/backup_basic77'
os.makedirs(BAK, exist_ok=True)

HASHES = json.load(open('/home/z/my-project/gen_art/_hashes.json'))

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
    pngs = glob.glob('/home/z/my-project/gen_art/*.png')
    done = 0
    for png in pngs:
        wid = os.path.basename(png)[:-4]
        if wid not in HASHES: continue
        h = HASHES[wid]
        awp = f'{ART}/{wid}-{h}.webp'
        # 1152x864 -> 居中裁 1080x864 (5:4) -> 700x560
        im = Image.open(png).convert('RGB')
        W, H = im.size
        cw = min(W, round(H * 5 / 4))
        left = (W - cw) // 2
        im2 = im.crop((left, 0, left + cw, H)).resize((700, 560), Image.LANCZOS)
        if not os.path.exists(awp):
            im2.save(awp, 'WEBP', quality=82)
        # 缩略图 240x192（备份原图一次）
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
    """无词音频时按词长估算（秒）"""
    return round(0.45 + 0.12 * max(len(word), 1), 3)

def process_audio():
    # 统一 0.35s 静音
    sil = '/home/z/my-project/gen_tts/sil.wav'
    if not os.path.exists(sil):
        sh(f'ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t {GAP} "{sil}"')
    made = 0
    stamps = {}
    for wid, d in C.items():
        for lv, key in (('easy','easy'), ('medium','med'), ('hard','hard')):
            wwav = f'/home/z/my-project/gen_tts/raw/{wid}__word.wav'
            swav = f'/home/z/my-project/gen_tts/raw/{wid}__{key}.wav'
            comb = f'/home/z/my-project/gen_tts/raw/{wid}__easycomb.wav'
            ah = hashlib.md5(f'{wid}{lv}iblock'.encode()).hexdigest()[:10]
            out = f'{TA}/{wid}-{lv}-{ah}.mp3'
            if lv == 'easy' and os.path.exists(comb) and os.path.getsize(comb) > 10000:
                # combined: 词+句已在一条里，直接转码；sentenceStart 按词长估算
                if not os.path.exists(out):
                    sh(f'ffmpeg -y -i "{comb}" -ar 24000 -ac 1 -b:a 64k "{out}"')
                ss = est_word_dur(d['word'])
                ed = round(dur(comb) + 0.12, 3)
            elif os.path.exists(wwav) and os.path.exists(swav):
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
    # word-reader.json
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
            sentence=d['easy'][0], translation=d['easy'][1], category='基础方块世界',
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

    # word-index.json 解锁
    ip = f'{SITE}/learning/content/word-index.json'
    idx = json.load(open(ip))
    n = 0
    for w in idx['words']:
        if w['id'] in C and w.get('locked'):
            w['locked'] = False; n += 1
    json.dump(idx, open(ip, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'index unlocked: {n}')

    # access.json 白名单追加
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
    if n_img < 77 or len(stamps) < 231:
        print(f'!!! 资源未齐: images={n_img}/77 audio={len(stamps)}/231 —— 仅部分装配')
    assemble(stamps)
    print('ASSEMBLY DONE')
