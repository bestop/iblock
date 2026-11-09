import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

// 断点续跑批次：node zai_tts_batch.mjs（可重复执行，只补缺失/损坏文件）
const CONTENT = JSON.parse(fs.readFileSync(process.env.CONTENT_JSON || '/home/z/my-project/scripts/basic77_content.json', 'utf8'));
const OUT = process.env.OUT_RAW || '/home/z/my-project/gen_tts/raw';
fs.mkdirSync(OUT, { recursive: true });

const CONCURRENCY = 1;
const GAP_MIN = 2200;         // 成功后的基础间隔（AIMD 下限）
const GAP_MAX = 20000;        // 限流后的最大间隔
const SPEED = 0.9;
const VOICE = 'jam';
const BUDGET_MS = parseInt(process.env.BUDGET_MS || '480000'); // 单轮 8 分钟，适配沙箱 10 分钟上限
const MAX_ATTEMPTS = 12;
let gap = 3000;               // 当前自适应间隔

const tasks = [];
for (const it of CONTENT.items) {
  tasks.push({ id: it.id, kind: 'word', text: it.word, out: `${OUT}/${it.id}__word.wav` });
  for (const lv of ['easy', 'med', 'hard']) {
    tasks.push({ id: it.id, kind: lv, text: it[lv][0], out: `${OUT}/${it.id}__${lv}.wav` });
  }
}
const pending = tasks.filter(t => !(fs.existsSync(t.out) && fs.statSync(t.out).size > 10000));
console.log(`total=${tasks.length} pending=${pending.length}`);
if (pending.length === 0) { console.log('DONE ok=0 fail=0 (nothing to do)'); process.exit(0); }

const zai = await ZAI.create(); // 复用单实例

let ok = 0, fail = 0, idx = 0, consec429 = 0;
const t0 = Date.now();
const sleep = ms => new Promise(s => setTimeout(s, ms));
// 所有等待都受预算钳制：确保脚本总能在 BUDGET_MS+~30s 内自行结束，不会被 shell 强杀
const sleepCapped = async ms => {
  const room = BUDGET_MS + 8000 - (Date.now() - t0);
  const w = Math.max(0, Math.min(ms, room));
  if (w > 0) await sleep(w);
};

async function worker() {
  while (idx < pending.length) {
    if (Date.now() - t0 > BUDGET_MS) { console.log('TIME BUDGET reached'); return; }
    if (consec429 >= 15) { console.log('QUOTA HARD STOP: 15 consecutive 429'); return; }
    const t = pending[idx++];
    let done = false;
    for (let attempt = 1; attempt <= MAX_ATTEMPTS && !done; attempt++) {
      try {
        const r = await zai.audio.tts.create({
          input: t.text, voice: VOICE, speed: SPEED, response_format: 'wav', stream: false
        });
        const ab = await r.arrayBuffer();
        const buf = Buffer.from(new Uint8Array(ab));
        if (buf.length < 5000) throw new Error('too small ' + buf.length);
        fs.writeFileSync(t.out, buf);
        ok++; done = true; consec429 = 0;
        gap = Math.max(GAP_MIN, gap * 0.85); // 成功后缓慢收紧间隔
        console.log(`OK ${t.id}__${t.kind} ${buf.length}B (${ok}/${pending.length}) gap=${gap | 0}ms`);
      } catch (e) {
        const msg = (e.message || '').slice(0, 110);
        const is429 = /429|Too many/i.test(msg);
        if (attempt === MAX_ATTEMPTS) {
          fail++; console.error(`GIVEUP ${t.id}__${t.kind}: ${msg}`);
        } else {
          const wait = is429 ? Math.min(20000 * attempt, 120000) : 6000 * attempt;
          if (is429) { consec429++; gap = Math.min(gap * 1.5 + 1500, GAP_MAX); }
          console.error(`ERR ${t.id}__${t.kind} a${attempt}: ${msg} -> wait ${wait / 1000}s gap=${gap | 0}ms`);
          await sleepCapped(wait);
        }
      }
    }
    await sleepCapped(gap);
  }
}
await Promise.all(Array.from({ length: CONCURRENCY }, worker));
console.log(`DONE ok=${ok} fail=${fail} elapsed=${((Date.now() - t0) / 1000 | 0)}s remaining=${pending.length - ok}`);
