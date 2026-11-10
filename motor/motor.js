// ============================================================================
// Zaman çizelgesi: plan.json'u okur, her kareyi seek(t) ile çizer.
// Geçişler: "kaydir" (kamera yana kayar), "yaprak" (yeni kâğıt sayfa üstten kapanır), "kesme".
// ============================================================================
let PLAN = null, W = 1920, H = 1080, DIKEY = false;
const cv = document.getElementById("c"), ctx = cv.getContext("2d");
const TR = 0.55;   // geçiş süresi (sn)
const _err = new Set();

function setup(plan) {
  PLAN = plan; W = plan.w; H = plan.h; DIKEY = H > W;
  cv.width = W; cv.height = H;
  GRAIN = makeGrain(384, 11); GRAIN_PAT = ctx.createPattern(GRAIN, "repeat");
  let t = 0;
  plan.sahneler.forEach((s, i) => { s.i = i; if (s.bas == null) s.bas = t; t = s.bas + s.sure; });
  plan.sure = plan.sure || t;
}

function background(off) {
  ctx.fillStyle = P.cream; ctx.fillRect(0, 0, W, H);
  ctx.save(); ctx.translate(-(off % 384), 0); ctx.globalCompositeOperation = "multiply"; ctx.globalAlpha = 0.5;
  ctx.fillStyle = GRAIN_PAT; ctx.fillRect(0, 0, W + 400, H); ctx.restore();
  // soluk büyük kâğıt şekiller (parallaks)
  ctx.save(); ctx.translate(-(off * 0.4) % (W * 3), 0);
  for (let k = -1; k < 6; k++) {
    const i = ((k % 6) + 6) % 6, x = k * W * 0.55 + 200, y = i % 2 ? H * 0.15 : H * 0.85;
    piece(ctx, "bgc" + i, shapes.circle(DIKEY ? 300 : 260 + (i % 3) * 60, 44), shade(i % 3 === 0 ? P.sage : i % 3 === 1 ? P.blue : P.mustard, 0.66), { x, y, depth: 0, edge: false });
  }
  ctx.restore();
}

function drawScene(s, ts, opts = {}) {
  const S = { W, H, dikey: DIKEY, ts: Math.max(0, ts), d: Math.max(0.5, s.sure), t: s.bas + Math.max(0, ts), p: s.p || {}, id: "s" + s.i + "_", kapak: !!opts.kapak };
  S.A = area(S);
  const u = Math.min(1, S.ts / S.d);
  ctx.save();
  // sahne boyunca hafif yaklaşma (kamera nefesi)
  const z = 1 + 0.035 * ease.inOut(u);
  ctx.translate(W / 2, H * 0.45); ctx.scale(z, z); ctx.translate(-W / 2, -H * 0.45);
  try { (KALIP[s.kalip] || KALIP.nesne)(ctx, S); }
  catch (e) { if (!_err.has(s.i)) { _err.add(s.i); console.log("HATA sahne " + s.i + " (" + s.kalip + "): " + e.message); } }
  ctx.restore();
}

// ---------- altyazı şeridi ----------
function subtitle(t) {
  const a = (PLAN.altyazi || []).find(q => t >= q.a && t < q.b);
  if (!a) return;
  const size = DIKEY ? 58 : 46, maxW = DIKEY ? 920 : 1500;
  const f = fit(ctx, a.metin, size, "bold", maxW, 2, 34);
  const lh = f.size * 1.22, w = Math.max(...f.lines.map(l => textW(ctx, l, f.size, "bold"))) + 56, h = lh * f.lines.length + 26;
  const cy = DIKEY ? 1480 : H - 92 - (f.lines.length - 1) * lh / 2;
  const pop = ease.out(win(t, a.a, a.a + 0.12));
  ctx.save(); ctx.translate(W / 2, cy + (1 - pop) * 8);
  piece(ctx, "sub" + Math.round(w / 30) + "_" + f.lines.length, shapes.crect(w, h), P.charcoal, { depth: 2, amp: 1.4, alpha: 0.95 });
  f.lines.forEach((l, i) => txt(ctx, l, 0, -h / 2 + 13 + lh * (i + 1) - f.size * 0.22, f.size, P.card, "bold", "center"));
  ctx.restore();
}

// ---------- kalıcı öğeler ----------
function overlays(t) {
  if (PLAN.ust_baslik) {   // Short üst başlık kartı
    const k = ease.out(win(t, 0, 0.5));
    const f = fit(ctx, upTR(PLAN.ust_baslik), 92, "head", 900, 2, 48);
    const lh = f.size * 1.12, h = lh * f.lines.length + 60, w = 960;
    ctx.save(); ctx.translate(W / 2, 160 + h / 2 - (1 - k) * 300); ctx.rotate(-0.012);
    piece(ctx, "ub" + f.lines.length, shapes.crect(w, h), P.card, { depth: 3, amp: 2 });
    f.lines.forEach((l, i) => {
      const y = -h / 2 + 30 + lh * (i + 1) - f.size * 0.2, last = i === f.lines.length - 1 && f.lines.length > 1;
      if (last) { const tw = textW(ctx, l, f.size, "head"); piece(ctx, "ubr" + Math.round(tw / 40), shapes.rect(tw + 30, f.size * 1.02), P.red, { x: -tw / 2 - 15, y: y - f.size * 0.86, depth: 0, amp: 1.5 }); }
      txt(ctx, l, 0, y, f.size, last ? P.card : P.charcoal, "head", "center");
    });
    tape(ctx, "ubt", -w / 2 - 20, -h / 2 - 6, -0.55, k);
    ctx.restore();
  }
  if (PLAN.seri && !DIKEY) {  // seri sekmesi
    const k = ease.out(win(t, 0.3, 0.9));
    const s = upTR(PLAN.seri), w = textW(ctx, s, 26, "bold") + 44;
    piece(ctx, "seri" + Math.round(w / 20), shapes.rect(w, 52), P.red, { x: W - w - 40 + (1 - k) * 300, y: 34, depth: 2, amp: 1.5 });
    txt(ctx, s, W - w / 2 - 40 + (1 - k) * 300, 70, 26, P.card, "bold", "center");
  }
}

// ---------- kare çiz ----------
function sceneAt(t) {
  const sc = PLAN.sahneler; let i = 0;
  while (i + 1 < sc.length && t >= sc[i + 1].bas) i++;
  return i;
}
window.seek = function (t) {
  const sc = PLAN.sahneler, i = sceneAt(t), s = sc[i];
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  // bir sonraki sahnenin geçişi başladı mı?
  const nx = sc[i + 1], into = nx ? t - (nx.bas - TR * 0.6) : -1;
  const inTr = nx && into > 0 && (nx.gecis || "kaydir") !== "kesme";
  // önceki geçişin bitişi (yeni sahne başında)
  const pv = i > 0 ? sc[i - 1] : null, since = t - s.bas;
  const prevTr = pv && since < TR * 0.4 && (s.gecis || "kaydir") !== "kesme";
  let A = null, B = null, k = 0, kind = "kaydir";
  if (inTr) { A = s; B = nx; k = into / TR; kind = nx.gecis || "kaydir"; }
  else if (prevTr) { A = pv; B = s; k = (since + TR * 0.6) / TR; kind = s.gecis || "kaydir"; }
  k = ease.inOut(Math.min(1, k));
  const off = (A ? A.i + k : i) * W;
  background(off);
  if (!A) drawScene(s, t - s.bas);
  else if (kind === "yaprak") {
    drawScene(A, t - A.bas);
    // yeni sayfa sağ üstten kayarak kapanır
    const x = (1 - k) * (W + 120), y = (1 - k) * -80, rot = (1 - k) * 0.06;
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot);
    piece(ctx, "sheet", shapes.rect(W + 60, H + 60), P.cream, { x: -10, y: -30, depth: 3, amp: 5, step: 16 });
    ctx.beginPath(); ctx.rect(-10, -30, W + 60, H + 60); ctx.clip();
    drawScene(B, t - B.bas);
    ctx.restore();
  } else {
    ctx.save(); ctx.translate(-k * W, 0); drawScene(A, t - A.bas); ctx.restore();
    ctx.save(); ctx.translate((1 - k) * W, 0); drawScene(B, t - B.bas); ctx.restore();
  }
  if (!PLAN.yazisiz) { overlays(t); subtitle(t); }
};
// kapak için: sahneyi yazısız çiz
window.kapak = function (i, frac) {
  const s = PLAN.sahneler[i]; ctx.setTransform(1, 0, 0, 1, 0, 0);
  background(i * W); drawScene(s, s.sure * frac, { kapak: true });
};

window.yukle = async function (plan) {
  setup(plan);
  await Promise.all(["40px Archivo", "40px InterB", "40px InterS"].map(f => document.fonts.load(f)));
  window.seek(0);
  return { sure: PLAN.sure, sahne: PLAN.sahneler.length };
};
