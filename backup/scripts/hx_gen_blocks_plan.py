#!/usr/bin/env python3
"""生成「方块与建造」267 词的例句计划(3 难度) + TTS 输入文本"""
import json, re, os

SITE = '/home/z/my-project/henhaoxue-site'
wi = json.load(open(f'{SITE}/learning/content/word-index.json'))
words = [w for w in wi['words'] if w['category'] == '方块与建造']
assert len(words) == 267, len(words)

VOWELS = 'aeiouAEIOU'

def art(w):
    return 'some' if w in UNCOUNTABLE else ('an' if w[0] in VOWELS else 'a')

UNCOUNTABLE = {'Dirt', 'Snow', 'Ice', 'Glass', 'Wool', 'Clay', 'Concrete', 'Sand', 'Redstone Dust', 'Redstone Wire', 'Bedrock'}

def spoken(w):
    """TTS 朗读用文本"""
    return w

def in_sentence(w):
    """句中引用形式：全大写(如 T N T / TNT)保留，否则整体小写"""
    if not re.search(r'[a-z]', w):
        return w
    return w.lower()

TPL = {
    'easy': [
        ("This is {a} {w}.", "这是{a_zh}{m}。"),
        ("I see {a} {w}.", "我看见了{a_zh}{m}。"),
        ("Look at that {w}!", "看那个{m}！"),
        ("I place the {w} here.", "我把{m}放在这里。"),
        ("I need {a} {w}.", "我需要{a_zh}{m}。"),
        ("Here is the {w}.", "这是{m}。"),
    ],
    'medium': [
        ("I use the {w} to build a small house.", "我用{m}建了一座小房子。"),
        ("Put the {w} next to the door, please.", "请把{m}放在门旁边。"),
        ("The {w} is very useful when you build your base.", "建造基地的时候，{m}非常有用。"),
        ("We made a wall with the {w} yesterday.", "昨天我们用{m}砌了一堵墙。"),
        ("You can find the {w} in almost every world.", "几乎在每个世界里你都能找到{m}。"),
        ("My friend gave me {a} {w} as a gift.", "朋友送了我{a_zh}{m}当礼物。"),
    ],
    'hard': [
        ("When I start a new world, I always craft {a} {w} first, because it makes building much easier.", "开始新世界时，我总会先做{a_zh}{m}，因为它能让建造轻松很多。"),
        ("Before the sun goes down, I place the {w} beside my shelter so that monsters cannot sneak in.", "太阳落山前，我把{m}放在庇护所旁边，这样怪物就溜不进来。"),
        ("If you want your base to look amazing, try mixing the {w} with wood and stone.", "如果你想让基地看起来更棒，试试把{m}和木头、石头搭配使用。"),
        ("My brother spent the whole afternoon building a tower, and the {w} was the last part he finished.", "弟弟花了一下午建塔，{m}是他最后完成的部分。"),
        ("The {w} is not easy to find, but once you get one, your builds will look much better.", "{m}并不容易找到，但一旦拥有，你的建筑会好看很多。"),
        ("We ran out of materials, so I had to trade three diamonds for {a} {w}.", "材料用完了，我只好用三颗钻石换了{a_zh}{m}。"),
    ],
}

def zh_art(w):
    return '一些' if w in UNCOUNTABLE else '一个'

plan = []
for i, w in enumerate(words):
    item = {'id': w['id'], 'word': w['word'], 'meaning': w['meaning'],
            'tts_text': f"{spoken(w['word'])}. ", 'levels': {}}
    # TTS: 单词 + easy 句子(一段音频)
    we = in_sentence(w['word'])
    e_tpl = TPL['easy'][(i * 5 + 1) % 6]
    easy_en = e_tpl[0].format(a=art(w['word']), w=we, m=w['meaning'])
    item['tts_text'] += easy_en
    item['levels']['easy'] = {'sentence': easy_en, 'translation': e_tpl[1].format(a_zh=zh_art(w['word']), m=w['meaning'])}
    for lv, stride in (('medium', 3), ('hard', 5)):
        t = TPL[lv][(i * stride + 2) % 6]
        en = t[0].format(a=art(w['word']), w=we, m=w['meaning'])
        item['levels'][lv] = {'sentence': en, 'translation': t[1].format(a_zh=zh_art(w['word']), m=w['meaning'])}
    plan.append(item)

os.makedirs('/tmp/build_blocks', exist_ok=True)
json.dump(plan, open('/tmp/build_blocks/plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('plan written:', len(plan))
# 抽样检查
for p in plan[:3] + plan[130:132]:
    print(f"  {p['word']} | {p['tts_text'][:70]}")
# 词表清洗检查：异常字符
bad = [p['word'] for p in plan if re.search(r'[^\w\s\-\.]', p['word'])]
print('odd words:', bad)
