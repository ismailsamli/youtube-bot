// ============================================================================
// Nesne kütüphanesi: her nesne birden çok kâğıt parçasından kurulur.
// Merkez (0,0), yaklaşık 220x220 birimlik kutu. k = 0..1 "kurulma" ilerlemesi:
// parçalar sırayla düşer/kayar ve yerine oturur. t = saniye (titreşim için).
// ============================================================================

// parça listesini sırayla kur: [ad, noktalar, renk, {x,y,rot,depth,from}]
function build(ctx, uid, k, t, list) {
  const n = list.length;
  list.forEach(([name, pts, col, o = {}], i) => {
    const a = win(k, i / (n + 3) * 1.6, i / (n + 3) * 1.6 + 0.45);
    if (a <= 0) return;
    const e = ease.outBack(a), from = o.from || (i % 3 === 0 ? "up" : i % 3 === 1 ? "left" : "right");
    const off = 70 * (1 - e);
    const dx = from === "left" ? -off : from === "right" ? off : 0, dy = from === "up" ? -off : from === "down" ? off : 0;
    piece(ctx, uid + name, pts, col, {
      x: (o.x || 0) + dx, y: (o.y || 0) + dy, rot: (o.rot || 0) + (1 - e) * 0.15 + jig(t, uid + i, 0.006),
      depth: o.depth ?? 1, alpha: Math.min(1, a * 3), edge: o.edge, amp: o.amp ?? 1.8, sx: o.sx, sy: o.sy,
    });
  });
}
const R = shapes;
const poly = (...p) => p;

const ICON = {
  // ---------------- uzay ----------------
  dunya: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["o", R.circle(100), P.blue, { depth: 2 }],
    ["k1", poly([-70, -40], [-30, -70], [10, -55], [5, -15], [-35, 5], [-75, -5]), P.sage, { depth: 0 }],
    ["k2", poly([20, 10], [70, -5], [85, 30], [50, 70], [15, 50]), P.sage, { depth: 0 }],
    ["k3", poly([-55, 40], [-20, 35], [-25, 75], [-50, 70]), shade(P.sage, -0.15), { depth: 0 }],
    ["b", R.ellipse(70, 9), "rgba(255,248,235,0.9)", { y: -82, depth: 0, edge: false }],
  ]),
  gezegen: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["o", R.circle(100), c || P.mustard, { depth: 2 }],
    ["b1", poly([-96, -30], [96, -30], [92, -8], [-92, -8]), P.terra, { depth: 0 }],
    ["b2", poly([-88, 25], [88, 25], [74, 50], [-74, 50]), shade(c || P.mustard, -0.18), { depth: 0 }],
    ["b3", poly([-60, -75], [60, -75], [76, -58], [-76, -58]), shade(P.terra, 0.3), { depth: 0 }],
  ]),
  halkali: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["r1", R.ellipse(150, 30), shade(P.mustard, -0.2), { depth: 1 }],
    ["o", R.circle(80), c || P.mustard, { depth: 2 }],
    ["b1", poly([-78, -10], [78, -10], [74, 10], [-74, 10]), P.terra, { depth: 0 }],
    ["r2", poly([-150, 0], [150, 0], [140, 18], [60, 30], [-60, 30], [-140, 18]), shade(P.mustard, 0.25), { depth: 1 }],
  ]),
  gunes: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["s", R.star(118, 86, 14), P.mustard, { depth: 1, rot: t * 0.1 }],
    ["o", R.circle(78), shade(P.terra, 0.15), { depth: 2 }],
    ["i", R.circle(50), shade(P.mustard, 0.2), { depth: 0 }],
  ]),
  ay: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["o", R.circle(95), shade(P.cream, -0.08), { depth: 2 }],
    ["c1", R.circle(22), shade(P.cream, -0.2), { x: -30, y: -25, depth: 0 }],
    ["c2", R.circle(14), shade(P.cream, -0.2), { x: 35, y: 20, depth: 0 }],
    ["c3", R.circle(10), shade(P.cream, -0.2), { x: -10, y: 50, depth: 0 }],
  ]),
  roket: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["f1", poly([-30, 60], [-70, 110], [-30, 100]), P.terra, { depth: 1 }],
    ["f2", poly([30, 60], [70, 110], [30, 100]), P.terra, { depth: 1 }],
    ["fl", poly([-20, 105], [0, 150 + Math.sin(t * 20) * 12], [20, 105]), P.mustard, { depth: 0 }],
    ["b", poly([-34, -40], [34, -40], [34, 105], [-34, 105]), P.card, { depth: 2 }],
    ["n", poly([-34, -40], [0, -120], [34, -40]), P.red, { depth: 1 }],
    ["w", R.circle(16), P.blue, { y: 0, depth: 0 }],
  ]),
  uydu: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["p1", R.crect(90, 46), P.blue, { x: -95, depth: 1 }],
    ["p2", R.crect(90, 46), P.blue, { x: 95, depth: 1 }],
    ["b", R.crect(70, 80), P.mustard, { depth: 2 }],
    ["d", R.arc(46, Math.PI * 1.1, Math.PI * 1.9), P.card, { y: -30, depth: 1 }],
  ]),
  kara_delik: (ctx, u, k, t, c) => {
    for (let i = 0; i < 3; i++) build(ctx, u + "r" + i, k, t, [["r", R.ellipse(170 - i * 30, 46 - i * 8), [P.mustard, P.terra, shade(P.mustard, 0.3)][i], { rot: -0.25 + Math.sin(t * 0.5 + i) * 0.02, depth: 1 }]]);
    build(ctx, u, k, t, [["o", R.circle(70), P.ink, { depth: 2 }]]);
  },
  yildiz: (ctx, u, k, t, c) => build(ctx, u, k, t, [["s", R.star(100, 42), c || P.mustard, { depth: 2 }]]),

  // ---------------- araçlar ----------------
  ucak: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["w1", poly([-10, -10], [40, -95], [62, -95], [40, -5]), shade(c || P.blue, -0.15), { depth: 1 }],
    ["tl", poly([-120, -8], [-140, -55], [-118, -55], [-92, -8]), shade(c || P.blue, -0.15), { depth: 1 }],
    ["b", poly([-130, -12], [110, -16], [140, 0], [110, 16], [-130, 12]), P.card, { depth: 2 }],
    ["st", poly([-125, -2], [120, -4], [120, 4], [-125, 4]), c || P.red, { depth: 0, edge: false }],
    ["w2", poly([-10, 8], [40, 90], [62, 90], [40, 4]), c || P.blue, { depth: 2 }],
    ["ck", poly([108, -12], [130, -4], [108, -3]), P.charcoal, { depth: 0 }],
  ]),
  gemi: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["m", R.rect(10, 140), P.charcoal, { x: -5, y: -150, depth: 1 }],
    ["s1", poly([10, -140], [90, -20], [10, -20]), P.card, { depth: 1 }],
    ["s2", poly([-10, -120], [-80, -20], [-10, -20]), shade(P.card, -0.05), { depth: 1 }],
    ["h", poly([-130, -10], [130, -10], [95, 50], [-95, 50]), c || P.terra, { depth: 2 }],
    ["hs", poly([-118, 8], [118, 8], [112, 18], [-112, 18]), P.card, { depth: 0, edge: false }],
  ]),
  yuk_gemisi: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["c1", R.crect(50, 34), P.terra, { x: -60, y: -30, depth: 1 }],
    ["c2", R.crect(50, 34), P.blue, { x: -5, y: -30, depth: 1 }],
    ["c3", R.crect(50, 34), P.mustard, { x: 50, y: -30, depth: 1 }],
    ["br", R.crect(36, 60), P.card, { x: 100, y: -42, depth: 1 }],
    ["h", poly([-140, -12], [140, -12], [120, 45], [-120, 45]), P.charcoal, { depth: 2 }],
    ["hs", poly([-130, 2], [130, 2], [126, 10], [-126, 10]), P.red, { depth: 0, edge: false }],
  ]),
  araba: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", poly([-130, 10], [-120, -25], [-60, -30], [-30, -70], [50, -70], [85, -30], [130, -20], [135, 30], [-130, 30]), c || P.red, { depth: 2 }],
    ["w1", poly([-20, -60], [40, -60], [65, -32], [-38, -32]), P.blue, { depth: 0 }],
    ["t1", R.circle(30), P.charcoal, { x: -75, y: 32, depth: 2 }],
    ["t2", R.circle(30), P.charcoal, { x: 80, y: 32, depth: 2 }],
    ["h1", R.circle(12), P.card, { x: -75, y: 32, depth: 0 }],
    ["h2", R.circle(12), P.card, { x: 80, y: 32, depth: 0 }],
  ]),
  tren: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", poly([-140, -60], [100, -60], [140, -10], [140, 40], [-140, 40]), c || P.blue, { depth: 2 }],
    ["w1", R.crect(50, 34), P.card, { x: -95, y: -25, depth: 0 }],
    ["w2", R.crect(50, 34), P.card, { x: -25, y: -25, depth: 0 }],
    ["w3", R.crect(50, 34), P.card, { x: 45, y: -25, depth: 0 }],
    ["s", R.rect(280, 10), P.red, { x: -140, y: 10, depth: 0, edge: false }],
    ["t1", R.circle(18), P.charcoal, { x: -90, y: 46, depth: 1 }],
    ["t2", R.circle(18), P.charcoal, { x: 90, y: 46, depth: 1 }],
  ]),
  denizalti: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.ellipse(140, 42), c || P.mustard, { depth: 2 }],
    ["k", poly([-20, -40], [40, -40], [36, -78], [-12, -78]), shade(c || P.mustard, -0.15), { depth: 1 }],
    ["p", R.rect(6, 40), P.charcoal, { x: 10, y: -118, depth: 0 }],
    ["w1", R.circle(13), P.blue, { x: -60, depth: 0 }], ["w2", R.circle(13), P.blue, { x: -10, depth: 0 }], ["w3", R.circle(13), P.blue, { x: 40, depth: 0 }],
  ]),

  // ---------------- yapılar ----------------
  bina: (ctx, u, k, t, c) => {
    const L = [["b", R.crect(150, 240), c || P.blue, { depth: 2 }]];
    for (let r = 0; r < 6; r++) for (let q = 0; q < 3; q++) L.push(["w" + r + q, R.crect(26, 22), P.card, { x: -44 + q * 44, y: -92 + r * 36, depth: 0, edge: false }]);
    L.push(["r", R.crect(170, 16), P.charcoal, { y: -126, depth: 1 }]);
    build(ctx, u, k, t, L);
  },
  banka: (ctx, u, k, t, c) => {
    const L = [["st", R.crect(260, 22), shade(P.cream, -0.1), { y: 92, depth: 1 }], ["rf", poly([-140, -60], [0, -125], [140, -60]), c || P.terra, { depth: 2 }],
      ["ar", R.crect(270, 18), shade(P.cream, -0.06), { y: -52, depth: 1 }]];
    for (let i = 0; i < 5; i++) L.push(["c" + i, R.crect(24, 130), P.card, { x: -100 + i * 50, y: 20, depth: 1 }]);
    L.push(["coin", R.circle(18), P.mustard, { y: -84, depth: 0 }]);
    build(ctx, u, k, t, L);
  },
  ev: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.crect(190, 140), P.card, { y: 30, depth: 2 }],
    ["r", poly([-120, -30], [0, -130], [120, -30]), c || P.terra, { depth: 2 }],
    ["d", R.crect(46, 76), P.charcoal, { y: 62, depth: 0 }],
    ["w", R.crect(40, 36), P.blue, { x: 55, y: 20, depth: 0 }],
    ["ch", R.crect(24, 46), P.charcoal, { x: 60, y: -88, depth: 1 }],
  ]),
  fabrika: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["ch", R.crect(30, 150), P.charcoal, { x: 90, y: -40, depth: 1 }],
    ["sm", R.circle(30 + Math.sin(t * 2) * 3), shade(P.cream, -0.12), { x: 105, y: -140, depth: 0 }],
    ["b", poly([-140, 100], [-140, -10], [-80, -50], [-80, -10], [-20, -50], [-20, -10], [40, -50], [40, 100]), c || P.terra, { depth: 2 }],
    ["b2", R.crect(100, 110), shade(c || P.terra, -0.15), { x: 90, y: 45, depth: 1 }],
    ["w", R.crect(140, 28), P.mustard, { x: -50, y: 40, depth: 0 }],
  ]),
  saray: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.crect(240, 120), P.card, { y: 50, depth: 2 }],
    ["d", R.arc(70, Math.PI, 2 * Math.PI), c || P.blue, { y: -10, depth: 2 }],
    ["m1", R.crect(18, 150), P.card, { x: -120, y: 0, depth: 1 }], ["m2", R.crect(18, 150), P.card, { x: 120, y: 0, depth: 1 }],
    ["t1", R.tri(30, 40), c || P.blue, { x: -120, y: -92, depth: 0 }], ["t2", R.tri(30, 40), c || P.blue, { x: 120, y: -92, depth: 0 }],
    ["g", R.arc(26, Math.PI, 2 * Math.PI), P.charcoal, { y: 110, depth: 0 }],
  ]),
  hapishane: (ctx, u, k, t, c) => {
    const L = [["f", R.crect(220, 220), P.charcoal, { depth: 2 }], ["i", R.crect(190, 190), shade(P.blue, -0.3), { depth: 0 }]];
    for (let i = 0; i < 5; i++) L.push(["bar" + i, R.crect(12, 200), shade(P.cream, -0.15), { x: -76 + i * 38, depth: 1 }]);
    L.push(["h", R.crect(200, 14), shade(P.cream, -0.15), { y: -40, depth: 1 }]);
    build(ctx, u, k, t, L);
  },
  mahkeme: (ctx, u, k, t, c) => ICON.terazi(ctx, u, k, t, c),

  // ---------------- para ----------------
  para: (ctx, u, k, t, c) => { // altın sikke yığını
    const L = [];
    for (let i = 0; i < 6; i++) L.push(["c" + i, R.ellipse(70, 20), i % 2 ? P.mustard : shade(P.mustard, -0.12), { x: -40, y: 70 - i * 18, depth: 1, from: "up" }]);
    for (let i = 0; i < 4; i++) L.push(["d" + i, R.ellipse(70, 20), i % 2 ? P.mustard : shade(P.mustard, -0.12), { x: 50, y: 70 - i * 18, depth: 1, from: "up" }]);
    L.push(["top", R.circle(46), P.mustard, { x: 60, y: -70, depth: 2 }], ["topi", R.circle(32), shade(P.mustard, 0.25), { x: 60, y: -70, depth: 0 }]);
    build(ctx, u, k, t, L);
  },
  banknot: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["n3", R.crect(240, 120), shade(c || P.sage, -0.1), { x: 20, y: -16, rot: 0.08, depth: 1 }],
    ["n2", R.crect(240, 120), c || P.sage, { x: 10, y: -6, rot: -0.04, depth: 1 }],
    ["n1", R.crect(240, 120), shade(c || P.sage, 0.15), { depth: 2 }],
    ["fr", R.crect(210, 92), shade(c || P.sage, -0.12), { depth: 0, edge: false }],
    ["md", R.circle(32), shade(c || P.sage, 0.35), { depth: 0 }],
    ["band", R.crect(40, 128), P.card, { x: -70, depth: 1 }],
  ]),
  altin: (ctx, u, k, t, c) => {
    const bar = (w) => poly([-w / 2 + 14, -22], [w / 2 - 14, -22], [w / 2, 22], [-w / 2, 22]);
    build(ctx, u, k, t, [
      ["b1", bar(120), P.mustard, { x: -64, y: 50, depth: 2, from: "up" }], ["b2", bar(120), shade(P.mustard, -0.08), { x: 64, y: 50, depth: 2, from: "up" }],
      ["b3", bar(120), shade(P.mustard, 0.1), { x: 0, y: 6, depth: 2, from: "up" }],
      ["s1", poly([-30, -10], [30, -10], [26, -4], [-26, -4]), shade(P.mustard, 0.45), { x: 0, y: 0, depth: 0, edge: false }],
    ]);
  },
  kripto: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["o", R.circle(100), c || P.mustard, { depth: 2 }],
    ["i", R.circle(78), shade(c || P.mustard, 0.2), { depth: 0 }],
    ["ch", R.crect(70, 70), P.charcoal, { depth: 1, rot: 0.785 }],
    ["c2", R.crect(34, 34), c || P.mustard, { depth: 0, rot: 0.785 }],
    ["p1", R.crect(8, 150), P.charcoal, { depth: 0, edge: false }], ["p2", R.crect(150, 8), P.charcoal, { depth: 0, edge: false }],
  ]),
  cuzdan: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["n", R.crect(180, 70), P.sage, { y: -60, rot: -0.1, depth: 1 }],
    ["b", R.crect(220, 140), c || P.terra, { depth: 2 }],
    ["f", R.crect(90, 54), shade(c || P.terra, -0.2), { x: 70, depth: 1 }],
    ["k", R.circle(10), P.mustard, { x: 78, depth: 0 }],
  ]),
  kasa: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.crect(220, 220), c || P.charcoal, { depth: 2 }],
    ["d", R.crect(180, 180), shade(c || P.charcoal, 0.15), { depth: 1 }],
    ["w", R.circle(44), P.mustard, { depth: 1, rot: t * 0.6 }],
    ["w2", R.crect(80, 10), shade(P.mustard, -0.2), { depth: 0, rot: t * 0.6 }],
    ["h", R.crect(16, 60), P.card, { x: 70, depth: 0 }],
  ]),
  grafik_dusus: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["bg", R.crect(240, 180), P.card, { depth: 2 }],
    ["a", poly([-100, -60], [-50, -40], [0, -55], [40, 10], [70, 0], [100, 60], [100, 66], [70, 8], [40, 18], [0, -47], [-50, -32], [-100, -52]), P.red, { depth: 0, edge: false }],
    ["ax", R.crect(210, 6), P.charcoal, { y: 75, depth: 0, edge: false }],
  ]),
  grafik_artis: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["bg", R.crect(240, 180), P.card, { depth: 2 }],
    ["a", poly([-100, 60], [-50, 30], [0, 40], [40, -10], [70, 0], [100, -60], [100, -52], [70, 8], [40, -2], [0, 48], [-50, 38], [-100, 68]), P.sage, { depth: 0, edge: false }],
    ["ax", R.crect(210, 6), P.charcoal, { y: 75, depth: 0, edge: false }],
  ]),
  petrol: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.crect(140, 200), c || P.charcoal, { depth: 2 }],
    ["r1", R.crect(150, 12), shade(c || P.charcoal, 0.3), { y: -50, depth: 1 }], ["r2", R.crect(150, 12), shade(c || P.charcoal, 0.3), { y: 50, depth: 1 }],
    ["d", poly([0, -30], [22, 10], [0, 30], [-22, 10]), P.mustard, { depth: 0 }],
  ]),
  elmas: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", poly([-100, -30], [-50, -90], [50, -90], [100, -30], [0, 100]), c || P.blue, { depth: 2 }],
    ["f1", poly([-100, -30], [100, -30], [0, 100]), shade(c || P.blue, -0.15), { depth: 0 }],
    ["f2", poly([-50, -90], [0, -30], [50, -90]), shade(c || P.blue, 0.3), { depth: 0 }],
  ]),
  tac: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", poly([-110, 60], [-120, -60], [-60, 0], [0, -90], [60, 0], [120, -60], [110, 60]), c || P.mustard, { depth: 2 }],
    ["s", R.crect(220, 26), shade(c || P.mustard, -0.18), { y: 52, depth: 1 }],
    ["g1", R.circle(14), P.red, { y: 52, depth: 0 }], ["g2", R.circle(10), P.blue, { x: -60, y: 52, depth: 0 }], ["g3", R.circle(10), P.blue, { x: 60, y: 52, depth: 0 }],
  ]),

  // ---------------- belgeler ----------------
  belge: (ctx, u, k, t, c) => {
    const L = [["p2", R.crect(170, 220), shade(P.card, -0.06), { x: 18, y: 10, rot: 0.06, depth: 1 }], ["p", R.crect(170, 220), P.card, { depth: 2 }]];
    for (let i = 0; i < 6; i++) L.push(["l" + i, R.rect(i === 0 ? 90 : 120 - (i % 2) * 30, 9), i === 0 ? P.charcoal : shade(P.charcoal, 0.5), { x: -60, y: -80 + i * 26, depth: 0, edge: false }]);
    L.push(["st", R.circle(28), c || P.red, { x: 45, y: 70, depth: 0, alpha: 0.85 }]);
    build(ctx, u, k, t, L);
  },
  gazete: (ctx, u, k, t, c) => {
    const L = [["p", R.crect(230, 250), P.card, { depth: 2 }], ["h", R.rect(190, 26), P.charcoal, { x: -95, y: -105, depth: 0, edge: false }],
      ["img", R.rect(90, 80), shade(c || P.blue, 0), { x: -95, y: -62, depth: 0 }]];
    for (let i = 0; i < 5; i++) L.push(["a" + i, R.rect(85, 7), shade(P.charcoal, 0.5), { x: 8, y: -60 + i * 16, depth: 0, edge: false }]);
    for (let i = 0; i < 5; i++) L.push(["b" + i, R.rect(190, 7), shade(P.charcoal, 0.5), { x: -95, y: 36 + i * 16, depth: 0, edge: false }]);
    build(ctx, u, k, t, L);
  },
  mektup: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.crect(240, 160), P.card, { depth: 2 }],
    ["f", poly([-120, -80], [0, 15], [120, -80]), shade(P.card, -0.08), { depth: 1 }],
    ["s", R.circle(24), c || P.red, { y: 10, depth: 1 }],
  ]),
  kitap: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["pg", R.crect(200, 170), P.card, { x: 8, y: 8, depth: 1 }],
    ["c", R.crect(200, 170), c || P.terra, { depth: 2 }],
    ["sp", R.crect(22, 170), shade(c || P.terra, -0.25), { x: -89, depth: 1 }],
    ["lb", R.crect(110, 30), P.card, { x: 15, y: -30, depth: 0 }],
  ]),
  harita: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["p1", poly([-120, -80], [-40, -95], [-40, 95], [-120, 80]), shade(P.card, -0.03), { depth: 2 }],
    ["p2", poly([-40, -95], [40, -80], [40, 80], [-40, 95]), shade(P.card, -0.1), { depth: 2 }],
    ["p3", poly([40, -80], [120, -95], [120, 95], [40, 80]), shade(P.card, -0.03), { depth: 2 }],
    ["l", poly([-90, -40], [-20, -60], [30, -10], [80, -30], [90, 40], [10, 50], [-60, 30]), P.sage, { depth: 0 }],
    ["pin", poly([0, 0], [-16, -30], [-12, -44], [0, -50], [12, -44], [16, -30]), P.red, { x: 40, y: 10, depth: 1 }],
  ]),
  anahtar: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["h", R.circle(55), c || P.mustard, { x: -80, depth: 2 }], ["hh", R.circle(22), P.cream, { x: -80, depth: 0 }],
    ["s", R.crect(170, 22), c || P.mustard, { x: 30, depth: 2 }],
    ["t1", R.crect(18, 40), c || P.mustard, { x: 80, y: 26, depth: 1 }], ["t2", R.crect(18, 30), c || P.mustard, { x: 110, y: 22, depth: 1 }],
  ]),
  kilit: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["sh", poly([-55, 0], [-55, -60], [-35, -95], [35, -95], [55, -60], [55, 0], [33, 0], [33, -55], [20, -72], [-20, -72], [-33, -55], [-33, 0]), shade(P.cream, -0.25), { depth: 1 }],
    ["b", R.crect(160, 130), c || P.mustard, { y: 50, depth: 2 }],
    ["kh", poly([-10, 30], [10, 30], [6, 70], [-6, 70]), P.charcoal, { depth: 0 }], ["kc", R.circle(14), P.charcoal, { y: 30, depth: 0 }],
  ]),
  terazi: (ctx, u, k, t, c) => {
    const tilt = Math.sin(t * 1.2) * 0.06;
    build(ctx, u, k, t, [
      ["base", R.crect(140, 18), P.charcoal, { y: 110, depth: 1 }], ["p", R.crect(16, 200), P.charcoal, { y: 10, depth: 1 }],
      ["bm", R.crect(240, 12), c || P.mustard, { y: -80, rot: tilt, depth: 2 }],
      ["l", R.arc(50, 0, Math.PI), c || P.mustard, { x: -110, y: -20 - tilt * 110, depth: 2 }],
      ["r", R.arc(50, 0, Math.PI), c || P.mustard, { x: 110, y: -20 + tilt * 110, depth: 2 }],
      ["top", R.circle(14), P.red, { y: -92, depth: 1 }],
    ]);
  },
  kelepce: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["r1", R.circle(62), shade(P.cream, -0.3), { x: -62, depth: 2 }], ["i1", R.circle(40), P.cream, { x: -62, depth: 0, edge: false }],
    ["r2", R.circle(62), shade(P.cream, -0.3), { x: 62, depth: 2 }], ["i2", R.circle(40), P.cream, { x: 62, depth: 0, edge: false }],
    ["ch", R.crect(40, 14), P.charcoal, { depth: 1 }],
  ]),

  // ---------------- insanlar ----------------
  insan: (ctx, u, k, t, c) => build(ctx, u, k, t, [ // yüzsüz siluet, takım elbise + kırmızı kravat
    ["b", poly([-85, 120], [-80, 20], [-55, -10], [55, -10], [80, 20], [85, 120]), c || P.charcoal, { depth: 2 }],
    ["sh", poly([-22, -10], [22, -10], [0, 40]), P.card, { depth: 0 }],
    ["tie", poly([-8, -6], [8, -6], [12, 50], [0, 66], [-12, 50]), P.red, { depth: 1 }],
    ["n", R.crect(30, 24), shade(P.terra, 0.35), { y: -20, depth: 0 }],
    ["h", R.ellipse(46, 54), shade(P.terra, 0.35), { y: -70, depth: 2 }],
    ["hr", R.arc(48, Math.PI * 1.05, Math.PI * 1.95), P.charcoal, { y: -76, depth: 0 }],
  ]),
  kadin: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["hb", R.ellipse(60, 80), P.charcoal, { y: -60, depth: 1 }],
    ["b", poly([-80, 120], [-70, 20], [-45, -10], [45, -10], [70, 20], [80, 120]), c || P.terra, { depth: 2 }],
    ["n", R.crect(28, 24), shade(P.terra, 0.4), { y: -20, depth: 0 }],
    ["h", R.ellipse(42, 52), shade(P.terra, 0.4), { y: -68, depth: 2 }],
    ["hr", R.arc(46, Math.PI * 1.0, Math.PI * 2.0), P.charcoal, { y: -78, depth: 0 }],
  ]),
  kalabalik: (ctx, u, k, t, c) => {
    const one = (id, x, s, col) => build(ctx, u + id, k, t, [
      ["b", poly([-60, 90], [-56, 15], [-38, -8], [38, -8], [56, 15], [60, 90]), col, { x, y: 30, sx: s, sy: s, depth: 1 }],
      ["h", R.circle(34), shade(col, 0.45), { x, y: 30 - 50 * s, sx: s, sy: s, depth: 1 }],
    ]);
    one("a", -120, 0.85, P.sage); one("b", 120, 0.85, P.blue); one("c", -60, 1, P.terra); one("d", 60, 1, P.mustard); one("e", 0, 1.15, P.charcoal);
  },
  polis: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", poly([-85, 120], [-80, 20], [-55, -10], [55, -10], [80, 20], [85, 120]), P.night, { depth: 2 }],
    ["bd", R.star(20, 10, 6), P.mustard, { x: -40, y: 30, depth: 0 }],
    ["n", R.crect(30, 24), shade(P.terra, 0.35), { y: -20, depth: 0 }],
    ["h", R.ellipse(46, 54), shade(P.terra, 0.35), { y: -70, depth: 2 }],
    ["cap", poly([-54, -96], [54, -96], [62, -80], [-62, -80]), P.night, { depth: 1 }], ["cp", R.arc(44, Math.PI, 2 * Math.PI), P.night, { y: -96, depth: 1 }],
  ]),
  bilim_insani: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", poly([-85, 120], [-80, 20], [-55, -10], [55, -10], [80, 20], [85, 120]), P.card, { depth: 2 }],
    ["l", poly([-6, -10], [6, -10], [6, 120], [-6, 120]), shade(P.card, -0.12), { depth: 0, edge: false }],
    ["n", R.crect(30, 24), shade(P.terra, 0.35), { y: -20, depth: 0 }],
    ["h", R.ellipse(46, 54), shade(P.terra, 0.35), { y: -70, depth: 2 }],
    ["g", R.crect(70, 14), P.charcoal, { y: -72, depth: 0 }],
    ["hr", R.arc(48, Math.PI * 1.05, Math.PI * 1.95), shade(P.cream, -0.3), { y: -76, depth: 0 }],
  ]),
  asker: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", poly([-85, 120], [-80, 20], [-55, -10], [55, -10], [80, 20], [85, 120]), P.sage, { depth: 2 }],
    ["bl", R.crect(170, 14), shade(P.sage, -0.3), { y: 60, depth: 0 }],
    ["n", R.crect(30, 24), shade(P.terra, 0.35), { y: -20, depth: 0 }],
    ["h", R.ellipse(46, 54), shade(P.terra, 0.35), { y: -70, depth: 2 }],
    ["hm", R.arc(54, Math.PI, 2 * Math.PI), shade(P.sage, -0.2), { y: -78, depth: 1 }],
  ]),

  // ---------------- zaman ve teknoloji ----------------
  saat: (ctx, u, k, t, c) => {
    build(ctx, u, k, t, [["o", R.circle(110), c || P.card, { depth: 2 }], ["r", R.circle(96), shade(P.card, -0.05), { depth: 0 }]]);
    if (k > 0.5) {
      for (let i = 0; i < 12; i++) piece(ctx, u + "tk" + i, R.crect(6, i % 3 ? 10 : 18), P.charcoal, { x: Math.cos(i * Math.PI / 6) * 80, y: Math.sin(i * Math.PI / 6) * 80, rot: i * Math.PI / 6 + Math.PI / 2, depth: 0, edge: false });
      piece(ctx, u + "hh", poly([-5, 0], [5, 0], [3, -50], [-3, -50]), P.charcoal, { rot: t * 0.15, depth: 1 });
      piece(ctx, u + "mh", poly([-4, 0], [4, 0], [2, -78], [-2, -78]), P.red, { rot: t * 1.2, depth: 1 });
      piece(ctx, u + "c", R.circle(9), P.charcoal, { depth: 1 });
    }
  },
  kum_saati: (ctx, u, k, t, c) => {
    const f = (t * 0.15) % 1;
    build(ctx, u, k, t, [
      ["t", R.crect(170, 20), P.charcoal, { y: -120, depth: 2 }], ["bt", R.crect(170, 20), P.charcoal, { y: 120, depth: 2 }],
      ["g", poly([-70, -110], [70, -110], [10, 0], [70, 110], [-70, 110], [-10, 0]), shade(P.blue, 0.55), { depth: 1 }],
      ["s1", poly([-60 * (1 - f), -100 + 90 * f], [60 * (1 - f), -100 + 90 * f], [6, -6], [-6, -6]), P.mustard, { depth: 0, edge: false }],
      ["s2", poly([-60, 100], [60, 100], [30 * (1 - f) + 6, 100 - 70 * f], [-30 * (1 - f) - 6, 100 - 70 * f]), P.mustard, { depth: 0, edge: false }],
    ]);
  },
  takvim: (ctx, u, k, t, c) => {
    const L = [["b", R.crect(210, 200), P.card, { depth: 2 }], ["h", R.rect(210, 50), c || P.red, { x: -105, y: -100, depth: 1 }],
      ["r1", R.crect(14, 34), P.charcoal, { x: -55, y: -104, depth: 1 }], ["r2", R.crect(14, 34), P.charcoal, { x: 55, y: -104, depth: 1 }]];
    for (let r = 0; r < 3; r++) for (let q = 0; q < 4; q++) L.push(["d" + r + q, R.crect(30, 26), (r === 1 && q === 2) ? P.mustard : shade(P.cream, -0.08), { x: -66 + q * 44, y: -18 + r * 40, depth: 0 }]);
    build(ctx, u, k, t, L);
  },
  bilgisayar: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["m", R.crect(260, 170), P.charcoal, { y: -20, depth: 2 }], ["s", R.crect(234, 142), c || P.blue, { y: -20, depth: 0 }],
    ["l1", R.rect(120, 10), P.card, { x: -100, y: -70, depth: 0, edge: false }], ["l2", R.rect(160, 10), shade(P.card, -0.2), { x: -100, y: -48, depth: 0, edge: false }],
    ["l3", R.rect(90, 10), shade(P.card, -0.2), { x: -100, y: -26, depth: 0, edge: false }],
    ["st", R.crect(40, 40), shade(P.charcoal, 0.2), { y: 80, depth: 1 }], ["bs", R.crect(130, 14), P.charcoal, { y: 102, depth: 1 }],
  ]),
  telefon: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.round(130, 240, 22), P.charcoal, { depth: 2 }], ["s", R.round(112, 200, 10), c || P.blue, { depth: 0 }],
    ["n1", R.round(84, 30, 8), P.card, { y: -60, depth: 1 }], ["n2", R.round(84, 30, 8), P.red, { y: -18, depth: 1 }], ["n3", R.round(84, 30, 8), P.card, { y: 24, depth: 1 }],
  ]),
  sunucu: (ctx, u, k, t, c) => {
    const L = [["b", R.crect(180, 250), P.charcoal, { depth: 2 }]];
    for (let i = 0; i < 5; i++) { L.push(["u" + i, R.crect(156, 36), shade(P.charcoal, 0.25), { y: -96 + i * 48, depth: 1 }]); L.push(["led" + i, R.circle(6), (Math.floor(t * 4 + i) % 3) ? P.sage : P.red, { x: 60, y: -96 + i * 48, depth: 0, edge: false }]); }
    build(ctx, u, k, t, L);
  },
  kamera: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["b", R.round(240, 150, 16), c || P.charcoal, { y: 10, depth: 2 }], ["tp", R.crect(70, 30), c || P.charcoal, { x: -50, y: -75, depth: 1 }],
    ["l", R.circle(56), shade(P.charcoal, 0.3), { y: 10, depth: 1 }], ["li", R.circle(36), P.blue, { y: 10, depth: 0 }],
    ["f", R.crect(36, 20), P.mustard, { x: 85, y: -40, depth: 0 }],
  ]),
  ampul: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["g", R.circle(90), P.mustard, { y: -30, depth: 2 }], ["gi", R.circle(54), shade(P.mustard, 0.4), { y: -40, depth: 0 }],
    ["n", R.crect(80, 30), shade(P.cream, -0.2), { y: 72, depth: 1 }], ["n2", R.crect(70, 22), shade(P.cream, -0.35), { y: 98, depth: 1 }],
  ]),

  // ---------------- bilim ve doğa ----------------
  beyin: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["l", poly([-120, 10], [-110, -50], [-70, -95], [-10, -100], [0, -40], [-10, 70], [-60, 80], [-110, 55]), c || shade(P.terra, 0.35), { depth: 2 }],
    ["r", poly([120, 10], [110, -50], [70, -95], [10, -100], [0, -40], [10, 70], [60, 80], [110, 55]), shade(c || shade(P.terra, 0.35), -0.08), { depth: 2 }],
    ["f1", poly([-90, -40], [-40, -60], [-35, -48], [-85, -28]), shade(P.terra, 0.1), { depth: 0, edge: false }],
    ["f2", poly([30, -20], [90, -45], [92, -32], [36, -8]), shade(P.terra, 0.1), { depth: 0, edge: false }],
    ["f3", poly([-80, 20], [-30, 10], [-30, 22], [-78, 33]), shade(P.terra, 0.1), { depth: 0, edge: false }],
    ["st", poly([-10, 70], [20, 70], [26, 130], [4, 130]), shade(P.terra, 0.2), { depth: 1 }],
  ]),
  kalp: (ctx, u, k, t, c) => {
    const b = 1 + Math.max(0, Math.sin(t * 7)) * 0.05;
    build(ctx, u, k, t, [["h", poly([0, 100], [-110, -10], [-100, -70], [-50, -95], [0, -55], [50, -95], [100, -70], [110, -10]), c || P.red, { depth: 2, sx: b, sy: b }],
      ["hl", R.ellipse(22, 14), shade(c || P.red, 0.4), { x: -55, y: -55, depth: 0, rot: -0.5 }]]);
  },
  dna: (ctx, u, k, t, c) => {
    const L = [];
    for (let i = 0; i < 9; i++) {
      const y = -120 + i * 30, ph = i * 0.7 + t * 1.2, x1 = Math.sin(ph) * 70, x2 = -x1;
      L.push(["r" + i, R.crect(Math.abs(x1 - x2) + 4, 7), shade(P.cream, -0.2), { y, depth: 0, edge: false }]);
      L.push(["a" + i, R.circle(16), P.terra, { x: x1, y, depth: 1 }], ["b" + i, R.circle(16), P.blue, { x: x2, y, depth: 1 }]);
    }
    build(ctx, u, k, t, L);
  },
  hucre: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["o", R.circle(110, 40), c || shade(P.sage, 0.3), { depth: 2 }], ["n", R.circle(40), P.terra, { x: 15, y: -10, depth: 1 }],
    ["m1", R.ellipse(22, 10), P.mustard, { x: -55, y: 40, rot: 0.6, depth: 0 }], ["m2", R.ellipse(22, 10), P.mustard, { x: 60, y: 55, rot: -0.4, depth: 0 }],
    ["m3", R.ellipse(18, 8), P.blue, { x: -50, y: -50, rot: 0.2, depth: 0 }],
  ]),
  virus: (ctx, u, k, t, c) => {
    const L = [];
    for (let i = 0; i < 10; i++) { const a = i / 10 * Math.PI * 2 + t * 0.2; L.push(["sp" + i, R.circle(16), P.red, { x: Math.cos(a) * 104, y: Math.sin(a) * 104, depth: 1 }]); }
    L.push(["o", R.circle(84), c || P.sage, { depth: 2 }], ["i1", R.circle(16), shade(P.sage, -0.2), { x: -25, y: -20, depth: 0 }], ["i2", R.circle(12), shade(P.sage, -0.2), { x: 30, y: 25, depth: 0 }]);
    build(ctx, u, k, t, L);
  },
  ilac: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["a", poly([-100, -30], [0, -30], [0, 30], [-100, 30]), c || P.red, { rot: -0.5, depth: 2 }],
    ["b", poly([0, -30], [100, -30], [100, 30], [0, 30]), P.card, { rot: -0.5, depth: 2 }],
    ["p1", R.circle(26), P.mustard, { x: 70, y: 80, depth: 1 }], ["p2", R.circle(22), P.blue, { x: -80, y: 80, depth: 1 }],
  ]),
  mikroskop: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["base", R.crect(180, 26), P.charcoal, { y: 110, depth: 2 }], ["arm", poly([40, 100], [70, 100], [70, -40], [40, -10]), P.charcoal, { depth: 1 }],
    ["tube", R.crect(46, 150), c || P.blue, { x: -10, y: -40, rot: -0.35, depth: 2 }], ["st", R.crect(120, 14), shade(P.charcoal, 0.3), { x: -10, y: 50, depth: 1 }],
    ["ey", R.crect(36, 30), P.charcoal, { x: -40, y: -118, rot: -0.35, depth: 1 }],
  ]),
  termometre: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["tb", R.round(54, 230, 26), P.card, { y: -20, depth: 2 }], ["f", R.round(20, 150, 10), c || P.red, { y: 10, depth: 0 }],
    ["bl", R.circle(46), c || P.red, { y: 100, depth: 2 }],
  ]),
  ates: (ctx, u, k, t, c) => {
    const w = Math.sin(t * 9) * 6;
    build(ctx, u, k, t, [
      ["a", poly([0, -130 + w], [70, -20], [80, 50], [40, 110], [-40, 110], [-80, 50], [-60, -40], [-30, -10]), P.red, { depth: 2 }],
      ["b", poly([0, -60 - w], [45, 10], [40, 80], [-40, 80], [-45, 20]), P.terra, { y: 20, depth: 1 }],
      ["c", poly([0, -10 + w], [25, 40], [0, 80], [-25, 40]), P.mustard, { y: 20, depth: 0 }],
    ]);
  },
  damla: (ctx, u, k, t, c) => build(ctx, u, k, t, [["d", poly([0, -120], [60, -20], [75, 40], [40, 95], [-40, 95], [-75, 40], [-60, -20]), c || P.blue, { depth: 2 }],
    ["h", R.ellipse(14, 26), shade(P.blue, 0.5), { x: -28, y: 20, rot: 0.3, depth: 0 }]]),
  simsek: (ctx, u, k, t, c) => build(ctx, u, k, t, [["s", poly([20, -130], [-60, 10], [0, 10], [-30, 130], [70, -30], [10, -30], [50, -130]), c || P.mustard, { depth: 2 }]]),
  dag: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["m2", poly([-20, 100], [70, -60], [160, 100]), shade(c || P.blue, -0.2), { depth: 1 }],
    ["m1", poly([-160, 100], [-40, -110], [80, 100]), c || P.blue, { depth: 2 }],
    ["sn", poly([-40, -110], [-70, -58], [-52, -66], [-40, -50], [-25, -66], [-10, -58]), P.card, { depth: 0 }],
  ]),
  agac: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["tr", R.crect(30, 120), shade(P.terra, -0.3), { y: 60, depth: 1 }],
    ["l1", R.circle(80), c || P.sage, { y: -40, depth: 2 }], ["l2", R.circle(56), shade(c || P.sage, -0.15), { x: -60, y: 0, depth: 2 }],
    ["l3", R.circle(56), shade(c || P.sage, 0.12), { x: 60, y: -5, depth: 2 }],
  ]),
  dalga: (ctx, u, k, t, c) => {
    const L = [];
    for (let i = 0; i < 3; i++) {
      const pts = [[-150, 120]]; for (let x = -150; x <= 150; x += 15) pts.push([x, -10 + i * 40 + Math.sin(x / 30 + t * 2 + i) * 14]); pts.push([150, 120]);
      L.push(["w" + i, pts, [shade(P.blue, 0.2), P.blue, shade(P.blue, -0.2)][i], { depth: 1, amp: 1.2 }]);
    }
    build(ctx, u, k, t, L);
  },
  buz: (ctx, u, k, t, c) => {
    const L = [];
    for (let i = 0; i < 6; i++) L.push(["a" + i, R.crect(18, 220), c || P.blue, { rot: i * Math.PI / 3, depth: 1 }]);
    for (let i = 0; i < 6; i++) L.push(["b" + i, R.crect(70, 14), c || P.blue, { x: Math.cos(i * Math.PI / 3 - Math.PI / 2) * 70, y: Math.sin(i * Math.PI / 3 - Math.PI / 2) * 70, rot: i * Math.PI / 3, depth: 1 }]);
    L.push(["c", R.circle(26), P.card, { depth: 2 }]);
    build(ctx, u, k, t, L);
  },
  kafatasi: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["s", poly([-90, -10], [-80, -80], [-30, -115], [30, -115], [80, -80], [90, -10], [60, 30], [55, 80], [-55, 80], [-60, 30]), P.card, { depth: 2 }],
    ["e1", R.circle(26), P.charcoal, { x: -38, y: -15, depth: 0 }], ["e2", R.circle(26), P.charcoal, { x: 38, y: -15, depth: 0 }],
    ["n", R.tri(22, 26), P.charcoal, { y: 30, depth: 0 }],
    ["t", R.crect(70, 10), shade(P.card, -0.2), { y: 64, depth: 0, edge: false }],
  ]),
  silah_yok: null,

  // ---------------- işaretler ----------------
  soru: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["q", poly([-60, -60], [-55, -100], [-15, -125], [35, -125], [70, -100], [75, -55], [45, -20], [20, 0], [20, 40], [-20, 40], [-20, -10], [10, -35], [30, -60], [20, -85], [-10, -88], [-25, -60]), c || P.red, { depth: 2 }],
    ["d", R.circle(24), c || P.red, { y: 90, depth: 2 }],
  ]),
  unlem: (ctx, u, k, t, c) => build(ctx, u, k, t, [["l", poly([-26, -130], [26, -130], [16, 50], [-16, 50]), c || P.red, { depth: 2 }], ["d", R.circle(24), c || P.red, { y: 100, depth: 2 }]]),
  carpi: (ctx, u, k, t, c) => build(ctx, u, k, t, [["a", R.crect(40, 240), c || P.red, { rot: 0.785, depth: 2 }], ["b", R.crect(40, 240), c || P.red, { rot: -0.785, depth: 2 }]]),
  tik: (ctx, u, k, t, c) => build(ctx, u, k, t, [["a", poly([-110, 0], [-70, -40], [-30, 10], [90, -110], [130, -70], [-30, 90]), c || P.sage, { depth: 2 }]]),
  hedef: (ctx, u, k, t, c) => build(ctx, u, k, t, [
    ["a", R.circle(120), P.red, { depth: 2 }], ["b", R.circle(86), P.card, { depth: 1 }], ["c", R.circle(52), P.red, { depth: 1 }], ["d", R.circle(20), P.card, { depth: 1 }],
  ]),
  bayrak: (ctx, u, k, t, c) => {
    const w = Math.sin(t * 3) * 8;
    build(ctx, u, k, t, [["p", R.crect(12, 260), P.charcoal, { x: -100, depth: 1 }],
      ["f", poly([-94, -120], [20, -110 + w], [120, -120], [120, -20], [20, -10 - w], [-94, -20]), c || P.red, { depth: 2 }]]);
  },
  zincir: (ctx, u, k, t, c) => {
    const L = [];
    for (let i = 0; i < 4; i++) L.push(["l" + i, R.ellipse(46, 26), shade(P.cream, -0.3), { x: -105 + i * 70, rot: i % 2 ? 0 : 0.2, depth: 2 }], ["h" + i, R.ellipse(28, 10), P.cream, { x: -105 + i * 70, depth: 0, edge: false }]);
    build(ctx, u, k, t, L);
  },
  kalkan: (ctx, u, k, t, c) => build(ctx, u, k, t, [["s", poly([0, -120], [100, -80], [90, 30], [0, 120], [-90, 30], [-100, -80]), c || P.blue, { depth: 2 }],
    ["i", poly([0, -90], [70, -62], [64, 22], [0, 88]), shade(c || P.blue, 0.25), { depth: 0 }]]),
  ok_yukari: (ctx, u, k, t, c) => build(ctx, u, k, t, [["a", poly([0, -130], [90, -20], [35, -20], [35, 120], [-35, 120], [-35, -20], [-90, -20]), c || P.sage, { depth: 2 }]]),
  ok_asagi: (ctx, u, k, t, c) => build(ctx, u, k, t, [["a", poly([0, 130], [90, 20], [35, 20], [35, -120], [-35, -120], [-35, 20], [-90, 20]), c || P.red, { depth: 2 }]]),
};
delete ICON.silah_yok;
const ICON_NAMES = Object.keys(ICON);

// Nesne çiz: ad bilinmiyorsa "soru" yerine en yakın eşleşmeyi dene
function icon(ctx, name, x, y, size, k, t, uid, color) {
  let f = ICON[name];
  if (!f) {
    const n = String(name || "").toLowerCase();
    const hit = ICON_NAMES.find(i => n.includes(i) || i.includes(n));
    f = ICON[hit] || ICON.belge;
  }
  ctx.save(); ctx.translate(x, y); const s = size / 220; ctx.scale(s, s);
  f(ctx, (uid || name) + ":", k, t, color);
  ctx.restore();
}
