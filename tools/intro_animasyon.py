"""Kanal giriş animasyonu (kâğıt kesme / stop-motion tarzı, ~8 sn).

Hikâye: kırmızı kravatlı adam kitaplığı karıştırır, aradığını bulamaz; sandığı karıştırır, yine bulamaz;
bilgisayarın başına oturur, ekranda Kırmızı Kravat açılır, aklına ampul yanar; kamera ekrana dalar → logo.

Çalıştırma:  python tools/intro_animasyon.py   ->  assets/intro_animasyon.mp4
"""
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot.branding import intro_frame, _tie  # noqa: E402
from bot.collage import _paper_bg, _torn_mask  # noqa: E402

W, H = 1920, 1080
FPS = 30
STEP = 2                      # stop-motion: her poz 2 kare tutulur (15 poz/sn)
FONT = ROOT / "assets" / "fonts" / "ArchivoBlack-Regular.ttf"

INK = (30, 26, 23)
RED = (184, 30, 42)
DRED = (143, 21, 32)
SKIN = (238, 200, 165)
HAIR = (72, 50, 38)
JACKET = (54, 60, 78)
JACKET_D = (40, 45, 60)
SHIRT = (248, 244, 234)
PANTS = (48, 46, 52)
SHOE = (28, 24, 22)
WOOD = (150, 98, 60)
WOOD_D = (112, 70, 42)
WALL = (232, 220, 196)
FLOOR = (176, 132, 92)


def font(size):
    return ImageFont.truetype(str(FONT), size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- arka planlar
def room(seed, floor_y=860):
    bg = _paper_bg(seed).resize((W, H))
    d = ImageDraw.Draw(bg, "RGBA")
    d.rectangle([0, 0, W, floor_y], fill=WALL + (150,))
    for x in range(-40, W, 120):                    # duvar kâğıdı çizgileri
        d.rectangle([x, 0, x + 46, floor_y], fill=(214, 198, 168, 90))
    d.rectangle([0, floor_y, W, H], fill=FLOOR + (255,))
    for x in range(0, W, 210):                      # parke
        d.line([x, floor_y, x - 60, H], fill=(150, 108, 72, 255), width=4)
    d.rectangle([0, floor_y - 18, W, floor_y], fill=(120, 84, 56, 255))   # süpürgelik
    return bg


def shadowed(base, layer, off=(10, 14), blur=10, strength=0.45):
    """Kâğıt katman etkisi: katmanın altına yumuşak gölge."""
    a = layer.split()[3]
    sh = Image.new("L", base.size, 0)
    sh.paste(a, off)
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda p: int(p * strength))
    base.paste(Image.new("RGB", base.size, (60, 42, 30)), (0, 0), sh)
    base.paste(layer, (0, 0), layer)


BOOK_COLORS = [(184, 30, 42), (60, 92, 120), (210, 170, 80), (90, 120, 80), (120, 70, 50),
               (230, 220, 200), (70, 60, 90), (196, 110, 60)]


def bookshelf(missing=()):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = 260, 230, 820, 860
    d.rectangle([x0, y0, x1, y1], fill=WOOD)
    d.rectangle([x0 + 24, y0 + 24, x1 - 24, y1 - 10], fill=WOOD_D)
    rnd = random.Random(5)
    books = []
    for r, sy in enumerate((y0 + 24, y0 + 230, y0 + 436)):
        d.rectangle([x0, sy + 180, x1, sy + 206], fill=WOOD)
        x = x0 + 34
        i = 0
        while x < x1 - 70:
            bw, bh = rnd.randint(34, 58), rnd.randint(120, 170)
            key = (r, i)
            if key not in missing:
                col = rnd.choice(BOOK_COLORS)
                d.rectangle([x, sy + 180 - bh, x + bw, sy + 180], fill=col)
                d.rectangle([x + 6, sy + 180 - bh + 20, x + bw - 6, sy + 180 - bh + 28], fill=(250, 240, 220))
            books.append((key, x, sy + 180, bw))
            x += bw + rnd.randint(2, 8)
            i += 1
    return lay, books


def book_sprite(col, bw=46, bh=150):
    im = Image.new("RGBA", (bw, bh), col + (255,))
    ImageDraw.Draw(im).rectangle([6, 20, bw - 6, 28], fill=(250, 240, 220))
    return im


def chest(lid_angle):
    """Ahşap sandık; lid_angle derece (0 kapalı, 100 açık)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = 520, 600, 1020, 860
    if lid_angle > 5:                       # açık kapak: gövdenin arkasında dik duran kapak
        k = min(1.0, lid_angle / 100)
        lt = y0 + 30 - 200 * k
        d.polygon([(x0 + 10, y0 + 30), (x1 - 10, y0 + 30), (x1 - 30, lt), (x0 + 30, lt)], fill=WOOD_D)
        d.polygon([(x0 + 40, y0 + 20), (x1 - 40, y0 + 20), (x1 - 52, lt + 24), (x0 + 52, lt + 24)],
                  fill=(128, 84, 52))
    d.rectangle([x0, y0 + 30, x1, y1], fill=WOOD)
    if lid_angle > 5:
        d.rectangle([x0 + 16, y0 + 30, x1 - 16, y0 + 58], fill=(52, 34, 24))   # iç karanlık
    for yy in (y0 + 110, y0 + 190):
        d.rectangle([x0, yy, x1, yy + 14], fill=WOOD_D)
    for bx in (x0 + 40, x1 - 70):           # pirinç köşe kayışları
        d.rectangle([bx, y0 + 58, bx + 30, y1 - 4], fill=(176, 140, 60))
    # kapak (menteşe arka-üst kenarda; açıldıkça yukarı kalkar ve incelir)
    a = math.radians(lid_angle)
    h = 90 * math.cos(a)
    top = y0 + 30 - 90 * math.sin(a) * 0.9
    pts = [(x0 - 10, y0 + 30 - (0 if lid_angle < 5 else 0)), (x1 + 10, y0 + 30),
           (x1 + 10, y0 + 30 - max(16, h)), (x0 - 10, y0 + 30 - max(16, h))]
    if lid_angle > 5:
        pass
    else:
        d.rounded_rectangle([x0 - 10, y0 - 50, x1 + 10, y0 + 40], radius=30, fill=WOOD_D)
        d.rectangle([x0 + 230, y0 + 10, x1 - 230, y0 + 60], fill=(200, 170, 70))
    return lay


def desk_scene(screen_state, t_screen):
    """Masa, sandalye, monitör. screen_state: 'off' | 'play' | 'logo'"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # masa
    d.rectangle([820, 640, 1700, 680], fill=WOOD)
    d.rectangle([860, 680, 890, 860], fill=WOOD_D)
    d.rectangle([1630, 680, 1660, 860], fill=WOOD_D)
    # monitör
    sx0, sy0, sx1, sy1 = 1030, 300, 1600, 620
    d.rectangle([1290, 620, 1340, 645], fill=(70, 70, 76))
    d.rectangle([1220, 636, 1410, 648], fill=(70, 70, 76))
    d.rounded_rectangle([sx0 - 18, sy0 - 18, sx1 + 18, sy1 + 18], radius=14, fill=(40, 40, 46))
    # klavye
    d.rounded_rectangle([880, 622, 1060, 642], radius=6, fill=(210, 205, 195))
    return lay, (sx0, sy0, sx1, sy1)


def screen_content(state, t):
    sw, sh = 570, 320
    im = Image.new("RGB", (sw, sh), (20, 20, 24))
    d = ImageDraw.Draw(im)
    if state == "off":
        return im
    im.paste((240, 232, 214), [0, 0, sw, sh])
    d = ImageDraw.Draw(im)
    if state == "play":
        r = 46 + 6 * math.sin(t * 10)
        cx, cy = sw // 2, sh // 2
        d.ellipse([cx - r - 20, cy - r - 20, cx + r + 20, cy + r + 20], fill=RED)
        d.polygon([(cx - 18, cy - 30), (cx - 18, cy + 30), (cx + 32, cy)], fill=(250, 246, 236))
        return im
    tie = _tie(0.42)
    im.paste(tie, (40, (sh - tie.height) // 2), tie)
    f = font(46)
    d.text((40 + tie.width + 26, 104), "KIRMIZI", font=f, fill=INK)
    d.text((40 + tie.width + 26, 160), "KRAVAT", font=f, fill=RED)
    return im


def chair():
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([560, 430, 610, 700], radius=16, fill=(140, 40, 40))
    d.rectangle([560, 690, 860, 730], fill=(140, 40, 40))
    d.rectangle([700, 730, 720, 840], fill=(70, 70, 76))
    d.rectangle([620, 840, 800, 856], fill=(70, 70, 76))
    return lay


# ---------------------------------------------------------------- karakter
def limb(d, p, a1, l1, a2, l2, w, col, end=None, end_r=0):
    """Omuz/kalçadan başlayan iki parçalı uzuv. Açılar derece; 0 = aşağı, + = sağa."""
    x, y = p
    e = (x + l1 * math.sin(math.radians(a1)), y + l1 * math.cos(math.radians(a1)))
    h = (e[0] + l2 * math.sin(math.radians(a1 + a2)), e[1] + l2 * math.cos(math.radians(a1 + a2)))
    for a, b in ((p, e), (e, h)):
        d.line([a, b], fill=col, width=w)
    for q in (p, e):
        d.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=col)
    if end:
        d.ellipse([h[0] - end_r, h[1] - end_r, h[0] + end_r, h[1] + end_r], fill=end)
    return h


def man(pose):
    """pose: x, y (kalça), lean, look (-1..1), arms (la1, la2, ra1, ra2), legs, sit, mood, head_tilt"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x, y = pose["x"], pose["y"]
    lean = math.radians(pose.get("lean", 0))
    sit = pose.get("sit", False)

    def T(px, py):          # gövde eğilmesi: kalça etrafında döndür
        return (x + px * math.cos(lean) - py * math.sin(lean), y + px * math.sin(lean) + py * math.cos(lean))

    # bacaklar
    if sit:
        for sx in (-26, 26):
            k = (x + sx + 150, y + 6)
            d.line([(x + sx, y), k], fill=PANTS, width=48)
            d.ellipse([k[0] - 24, k[1] - 24, k[0] + 24, k[1] + 24], fill=PANTS)
            f = (k[0] + 6, k[1] + 150)
            d.line([k, f], fill=PANTS, width=44)
            d.rounded_rectangle([f[0] - 22, f[1] - 8, f[0] + 46, f[1] + 18], radius=8, fill=SHOE)
    else:
        lg = pose.get("legs", (4, -4))
        for sx, a in zip((-26, 26), lg):
            f = limb(d, (x + sx, y), a, 130, -a * 0.4, 130, 46, PANTS)
            d.rounded_rectangle([f[0] - 26, f[1] - 6, f[0] + 40, f[1] + 20], radius=8, fill=SHOE)
    # gövde (ceket + gömlek + kravat)
    body = [T(-66, 10), T(66, 10), T(84, -225), T(-84, -225)]
    d.polygon(body, fill=JACKET)
    d.polygon([T(-34, -225), T(34, -225), T(0, -120)], fill=SHIRT)
    d.polygon([T(-14, -222), T(14, -222), T(9, -202), T(-9, -202)], fill=DRED)       # düğüm
    d.polygon([T(-9, -202), T(9, -202), T(18, -110), T(0, -88), T(-18, -110)], fill=RED)
    d.line([T(-34, -225), T(-6, -120)], fill=JACKET_D, width=6)
    d.line([T(34, -225), T(6, -120)], fill=JACKET_D, width=6)
    for by in (-80, -40):
        bx, byy = T(0, by)
        d.ellipse([bx - 6, byy - 6, bx + 6, byy + 6], fill=JACKET_D)
    # kollar
    la1, la2, ra1, ra2 = pose.get("arms", (8, 10, -8, -10))
    lsh, rsh = T(-80, -210), T(80, -210)
    limb(d, lsh, la1 + math.degrees(lean), 120, la2, 112, 36, JACKET, SKIN, 21)
    limb(d, rsh, ra1 + math.degrees(lean), 120, ra2, 112, 36, JACKET, SKIN, 21)
    # boyun + kafa
    nx, ny = T(0, -235)
    d.rectangle([nx - 16, ny - 26, nx + 16, ny + 6], fill=SKIN)
    tilt = pose.get("head_tilt", 0)
    hx, hy = T(math.sin(math.radians(tilt)) * 10, -300)
    r = 64
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=SKIN)
    d.ellipse([hx - r - 12, hy - 6, hx - r + 12, hy + 22], fill=SKIN)        # kulaklar
    d.ellipse([hx + r - 12, hy - 6, hx + r + 12, hy + 22], fill=SKIN)
    d.chord([hx - r - 4, hy - r - 12, hx + r + 4, hy + r - 30], 180, 360, fill=HAIR)
    d.polygon([(hx - r - 2, hy - 18), (hx - r + 30, hy - 40), (hx - r + 4, hy + 6)], fill=HAIR)
    look = pose.get("look", 0)
    ex = look * 16
    for sx in (-24, 24):
        d.ellipse([hx + sx + ex - 8, hy - 6, hx + sx + ex + 8, hy + 12], fill=INK)
    mood = pose.get("mood", "neutral")
    if mood == "confused":
        d.line([(hx - 38 + ex, hy - 26), (hx - 12 + ex, hy - 20)], fill=HAIR, width=7)
        d.line([(hx + 12 + ex, hy - 18), (hx + 38 + ex, hy - 30)], fill=HAIR, width=7)
        d.arc([hx - 16 + ex, hy + 24, hx + 18 + ex, hy + 44], 200, 340, fill=INK, width=5)
    elif mood == "happy":
        d.line([(hx - 38 + ex, hy - 28), (hx - 12 + ex, hy - 32)], fill=HAIR, width=7)
        d.line([(hx + 12 + ex, hy - 32), (hx + 38 + ex, hy - 28)], fill=HAIR, width=7)
        d.chord([hx - 22 + ex, hy + 14, hx + 22 + ex, hy + 44], 0, 180, fill=INK)
    else:
        d.line([(hx - 10 + ex, hy + 32), (hx + 12 + ex, hy + 32)], fill=INK, width=5)
    return lay, (hx, hy)


def popup(base, text, cx, cy, t, col=INK, bg=(250, 246, 236), size=110):
    """Kafanın üstünde zıplayarak beliren kâğıt balon ('?', '!')."""
    if t <= 0:
        return
    s = min(1.0, t * 3) * (1 + 0.25 * math.sin(min(1.0, t * 3) * math.pi))
    r = int(70 * s)
    if r < 4:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    f = font(max(10, int(size * s)))
    tw = d.textlength(text, font=f)
    d.text((cx - tw / 2, cy - size * s * 0.62), text, font=f, fill=col)
    shadowed(base, lay, off=(6, 8), blur=6)


def bulb(base, cx, cy, t):
    if t <= 0:
        return
    s = min(1.0, t * 3)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    glow = int(60 * s + 10 * math.sin(t * 20))
    d.ellipse([cx - 60 - glow, cy - 60 - glow, cx + 60 + glow, cy + 60 + glow], fill=(255, 226, 120, 70))
    r = int(56 * s)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 214, 90))
    d.rectangle([cx - 24 * s, cy + r - 6, cx + 24 * s, cy + r + 28 * s], fill=(140, 140, 150))
    for k in range(8):
        a = k * math.pi / 4
        d.line([(cx + math.cos(a) * (r + 22), cy + math.sin(a) * (r + 22)),
                (cx + math.cos(a) * (r + 46 * s), cy + math.sin(a) * (r + 46 * s))], fill=(220, 160, 40), width=8)
    shadowed(base, lay, off=(6, 8), blur=6)


def paste_rot(base, sprite, cx, cy, ang):
    sp = sprite.rotate(ang, expand=True, resample=Image.BICUBIC)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)), sp)
    shadowed(base, lay, off=(6, 10), blur=6)


# ---------------------------------------------------------------- sahneler
BG1, BG2, BG3 = room(1), room(2), room(3)
S1, S2, S3, S4 = 2.6, 2.2, 2.1, 1.5          # sahne süreleri (sn)


def shot1(t):
    """Kitaplık: 3 kitap çeker, atar; '?'."""
    base = BG1.copy()
    pulls = [(0.25, (0, 3)), (0.95, (1, 5)), (1.6, (2, 2))]
    missing = {k for tt, k in pulls if t > tt + 0.18}
    shelf, books = bookshelf(missing)
    shadowed(base, shelf, off=(14, 18), blur=14)
    bmap = {k: (x, y, bw) for k, x, y, bw in books}
    # adam: kitaplığın sağında, sola bakıyor
    arm = (-8, 10)
    look, mood, tilt = -1, "neutral", 0
    for tt, k in pulls:
        if tt - 0.2 < t < tt + 0.35:
            arm = (-110, -20)          # sol kol kitaplığa uzanır
    if t > 2.0:
        look, mood = 0, "confused"
        tilt = 8 * math.sin(t * 18) if t < 2.3 else 6
    lay, (hx, hy) = man({"x": 1040, "y": 600, "look": look, "mood": mood, "head_tilt": tilt,
                         "arms": (arm[0], arm[1], -20 if t < 2.0 else -150, -40 if t < 2.0 else 120)})
    shadowed(base, lay, off=(12, 16), blur=12)
    # uçan kitaplar
    for tt, k in pulls:
        u = (t - tt - 0.18) / 0.7
        if 0 <= u <= 1 and k in bmap:
            x, y, bw = bmap[k]
            sx, sy = x + bw / 2, y - 75
            ex, ey = 1350 + 120 * (k[0] - 1), 820
            px = lerp(sx, ex, u)
            py = lerp(sy, ey, u) - 380 * math.sin(math.pi * u)
            paste_rot(base, book_sprite(BOOK_COLORS[(k[0] * 3 + k[1]) % len(BOOK_COLORS)]), px, py, -540 * u)
        elif u > 1 and k in bmap:
            ex, ey = 1350 + 120 * (k[0] - 1), 830
            paste_rot(base, book_sprite(BOOK_COLORS[(k[0] * 3 + k[1]) % len(BOOK_COLORS)]).rotate(90, expand=True),
                      ex, ey, 4 * k[0])
    popup(base, "?", hx + 110, hy - 120, t - 2.0)
    return base


def shot2(t):
    """Sandık: kapak açılır, kâğıtlar uçar, omuz silker; '??'."""
    base = BG2.copy()
    lid = 100 * ease(t / 0.35)
    bend = t < 1.3
    lay_m, (hx, hy) = man({"x": 1180, "y": 600, "lean": -28 if bend else 0, "look": -1 if bend else 0,
                           "mood": "neutral" if bend else "confused",
                           "arms": ((-35 + 25 * math.sin(t * 22), -20, -50 + 25 * math.cos(t * 22), 10) if bend
                                    else (-60, -60, 60, 60))})
    c = chest(lid)
    shadowed(base, c, off=(14, 18), blur=14)
    shadowed(base, lay_m, off=(12, 16), blur=12)
    # uçan kâğıtlar
    rnd = random.Random(9)
    for i in range(6):
        t0 = 0.35 + i * 0.13
        u = (t - t0) / 0.9
        if u <= 0:
            continue
        u = min(u, 1.0)
        sheet = Image.new("RGBA", (90, 110), (250, 246, 232, 255))
        sd = ImageDraw.Draw(sheet)
        for ly in range(18, 100, 16):
            sd.line([(12, ly), (78, ly)], fill=(150, 140, 120), width=3)
        sx = 770 + rnd.randint(-120, 120)
        px = sx + (rnd.choice([-1, 1]) * 260 + rnd.randint(-80, 80)) * u
        py = 620 - 520 * math.sin(math.pi * min(u * 0.9, 0.5) * 1.0) + 420 * max(0, u - 0.55)
        paste_rot(base, sheet, px, py, rnd.randint(-40, 40) + 260 * u * rnd.choice([-1, 1]))
    popup(base, "??", hx + 120, hy - 120, t - 1.35, size=96)
    return base


def shot3(t):
    """Masa: oturur, ekran açılır, Kırmızı Kravat logosu, ampul yanar."""
    base = BG3.copy()
    ch = chair()
    shadowed(base, ch, off=(12, 16), blur=12)
    happy = t > 1.0
    lay_m, (hx, hy) = man({"x": 640, "y": 690, "sit": True, "look": 1, "mood": "happy" if happy else "neutral",
                           "lean": 6 if happy else 0,
                           "arms": (20, 60, 30 + (6 * math.sin(t * 30) if t < 0.6 else 0), 50)})
    dsk, (sx0, sy0, sx1, sy1) = desk_scene(None, t)
    shadowed(base, dsk, off=(14, 18), blur=14)
    state = "off" if t < 0.25 else ("play" if t < 0.75 else "logo")
    scr = screen_content(state, t)
    base.paste(scr, (sx0, sy0))
    shadowed(base, lay_m, off=(12, 16), blur=12)
    bulb(base, hx + 10, hy - 170, t - 1.05)
    return base, (sx0, sy0, sx1, sy1)


def shot4(t, screen_box):
    """Kamera ekrana dalar, kanal logosu."""
    frame, _ = shot3(S3 - 0.01)
    sx0, sy0, sx1, sy1 = screen_box
    u = ease(t / 0.8)
    # kırpma kutusu: tüm kare -> ekran
    cx0, cy0 = lerp(0, sx0, u), lerp(0, sy0 - (sx1 - sx0) * 9 / 16 * 0 + 0, u)
    cw = lerp(W, sx1 - sx0, u)
    ch = cw * 9 / 16
    cy0 = lerp(0, (sy0 + sy1) / 2 - ch / 2, u)
    zoomed = frame.crop((int(cx0), int(cy0), int(cx0 + cw), int(cy0 + ch))).resize((W, H), Image.BICUBIC)
    logo = LOGO
    if t > 0.55:
        k = ease((t - 0.55) / 0.35)
        zoomed = Image.blend(zoomed, logo, k)
    if t > S4 - 0.25:
        k = ease((t - (S4 - 0.25)) / 0.25)
        zoomed = Image.blend(zoomed, Image.new("RGB", (W, H), (0, 0, 0)), k * 0.0)
    return zoomed


def wipe(prev, nxt, u):
    """Yeni sahne yırtık kenarlı bir kâğıt gibi sağdan kayarak gelir."""
    x = int(W * (1 - ease(u)))
    out = prev.copy()
    mask = _torn_mask(W + 40, H, 3, amp=18)
    pane = Image.new("RGB", (W + 40, H))
    pane.paste(nxt, (40, 0))
    pane.paste(nxt.crop((0, 0, 40, H)), (0, 0))
    sh = Image.new("L", (W, H), 0)
    sh.paste(mask, (x - 30, 0))
    sh = sh.filter(ImageFilter.GaussianBlur(20)).point(lambda p: int(p * 0.5))
    out.paste(Image.new("RGB", (W, H), (50, 36, 26)), (0, 0), sh)
    out.paste(pane, (x - 40, 0), mask)
    return out


LOGO = None


def render_frames(outdir: Path):
    global LOGO
    LOGO = intro_frame()
    outdir.mkdir(parents=True, exist_ok=True)
    total = S1 + S2 + S3 + S4
    n = int(round(total * FPS))
    box = (1030, 300, 1600, 620)
    last = None
    WIPE = 0.27
    for i in range(n):
        if i % STEP and last is not None:
            last.save(outdir / f"f{i:04d}.png")
            continue
        t = i / FPS
        if t < S1:
            img = shot1(t)
            if t > S1 - WIPE:
                img = wipe(img, shot2(0), (t - (S1 - WIPE)) / WIPE)
        elif t < S1 + S2:
            tt = t - S1
            img = shot2(tt)
            if tt > S2 - WIPE:
                img = wipe(img, shot3(0)[0], (tt - (S2 - WIPE)) / WIPE)
        elif t < S1 + S2 + S3:
            img, box = shot3(t - S1 - S2)
        else:
            img = shot4(t - S1 - S2 - S3, box)
        # stop-motion titreşimi: kâğıtlar elle oynatılıyormuş gibi
        j = random.Random(i // STEP)
        img = img.rotate(j.uniform(-0.15, 0.15), resample=Image.BICUBIC, center=(W / 2, H / 2), fillcolor=(30, 22, 16))
        img.save(outdir / f"f{i:04d}.png")
        last = img
    return n, total


# ---------------------------------------------------------------- ses
SR = 44100


def tone(freq, dur, vol=0.3, decay=6.0, harm=(1, 0.5, 0.25)):
    t = np.arange(int(SR * dur)) / SR
    s = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harm))
    return vol * s * np.exp(-decay * t)


def noise(dur, vol=0.3, smooth=8, decay=8.0):
    n = np.random.default_rng(1).standard_normal(int(SR * dur))
    if smooth > 1:
        n = np.convolve(n, np.ones(smooth) / smooth, mode="same")
    t = np.arange(len(n)) / SR
    env = np.minimum(1, t * 60) * np.exp(-decay * t)
    return vol * n * env


def thump(vol=0.6):
    t = np.arange(int(SR * 0.25)) / SR
    f = 110 * np.exp(-8 * t)
    return vol * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-14 * t) + noise(0.25, 0.08, 30, 20)


def whoosh(dur=0.35, vol=0.35):
    n = noise(dur, vol, 4, 0)
    t = np.arange(len(n)) / SR
    return n * np.sin(np.pi * t / dur) ** 2


def render_audio(path: Path, total: float):
    out = np.zeros(int(SR * (total + 0.5)))

    def put(sig, at):
        i = int(at * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    # merak motifi (pizzicato)
    notes = {"C": 261.6, "D": 293.7, "E": 329.6, "F": 349.2, "G": 392.0, "A": 440.0, "B": 493.9,
             "C5": 523.3, "E5": 659.3, "G5": 784.0, "Eb": 311.1, "Ab": 415.3, "Bb": 466.2}
    motif = [("C", 0.0), ("E", 0.2), ("G", 0.4), ("F", 0.6), ("E", 0.85), ("D", 1.05),
             ("C", 1.3), ("E", 1.5), ("G", 1.7), ("Ab", 1.95), ("G", 2.15)]
    for nm, at in motif:
        put(tone(notes[nm], 0.35, 0.22, 9), at)
    motif2 = [("A", 0.0), ("C5", 0.2), ("E5", 0.4), ("Eb", 0.65), ("D", 0.9), ("C", 1.2), ("Bb", 1.45)]
    for nm, at in motif2:
        put(tone(notes[nm] if nm not in ("Eb", "D", "C", "Bb") else notes[nm] * 2 / 2, 0.35, 0.2, 9), S1 + at)
    # bas vuruşları
    for b in np.arange(0, S1 + S2 + S3, 0.4):
        put(tone(65.4 if b < S1 + S2 else 87.3, 0.3, 0.25, 10, (1, 0.3)), b)
    # efektler
    for at in (0.43, 1.13, 1.78):
        put(noise(0.18, 0.18, 3, 18), at)            # kitap çekme hışırtısı
    for at in (1.13, 1.83, 2.48):
        put(thump(0.5), at)                          # kitap yere düşer
    put(whoosh(), S1 - 0.27)
    put(noise(0.4, 0.25, 6, 4), S1 + 0.1)            # sandık gıcırtı/hışırtı
    for k in range(6):
        put(noise(0.15, 0.12, 2, 20), S1 + 0.35 + k * 0.13)
    put(whoosh(), S1 + S2 - 0.27)
    put(noise(0.04, 0.25, 1, 60), S1 + S2 + 0.1)     # klik
    put(noise(0.04, 0.25, 1, 60), S1 + S2 + 0.3)
    t3 = S1 + S2 + 1.05
    for f, d in ((1318.5, 0.0), (1760.0, 0.08), (2637.0, 0.16)):   # "ding" — fikir!
        put(tone(f, 0.8, 0.18, 4, (1, 0.2)), t3 + d)
    put(whoosh(0.6, 0.4), S1 + S2 + S3 - 0.1)
    for nm in ("C", "E", "G", "C5"):                 # logo akoru
        put(tone(notes[nm], 1.4, 0.16, 2.2), S1 + S2 + S3 + 0.55)
    put(tone(65.4, 1.4, 0.3, 2.5, (1, 0.4)), S1 + S2 + S3 + 0.55)
    # son 0,25 sn yumuşak bitiş
    n_end = int(SR * total)
    fade = int(SR * 0.25)
    out[n_end - fade:n_end] *= np.linspace(1, 0, fade)
    out = out[:n_end]
    out = out / max(1e-6, np.abs(out).max()) * 0.8
    pcm = (out * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(stereo.tobytes())


def main():
    tmp = ROOT / "data" / "_intro_frames"
    n, total = render_frames(tmp)
    wav = tmp / "ses.wav"
    render_audio(wav, total)
    out = ROOT / "assets" / "intro_animasyon.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                    "-i", str(wav), "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                    "-t", f"{total:.3f}", str(out)], check=True)
    print(out, f"{total:.1f} sn, {n} kare")


if __name__ == "__main__":
    main()
