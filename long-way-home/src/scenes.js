'use strict';
// The eleven shots of Episode 1. Each scene draws itself for absolute time t (seconds).

const toScreen = (x, y) => { const m = X.getTransform(); return [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f]; };
function zoomAt(sc, cx, cy, dx = 0, dy = 0) { X.setTransform(sc, 0, 0, sc, cx - sc * cx + dx, cy - sc * cy + dy); }

function dogHeadOnly(ctx, P) {
  ctx.save(); ctx.translate(P.x, P.y); ctx.scale(P.s * (P.face || 1), P.s); ctx.rotate(P.head || 0);
  capsule(ctx, -0.06, 0.05, -0.36, 0.34, 0.15, 0.21);
  const jaw = P.jaw || 0, pv = [0.02, 0.075];
  const jp = JAW.map(p => add(pv, rot(sub(p, pv), jaw)));
  ctx.beginPath(); smoothPath(ctx, HEAD_TOP.concat(jp, HEAD_BOT), true, 1 / 7); ctx.fill();
  if (P.tongue) { const tp = TONGUE.map(p => add(pv, rot(sub(p, pv), jaw * 0.8))); ctx.beginPath(); smoothPath(ctx, tp); ctx.fill(); }
  const ep = [-0.05, -0.10], es = P.earStretch || 1;
  ctx.beginPath(); smoothPath(ctx, EAR.map(p => add(ep, rot([p[0] / Math.sqrt(es), p[1] * es], P.ear || 0)))); ctx.fill();
  ctx.restore();
}

function moonAndWisps(mx, my, r, a = 1, t = 0) {
  light(mx, my, r * 7, [190, 205, 255], 0.16 * a, 0.5);
  light(mx, my, r * 2.2, [220, 228, 255], 0.35 * a, 0.9);
  X.save();
  const g = X.createRadialGradient(mx - r * 0.3, my - r * 0.3, r * 0.1, mx, my, r);
  g.addColorStop(0, css([248, 246, 236], a)); g.addColorStop(1, css([214, 216, 228], a));
  X.fillStyle = g; X.beginPath(); X.arc(mx, my, r, 0, TAU); X.fill();
  X.fillStyle = css([170, 172, 190], 0.35 * a);
  for (const [dx, dy, rr] of [[-0.3, -0.2, 0.22], [0.25, 0.1, 0.18], [-0.05, 0.35, 0.14], [0.35, -0.35, 0.1]]) { X.beginPath(); X.arc(mx + dx * r, my + dy * r, rr * r, 0, TAU); X.fill(); }
  X.restore();
  for (let i = 0; i < 5; i++) streak(mx - 420 + i * 210 + t * 4, my + 120 + i * 70 + hash1(i) * 60, 260 + hash1(i * 3) * 220, 10 + hash1(i) * 10, [120, 130, 180], 0.2 * a);
}

function stormClouds(t, a, drift, seed = 40, y0 = 120, y1 = 820, top = [34, 42, 58], bot = [8, 11, 20]) {
  for (let i = 0; i < 7; i++) {
    const cx = ((hash1(seed + i) * 1600 + t * drift * (0.6 + hash1(seed + i + 9))) % 1800) - 360;
    const cy = lerp(y0, y1, hash1(seed + i + 3));
    cloud(cx, cy, 520 + hash1(seed + i + 5) * 500, 160 + hash1(seed + i + 7) * 140, top, bot, a, seed * 10 + i);
  }
}

function lightningBolt(seed, x0, y0, y1, a) {
  if (a <= 0.01) return;
  const r = rng(seed);
  const pts = [[x0, y0]];
  let x = x0, y = y0;
  while (y < y1) { y += 30 + r() * 50; x += (r() - 0.5) * 70; pts.push([x, y]); }
  X.save(); X.globalCompositeOperation = 'lighter'; X.lineJoin = 'round';
  for (const [w, al] of [[14, 0.12], [6, 0.35], [2.5, 1]]) {
    X.strokeStyle = css([210, 225, 255], al * a); X.lineWidth = w;
    X.beginPath(); pts.forEach((p, i) => (i ? X.lineTo(p[0], p[1]) : X.moveTo(p[0], p[1]))); X.stroke();
  }
  X.restore();
  emit(e => { e.strokeStyle = css([200, 220, 255], a); e.lineWidth = 8; e.beginPath(); pts.forEach((p, i) => (i ? e.lineTo(p[0], p[1]) : e.moveTo(p[0], p[1]))); e.stroke(); });
}

// ======================= S1: night, rain, taillights (0-3s)
function S1(t) {
  const sc = lerp(1.0, 1.07, ease.sine(inv(0, 3.4, t)));
  const VP = [600, 1032];
  zoomAt(lerp(1, sc, 0.3), 540, 1150);
  sky([[0, [3, 5, 10]], [0.45, [8, 13, 24]], [0.78, [22, 30, 44]], [0.86, [48, 42, 48]], [1, [20, 22, 28]]], -300, 1250);
  stormClouds(t, 0.6, 7);
  pool(820, 1034, 520, 70, [150, 95, 70], 0.28);
  for (let i = 0; i < 9; i++) { const x = 700 + hash1(i * 3) * 330; light(x, 1029 - hash1(i) * 4, 9 + hash1(i + 1) * 8, [255, 190, 120], 0.6, 0.5); }
  zoomAt(lerp(1, sc, 0.6), 540, 1150);
  treeLine(1038, 12, 12, 38, 20, [9, 11, 17]);
  zoomAt(sc, 540, 1150);
  X.fillStyle = css([8, 10, 14]); X.fillRect(-300, 1032, W + 600, 1100);
  road(VP, 1940, -700, 700, vgrad(X, 1032, 1940, [[0, [44, 46, 58]], [0.25, [22, 25, 33]], [1, [11, 13, 18]]]), { lineA: 0.22 });
  fogBand(X, t, 1050, 50, [60, 70, 90], 0.25, 10, 1);
  const gs = gasStation({ x: 360, y: 1150, s: 26, lights: { canopy: 1, store: 0, sign: 0.75 + 0.25 * noise1(t * 9) - (hash1(Math.floor(t * 12)) > 0.9 ? 0.6 : 0) }, wet: 1, rim: { c: [120, 150, 200], a: 0.35, dx: 2, dy: -2 } });
  // receding car
  const d = lerp(5, 75, Math.pow(inv(-0.2, 3.0, t), 1.7));
  const cy = VP[1] + 908 / d, cx = lerp(VP[0], 350, (cy - VP[1]) / 908), ppm = 335 / d;
  const tail = 1 - sstep(2.3, 3.0, t) * 0.7;
  carRear(cx, cy, ppm, tail, 0.95);
  for (const sx of [-0.8, 0.8]) wetReflect(cx + sx * ppm, cy - 0.85 * ppm, cy, [255, 50, 35], 0.9 * tail, 1.4);
  // the dog, back view, watching
  const P = { x: 790, y: 1730, s: 245, sit: 1, t, turn: -0.32 - sstep(1.0, 1.8, t) * 0.12, tilt: 0.03 * Math.sin(t * 1.3) + sstep(1.2, 2.2, t) * 0.07, perk: sstep(0.6, 1.4, t) * 0.7 - sstep(2.2, 3, t) * 0.5 };
  silhouette(ctx => dogBack(ctx, P), { rim: { c: [255, 110, 85], a: 0.8, dx: -3, dy: -1.5, bloom: 0.5 } });
  silhouette(ctx => dogBack(ctx, P), { col: INK, alpha: 0, rim: { c: [150, 190, 255], a: 0.35, dx: 2, dy: -2 } });
  drawBall(640, 1716, 15, 0.6, 0.2);
  // rain
  const sg = toScreen(...gs.sign), cg = toScreen(...gs.canopy);
  drawRain(X, t, 0.85, { wind: -0.1, lights: [{ x: sg[0], y: sg[1], r: 260, c: [255, 90, 70], a: 0.7 }, { x: cg[0], y: cg[1] + 40, r: 300, c: [190, 220, 255], a: 0.6 }] });
  drawSplashes(X, t, 0.9, 1180, 1920);
}

// ======================= S2a: nursery flashback (3-6.4s)
function S2a(t) {
  const sc = lerp(1.07, 1.0, ease.sine(inv(2.6, 6.8, t)));
  zoomAt(sc, 540, 1150);
  fillGrad(X, -200, -200, W + 200, H + 200, [[0, [40, 26, 22]], [0.5, [72, 46, 32]], [1, [28, 18, 14]]]);
  // window
  const wx0 = 640, wx1 = 1000, wy0 = 560, wy1 = 1200;
  fillGrad(X, wx0, wy0, wx1, wy1, [[0, [255, 240, 200]], [1, [255, 194, 120]]]);
  light((wx0 + wx1) / 2, (wy0 + wy1) / 2, 620, [255, 196, 120], 0.38, 1.2);
  X.fillStyle = css(INK, 0.95);
  X.fillRect(wx0 - 18, wy0 - 18, wx1 - wx0 + 36, 20); X.fillRect(wx0 - 18, wy1, wx1 - wx0 + 36, 26);
  X.fillRect(wx0 - 18, wy0, 20, wy1 - wy0); X.fillRect(wx1 - 2, wy0, 20, wy1 - wy0);
  X.fillRect((wx0 + wx1) / 2 - 6, wy0, 12, wy1 - wy0); X.fillRect(wx0, (wy0 + wy1) / 2 - 6, wx1 - wx0, 12);
  // curtains
  for (const [cx, dir] of [[wx0 - 30, -1], [wx1 + 30, 1]]) {
    const sw = 10 * noise1(t * 0.6 + cx);
    X.fillStyle = css([20, 12, 10], 0.92);
    X.beginPath(); X.moveTo(cx - 70 * dir, 520);
    X.bezierCurveTo(cx + 40 * dir + sw, 800, cx - 20 * dir + sw, 1050, cx + 30 * dir + sw * 1.5, 1290);
    X.lineTo(cx + 130 * dir, 1290); X.lineTo(cx + 120 * dir, 520); X.closePath(); X.fill();
  }
  X.fillRect(wx0 - 140, 512, wx1 - wx0 + 280, 12);
  // floor
  fillGrad(X, -200, 1520, W + 200, H + 300, [[0, [44, 28, 18]], [1, [16, 10, 8]]]);
  pool(640, 1600, 480, 90, [255, 190, 120], 0.35);
  // crib
  const x0 = 120, x1 = 620;
  silhouette(ctx => {
    ctx.beginPath(); smoothPath(ctx, [[220, 1362], [250, 1300], [330, 1262], [440, 1250], [560, 1300], [600, 1362]]); ctx.fill(); // blanket
    ctx.beginPath(); ctx.ellipse(205, 1312, 40, 36, 0, 0, TAU); ctx.fill(); // baby head
    ctx.beginPath(); ctx.ellipse(205, 1350, 70, 20, 0, 0, TAU); ctx.fill();
    ctx.fillRect(x0, 1040, 30, 490); ctx.fillRect(x1 - 30, 1040, 30, 490);
    ctx.fillRect(x0, 1086, x1 - x0, 22); ctx.fillRect(x0, 1356, x1 - x0, 26);
    for (let x = x0 + 40; x < x1 - 30; x += 34) ctx.fillRect(x, 1104, 9, 254);
    // mobile arm
    ctx.fillRect(x0 + 10, 800, 10, 260); ctx.fillRect(x0 + 10, 800, 300, 9);
  }, { rim: { c: [255, 200, 140], a: 0.7, dx: 2.5, dy: -1, bloom: 0.3 } });
  // mobile ornaments
  X.save();
  for (let i = 0; i < 5; i++) {
    const ang = t * 0.9 + i * TAU / 5, depth = 0.75 + 0.25 * Math.sin(ang);
    const ox = 330 + Math.cos(ang) * 110, len = 70 + (i % 3) * 30, oy = 809 + len;
    X.strokeStyle = css([30, 20, 16], 0.7); X.lineWidth = 1.5; X.beginPath(); X.moveTo(330 + Math.cos(ang) * 60, 809); X.lineTo(ox, oy); X.stroke();
    X.fillStyle = css(INK);
    X.save(); X.translate(ox, oy + 12); X.scale(depth, 1);
    if (i === 2) { X.beginPath(); X.arc(0, 0, 18, 0, TAU); X.fill(); X.globalCompositeOperation = 'destination-out'; X.beginPath(); X.arc(8, -5, 15, 0, TAU); X.fill(); }
    else { X.beginPath(); for (let k = 0; k < 10; k++) { const rr = k % 2 ? 7 : 17, a = -PI / 2 + k * PI / 5; X.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); } X.closePath(); X.fill(); }
    X.restore();
  }
  X.restore();
  // rug + puppy
  pool(820, 1566, 260, 46, [140, 70, 40], 0.5);
  silhouette(ctx => puppyCurled(ctx, 820, 1566, 160, Math.sin(t * 2.4)), { rim: { c: [255, 205, 150], a: 0.85, dx: 2.5, dy: -2, bloom: 0.4 } });
  // god rays
  X.save(); X.globalCompositeOperation = 'lighter';
  for (let k = 0; k < 6; k++) {
    const ya = lerp(wy0 + 40, wy1 - 60, k / 5), xa = lerp(wx0, wx1, hash1(k + 4) * 0.4);
    const dir = [-0.62, 0.78], len = 1500, w0 = 40 + hash1(k) * 50, w1 = w0 * 3.2;
    const n = [-dir[1], dir[0]];
    const a = (0.06 + 0.05 * hash1(k * 2)) * (0.75 + 0.25 * noise1(t * 0.7 + k));
    const g = X.createLinearGradient(xa, ya, xa + dir[0] * len, ya + dir[1] * len);
    g.addColorStop(0, css([255, 214, 150], a)); g.addColorStop(1, css([255, 214, 150], 0));
    X.fillStyle = g;
    X.beginPath(); X.moveTo(xa + n[0] * w0, ya + n[1] * w0); X.lineTo(xa - n[0] * w0, ya - n[1] * w0);
    X.lineTo(xa + dir[0] * len - n[0] * w1, ya + dir[1] * len - n[1] * w1); X.lineTo(xa + dir[0] * len + n[0] * w1, ya + dir[1] * len + n[1] * w1); X.fill();
  }
  // dust motes
  for (let i = 0; i < 70; i++) {
    const px = 300 + hash1(i * 7) * 700 + 30 * noise1(t * 0.2 + i), py = 600 + hash1(i * 3) * 900 + 40 * noise1(t * 0.15 + i * 2) - t * 6;
    const a = 0.5 * (0.5 + 0.5 * Math.sin(t * 2 + i)) * (hash1(i) > 0.4 ? 1 : 0.4);
    X.fillStyle = css([255, 225, 180], a); X.beginPath(); X.arc(px, py, 1.2 + hash1(i * 5) * 2, 0, TAU); X.fill();
  }
  X.restore();
}

// ======================= S2b: walking Lily to the school bus (6.2-9.2s)
function houseSil(x, y, w, h, roof, col, seed, winA = 0) {
  X.fillStyle = css(col);
  X.fillRect(x, y - h, w, h);
  X.beginPath(); X.moveTo(x - 20, y - h); X.lineTo(x + w / 2, y - h - roof); X.lineTo(x + w + 20, y - h); X.closePath(); X.fill();
  X.fillRect(x + w * 0.72, y - h - roof * 0.9, w * 0.09, roof * 0.6);
  if (winA > 0) {
    X.fillStyle = css([255, 200, 140], winA);
    X.fillRect(x + w * 0.18, y - h * 0.62, w * 0.18, h * 0.24); X.fillRect(x + w * 0.62, y - h * 0.62, w * 0.18, h * 0.24);
  }
}
function S2b(t) {
  const lt = t - 6.2;
  zoomAt(1, 540, 960);
  sky([[0, [92, 120, 165]], [0.45, [186, 166, 168]], [0.66, [250, 198, 150]], [0.76, [255, 222, 175]], [1, [255, 214, 160]]], -100, 1500);
  const sunP = [890 - lt * 4, 1235];
  sun(sunP[0], sunP[1], 52, [255, 214, 150], 1);
  for (let i = 0; i < 4; i++) streak(200 + i * 260 - lt * 6, 520 + i * 90, 380, 22, [255, 210, 180], 0.25);
  // far trees
  X.save(); X.translate(-lt * 10, 0); treeLine(1340, 21, 80, 190, 38, [178, 128, 116], -100, W + 200); X.restore();
  // mid houses
  X.save(); X.translate(-lt * 38, 0);
  const hc = [96, 62, 58];
  houseSil(-60, 1450, 330, 220, 140, hc, 1, 0.35); oak(X, 340, 1450, 300, 9);
  houseSil(430, 1450, 360, 250, 150, hc, 2, 0.3); oak(X, 860, 1450, 260, 11);
  houseSil(960, 1450, 330, 210, 130, hc, 3, 0.35);
  X.fillRect(-200, 1440, 1600, 30);
  X.restore();
  // bus parked ahead
  const busX = 1250 - lt * 100;
  busSide({ x: busX, y: 1500, s: 62, face: 1, winA: 0.9, winCol: [255, 205, 140], rim: { c: [255, 210, 160], a: 0.9, dx: 3, dy: -1, bloom: 0.4 } });
  // fence near layer
  X.save(); X.translate(-((lt * 100) % 26), 0);
  silhouette(ctx => {
    for (let x = -60; x < W + 60; x += 26) { ctx.beginPath(); ctx.moveTo(x, 1500); ctx.lineTo(x, 1418); ctx.lineTo(x + 6, 1408); ctx.lineTo(x + 12, 1418); ctx.lineTo(x + 12, 1500); ctx.fill(); }
    ctx.fillRect(-60, 1432, W + 120, 8); ctx.fillRect(-60, 1468, W + 120, 8);
  }, { col: [30, 20, 18], rim: { c: [255, 200, 150], a: 0.6, dx: 2, dy: -1 } });
  X.restore();
  fillGrad(X, -100, 1500, W + 100, H + 100, [[0, [70, 48, 36]], [0.1, [34, 24, 20]], [1, [14, 10, 9]]]);
  pool(sunP[0], 1520, 700, 40, [255, 200, 140], 0.35);
  // Lily and Rusty
  const rim = { c: [255, 205, 150], a: 0.95, dx: 3, dy: -2, bloom: 0.45 };
  silhouette(ctx => lilyWalk(ctx, { x: 400, y: 1500, s: 270, phase: lt * 0.92 }), { rim });
  const P = { x: 650, y: 1500, s: 128, face: 1, gait: 'walk', phase: lt * 1.9, tail: 0.75, wag: 0.25, wagPh: lt * 9, head: -0.12, ear: 0.1 + 0.08 * Math.sin(lt * 10) };
  silhouette(ctx => dogSide(ctx, P), { rim });
  // falling leaves
  for (let i = 0; i < 18; i++) {
    const ph = (lt * 0.18 + hash1(i)) % 1;
    const lx = hash1(i * 3) * 1300 - ph * 300 + 30 * Math.sin(lt * 2 + i), ly = -50 + ph * 1700;
    X.save(); X.translate(lx, ly); X.rotate(lt * (1 + hash1(i)) * 3 + i); X.scale(1, Math.sin(lt * 3 + i));
    X.fillStyle = css(mixc([180, 80, 30], [255, 170, 80], hash1(i * 5)), 0.85);
    X.beginPath(); X.ellipse(0, 0, 9, 5, 0, 0, TAU); X.fill(); X.restore();
  }
  const ss = toScreen(...sunP);
  lensFlare(X, ss[0], ss[1], 0.75);
}

// ======================= S3a: kitchen, Dad at the table (9-12.6s)
function S3a(t) {
  const sc = lerp(1.0, 1.06, ease.sine(inv(8.6, 12.9, t)));
  zoomAt(sc, 600, 1250);
  fillGrad(X, -200, -200, W + 200, H + 200, [[0, [9, 12, 22]], [0.6, [16, 20, 34]], [1, [8, 9, 14]]]);
  // window with night + rain
  const w0 = [70, 620], w1 = [380, 1120];
  fillGrad(X, w0[0], w0[1], w1[0], w1[1], [[0, [16, 26, 54]], [1, [34, 50, 86]]]);
  light(290, 720, 30, [200, 215, 255], 0.9, 1); light(290, 720, 160, [140, 160, 220], 0.25, 0.4);
  X.save(); X.beginPath(); X.rect(w0[0], w0[1], w1[0] - w0[0], w1[1] - w0[1]); X.clip();
  drawRainGlass(t, w0, w1, 41, [170, 190, 230]);
  X.restore();
  X.fillStyle = css(INK);
  X.fillRect(w0[0] - 16, w0[1] - 16, w1[0] - w0[0] + 32, 18); X.fillRect(w0[0] - 16, w1[1], w1[0] - w0[0] + 32, 26);
  X.fillRect(w0[0] - 16, w0[1], 18, w1[1] - w0[1]); X.fillRect(w1[0] - 2, w0[1], 18, w1[1] - w0[1]);
  X.fillRect((w0[0] + w1[0]) / 2 - 6, w0[1], 12, w1[1] - w0[1]);
  // lamp
  X.fillRect(698, -400, 4, 1280);
  X.beginPath(); X.moveTo(610, 965); X.quadraticCurveTo(620, 870, 700, 868); X.quadraticCurveTo(780, 870, 790, 965); X.closePath(); X.fill();
  const flick = 1 - 0.04 * Math.max(0, noise1(t * 7));
  X.save(); X.globalCompositeOperation = 'lighter';
  const g = X.createLinearGradient(0, 965, 0, 1600);
  g.addColorStop(0, css([255, 200, 130], 0.20 * flick)); g.addColorStop(1, css([255, 200, 130], 0));
  X.fillStyle = g; X.beginPath(); X.moveTo(625, 965); X.lineTo(775, 965); X.lineTo(1150, 1600); X.lineTo(260, 1600); X.closePath(); X.fill();
  X.restore();
  light(700, 968, 90, [255, 215, 160], 0.9 * flick, 1.5);
  light(700, 1000, 520, [255, 190, 120], 0.22 * flick, 0.5);
  // floor + table
  fillGrad(X, -200, 1560, W + 200, H + 300, [[0, [20, 16, 18]], [1, [6, 6, 9]]]);
  pool(760, 1575, 420, 50, [255, 180, 110], 0.4);
  pool(790, 1330, 300, 18, [255, 210, 150], 0.6);
  const rim = { c: [255, 190, 120], a: 0.85, dx: 2.5, dy: -2.5, bloom: 0.4 };
  silhouette(ctx => {
    ctx.fillRect(520, 1330, 540, 22); ctx.fillRect(556, 1352, 18, 208); ctx.fillRect(1010, 1352, 18, 208);
    ctx.beginPath(); ctx.roundRect(880, 1266, 54, 64, 6); ctx.fill(); ctx.fillRect(934, 1282, 16, 30);
  }, { rim });
  X.fillStyle = css([230, 215, 190], 0.85); X.fillRect(640, 1324, 170, 6); X.fillRect(660, 1319, 150, 5);
  // Dad + Rusty
  silhouette(ctx => dadSitting(ctx, { x: 430, y: 1560, s: 330, t, sigh: sstep(10.4, 11.2, t) - sstep(11.2, 12.4, t) }), { rim });
  const P = { x: 185, y: 1560, s: 150, face: 1, sit: 1, head: -0.42 + 0.05 * Math.sin(t * 0.8), ear: 0.15, tailAngs: [2.2, 2.75 + 0.15 * Math.sin(t * 2.2), 3.05, 3.15], neck: -0.1 };
  silhouette(ctx => dogSide(ctx, P), { rim: { c: [255, 190, 120], a: 0.7, dx: 2, dy: -2, bloom: 0.3 } });
  const e = P.eyeXY; light(e[0], e[1], 7, [255, 220, 170], 0.7, 0.6);
}
function drawRainGlass(t, a, b, seed, col) {
  const r = rng(seed);
  X.save();
  for (let i = 0; i < 90; i++) {
    const x = lerp(a[0], b[0], r()), y0 = lerp(a[1], b[1], r()), rr = 1.5 + r() * 4;
    const run = r() < 0.18, sp = 60 + r() * 140;
    const y = run ? a[1] + ((y0 - a[1] + t * sp) % (b[1] - a[1])) : y0;
    X.fillStyle = css(col, 0.35); X.beginPath(); X.arc(x, y, rr, 0, TAU); X.fill();
    X.fillStyle = css([255, 255, 255], 0.35); X.beginPath(); X.arc(x - rr * 0.3, y - rr * 0.3, rr * 0.35, 0, TAU); X.fill();
    if (run) { X.strokeStyle = css(col, 0.18); X.lineWidth = rr * 0.8; X.beginPath(); X.moveTo(x, y - 60); X.lineTo(x, y); X.stroke(); }
  }
  X.restore();
}

// ======================= S3b: the lease (12.4-16.2s)
function S3b(t) {
  const u = inv(12.0, 16.4, t);
  zoomAt(lerp(1.0, 1.09, ease.sine(u)), 540, 980);
  X.translate(540, 980); X.rotate(lerp(-0.025, 0.012, u)); X.translate(-540, -980);
  // wooden table
  X.fillStyle = css([22, 15, 11]); X.fillRect(-300, -300, W + 600, H + 600);
  const r = rng(77);
  for (let i = 0; i < 60; i++) {
    const y = -200 + i * 40 + r() * 20;
    X.strokeStyle = css(r() > 0.5 ? [40, 26, 18] : [12, 8, 6], 0.5); X.lineWidth = 2 + r() * 6;
    X.beginPath(); X.moveTo(-300, y); for (let x = -300; x < W + 300; x += 60) X.lineTo(x, y + 6 * Math.sin(x * 0.004 + i)); X.stroke();
  }
  light(560, 930, 900, [255, 180, 110], 0.42, 0.25);
  // coffee ring + keys
  X.strokeStyle = css([60, 34, 20], 0.5); X.lineWidth = 5; X.beginPath(); X.arc(880, 1460, 64, 0.3, 5.9); X.stroke();
  X.save(); X.translate(190, 1450); X.rotate(0.35);
  const metal = (x0, y0, x1, y1) => { const g = X.createLinearGradient(x0, y0, x1, y1); g.addColorStop(0, css([214, 204, 178])); g.addColorStop(0.5, css([128, 118, 100])); g.addColorStop(1, css([196, 186, 160])); return g; };
  X.strokeStyle = metal(-30, -30, 30, 30); X.lineWidth = 6; X.beginPath(); X.arc(0, 0, 30, 0, TAU); X.stroke();
  for (const [ang, len] of [[0.2, 160], [1.4, 135]]) {
    X.save(); X.rotate(ang); X.translate(28, 0);
    X.fillStyle = metal(0, -24, len, 24);
    X.beginPath(); X.arc(26, 0, 25, 0, TAU); X.fill();
    X.fillRect(46, -7, len - 46, 14);
    for (let k = 0; k < 4; k++) X.fillRect(len - 42 + k * 9, 6, 6, 5 + (k % 2) * 5);
    X.fillStyle = css([22, 15, 11]); X.beginPath(); X.arc(14, 0, 7, 0, TAU); X.fill();
    X.restore();
  }
  X.restore();
  light(260, 1490, 40, [255, 230, 190], 0.35 + 0.25 * Math.sin(t * 3), 0.8);
  // paper
  X.save(); X.translate(560, 990); X.rotate(-0.055);
  X.shadowColor = 'rgba(0,0,0,0.6)'; X.shadowBlur = 40; X.shadowOffsetY = 14;
  X.fillStyle = vgrad(X, -420, 420, [[0, [240, 230, 208]], [1, [214, 199, 172]]]);
  X.fillRect(-320, -420, 640, 840);
  X.shadowColor = 'transparent';
  X.fillStyle = css([40, 32, 28]); X.textAlign = 'center'; X.textBaseline = 'middle';
  X.font = '700 34px Cinzel'; X.fillText('RESIDENTIAL LEASE', 0, -350);
  X.font = 'italic 500 20px Lora'; X.fillStyle = css([90, 80, 70]); X.fillText('Maple Court Apartments · Unit 4B', 0, -312);
  X.fillStyle = css([120, 108, 96], 0.55);
  const rr = rng(5);
  for (let y = -270; y < 360; y += 25) {
    if (y > 20 && y < 150) continue;
    const w = y % 125 === 5 ? 300 : 520 - rr() * 120;
    X.fillRect(-270, y, w, 9);
  }
  X.textAlign = 'left';
  X.fillStyle = css([28, 22, 20]); X.font = '700 31px Lora'; X.fillText('12. PETS.', -270, 50);
  X.font = '600 31px Lora'; X.fillText('No pets of any kind', -100, 50);
  X.fillText('are permitted on the premises.', -270, 100);
  // red pen circle, drawn on
  const p = ease.inOut(inv(13.1, 14.0, t));
  if (p > 0) {
    X.strokeStyle = css([190, 25, 25], 0.9); X.lineWidth = 5; X.lineCap = 'round';
    X.beginPath();
    for (let k = 0; k <= 60 * p; k++) {
      const a = -2.6 + (k / 60) * TAU * 1.08, rx = 210 + 6 * Math.sin(k * 0.7), ry = 46 + 4 * Math.sin(k * 0.5);
      const x = 85 + Math.cos(a) * rx, y = 52 + Math.sin(a) * ry;
      k ? X.lineTo(x, y) : X.moveTo(x, y);
    }
    X.stroke();
  }
  X.fillStyle = css([120, 108, 96], 0.7); X.font = 'italic 500 22px Lora'; X.fillText('Tenant signature:', -270, 330);
  X.strokeStyle = css([60, 50, 44], 0.8); X.lineWidth = 2; X.beginPath(); X.moveTo(-60, 342); X.lineTo(250, 342); X.stroke();
  X.restore();
  // Dad's hand resting at the edge
  const tr = 2 * noise1(t * 6);
  silhouette(ctx => {
    ctx.save(); ctx.translate(1010 + tr, 1210); ctx.rotate(-0.35);
    ctx.beginPath(); ctx.ellipse(70, 0, 120, 82, 0, 0, TAU); ctx.fill();
    for (let k = 0; k < 4; k++) capsule(ctx, -10, -55 + k * 34, -110 + Math.abs(k - 1.5) * 12, -60 + k * 38, 19, 16);
    capsule(ctx, 40, 70, -30, 110, 22, 17);
    capsule(ctx, 150, 0, 400, 40, 90, 100);
    ctx.restore();
  }, { rim: { c: [255, 190, 120], a: 0.8, dx: -2, dy: -2, bloom: 0.3 } });
}

// ======================= S4: sunset highway (16-22s)
function S4(t) {
  const lt = t - 16;
  zoomAt(1, 540, 960, 0, 0);
  sky([[0, [40, 28, 68]], [0.3, [128, 58, 96]], [0.52, [226, 112, 84]], [0.62, [255, 168, 104]], [0.7, [255, 214, 150]], [1, [255, 200, 140]]], -100, 1600);
  for (let i = 0; i < 6; i++) streak(((hash1(i) * 1400 - lt * (8 + i * 3)) % 1500) + 100, 420 + i * 110, 300 + hash1(i + 2) * 300, 14 + hash1(i) * 16, mixc([255, 150, 160], [255, 220, 170], i / 6), 0.28);
  const sunP = [760, 1140];
  sun(sunP[0], sunP[1], 72, [255, 200, 130], 1);
  birds(lt, [0, 1, 2, 3, 4, 5, 6].map(i => ({ x: 200 + i * 38 + hash1(i) * 30, y: 700 + hash1(i + 4) * 60 + Math.abs(i - 3) * 14, vx: 22, vy: -2, s: 9 + hash1(i) * 4, f: 9 + hash1(i) * 3, p: i })), [60, 30, 50]);
  // mountain layers
  ridge(1170, 170, 0.0021, 3, [200, 112, 116], -200, W + 200, H + 200, lt * 6);
  ridge(1215, 120, 0.003, 7, [134, 70, 96], -200, W + 200, H + 200, lt * 16);
  ridge(1270, 80, 0.0045, 11, [72, 38, 66], -200, W + 200, H + 200, lt * 40);
  X.save(); X.translate(-((lt * 110) % 2000), 0); treeLine(1340, 31, 40, 110, 28, [34, 18, 34], -100, W + 2200); X.restore();
  fogBand(X, lt, 1300, 50, [255, 170, 130], 0.2, 25, 2);
  // ground + road
  fillGrad(X, -100, 1340, W + 100, H + 100, [[0, [30, 16, 28]], [1, [10, 6, 12]]]);
  X.fillStyle = css([24, 16, 22]); X.fillRect(-100, 1452, W + 200, 80);
  X.fillStyle = css([255, 210, 150], 0.35);
  for (let k = 0; k < 8; k++) { const x = ((k * 260 - lt * 950) % 2080 + 2080) % 2080 - 300; X.fillRect(x, 1490, 120, 6); }
  pool(sunP[0], 1460, 600, 20, [255, 180, 120], 0.25);
  // the car with Rusty
  const bounce = Math.sin(lt * 9) * 1.6 + noise1(lt * 3) * 1.2;
  const car = { x: 540, y: 1508 + bounce, s: 200, face: 1, wheelRot: lt * 18, rim: { c: [255, 175, 110], a: 0.95, dx: 2.5, dy: -2.5, bloom: 0.5 }, glass: [[0, [255, 176, 130], 0.6], [1, [200, 100, 100], 0.55]], hubCol: [255, 170, 110] };
  carSide(car);
  const sill = [540 - 1.22 * 200, 1508 + bounce - 1.06 * 200];
  const hx = 540 - 0.86 * 200, hy = 1508 + bounce - 1.40 * 200 + Math.sin(lt * 7) * 2;
  const H1 = { x: hx, y: hy, s: 200, face: 1, head: -0.08 + 0.05 * Math.sin(lt * 1.7), jaw: 0.34 + 0.05 * Math.sin(lt * 12), tongue: 1, ear: 1.62 + 0.22 * Math.sin(lt * 15) + 0.1 * noise1(lt * 9), earStretch: 1.35 };
  silhouette(ctx => {
    capsule(ctx, sill[0] + 4, sill[1] + 6, hx - 34, hy + 34, 30, 27);
    capsule(ctx, sill[0] + 46, sill[1] - 2, sill[0] + 84, sill[1] - 8, 11, 10);
    ctx.beginPath(); ctx.ellipse(sill[0] + 92, sill[1] - 7, 15, 9, -0.15, 0, TAU); ctx.fill();
    dogHeadOnly(ctx, H1);
  }, { rim: { c: [255, 180, 120], a: 0.95, dx: 2.5, dy: -2.5, bloom: 0.5 } });
  // power poles whipping past (foreground)
  const pp = 820, off = (lt * 620) % pp;
  for (let k = -1; k < 3; k++) {
    const x = k * pp - off + 300;
    X.save(); X.globalAlpha = 0.95; pole(x, 1600, 1250, 1.6, INK); X.restore();
    wire(x - 54, 1600 - 1250 + 22, x + pp - 54, 1600 - 1250 + 22, 60, INK, 3);
    wire(x + 54, 1600 - 1250 + 22, x + pp + 54, 1600 - 1250 + 22, 60, INK, 3);
  }
  grass(1920, -50, W + 50, lt * 3, { col: INK, h: 160, dens: 5, seed: 8, wind: 2 });
  lensFlare(X, sunP[0], sunP[1], 0.8);
}

// ======================= S5a: the throw (22-26.2s)
function blueHourSky(t, dark = 0) {
  sky([[0, mixc([10, 18, 42], [5, 8, 20], dark)], [0.45, mixc([34, 54, 98], [16, 24, 50], dark)], [0.7, mixc([110, 92, 120], [44, 44, 74], dark)], [0.8, mixc([210, 124, 96], [90, 60, 70], dark)], [1, [40, 30, 34]]], -100, 1800);
  stars(t, 0.6 + dark * 0.4, 9, 120, 900);
}
function S5a(t) {
  const lt = t - 22;
  const pan = -210 * ease.inOut(inv(23.2, 24.9, t)) + 90 * ease.inOut(inv(24.9, 26.2, t));
  zoomAt(lerp(1.36, 1.42, inv(22, 26.2, t)), 520, 1480, pan, 0);
  blueHourSky(lt);
  moonAndWisps(800, 760, 46, 1, t);
  treeLine(1430, 44, 20, 70, 26, [14, 16, 28]);
  gasStation({ x: 120, y: 1480, s: 38, store: false, lights: { canopy: 1, store: 0, sign: 1 }, rim: { c: [120, 150, 210], a: 0.4, dx: 2, dy: -2 } });
  fillGrad(X, -400, 1478, W + 400, H + 300, [[0, [26, 26, 36]], [1, [8, 8, 12]]]);
  grass(1482, 560, W + 300, t, { col: [12, 13, 20], h: 70, dens: 3, seed: 3 });
  // car parked, facing left, mostly off frame
  carSide({ x: -170, y: 1488, s: 190, face: -1, rim: { c: [150, 180, 240], a: 0.5, dx: 2, dy: -2 }, glass: [[0, [60, 80, 130], 0.7], [1, [30, 40, 70], 0.7]] });
  // Dad throwing
  const u = inv(22.5, 23.7, t);
  let hand;
  const dadRim = { rim: { c: [140, 175, 240], a: 0.6, dx: 2, dy: -2.5, bloom: 0.2 } };
  if (t < 25.0) silhouette(ctx => { hand = dadThrow(ctx, { x: 430, y: 1484, s: 190, u, face: 1 }); }, dadRim);
  else { const wt = t - 25.0; silhouette(ctx => dadWalk(ctx, { x: 430 - wt * 190, y: 1484, s: 190, face: -1, phase: wt * 0.9, amp: sstep(25.0, 25.25, t) }), dadRim); }
  // ball
  const rel = 23.22, land = 24.6;
  if (t < rel) drawBall(hand[0], hand[1], 9, 0.7, 0.35);
  else {
    const h0 = dadThrow(RX, { x: 430, y: 1484, s: 190, u: inv(22.5, 23.7, rel), face: 1 });
    const q = inv(rel, land, t);
    const bp = q2 => { const sx = lerp(h0[0], 1060, q2), sy = lerp(h0[1], 1395, q2) - Math.sin(PI * q2) * 560 * (1 - q2 * 0.25); return [sx, sy]; };
    if (q < 1) {
      for (let k = 6; k >= 1; k--) { const qq = Math.max(0, q - k * 0.025); const p2 = bp(qq); X.fillStyle = css(TENNIS, 0.08 * (7 - k)); X.beginPath(); X.arc(p2[0], p2[1], lerp(9, 5, qq), 0, TAU); X.fill(); }
      const p = bp(q);
      drawBall(p[0], p[1], lerp(9, 5, q), 0.75, 0.5);
    }
  }
  // Rusty: excited, then the chase
  const runT = inv(23.25, 25.6, t);
  let P;
  if (t < 23.3) {
    const hop = Math.abs(Math.sin(lt * 9)) * 0.06;
    P = { x: 640, y: 1486, s: 116, face: -1, sit: 0, bob: -hop, head: -0.3 - sstep(22.6, 23.0, t) * 0.25, tail: 0.9, wag: 0.5, wagPh: t * 16, ear: -0.1, feet: [[0, -hop * 2], [0, -hop * 2], [0, -hop], [0, -hop]] };
  } else {
    const k = ease.in2(runT);
    P = { x: lerp(640, 1250, k), y: lerp(1486, 1440, k), s: lerp(116, 70, k), face: 1, gait: 'gallop', phase: t * 2.7, amp: sstep(23.25, 23.6, t), tail: 0.6, ear: 0.6, head: 0.05 };
  }
  silhouette(ctx => dogSide(ctx, P), { rim: { c: [150, 185, 250], a: 0.65, dx: 2, dy: -2.5, bloom: 0.2 } });
  grass(1500, 700, W + 400, t, { col: [10, 11, 17], h: 55, dens: 4, seed: 13 });
}

// ======================= S5b: wide, the car leaves (26.2-30s)
function S5b(t) {
  zoomAt(lerp(1.5, 1.56, inv(26.2, 30, t)), 600, 1515);
  blueHourSky(t, 0.25);
  moonAndWisps(760, 1150, 26, 1, t);
  treeLine(1450, 45, 8, 26, 20, [12, 14, 26]);
  gasStation({ x: 170, y: 1520, s: 20, lights: { canopy: 1, store: 1, sign: 1 } });
  fillGrad(X, -400, 1518, W + 400, H + 300, [[0, [24, 24, 34]], [1, [7, 7, 11]]]);
  grass(1505, 560, W + 300, t, { col: [12, 13, 20], h: 46, dens: 3, seed: 6 });
  // tiny Rusty far in the field
  const found = sstep(28.6, 29.0, t);
  const P = { x: 790, y: 1474, s: 46, face: 1, head: lerp(0.75, -0.15, found), neck: lerp(0.3, 0, found), tail: 0.7, wag: 0.5, wagPh: t * 14, ear: 0.2 };
  silhouette(ctx => dogSide(ctx, P), { col: [8, 9, 15], rim: { c: [150, 180, 240], a: 0.7, dx: 1, dy: -2 } });
  if (found > 0.5) drawBall(P.ballXY[0], P.ballXY[1], 4, 0.7, 0.45);
  grass(1512, 860, W + 300, t, { col: [11, 12, 19], h: 30, dens: 3, seed: 16 });
  // the car: door slam, lights, drive away left
  const shake = (t > 26.5 && t < 26.8) ? Math.sin((t - 26.5) * 80) * 3 * (1 - inv(26.5, 26.8, t)) : 0;
  const go = Math.pow(inv(27.6, 29.6, t), 2.2);
  const cx = lerp(470, -520, go);
  carSide({ x: cx, y: 1530 + shake, s: 92, face: -1, wheelRot: -go * 40, lights: { tail: sstep(27.0, 27.15, t), head: sstep(27.05, 27.2, t) }, glass: [[0, [60, 80, 130], 0.7], [1, [30, 40, 70], 0.7]], rim: { c: [150, 180, 240], a: 0.4, dx: 2, dy: -2 } });
  if (go > 0.02) { // taillight trail
    X.save(); X.globalCompositeOperation = 'lighter';
    const tx = cx + 2.24 * 92;
    const g = X.createLinearGradient(tx, 0, tx + 260 * go + 20, 0);
    g.addColorStop(0, css([255, 40, 30], 0.5)); g.addColorStop(1, css([255, 40, 30], 0));
    X.fillStyle = g; X.fillRect(tx, 1530 - 0.98 * 92, 260 * go + 20, 10);
    X.restore();
  }
  fogBand(X, t, 1500, 40, [70, 80, 120], 0.15, 8, 4);
}

// ======================= S6: the empty spot (30-36s)
function S6(t) {
  const sc = lerp(1.3, 1.42, ease.sine(inv(30, 36.4, t)));
  zoomAt(sc, 640, 1520);
  sky([[0, [5, 9, 22]], [0.5, [16, 26, 52]], [0.72, [44, 52, 84]], [0.8, [70, 58, 76]], [1, [20, 20, 28]]], -200, 1700);
  stars(t, 0.9, 12, 160, 1000);
  moonAndWisps(830, 1080, 30, 1, t);
  treeLine(1405, 52, 14, 46, 22, [10, 12, 22]);
  const flick = 1 - (hash1(Math.floor(t * 10)) > 0.93 ? 0.35 : 0);
  gasStation({ x: 360, y: 1420, s: 30, lights: { canopy: flick, store: 1, sign: 1 }, rim: { c: [150, 190, 255], a: 0.3, dx: 2, dy: -2 } });
  // parking lot
  fillGrad(X, -400, 1418, W + 400, H + 300, [[0, [30, 32, 44]], [0.3, [16, 17, 24]], [1, [6, 6, 9]]]);
  X.save(); X.strokeStyle = css([200, 205, 220], 0.28); X.lineWidth = 7;
  for (const x of [130, 520, 910]) { X.beginPath(); X.moveTo(x, 1450); X.lineTo(x - 260, 1940); X.stroke(); }
  X.restore();
  X.fillStyle = css([2, 2, 4], 0.45); X.beginPath(); X.ellipse(470, 1600, 110, 14, 0, 0, TAU); X.fill(); // oil stain
  X.strokeStyle = css([2, 2, 4], 0.35); X.lineWidth = 16; X.beginPath(); X.moveTo(420, 1600); X.quadraticCurveTo(300, 1660, 120, 1700); X.stroke();
  pool(360, 1440, 620, 60, [180, 210, 255], 0.22 * flick);
  // Rusty trots back, stops, looks around, drops the ball
  const arrive = 32.4;
  const k = ease.out(inv(30.0, arrive, t));
  const trotAmp = 1 - sstep(arrive - 0.35, arrive + 0.1, t);
  const look = t > 33.0 && t < 33.35 ? 1 : -1;
  const sad = sstep(34.0, 35.6, t);
  const P = {
    x: lerp(1180, 620, k), y: lerp(1500, 1545, k), s: lerp(120, 152, k), face: look,
    gait: 'trot', phase: t * 2.3, amp: trotAmp,
    tail: lerp(0.45, -0.6, sad), wag: 0.3 * (1 - sad), wagPh: t * 13,
    head: lerp(-0.2, 0.32, sad) - sstep(32.4, 32.8, t) * 0.15 * (1 - sad), neck: sad * 0.25,
    ear: lerp(0.0, 0.35, sad) - sstep(32.4, 32.7, t) * 0.25 * (1 - sad),
    jaw: t < 33.6 ? 0.14 : lerp(0.14, 0.42, sstep(33.6, 33.8, t)) - sstep(34.2, 34.8, t) * 0.4,
  };
  silhouette(ctx => dogSide(ctx, P), { rim: { c: [170, 205, 255], a: 0.6, dx: -1, dy: -2.5, bloom: 0.3 } });
  // ball: in mouth, then dropped
  if (t < 33.65) drawBall(P.ballXY[0], P.ballXY[1], 10, 0.6, 0.25);
  else {
    const lt = t - 33.65, g0 = 1556;
    const x0 = P.ballXY[0], y0 = P.ballXY[1];
    // bounces: decreasing heights, rolling toward camera
    const T1 = 0.32, T2 = 0.26, T3 = 0.16;
    let y, h;
    if (lt < T1) { const q = lt / T1; y = lerp(y0, g0, q * q); }
    else if (lt < T1 + T2) { const q = (lt - T1) / T2; y = g0 - 70 * 4 * q * (1 - q); }
    else if (lt < T1 + T2 + T3) { const q = (lt - T1 - T2) / T3; y = g0 - 24 * 4 * q * (1 - q); }
    else y = g0;
    const roll = ease.out(inv(0, 1.6, lt));
    const bx = x0 + roll * 190, by = y + roll * 40;
    const br = lerp(10, 15, roll);
    X.fillStyle = css([0, 0, 0], 0.4); X.beginPath(); X.ellipse(bx, g0 + roll * 40 + br * 0.9, br * 1.1, br * 0.3, 0, 0, TAU); X.fill();
    drawBall(bx, by, br, 0.65, 0.3, roll * 1.5);
  }
  if (t > 34.2) { const e = P.eyeXY; light(e[0], e[1], 6, [200, 225, 255], 0.75 * sstep(34.2, 34.8, t), 0.7); }
}

// ======================= S7: waiting all night (36-43s)
function S7(t) {
  const u = inv(36, 43, t);
  const night = sstep(0.0, 0.45, u), storm = sstep(0.35, 0.7, u);
  const flash = t > 41.55 && t < 41.95 ? Math.pow(1 - inv(41.55, 41.95, t), 2) * (Math.sin((t - 41.55) * 60) > -0.3 ? 1 : 0.4) : 0;
  const VP = [560, 1050];
  zoomAt(lerp(1.0, 1.05, u), 540, 1300);
  sky([[0, mixc([20, 30, 62], [3, 4, 9], night)], [0.5, mixc([60, 64, 104], [8, 11, 20], night)], [0.8, mixc([200, 120, 90], [22, 22, 30], night)], [1, [16, 16, 22]]], -200, 1250);
  stars(t, sstep(0.2, 0.4, u) * (1 - storm), 21, 220, 900);
  stormClouds(t * 22, 0.25 + storm * 0.55, 6, 70, 80, 900, mixc([60, 64, 90], [34, 42, 58], night), [8, 11, 20]);
  if (flash > 0) { X.save(); X.globalCompositeOperation = 'screen'; X.fillStyle = css([170, 185, 230], flash * 0.7); X.fillRect(-200, -200, W + 400, 1300); X.restore(); lightningBolt(99, 820, 60, 1000, flash); }
  treeLine(1056, 61, 12, 40, 20, [9, 11, 17]);
  X.fillStyle = css([8, 10, 14]); X.fillRect(-300, 1050, W + 600, 1100);
  road(VP, 1940, -560, 760, vgrad(X, 1050, 1940, [[0, mixc([60, 60, 80], [34, 38, 50], night)], [0.3, [20, 23, 31]], [1, [10, 12, 17]]]), { lineA: 0.2 });
  // light trails of passing cars, fewer as the night goes on
  for (let k = 0; k < 26; k++) {
    const st = 36 + k * 0.27 + hash1(k) * 0.2;
    if (hash1(k * 9) < u * 1.1) continue;
    const q = inv(st, st + 0.55, t);
    if (q <= 0 || q >= 1) continue;
    const away = k % 2 === 0, lane = away ? 300 : -200;
    const dA = away ? lerp(1.3, 20, q) : lerp(20, 1.3, q), dB = away ? Math.max(1.05, dA - 4) : Math.min(30, dA + 6);
    const yA = VP[1] + 890 / dA, yB = VP[1] + 890 / dB;
    const xA = lerp(VP[0], lane, (yA - VP[1]) / 890), xB = lerp(VP[0], lane, (yB - VP[1]) / 890);
    const c = away ? [255, 40, 30] : [255, 240, 210];
    X.save(); X.globalCompositeOperation = 'lighter'; X.lineCap = 'round';
    X.strokeStyle = css(c, 0.55); X.lineWidth = 2 + 26 / Math.min(dA, dB);
    X.beginPath(); X.moveTo(xA, yA); X.lineTo(xB, yB); X.stroke(); X.restore();
    emit(e => { e.strokeStyle = css(c, 0.6); e.lineWidth = 4 + 30 / Math.min(dA, dB); e.beginPath(); e.moveTo(xA, yA); e.lineTo(xB, yB); e.stroke(); });
  }
  const offC = t < 39.4 ? 1 : (t < 39.7 ? (hash1(Math.floor(t * 30)) > 0.5 ? 1 : 0) : 0);
  const offS = t < 40.2 ? 1 : 0;
  const offG = t < 40.9 ? 0.9 : (t < 41.25 ? (hash1(Math.floor(t * 25)) > 0.45 ? 0.8 : 0.05) : 0);
  const gs = gasStation({ x: 280, y: 1170, s: 26, lights: { canopy: offC, store: offS, sign: offG }, wet: storm, rim: { c: [190, 205, 255], a: flash * 0.9, dx: 3, dy: -2 } });
  if (flash > 0) { X.save(); X.globalCompositeOperation = 'screen'; X.fillStyle = css([120, 135, 180], flash * 0.25); X.fillRect(-200, 1050, W + 400, 1000); X.restore(); }
  const jit = Math.floor(t * 2);
  const P = { x: 610, y: 1720, s: 225, sit: 1, t: t * 3, turn: -0.12 + (hash1(jit + 7) - 0.5) * 0.5, sweep: Math.sin(t * 5) * (1 - u), tilt: (hash1(jit) - 0.5) * 0.12 + sstep(0.6, 1, u) * 0.1, headY: sstep(0.3, 1, u) * 0.07, perk: (hash1(jit + 3) - 0.5) * 0.6 - storm * 0.4 };
  silhouette(ctx => dogBack(ctx, P), { rim: { c: [200, 215, 255], a: 0.35 + flash * 0.9, dx: 2, dy: -2.5, bloom: flash } });
  silhouette(ctx => dogBack(ctx, P), { alpha: 0, rim: { c: [255, 150, 110], a: 0.55 * offG + 0.35 * offC, dx: -3, dy: -1.5, bloom: 0.3 } });
  drawBall(760, 1712, 14, 0.25 + flash, 0.08);
  const sg = toScreen(...gs.sign);
  drawRain(X, t, storm * 0.95, { wind: -0.14, gain: 1 + flash * 2, lights: offG > 0.1 ? [{ x: sg[0], y: sg[1], r: 240, c: [255, 90, 70], a: 0.6 * offG }] : [] });
  drawSplashes(X, t, storm, 1180, 1920, { gain: 1 + flash * 2 });
}

// ======================= S8: home, the porch light (43-52s)
function S8(t) {
  const pan = ease.inOut(inv(48.8, 50.5, t));
  const sc = lerp(1.32, 1.12, pan) + 0.03 * inv(50.5, 52.4, t);
  const cx = lerp(540, 560, pan), cy = lerp(840, 1520, pan);
  X.setTransform(sc, 0, 0, sc, W / 2 - sc * cx, H / 2 - sc * cy);
  sky([[0, [6, 8, 16]], [0.5, [12, 16, 30]], [1, [16, 20, 34]]], -400, 1900);
  stormClouds(t, 0.4, 10, 90, -100, 400);
  // house
  const wall = [18, 22, 36];
  X.fillStyle = css(wall); X.fillRect(40, 520, 1000, 1290);
  X.fillStyle = css([12, 14, 24]);
  X.beginPath(); X.moveTo(-60, 560); X.lineTo(540, 150); X.lineTo(1140, 560); X.closePath(); X.fill();
  X.fillStyle = css(INK); X.fillRect(-60, 548, 1200, 26); X.fillRect(800, 210, 80, 220);
  X.strokeStyle = css([26, 32, 50], 0.6); X.lineWidth = 3;
  for (let y = 600; y < 1800; y += 34) { X.beginPath(); X.moveTo(40, y); X.lineTo(1040, y); X.stroke(); }
  // upstairs window: Lily + Dad
  const wx0 = 330, wx1 = 750, wy0 = 600, wy1 = 1060;
  fillGrad(X, wx0, wy0, wx1, wy1, [[0, [255, 196, 128]], [1, [230, 150, 90]]]);
  light(540, 830, 480, [255, 180, 110], 0.4, 1.0);
  X.save(); X.beginPath(); X.rect(wx0, wy0, wx1 - wx0, wy1 - wy0); X.clip();
  silhouette(ctx => windowFamily(ctx, { x: 545, y: wy1 + 24, s: 430, t, hand: sstep(46.6, 47.3, t) }), { col: [12, 8, 10] });
  X.restore();
  X.save(); X.beginPath(); X.rect(wx0, wy0, wx1 - wx0, wy1 - wy0); X.clip(); drawRainGlass(t, [wx0, wy0], [wx1, wy1], 17, [255, 210, 160]); X.restore();
  X.fillStyle = css(INK);
  X.fillRect(wx0 - 22, wy0 - 22, wx1 - wx0 + 44, 24); X.fillRect(wx0 - 30, wy1, wx1 - wx0 + 60, 30);
  X.fillRect(wx0 - 22, wy0, 24, wy1 - wy0); X.fillRect(wx1 - 2, wy0, 24, wy1 - wy0);
  X.fillRect(538, wy0, 10, wy1 - wy0); X.fillRect(wx0, 826, wx1 - wx0, 10);
  fillGrad(X, -300, 1806, W + 300, 2800, [[0, [12, 14, 22]], [0.3, [6, 7, 11]], [1, [3, 3, 5]]]);
  X.fillStyle = css([16, 18, 28]); X.beginPath(); X.moveTo(400, 1900); X.lineTo(700, 1900); X.lineTo(820, 2800); X.lineTo(260, 2800); X.closePath(); X.fill();
  // downstairs dark windows, porch, door
  X.fillStyle = css([8, 10, 18]); X.fillRect(120, 1300, 230, 300); X.fillRect(760, 1300, 230, 300);
  X.fillStyle = css(INK);
  X.fillRect(20, 1250, 1040, 34);
  for (const x of [60, 1010]) X.fillRect(x, 1284, 22, 520);
  X.fillRect(470, 1420, 150, 380);
  X.fillStyle = css([30, 26, 30]); X.fillRect(500, 1450, 90, 120);
  for (let k = 0; k < 3; k++) X.fillRect(380 - k * 30, 1800 + k * 34, 330 + k * 60, 34);
  // porch light
  const on = t < 50.55 ? 0 : (t < 50.95 ? (hash1(Math.floor(t * 28)) > 0.4 ? 1 : 0.15) : 1);
  X.fillStyle = css(INK); X.fillRect(672, 1430, 16, 20); X.beginPath(); X.roundRect(662, 1446, 36, 52, 6); X.fill();
  if (on > 0) {
    X.fillStyle = css([255, 225, 170], on); X.beginPath(); X.roundRect(668, 1452, 24, 40, 4); X.fill();
    light(680, 1472, 70, [255, 220, 160], 0.95 * on, 1.6);
    light(680, 1472, 520, [255, 180, 100], 0.35 * on, 0.6);
    pool(640, 1800, 360, 50, [255, 180, 110], 0.4 * on);
  }
  // Rusty's bowl on the top step
  X.save();
  X.fillStyle = css(mixc([12, 16, 34], [40, 60, 120], on * 0.8));
  X.beginPath(); X.moveTo(506, 1766); X.lineTo(654, 1766); X.quadraticCurveTo(648, 1800, 628, 1802); X.lineTo(532, 1802); X.quadraticCurveTo(512, 1800, 506, 1766); X.closePath(); X.fill();
  X.fillStyle = css(mixc([6, 8, 18], [24, 34, 70], on)); X.beginPath(); X.ellipse(580, 1766, 74, 11, 0, 0, TAU); X.fill();
  X.fillStyle = css([240, 225, 190], 0.15 + on * 0.75); X.font = '700 19px Lora'; X.textAlign = 'center'; X.textBaseline = 'middle'; X.fillText('RUSTY', 580, 1787);
  X.restore();
  // tree branches framing left
  silhouette(ctx => {
    const sw = 14 * noise1(t * 0.9) + 6 * Math.sin(t * 2.1);
    ctx.lineCap = 'round'; ctx.strokeStyle = '#000';
    capsule(ctx, -80, 300, 260 + sw, 520, 26, 8); capsule(ctx, 100 + sw * 0.4, 400, 210 + sw, 300, 10, 4);
    capsule(ctx, -80, 1150, 180 + sw, 1080, 22, 6);
    for (let k = 0; k < 14; k++) { const lx = 40 + k * 18 + sw * (k / 14), ly = 420 + Math.sin(k * 1.7) * 60; ctx.beginPath(); ctx.ellipse(lx, ly, 16, 7, k, 0, TAU); ctx.fill(); }
  }, { col: [3, 4, 7] });
  const lp = toScreen(680, 1472), wp = toScreen(540, 830);
  drawRain(X, t, 0.9, { wind: -0.12, lights: [{ x: lp[0], y: lp[1], r: 380, c: [255, 200, 130], a: on * 0.9 }, { x: wp[0], y: wp[1], r: 420 * sc, c: [255, 190, 120], a: 0.35 }] });
  const g0 = toScreen(0, 1800)[1];
  drawSplashes(X, t, 0.8, Math.min(g0, H), H + 10);
}

// ======================= S10: dawn, he starts walking (52-60s)
function S10(t) {
  const VP = [560, 1070];
  const crane = ease.inOut(inv(51.6, 60, t));
  zoomAt(lerp(1.07, 1.0, crane), 560, 1300, 0, lerp(30, -10, crane));
  sky([[0, [24, 30, 62]], [0.32, [88, 72, 116]], [0.52, [210, 128, 112]], [0.62, [255, 182, 128]], [0.7, [255, 214, 160]], [1, [255, 200, 150]]], -200, 1500);
  for (let i = 0; i < 6; i++) streak(80 + i * 190 + (t - 52) * 6, 360 + i * 95, 260 + hash1(i * 4) * 260, 16, [255, 160, 170], 0.26);
  const sunY = 1088 - (t - 52) * 3.2;
  sun(VP[0], sunY, 58, [255, 205, 140], 1);
  birds(t - 52, [0, 1, 2, 3, 4].map(i => ({ x: 120 + i * 50, y: 520 + hash1(i) * 80, vx: 18, vy: -3, s: 10, f: 10 + i, p: i })), [70, 40, 60]);
  treeLine(1076, 81, 12, 52, 22, [52, 30, 44], -100, 440); treeLine(1076, 82, 12, 46, 22, [52, 30, 44], 690, W + 100);
  fogBand(X, t, 1090, 50, [255, 190, 150], 0.35, 14, 6);
  // fields
  fillGrad(X, -300, 1068, W + 300, H + 300, [[0, [70, 44, 50]], [0.2, [30, 20, 26]], [1, [10, 8, 12]]]);
  // wet road reflecting the sky
  road(VP, 1940, -380, 1500, vgrad(X, 1070, 1940, [[0, [240, 176, 130]], [0.18, [126, 86, 96]], [0.5, [44, 34, 44]], [1, [16, 13, 18]]]), { lineA: 0.35 });
  glowTo(X, VP[0], 1180, 140, [255, 210, 150], 0.65, 0.5, 6.5);
  emit(e => glowTo(e, VP[0], 1180, 90, [255, 210, 150], 0.35, 0.5, 6));
  for (let i = 0; i < 4; i++) { const px = 300 + hash1(i * 5) * 600, py = 1300 + hash1(i * 7) * 520; pool(px, py, 90 + hash1(i) * 80, 12, [255, 190, 150], 0.4); }
  gasStation({ x: 150, y: 1200, s: 24, lights: { canopy: 0, store: 0, sign: 0 }, rim: { c: [255, 180, 130], a: 0.5, dx: 2, dy: -2 } });
  grass(1078, -60, 300, t, { col: [40, 24, 34], h: 22, dens: 3, seed: 2 });
  grass(1078, 820, W + 60, t, { col: [40, 24, 34], h: 22, dens: 3, seed: 4 });
  // Rusty
  const standK = ease.inOut(inv(52.7, 53.4, t));
  const pick = sstep(53.4, 53.8, t) - sstep(53.95, 54.35, t);
  const walk = inv(54.3, 60, t);
  const z = 4 + 1.25 * Math.max(0, t - 54.3) * ease.out2(inv(54.3, 54.8, t)) ;
  const kz = 4 / z;
  const px = lerp(560, VP[0] + 30, 1 - kz) + 0, py = VP[1] + 570 * kz;
  const P = { x: px, y: py, s: 200 * kz, sit: 1 - standK, t: t * 3, phase: (t - 54.3) * 1.75, amp: sstep(54.3, 54.7, t),
    perk: sstep(52.0, 52.5, t) * 0.7, headY: pick * 0.13, turn: sstep(53.3, 53.7, t) * 0.55 - sstep(54.2, 54.6, t) * 0.3, tilt: pick * 0.15, tail: 0.15 + walk * 0.2 };
  // long shadow toward the camera
  X.save(); X.translate(P.x, P.y); X.transform(1, 0, -0.18, -1.9, 0, 0); X.translate(-P.x, -P.y);
  X.filter = 'blur(3px)'; X.fillStyle = css([12, 8, 14], 0.5); dogBack(X, P); X.filter = 'none';
  X.restore();
  silhouette(ctx => dogBack(ctx, P), { rim: { c: [255, 205, 150], a: 1, dx: 0, dy: -3, bloom: 0.7 } });
  // the ball: on the ground, then carried
  const groundBall = [700, 1627];
  const carry = [P.mouthXY[0] + P.s * 0.03, P.mouthXY[1] + P.s * 0.03];
  const bq = sstep(53.75, 54.1, t);
  const bpos = [lerp(groundBall[0], carry[0], bq), lerp(groundBall[1], carry[1], bq)];
  drawBall(bpos[0], bpos[1], lerp(13, 13 * kz, bq), 0.95, 0.35);
  lensFlare(X, VP[0], sunY, 0.55);
}
