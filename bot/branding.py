"""Kanal jeneriği: kısa giriş (soğuk açılıştan sonra) ve bitiş ekranı (YouTube bitiş ekranı öğeleri için alan)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .collage import _paper_bg, _tape, _torn_mask
from .utils import ROOT, media_duration, run

W, H = 1920, 1080
INK = (30, 26, 23)
RED = (184, 30, 42)
DARK_RED = (143, 21, 32)
CARD = (250, 246, 236)
FONT = ROOT / "assets" / "fonts" / "ArchivoBlack-Regular.ttf"
INTRO_SECONDS = 3.0
OUTRO_MIN_SECONDS = 12.0
OUTRO_LINE = "Bir sonraki hikâye hemen burada. Kırmızı Kravat'a abone olmayı unutma, görüşmek üzere."


def _font(size: int):
    try:
        return ImageFont.truetype(str(FONT), size)
    except OSError:
        return ImageFont.load_default()


def _tie(scale: float) -> Image.Image:
    """Kanal logosundaki kırmızı kravat (profil fotoğrafıyla aynı çizim)."""
    s = scale
    w, h = int(160 * s), int(400 * s)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = lambda pts: [((x + 80) * s, (y + 10) * s) for x, y in pts]
    d.polygon(P([(-46, 0), (46, 0), (32, 56), (-32, 56)]), fill=DARK_RED)
    d.polygon(P([(-32, 56), (32, 56), (68, 300), (0, 380), (-68, 300)]), fill=RED)
    for a, b in [((-40, 120), (50, 90)), ((-50, 190), (58, 154)), ((-60, 260), (64, 218)), ((-46, 332), (60, 286))]:
        d.line(P([a, b]), fill=DARK_RED, width=max(2, int(12 * s)))
    # kravatın gövdesi dışına taşan çizgileri kes
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.polygon(P([(-46, 0), (46, 0), (32, 56), (-32, 56)]), fill=255)
    md.polygon(P([(-32, 56), (32, 56), (68, 300), (0, 380), (-68, 300)]), fill=255)
    im.putalpha(Image.composite(im.split()[3], Image.new("L", (w, h), 0), mask))
    return im


def _paste_card(bg: Image.Image, card: Image.Image, x: int, y: int, seed: int, angle: float) -> None:
    mask = _torn_mask(*card.size, seed, amp=10)
    card = card.rotate(angle, expand=True, resample=Image.BICUBIC)
    mask = mask.rotate(angle, expand=True, resample=Image.BICUBIC)
    shadow = Image.new("L", bg.size, 0)
    shadow.paste(mask, (x + 14, y + 18))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18)).point(lambda p: int(p * 0.5))
    bg.paste(Image.composite(Image.new("RGB", bg.size, (90, 70, 55)), bg, shadow))
    bg.paste(card, (x, y), mask)


def intro_frame() -> Image.Image:
    bg = _paper_bg(1)
    f1, f2 = _font(124), _font(40)
    tie = _tie(0.9)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    x = 70 + tie.width + 60
    cw, ch = int(x + probe.textlength("KIRMIZI KRAVAT", font=f1) + 90), 420
    card = Image.new("RGB", (cw, ch), CARD)
    d = ImageDraw.Draw(card)
    card.paste(tie, (70, (ch - tie.height) // 2), tie)
    d.text((x, 95), "KIRMIZI", font=f1, fill=INK)
    w1 = d.textlength("KIRMIZI ", font=f1)
    d.text((x + w1, 95), "KRAVAT", font=f1, fill=RED)
    d.text((x + 4, 270), "BİLMEDİĞİN GERÇEKLER", font=f2, fill=INK)
    _paste_card(bg, card, (W - cw) // 2, (H - ch) // 2 - 10, seed=7, angle=-1.2)
    for pos, ang, seed in ((((W - cw) // 2 - 60, (H - ch) // 2 - 70), -32, 3), (((W + cw) // 2 - 150, (H + ch) // 2 - 70), -32, 8)):
        t = _tape(seed, ang)
        bg.paste(t, pos, t)
    return bg


def outro_frame() -> Image.Image:
    """Sol: 'sıradaki video' kutusu, sağ: abone ol dairesi. YouTube Studio'daki bitiş ekranı öğeleri
    bu alanların üstüne yerleştirilir."""
    bg = _paper_bg(2)
    d = ImageDraw.Draw(bg)
    title = _font(76)
    txt = "SIRADAKİ HİKÂYE"
    d.text(((W - d.textlength(txt, font=title)) // 2, 110), txt, font=title, fill=INK)
    # sıradaki video alanı (16:9)
    vx, vy, vw, vh = 170, 300, 960, 540
    box = Image.new("RGB", (vw + 40, vh + 40), CARD)
    bd = ImageDraw.Draw(box)
    bd.rectangle([20, 20, vw + 20, vh + 20], fill=(226, 214, 192))
    lbl = _font(54)
    t2 = "İZLEMEYE DEVAM ET"
    bd.text(((vw + 40 - bd.textlength(t2, font=lbl)) // 2, (vh + 40) // 2 - 34), t2, font=lbl, fill=(120, 100, 80))
    _paste_card(bg, box, vx - 20, vy - 20, seed=11, angle=0)
    t = _tape(4, -35)
    bg.paste(t, (vx - 80, vy - 60), t)
    # abone ol dairesi
    cx, cy, r = 1500, 560, 190
    circ = Image.new("RGBA", (2 * r + 20, 2 * r + 20), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(circ)
    cdraw.ellipse([10, 10, 2 * r + 10, 2 * r + 10], fill=CARD)
    tie = _tie(0.75)
    circ.paste(tie, ((circ.width - tie.width) // 2, (circ.height - tie.height) // 2), tie)
    sh = Image.new("L", bg.size, 0)
    ImageDraw.Draw(sh).ellipse([cx - r + 14, cy - r + 18, cx + r + 14, cy + r + 18], fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(18)).point(lambda p: int(p * 0.5))
    bg.paste(Image.composite(Image.new("RGB", bg.size, (90, 70, 55)), bg, sh))
    bg.paste(circ, (cx - r - 10, cy - r - 10), circ)
    btn = _font(48)
    bt = "ABONE OL"
    bw = d.textlength(bt, font=btn)
    d.rectangle([cx - bw / 2 - 28, cy + r + 40, cx + bw / 2 + 28, cy + r + 120], fill=RED)
    d.text((cx - bw / 2, cy + r + 50), bt, font=btn, fill=CARD)
    return bg


ENCODE = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]


def make_intro(work: Path, cfg: dict) -> Path:
    out = work / "intro.mp4"
    if out.exists():
        return out
    work.mkdir(parents=True, exist_ok=True)
    anim = ROOT / "assets" / "intro_animasyon.mp4"
    if anim.exists() and cfg["video"].get("intro_animation", True):
        # hazır animasyon (tools/intro_animasyon.py ile üretildi); diğer sahnelerle aynı ayarlarla kodlanır
        fps = cfg["video"]["fps"]
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(anim),
             "-vf", f"scale={W}:{H},fps={fps},setsar=1,format=yuv420p", *ENCODE, out.name], cwd=work)
        return out
    png = work / "intro.png"
    intro_frame().save(png)
    fps = cfg["video"]["fps"]
    d = INTRO_SECONDS
    frames = int(d * fps) + 2
    vf = (f"[0:v]scale={W * 3 // 2}:{H * 3 // 2},"
          f"zoompan=z='max(1.12-0.0035*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},"
          f"setsar=1,format=yuv420p,fade=t=in:st=0:d=0.2,fade=t=out:st={d - 0.3}:d=0.3[v]")
    # kâğıt hışırtısı gibi kısa bir "vuş" sesi + sessizlik
    af = (f"[1:a]highpass=f=500,lowpass=f=4000,afade=t=in:d=0.15,afade=t=out:st=0.2:d=0.45,"
          f"volume=0.6,apad=whole_dur={d}[a]")
    run(["ffmpeg", "-y", "-hide_banner", "-loop", "1", "-i", png.name,
         "-f", "lavfi", "-i", "anoisesrc=d=0.7:c=pink:a=0.5:r=44100",
         "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", f"{d:.2f}",
         *ENCODE, out.name], cwd=work)
    return out


def make_outro(work: Path, cfg: dict, voice: Path = None) -> Path:
    out = work / "outro.mp4"
    if out.exists():
        return out
    work.mkdir(parents=True, exist_ok=True)
    png = work / "outro.png"
    outro_frame().save(png)
    fps = cfg["video"]["fps"]
    speech = media_duration(voice) if voice and voice.exists() else 0
    d = max(OUTRO_MIN_SECONDS, speech + 6)
    if voice and voice.exists():
        audio_in = ["-i", str(voice.resolve())]
        af = f"[1:a]adelay=400|400,apad=whole_dur={d}[a]"
    else:
        audio_in = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        af = f"[1:a]atrim=0:{d}[a]"
    vf = f"[0:v]scale={W}:{H},fps={fps},setsar=1,format=yuv420p,fade=t=in:st=0:d=0.5:color=0xF3EBDD[v]"
    run(["ffmpeg", "-y", "-hide_banner", "-loop", "1", "-i", png.name, *audio_in,
         "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", f"{d:.2f}",
         *ENCODE, out.name], cwd=work)
    return out
