"""Kanal kimliği: kâğıt kolaj çerçeve (kâğıt doku zemin, yırtık kenarlı fotoğraf, gölge, kırmızı bant)."""
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

W, H = 1920, 1080
TAPE = (190, 30, 40, 215)       # kanal rengi: kırmızı (Kırmızı Kravat)
PAPER = (236, 226, 206)
_BG_CACHE = {}


def _paper_bg(seed: int) -> Image.Image:
    key = seed % 4                # 4 farklı doku, tekrar tekrar hesaplanmasın
    if key not in _BG_CACHE:
        random.seed(key)
        base = Image.new("RGB", (W, H), PAPER)
        noise = Image.effect_noise((W // 2, H // 2), 28).resize((W, H)).convert("RGB")
        base = Image.blend(base, ImageChops.multiply(base, noise.point(lambda p: 180 + p // 4)), 0.6)
        fib = (Image.effect_noise((W // 6, H // 6), 60).resize((W, H), Image.BICUBIC)
               .filter(ImageFilter.GaussianBlur(2)).convert("RGB"))
        base = Image.blend(base, ImageChops.multiply(base, fib.point(lambda p: 200 + p // 5)), 0.5)
        _BG_CACHE[key] = base
    return _BG_CACHE[key].copy()


def _torn_mask(w: int, h: int, seed: int, amp: float = 10) -> Image.Image:
    rnd = random.Random(seed)
    step = 14
    pts = [(x, rnd.uniform(0, amp)) for x in range(0, w + 1, step)]
    pts += [(w - rnd.uniform(0, amp), y) for y in range(0, h + 1, step)]
    pts += [(x, h - rnd.uniform(0, amp)) for x in range(w, -1, -step)]
    pts += [(rnd.uniform(0, amp), y) for y in range(h, -1, -step)]
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def _tape(seed: int, angle: float) -> Image.Image:
    t = Image.new("RGBA", (230, 60), TAPE)
    t.putalpha(ImageChops.multiply(t.split()[3], _torn_mask(230, 60, seed, amp=6)))
    return t.rotate(angle, expand=True, resample=Image.BICUBIC)


def collage(photo: Image.Image, seed: int) -> Image.Image:
    """16:9 görseli kâğıt zemine yapıştırılmış fotoğraf gibi gösterir."""
    rnd = random.Random(seed)
    bg = _paper_bg(seed)
    pw, ph = int(W * 0.72), int(H * 0.72)
    pic = ImageOps.fit(photo.convert("RGB"), (pw, ph), Image.LANCZOS)
    bw = 22
    card = Image.new("RGB", (pw + 2 * bw, ph + 2 * bw), (250, 246, 236))
    card.paste(pic, (bw, bw))
    mask = _torn_mask(*card.size, seed, amp=12)
    ang = rnd.uniform(-2.5, 2.5)
    card = card.rotate(ang, expand=True, resample=Image.BICUBIC)
    mask = mask.rotate(ang, expand=True, resample=Image.BICUBIC)
    x = (W - card.width) // 2 + rnd.randint(-30, 30)
    y = (H - card.height) // 2 - 40 + rnd.randint(-15, 15)   # altyazıya yer kalsın
    shadow = Image.new("L", (W, H), 0)
    shadow.paste(mask, (x + 14, y + 18))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18)).point(lambda p: int(p * 0.55))
    bg = Image.composite(Image.new("RGB", (W, H), (90, 70, 55)), bg, shadow)
    bg.paste(card, (x, y), mask)
    a = rnd.choice([-38, 38]) + rnd.uniform(-5, 5)
    t1 = _tape(seed + 5, a)
    bg.paste(t1, (x - 60, y - 30), t1)
    t2 = _tape(seed + 9, a).transpose(Image.FLIP_LEFT_RIGHT)
    bg.paste(t2, (x + card.width - t2.width + 60, y + card.height - t2.height + 30), t2)
    return bg
