import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

const [,, mode, outPath, arg] = process.argv;

async function main() {
  const zai = await ZAI.create();
  if (mode === 'tts') {
    const response = await zai.audio.tts.create({
      input: arg, voice: 'jam', speed: 1.0, response_format: 'mp3', stream: false
    });
    const ab = await response.arrayBuffer();
    fs.writeFileSync(outPath, Buffer.from(new Uint8Array(ab)));
    console.log('TTS_OK', fs.statSync(outPath).size);
  } else if (mode === 'img') {
    const response = await zai.images.generations.create({
      prompt: arg, size: '1152x864'
    });
    const b64 = response.data[0].base64;
    fs.writeFileSync(outPath, Buffer.from(b64, 'base64'));
    console.log('IMG_OK', fs.statSync(outPath).size);
  }
}
main().catch(e => { console.error('FAIL', e.message?.slice(0, 300)); process.exit(1); });
