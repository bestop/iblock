import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

const OUT = '/tmp/tts_test/pool';
fs.mkdirSync(OUT, { recursive: true });

const items = Array.from({ length: 12 }, (_, i) => ({
  file: `${OUT}/p${i}.wav`,
  text: `Sample ${i}. I use this block to build my house in the game.`,
}));

const stats = { ok: 0, fail: 0 };
const zai = await ZAI.create();

async function one(item, tries = 3) {
  for (let k = 1; k <= tries; k++) {
    try {
      const resp = await zai.audio.tts.create({
        input: item.text,
        voice: 'kazi',
        speed: 1.0,
        response_format: 'wav',
        stream: false,
      });
      const buf = Buffer.from(new Uint8Array(await resp.arrayBuffer()));
      if (buf.length < 5000) throw new Error('too small: ' + buf.length);
      fs.writeFileSync(item.file, buf);
      stats.ok++;
      return true;
    } catch (e) {
      if (k === tries) {
        stats.fail++;
        console.log('FAIL', item.file, e.message?.slice(0, 120));
        return false;
      }
      await new Promise(r => setTimeout(r, 800 * k));
    }
  }
}

const t0 = Date.now();
// concurrency pool of 4
let idx = 0;
async function worker() {
  while (idx < items.length) {
    const it = items[idx++];
    await one(it);
  }
}
await Promise.all(Array.from({ length: 4 }, worker));
console.log(`done in ${((Date.now() - t0) / 1000).toFixed(1)}s ok=${stats.ok} fail=${stats.fail}`);
