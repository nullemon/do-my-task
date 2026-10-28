'use strict';
// Core math, color, drawing and post-processing helpers.

const W = 1080, H = 1920, FPS = 24, DUR = 60;
const TAU = Math.PI * 2, PI = Math.PI;
const EMS = 4; // emissive buffer downscale

const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
const sstep = (a, b, x) => { const t = inv(a, b, x); return t * t * (3 - 2 * t); };
const ease = {
  inOut: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  out: t => 1 - Math.pow(1 - t, 3),
  in: t => t * t * t,
  sine: t => -(Math.cos(PI * t) - 1) / 2,
  out2: t => 1 - (1 - t) * (1 - t),
  in2: t => t * t,
};

function hash1(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453123; return s - Math.floor(s); }
function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash1(i), hash1(i + 1), u) * 2 - 1; }
function fbm(x, o = 3) { let s = 0, a = 0.5, f = 1; for (let k = 0; k < o; k++) { s += a * noise1(x * f + k * 19.19); f *= 2; a *= 0.5; } return s; }
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6D2B79F5) >>> 0; let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hex(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function mixc(a, b, t) { return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]; }
function css(c, a = 1) { return `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${clamp(a)})`; }
function mkCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function lerpPts(A, B, t) { return A.map((p, i) => [lerp(p[0], B[i][0], t), lerp(p[1], B[i][1], t)]); }
function rot(p, a) { const c = Math.cos(a), s = Math.sin(a); return [p[0] * c - p[1] * s, p[0] * s + p[1] * c]; }
function add(a, b) { return [a[0] + b[0], a[1] + b[1]]; }
function sub(a, b) { return [a[0] - b[0], a[1] - b[1]]; }
function mirrorHalf(R) { // right-half outline (bottom center -> top center) to a closed symmetric outline
  const L = R.slice(1, -1).reverse().map(p => [-p[0], p[1]]);
  return R.concat(L);
}

// Catmull-Rom spline through points, as bezier segments.
function smoothPath(ctx, P, closed = true, k = 1 / 6) {
  const n = P.length;
  ctx.moveTo(P[0][0], P[0][1]);
  const last = closed ? n : n - 1;
  for (let i = 0; i < last; i++) {
    const p0 = P[closed ? (i - 1 + n) % n : Math.max(i - 1, 0)];
    const p1 = P[i], p2 = P[(i + 1) % n];
    const p3 = P[closed ? (i + 2) % n : Math.min(i + 2, n - 1)];
    ctx.bezierCurveTo(p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k,
      p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k, p2[0], p2[1]);
  }
  if (closed) ctx.closePath();
}
function polyPath(ctx, P) { ctx.moveTo(P[0][0], P[0][1]); for (let i = 1; i < P.length; i++) ctx.lineTo(P[i][0], P[i][1]); ctx.closePath(); }
function fillSmooth(ctx, P) { ctx.beginPath(); smoothPath(ctx, P); ctx.fill(); }
function fillPoly(ctx, P) { ctx.beginPath(); polyPath(ctx, P); ctx.fill(); }

function capsule(ctx, ax, ay, bx, by, ra, rb) {
  const dx = bx - ax, dy = by - ay, d = Math.hypot(dx, dy) || 1e-6, nx = -dy / d, ny = dx / d;
  ctx.beginPath();
  ctx.moveTo(ax + nx * ra, ay + ny * ra); ctx.lineTo(bx + nx * rb, by + ny * rb);
  ctx.lineTo(bx - nx * rb, by - ny * rb); ctx.lineTo(ax - nx * ra, ay - ny * ra); ctx.closePath();
  ctx.fill();
  ctx.beginPath(); ctx.arc(ax, ay, ra, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.arc(bx, by, rb, 0, TAU); ctx.fill();
}

// two-bone IK: joint position for a chain a->joint->b
function ik2(a, b, l1, l2, bend) {
  let dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy);
  const maxd = (l1 + l2) * 0.999, mind = Math.abs(l1 - l2) + 1e-3;
  if (d > maxd) { dx *= maxd / d; dy *= maxd / d; d = maxd; }
  if (d < mind) { dx *= mind / (d || 1); dy *= mind / (d || 1); d = mind; }
  const ang = Math.atan2(dy, dx);
  const al = Math.acos(clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1));
  const j = ang + bend * al;
  return { joint: [a[0] + Math.cos(j) * l1, a[1] + Math.sin(j) * l1], end: [a[0] + dx, a[1] + dy] };
}

// ---------- render targets (set by the compositor before each scene draws)
let X = null;   // scene context
let EX = null;  // emissive (bloom source) context, 1/EMS scale

function emit(fn) {
  if (!EX) return;
  const m = X.getTransform();
  EX.save();
  EX.setTransform(m.a / EMS, m.b / EMS, m.c / EMS, m.d / EMS, m.e / EMS, m.f / EMS);
  EX.globalCompositeOperation = 'lighter';
  fn(EX);
  EX.restore();
}

function radial(ctx, x, y, r, c, a, falloff = [1, 0.45, 0.12, 0]) {
  if (a <= 0.001 || r <= 0.5) return;
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, css(c, a * falloff[0]));
  g.addColorStop(0.22, css(c, a * falloff[1]));
  g.addColorStop(0.55, css(c, a * falloff[2]));
  g.addColorStop(1, css(c, a * falloff[3]));
  ctx.fillStyle = g;
  ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
}
function glowTo(ctx, x, y, r, c, a, sx = 1, sy = 1) {
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.translate(x, y); ctx.scale(sx, sy);
  radial(ctx, 0, 0, r, c, a);
  ctx.restore();
}
// light: visible glow + bloom contribution
function light(x, y, r, c, a = 1, bloom = 1, sx = 1, sy = 1) {
  glowTo(X, x, y, r, c, a, sx, sy);
  if (bloom > 0) emit(e => glowTo(e, x, y, r * 0.55, c, a * bloom, sx, sy));
}
// soft ambient pool (no bloom)
function pool(x, y, rx, ry, c, a) { glowTo(X, x, y, rx, c, a, 1, ry / rx); }

function vgrad(ctx, y0, y1, stops) {
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  for (const s of stops) g.addColorStop(s[0], css(s[1], s[2] ?? 1));
  return g;
}
function fillGrad(ctx, x0, y0, x1, y1, stops) {
  ctx.fillStyle = vgrad(ctx, y0, y1, stops);
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
}

// ---------- post FX
const GRAIN = [0, 1, 2, 3].map(k => {
  const c = mkCanvas(256, 256), g = c.getContext('2d'), d = g.createImageData(256, 256), r = rng(100 + k);
  for (let i = 0; i < d.data.length; i += 4) {
    const v = 128 + ((r() + r() + r()) / 3 - 0.5) * 2 * 120;
    d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255;
  }
  g.putImageData(d, 0, 0); return c;
});
function drawGrain(ctx, f, amt) {
  if (amt <= 0) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = amt;
  const p = ctx.createPattern(GRAIN[f % 4], 'repeat');
  const ox = Math.floor(hash1(f * 1.37) * 256), oy = Math.floor(hash1(f * 2.71) * 256);
  ctx.scale(1.6, 1.6); ctx.translate(-ox, -oy);
  ctx.fillStyle = p; ctx.fillRect(0, 0, W / 1.6 + 512, H / 1.6 + 512);
  ctx.restore();
}
function vignette(ctx, a = 0.55, cy = 0.5) {
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  const g = ctx.createRadialGradient(W / 2, H * cy, H * 0.22, W / 2, H * cy, H * 0.78);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(0.6, `rgba(0,0,0,${a * 0.35})`); g.addColorStop(1, `rgba(0,0,0,${a})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
}
function lightLeak(ctx, t, a) {
  if (a <= 0) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'screen';
  const blobs = [[0.9, 0.15, 900, [255, 150, 70]], [0.05, 0.75, 800, [255, 90, 60]], [0.7, 0.95, 700, [255, 200, 120]]];
  blobs.forEach((b, i) => {
    const x = W * (b[0] + 0.12 * noise1(t * 0.35 + i * 5)), y = H * (b[1] + 0.08 * noise1(t * 0.3 + i * 9));
    radial(ctx, x, y, b[2], b[3], a * (0.55 + 0.45 * noise1(t * 0.8 + i)), [0.6, 0.35, 0.1, 0]);
  });
  ctx.restore();
}
function lensFlare(ctx, lx, ly, a, tint = [255, 190, 120]) {
  if (a <= 0.01) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'lighter';
  const cx = W / 2, cy = H / 2, dx = cx - lx, dy = cy - ly;
  const ghosts = [[0.35, 40, 0.10, [255, 170, 90]], [0.62, 90, 0.06, [120, 200, 255]], [0.9, 26, 0.12, [255, 220, 160]],
    [1.25, 150, 0.045, [200, 120, 255]], [1.6, 60, 0.07, [255, 140, 80]], [2.0, 210, 0.035, [140, 255, 200]]];
  for (const g of ghosts) {
    const x = lx + dx * g[0], y = ly + dy * g[0];
    const gr = ctx.createRadialGradient(x, y, g[1] * 0.6, x, y, g[1]);
    gr.addColorStop(0, css(g[3], g[2] * a * 0.5)); gr.addColorStop(0.85, css(g[3], g[2] * a)); gr.addColorStop(1, css(g[3], 0));
    ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(x, y, g[1], 0, TAU); ctx.fill();
  }
  // anamorphic streak
  ctx.translate(lx, ly); ctx.scale(1, 0.018);
  radial(ctx, 0, 0, 1100, tint, a * 0.35, [1, 0.4, 0.1, 0]);
  ctx.restore();
}

// ---------- rain
const RAIN = (() => {
  const r = rng(7), B = [[], [], [], [], []];
  for (let i = 0; i < 1900; i++) {
    const z = r(), b = Math.min(4, Math.floor(z * 5));
    B[b].push({ x: r(), y: r(), v: 1300 + z * 2400, len: 14 + z * 120 });
  }
  return B;
})();
const RW = [0.6, 0.9, 1.3, 1.9, 2.7], RA = [0.07, 0.10, 0.13, 0.16, 0.19];
function rainPos(d, t, wind) {
  const span = H + 400;
  const y = ((d.y * span + d.v * t) % span) - 200;
  const x = ((d.x * (W + 600) + wind * (y + 200)) % (W + 600) + (W + 600)) % (W + 600) - 300;
  return [x, y];
}
function drawRain(ctx, t, amt, o = {}) {
  if (amt <= 0.002) return;
  const wind = o.wind ?? -0.12, col = o.col || [180, 196, 222], gain = o.gain ?? 1;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.lineCap = 'round';
  for (let b = 0; b < 5; b++) {
    const arr = RAIN[b], n = Math.floor(arr.length * clamp(amt));
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const d = arr[i], [x, y] = rainPos(d, t, wind);
      ctx.moveTo(x, y); ctx.lineTo(x - wind * d.len, y - d.len);
    }
    ctx.strokeStyle = css(col, RA[b] * gain); ctx.lineWidth = RW[b]; ctx.stroke();
  }
  if (o.lights) { // drops catching light
    ctx.globalCompositeOperation = 'lighter';
    for (const L of o.lights) {
      if (L.a <= 0.01) continue;
      for (let b = 1; b < 5; b++) {
        const arr = RAIN[b], n = Math.floor(arr.length * clamp(amt));
        ctx.lineWidth = RW[b] * 1.1;
        for (let i = 0; i < n; i++) {
          const d = arr[i], [x, y] = rainPos(d, t, wind);
          const dd = Math.hypot(x - L.x, (y - d.len / 2) - L.y) / L.r;
          if (dd >= 1) continue;
          const k = (1 - dd) * (1 - dd) * L.a;
          ctx.strokeStyle = css(L.c, k * 0.9);
          ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - wind * d.len, y - d.len); ctx.stroke();
        }
      }
    }
  }
  ctx.restore();
}
function drawSplashes(ctx, t, amt, y0, y1, o = {}) {
  if (amt <= 0.01) return;
  const n = Math.floor(140 * amt), col = o.col || [190, 205, 230];
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.strokeStyle = css(col, 1); ctx.lineWidth = 1.4;
  for (let k = 0; k < n; k++) {
    const rate = 2.0 + hash1(k * 3.1) * 1.6, c = t * rate + hash1(k * 7.7), id = Math.floor(c), ph = c - id;
    const hx = hash1(id * 13.1 + k * 0.77), hy = hash1(id * 5.3 + k * 1.91);
    const y = lerp(y0, y1, Math.pow(hy, 0.75)), sc = lerp(0.3, 1.4, (y - y0) / (y1 - y0 || 1));
    const x = o.xRange ? lerp(o.xRange[0], o.xRange[1], hx) : hx * W;
    if (o.mask && !o.mask(x, y)) continue;
    const r = (3 + ph * 20) * sc;
    ctx.globalAlpha = (1 - ph) * 0.32 * amt * (o.gain ?? 1);
    ctx.beginPath(); ctx.ellipse(x, y, r, r * 0.26, 0, 0, TAU); ctx.stroke();
    if (ph < 0.25) { ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + (hx - 0.5) * 6 * sc, y - (1 - ph * 4) * 10 * sc); ctx.stroke(); }
  }
  ctx.restore();
}

// drifting fog bank
function fogBand(ctx, t, y, h, c, a, speed = 12, seed = 0) {
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  for (let i = 0; i < 7; i++) {
    const s = seed * 10 + i;
    const span = W * 2.2;
    const x = ((hash1(s) * span + t * speed * (0.6 + hash1(s + 3))) % span) - W * 0.6;
    const yy = y + (hash1(s + 7) - 0.5) * h * 0.6;
    const rx = 420 + hash1(s + 11) * 380;
    ctx.save(); ctx.translate(x, yy); ctx.scale(1, h / rx);
    radial(ctx, 0, 0, rx, c, a * (0.6 + 0.4 * hash1(s + 13)), [0.8, 0.6, 0.25, 0]);
    ctx.restore();
  }
  ctx.restore();
}

// ---------- typography
function setFont(ctx, o) {
  ctx.font = `${o.italic ? 'italic ' : ''}${o.weight || 600} ${o.size}px ${o.family || 'Lora'}`;
}
// Caption: {t0,t1,y,size,italic,lines:[{segs:[[text,color?]], d}]}
function drawCaption(ctx, t, c) {
  const fin = 0.5, fout = 0.45;
  if (t < c.t0 - 0.01 || t > c.t1 + fout) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  setFont(ctx, c); ctx.textBaseline = 'middle';
  const lh = c.size * 1.32;
  const y0 = c.y - ((c.lines.length - 1) * lh) / 2;
  c.lines.forEach((ln, i) => {
    const st = c.t0 + (ln.d || 0);
    const a = ease.out(inv(st, st + fin, t)) * (1 - ease.in2(inv(c.t1, c.t1 + fout, t)));
    if (a <= 0.003) return;
    const segs = ln.segs;
    const widths = segs.map(s => ctx.measureText(s[0]).width);
    const total = widths.reduce((p, q) => p + q, 0);
    let x = W / 2 - total / 2;
    const rise = (1 - ease.out(inv(st, st + 0.9, t))) * 22;
    const blur = (1 - ease.out(inv(st, st + 0.6, t))) * 9;
    const y = y0 + i * lh + rise;
    if (c.scrim) {
      ctx.save(); ctx.globalAlpha = a * c.scrim;
      ctx.translate(W / 2, y); ctx.scale(1, 0.28);
      radial(ctx, 0, 0, total * 0.75 + 120, [0, 0, 0], 1, [0.9, 0.75, 0.35, 0]);
      ctx.restore();
    }
    ctx.globalAlpha = a;
    ctx.filter = blur > 0.3 ? `blur(${blur.toFixed(1)}px)` : 'none';
    ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 26; ctx.shadowOffsetY = 3;
    segs.forEach((s, k) => {
      ctx.fillStyle = s[1] || '#F6EFE2';
      ctx.fillText(s[0], x, y);
      x += widths[k];
    });
    ctx.filter = 'none';
  });
  ctx.restore();
}
