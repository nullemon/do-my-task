// Renders the film headlessly with Playwright's Chromium.
//   node render.cjs --stills 1.5,4,10        -> out/stills/t_XX.png
//   node render.cjs --video out/video.mp4    -> H.264, no audio (mux separately)
//   options: --from <sec> --to <sec>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
const FPS = 24;

(async () => {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => { console.error('[pageerror]', e.message); process.exitCode = 1; });
  await page.goto('file://' + path.resolve(__dirname, 'index.html'));
  await page.evaluate(() => window.READY);

  const stills = opt('--stills');
  if (stills) {
    const dir = path.resolve(__dirname, 'out/stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of stills.split(',')) {
      const f = Math.round(parseFloat(s) * FPS);
      const t0 = Date.now();
      const url = await page.evaluate(f => { renderFrame(f); return document.getElementById('c').toDataURL('image/png'); }, f);
      const file = path.join(dir, `t_${parseFloat(s).toFixed(2).padStart(5, '0')}.png`);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
      console.log(file, `${Date.now() - t0}ms`);
    }
  }

  const video = opt('--video');
  if (video) {
    const from = Math.round(parseFloat(opt('--from', '0')) * FPS), to = Math.round(parseFloat(opt('--to', '60')) * FPS);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', path.resolve(__dirname, video)],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    const done = new Promise(r => ff.on('close', r));
    const t0 = Date.now();
    for (let f = from; f < to; f++) {
      const url = await page.evaluate(f => { renderFrame(f); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, f);
      const buf = Buffer.from(url.split(',')[1], 'base64');
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((f - from) % 48 === 0) console.log(`frame ${f}/${to}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end();
    await done;
    console.log('wrote', video, `${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  await browser.close();
})();
