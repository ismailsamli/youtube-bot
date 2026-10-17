"""Kapak fotoğrafı (thumbnail): yapay zeka arka planı + büyük, kontrastlı yazı."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .utils import ROOT, tr_upper
from .visuals import fit_16_9

W, H = 1280, 720
FONT_CANDIDATES = [
    ROOT / "assets" / "fonts" / "ArchivoBlack-Regular.ttf",
    *sorted((ROOT / "assets" / "fonts").glob("*.ttf")),
    Path("C:/Windows/Fonts/impact.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("/System/Library/Fonts/Supplemental/Impact.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int) -> list:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def make_thumbnail(background: Path, text: str, out: Path) -> Path:
    """Kanal tarzı kapak: kâğıt diorama arka plan + yırtık kenarlı krem kâğıt üzerinde büyük yazı,
    son satır kırmızı kâğıt şerit üzerinde, kırmızı bant."""
    import random
    from .collage import _tape, _torn_mask
    rnd = random.Random(len(text))
    if background and Path(background).exists():
        bg = fit_16_9(Image.open(background).convert("RGB"), W, H, style=False)
    else:
        bg = Image.new("RGB", (W, H), (236, 226, 206))
    bg = ImageEnhance.Contrast(bg).enhance(1.12)
    bg = ImageEnhance.Color(bg).enhance(1.15)

    words = tr_upper(text.strip()).split()
    if len(words) > 4:          # kapakta en fazla 3 kelime: telefonda okunabilsin
        words = words[:3]
    text = " ".join(words)
    card_w, pad = int(W * 0.56), 40
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    max_w = card_w - 2 * pad
    size = 170
    while size > 54:
        font = _font(size)
        lines = _wrap(probe, text, font, max_w)
        if len(lines) <= 3 and all(probe.textlength(l, font=font) <= max_w for l in lines):
            break
        size -= 6
    font = _font(size)
    lines = _wrap(probe, text, font, max_w)
    line_h = int(size * 1.12)
    card_h = min(H - 90, line_h * len(lines) + 2 * pad + 10)

    card = Image.new("RGB", (card_w, card_h), (246, 238, 222))
    cd = ImageDraw.Draw(card)
    y = (card_h - line_h * len(lines)) // 2
    for i, line in enumerate(lines):
        last = i == len(lines) - 1 and len(lines) > 1
        tw = probe.textlength(line, font=font)
        if last:   # son satır kırmızı kâğıt şerit üzerinde
            cd.rectangle([pad - 14, y + int(size * 0.08), pad + tw + 14, y + int(size * 1.08)], fill=(184, 30, 42))
            cd.text((pad, y), line, font=font, fill=(250, 244, 232))
        else:
            cd.text((pad, y), line, font=font, fill=(30, 26, 23))
        y += line_h
    mask = _torn_mask(card_w, card_h, rnd.randint(0, 999), amp=10)
    ang = rnd.uniform(-3, -1)
    card = card.rotate(ang, expand=True, resample=Image.BICUBIC)
    mask = mask.rotate(ang, expand=True, resample=Image.BICUBIC)
    x0, y0 = 34, (H - card.height) // 2
    shadow = Image.new("L", (W, H), 0)
    shadow.paste(mask, (x0 + 12, y0 + 16))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.6))
    bg = Image.composite(Image.new("RGB", (W, H), (40, 30, 24)), bg, shadow)
    bg.paste(card, (x0, y0), mask)
    t = _tape(rnd.randint(0, 999), -35)
    t = t.resize((int(t.width * 0.65), int(t.height * 0.65)))
    bg.paste(t, (max(0, x0 - 70), max(0, y0 - 62)), t)

    bg = bg.filter(ImageFilter.UnsharpMask(radius=2, percent=50))
    quality = 92
    while True:
        bg.save(out, "JPEG", quality=quality)
        if out.stat().st_size < 1_900_000 or quality < 60:  # YouTube sınırı 2 MB
            break
        quality -= 8
    return out
