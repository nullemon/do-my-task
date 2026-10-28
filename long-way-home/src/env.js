'use strict';
// Environment pieces: skies, clouds, terrain, trees, grass, roads, the gas station, the house.

function sky(stops, y0 = -400, y1 = H + 200) { fillGrad(X, -W, y0, 2 * W, y1, stops); }

function stars(t, a, seed = 3, n = 160, y1 = H * 0.5) {
  if (a <= 0) return;
  const r = rng(seed);
  X.save(); X.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) {
    const x = r() * W, y = Math.pow(r(), 1.4) * y1, s = 0.6 + r() * 1.6, tw = 0.6 + 0.4 * Math.sin(t * (1 + r() * 3) + i);
    X.fillStyle = css([220, 230, 255], a * tw * (0.3 + r() * 0.7));
    X.fillRect(x, y, s, s);
  }
  X.restore();
}

function sun(x, y, r, c, a = 1) {
  light(x, y, r * 9, c, 0.35 * a, 0.8);
  light(x, y, r * 3.2, mixc(c, [255, 255, 230], 0.4), 0.6 * a, 1.2);
  X.save(); X.fillStyle = css(mixc(c, [255, 252, 235], 0.75), a); X.beginPath(); X.arc(x, y, r, 0, TAU); X.fill(); X.restore();
  emit(e => { e.fillStyle = css([255, 245, 220], a); e.beginPath(); e.arc(x, y, r * 1.1, 0, TAU); e.fill(); });
}

// soft cloud mass made from shaded puffs
function cloud(cx, cy, w, h, top, bot, a, seed, t = 0, drift = 0) {
  const r = rng(seed);
  const n = 9;
  for (let i = 0; i < n; i++) {
    const px = cx + (r() - 0.5) * w + t * drift, py = cy + (r() - 0.5) * h * 0.5;
    const pr = (0.25 + r() * 0.35) * w * 0.5;
    const g = X.createRadialGradient(px, py - pr * 0.35, pr * 0.1, px, py, pr);
    g.addColorStop(0, css(top, a)); g.addColorStop(0.6, css(mixc(top, bot, 0.6), a * 0.8)); g.addColorStop(1, css(bot, 0));
    X.fillStyle = g; X.save(); X.translate(px, py); X.scale(1, h / w * 1.6); X.translate(-px, -py);
    X.beginPath(); X.arc(px, py, pr, 0, TAU); X.fill(); X.restore();
  }
}
// long thin sunset cloud streak
function streak(cx, cy, len, th, c, a) {
  X.save(); X.translate(cx, cy); X.scale(1, th / len);
  radial(X, 0, 0, len, c, a, [0.9, 0.7, 0.3, 0]);
  X.restore();
}

function ridge(y, amp, freq, seed, col, x0 = -200, x1 = W + 200, bottom = H + 200, off = 0, oct = 4) {
  X.fillStyle = typeof col === 'string' || col instanceof CanvasGradient ? col : css(col);
  X.beginPath(); X.moveTo(x0, bottom);
  for (let x = x0; x <= x1; x += 8) {
    const v = fbm((x + off) * freq + seed * 13.7, oct);
    X.lineTo(x, y - amp * (v * 0.5 + 0.5));
  }
  X.lineTo(x1, bottom); X.closePath(); X.fill();
}

function pine(ctx, x, y, h, w) {
  ctx.beginPath(); ctx.moveTo(x, y - h);
  const tiers = 5;
  for (let i = 1; i <= tiers; i++) { const ty = y - h + (h * 0.85) * (i / tiers); const tw = w * (0.3 + 0.7 * i / tiers); ctx.lineTo(x + tw / 2, ty); ctx.lineTo(x + tw * 0.18, ty - h * 0.06); }
  for (let i = tiers; i >= 1; i--) { const ty = y - h + (h * 0.85) * (i / tiers); const tw = w * (0.3 + 0.7 * i / tiers); ctx.lineTo(x - tw * 0.18, ty - h * 0.06); ctx.lineTo(x - tw / 2, ty); }
  ctx.closePath(); ctx.fill();
  ctx.fillRect(x - w * 0.04, y - h * 0.16, w * 0.08, h * 0.16);
}
function oak(ctx, x, y, h, seed) {
  const r = rng(seed);
  ctx.fillRect(x - h * 0.03, y - h * 0.5, h * 0.06, h * 0.5);
  for (let i = 0; i < 9; i++) {
    const a = r() * TAU, d = r() * h * 0.22;
    ctx.beginPath(); ctx.arc(x + Math.cos(a) * d * 1.3, y - h * 0.66 + Math.sin(a) * d * 0.8, h * (0.14 + r() * 0.1), 0, TAU); ctx.fill();
  }
}
function treeLine(y, seed, hmin, hmax, step, col, x0 = -100, x1 = W + 100, mixOak = 0.35) {
  const r = rng(seed);
  X.fillStyle = css(col);
  for (let x = x0; x < x1; x += step * (0.5 + r())) {
    const h = lerp(hmin, hmax, r());
    if (r() < mixOak) oak(X, x, y, h, seed * 100 + x); else pine(X, x, y, h, h * 0.42);
  }
  X.fillRect(x0, y - 2, x1 - x0, H);
}

// grass blades along a horizon line
function grass(y, x0, x1, t, o = {}) {
  const r = rng(o.seed || 5), col = o.col || INK, hh = o.h || 40, dens = o.dens || 3, wind = o.wind ?? 1;
  X.fillStyle = css(col, o.a ?? 1);
  X.beginPath();
  for (let x = x0; x < x1; x += dens) {
    const h = hh * (0.4 + r() * 0.9), lean = (r() - 0.5) * 0.5 + wind * 0.25 * noise1(x * 0.01 + t * 1.3) + wind * 0.08 * Math.sin(t * 2 + x * 0.05);
    const w = 1.2 + r() * 2.2;
    const tx = x + lean * h, ty = y - h;
    X.moveTo(x - w, y); X.quadraticCurveTo(x + lean * h * 0.4, y - h * 0.6, tx, ty); X.quadraticCurveTo(x + lean * h * 0.4 + w * 0.5, y - h * 0.5, x + w, y);
  }
  X.fill();
}

function pole(x, y, h, s, col) {
  X.fillStyle = css(col);
  X.fillRect(x - 3 * s, y - h, 6 * s, h);
  X.fillRect(x - 34 * s, y - h + 14 * s, 68 * s, 5 * s);
  for (const dx of [-28, -10, 10, 28]) X.fillRect(x + dx * s - 1.5 * s, y - h + 6 * s, 3 * s, 9 * s);
}
function wire(x0, y0, x1, y1, sag, col, w) {
  X.strokeStyle = css(col); X.lineWidth = w;
  X.beginPath(); X.moveTo(x0, y0); X.quadraticCurveTo((x0 + x1) / 2, (y0 + y1) / 2 + sag, x1, y1); X.stroke();
}

function birds(t, list, col = INK) {
  X.save(); X.strokeStyle = css(col); X.lineCap = 'round';
  for (const b of list) {
    const x = b.x + b.vx * t, y = b.y + b.vy * t + Math.sin(t * 1.3 + b.p) * 6;
    const f = Math.sin(t * b.f + b.p), s = b.s;
    X.lineWidth = Math.max(1, s * 0.18);
    X.beginPath(); X.moveTo(x - s, y - f * s * 0.5); X.quadraticCurveTo(x - s * 0.4, y - s * 0.2, x, y); X.quadraticCurveTo(x + s * 0.4, y - s * 0.2, x + s, y - f * s * 0.5); X.stroke();
  }
  X.restore();
}

// one-point perspective road: vp = vanishing point, yb = bottom y, half widths at bottom
function road(vp, yb, xl, xr, col, o = {}) {
  X.fillStyle = typeof col === 'object' && !Array.isArray(col) ? col : css(col);
  X.beginPath(); X.moveTo(vp[0], vp[1]); X.lineTo(xr, yb); X.lineTo(xl, yb); X.closePath(); X.fill();
  const lc = o.lineCol || [210, 200, 170], la = o.lineA ?? 0.5;
  // edge lines
  X.strokeStyle = css(lc, la * 0.55);
  for (const ex of [xl, xr]) {
    const ix = lerp(ex, vp[0], 0.05);
    X.lineWidth = 6; X.beginPath(); X.moveTo(vp[0], vp[1]); X.lineTo(ix, yb); X.stroke();
  }
  // dashed center line
  const cxb = (xl + xr) / 2, K = yb - vp[1];
  X.fillStyle = css(o.dashCol || [230, 200, 110], la);
  for (let i = 0; i < 40; i++) {
    const d0 = 1 + i * 0.9 + (o.dashOff || 0), d1 = d0 + 0.42;
    const y0 = vp[1] + K / d0, y1 = vp[1] + K / d1;
    if (y0 < vp[1] + 2) break;
    const w0 = 9 / d0, w1 = 9 / d1;
    const x0 = lerp(vp[0], cxb, (y0 - vp[1]) / K), x1 = lerp(vp[0], cxb, (y1 - vp[1]) / K);
    X.beginPath(); X.moveTo(x0 - w0, y0); X.lineTo(x0 + w0, y0); X.lineTo(x1 + w1, y1); X.lineTo(x1 - w1, y1); X.closePath(); X.fill();
  }
}
// reflection of a light on wet ground
function wetReflect(x, y, gy, c, a, len = 1) {
  const ry = gy + (gy - y) * 0.6;
  glowTo(X, x, Math.max(ry, gy + 4), 70, c, a * 0.5, 0.45, 3.2 * len);
  emit(e => glowTo(e, x, Math.max(ry, gy + 4), 40, c, a * 0.3, 0.45, 3.2 * len));
}

// gas station, frontal elevation. x = canopy center, y = ground, s = px per meter
function gasStation(o) {
  const { x, y, s } = o, col = o.col || INK, L = o.lights || {}, wet = o.wet ?? 0;
  const P = (mx, my) => [x + mx * s, y + my * s];
  const canopyA = L.canopy ?? 0, storeA = L.store ?? 0, signA = L.sign ?? 0;
  // ground light pools
  if (canopyA > 0) {
    pool(x, y + 0.2 * s, 8 * s, 1.6 * s, [170, 215, 255], 0.30 * canopyA);
    pool(x, y + 0.1 * s, 4.5 * s, 0.8 * s, [210, 235, 255], 0.30 * canopyA);
  }
  if (storeA > 0 && o.store !== false) pool(x + 10 * s, y + 0.3 * s, 5 * s, 1.0 * s, [255, 190, 120], 0.25 * storeA);
  // structure silhouette
  silhouette(ctx => {
    ctx.fillRect(...P(-6.2, -5.4), 12.4 * s, 0.85 * s);         // canopy fascia
    for (const px of [-3.8, 3.8]) ctx.fillRect(...P(px - 0.22, -4.6), 0.44 * s, 4.6 * s); // pillars
    for (const px of [-2.2, 1.6]) { ctx.beginPath(); ctx.roundRect(...P(px - 0.45, -1.75), 0.9 * s, 1.75 * s, 0.08 * s); ctx.fill(); }
    ctx.fillRect(...P(-2.9, -0.18), 5.8 * s, 0.18 * s); // island
    if (o.store !== false) {
      ctx.fillRect(...P(7.2, -3.7), 7.5 * s, 3.7 * s);
      ctx.fillRect(...P(7.0, -3.95), 7.9 * s, 0.3 * s);
    }
    // sign pole
    ctx.fillRect(...P(-9.15, -8.6), 0.3 * s, 8.6 * s);
    ctx.fillRect(...P(-10.7, -10.7), 3.4 * s, 2.5 * s);
  }, { col, rim: o.rim });
  // canopy underside light strips
  if (canopyA > 0) {
    X.fillStyle = css([225, 245, 255], 0.95 * canopyA);
    for (const px of [-4.6, -0.8, 3.0]) X.fillRect(...P(px, -4.62), 1.6 * s, 0.09 * s);
    for (const px of [-3.8, 0.0, 3.8]) light(...P(px, -4.55), 3.2 * s, [190, 225, 255], 0.38 * canopyA, 1);
    // fascia trim
    X.fillStyle = css([140, 30, 30], 0.6 * canopyA); X.fillRect(...P(-6.2, -4.75), 12.4 * s, 0.12 * s);
    if (wet > 0) for (const px of [-3.8, 0, 3.8]) wetReflect(...P(px, -4.55), y, [190, 225, 255], 0.35 * canopyA * wet, 0.8);
    // pump screens
    for (const px of [-2.2, 1.6]) { X.fillStyle = css([255, 200, 110], 0.8 * canopyA); X.fillRect(...P(px - 0.22, -1.45), 0.44 * s, 0.25 * s); light(...P(px, -1.32), 0.8 * s, [255, 190, 100], 0.35 * canopyA, 0.6); }
  }
  // store window
  if (storeA > 0 && o.store !== false) {
    X.fillStyle = css([255, 196, 128], 0.85 * storeA); X.fillRect(...P(8.0, -2.7), 4.3 * s, 1.8 * s);
    X.fillStyle = css(INK, 0.8); for (let i = 1; i < 4; i++) X.fillRect(...P(8.0 + i * 1.075 - 0.04, -2.7), 0.08 * s, 1.8 * s);
    X.fillStyle = css([255, 210, 150], 0.7 * storeA); X.fillRect(...P(12.8, -2.5), 1.0 * s, 2.5 * s);
    light(...P(10.2, -1.8), 4 * s, [255, 180, 110], 0.3 * storeA, 0.8);
    if (wet > 0) wetReflect(...P(10.2, -1.8), y, [255, 180, 110], 0.4 * storeA * wet, 1);
  }
  // sign panel
  if (signA >= 0) {
    const f = signA;
    const [sx, sy] = P(-10.55, -10.55);
    X.fillStyle = css([20, 14, 14], 1); X.fillRect(sx, sy, 3.1 * s, 2.2 * s);
    X.save();
    X.font = `700 ${1.05 * s}px Cinzel`; X.textAlign = 'center'; X.textBaseline = 'middle';
    X.fillStyle = css(mixc([60, 20, 20], [255, 70, 60], f), 1); X.fillText('GAS', ...P(-9.0, -9.95));
    X.font = `700 ${0.75 * s}px Lora`; X.fillStyle = css(mixc([50, 40, 20], [255, 190, 90], f), 1); X.fillText('3.49', ...P(-9.0, -8.95));
    X.restore();
    if (f > 0) {
      emit(e => { e.font = `700 ${1.05 * s}px Cinzel`; e.textAlign = 'center'; e.textBaseline = 'middle'; e.fillStyle = css([255, 70, 60], f); e.fillText('GAS', ...P(-9.0, -9.95)); e.font = `700 ${0.75 * s}px Lora`; e.fillStyle = css([255, 190, 90], f); e.fillText('3.49', ...P(-9.0, -8.95)); });
      light(...P(-9.0, -9.6), 5.5 * s, [255, 70, 50], 0.28 * f, 0.6);
      if (wet > 0) wetReflect(...P(-9.0, -9.6), y, [255, 80, 60], 0.45 * f * wet, 1.3);
    }
  }
  return { sign: P(-9.0, -9.6), canopy: P(0, -4.6), store: P(10.2, -1.8) };
}
