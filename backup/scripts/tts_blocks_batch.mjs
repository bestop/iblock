import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import { execFileSync } from 'child_process';

process.on('unhandledRejection', e => console.log('UNHANDLED', String(e).slice(0, 120)));
process.on('uncaughtException', e => console.log('UNCAUGHT', String(e).slice(0, 120)));

const PLAN = '/tmp/build_blocks/plan.json';
const OUTDIR = '/home/z/my-project/henhaoxue-site/learning/trial-audio';
const TMP = '/tmp/build_blocks';
const TIMINGS = TMP + '/timings.json';

const plan = JSON.parse(fs.readFileSync(PLAN, 'utf-8'));
const timings = fs.existsSync(TIMINGS) ? JSON.parse(fs.readFileSync(TIMINGS, 'utf-8')) : {};
const BUDGET_MS = parseInt(process.env.BUDGET_MS || '480000');
let zai;
try { zai = await ZAI.create(); } catch (e) { console.log('ZAI.create failed', String(e).slice(0, 120)); process.exit(1); }

let done = 0, fail = 0, skip = 0;
const t0 = Date.now();
const sleep = ms => new Promise(r => setTimeout(r, ms));

for (const item of plan) {
  if (Date.now() - t0 > BUDGET_MS) { console.log('TIME BUDGET reached'); break; }
  const base = `${item.id}-easy-g1`;
  const mp3 = `${OUTDIR}/${base}.mp3`;
  if (fs.existsSync(mp3) && fs.statSync(mp3).size > 3000) { skip++; continue; }

  const wav = `${TMP}/${base}.wav`;
  let ok = false, lastErr = '';
  for (let k = 1; k <= 8 && !ok; k++) {
    try {
      const resp = await zai.audio.tts.create({
        input: item.tts_text, voice: 'kazi', speed: 1.0,
        response_format: 'wav', stream: false,
      });
      const buf = Buffer.from(new Uint8Array(await resp.arrayBuffer()));
      if (buf.length < 5000) throw new Error('too small ' + buf.length);
      fs.writeFileSync(wav, buf);
      ok = true;
    } catch (e) {
      lastErr = String(e && e.message || e).slice(0, 100);
      const is429 = /429|Too many/i.test(lastErr);
      const is405 = /405|blocked|threat/i.test(lastErr);
      await sleep(is429 ? Math.min(15000 * k, 90000) : is405 ? 12000 : 5000 * k);
    }
  }
  if (!ok) { fail++; console.log(`FAIL ${item.id}: ${lastErr}`); continue; }

  try {
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', wav,
      '-codec:a', 'libmp3lame', '-b:a', '48k', '-ac', '1', '-ar', '24000', mp3]);
    fs.unlinkSync(wav);
    const dur = parseFloat(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration',
      '-of', 'csv=p=0', mp3]).toString().trim());
    const wordDur = Math.max(0.7, 0.4 + 0.075 * item.word.length) + 0.25;
    timings[item.id] = {
      file: base + '.mp3',
      wordStart: 0, readingStart: 0,
      sentenceStart: Math.round(Math.min(wordDur, Math.max(0.8, dur - 0.5)) * 1000) / 1000,
      end: Math.round(dur * 1000) / 1000,
    };
    done++;
  } catch (e) {
    fail++;
    console.log(`FFMPEG FAIL ${item.id}: ${String(e).slice(0, 80)}`);
  }
  if (done % 10 === 0) {
    fs.writeFileSync(TIMINGS, JSON.stringify(timings, null, 1));
    console.log(`${done} done, ${skip} skip, ${fail} fail, ${(Date.now() - t0) / 1000 | 0}s`);
  }
  await sleep(1200 + Math.random() * 900);
}

fs.writeFileSync(TIMINGS, JSON.stringify(timings, null, 1));
console.log(`BATCH END: ${done} generated, ${skip} skipped, ${fail} failed, total ${((Date.now() - t0) / 60000).toFixed(1)}min`);
