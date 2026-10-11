"""Kapak fotoğrafı (thumbnail): yapay zeka arka planı + büyük, kontrastlı yazı."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .utils import ROOT, tr_upper
from .visuals import fit_16_9

W, H = 1280, 720
FONT_CANDIDATES = [
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
    if background and Path(background).exists():
        bg = fit_16_9(Image.open(background).convert("RGB"), W, H)
    else:
        bg = Image.new("RGB", (W, H), (20, 24, 36))
    bg = ImageEnhance.Contrast(bg).enhance(1.15)
    bg = ImageEnhance.Color(bg).enhance(1.2)

    # Yazının okunması için soldan sağa koyulaşan gradyan
    shade = Image.new("L", (W, H))
    sd = ImageDraw.Draw(shade)
    for x in range(W):
        sd.line([(x, 0), (x, H)], fill=int(max(0, 210 * (1 - x / (W * 0.75)))))
    bg = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), bg, shade)

    draw = ImageDraw.Draw(bg)
    text = tr_upper(text.strip())
    max_w = int(W * 0.58)
    size = 140
    while size > 50:
        font = _font(size)
        lines = _wrap(draw, text, font, max_w)
        line_h = int(size * 1.08)
        if len(lines) <= 3 and line_h * len(lines) <= H * 0.75 and \
                all(draw.textlength(l, font=font) <= max_w for l in lines):
            break
        size -= 6
    font = _font(size)
    lines = _wrap(draw, text, font, max_w)
    line_h = int(size * 1.08)
    y = (H - line_h * len(lines)) // 2
    colors = [(255, 255, 255), (255, 214, 0)]  # beyaz + son satır sarı vurgu
    for i, line in enumerate(lines):
        color = colors[1] if i == len(lines) - 1 and len(lines) > 1 else colors[0]
        draw.text((60, y), line, font=font, fill=color,
                  stroke_width=max(4, size // 14), stroke_fill=(0, 0, 0))
        y += line_h

    bg = bg.filter(ImageFilter.UnsharpMask(radius=2, percent=60))
    quality = 92
    while True:
        bg.save(out, "JPEG", quality=quality)
        if out.stat().st_size < 1_900_000 or quality < 60:  # YouTube sınırı 2 MB
            break
        quality -= 8
    return out
