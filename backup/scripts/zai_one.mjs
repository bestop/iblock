import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

// 一次性任务进程: node zai_one.mjs <out> <voice> <speed> <text>
const [,, outPath, voice, speed, ...rest] = process.argv;
const text = rest.join(' ');

async function main() {
  const zai = await ZAI.create();
  const r = await zai.audio.tts.create({
    input: text, voice, speed: parseFloat(speed), response_format: 'wav', stream: false
  });
  const ab = await r.arrayBuffer();
  fs.writeFileSync(outPath, Buffer.from(new Uint8Array(ab)));
  console.log('TTS_OK', fs.statSync(outPath).size);
}
main().catch(e => { console.error('FAIL ' + (e.message || '').slice(0, 200)); process.exit(1); });
