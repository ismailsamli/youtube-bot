"""Uzun videodan dikey Shorts üretir: aynı hikâyenin en çarpıcı anları, aynı çizimler, aynı ses.

Her Short kendi başına anlaşılan 40-55 sn'lik mini bir hikâyedir ve uzun videoya yönlendirir.
Düzen (1080x1920): kâğıt zemin, üstte kırmızı şeritli başlık kartı, ortada yırtık kenarlı çizim, altta altyazı.
"""
import copy
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import editor, tts
from .collage import _tape, _torn_mask
from .utils import ROOT, log, media_duration, run, tr_upper

W, H = 1080, 1920
FONT = ROOT / "assets" / "fonts" / "ArchivoBlack-Regular.ttf"
MAX_SECONDS = 58


def _font(size):
    return ImageFont.truetype(str(FONT), size)


def _paper_v(seed: int) -> Image.Image:
    rnd = random.Random(seed)
    base = Image.new("RGB", (W, H), (236, 226, 206))
    noise = Image.effect_noise((W // 2, H // 2), 28).resize((W, H)).convert("RGB")
    from PIL import ImageChops
    base = Image.blend(base, ImageChops.multiply(base, noise.point(lambda p: 180 + p // 4)), 0.6)
    return base


_BG = {}


def frame(image: Path, headline: str, seed: int) -> Image.Image:
    if "bg" not in _BG:
        _BG["bg"] = _paper_v(1)
    bg = _BG["bg"].copy()
    rnd = random.Random(seed)
    d = ImageDraw.Draw(bg)
    # başlık kartı
    text = tr_upper(headline.strip())
    size = 104
    while size > 52:
        f = _font(size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = f"{cur} {w}".strip()
            if d.textlength(t, font=f) <= W - 200 or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= 3 and all(d.textlength(l, font=f) <= W - 200 for l in lines):
            break
        size -= 6
    lh = int(size * 1.15)
    ch = lh * len(lines) + 70
    card = Image.new("RGB", (W - 120, ch), (250, 246, 236))
    cd = ImageDraw.Draw(card)
    y = 35
    for i, l in enumerate(lines):
        tw = cd.textlength(l, font=f)
        x = (card.width - tw) // 2
        if i == len(lines) - 1 and len(lines) > 1:
            cd.rectangle([x - 14, y + int(size * 0.08), x + tw + 14, y + int(size * 1.08)], fill=(184, 30, 42))
            cd.text((x, y), l, font=f, fill=(250, 244, 232))
        else:
            cd.text((x, y), l, font=f, fill=(30, 26, 23))
        y += lh
    _paste(bg, card, 60, 170, seed, rnd.uniform(-1.5, 1.5))
    # çizim
    try:
        pic = Image.open(image).convert("RGB")
    except Exception:
        pic = Image.new("RGB", (16, 9), (200, 190, 170))
    pw = W - 80
    ph = int(pw * 0.78)
    pic = ImageOps.fit(pic, (pw - 36, ph - 36), Image.LANCZOS)
    pc = Image.new("RGB", (pw, ph), (250, 246, 236))
    pc.paste(pic, (18, 18))
    top = 170 + ch + 70
    _paste(bg, pc, 40, top, seed + 3, rnd.uniform(-2, 2))
    t = _tape(seed + 5, -35)
    bg.paste(t, (10, top - 40), t)
    t2 = _tape(seed + 9, -35)
    bg.paste(t2, (W - t2.width - 10, top + ph - t2.height + 40), t2)
    # alt bilgi
    f2 = _font(34)
    s = "KIRMIZI KRAVAT · TAMAMI KANALDA"
    d = ImageDraw.Draw(bg)
    d.text(((W - d.textlength(s, font=f2)) // 2, H - 250), s, font=f2, fill=(120, 100, 80))
    return bg


def _paste(bg, card, x, y, seed, ang):
    mask = _torn_mask(*card.size, seed, amp=10)
    card = card.rotate(ang, expand=True, resample=Image.BICUBIC)
    mask = mask.rotate(ang, expand=True, resample=Image.BICUBIC)
    sh = Image.new("L", bg.size, 0)
    sh.paste(mask, (x + 12, y + 16))
    sh = sh.filter(ImageFilter.GaussianBlur(16)).point(lambda p: int(p * 0.5))
    bg.paste(Image.composite(Image.new("RGB", bg.size, (90, 70, 55)), bg, sh))
    bg.paste(card, (x, y), mask)


# ---------------------------------------------------------------- senaryo
# Short başına farklı uzunluk: hangi sürenin daha iyi tuttuğunu istatistikten görmek için (test)
# 28 Eki testi: ~50 sn Short'lar ort. 971 izlenme / 10 beğeni; ~30 sn 382 / 2,2; ~40 sn 437 / 3,7 → hepsi ~50 sn
LENGTHS = [(110, 125, "yaklaşık 50 sn"), (110, 125, "yaklaşık 50 sn"), (115, 130, "yaklaşık 55 sn")]
KLON_LENGTHS = [(105, 115, "yaklaşık 50 sn"), (105, 115, "yaklaşık 50 sn"), (110, 120, "yaklaşık 55 sn")]  # 1 Kas: 90-100 kelime 34-40 sn çıktı


def _lengths(cfg: dict) -> list:
    return KLON_LENGTHS if cfg.get("shorts", {}).get("voice_engine") == "klon" else LENGTHS


_SAAT_DE = {"bir": "birde", "iki": "ikide", "üç": "üçte", "dört": "dörtte", "beş": "beşte", "altı": "altıda",
            "yedi": "yedide", "sekiz": "sekizde", "dokuz": "dokuzda", "on": "onda", "yirmi": "yirmide"}


def _saatte(hhmm: str) -> str:
    """'15:00' → 'saat on beşte' (klon ses rakam okumasın diye yazıyla)."""
    from .sayilar import oku
    w = oku(int(hhmm.split(":")[0])).split()
    return "saat " + " ".join(w[:-1] + [_SAAT_DE.get(w[-1], w[-1] + "'de")])


def _bolum_kurali(cfg: dict, count: int) -> str:
    """Günün Short'ları tek hikâyenin bölümleri: 1. bölümü izleyen devamı için kanala gelir (abone dönüşümü)."""
    t = cfg.get("shorts", {}).get("publish_times", ["12:00", "15:00", "21:00"])
    sonlar = []
    for k in range(count):
        if k < count - 1 and k + 1 < len(t):
            sonlar.append(f'{k + 1}. Short son sahne tam olarak: "Devamı {k + 2}. bölümde, bugün {_saatte(t[k + 1])}. '
                          'Kaçırmamak için abone ol."')
        else:
            sonlar.append(f'{k + 1}. Short son sahne tam olarak: "Hikâyenin tamamı kanalda. Her gün yeni bir gerçek '
                          'hikâye için abone ol."')
    return f"""- Bu {count} Short, videonun hikâyesini {count} BÖLÜM halinde, sırayla anlatsın: 1. bölüm en çarpıcı
  an ve hikâyenin başlangıcı, 2. bölüm olayın nasıl geliştiği, son bölüm dönüm noktası ve sonuç.
  Her bölüm yine de tek başına anlaşılsın: ilk cümle doğrudan kanca (izleyici 1 saniyede kaydırmasın),
  önceki bölümü bilmeyen izleyici de takip edebilsin. Bölümler arası tekrar YOK.
- {chr(10).join("  " + x for x in sonlar).strip()}"""


def write_shorts(llm, cfg: dict, script: dict, count: int) -> list:
    from .script_writer import _ask_json, _system
    lines = "\n".join(f"[{i}] {s['text']}" for i, s in enumerate(script["scenes"]))[:14000]
    bolumlu = cfg.get("shorts", {}).get("bolumlu", False) and count >= 2
    kural = _bolum_kurali(cfg, count) if bolumlu else """- Videonun FARKLI bir çarpıcı anını anlatsın (biri en gerilimli an, biri en şaşırtıcı bilgi, biri dönüm noktası).
- KENDİ BAŞINA anlaşılsın: ilk cümle doğrudan kanca (izleyici 1 saniyede kaydırmasın), sonra 3-5 cümlede
  mini hikâye, sonunda merak bırakan bir cümle. Sonucu/sırrın cevabını tamamen VERME.
- Son sahne tam olarak şu olsun: "Hikâyenin tamamı kanalda. Her gün yeni bir gerçek hikâye için abone ol."
  (Short izleyicisi abone olmuyor; bu çağrı net ve kısa kalmalı.)"""
    prompt = f"""Uzun video: "{script['title']}"
Sahneler (numaralı):
{lines}

Bu videodan {count} adet YouTube Shorts senaryosu çıkar. Her Short:
{kural}
- UZUNLUK (sırayla, her Short için farklı): {"; ".join(f"{i + 1}. Short toplam {a}-{b} kelime ({t})" for i, (a, b, t) in enumerate(_lengths(cfg)[:count]))}.
  Sahne başına 12-18 kelime. Sadece videodaki doğru bilgileri kullan.
- Her sahne için "src": o sahneye en uygun görselin bulunduğu uzun video sahne numarası.
- "title": en fazla 70 karakter, merak uyandıran dürüst Türkçe başlık (hashtag yazma).
- "headline": ekranın üstünde duracak 2-5 kelimelik çarpıcı başlık (ör. "72 GÜN KARDA").
- "comment": izleyiciye sorulacak kısa bir soru (yorum için).

Sadece şu JSON'u döndür:
{{"shorts": [{{"title": "...", "headline": "...", "comment": "...", "scenes": [{{"text": "...", "src": 0}}]}}]}}"""
    data = _ask_json(llm, _system(cfg), prompt, 6000, "shorts")
    out = []
    n = len(script["scenes"])
    for s in data.get("shorts", [])[:count]:
        scenes = [sc for sc in s.get("scenes", []) if (sc.get("text") or "").strip()]
        if len(scenes) < 3 or not s.get("title"):
            continue
        for k, sc in enumerate(scenes):
            try:
                sc["src"] = max(0, min(n - 1, int(sc.get("src", 0))))
            except (TypeError, ValueError):
                sc["src"] = min(n - 1, k)
        s["scenes"] = scenes
        s["hedef"] = _lengths(cfg)[min(len(out), len(LENGTHS) - 1)][2]
        if bolumlu:
            s["bolum"] = f"{len(out) + 1}/{count}"
        out.append(s)
    return out


# ---------------------------------------------------------------- üretim
def _visual_for(folder: Path, idx: int) -> Path:
    vis = folder / "visuals"
    for name in (f"visual_{idx:03d}_ham.png", f"visual_{idx:03d}.png"):
        if (vis / name).exists():
            return vis / name
    mp4 = vis / f"visual_{idx:03d}.mp4"
    if mp4.exists():
        png = vis / f"visual_{idx:03d}_kare.png"
        if not png.exists():
            run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", str(mp4), "-frames:v", "1", str(png)])
        return png
    cands = sorted(vis.glob("visual_*_ham.png"))
    return cands[idx % len(cands)] if cands else None


def build_short(cfg: dict, folder: Path, short: dict, n: int) -> Path:
    work = folder / "shorts" / f"s{n}"
    work.mkdir(parents=True, exist_ok=True)
    out = work / "short.mp4"
    if out.exists():
        return out
    scfg = copy.deepcopy(cfg)
    scfg["video"].update({"width": W, "height": H, "subtitle_size": 72, "subtitle_margin_v": 430,
                          "subtitle_margin_lr": 70, "subtitle_words": 4, "music_volume": 0, "zoom_max": 1.05})
    scfg["voice"]["gemini_prefer"] = "lite"     # Short'lar Gemini'nin hafif ses modelini kullanır (ayrı günlük kota)
    if cfg.get("shorts", {}).get("voice_engine"):
        scfg["voice"]["engine"] = cfg["shorts"]["voice_engine"]   # "klon" = kullanıcının klon sesi (olmazsa Gemini)
    audios = tts.voice_scenes(short["scenes"], scfg, work / "audio")
    clips = []
    for i, (sc, au) in enumerate(zip(short["scenes"], audios)):
        img = work / f"kare_{i:02d}.png"
        if not img.exists():
            frame(_visual_for(folder, sc["src"]), short.get("headline") or short["title"], n * 100 + i).save(img)
        clips.append(editor.build_scene(i, img, "image", au, sc["text"], work, scfg))
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    joined = work / "joined.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy",
         joined.name], cwd=work)
    dur = media_duration(joined)
    if dur > MAX_SECONDS:       # 58 sn'yi aşarsa hafifçe hızlandır
        k = min(1.25, dur / MAX_SECONDS)
        run(["ffmpeg", "-y", "-hide_banner", "-i", joined.name, "-filter_complex",
             f"[0:v]setpts=PTS/{k:.4f}[v];[0:a]atempo={k:.4f}[a]", "-map", "[v]", "-map", "[a]",
             *editor.ENCODE, "-movflags", "+faststart", out.name], cwd=work)
    else:
        run(["ffmpeg", "-y", "-hide_banner", "-i", joined.name, "-c", "copy", "-movflags", "+faststart",
             out.name], cwd=work)
    log(f"  Short {n + 1} hazır: {media_duration(out):.0f} sn — {short['title']}")
    return out


def publish_times(cfg: dict, long_publish_iso: str, count: int) -> list:
    sc = cfg.get("shorts", {})
    tz = ZoneInfo(cfg["upload"].get("timezone", "Europe/Istanbul"))
    times = (sc.get("publish_times") or ["12:00", "15:00", "21:00"])[:count]
    base = datetime.fromisoformat(long_publish_iso).astimezone(tz) if long_publish_iso else datetime.now(tz)
    day = (base + timedelta(days=sc.get("day_offset", 1))).date()
    out = []
    for t in times:
        hh, mm = map(int, t.split(":"))
        out.append(datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz))
    return out


def _toplu_klon(cfg: dict, folder: Path, shorts: list) -> None:
    """Günün tüm Short'larının sesini TEK Kaggle işinde okutur (her iş ~5 dk kurulum + bazen uzun GPU kuyruğu;
    1 Kas'ta Short başına 35-48 dk bekledi). Olmazsa her Short kendi sesini ayrı okur."""
    if cfg.get("shorts", {}).get("voice_engine") != "klon":
        return
    import shutil
    try:
        hepsi, yer, dirs = [], [], []
        for n, s in enumerate(shorts):
            work = folder / "shorts" / f"s{n}"
            if (work / "short.mp4").exists() or (work / "audio" / "motor.txt").exists():
                continue
            dirs.append(work / "audio")
            for i, sc in enumerate(s["scenes"]):
                hepsi.append({"text": sc["text"]})
                yer.append(work / "audio" / f"audio_{i:03d}.mp3")
        if not hepsi:
            return
        tmp = folder / "shorts" / "_toplu_ses"
        tmp.mkdir(parents=True, exist_ok=True)
        tts.klon_voice_scenes(hepsi, cfg, tmp)
        for i, hedef in enumerate(yer):
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(tmp / f"audio_{i:03d}.mp3", hedef)
        for d in dirs:
            (d / "motor.txt").write_text("klon")
        log(f"  Short sesleri tek seferde okundu ({len(hepsi)} sahne)")
    except Exception as e:
        log(f"  Short sesleri toplu okunamadı, her Short ayrı okunacak: {str(e)[:200]}")


def make_and_upload(cfg: dict, folder: Path, script: dict, long_entry: dict, upload_fn) -> list:
    """Short'ları üretir ve (upload_fn verilirse) planlı olarak yükler. Geçmiş kayıtlarını döndürür."""
    from .script_writer import LLM
    sc = cfg.get("shorts", {})
    count = int(sc.get("per_video", 2))
    if not sc.get("enabled", True) or count <= 0:
        return []
    store = folder / "shorts" / "shorts.json"
    if store.exists():
        shorts = json.loads(store.read_text(encoding="utf-8"))
    else:
        log("Shorts senaryoları yazılıyor...")
        shorts = write_shorts(LLM(cfg), cfg, script, count)
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(shorts, ensure_ascii=False, indent=2), encoding="utf-8")
    _toplu_klon(cfg, folder, shorts)
    vid = long_entry.get("video_id")
    link = f"https://youtu.be/{vid}" if vid else ""
    times = publish_times(cfg, long_entry.get("publish_at"), len(shorts))
    entries = []
    for n, (s, when) in enumerate(zip(shorts, times)):
        try:
            video = build_short(cfg, folder, s, n)
        except Exception as e:
            log(f"  Short {n + 1} üretilemedi: {e}")
            continue
        if upload_fn is None:
            continue
        tags = (script.get("tags") or [])[:8] + ["shorts"]
        desc = (f"{s['title']}\n\nHikâyenin tamamı 👉 {link}\n\n"
                f"Her akşam 19:00'da yeni bir gerçek hikâye: Kırmızı Kravat.\n#shorts #bilgi #ilginçbilgiler")
        baslik = s["title"][:80] + (f" ({s['bolum']})" if s.get("bolum") else "")
        meta = {"title": (baslik + " #shorts")[:100], "description": desc, "tags": tags}
        try:
            short_id = upload_fn(video, meta, when)
        except Exception as e:
            log(f"  Short {n + 1} yüklenemedi: {e}")
            continue
        comment = (s.get("comment") or "").strip()
        if link:
            comment = (comment + f"\n\nHikâyenin tamamı burada 👉 {link}").strip()
        entries.append({"folder": f"{folder.name}#short{n + 1}", "title": s["title"], "type": "short",
                        "status": "yüklendi", "video_id": short_id, "publish_at": when.isoformat(),
                        "comment": comment, "long_video": vid, "hedef": s.get("hedef")})
    return entries
