"""Kanal fragmanı (≈50 sn, 16:9): klon sesle okunur, kanal kimliğiyle (kâğıt kolaj) kurgulanır.

Kullanım:
  python tools/fragman.py deneme   → videoyu üretir, onizleme_kesit/fragman/ klasörüne koyar (YÜKLEMEZ)
  python tools/fragman.py yukle    → onizleme_kesit/fragman/fragman.mp4'ü herkese açık yükler ve
                                     kanal sayfasında "abone olmayanlara gösterilen fragman" yapar
"""
import random
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import editor, tts  # noqa: E402
from bot.collage import _paper_bg, _torn_mask  # noqa: E402
from bot.utils import load_config, log, media_duration  # noqa: E402
from bot.visuals import VisualFinder  # noqa: E402

HEDEF = ROOT / "onizleme_kesit" / "fragman"
W, H = 1920, 1080
RED, DARK, CREAM = (183, 31, 46), (32, 28, 26), (248, 243, 232)
FONT = ROOT / "assets" / "fonts" / "ArchivoBlack-Regular.ttf"

# Sahneler: "prompt" olanlar yapay zekâ çizimi, "kart" olanlar kanal kimliği kartı
SAHNELER = [
    {"text": "Bir adam, haritada bile olmayan bir ülkeyi Londra'nın göbeğinde sattı.",
     "prompt": "busy 1820s London street, a large printed poster advertising a tropical paradise land with "
               "palm trees, gentlemen in top hats looking at it, sailing ships in the distance"},
    {"text": "Dev bir kripto borsası, birkaç gün içinde milyarlarca doları buharlaştırdı.",
     "prompt": "giant glowing trading screen with red falling chart lines, golden coins crumbling and "
               "falling into darkness, empty modern office at night"},
    {"text": "Ve evrenin derinliklerinde, Güneş'ten on milyarlarca kat ağır bir kara delik duruyor.",
     "prompt": "enormous black hole in deep space with a blazing bright accretion disk, tiny sun far away "
               "for scale, stars and galaxies around"},
    {"text": "Merhaba, burası Kırmızı Kravat.", "kart": "isim"},
    {"text": "Bu kanalda tarihin, bilimin ve insan beyninin pek bilinmeyen dosyalarını açıyoruz.",
     "kart": "slogan"},
    {"text": "Vurgun Dosyaları'nda dünyayı kandıran dolandırıcıların izini sürüyoruz.",
     "kart": "seri", "seri": "VURGUN DOSYALARI"},
    {"text": "Çözülemeyen Gizemler'de hâlâ cevabı olmayan soruları masaya yatırıyoruz.",
     "kart": "seri", "seri": "ÇÖZÜLEMEYEN GİZEMLER"},
    {"text": "İnsan Vücudu ve Beyin serisinde, kendi bedenini hiç tanımadığın bir yönden göreceksin.",
     "kart": "seri", "seri": "İNSAN VÜCUDU VE BEYİN"},
    {"text": "Her akşam saat yedide yeni bir dosya açılıyor. Bir sonrakini kaçırmamak için abone ol.",
     "kart": "abone"},
]


def _f(s):
    return ImageFont.truetype(str(FONT), s)


def _etiket(text, size, fg, bg, px=40, py=22):
    f = _f(size)
    b = f.getbbox(text)
    c = Image.new("RGB", (b[2] - b[0] + 2 * px, b[3] - b[1] + 2 * py), bg)
    ImageDraw.Draw(c).text((px - b[0], py - b[1]), text, font=f, fill=fg)
    return c


def _yapistir(bg, card, cx, y, seed, ang):
    """Kartı yırtık kenar + gölgeyle yatayda ortalayarak yapıştırır."""
    m = _torn_mask(*card.size, seed, amp=10)
    card = card.rotate(ang, expand=True, resample=Image.BICUBIC)
    m = m.rotate(ang, expand=True, resample=Image.BICUBIC)
    x = cx - card.width // 2
    sh = Image.new("L", bg.size, 0)
    sh.paste(m, (x + 12, y + 16))
    sh = sh.filter(ImageFilter.GaussianBlur(16)).point(lambda p: int(p * 0.5))
    bg.paste(Image.composite(Image.new("RGB", bg.size, (90, 70, 55)), bg, sh))
    bg.paste(card, (x, y), m)
    return x, card.width


def _bant(bg, x, y, ang, seed):
    t = Image.new("RGBA", (220, 58), RED + (215,))
    t.putalpha(ImageChops.multiply(t.split()[3], _torn_mask(220, 58, seed, amp=6)))
    t = t.rotate(ang, expand=True, resample=Image.BICUBIC)
    bg.paste(t, (x, y), t)


def _logo(s):
    return Image.open(ROOT / "assets" / "filigran.png").convert("RGBA").resize((s, s), Image.LANCZOS)


def kart(sc: dict, idx: int) -> Image.Image:
    """Altyazı alanı (alt ~%25) boş kalacak şekilde kanal kimliği kartı."""
    bg = _paper_bg(idx).copy()
    cx = W // 2
    tur = sc["kart"]
    if tur == "isim":
        lg = _logo(300)
        bg.paste(lg, (cx - 150, 110), lg)
        x, w = _yapistir(bg, _etiket("KIRMIZI KRAVAT", 130, CREAM, RED), cx, 450, 7, -1.5)
        _bant(bg, x - 120, 420, -35, 3)
    elif tur == "slogan":
        x, w = _yapistir(bg, _etiket("TARİHİN, BİLİMİN VE İNSANIN", 70, DARK, CREAM), cx, 230, 11, -1)
        _bant(bg, x - 130, 195, -35, 4)
        _yapistir(bg, _etiket("BİLİNMEYEN DOSYALARI", 96, CREAM, RED), cx, 400, 12, 1.2)
    elif tur == "seri":
        lg = _logo(150)
        bg.paste(lg, (cx - 75, 120), lg)
        _yapistir(bg, _etiket("SERİ", 54, DARK, CREAM, 30, 14), cx, 320, 20 + idx, -2)
        x, w = _yapistir(bg, _etiket(sc["seri"], 104, CREAM, RED), cx, 440, 30 + idx, 1)
        _bant(bg, x + w - 90, 405, -35, 5 + idx)
    elif tur == "abone":
        _yapistir(bg, _etiket("HER GÜN 19:00", 120, DARK, CREAM), cx, 170, 41, -1.5)
        x, w = _yapistir(bg, _etiket("ABONE OL", 120, CREAM, RED, 60, 28), cx + 90, 420, 42, 1.5)
        lg = _logo(190)
        bg.paste(lg, (x - 230, 425), lg)
    return bg


def uret(cfg: dict) -> Path:
    work = ROOT / "output" / "fragman"
    (work / "visuals").mkdir(parents=True, exist_ok=True)
    log("Fragman sesi okunuyor (klon ses)...")
    audios = tts.voice_scenes(SAHNELER, cfg, work / "audio")
    finder = VisualFinder(cfg, work / "visuals")
    visuals = []
    for i, sc in enumerate(SAHNELER):
        img = work / "visuals" / f"visual_{i:03d}.png"
        if "kart" in sc:
            kart(sc, i).save(img, "PNG")
        elif not img.exists():
            if not finder.ai_image(sc["prompt"], img):
                finder.commons_image(" ".join(sc["prompt"].split()[:3]), img)
            finder._finish(img, i)
        visuals.append((img, "image"))
    final = work / "fragman.mp4"
    editor.assemble(SAHNELER, visuals, audios, work / "scenes", final, cfg)
    log(f"Fragman hazır: {media_duration(final):.1f} sn")
    return final


def yukle(cfg: dict) -> None:
    from bot import uploader
    video = HEDEF / "fragman.mp4"
    if not video.exists():
        sys.exit("HATA: önce 'deneme' ile fragman üretilmeli (onizleme_kesit/fragman/fragman.mp4 yok).")
    meta = {"title": "Kırmızı Kravat'a hoş geldin | Bilinmeyen hikâyelerin dosyası",
            "description": "Kırmızı Kravat: tarihin, bilimin ve insan beyninin pek bilinmeyen dosyaları.\n\n"
                           "Seriler: Vurgun Dosyaları • Çözülemeyen Gizemler • İnsan Vücudu ve Beyin\n"
                           "Her akşam 19:00'da yeni bir dosya. Kaçırmamak için abone ol.",
            "tags": ["kırmızı kravat", "belgesel", "ilginç bilgiler", "tarih", "bilim"]}
    vid = uploader.upload(video, None, meta, cfg, None)        # yayın saati yok → herkese açık
    yt = uploader.get_service()
    ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
    bs = ch.get("brandingSettings", {})
    c = bs.get("channel", {})
    c["unsubscribedTrailer"] = vid
    body = {"id": ch["id"], "brandingSettings": {"channel": c}}
    if bs.get("watch"):
        body["brandingSettings"]["watch"] = bs["watch"]
    try:
        yt.channels().update(part="brandingSettings", body=body).execute()
        log(f"Fragman kanal sayfasına eklendi (abone olmayanlara gösterilir): https://youtu.be/{vid}")
    except Exception as e:
        log(f"Video yüklendi ama fragman olarak ayarlanamadı ({str(e)[:200]}). "
            f"Studio > Özelleştirme > Düzen'den elle seçilebilir: https://youtu.be/{vid}")


def main():
    mod = sys.argv[1] if len(sys.argv) > 1 else "deneme"
    cfg = load_config()
    random.seed(7)
    if mod == "yukle":
        yukle(cfg)
        return
    final = uret(cfg)
    HEDEF.mkdir(parents=True, exist_ok=True)
    shutil.copy(final, HEDEF / "fragman.mp4")
    for i in range(len(SAHNELER)):                 # telefondan bakmak için kareler
        v = ROOT / "output" / "fragman" / "visuals" / f"visual_{i:03d}.png"
        if v.exists():
            Image.open(v).convert("RGB").resize((640, 360)).save(HEDEF / f"sahne_{i + 1}.jpg", quality=85)
    log("Deneme fragmanı onizleme_kesit/fragman/ klasörüne kondu (YouTube'a yüklenmedi).")


if __name__ == "__main__":
    main()
