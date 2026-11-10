// ============================================================================
// Kâğıt malzemesi: deterministik doku, kesik kenar, katman gölgesi, yazı, etiket.
// Her şey zamana göre (seek) çizilir; hiçbir şey önceki kareye bağlı değildir.
// ============================================================================
const P = {
  cream: "#F3EBDD", charcoal: "#243139", terra: "#C56B50", mustard: "#E8B65C",
  sage: "#8A9B7C", blue: "#7C9DA5", card: "#FFF8EB",
  red: "#B71F2E",          // kanal kırmızısı (kravat): vurgu, bant, önemli rakam
  ink: "#1E2529", sky: "#F1D9A6", night: "#2E3B45",
};

// ---------- iyi karışan rastgele (splitmix32 tarzı) ----------
function hash(n) {
  n = (n + 0x9e3779b9) | 0;
  n = Math.imul(n ^ (n >>> 16), 0x85ebca6b);
  n = Math.imul(n ^ (n >>> 13), 0xc2b2ae35);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
}
function rnd(seed, i) { return hash(Math.imul(seed | 0, 0x27d4eb2d) ^ Math.floor(hash(i | 0) * 4294967296)); }
function strSeed(s) { let h = 7; for (const c of String(s)) h = (Math.imul(h, 31) + c.charCodeAt(0)) | 0; return h; }
function vnoise(seed, x) {
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return rnd(seed, i) * (1 - u) + rnd(seed, i + 1) * u;
}

// ---------- kâğıt dokusu (bir kez üretilir) ----------
function makeGrain(size, seed) {
  const c = document.createElement("canvas"); c.width = c.height = size;
  const g = c.getContext("2d"), img = g.createImageData(size, size), d = img.data;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const k = y * size + x;
    const fine = rnd(seed, k) - 0.5;
    const blot = vnoise(seed + 7, x / 23 + Math.floor(y / 19) * 31.7) - 0.5;
    const v = 238 + fine * 24 + blot * 14;
    d[k * 4] = v; d[k * 4 + 1] = v - 2; d[k * 4 + 2] = v - 6; d[k * 4 + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  for (let i = 0; i < size * 1.4; i++) {   // lifler
    const x = rnd(seed + 1, i) * size, y = rnd(seed + 2, i) * size;
    const a = rnd(seed + 3, i) * Math.PI, L = 6 + rnd(seed + 4, i) * 18;
    g.strokeStyle = rnd(seed + 5, i) > 0.5 ? "rgba(255,255,255,0.35)" : "rgba(120,100,80,0.18)";
    g.lineWidth = 0.6 + rnd(seed + 6, i) * 0.6;
    g.beginPath(); g.moveTo(x, y);
    g.quadraticCurveTo(x + Math.cos(a + 0.4) * L / 2, y + Math.sin(a + 0.4) * L / 2, x + Math.cos(a) * L, y + Math.sin(a) * L);
    g.stroke();
  }
  return c;
}
let GRAIN, GRAIN_PAT;

// ---------- kesik kenar (önbellekli) ----------
const _edge = new Map();
function roughen(id, pts, amp = 2.2, step = 9) {
  // anahtar şeklin boyutunu da içerir: büyüyen/küçülen şekiller (çubuk, şerit) yeniden hesaplanır
  let mnx = 1e9, mny = 1e9, mxx = -1e9, mxy = -1e9;
  for (const q of pts) { if (q[0] < mnx) mnx = q[0]; if (q[0] > mxx) mxx = q[0]; if (q[1] < mny) mny = q[1]; if (q[1] > mxy) mxy = q[1]; }
  const key = id + "|" + pts.length + "|" + amp + "|" + Math.round(mnx / 2) + "," + Math.round(mny / 2) + "," + Math.round(mxx / 2) + "," + Math.round(mxy / 2);
  if (_edge.size > 40000) _edge.clear();
  const hit = _edge.get(key); if (hit) return hit;
  const out = [], seed = strSeed(id); let s = 0;
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i], b = pts[(i + 1) % pts.length];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.round(len / step));
    const nx = -(b[1] - a[1]) / (len || 1), ny = (b[0] - a[0]) / (len || 1);
    for (let j = 0; j < n; j++) {
      const t = j / n; s++;
      const off = (vnoise(seed, s / 3.1) - 0.5) * amp * 2 + (rnd(seed, s) - 0.5) * amp * 0.6;
      out.push([a[0] + (b[0] - a[0]) * t + nx * off, a[1] + (b[1] - a[1]) * t + ny * off]);
    }
  }
  const path = new Path2D(); out.forEach((p, i) => i ? path.lineTo(p[0], p[1]) : path.moveTo(p[0], p[1])); path.closePath();
  const r = { pts: out, path }; _edge.set(key, r); return r;
}

const shapes = {
  rect: (w, h) => [[0, 0], [w, 0], [w, h], [0, h]],
  crect: (w, h) => [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]],
  circle: (r, n = 56) => Array.from({ length: n }, (_, i) => [Math.cos(i / n * 2 * Math.PI) * r, Math.sin(i / n * 2 * Math.PI) * r]),
  ellipse: (rx, ry, n = 56) => Array.from({ length: n }, (_, i) => [Math.cos(i / n * 2 * Math.PI) * rx, Math.sin(i / n * 2 * Math.PI) * ry]),
  arc: (r, a0, a1, n = 30) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return [Math.cos(a) * r, Math.sin(a) * r]; }),
  round: (w, h, r, n = 6) => { // köşeleri yuvarlatılmış dikdörtgen (merkezli)
    const pts = [], c = [[w / 2 - r, -h / 2 + r, -Math.PI / 2], [w / 2 - r, h / 2 - r, 0], [-w / 2 + r, h / 2 - r, Math.PI / 2], [-w / 2 + r, -h / 2 + r, Math.PI]];
    for (const [cx, cy, a0] of c) for (let i = 0; i <= n; i++) { const a = a0 + i / n * Math.PI / 2; pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); }
    return pts;
  },
  star: (r1, r2, k = 5) => Array.from({ length: k * 2 }, (_, i) => { const r = i % 2 ? r2 : r1, a = -Math.PI / 2 + i * Math.PI / k; return [Math.cos(a) * r, Math.sin(a) * r]; }),
  tri: (w, h) => [[0, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]],
};

function shade(hex, k) { // k<0 koyulaştır, k>0 aç
  if (hex[0] !== "#") return hex;
  const n = parseInt(hex.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  const f = v => Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k);
  return `rgb(${f(r)},${f(g)},${f(b)})`;
}

// ---------- tek kâğıt parçası ----------
// o: {x,y,rot,scale,sx,sy,alpha,depth(0-3),edge,amp,tex}
function piece(ctx, id, pts, color, o = {}) {
  const a = o.alpha ?? 1;
  if (a <= 0.003) return;
  const { path } = roughen(id, pts, o.amp ?? 2.2, o.step ?? 9);
  const depth = o.depth ?? 1;
  ctx.save();
  ctx.translate(o.x || 0, o.y || 0); if (o.rot) ctx.rotate(o.rot);
  const sc = o.scale ?? 1; ctx.scale(sc * (o.sx ?? 1), sc * (o.sy ?? 1));
  ctx.globalAlpha *= a;
  if (depth > 0) {
    ctx.save();
    const k = 1 / Math.max(0.2, sc);
    ctx.shadowColor = `rgba(70,45,25,${0.2 + depth * 0.06})`;
    ctx.shadowBlur = (3 + depth * 6) * sc; ctx.shadowOffsetX = (1.5 + depth * 2.2) * sc; ctx.shadowOffsetY = (2.5 + depth * 3) * sc;
    ctx.fillStyle = color; ctx.fill(path); ctx.restore();
  }
  if (o.edge !== false) {
    const k = 1 / Math.max(0.3, sc);
    ctx.save(); ctx.translate(1.1 * k, 1.5 * k); ctx.fillStyle = shade(color, -0.2); ctx.fill(path); ctx.restore();
    ctx.save(); ctx.translate(-0.7 * k, -0.7 * k); ctx.fillStyle = shade(color, 0.25); ctx.fill(path); ctx.restore();
  }
  ctx.fillStyle = color; ctx.fill(path);
  if (o.tex !== false) {
    ctx.save(); ctx.clip(path);
    ctx.globalCompositeOperation = "multiply"; ctx.globalAlpha *= 0.55;
    ctx.fillStyle = GRAIN_PAT; ctx.fill(path);
    ctx.restore();
  }
  ctx.restore();
}

// çizgi (ip, kesikli bağlantı, ok)
function line(ctx, pts, color = P.charcoal, w = 3, dash = null, prog = 1) {
  if (prog <= 0 || pts.length < 2) return;
  let total = 0; const seg = [];
  for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
  let left = total * Math.min(1, prog);
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round";
  if (dash) ctx.setLineDash(dash);
  ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length && left > 0; i++) {
    const k = Math.min(1, left / seg[i - 1]);
    ctx.lineTo(pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k);
    left -= seg[i - 1];
  }
  ctx.stroke(); ctx.restore();
}
function pointAlong(pts, prog) {
  let total = 0; const seg = [];
  for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
  let left = total * Math.max(0, Math.min(1, prog));
  for (let i = 1; i < pts.length; i++) {
    if (left <= seg[i - 1]) { const k = left / seg[i - 1]; return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k, Math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0])]; }
    left -= seg[i - 1];
  }
  const n = pts.length - 1; return [pts[n][0], pts[n][1], Math.atan2(pts[n][1] - pts[n - 1][1], pts[n][0] - pts[n - 1][0])];
}

// ---------- yazı ----------
const FONTS = { head: "Archivo", bold: "InterB", semi: "InterS" };
const upTR = s => String(s).toLocaleUpperCase("tr-TR");
function setFont(ctx, size, font) { ctx.font = `${size}px ${FONTS[font] || font}`; }
function textW(ctx, s, size, font = "head") { ctx.save(); setFont(ctx, size, font); const w = ctx.measureText(s).width; ctx.restore(); return w; }
function wrap(ctx, s, size, font, maxW, maxLines = 3) {
  const words = String(s).split(/\s+/).filter(Boolean), lines = []; let cur = "";
  for (const w of words) {
    const t = cur ? cur + " " + w : w;
    if (!cur || textW(ctx, t, size, font) <= maxW) cur = t; else { lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  return lines.slice(0, maxLines);
}
// sığdır: kutuya sığana kadar puntoyu küçült
function fit(ctx, s, size, font, maxW, maxLines = 2, minSize = 22) {
  let z = size, lines;
  while (true) {
    lines = wrap(ctx, s, z, font, maxW, 99);
    if ((lines.length <= maxLines && lines.every(l => textW(ctx, l, z, font) <= maxW)) || z <= minSize) break;
    z = Math.max(minSize, Math.round(z * 0.92));
  }
  return { size: z, lines: lines.slice(0, maxLines) };
}
function txt(ctx, s, x, y, size, color, font = "head", align = "left", reveal = 1) {
  if (reveal <= 0) return;
  ctx.save(); setFont(ctx, size, font); ctx.textAlign = align; ctx.textBaseline = "alphabetic"; ctx.fillStyle = color;
  if (reveal < 1) {
    const w = ctx.measureText(s).width, x0 = align === "center" ? x - w / 2 : align === "right" ? x - w : x;
    ctx.beginPath(); ctx.rect(x0 - 6, y - size * 1.15, (w + 12) * reveal, size * 1.6); ctx.clip();
  }
  ctx.fillText(s, x, y); ctx.restore();
}

// ---------- kâğıt etiket (kart + yazı, çok satırlı) ----------
// o: {font, pad, from:'left'|'right'|'up'|'down', rot, depth, maxW, align:'left'|'center', anchor:'tl'|'c'}
function label(ctx, id, s, x, y, size, bg, fg, inP, o = {}) {
  if (inP <= 0 || !s) return null;
  const font = o.font || "head";
  const f = fit(ctx, s, size, font, (o.maxW || 1600) - 2 * (o.pad ?? size * 0.45), o.lines || 2, Math.round(size * 0.55));
  const pad = o.pad ?? f.size * 0.45, lh = f.size * 1.18;
  const w = Math.max(...f.lines.map(l => textW(ctx, l, f.size, font))) + pad * 2;
  const h = lh * f.lines.length + pad * 0.9;
  let bx = x, by = y;
  if (o.anchor === "c") { bx = x - w / 2; by = y - h / 2; }
  else if (o.anchor === "tc") { bx = x - w / 2; }
  else if (o.anchor === "tr") { bx = x - w; }
  const e = ease.outBack(Math.min(1, inP));
  const from = o.from || "right", D = o.dist ?? 110;
  const dx = (1 - e) * (from === "left" ? -D : from === "right" ? D : 0);
  const dy = (1 - e) * (from === "up" ? -D : from === "down" ? D : 14);
  const rot = (o.rot ?? -0.012) + (1 - e) * 0.07;
  ctx.save(); ctx.translate(bx + dx + w / 2, by + dy + h / 2); ctx.rotate(rot);
  piece(ctx, "lbl-" + id + "-" + Math.round(w) + "x" + Math.round(h), shapes.rect(w, h), bg, { x: -w / 2, y: -h / 2, depth: o.depth ?? 2, alpha: Math.min(1, inP * 3), amp: 1.5 });
  const rv = Math.min(1, Math.max(0, (inP - 0.2) / 0.6));
  f.lines.forEach((l, i) => {
    const tx = o.align === "center" ? 0 : -w / 2 + pad;
    txt(ctx, l, tx, -h / 2 + pad * 0.45 + lh * (i + 1) - f.size * 0.2, f.size, fg, font, o.align === "center" ? "center" : "left", rv);
  });
  if (o.tape) tape(ctx, "tp-" + id, -w / 2 + 10, -h / 2 - 8, -0.5, Math.min(1, inP * 2));
  ctx.restore();
  return { x: bx, y: by, w, h };
}

// kırmızı bant parçası
function tape(ctx, id, x, y, rot, a = 1, len = 110) {
  piece(ctx, id, shapes.rect(len, 30), P.red, { x, y, rot, alpha: a * 0.88, depth: 0, edge: false, amp: 2.6, step: 6 });
}

// ---------- zaman yardımcıları ----------
const ease = {
  clamp: t => Math.max(0, Math.min(1, t)),
  inOut: t => (t = Math.max(0, Math.min(1, t)), t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  out: t => 1 - Math.pow(1 - Math.max(0, Math.min(1, t)), 3),
  in: t => Math.pow(Math.max(0, Math.min(1, t)), 2.2),
  outBack: t => { t = Math.max(0, Math.min(1, t)); const c = 1.35; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); },
  settle: t => { t = Math.max(0, Math.min(1, t)); return 1 - Math.exp(-6 * t) * Math.cos(7 * t); },
};
const win = (t, a, b) => ease.clamp((t - a) / (b - a));
// stop-motion vurgusu: kâğıt parçalarının saniyede 12 kez minik oynaması
const jig = (t, id, amt = 0.004) => (rnd(strSeed(String(id)), Math.floor(t * 12)) - 0.5) * amt;
const lerp = (a, b, k) => a + (b - a) * k;

// sayı biçimi (Türkçe)
function fmtNum(v, dec = 0) {
  const s = Math.abs(v).toFixed(dec).split(".");
  s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (v < 0 ? "−" : "") + s.join(",");
}
