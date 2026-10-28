'use strict';
// Characters and vehicles, drawn as silhouettes. Shape functions only fill with the
// context's current fillStyle, so the same function can draw the silhouette and its rim light.

const INK = [7, 8, 12];
const TENNIS = [206, 228, 74];

// ---------- silhouette + rim light
const RIM = mkCanvas(W, H), RX = RIM.getContext('2d');
function silhouette(drawFn, o = {}) {
  X.save(); X.fillStyle = css(o.col || INK, o.alpha ?? 1); drawFn(X); X.restore();
  if (!o.rim) return;
  const m = X.getTransform();
  RX.setTransform(1, 0, 0, 1, 0, 0); RX.globalCompositeOperation = 'source-over'; RX.clearRect(0, 0, W, H);
  RX.setTransform(m); RX.fillStyle = css(o.rim.c, 1); drawFn(RX);
  RX.globalCompositeOperation = 'destination-out';
  RX.setTransform(1, 0, 0, 1, -o.rim.dx, -o.rim.dy); RX.transform(m.a, m.b, m.c, m.d, m.e, m.f);
  RX.fillStyle = '#000'; drawFn(RX);
  RX.globalCompositeOperation = 'source-over';
  X.save(); X.setTransform(1, 0, 0, 1, 0, 0); X.globalCompositeOperation = 'lighter'; X.globalAlpha = clamp(o.rim.a);
  X.drawImage(RIM, 0, 0); X.restore();
  if (o.rim.bloom && EX) {
    EX.save(); EX.setTransform(1, 0, 0, 1, 0, 0); EX.globalCompositeOperation = 'lighter';
    EX.globalAlpha = clamp(o.rim.a * o.rim.bloom); EX.drawImage(RIM, 0, 0, W / EMS, H / EMS); EX.restore();
  }
}

// ---------- tennis ball: the one saturated thing in a silhouette world
function drawBall(x, y, r, lit = 1, glowAmt = 0.25, blur = 0) {
  X.save();
  if (blur > 0.3) X.filter = `blur(${blur}px)`;
  const base = mixc([30, 34, 18], TENNIS, clamp(lit));
  const g = X.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
  g.addColorStop(0, css(mixc(base, [255, 255, 220], 0.35)));
  g.addColorStop(0.55, css(base));
  g.addColorStop(1, css(mixc(base, [0, 0, 0], 0.55)));
  X.fillStyle = g; X.beginPath(); X.arc(x, y, r, 0, TAU); X.fill();
  X.strokeStyle = css([245, 245, 230], 0.55 * clamp(lit)); X.lineWidth = Math.max(1, r * 0.09);
  X.beginPath(); X.arc(x - r * 0.9, y, r * 0.75, -0.9, 0.9); X.stroke();
  X.beginPath(); X.arc(x + r * 0.9, y, r * 0.75, PI - 0.9, PI + 0.9); X.stroke();
  X.restore();
  if (glowAmt > 0) light(x, y, r * 3.2, TENNIS, glowAmt * clamp(lit + 0.3), 0.6);
}

// ---------- dog, side view. Local units: withers height = 1, ground y = 0, facing +x.
const DOG_BODY = [[0.13, -1.03], [-0.08, -1.00], [-0.33, -0.99], [-0.56, -1.00], [-0.70, -0.95], [-0.77, -0.82], [-0.73, -0.64],
  [-0.57, -0.52], [-0.36, -0.53], [-0.13, -0.48], [0.10, -0.41], [0.27, -0.45], [0.38, -0.60], [0.41, -0.80], [0.31, -0.97]];
const HIP0 = [-0.51, -0.74], SHO0 = [0.22, -0.74], NECK0 = [0.25, -0.92], HEAD0 = [0.64, -1.28], TAIL0 = [-0.70, -0.92];
const GAITS = {
  walk: { st: 0.62, stride: 0.42, lift: 0.11, ph: [0, 0.5, 0.25, 0.75], bob: 0.018 },
  trot: { st: 0.5, stride: 0.62, lift: 0.16, ph: [0, 0.5, 0.5, 0], bob: 0.03 },
  gallop: { st: 0.36, stride: 1.05, lift: 0.24, ph: [0, 0.12, 0.52, 0.62], bob: 0.06 },
};
function gaitFoot(phase, st, stride, lift) {
  const p = ((phase % 1) + 1) % 1;
  if (p < st) return [lerp(stride / 2, -stride / 2, p / st), 0];
  const q = (p - st) / (1 - st);
  return [lerp(-stride / 2, stride / 2, ease.sine(q)), -lift * Math.sin(PI * q)];
}
const HEAD_TOP = [[-0.17, 0.02], [-0.13, -0.10], [-0.04, -0.155], [0.07, -0.15], [0.135, -0.095], [0.20, -0.078], [0.30, -0.062],
  [0.345, -0.038], [0.362, 0.0], [0.345, 0.032], [0.30, 0.055], [0.20, 0.068], [0.13, 0.082]];
const JAW = [[0.28, 0.078], [0.20, 0.118], [0.07, 0.135]];
const HEAD_BOT = [[-0.04, 0.152], [-0.14, 0.10]];
const EAR = [[0.04, -0.02], [-0.05, -0.035], [-0.115, 0.05], [-0.12, 0.17], [-0.065, 0.24], [0.012, 0.19], [0.048, 0.07]];
const TONGUE = [[0.12, 0.11], [0.22, 0.125], [0.255, 0.19], [0.225, 0.245], [0.17, 0.215], [0.14, 0.16]];

function dogSide(ctx, P) {
  const sit = P.sit || 0, g = P.gait ? GAITS[P.gait] : null, ph = P.phase || 0, amp = g ? (P.amp ?? 1) : 0;
  let bob = 0, pitch = 0;
  if (g) {
    bob = g.bob * amp * Math.sin(2 * TAU * ph);
    if (P.gait === 'gallop') { pitch = 0.10 * amp * Math.sin(TAU * ph + 0.6); bob = 0.06 * amp * Math.sin(TAU * ph); }
  }
  bob += P.bob || 0;
  const hip = [lerp(HIP0[0], -0.33, sit), lerp(HIP0[1], -0.27, sit) + bob];
  const rb = lerp(0, -0.60, sit) + pitch + (P.lean || 0);
  const T = p => add(hip, rot(sub(p, HIP0), rb));
  const sho = T(SHO0);

  // head transform
  const N = T(NECK0);
  const hc = add(N, rot(sub(HEAD0, NECK0), rb * 0.5 + (P.neck || 0)));
  const hr = (P.head || 0) + (g ? 0.04 * amp * Math.sin(2 * TAU * ph + 1) : 0);
  const Hd = p => add(hc, rot(p, hr));

  ctx.save();
  ctx.translate(P.x, P.y);
  ctx.scale(P.s * (P.face || 1), P.s);

  // legs
  const legs = [];
  for (let i = 0; i < 4; i++) {
    const hind = i < 2, far = i % 2 === 1;
    let fx = hind ? lerp(hip[0] + 0.04, hip[0] + 0.30, sit) : lerp(sho[0] + 0.03, sho[0] + 0.05, sit);
    let fy = 0;
    if (g) { const d = gaitFoot(ph + g.ph[i], g.st, g.stride, g.lift); fx += d[0] * amp * (1 - sit); fy += d[1] * amp * (1 - sit); }
    if (far) fx += 0.05;
    if (P.feet && P.feet[i]) { fx += P.feet[i][0]; fy += P.feet[i][1]; }
    legs.push({ hind, far, foot: [fx, fy] });
  }
  const drawLeg = L => {
    const k = L.far ? 0.9 : 1, f = L.foot;
    if (L.hind) {
      const lift = Math.max(0, -f[1]);
      const off = lerpPts([[-0.07, -0.23]], [[-0.30, -0.035]], sit)[0];
      const hock = add(f, rot(off, -lift * 1.2));
      const r = ik2(hip, hock, 0.40, 0.38, -1);
      capsule(ctx, hip[0], hip[1], r.joint[0], r.joint[1], 0.19 * k, 0.095 * k);
      capsule(ctx, r.joint[0], r.joint[1], r.end[0], r.end[1], 0.08 * k, 0.05 * k);
      capsule(ctx, r.end[0], r.end[1], f[0], f[1] - 0.03, 0.05 * k, 0.042 * k);
      ctx.beginPath(); ctx.ellipse(f[0] + 0.035, f[1] - 0.032, 0.07 * k, 0.034, 0, 0, TAU); ctx.fill();
    } else {
      const wrist = add(f, [-0.035, -0.13]);
      const r = ik2(sho, wrist, 0.36, 0.34, 1);
      capsule(ctx, sho[0], sho[1], r.joint[0], r.joint[1], 0.13 * k, 0.085 * k);
      capsule(ctx, r.joint[0], r.joint[1], r.end[0], r.end[1], 0.07 * k, 0.046 * k);
      capsule(ctx, r.end[0], r.end[1], f[0], f[1] - 0.03, 0.046 * k, 0.04 * k);
      ctx.beginPath(); ctx.ellipse(f[0] + 0.04, f[1] - 0.03, 0.068 * k, 0.033, 0, 0, TAU); ctx.fill();
    }
  };
  legs.filter(l => l.far).forEach(drawLeg);

  // tail
  {
    const base = T(TAIL0);
    let angs;
    if (P.tailAngs) angs = P.tailAngs;
    else {
      const up = clamp(((P.tail ?? 0) + 1) / 2);
      const wag = (P.wag || 0) * Math.sin(P.wagPh || 0);
      const a0 = lerp(2.05, 3.95, up) + rb + wag;
      const curl = lerp(-0.05, 0.22, up);
      angs = [a0, a0 + curl, a0 + curl * 2, a0 + curl * 3];
      if (sit > 0.5) angs = angs.map((a, i) => lerp(a, [2.15, 2.75, 3.05, 3.15][i], (sit - 0.5) * 2));
    }
    const sp = [base];
    for (const a of angs) { const q = sp[sp.length - 1]; sp.push([q[0] + Math.cos(a) * 0.19, q[1] + Math.sin(a) * 0.19]); }
    const tw = [0.08, 0.065, 0.05, 0.034, 0.014], fw = [0.06, 0.12, 0.145, 0.12, 0.04];
    const top = [], bot = [];
    sp.forEach((p, i) => {
      const a = angs[Math.min(i, angs.length - 1)], n = [-Math.sin(a), Math.cos(a)];
      top.push([p[0] + n[0] * tw[i], p[1] + n[1] * tw[i]]);
      bot.push([p[0] - n[0] * fw[i], p[1] - n[1] * fw[i]]);
      if (i < sp.length - 1) { // feather tufts
        const q = sp[i + 1], m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2], w = (fw[i] + fw[i + 1]) * 0.62;
        bot.push([m[0] - n[0] * w + Math.cos(a) * 0.03, m[1] - n[1] * w + Math.sin(a) * 0.03]);
      }
    });
    ctx.beginPath(); polyPath(ctx, top.concat(bot.reverse())); ctx.fill();
  }

  // body
  ctx.beginPath(); smoothPath(ctx, DOG_BODY.map(T)); ctx.fill();
  // neck
  {
    const bt = T([0.05, -1.01]), bf = T([0.38, -0.70]);
    const hb = Hd([-0.13, -0.07]), ht = Hd([-0.03, 0.14]);
    ctx.beginPath(); ctx.moveTo(bt[0], bt[1]);
    ctx.quadraticCurveTo((bt[0] + hb[0]) / 2 - 0.04, (bt[1] + hb[1]) / 2 - 0.05, hb[0], hb[1]);
    ctx.lineTo(ht[0], ht[1]);
    ctx.quadraticCurveTo((ht[0] + bf[0]) / 2 + 0.06, (ht[1] + bf[1]) / 2, bf[0], bf[1]);
    ctx.lineTo(T([0.16, -0.75])[0], T([0.16, -0.75])[1]); ctx.closePath(); ctx.fill();
  }
  legs.filter(l => !l.far).forEach(drawLeg);

  // head
  {
    const jaw = P.jaw || 0, pv = [0.02, 0.075];
    const jp = JAW.map(p => add(pv, rot(sub(p, pv), jaw)));
    const pts = HEAD_TOP.concat(jp, HEAD_BOT).map(Hd);
    ctx.beginPath(); smoothPath(ctx, pts, true, 1 / 7); ctx.fill();
    if (P.tongue) { const tp = TONGUE.map(p => Hd(add(pv, rot(sub(p, pv), jaw * 0.8)))); ctx.beginPath(); smoothPath(ctx, tp); ctx.fill(); }
    const ep = [-0.05, -0.10], ea = (P.ear || 0);
    const er = EAR.map(p => Hd(add(ep, rot(p, ea))));
    ctx.beginPath(); smoothPath(ctx, er); ctx.fill();
    P._ball = Hd(add(pv, rot([0.235, 0.075], jaw * 0.6)));
    P._eye = Hd([0.075, -0.07]);
    P._nose = Hd([0.36, 0.0]);
  }
  ctx.restore();
  const toScreen = q => [P.x + (P.face || 1) * P.s * q[0], P.y + P.s * q[1]];
  P.ballXY = toScreen(P._ball); P.eyeXY = toScreen(P._eye); P.noseXY = toScreen(P._nose);
  P.headXY = toScreen(hc);
}

// ---------- dog, back view (seen from behind). Units: withers = 1, ground y = 0.
// Right-half outlines from bottom center to top center; equal point counts so sit and stand morph.
const DB_SIT = [[0, 0], [0.30, 0], [0.40, -0.06], [0.435, -0.18], [0.415, -0.33], [0.355, -0.47], [0.275, -0.60], [0.215, -0.74], [0.185, -0.88], [0.17, -0.98], [0.135, -1.05], [0.07, -1.085], [0, -1.095]];
const DB_STAND = [[0, -0.50], [0.10, -0.52], [0.17, -0.58], [0.21, -0.68], [0.225, -0.80], [0.205, -0.90], [0.165, -0.97], [0.15, -1.03], [0.155, -1.08], [0.145, -1.12], [0.115, -1.16], [0.06, -1.18], [0, -1.19]];
const DB_EAR = [[-0.02, -0.03], [0.06, -0.02], [0.11, 0.06], [0.118, 0.17], [0.085, 0.235], [0.035, 0.205], [0.005, 0.1]];
function dogBack(ctx, P) {
  const sit = clamp(P.sit ?? 1), st = 1 - sit, ph = P.phase || 0, amp = P.amp ?? 0, turn = P.turn || 0;
  const sway = 0.03 * amp * Math.sin(TAU * ph);
  ctx.save();
  ctx.translate(P.x, P.y); ctx.scale(P.s, P.s); ctx.rotate(sway * 0.5 + (P.lean || 0));
  const body = mirrorHalf(lerpPts(DB_SIT, DB_STAND, st));
  const breath = 1 + 0.008 * Math.sin((P.t || 0) * 2.2);
  // legs when standing: front legs further back between the hind legs
  const legK = clamp(st * 1.4);
  if (legK > 0) {
    for (const [lx, o] of [[-0.075, 0.5], [0.075, 0]]) {
      const fl = Math.max(0, Math.sin(TAU * (ph + o))) * 0.06 * amp;
      capsule(ctx, lx, -0.55 * legK, lx, -fl - 0.02, 0.042, 0.034);
      ctx.beginPath(); ctx.ellipse(lx, -fl - 0.018, 0.045, 0.024, 0, 0, TAU); ctx.fill();
    }
    for (const [lx, o] of [[-0.13, 0], [0.13, 0.5]]) {
      const lift = Math.max(0, Math.sin(TAU * (ph + o))) * 0.09 * amp, s = Math.sign(lx);
      const top = -0.66 * legK, hock = -0.24 - lift * 0.5;
      capsule(ctx, lx, top, lx * 1.05, hock, 0.105, 0.05);
      ctx.beginPath(); ctx.moveTo(lx + s * 0.07, top + 0.08); ctx.lineTo(lx + s * 0.12, top + 0.30); ctx.lineTo(lx + s * 0.04, top + 0.27); ctx.closePath(); ctx.fill();
      capsule(ctx, lx * 1.05, hock, lx * 1.05, -lift - 0.02, 0.046, 0.04);
      ctx.beginPath(); ctx.ellipse(lx * 1.05, -lift - 0.02, 0.055, 0.028, 0, 0, TAU); ctx.fill();
    }
  }
  ctx.save(); ctx.scale(1, breath);
  ctx.beginPath(); smoothPath(ctx, body); ctx.fill();
  if (sit > 0.5) { // fur on the haunches + hind paws peeking out
    for (const s of [-1, 1]) {
      for (let k = 0; k < 4; k++) {
        const y = -0.10 - k * 0.085, x = s * (0.428 - k * 0.012 - (k === 3 ? 0.03 : 0));
        ctx.beginPath(); ctx.moveTo(x - s * 0.035, y - 0.055); ctx.lineTo(x + s * 0.035, y + 0.012); ctx.lineTo(x - s * 0.025, y + 0.03); ctx.closePath(); ctx.fill();
      }
      ctx.beginPath(); ctx.ellipse(s * 0.30, -0.03, 0.10, 0.045, s * 0.15, 0, TAU); ctx.fill();
    }
  }
  ctx.restore();
  // tail
  {
    let sp, wd;
    if (sit > 0.5) {
      const sw = (P.sweep || 0) * 0.08;
      sp = [[0.12, -0.04], [0.32, -0.035 + sw * 0.3], [0.52, -0.035 + sw], [0.68, -0.07 + sw * 1.4]];
      wd = [0.055, 0.068, 0.062, 0.03];
    } else {
      const up = P.tail ?? 0, w = 0.06 * Math.sin(TAU * ph) * (amp + 0.3);
      sp = [[0, -0.93], [0.01 + w * 0.4, lerp(-0.78, -1.08, up)], [0.03 + w, lerp(-0.64, -1.20, up)], [0.05 + w * 1.5, lerp(-0.52, -1.28, up)]];
      wd = [0.06, 0.072, 0.066, 0.03];
    }
    for (let i = 0; i < sp.length - 1; i++) capsule(ctx, sp[i][0], sp[i][1], sp[i + 1][0], sp[i + 1][1], wd[i], wd[i + 1]);
    for (let i = 1; i < sp.length - 1; i++) { // feathering
      const p = sp[i], q = sp[i + 1], m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2], dx = q[0] - p[0], dy = q[1] - p[1], d = Math.hypot(dx, dy) || 1;
      const n = sit > 0.5 ? [0, -1] : [Math.sign(dx || 1), 0];
      ctx.beginPath(); ctx.moveTo(m[0] - dx / d * 0.05, m[1] - dy / d * 0.05); ctx.lineTo(m[0] + n[0] * 0.1 + dx / d * 0.04, m[1] + n[1] * 0.1 + dy / d * 0.04); ctx.lineTo(m[0] + dx / d * 0.06, m[1] + dy / d * 0.06); ctx.closePath(); ctx.fill();
    }
  }
  // head
  const hs = lerp(1, 0.86, st);
  const hy = lerp(-1.205, -1.30, st) + (P.headY || 0) + 0.015 * amp * Math.sin(2 * TAU * ph);
  ctx.save(); ctx.translate(0, hy); ctx.rotate(P.tilt || 0); ctx.scale(hs, hs);
  ctx.fillRect(-0.12, 0, 0.24, 0.17);
  ctx.beginPath(); ctx.ellipse(0, 0, 0.145, 0.135, 0, 0, TAU); ctx.fill();
  if (Math.abs(turn) > 0.02) {
    const s = Math.sign(turn), k = Math.abs(turn);
    ctx.beginPath(); ctx.ellipse(s * (0.08 + 0.10 * k), 0.035, 0.05 + 0.08 * k, 0.056, s * 0.1, 0, TAU); ctx.fill();
    ctx.beginPath(); ctx.arc(s * (0.10 + 0.17 * k), 0.03, 0.032, 0, TAU); ctx.fill();
  }
  const perk = P.perk || 0;
  for (const s of [-1, 1]) {
    ctx.save(); ctx.scale(s, 1); ctx.translate(0.09, -0.08); ctx.rotate(-perk * 0.3 + (s * turn > 0 ? -0.12 : 0.04));
    ctx.beginPath(); smoothPath(ctx, DB_EAR); ctx.fill();
    ctx.restore();
  }
  ctx.restore();
  ctx.restore();
  P.headXY = [P.x, P.y + P.s * hy];
  const ms = Math.sign(turn || 1);
  P.mouthXY = [P.x + P.s * hs * ms * (0.10 + 0.17 * Math.abs(turn)), P.y + P.s * (hy + 0.07 * hs)];
}

// sleeping puppy, curled up (local px units around its center)
function puppyCurled(ctx, x, y, s, breath) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  const b = 1 + 0.035 * breath;
  ctx.save(); ctx.scale(1, b);
  ctx.beginPath(); ctx.ellipse(0, -0.24, 0.62, 0.26, 0, 0, TAU); ctx.fill(); // body
  ctx.beginPath(); ctx.ellipse(-0.42, -0.38, 0.22, 0.2, -0.3, 0, TAU); ctx.fill(); // haunch
  ctx.restore();
  // head resting on front paws, facing left, nose tucked toward tail
  ctx.beginPath(); ctx.ellipse(0.46, -0.24, 0.24, 0.18, 0.15, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.ellipse(0.66, -0.15, 0.15, 0.09, 0.35, 0, TAU); ctx.fill(); // muzzle
  ctx.beginPath(); smoothPath(ctx, [[0.38, -0.36], [0.30, -0.30], [0.28, -0.12], [0.34, -0.04], [0.42, -0.12], [0.44, -0.30]]); ctx.fill(); // ear
  ctx.beginPath(); ctx.ellipse(0.55, -0.03, 0.2, 0.05, 0, 0, TAU); ctx.fill(); // paws
  // tail curled around front
  capsule(ctx, -0.55, -0.12, -0.2, -0.02, 0.07, 0.05);
  capsule(ctx, -0.2, -0.02, 0.15, -0.02, 0.05, 0.03);
  ctx.restore();
}

// ---------- people. Units: meters, ground y = 0.
function headShape(ctx, x, y, r, hair = 'short', ang = 0) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
  ctx.beginPath(); ctx.ellipse(0, 0, r * 0.88, r, 0, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.ellipse(r * 0.55, r * 0.15, r * 0.35, r * 0.3, 0, 0, TAU); ctx.fill(); // nose/face front
  if (hair === 'short') { ctx.beginPath(); ctx.ellipse(-r * 0.1, -r * 0.35, r * 0.95, r * 0.75, -0.2, PI, TAU); ctx.fill(); }
  ctx.restore();
}

function dadSitting(ctx, P) {
  const br = Math.sin((P.t || 0) * 1.6) * 0.012 + (P.sigh || 0) * 0.03;
  ctx.save(); ctx.translate(P.x, P.y); ctx.scale(P.s, P.s);
  // chair
  capsule(ctx, -0.24, -0.47, -0.27, -1.0, 0.025, 0.025);
  ctx.fillRect(-0.26, -0.49, 0.5, 0.045);
  capsule(ctx, -0.22, -0.47, -0.24, 0, 0.02, 0.02); capsule(ctx, 0.2, -0.47, 0.22, 0, 0.02, 0.02);
  // legs
  capsule(ctx, 0.0, -0.55, 0.46, -0.55, 0.085, 0.065);
  capsule(ctx, 0.46, -0.55, 0.47, -0.06, 0.06, 0.045);
  ctx.beginPath(); ctx.ellipse(0.52, -0.035, 0.12, 0.04, 0, 0, TAU); ctx.fill();
  // torso leaning forward
  ctx.beginPath(); smoothPath(ctx, [[-0.11, -0.52], [-0.08, -0.80], [0.03, -1.02 - br], [0.17, -1.13 - br], [0.30, -1.08 - br], [0.34, -0.92], [0.23, -0.66], [0.13, -0.50]]); ctx.fill();
  // head bowed into hands
  headShape(ctx, 0.37, -1.10 - br * 0.6, 0.115, 'short', 0.75);
  // arms: shoulder -> elbow on table -> hands at head
  capsule(ctx, 0.17, -1.07 - br, 0.52, -0.80, 0.065, 0.05);
  capsule(ctx, 0.52, -0.80, 0.45, -1.06 - br * 0.6, 0.048, 0.05);
  ctx.beginPath(); ctx.ellipse(0.44, -1.07 - br * 0.6, 0.06, 0.08, 0.4, 0, TAU); ctx.fill();
  ctx.restore();
}

// throwing pose; u in [0,1]. returns hand position (screen)
function dadThrow(ctx, P) {
  const u = P.u || 0;
  const K = [[0, 85, 95, 0], [0.42, 215, 250, -0.10], [0.6, 300, 318, 0.10], [0.78, 15, 35, 0.12], [1, 84, 94, 0.02]];
  let i = 0; while (i < K.length - 2 && u > K[i + 1][0]) i++;
  const k = ease.sine(inv(K[i][0], K[i + 1][0], u));
  const a1 = lerp(K[i][1], K[i + 1][1], k) * PI / 180, a2 = lerp(K[i][2], K[i + 1][2], k) * PI / 180, lean = lerp(K[i][3], K[i + 1][3], k);
  ctx.save(); ctx.translate(P.x, P.y); ctx.scale(P.s * (P.face || 1), P.s);
  // legs
  capsule(ctx, -0.04, -0.95, -0.22, -0.5, 0.09, 0.07); capsule(ctx, -0.22, -0.5, -0.3, -0.05, 0.07, 0.05);
  capsule(ctx, 0.04, -0.95, 0.2, -0.5, 0.09, 0.07); capsule(ctx, 0.2, -0.5, 0.26, -0.05, 0.07, 0.05);
  ctx.beginPath(); ctx.ellipse(-0.27, -0.035, 0.12, 0.04, 0, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.ellipse(0.31, -0.035, 0.12, 0.04, 0, 0, TAU); ctx.fill();
  ctx.save(); ctx.translate(0, -0.95); ctx.rotate(lean);
  // far arm swings opposite
  const fa = (lerp(110, 60, k) + (u > 0.5 ? -40 : 30)) * PI / 180;
  const fe = [0.0 + Math.cos(fa) * 0.3, -0.48 + Math.sin(fa) * 0.3];
  capsule(ctx, 0.0, -0.48, fe[0], fe[1], 0.06, 0.05); capsule(ctx, fe[0], fe[1], fe[0] + Math.cos(fa + 0.3) * 0.27, fe[1] + Math.sin(fa + 0.3) * 0.27, 0.05, 0.045);
  // torso
  ctx.beginPath(); smoothPath(ctx, [[-0.13, 0.02], [-0.15, -0.25], [-0.13, -0.47], [-0.02, -0.56], [0.11, -0.52], [0.16, -0.3], [0.13, -0.02]]); ctx.fill();
  headShape(ctx, 0.03, -0.70, 0.115, 'short', lean * 0.5);
  capsule(ctx, 0.0, -0.58, 0.03, -0.6, 0.05, 0.05);
  // throwing arm
  const sh = [0.02, -0.48], el = [sh[0] + Math.cos(a1) * 0.30, sh[1] + Math.sin(a1) * 0.30], ha = [el[0] + Math.cos(a2) * 0.28, el[1] + Math.sin(a2) * 0.28];
  capsule(ctx, sh[0], sh[1], el[0], el[1], 0.065, 0.05); capsule(ctx, el[0], el[1], ha[0], ha[1], 0.05, 0.045);
  ctx.beginPath(); ctx.arc(ha[0], ha[1], 0.055, 0, TAU); ctx.fill();
  ctx.restore();
  ctx.restore();
  // hand in screen coords
  const hl = rot(ha, lean); const hx = hl[0], hy = hl[1] - 0.95;
  return [P.x + (P.face || 1) * P.s * hx, P.y + P.s * hy];
}

// adult walking, side view, facing +x
function dadWalk(ctx, P) {
  const ph = P.phase || 0, sw = Math.sin(TAU * ph), amp = P.amp ?? 1;
  const bob = Math.abs(Math.cos(TAU * ph)) * 0.025 * amp;
  ctx.save(); ctx.translate(P.x, P.y - bob * P.s); ctx.scale(P.s * (P.face || 1), P.s);
  const hip = [0, -0.95];
  for (const s of [-1, 1]) {
    const a = PI / 2 + s * sw * 0.36 * amp;
    const knee = [hip[0] + Math.cos(a) * 0.46, hip[1] + Math.sin(a) * 0.46];
    const a2 = a + Math.max(0, -s * Math.cos(TAU * ph)) * 0.55 * amp;
    const foot = [knee[0] + Math.cos(a2) * 0.45, knee[1] + Math.sin(a2) * 0.45];
    capsule(ctx, hip[0], hip[1], knee[0], knee[1], 0.085, 0.065); capsule(ctx, knee[0], knee[1], foot[0], foot[1], 0.062, 0.048);
    ctx.beginPath(); ctx.ellipse(foot[0] + 0.06, foot[1] - 0.01, 0.12, 0.04, 0, 0, TAU); ctx.fill();
  }
  ctx.beginPath(); smoothPath(ctx, [[-0.13, -0.93], [-0.15, -1.2], [-0.13, -1.42], [-0.02, -1.51], [0.11, -1.47], [0.16, -1.25], [0.13, -0.93]]); ctx.fill();
  capsule(ctx, 0, -1.5, 0.02, -1.56, 0.05, 0.05);
  headShape(ctx, 0.03, -1.65, 0.115, 'short', P.headTilt ?? 0.12);
  for (const s of [-1, 1]) {
    const a = PI / 2 - s * sw * 0.42 * amp, el = [Math.cos(a) * 0.3, -1.43 + Math.sin(a) * 0.3], a2 = a - 0.25;
    capsule(ctx, 0, -1.43, el[0], el[1], 0.06, 0.05); capsule(ctx, el[0], el[1], el[0] + Math.cos(a2) * 0.28, el[1] + Math.sin(a2) * 0.28, 0.05, 0.045);
  }
  ctx.restore();
}

// girl walking, side view, facing +x
function lilyWalk(ctx, P) {
  const ph = P.phase || 0, sw = Math.sin(TAU * ph), bob = Math.abs(Math.cos(TAU * ph)) * 0.02;
  ctx.save(); ctx.translate(P.x, P.y - bob * P.s); ctx.scale(P.s * (P.face || 1), P.s);
  const hip = [0, -0.62];
  for (const s of [-1, 1]) {
    const a = PI / 2 + s * sw * 0.42;
    const knee = [hip[0] + Math.cos(a) * 0.3, hip[1] + Math.sin(a) * 0.3];
    const a2 = a + Math.max(0, -s * Math.cos(TAU * ph)) * 0.5;
    const foot = [knee[0] + Math.cos(a2) * 0.29, knee[1] + Math.sin(a2) * 0.29];
    capsule(ctx, hip[0], hip[1], knee[0], knee[1], 0.055, 0.045); capsule(ctx, knee[0], knee[1], foot[0], foot[1], 0.042, 0.035);
    ctx.beginPath(); ctx.ellipse(foot[0] + 0.04, foot[1] + 0.005, 0.075, 0.03, 0, 0, TAU); ctx.fill();
  }
  // skirt/dress
  ctx.beginPath(); smoothPath(ctx, [[-0.1, -0.62], [-0.16, -0.5], [0.0, -0.47 + sw * 0.01], [0.17, -0.5], [0.1, -0.64], [0.09, -0.92], [-0.08, -0.92]]); ctx.fill();
  // backpack
  ctx.beginPath(); ctx.roundRect(-0.25, -0.98, 0.17, 0.3, 0.05); ctx.fill();
  // arms
  for (const s of [-1, 1]) { const a = PI / 2 - s * sw * 0.5; capsule(ctx, 0.0, -0.88, Math.cos(a) * 0.36, -0.88 + Math.sin(a) * 0.36, 0.04, 0.035); }
  // head + pigtails
  headShape(ctx, 0.02, -1.06, 0.105, 'none', 0.02);
  ctx.beginPath(); ctx.ellipse(-0.02, -1.11, 0.1, 0.08, -0.2, PI, TAU); ctx.fill();
  const pt = 0.05 * Math.sin(TAU * ph * 2 + 1);
  capsule(ctx, -0.08, -1.08, -0.17, -0.96 + pt, 0.035, 0.03);
  ctx.beginPath(); ctx.ellipse(-0.18, -0.93 + pt, 0.04, 0.06, 0.3, 0, TAU); ctx.fill();
  ctx.restore();
}

// Dad and Lily seen from outside through a window (front view). x,y = window sill center
const BUST = [[0, 0.05], [0.30, 0.05], [0.30, -0.30], [0.275, -0.44], [0.20, -0.52], [0.11, -0.56], [0.066, -0.60], [0.06, -0.66], [0.082, -0.72], [0.094, -0.80], [0.086, -0.88], [0.052, -0.935], [0, -0.945]];
function windowFamily(ctx, P) {
  ctx.save(); ctx.translate(P.x, P.y); ctx.scale(P.s, P.s);
  const br = Math.sin((P.t || 0) * 1.5) * 0.006;
  // Dad behind, left, head bowed a little
  ctx.save(); ctx.translate(-0.17, 0); ctx.scale(1, 1 + br);
  ctx.beginPath(); smoothPath(ctx, mirrorHalf(BUST)); ctx.fill();
  ctx.beginPath(); ctx.ellipse(-0.098, -0.79, 0.02, 0.035, 0, 0, TAU); ctx.fill(); ctx.beginPath(); ctx.ellipse(0.098, -0.79, 0.02, 0.035, 0, 0, TAU); ctx.fill();
  capsule(ctx, 0.25, -0.46, 0.36, -0.36, 0.05, 0.045); // arm reaching to her shoulder
  ctx.restore();
  // Lily in front, right
  ctx.save(); ctx.translate(0.2, 0.02); ctx.scale(0.66, 0.66);
  ctx.beginPath(); smoothPath(ctx, mirrorHalf(BUST.map(([x, y]) => [x * (y < -0.6 ? 1.15 : 0.9), y]))); ctx.fill();
  for (const sd of [-1, 1]) { // braids
    capsule(ctx, sd * 0.09, -0.74, sd * 0.13, -0.56, 0.035, 0.03);
    capsule(ctx, sd * 0.13, -0.56, sd * 0.14, -0.45, 0.03, 0.022);
    ctx.beginPath(); ctx.ellipse(sd * 0.145, -0.43, 0.028, 0.02, 0, 0, TAU); ctx.fill();
  }
  // hand raised to the glass
  const hr = P.hand ?? 1;
  const hand = [lerp(0.26, 0.24, hr), lerp(-0.2, -0.86, hr)];
  capsule(ctx, 0.22, -0.42, hand[0], hand[1] + 0.06, 0.05, 0.042);
  ctx.beginPath(); ctx.ellipse(hand[0], hand[1], 0.055, 0.07, 0, 0, TAU); ctx.fill();
  for (let k = 0; k < 4; k++) capsule(ctx, hand[0] - 0.04 + k * 0.027, hand[1] - 0.04, hand[0] - 0.05 + k * 0.033, hand[1] - 0.12 + Math.abs(k - 1.5) * 0.015, 0.014, 0.012);
  capsule(ctx, hand[0] + 0.05, hand[1] + 0.01, hand[0] + 0.1, hand[1] - 0.04, 0.016, 0.013);
  ctx.restore();
  ctx.restore();
}

// ---------- vehicles. Units: meters, ground y = 0, facing +x. Origin at car center.
const CAR_TOP = [[-2.21, -0.40], [-2.25, -0.72], [-2.17, -1.06], [-1.93, -1.43], [-0.70, -1.51], [0.22, -1.48], [0.78, -1.10], [1.85, -0.99], [2.18, -0.86], [2.23, -0.55], [2.19, -0.37]];
function carBody(ctx) {
  ctx.beginPath();
  smoothPath(ctx, CAR_TOP, false, 1 / 8);
  ctx.lineTo(1.82, -0.33);
  ctx.arc(1.42, -0.36, 0.42, 0, PI, true);
  ctx.lineTo(-0.95, -0.33);
  ctx.arc(-1.36, -0.36, 0.42, 0, PI, true);
  ctx.lineTo(-2.21, -0.40);
  ctx.closePath(); ctx.fill();
  ctx.fillRect(-2.0, -0.42, 4.0, 0.12);
}
function carWheels(ctx) {
  for (const wx of [-1.36, 1.42]) { ctx.beginPath(); ctx.arc(wx, -0.34, 0.34, 0, TAU); ctx.fill(); }
}
const CAR_WIN_R = [[-1.88, -1.36], [-0.78, -1.43], [-0.78, -1.06], [-2.02, -1.06]];
const CAR_WIN_F = [[-0.64, -1.43], [0.16, -1.41], [0.62, -1.08], [-0.64, -1.06]];
function carSide(P) {
  // P: x,y,s,face, glass:[stops], rim, lightsOn, tail, head, wheelRot
  X.save(); X.translate(P.x, P.y); X.scale(P.s * (P.face || 1), P.s);
  silhouette(ctx => { carBody(ctx); carWheels(ctx); }, { rim: P.rim });
  // glass
  if (P.glass) {
    for (const wpts of [CAR_WIN_R, CAR_WIN_F]) {
      X.save(); X.beginPath(); polyPath(X, wpts); X.clip();
      X.fillStyle = vgrad(X, -1.45, -1.05, P.glass); X.fillRect(-2.2, -1.6, 4.4, 0.7);
      // reflection streak
      X.globalCompositeOperation = 'lighter';
      X.fillStyle = css([255, 230, 200], 0.08); X.beginPath(); X.moveTo(-1.2, -1.5); X.lineTo(-0.9, -1.5); X.lineTo(-1.25, -1.0); X.lineTo(-1.55, -1.0); X.fill();
      X.restore();
    }
    // interior: headrests + Dad
    X.fillStyle = css(INK, 0.92);
    X.beginPath(); X.ellipse(-1.25, -1.17, 0.09, 0.12, 0, 0, TAU); X.fill();
    headShape(X, -0.05, -1.22, 0.115, 'short', 0.05);
    X.fillRect(-0.22, -1.12, 0.3, 0.1);
  }
  // wheel hubs
  X.strokeStyle = css(P.hubCol || [90, 80, 80], 0.5); X.lineWidth = 0.025;
  for (const wx of [-1.36, 1.42]) {
    X.beginPath(); X.arc(wx, -0.34, 0.2, 0, TAU); X.stroke();
    for (let k = 0; k < 5; k++) { const a = (P.wheelRot || 0) + k * TAU / 5; X.beginPath(); X.moveTo(wx + Math.cos(a) * 0.05, -0.34 + Math.sin(a) * 0.05); X.lineTo(wx + Math.cos(a) * 0.18, -0.34 + Math.sin(a) * 0.18); X.stroke(); }
  }
  if (P.lights) {
    const tl = P.lights.tail ?? 0, hl = P.lights.head ?? 0;
    if (tl > 0) { X.fillStyle = css([255, 40, 30], 0.9 * tl); X.fillRect(-2.25, -1.0, 0.08, 0.2); light(-2.24, -0.9, 0.9, [255, 40, 25], 0.55 * tl, 1.2); }
    if (hl > 0) { X.fillStyle = css([255, 245, 220], hl); X.fillRect(2.13, -0.82, 0.09, 0.14); light(2.2, -0.75, 1.2, [255, 235, 200], 0.6 * hl, 1.2); }
  }
  X.restore();
}
// receding car seen from behind (small), x,y = ground center
function carRear(x, y, s, tail = 1, body = 1) {
  X.save(); X.translate(x, y); X.scale(s, s);
  if (body > 0) {
    X.fillStyle = css(INK, body);
    X.beginPath(); smoothPath(X, [[-0.95, -0.25], [-0.98, -0.75], [-0.75, -1.38], [0.75, -1.38], [0.98, -0.75], [0.95, -0.25]], true, 1 / 10); X.fill();
    X.fillRect(-0.9, -0.3, 0.3, 0.3); X.fillRect(0.6, -0.3, 0.3, 0.3);
  }
  X.restore();
  if (tail > 0) {
    for (const sx of [-0.8, 0.8]) {
      const lx = x + sx * s, ly = y - 0.85 * s;
      X.fillStyle = css([255, 50, 35], tail); X.beginPath(); X.ellipse(lx, ly, 0.13 * s + 1, 0.08 * s + 1, 0, 0, TAU); X.fill();
      light(lx, ly, 2.6 * s + 22, [255, 40, 25], 0.7 * tail, 1.4);
    }
  }
}
function busSide(P) {
  X.save(); X.translate(P.x, P.y); X.scale(P.s * (P.face || 1), P.s);
  silhouette(ctx => {
    ctx.beginPath(); ctx.roundRect(-5.2, -3.1, 8.4, 2.75, 0.18); ctx.fill();
    ctx.beginPath(); smoothPath(ctx, [[3.1, -2.2], [4.3, -2.0], [4.6, -1.6], [4.6, -0.5], [3.1, -0.4]], true, 1 / 10); ctx.fill();
    ctx.fillRect(-5.2, -0.6, 9.8, 0.3);
    for (const wx of [-3.6, 2.6]) { ctx.beginPath(); ctx.arc(wx, -0.48, 0.48, 0, TAU); ctx.fill(); }
  }, { rim: P.rim });
  // windows glowing with low sun shining through the bus
  for (let i = 0; i < 9; i++) {
    const wx = -4.9 + i * 0.86;
    X.fillStyle = css(P.winCol || [255, 196, 120], P.winA ?? 0.85);
    X.beginPath(); X.roundRect(wx, -2.85, 0.68, 0.78, 0.06); X.fill();
  }
  if (P.winA) emit(e => { e.fillStyle = css(P.winCol || [255, 196, 120], 0.5); e.fillRect(-4.9, -2.85, 7.6, 0.78); });
  X.restore();
}
