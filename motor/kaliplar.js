// ============================================================================
// Sahne kalıpları. Her kalıp: (ctx, S) => çizer.
// S = {W,H,dikey, ts: sahne içi saniye, d: sahne süresi, t: genel saniye, p: parametreler,
//      id, kapak: true ise yazılar gizlenir (kapak görseli için), A: içerik alanı}
// Alt şerit (altyazı) için içerik alanının altı boş bırakılır.
// ============================================================================

function area(S) {
  return S.dikey ? { x0: 70, x1: 1010, y0: 480, y1: 1380, cx: 540, cy: 930 }
                 : { x0: 110, x1: 1810, y0: 80, y1: 860, cx: 960, cy: 470 };
}
// saniye tabanlı giriş, kısa sahnelerde sıkıştırılır
function E(S, a, b) { const k = Math.min(1, S.d / 6); return win(S.ts, a * k, b * k); }
// sahne süresinin oranı
function F(S, a, b) { return win(S.ts / S.d, a, b); }
const num = v => { const n = typeof v === "number" ? v : parseFloat(String(v).replace(/\./g, "").replace(",", ".").replace(/[^\d.\-]/g, "")); return isFinite(n) ? n : null; };
const decOf = v => { const s = String(v); const m = s.match(/[.,](\d+)$/); return typeof v === "number" ? (String(v).split(".")[1] || "").length : (m && s.split(/[.,]/).length === 2 && m[1].length < 3 ? m[1].length : 0); };

function headline(ctx, S, s, inP, o = {}) {
  if (!s || S.kapak) return null;
  const A = S.A;
  return label(ctx, S.id + "h", upTR(s), o.x ?? A.x0, o.y ?? A.y0, o.size ?? (S.dikey ? 66 : 92), o.bg || P.card, o.fg || P.charcoal, inP,
    { from: o.from || "left", maxW: o.maxW ?? (S.dikey ? 940 : 1100), lines: 2, rot: o.rot ?? -0.015, tape: o.tape ?? true, anchor: o.anchor });
}
function headBox(ctx, S, s) {
  if (!s) return null;
  const size = S.dikey ? 66 : 92, f = fit(ctx, upTR(s), size, "head", (S.dikey ? 940 : 1100) - 2 * size * 0.45, 2, Math.round(size * 0.55));
  return { x: S.A.x0, y: S.A.y0, w: 0, h: f.size * 1.18 * f.lines.length + f.size * 0.45 * 0.9 };
}
function sub(ctx, S, s, x, y, inP, o = {}) {
  if (!s || S.kapak) return null;
  return label(ctx, S.id + "s" + (o.k || ""), s, x, y, o.size ?? (S.dikey ? 44 : 40), o.bg || P.red, o.fg || P.card, inP,
    { font: "bold", maxW: o.maxW ?? (S.dikey ? 920 : 900), lines: o.lines ?? 2, from: o.from || "right", rot: o.rot ?? 0.01, anchor: o.anchor, depth: 2 });
}

const KALIP = {
  // ---------------------------------------------------------------- başlık
  baslik(ctx, S) {
    const A = S.A, p = S.p;
    if (S.dikey) {
      if (p.ikon) icon(ctx, p.ikon, A.cx, A.cy + 120, 460, E(S, 0.1, 1.6), S.t, S.id + "i");
      headline(ctx, S, p.baslik, E(S, 0.2, 0.9), { x: A.cx, y: A.y0 + 10, anchor: "tc", size: 96 });
      sub(ctx, S, p.alt, A.cx, A.y0 + 280, E(S, 0.6, 1.3), { anchor: "tc" });
      return;
    }
    if (p.ikon) icon(ctx, p.ikon, 1400, 470, 520, E(S, 0.1, 1.6), S.t, S.id + "i");
    // büyük başlık şeridi: kâğıt şerit soldan açılır
    const r = E(S, 0.15, 0.9);
    piece(ctx, S.id + "strip", shapes.rect(1000 * ease.out(r) + 10, 260), P.charcoal, { x: A.x0 - 10, y: 230, depth: 2, rot: -0.01, amp: 3 });
    if (!S.kapak) {
      const f = fit(ctx, upTR(p.baslik || ""), 104, "head", 920, 2, 54);
      f.lines.forEach((l, i) => txt(ctx, l, A.x0 + 40, 230 + 130 / f.lines.length + (i + 0.6) * f.size * 1.12 - (f.lines.length - 1) * 8, f.size, P.card, "head", "left", E(S, 0.45, 1.2)));
    }
    sub(ctx, S, p.alt, A.x0 + 20, 520, E(S, 0.8, 1.4), { bg: P.mustard, fg: P.charcoal });
    tape(ctx, S.id + "tp", A.x0 + 900 * ease.out(r), 215, 0.6, r);
  },

  // ---------------------------------------------------------------- nesne + etiketler
  nesne(ctx, S) {
    const A = S.A, p = S.p, labels = (p.etiketler || []).slice(0, 3);
    const has = labels.length > 0;
    const ix = S.dikey ? A.cx : (has ? 640 : A.cx), iy = S.dikey ? A.cy - (has ? 90 : 0) : A.cy + 40;
    const sz = S.dikey ? (has ? 520 : 640) : (has ? 560 : 640);
    const fl = Math.sin(S.ts * 1.1) * 6;
    // zemin gölgesi
    piece(ctx, S.id + "fl", shapes.ellipse(sz * 0.36, 26), "rgba(80,55,35,0.16)", { x: ix, y: iy + sz * 0.5, depth: 0, edge: false, tex: false, alpha: E(S, 0.3, 1) });
    icon(ctx, p.ikon, ix, iy + fl, sz, E(S, 0, 1.7), S.t, S.id + "i", p.renk);
    headline(ctx, S, p.baslik, E(S, 0.3, 1.0));
    labels.forEach((s, i) => {
      const a = F(S, 0.18 + i * 0.2, 0.3 + i * 0.2);
      if (S.dikey) { sub(ctx, S, s, A.cx, iy + sz * 0.5 + 20 + i * 92, a, { anchor: "tc", bg: [P.charcoal, P.red, P.blue][i], k: i, size: 40 }); return; }
      const lx = 1090, ly = 260 + i * 170;
      if (a > 0 && !S.kapak) line(ctx, [[ix + sz * 0.3, iy - 60 + i * 60], [lx - 20, ly + 34]], P.charcoal, 3, [9, 8], ease.out(a * 1.5));
      sub(ctx, S, s, lx, ly, a, { bg: [P.charcoal, P.red, P.blue][i], k: i, maxW: 680 });
    });
  },

  // ---------------------------------------------------------------- büyük sayı
  sayi(ctx, S) {
    const A = S.A, p = S.p, v = num(p.deger), dec = decOf(p.deger);
    const prog = ease.inOut(F(S, 0.05, 0.45));
    const shown = v == null ? String(p.deger || "") : (p.onek || "") + fmtNum(v * prog, prog < 1 ? 0 : dec);
    const ix = S.dikey ? A.cx : 470, iy = S.dikey ? A.y0 + 230 : 480;
    if (p.ikon) icon(ctx, p.ikon, ix, iy, S.dikey ? 400 : 440, E(S, 0, 1.4), S.t, S.id + "i");
    headline(ctx, S, p.baslik, E(S, 0.2, 0.9));
    if (S.kapak) return;
    const nx = S.dikey ? A.cx : (p.ikon ? 820 : A.cx), ny = S.dikey ? A.y0 + 640 : 520, al = S.dikey || !p.ikon ? "center" : "left";
    const f = fit(ctx, shown, S.dikey ? 190 : 230, "head", S.dikey ? 900 : (p.ikon ? 960 : 1500), 1, 80);
    // rakamın arkasında kesik kâğıt vurgu
    const bw = textW(ctx, shown, f.size, "head");
    const bx = al === "center" ? nx - bw / 2 : nx;
    piece(ctx, S.id + "hl" + Math.round(bw / 40), shapes.rect(bw + 60, f.size * 0.5), P.mustard, { x: bx - 30, y: ny - f.size * 0.3, depth: 0, rot: -0.01, alpha: E(S, 0.2, 0.6), amp: 3 });
    txt(ctx, shown, nx, ny, f.size, P.charcoal, "head", al);
    if (p.birim) txt(ctx, upTR(p.birim), al === "center" ? nx : nx + 8, ny + (S.dikey ? 90 : 100), S.dikey ? 62 : 64, P.red, "head", al, E(S, 0.5, 1.2));
    sub(ctx, S, p.etiket, al === "center" ? nx : nx, ny + (S.dikey ? 150 : 170), F(S, 0.3, 0.42), { anchor: al === "center" ? "tc" : undefined, bg: P.charcoal, maxW: S.dikey ? 920 : 860 });
  },

  // ---------------------------------------------------------------- iki değer karşılaştırma
  karsilastirma(ctx, S) {
    const A = S.A, p = S.p, a = p.sol || {}, b = p.sag || {};
    const va = Math.abs(num(a.deger) ?? 1), vb = Math.abs(num(b.deger) ?? 1), mx = Math.max(va, vb, 1e-9);
    const base = S.dikey ? 1180 : 760, maxH = S.dikey ? 520 : 480;
    const hOf = v => Math.max(maxH * 0.06, maxH * v / mx);
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8));
    const cols = [[a, S.dikey ? 300 : 620, P.blue, 0], [b, S.dikey ? 780 : 1300, P.red, 1]];
    piece(ctx, S.id + "fl", shapes.rect(S.dikey ? 900 : 1300, 18), P.charcoal, { x: S.dikey ? 90 : 310, y: base, depth: 1, alpha: E(S, 0.2, 0.6) });
    cols.forEach(([c, x, col, i]) => {
      const v = Math.abs(num(c.deger) ?? 0), g = ease.inOut(F(S, 0.12 + i * 0.22, 0.42 + i * 0.22));
      const h = hOf(v) * g, w = S.dikey ? 220 : 260, n = Math.max(1, Math.round(h / 22));
      for (let j = 0; j < n; j++) { // üst üste kâğıt dilimleri
        const hh = Math.min(22, h - j * 22); if (hh <= 1) break;
        piece(ctx, S.id + "c" + i + "_" + (j % 7), shapes.rect(w, hh - 2), j % 6 === 5 ? shade(col, -0.2) : col, { x: x - w / 2, y: base - (j + 1) * 22 + (22 - hh), depth: j === n - 1 ? 2 : 0, edge: j === n - 1, amp: 1.2, rot: jig(S.t, S.id + i + j, 0.004) });
      }
      if (c.ikon) icon(ctx, c.ikon, x, base - h - 90, 150, g > 0.05 ? E(S, 0.3, 1.2) : 0, S.t, S.id + "ci" + i);
      if (S.kapak) return;
      const vs = c.deger != null ? (num(c.deger) != null ? fmtNum((num(c.deger)) * g, g < 1 ? 0 : decOf(c.deger)) : String(c.deger)) : "";
      if (g > 0) txt(ctx, vs + (p.birim && vs ? " " + p.birim : ""), x, base - h - (c.ikon ? 190 : 30), S.dikey ? 58 : 66, P.charcoal, "head", "center");
      label(ctx, S.id + "l" + i, c.etiket || "", x, base + 34, S.dikey ? 40 : 40, P.card, P.charcoal, F(S, 0.08 + i * 0.22, 0.2 + i * 0.22), { font: "bold", anchor: "tc", maxW: S.dikey ? 440 : 560, from: "down" });
    });
  },

  // ---------------------------------------------------------------- zaman çizelgesi
  zaman(ctx, S) {
    const A = S.A, p = S.p, ev = (p.olaylar || []).slice(0, 5), n = Math.max(1, ev.length);
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8));
    const lineP = ease.inOut(F(S, 0.05, 0.3));
    if (!S.dikey) {
      const y = 520, x0 = 330, x1 = 1590;
      piece(ctx, S.id + "ln", shapes.rect((x1 - x0) * lineP + 20, 16), P.charcoal, { x: x0 - 10, y: y - 8, depth: 1, amp: 1.5 });
      ev.forEach((e, i) => {
        const x = n === 1 ? (x0 + x1) / 2 : x0 + (x1 - x0) * i / (n - 1), a = F(S, 0.15 + i * 0.7 / n, 0.25 + i * 0.7 / n);
        const up = i % 2 === 0;
        piece(ctx, S.id + "pt" + i, shapes.circle(24), i === n - 1 ? P.red : P.mustard, { x, y, depth: 2, scale: ease.outBack(a), alpha: Math.min(1, a * 3) });
        if (S.kapak || a <= 0) return;
        line(ctx, [[x, y + (up ? -26 : 26)], [x, y + (up ? -80 : 80)]], P.charcoal, 3, [6, 6], a);
        txt(ctx, String(e.yil || ""), x, up ? y - 100 : y + 150, 68, i === n - 1 ? P.red : P.charcoal, "head", "center", ease.out(a * 1.4));
        label(ctx, S.id + "e" + i, e.metin || "", x, up ? y - 250 : y + 175, 34, P.card, P.charcoal, a, { font: "bold", anchor: "tc", maxW: Math.min(420, 1500 / n + 60), lines: 3, from: up ? "up" : "down", dist: 60 });
      });
      // ilerleyen işaretçi
      const k = ease.inOut(F(S, 0.15, 0.95)); const px = x0 + (x1 - x0) * k;
      if (lineP >= 1) piece(ctx, S.id + "ptr", shapes.tri(34, 30), P.red, { x: px, y: y + 36, rot: Math.PI, depth: 1 });
    } else {
      const x = 200, y0 = A.y0 + 160, y1 = A.y1 - 40;
      piece(ctx, S.id + "ln", shapes.rect(16, (y1 - y0) * lineP + 20), P.charcoal, { x: x - 8, y: y0 - 10, depth: 1, amp: 1.5 });
      ev.forEach((e, i) => {
        const y = n === 1 ? (y0 + y1) / 2 : y0 + (y1 - y0) * i / (n - 1), a = F(S, 0.15 + i * 0.7 / n, 0.25 + i * 0.7 / n);
        piece(ctx, S.id + "pt" + i, shapes.circle(24), i === n - 1 ? P.red : P.mustard, { x, y, depth: 2, scale: ease.outBack(a), alpha: Math.min(1, a * 3) });
        if (S.kapak || a <= 0) return;
        txt(ctx, String(e.yil || ""), x + 60, y + 20, 64, i === n - 1 ? P.red : P.charcoal, "head", "left", ease.out(a * 1.4));
        label(ctx, S.id + "e" + i, e.metin || "", x + 60, y + 36, 34, P.card, P.charcoal, a, { font: "bold", maxW: 700, lines: 2, from: "right", dist: 60 });
      });
    }
  },

  // ---------------------------------------------------------------- rota
  rota(ctx, S) {
    const A = S.A, p = S.p;
    // kara parçaları
    const lands = S.dikey ? [[-80, 560, 520, 300], [380, 1050, 640, 320]] : [[60, 160, 760, 560], [1050, 260, 860, 600]];
    lands.forEach(([x, y, w, h], i) => {
      const pts = shapes.ellipse(w / 2, h / 2, 26).map(([px, py], j) => [px * (0.82 + 0.3 * rnd(strSeed(S.id) + i, j)), py * (0.8 + 0.3 * rnd(strSeed(S.id) + 9 + i, j))]);
      piece(ctx, S.id + "land" + i, pts, i ? shade(P.sage, 0.1) : P.sage, { x: x + w / 2, y: y + h / 2, depth: 1, alpha: E(S, 0, 0.6 + i * 0.2), amp: 5, step: 14 });
    });
    const a = S.dikey ? [250, 700] : [430, 470], b = S.dikey ? [800, 1180] : [1460, 560];
    const mid = [(a[0] + b[0]) / 2, Math.min(a[1], b[1]) - (S.dikey ? 60 : 260)];
    const path = []; for (let i = 0; i <= 40; i++) { const k = i / 40; path.push([(1 - k) ** 2 * a[0] + 2 * (1 - k) * k * mid[0] + k * k * b[0], (1 - k) ** 2 * a[1] + 2 * (1 - k) * k * mid[1] + k * k * b[1]]); }
    const go = ease.inOut(F(S, 0.2, 0.8));
    line(ctx, path, P.charcoal, 4, [14, 10], go);
    [[a, p.nereden, 0], [b, p.nereye, 1]].forEach(([pt, name, i]) => {
      const pa = E(S, 0.3 + i * 0.4, 0.9 + i * 0.4);
      piece(ctx, S.id + "pin" + i, [[0, 0], [-20, -38], [-15, -56], [0, -64], [15, -56], [20, -38]], P.red, { x: pt[0], y: pt[1] - 60 * (1 - ease.outBack(pa)), depth: 2, alpha: Math.min(1, pa * 3) });
      piece(ctx, S.id + "pc" + i, shapes.circle(8), P.card, { x: pt[0], y: pt[1] - 44 - 60 * (1 - ease.outBack(pa)), depth: 0, alpha: Math.min(1, pa * 3) });
      if (!S.kapak) label(ctx, S.id + "pn" + i, upTR(name || ""), pt[0], pt[1] + 18, S.dikey ? 44 : 46, P.card, P.charcoal, pa, { anchor: "tc", maxW: 520, from: "down", dist: 40 });
    });
    const [vx, vy, ang] = pointAlong(path, go);
    const ar = p.arac || "ucak", rotates = ar === "ucak";
    if (go > 0.01) {
      ctx.save(); ctx.translate(vx, vy - (rotates ? 0 : 40)); if (rotates) ctx.rotate(ang);
      if (!rotates && b[0] < a[0]) ctx.scale(-1, 1);
      icon(ctx, ar, 0, 0, S.dikey ? 200 : 230, 1, S.t, S.id + "v"); ctx.restore();
    }
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8), S.dikey ? {} : { y: A.y0 });
  },

  // ---------------------------------------------------------------- çizgi grafik
  grafik(ctx, S) {
    const A = S.A, p = S.p, vals = (p.degerler || []).map(num).filter(v => v != null).slice(0, 10);
    if (vals.length < 2) return KALIP.nesne(ctx, { ...S, p: { ikon: "grafik_artis", baslik: p.baslik } });
    const lbl = p.etiketler || [];
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8));
    const cx0 = S.dikey ? 120 : 260, cx1 = S.dikey ? 960 : 1660, cy0 = S.dikey ? A.y0 + 240 : 260, cy1 = S.dikey ? A.y1 - 60 : 760;
    piece(ctx, S.id + "card", shapes.rect(cx1 - cx0 + 120, cy1 - cy0 + 150), P.card, { x: cx0 - 60, y: cy0 - 60, depth: 2, alpha: E(S, 0, 0.5), rot: -0.006 });
    const mn = Math.min(0, ...vals), mx = Math.max(...vals);
    const X = i => cx0 + (cx1 - cx0) * i / (vals.length - 1), Y = v => cy1 - (cy1 - cy0) * (v - mn) / ((mx - mn) || 1);
    for (let g = 0; g <= 3; g++) line(ctx, [[cx0, cy0 + (cy1 - cy0) * g / 3], [cx1, cy0 + (cy1 - cy0) * g / 3]], shade(P.cream, -0.12), 2, null, E(S, 0.2, 0.8));
    const down = vals[vals.length - 1] < vals[0], col = down ? P.red : P.sage;
    const pts = vals.map((v, i) => [X(i), Y(v)]), prog = ease.inOut(F(S, 0.15, 0.75));
    // dolgu (kesik kâğıt alan)
    const nShown = prog * (vals.length - 1), last = pointAlong(pts, prog);
    if (prog > 0.02) {
      const area_ = [[cx0, cy1]]; pts.forEach((q, i) => { if (i <= nShown) area_.push(q); }); area_.push([last[0], last[1]], [last[0], cy1]);
      ctx.save(); ctx.globalAlpha = 0.35; ctx.fillStyle = col; ctx.beginPath(); area_.forEach((q, i) => i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])); ctx.fill(); ctx.restore();
    }
    line(ctx, pts, col, 9, null, prog);
    pts.forEach((q, i) => {
      if (i > nShown + 0.001) return;
      piece(ctx, S.id + "d" + i, shapes.circle(13), P.charcoal, { x: q[0], y: q[1], depth: 1 });
      if (!S.kapak && lbl[i]) txt(ctx, String(lbl[i]), q[0], cy1 + 50, S.dikey ? 30 : 32, P.charcoal, "bold", "center");
    });
    if (!S.kapak) {
      const lv = vals[Math.min(vals.length - 1, Math.round(nShown))];
      label(ctx, S.id + "v", fmtNum(lv, decOf(p.degerler[Math.round(nShown)])) + (p.birim ? " " + p.birim : ""), last[0], last[1] - 110, 52, col === P.red ? P.red : P.charcoal, P.card, E(S, 0.4, 1), { anchor: "tc", maxW: 600 });
    }
  },

  // ---------------------------------------------------------------- liste
  liste(ctx, S) {
    const A = S.A, p = S.p, items = (p.maddeler || []).slice(0, 4), n = Math.max(1, items.length);
    const hb = headline(ctx, S, p.baslik, E(S, 0.1, 0.8)) || headBox(ctx, S, p.baslik);
    const top = hb ? hb.y + hb.h + (S.dikey ? 60 : 50) : (S.dikey ? A.y0 + 60 : 200);
    const step = Math.min(S.dikey ? 210 : 150, ((S.dikey ? A.y1 : A.y1 - 20) - top) / n);
    const cur = Math.min(n - 1, Math.floor(F(S, 0.1, 0.95) * n));
    items.forEach((it, i) => {
      const m = typeof it === "string" ? { metin: it } : it, a = F(S, 0.08 + i * 0.75 / n, 0.18 + i * 0.75 / n);
      if (a <= 0) return;
      const x = S.dikey ? A.x0 + 20 : 220, y = top + i * step, active = i === cur;
      piece(ctx, S.id + "nb" + i, shapes.circle(44), active ? P.red : P.charcoal, { x: x + 44, y: y + 46, depth: 2, scale: ease.outBack(a) });
      if (m.ikon) icon(ctx, m.ikon, x + 44, y + 46, 70, 1, S.t, S.id + "mi" + i, P.card);
      else txt(ctx, String(i + 1), x + 44, y + 64, 50, P.card, "head", "center");
      if (!S.kapak) label(ctx, S.id + "m" + i, m.metin || "", x + 110, y, S.dikey ? 42 : 46, active ? P.card : shade(P.card, -0.05), P.charcoal, a, { font: "bold", maxW: S.dikey ? 800 : 1400, lines: 2, from: "right", depth: active ? 3 : 1, rot: active ? -0.01 : 0.004 });
    });
  },

  // ---------------------------------------------------------------- gazete kupürü
  gazete(ctx, S) {
    const A = S.A, p = S.p;
    const w = S.dikey ? 880 : 1080, h = S.dikey ? 820 : 640, cx = A.cx, cy = S.dikey ? A.cy : 470;
    const a = E(S, 0, 1.0), z = 1 + 0.05 * F(S, 0, 1);
    ctx.save(); ctx.translate(cx, cy); ctx.scale(z, z); ctx.rotate(-0.03 + (1 - ease.out(a)) * 0.2);
    ctx.translate(0, (1 - ease.out(a)) * 200);
    piece(ctx, S.id + "pp", shapes.rect(w, h), shade(P.card, -0.03), { x: -w / 2, y: -h / 2, depth: 3, amp: 4, step: 7, alpha: Math.min(1, a * 3) });
    if (a > 0.3) {
      const pub = upTR(p.kaynak || "GAZETE ARŞİVİ");
      txt(ctx, pub, 0, -h / 2 + 70, 44, P.charcoal, "head", "center");
      line(ctx, [[-w / 2 + 40, -h / 2 + 92], [w / 2 - 40, -h / 2 + 92]], P.charcoal, 3);
      txt(ctx, p.tarih || "", 0, -h / 2 + 128, 26, shade(P.charcoal, 0.3), "semi", "center");
      line(ctx, [[-w / 2 + 40, -h / 2 + 142], [w / 2 - 40, -h / 2 + 142]], P.charcoal, 1.5);
      if (!S.kapak) {
        const f = fit(ctx, upTR(p.manset || ""), S.dikey ? 72 : 76, "head", w - 100, 3, 40);
        f.lines.forEach((l, i) => txt(ctx, l, 0, -h / 2 + 220 + i * f.size * 1.1, f.size, P.ink, "head", "center", E(S, 0.5 + i * 0.25, 1.1 + i * 0.25)));
      }
      const iy = S.dikey ? 110 : 120;
      piece(ctx, S.id + "img", shapes.rect(w * 0.38, h * 0.36), shade(P.blue, 0.35), { x: -w / 2 + 50, y: iy - 40, depth: 0 });
      if (p.ikon) icon(ctx, p.ikon, -w / 2 + 50 + w * 0.19, iy - 40 + h * 0.18, h * 0.3, E(S, 0.6, 1.5), S.t, S.id + "gi");
      for (let i = 0; i < 7; i++) piece(ctx, S.id + "tl" + i, shapes.rect(w * 0.46 - (i % 3) * 30, 8), shade(P.charcoal, 0.55), { x: 20, y: iy - 30 + i * 30, depth: 0, edge: false, amp: 0.8 });
    }
    tape(ctx, S.id + "t1", -w / 2 - 30, -h / 2 - 10, -0.6, a); tape(ctx, S.id + "t2", w / 2 - 80, h / 2 - 20, -0.6, a);
    ctx.restore();
  },

  // ---------------------------------------------------------------- yığın (para, altın, belge, insan)
  yigin(ctx, S) {
    const A = S.A, p = S.p, ik = p.ikon || "banknot";
    const sizes = [6, 5, 4, 3, 2, 1], cnt = 21, prog = F(S, 0.05, 0.7);
    const cx = S.dikey ? A.cx : 620, base = S.dikey ? A.y1 - 120 : 780;
    piece(ctx, S.id + "fl", shapes.ellipse(380, 30), "rgba(80,55,35,0.15)", { x: cx, y: base + 70, depth: 0, edge: false, tex: false });
    let i = 0;
    for (let r = 0; r < sizes.length; r++) for (let j = 0; j < sizes[r]; j++, i++) {
      const a = win(prog, i / cnt * 0.85, i / cnt * 0.85 + 0.15);
      if (a <= 0) continue;
      const x = cx + (j - (sizes[r] - 1) / 2) * 120 + (rnd(strSeed(S.id), i) - 0.5) * 30;
      const y = base - r * 66 - (1 - ease.in(a)) * 700;
      ctx.save(); ctx.translate(x, y); ctx.rotate((rnd(strSeed(S.id) + 3, i) - 0.5) * 0.4);
      icon(ctx, ik, 0, 0, 160, 1, S.t, S.id + "y" + (i % 4));
      ctx.restore();
    }
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8));
    if (S.kapak) return;
    const tx = S.dikey ? A.cx : 1300, ty = S.dikey ? A.y0 + 330 : 430;
    const f = fit(ctx, upTR(p.metin || ""), S.dikey ? 120 : 130, "head", S.dikey ? 900 : 760, 2, 60);
    f.lines.forEach((l, i) => txt(ctx, l, tx, ty + i * f.size * 1.05, f.size, i === f.lines.length - 1 ? P.red : P.charcoal, "head", "center", F(S, 0.25 + i * 0.08, 0.4 + i * 0.08)));
    sub(ctx, S, p.etiket, tx, ty + f.lines.length * f.size * 1.05 + 10, F(S, 0.45, 0.55), { anchor: "tc", bg: P.charcoal, maxW: S.dikey ? 900 : 700 });
  },

  // ---------------------------------------------------------------- gösterge (termometre / kadran)
  gosterge(ctx, S) {
    const A = S.A, p = S.p, v = num(p.deger) ?? 0, mn = num(p.min) ?? 0, mx = num(p.max) ?? Math.max(v * 1.15, 1);
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8));
    const prog = ease.inOut(F(S, 0.12, 0.6)), cur = mn + (v - mn) * prog;
    const marks = (p.isaretler || []).slice(0, 3);
    if (String(p.birim || "").includes("°")) {
      const TX = S.dikey ? 300 : 560, top = S.dikey ? A.y0 + 280 : 230, bot = S.dikey ? A.y1 - 80 : 760, Y = q => bot - (q - mn) / (mx - mn) * (bot - top);
      piece(ctx, S.id + "tube", shapes.rect(90, bot - top + 50), P.card, { x: TX - 45, y: top - 30, depth: 2 });
      piece(ctx, S.id + "fill", shapes.rect(46, Math.max(4, bot - Y(cur) + 30)), P.red, { x: TX - 23, y: Y(cur), depth: 0, edge: false, amp: 0.8 });
      piece(ctx, S.id + "bulb", shapes.circle(78), P.red, { x: TX, y: bot + 70, depth: 2 });
      for (let i = 0; i <= 4; i++) { const q = mn + (mx - mn) * i / 4; piece(ctx, S.id + "tk" + i, shapes.rect(26, 7), P.charcoal, { x: TX - 80, y: Y(q) - 3, depth: 0, amp: 0.6 }); if (!S.kapak) txt(ctx, fmtNum(q), TX - 90, Y(q) + 10, 26, P.charcoal, "semi", "right"); }
      if (S.kapak) return;
      const NX = S.dikey ? A.x0 + 30 : 1120, NY = S.dikey ? A.y0 + 140 : 420;
      txt(ctx, fmtNum(cur) + (p.birim || ""), NX, NY, S.dikey ? 130 : 170, P.charcoal, "head");
      sub(ctx, S, p.etiket, NX, NY + 40, E(S, 0.6, 1.2), { bg: P.charcoal, maxW: S.dikey ? 600 : 640, from: "down" });
      marks.forEach((m, i) => {
        const mv = num(m.deger); if (mv == null) return;
        const a = cur >= mv ? win(cur, mv, mv + (mx - mn) * 0.08) : 0;
        if (a <= 0) return;
        line(ctx, [[TX + 46, Y(mv)], [TX + 110, Y(mv)]], P.charcoal, 3, [7, 6], a);
        sub(ctx, S, m.metin, TX + 120, Y(mv) - 34, a, { bg: [P.sage, P.blue, P.mustard][i], fg: i === 2 ? P.charcoal : P.card, k: "m" + i, size: 34, maxW: S.dikey ? 520 : 440 });
      });
      return;
    }
    // yarım daire kadran
    const cx = S.dikey ? A.cx : 700, cy = S.dikey ? A.y0 + 620 : 640, r = S.dikey ? 360 : 380;
    const segs = 18;
    for (let i = 0; i < segs; i++) {
      const a0 = Math.PI + i / segs * Math.PI, a1 = Math.PI + (i + 1) / segs * Math.PI - 0.015;
      const pts = [...shapes.arc(r, a0, a1, 4), ...shapes.arc(r * 0.72, a1, a0, 4)];
      piece(ctx, S.id + "sg" + i, pts, i / segs < 0.5 ? P.sage : i / segs < 0.8 ? P.mustard : P.red, { x: cx, y: cy, depth: 1, alpha: win(E(S, 0, 1.2), i / segs * 0.7, i / segs * 0.7 + 0.3) });
    }
    const ang = Math.PI + (cur - mn) / (mx - mn || 1) * Math.PI;
    piece(ctx, S.id + "nd", [[0, -8], [r * 0.85, 0], [0, 8], [-20, 0]], P.charcoal, { x: cx, y: cy, rot: ang, depth: 2 });
    piece(ctx, S.id + "hub", shapes.circle(28), P.charcoal, { x: cx, y: cy, depth: 2 });
    if (S.kapak) return;
    txt(ctx, fmtNum(cur, prog < 1 ? 0 : decOf(p.deger)) + " " + (p.birim || ""), cx, cy + 120, S.dikey ? 110 : 120, P.charcoal, "head", "center");
    sub(ctx, S, p.etiket, S.dikey ? A.cx : 1180, S.dikey ? cy + 170 : 380, E(S, 0.6, 1.2), { anchor: S.dikey ? "tc" : undefined, bg: P.charcoal, maxW: S.dikey ? 900 : 600 });
  },

  // ---------------------------------------------------------------- kişi (yüzsüz siluet + dosya)
  kisi(ctx, S) {
    const A = S.A, p = S.p;
    const fx = S.dikey ? A.cx : 600, fy = S.dikey ? A.y0 + 330 : 470;
    // arkada dosya klasörü
    piece(ctx, S.id + "fold", [[-260, -230], [-80, -230], [-50, -200], [260, -200], [260, 250], [-260, 250]], P.mustard, { x: fx, y: fy, depth: 2, rot: -0.03, alpha: E(S, 0, 0.6) });
    piece(ctx, S.id + "fold2", shapes.rect(500, 400), shade(P.mustard, 0.25), { x: fx - 250, y: fy - 160, depth: 0, rot: -0.03, alpha: E(S, 0.1, 0.7) });
    icon(ctx, p.ikon || "insan", fx, fy + 30, S.dikey ? 420 : 440, E(S, 0.2, 1.6), S.t, S.id + "f");
    // damga
    const st = E(S, 1.2, 1.5);
    if (st > 0 && p.damga !== false) {
      ctx.save(); ctx.translate(fx + 150, fy + 180); ctx.rotate(-0.25); ctx.scale(1 + (1 - st) * 0.8, 1 + (1 - st) * 0.8); ctx.globalAlpha = st * 0.85;
      ctx.strokeStyle = P.red; ctx.lineWidth = 7; ctx.strokeRect(-120, -42, 240, 84);
      txt(ctx, upTR(p.damga || "DOSYA"), 0, 20, 52, P.red, "head", "center"); ctx.restore();
    }
    if (S.kapak) return;
    const nx = S.dikey ? A.cx : 1000, ny = S.dikey ? A.y0 + 690 : 330;
    const nb = label(ctx, S.id + "nm", upTR(p.isim || ""), nx, S.dikey ? ny - 60 : ny - 60, S.dikey ? 76 : 86, P.card, P.charcoal, Math.max(0.001, E(S, 0.4, 1.0)), { anchor: S.dikey ? "tc" : undefined, maxW: S.dikey ? 940 : 820, tape: true });
    const y2 = (nb ? nb.y + nb.h : ny) + 24;
    const rb = sub(ctx, S, p.rol, nx + (S.dikey ? 0 : 10), y2, Math.max(0.001, E(S, 0.8, 1.4)), { anchor: S.dikey ? "tc" : undefined, bg: P.charcoal, maxW: S.dikey ? 920 : 760 });
    if (p.not) sub(ctx, S, p.not, nx + 10, (rb ? rb.y + rb.h : y2 + 80) + 20, F(S, 0.45, 0.55), { anchor: S.dikey ? "tc" : undefined, bg: P.red, k: "n", maxW: S.dikey ? 920 : 760 });
  },

  // ---------------------------------------------------------------- ortam (ortam + hareketli nesne)
  ortam(ctx, S) {
    const A = S.A, p = S.p, o = p.ortam || "sehir", W = S.W, H = S.H;
    const sky = { uzay: P.night, gece: P.night, deniz: shade(P.blue, 0.45), okyanus: shade(P.blue, -0.3), col: P.sky, sehir: shade(P.blue, 0.55), dag: shade(P.blue, 0.5), orman: shade(P.sage, 0.5), ofis: shade(P.cream, -0.05), buz: shade(P.blue, 0.6) }[o] || shade(P.blue, 0.55);
    const s0 = ease.out(E(S, 0, 0.8));
    piece(ctx, S.id + "sky", shapes.rect(W + 80, H + 80), sky, { x: -40, y: -40 - (1 - s0) * (H + 80), depth: 2, edge: false, amp: 4, step: 20 });
    const par = S.ts * 8; // yavaş yatay kayma (parallaks)
    const layer = (k, col, base, amp, f, dl) => {
      const pts = [[-100, H + 50]]; for (let i = 0; i <= 30; i++) { const x = -100 + i * (W + 200) / 30; pts.push([x, base - amp * (0.6 + 0.4 * Math.sin(i * f + k * 3)) - amp * 0.3 * Math.sin(i * 2.7 * f + k)]); } pts.push([W + 100, H + 50]);
      piece(ctx, S.id + "ly" + k, pts, col, { x: -par * (0.3 + k * 0.25) % 60, y: (1 - ease.out(E(S, dl, dl + 0.8))) * 400, depth: 1, amp: 3, step: 14 });
    };
    if (o === "uzay" || o === "gece") {
      for (let i = 0; i < 40; i++) piece(ctx, S.id + "st" + (i % 6), shapes.star(6 + (i % 3) * 3, 2.5), P.card, { x: rnd(strSeed(S.id), i) * W, y: rnd(strSeed(S.id) + 1, i) * H * 0.7, depth: 0, edge: false, alpha: s0 * (0.5 + 0.5 * Math.sin(S.t * 2 + i)) });
      if (o === "uzay") icon(ctx, "gezegen", S.dikey ? 260 : 300, S.dikey ? 640 : 250, 300, E(S, 0.3, 1.5), S.t, S.id + "pl");
      if (o === "gece") { layer(0, shade(P.night, -0.3), H * 0.78, 160, 1.3, 0.2); }
    } else if (o === "deniz" || o === "okyanus") {
      if (o === "deniz") icon(ctx, "gunes", S.dikey ? 800 : 1550, S.dikey ? 600 : 200, 200, E(S, 0.2, 1.2), S.t, S.id + "sn");
      for (let k = 0; k < 3; k++) {
        const pts = [[-100, H + 50]]; for (let x = -100; x <= W + 100; x += 40) pts.push([x, H * (o === "okyanus" ? 0.25 : 0.62) + k * 90 + Math.sin(x / 90 + S.t * 1.5 + k) * 14]); pts.push([W + 100, H + 50]);
        piece(ctx, S.id + "wv" + k, pts, [shade(P.blue, 0.15), P.blue, shade(P.blue, -0.2)][k], { y: (1 - ease.out(E(S, 0.1 + k * 0.1, 0.9 + k * 0.1))) * 300, depth: 1, amp: 1.5 });
      }
    } else if (o === "col") {
      icon(ctx, "gunes", S.dikey ? 800 : 1500, S.dikey ? 600 : 220, 260, E(S, 0.2, 1.2), S.t, S.id + "sn");
      layer(0, shade(P.mustard, 0.15), H * 0.72, 90, 0.5, 0.1); layer(1, P.mustard, H * 0.82, 70, 0.8, 0.2); layer(2, shade(P.terra, 0.2), H * 0.92, 50, 1.1, 0.3);
    } else if (o === "dag" || o === "buz") {
      layer(0, shade(P.blue, 0.1), H * 0.55, 260, 0.9, 0.1); layer(1, o === "buz" ? P.card : P.blue, H * 0.72, 200, 1.3, 0.2); layer(2, o === "buz" ? shade(P.blue, 0.4) : shade(P.sage, -0.2), H * 0.9, 90, 1.7, 0.3);
    } else if (o === "orman") {
      layer(0, shade(P.sage, -0.25), H * 0.85, 60, 1, 0.1);
      for (let i = 0; i < 7; i++) icon(ctx, "agac", (i + 0.5) * W / 7 - par * 0.5 % 40, H * (S.dikey ? 0.6 : 0.62) + (i % 2) * 40, 260 + (i % 3) * 40, E(S, 0.1 + i * 0.08, 0.9 + i * 0.08), S.t, S.id + "tr" + i);
    } else if (o === "ofis") {
      piece(ctx, S.id + "desk", shapes.rect(W + 100, 60), shade(P.terra, -0.2), { x: -50, y: H * 0.7, depth: 2 });
      icon(ctx, "bilgisayar", A.cx, H * 0.7 - 140, 360, E(S, 0.2, 1.4), S.t, S.id + "pc");
      icon(ctx, "belge", A.cx - (S.dikey ? 300 : 420), H * 0.7 - 70, 200, E(S, 0.5, 1.6), S.t, S.id + "dc");
    } else { // şehir
      for (let i = 0; i < 9; i++) {
        const w = 120 + (i % 3) * 50, h = 200 + rnd(strSeed(S.id), i) * 330, x = i * W / 8 - 60 - par * 0.4 % 40;
        piece(ctx, S.id + "b" + i, shapes.rect(w, h + 60), i % 2 ? P.blue : shade(P.blue, -0.2), { x, y: H * 0.86 - h + (1 - ease.out(E(S, 0.1 + i * 0.06, 0.8 + i * 0.06))) * 600, depth: 1 });
      }
      piece(ctx, S.id + "road", shapes.rect(W + 100, H * 0.2), P.charcoal, { x: -50, y: H * 0.85, depth: 2 });
    }
    // hareketli nesne: soldan sağa geçer
    if (p.ikon) {
      const k = ease.inOut(F(S, 0.1, 0.95)), flying = ["ucak", "roket", "uydu"].includes(p.ikon);
      const y = { deniz: H * 0.6, okyanus: H * 0.55, uzay: H * 0.58, gece: H * 0.35 }[o] ?? (flying ? H * 0.32 : H * (S.dikey ? 0.62 : 0.66));
      const x = lerp(W * 0.18, W * 0.8, k);
      icon(ctx, p.ikon, x, y + Math.sin(S.t * 2) * 8, S.dikey ? 340 : 380, 1, S.t, S.id + "mv");
    }
    if (p.baslik && !S.kapak) headline(ctx, S, p.baslik, E(S, 0.5, 1.2));
    if (p.etiket && !S.kapak) sub(ctx, S, p.etiket, S.dikey ? A.cx : A.x0, S.dikey ? A.y0 + 230 : A.y0 + 190, F(S, 0.3, 0.42), { anchor: S.dikey ? "tc" : undefined, bg: P.charcoal });
  },

  // ---------------------------------------------------------------- soru
  soru(ctx, S) {
    const A = S.A, p = S.p;
    const qx = S.dikey ? A.cx : 480, qy = S.dikey ? A.y0 + 230 : 470;
    icon(ctx, "soru", qx, qy + Math.sin(S.ts * 1.4) * 8, S.dikey ? 420 : 520, E(S, 0, 1.3), S.t, S.id + "q");
    if (S.kapak) return;
    label(ctx, S.id + "qt", p.soru || "", S.dikey ? A.cx : 860, S.dikey ? A.y0 + 520 : 300, S.dikey ? 58 : 64, P.card, P.charcoal, E(S, 0.5, 1.2), { font: "head", maxW: S.dikey ? 940 : 920, lines: 4, anchor: S.dikey ? "tc" : undefined, tape: true });
  },

  // ---------------------------------------------------------------- yüzde (pasta)
  yuzde(ctx, S) {
    const A = S.A, p = S.p, v = Math.max(0, Math.min(100, num(p.yuzde) ?? 50));
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8));
    const cx = S.dikey ? A.cx : 620, cy = S.dikey ? A.y0 + 340 : 500, r = S.dikey ? 260 : 300;
    piece(ctx, S.id + "base", shapes.circle(r), P.card, { x: cx, y: cy, depth: 2, alpha: E(S, 0, 0.5) });
    const prog = ease.inOut(F(S, 0.12, 0.6)), a1 = -Math.PI / 2 + Math.PI * 2 * v / 100 * prog;
    if (prog > 0.005) piece(ctx, S.id + "w" + Math.round(v * prog), [[0, 0], ...shapes.arc(r - 18, -Math.PI / 2, a1, Math.max(4, Math.round(60 * v / 100 * prog)))], P.red, { x: cx, y: cy, depth: 1, amp: 1.5 });
    piece(ctx, S.id + "hole", shapes.circle(r * 0.42), P.cream, { x: cx, y: cy, depth: 0 });
    if (S.kapak) return;
    txt(ctx, "%" + fmtNum(v * prog, prog < 1 ? 0 : decOf(p.yuzde)), cx, cy + 34, 96, P.charcoal, "head", "center");
    sub(ctx, S, p.etiket, S.dikey ? A.cx : 1060, S.dikey ? cy + r + 40 : 430, E(S, 0.6, 1.2), { anchor: S.dikey ? "tc" : undefined, bg: P.charcoal, maxW: S.dikey ? 920 : 720, lines: 3 });
  },

  // ---------------------------------------------------------------- akış (neden → sonuç, para akışı)
  akis(ctx, S) {
    const A = S.A, p = S.p, st = (p.adimlar || []).slice(0, 4), ik = p.ikonlar || [], n = Math.max(2, st.length);
    headline(ctx, S, p.baslik, E(S, 0.1, 0.8));
    const pos = i => S.dikey ? [220, A.y0 + 220 + i * (A.y1 - A.y0 - 300) / (n - 1)] : [260 + i * 1400 / (n - 1), 480 + (i % 2 ? 60 : -40)];
    for (let i = 0; i < st.length - 1; i++) {
      const a = pos(i), b = pos(i + 1), pr = F(S, 0.15 + (i + 0.5) * 0.65 / n, 0.15 + (i + 1) * 0.65 / n);
      const pts = S.dikey ? [[a[0], a[1] + 90], [b[0], b[1] - 90]] : [[a[0] + 120, a[1]], [b[0] - 120, b[1]]];
      line(ctx, pts, P.charcoal, 5, [14, 10], pr);
      if (pr >= 1) { const [ex, ey, an] = pointAlong(pts, 1); piece(ctx, S.id + "ah" + i, shapes.tri(30, 30), P.charcoal, { x: ex, y: ey, rot: an + Math.PI / 2, depth: 0 }); }
      // akan jeton
      const fl = (S.ts * 0.6 + i * 0.3) % 1;
      if (pr >= 1 && p.akan !== false) { const [fx, fy] = pointAlong(pts, fl); piece(ctx, S.id + "tok" + i, shapes.circle(16), P.mustard, { x: fx, y: fy, depth: 1 }); }
    }
    st.forEach((s, i) => {
      const [x, y] = pos(i), a = F(S, 0.1 + i * 0.65 / n, 0.2 + i * 0.65 / n);
      if (a <= 0) return;
      if (ik[i]) icon(ctx, ik[i], x, y - (S.dikey ? 0 : 20), S.dikey ? 150 : 170, a, S.t, S.id + "ai" + i);
      else piece(ctx, S.id + "ac" + i, shapes.circle(60), i === st.length - 1 ? P.red : P.charcoal, { x, y, depth: 2, scale: ease.outBack(a) });
      if (!S.kapak) label(ctx, S.id + "at" + i, s, S.dikey ? x + 110 : x, S.dikey ? y - 30 : y + 90, S.dikey ? 38 : 34, P.card, P.charcoal, a, { font: "bold", anchor: S.dikey ? undefined : "tc", maxW: S.dikey ? 700 : 1400 / n - 10, lines: 3, from: "down", dist: 50 });
    });
  },
};
// kapak: nesne sağda büyük (solda yazı kartı olacak), arkasında kâğıt ışın patlaması
KALIP.kapak = function (ctx, S) {
  const p = S.p, cx = S.W * 0.79, cy = S.H * 0.52;
  for (let i = 0; i < 14; i++) {
    const a0 = i / 14 * Math.PI * 2, a1 = a0 + Math.PI / 14;
    piece(ctx, "ray" + i, [[0, 0], [Math.cos(a0) * 1400, Math.sin(a0) * 1400], [Math.cos(a1) * 1400, Math.sin(a1) * 1400]], i % 2 ? shade(P.mustard, 0.45) : shade(P.mustard, 0.62), { x: cx, y: cy, depth: 0, edge: false });
  }
  piece(ctx, "disk", shapes.circle(330, 70), p.renk || P.red, { x: cx, y: cy, depth: 2, amp: 4 });
  piece(ctx, "disk2", shapes.circle(296, 70), P.card, { x: cx, y: cy, depth: 1, amp: 3 });
  if (p.ikon2) icon(ctx, p.ikon2, cx + 210, cy + 280, 230, 1, 2, "k2");
  icon(ctx, p.ikon || "soru", cx, cy, 500, 1, 2, "k1");
  tape(ctx, "kt1", cx + 150, cy - 330, 0.6, 1, 160);
};
const KALIP_NAMES = Object.keys(KALIP);
