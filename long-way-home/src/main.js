'use strict';
// Compositor: scene list, transitions, bloom, grading, captions, title, grain.

const OUT_CV = document.getElementById('c');
const OUT = OUT_CV.getContext('2d');

function makeBuf() {
  const cv = mkCanvas(W, H), em = mkCanvas(W / EMS, H / EMS), b1 = mkCanvas(W / EMS, H / EMS), b2 = mkCanvas(W / EMS, H / EMS);
  return { cv, ctx: cv.getContext('2d'), em, ex: em.getContext('2d'), b1, b1x: b1.getContext('2d'), b2, b2x: b2.getContext('2d') };
}
const BUFS = [makeBuf(), makeBuf()];

//  t0: start, x: transition length into this scene, type: cross | black | flash
const SCENES = [
  { fn: S1, t0: 0, bloom: 1.0, grade: 'contrast(1.08) saturate(1.05)', grain: 0.12, vig: 0.6 },
  { fn: S2a, t0: 3.0, x: 0.5, type: 'flash', bloom: 0.9, grade: 'sepia(0.22) saturate(1.15) contrast(1.02) brightness(1.03)', grain: 0.16, vig: 0.62, leak: 0.35 },
  { fn: S2b, t0: 6.2, x: 0.6, type: 'cross', bloom: 0.9, grade: 'sepia(0.15) saturate(1.12) contrast(1.04)', grain: 0.15, vig: 0.55, leak: 0.3 },
  { fn: S3a, t0: 9.0, x: 0.7, type: 'black', bloom: 0.9, grade: 'contrast(1.08) saturate(1.05)', grain: 0.12, vig: 0.68 },
  { fn: S3b, t0: 12.4, x: 0.5, type: 'cross', bloom: 0.6, grade: 'contrast(1.06) saturate(1.05)', grain: 0.12, vig: 0.75 },
  { fn: S4, t0: 16.0, x: 0.6, type: 'cross', bloom: 1.0, grade: 'contrast(1.05) saturate(1.12)', grain: 0.11, vig: 0.5, leak: 0.12 },
  { fn: S5a, t0: 22.0, x: 0.35, type: 'cross', bloom: 0.9, grade: 'contrast(1.06) saturate(1.05)', grain: 0.12, vig: 0.58 },
  { fn: S5b, t0: 26.2, x: 0.3, type: 'cross', bloom: 0.9, grade: 'contrast(1.06)', grain: 0.12, vig: 0.58 },
  { fn: S6, t0: 30.0, x: 0.6, type: 'cross', bloom: 1.0, grade: 'contrast(1.08) saturate(1.05)', grain: 0.12, vig: 0.62 },
  { fn: S7, t0: 36.0, x: 0.8, type: 'cross', bloom: 1.0, grade: 'contrast(1.08)', grain: 0.13, vig: 0.62 },
  { fn: S8, t0: 43.0, x: 0.8, type: 'black', bloom: 1.0, grade: 'contrast(1.06) saturate(1.08)', grain: 0.12, vig: 0.62 },
  { fn: S10, t0: 52.0, x: 1.0, type: 'cross', bloom: 1.05, grade: 'contrast(1.05) saturate(1.12)', grain: 0.11, vig: 0.5, leak: 0.15 },
];

const GOLD = '#F2B46A';
const CAPTIONS = [
  { t0: 0.2, t1: 2.75, y: 690, size: 70, weight: 700, lines: [{ segs: [['They drove '], ['200 miles', GOLD]] }, { segs: [['to leave him here.']], d: 0.35 }] },
  { t0: 3.4, t1: 8.5, y: 470, size: 58, lines: [{ segs: [["Rusty had been Lily's dog"]] }, { segs: [['since the day she was born.']], d: 0.5 }], scrim: 0.35 },
  { t0: 9.5, t1: 12.2, y: 470, size: 60, lines: [{ segs: [['Then Dad lost his job.']] }] },
  { t0: 12.7, t1: 15.45, y: 400, size: 56, lines: [{ segs: [['The only place they could afford']] }, { segs: [['said: '], ['no dogs.', GOLD]], d: 0.6 }] },
  { t0: 16.7, t1: 21.6, y: 520, size: 62, lines: [{ segs: [['Rusty thought they were']] }, { segs: [['going to the '], ['lake.', GOLD]], d: 0.5 }], scrim: 0.45 },
  { t0: 33.9, t1: 35.5, y: 640, size: 60, lines: [{ segs: [['He brought the ball back.']] }, { segs: [['Like he always did.']], d: 0.85 }] },
  { t0: 37.6, t1: 42.6, y: 640, size: 64, lines: [{ segs: [['He waited all night.']] }] },
  { t0: 43.7, t1: 46.0, y: 330, size: 58, italic: true, weight: 500, lines: [{ segs: [['“He ran away, sweetheart.”']] }] },
  { t0: 46.4, t1: 49.9, y: 330, size: 58, italic: true, weight: 500, lines: [{ segs: [['“Then I’ll leave the light on…']] }, { segs: [['so he can find his way home.”']], d: 1.1 }] },
  { t0: 52.6, t1: 56.8, y: 500, size: 62, lines: [{ segs: [['Home was '], ['200 miles', GOLD], [' away.']] }, { segs: [['So Rusty started walking.']], d: 1.6 }], scrim: 0.3 },
];

function drawTitle(ctx, t) {
  const a = ease.out(inv(57.0, 57.9, t));
  if (a <= 0) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = a;
  ctx.fillStyle = vgrad(ctx, 250, 1050, [[0, [0, 0, 0], 0], [0.35, [6, 4, 10], 0.55], [0.7, [6, 4, 10], 0.5], [1, [0, 0, 0], 0]]);
  ctx.fillRect(0, 250, W, 800);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const sp = lerp(26, 9, ease.out(inv(57.0, 59.4, t)));
  ctx.shadowColor = 'rgba(255,170,90,0.55)'; ctx.shadowBlur = 40;
  ctx.fillStyle = '#F7E7CC';
  ctx.letterSpacing = `${sp}px`;
  ctx.font = '700 84px Cinzel'; ctx.fillText('THE LONG WAY', W / 2, 590);
  ctx.letterSpacing = `${sp * 1.6}px`;
  ctx.font = '700 168px Cinzel'; ctx.fillText('HOME', W / 2, 735);
  ctx.shadowBlur = 0;
  ctx.globalAlpha = a * 0.8; ctx.fillStyle = GOLD; ctx.fillRect(W / 2 - 150 * a, 846, 300 * a, 3);
  ctx.letterSpacing = '10px'; ctx.font = '600 30px Lora'; ctx.fillStyle = GOLD; ctx.globalAlpha = a; ctx.fillText('PART 1', W / 2, 470);
  const b = ease.out(inv(58.0, 58.8, t));
  ctx.globalAlpha = b; ctx.letterSpacing = '1px'; ctx.font = 'italic 500 46px Lora'; ctx.fillStyle = '#F6EFE2';
  ctx.shadowColor = 'rgba(0,0,0,0.8)'; ctx.shadowBlur = 20;
  ctx.fillText('Part 2 tomorrow', W / 2, 925 + (1 - b) * 14);
  ctx.restore();
}

function renderScene(buf, sc, t) {
  const c = buf.ctx;
  c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; c.filter = 'none';
  c.fillStyle = '#000'; c.fillRect(0, 0, W, H);
  buf.ex.setTransform(1, 0, 0, 1, 0, 0); buf.ex.clearRect(0, 0, W / EMS, H / EMS);
  X = c; EX = buf.ex;
  c.save(); sc.fn(t); c.restore();
  c.setTransform(1, 0, 0, 1, 0, 0);
  // bloom
  const s = sc.bloom ?? 1;
  buf.b1x.clearRect(0, 0, W / EMS, H / EMS); buf.b1x.filter = 'blur(2px)'; buf.b1x.drawImage(buf.em, 0, 0); buf.b1x.filter = 'none';
  buf.b2x.clearRect(0, 0, W / EMS, H / EMS); buf.b2x.filter = 'blur(9px)'; buf.b2x.drawImage(buf.em, 0, 0); buf.b2x.filter = 'none';
  c.save(); c.globalCompositeOperation = 'lighter';
  c.globalAlpha = clamp(0.85 * s); c.drawImage(buf.b1, 0, 0, W, H);
  c.globalAlpha = clamp(0.9 * s); c.drawImage(buf.b2, 0, 0, W, H);
  c.restore();
  X = null; EX = null;
}

function compose(sc, buf, alpha, t) {
  OUT.save(); OUT.globalAlpha = alpha; OUT.filter = sc.grade || 'none';
  OUT.drawImage(buf.cv, 0, 0); OUT.restore();
}

window.renderFrame = function (f) {
  const t = f / FPS;
  OUT.setTransform(1, 0, 0, 1, 0, 0); OUT.globalAlpha = 1; OUT.filter = 'none'; OUT.globalCompositeOperation = 'source-over';
  OUT.fillStyle = '#000'; OUT.fillRect(0, 0, W, H);
  // which scenes are visible
  let i = 0; while (i < SCENES.length - 1 && t >= SCENES[i + 1].t0) i++;
  let cur = SCENES[i], prev = null, next = null, a = 1;
  if (i > 0 && cur.x && t < cur.t0 + cur.x / 2) { prev = SCENES[i - 1]; a = inv(cur.t0 - cur.x / 2, cur.t0 + cur.x / 2, t); }
  else if (i < SCENES.length - 1 && SCENES[i + 1].x && t >= SCENES[i + 1].t0 - SCENES[i + 1].x / 2) { prev = cur; cur = SCENES[i + 1]; a = inv(cur.t0 - cur.x / 2, cur.t0 + cur.x / 2, t); }
  let mixGrain = cur.grain, mixVig = cur.vig, mixLeak = cur.leak || 0;
  if (prev) {
    const k = ease.sine(a);
    if (cur.type === 'black') {
      if (k < 0.5) { renderScene(BUFS[0], prev, t); compose(prev, BUFS[0], 1 - k * 2, t); }
      else { renderScene(BUFS[0], cur, t); compose(cur, BUFS[0], k * 2 - 1, t); }
    } else {
      renderScene(BUFS[0], prev, t); renderScene(BUFS[1], cur, t);
      compose(prev, BUFS[0], 1, t); compose(cur, BUFS[1], k, t);
      if (cur.type === 'flash') {
        OUT.save(); OUT.globalCompositeOperation = 'screen'; OUT.fillStyle = css([255, 226, 180], (1 - Math.abs(2 * k - 1)) * 0.85); OUT.fillRect(0, 0, W, H); OUT.restore();
      }
    }
    mixGrain = lerp(prev.grain, cur.grain, k); mixVig = lerp(prev.vig, cur.vig, k); mixLeak = lerp(prev.leak || 0, cur.leak || 0, k);
  } else {
    renderScene(BUFS[0], cur, t); compose(cur, BUFS[0], 1, t);
  }
  lightLeak(OUT, t, mixLeak);
  vignette(OUT, mixVig);
  for (const c of CAPTIONS) drawCaption(OUT, t, c);
  drawTitle(OUT, t);
  drawGrain(OUT, f, mixGrain);
  // fade in from black at the very start, gentle settle at the end
  const fin = 1 - inv(0, 0.18, t);
  if (fin > 0) { OUT.fillStyle = `rgba(0,0,0,${fin})`; OUT.fillRect(0, 0, W, H); }
};

window.READY = (async () => {
  await Promise.all(['700 40px Cinzel', '600 40px Lora', 'italic 500 40px Lora', '700 40px Lora', '500 20px Lora'].map(f => document.fonts.load(f)));
  await document.fonts.ready;
  return true;
})();
