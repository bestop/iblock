import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import crypto from 'crypto';

const CONTENT = JSON.parse(fs.readFileSync(process.env.CONTENT_JSON || '/home/z/my-project/scripts/basic77_content.json', 'utf8'));
const OUT = process.env.OUT_DIR || '/home/z/my-project/gen_art';
const BUDGET_MS = parseInt(process.env.BUDGET_MS || '999999999');
const t0 = Date.now();
fs.mkdirSync(OUT, { recursive: true });

const CONCURRENCY = 2;
const GAP_MS = 2500;
const tasks = CONTENT.items.map(it => {
  const hash = crypto.createHash('md5').update(it.id + it.word).digest('hex').slice(0, 10);
  return { id: it.id, word: it.word, prompt: `${it.prompt}, ${CONTENT.style}`, out: `${OUT}/${it.id}.png`, hash };
});

// 断点续跑:跳过已成功且 >20KB 的
const pending = tasks.filter(t => {
  if (fs.existsSync(t.out) && fs.statSync(t.out).size > 20000) return false;
  return true;
});
console.log(`total=${tasks.length} pending=${pending.length}`);

const sleepCapped = async ms => {
  const room = BUDGET_MS + 8000 - (Date.now() - t0);
  const w = Math.max(0, Math.min(ms, room));
  if (w > 0) await new Promise(s => setTimeout(s, w));
};

let ok = 0, fail = 0, idx = 0;
async function worker() {
  while (idx < pending.length) {
    if (Date.now() - t0 > BUDGET_MS) { console.log('TIME BUDGET reached'); return; }
    const t = pending[idx++];
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const zai = await ZAI.create();
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 90000);
        const r = await zai.images.generations.create({ prompt: t.prompt, size: '1152x864', signal: ctrl.signal }).finally(() => clearTimeout(timer));
        if (!r?.data?.[0]?.base64) throw new Error('empty base64');
        fs.writeFileSync(t.out, Buffer.from(r.data[0].base64, 'base64'));
        ok++;
        console.log(`OK ${t.word} ${t.id} (${ok}/${pending.length})`);
        break;
      } catch (e) {
        console.error(`ERR ${t.id} attempt${attempt}: ${(e.message || '').slice(0, 120)}`);
        if (attempt === 3) fail++;
        else await sleepCapped(4000 * attempt);
      }
    }
    await sleepCapped(GAP_MS);
  }
}
await Promise.all(Array.from({ length: CONCURRENCY }, worker));
console.log(`DONE ok=${ok} fail=${fail} elapsed=${((Date.now() - t0) / 1000 | 0)}s remaining=${pending.length - ok}`);
const TAG = process.env.TAG;
const hpath = TAG ? `${OUT}/_hashes_${TAG}.json` : '/home/z/my-project/gen_art/_hashes.json';
fs.writeFileSync(hpath,
  JSON.stringify(Object.fromEntries(tasks.map(t => [t.id, t.hash])), null, 1));
console.log('hashes ->', hpath);
