"""Sahne görselleri: Wikimedia Commons / Openverse (ücretsiz, lisanslı gerçek görseller),
Pexels stok video, isteğe bağlı yapay zeka görseli ve son çare olarak başlık kartı."""
import io
import time
from pathlib import Path
from urllib.parse import quote

import html
import re

import requests
import random

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .collage import collage
from .paperstyle import kagit_kesme
from .utils import env, log

UA = {"User-Agent": "youtube-bilgi-botu/1.0 (https://github.com/ismailsamli/youtube-bot)"}
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
# Ticari kullanıma ve değiştirmeye izin vermeyen lisanslar atlanır
BAD_LICENSE = re.compile(r"\b(NC|ND)\b|non-?commercial|no-?deriv|fair use", re.I)

PEXELS_VIDEO = "https://api.pexels.com/videos/search"
PEXELS_PHOTO = "https://api.pexels.com/v1/search"


class VisualFinder:
    def __init__(self, cfg: dict, out_dir: Path):
        self.cfg = cfg
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self.pexels_key = env("PEXELS_API_KEY", required=False)
        self.gemini_key = env("GEMINI_API_KEY", required=False)
        self.used_ids = set()
        self._gemini = None
        self.credits = []          # açıklamaya eklenecek görsel kaynakları
        self.dead = set()          # bu çalışmada kapalı olduğu anlaşılan servisler
        self.topic = ""
        self.found = []            # bulunan görseller (son çarede farklı kadrajla yeniden kullanılır)
        self.frame = (cfg.get("images") or {}).get("frame", "kolaj")   # kanal çerçevesi: "kolaj" | "yok"
        global PHOTO_STYLE
        PHOTO_STYLE = (cfg.get("images") or {}).get("photo_style", "kagit")

    # ---------------- Pexels ----------------
    def _pexels(self, url: str, query: str) -> dict:
        r = requests.get(url, headers={"Authorization": self.pexels_key},
                         params={"query": query, "orientation": "landscape", "per_page": 15},
                         timeout=30)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _download(url: str, path: Path) -> None:
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)

    def stock_video(self, query: str, path: Path, min_seconds: float) -> bool:
        try:
            videos = self._pexels(PEXELS_VIDEO, query).get("videos", [])
        except Exception as e:
            log(f"  Pexels video hatası ({query}): {e}")
            return False
        # Önce yeterince uzun ve daha önce kullanılmamış videolar
        videos.sort(key=lambda v: (v["id"] in self.used_ids, v.get("duration", 0) < min_seconds))
        for v in videos:
            files = [f for f in v.get("video_files", [])
                     if f.get("file_type") == "video/mp4" and (f.get("width") or 0) >= 1280
                     and (f.get("width") or 0) >= (f.get("height") or 0)]
            if not files:
                continue
            # 1920'ye en yakın (gereksiz 4K indirmemek için)
            best = min(files, key=lambda f: abs((f.get("width") or 0) - 1920))
            try:
                self._download(best["link"], path)
                self.used_ids.add(v["id"])
                return True
            except Exception as e:
                log(f"  indirme hatası: {e}")
        return False

    def stock_photo(self, query: str, path: Path) -> bool:
        try:
            photos = self._pexels(PEXELS_PHOTO, query).get("photos", [])
        except Exception as e:
            log(f"  Pexels foto hatası ({query}): {e}")
            return False
        for p in sorted(photos, key=lambda p: p["id"] in self.used_ids):
            try:
                self._download(p["src"]["large2x"], path)
                self.used_ids.add(p["id"])
                return True
            except Exception:
                continue
        return False

    # ---------------- Wikimedia Commons ----------------
    def commons_image(self, query: str, path: Path) -> bool:
        if "commons" in self.dead:
            return False
        try:
            r = requests.get(COMMONS_API, headers=UA, timeout=30, params={
                "action": "query", "format": "json", "generator": "search",
                "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": 20,
                "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1920,
                "iiextmetadatafilter": "LicenseShortName|Artist|UsageTerms"})
            r.raise_for_status()
            pages = (r.json().get("query") or {}).get("pages") or {}
        except Exception as e:
            log(f"  Commons hatası ({query}): {e}")
            return False
        cands = []
        for pg in sorted(pages.values(), key=lambda p: p.get("index", 99)):
            ii = (pg.get("imageinfo") or [{}])[0]
            w, h = ii.get("width") or 0, ii.get("height") or 0
            meta = ii.get("extmetadata") or {}
            lic = (meta.get("LicenseShortName") or {}).get("value", "")
            if pg.get("title") in self.used_ids or w < 800 or h < 450:
                continue
            if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp", "image/tiff"):
                continue
            if not lic or BAD_LICENSE.search(lic):
                continue
            artist = re.sub(r"<[^>]+>", "", html.unescape((meta.get("Artist") or {}).get("value", ""))).strip()
            score = (w / max(h, 1) >= 1.2, min(w, 4000))   # yatay ve büyük olanlar önce
            cands.append((score, pg["title"], ii.get("thumburl") or ii.get("url"), lic, artist))
        for _, title, url, lic, artist in sorted(cands, reverse=True):
            if self._save_remote_image(url, path):
                self.used_ids.add(title)
                self.credits.append(f"{title.replace('File:', '')} – {artist or 'Wikimedia Commons'} ({lic})")
                return True
        return False

    # ---------------- Openverse (Flickr vb. CC lisanslı görseller) ----------------
    def openverse_image(self, query: str, path: Path) -> bool:
        if "openverse" in self.dead:
            return False
        try:
            r = requests.get(OPENVERSE_API, headers=UA, timeout=30, params={
                "q": query, "license_type": "commercial,modification",
                "aspect_ratio": "wide", "size": "large", "page_size": 15})
            if r.status_code in (401, 403, 429):
                self.dead.add("openverse")
                log(f"  Openverse şu an kullanılamıyor ({r.status_code}).")
                return False
            r.raise_for_status()
            results = r.json().get("results") or []
        except Exception as e:
            log(f"  Openverse hatası ({query}): {e}")
            return False
        for it in results:
            if it.get("id") in self.used_ids or (it.get("width") or 0) < 1000:
                continue
            if self._save_remote_image(it.get("url"), path):
                self.used_ids.add(it.get("id"))
                lic = f"CC {str(it.get('license', '')).upper()} {it.get('license_version', '')}".strip()
                self.credits.append(f"{it.get('title') or 'Görsel'} – {it.get('creator') or it.get('source')} ({lic})")
                return True
        return False

    def _save_remote_image(self, url: str, path: Path) -> bool:
        if not url:
            return False
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            if img.width < 640:
                return False
            fit_16_9(img).save(path, "PNG")
            return True
        except Exception as e:
            log(f"  görsel indirilemedi: {e}")
            return False

    # ---------------- Son çare: başlık kartı ----------------
    def title_card(self, text: str, path: Path, idx: int) -> None:
        W, H = 1920, 1080
        palettes = [((20, 24, 38), (196, 52, 52)), ((16, 32, 30), (229, 170, 60)),
                    ((30, 20, 40), (120, 160, 230)), ((24, 24, 24), (240, 240, 240))]
        bg, accent = palettes[idx % len(palettes)]
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)
        d.rectangle([120, 470, 140, 610], fill=accent)
        first = re.split(r"[.!?;:,]", text.strip())[0]
        words = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ' ]", "", first).split()
        if len(words) > 9:
            words = words[:8] + ["…"]
        font = _card_font(84)
        lines, cur = [], ""
        for w in words:
            t = f"{cur} {w}".strip()
            if d.textlength(t, font=font) > 1500 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        y = 540 - len(lines) * 50
        for line in lines[:3]:
            d.text((180, y), line, font=font, fill=(245, 245, 245))
            y += 100
        img.filter(ImageFilter.SMOOTH).save(path, "PNG")

    # ---------------- Gemini (Nano Banana) ----------------
    def ai_image(self, prompt: str, path: Path) -> bool:
        provider = self.cfg["images"].get("provider", "free")
        if provider == "none":
            return False
        if provider == "cloudflare":
            return self.cloudflare_image(prompt, path)
        if provider == "free":
            return self.free_image(prompt, path)
        if not self.gemini_key:
            return False
        try:
            from google import genai
            from google.genai import types
            if self._gemini is None:
                self._gemini = genai.Client(api_key=self.gemini_key)
            full = (f"{prompt}. Cinematic, photorealistic, highly detailed, 16:9 widescreen "
                    "composition, no text, no letters, no watermark, no logos.")
            try:
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9"))
                resp = self._gemini.models.generate_content(
                    model=self.cfg["images"]["model"], contents=[full], config=config)
            except (TypeError, AttributeError):  # eski SDK sürümleri
                resp = self._gemini.models.generate_content(
                    model=self.cfg["images"]["model"], contents=[full])
            for part in resp.candidates[0].content.parts:
                data = getattr(part, "inline_data", None)
                if data and data.data:
                    img = Image.open(io.BytesIO(data.data)).convert("RGB")
                    fit_16_9(img).save(path, "PNG")
                    return True
        except Exception as e:
            log(f"  Gemini görsel hatası: {e}")
        return False

    # ---------------- Cloudflare Workers AI (ücretsiz günlük kota) ----------------
    def cloudflare_image(self, prompt: str, path: Path) -> bool:
        if "cloudflare" in self.dead:
            return False
        acc_raw = env("CF_ACCOUNT_ID", required=False) or ""
        tok_raw = env("CF_API_TOKEN", required=False) or ""
        # Kopyalarken araya giren boşluk/satır sonlarına dayanıklı: geçerli biçimdeki parçayı al
        accs = re.findall(r"\b[0-9a-f]{32}\b", acc_raw) or re.findall(r"\b[0-9a-f]{32}\b", tok_raw)
        acc = accs[0] if accs else acc_raw.strip()
        toks = [t for t in re.findall(r"[A-Za-z0-9_\-]{35,60}", tok_raw) if t != acc]
        tok = toks[0] if toks else tok_raw.strip()
        if tok_raw.strip() and ("\n" in tok_raw.strip() or " " in tok_raw.strip()) and "cf_note" not in self.dead:
            self.dead.add("cf_note")
            lens = [len(x.strip()) for x in tok_raw.strip().splitlines()]
            log(f"  Not: CF_API_TOKEN {len(lens)} satır (uzunluklar: {lens}); içinden {len(toks)} uygun anahtar bulundu. "
                f"CF_ACCOUNT_ID uzunluğu: {len(acc_raw.strip())}")
        if not acc or not tok:
            self.dead.add("cloudflare")
            log("  Cloudflare bilgileri tanımlı değil; yapay zeka çizimi yerine fotoğraf kullanılacak.")
            return False
        if not getattr(self, "_cf_acc_checked", False):
            self._cf_acc_checked = True
            try:
                r = requests.get("https://api.cloudflare.com/client/v4/accounts",
                                 headers={"Authorization": f"Bearer {tok}"}, timeout=30)
                ids = [a.get("id") for a in (r.json().get("result") or []) if a.get("id")]
                if ids and acc not in ids:
                    log(f"  Cloudflare hesap numarası anahtarla eşleşmedi; anahtarın bağlı olduğu hesap kullanılıyor "
                        f"({len(ids)} hesap bulundu).")
                    acc = ids[0]
                elif not ids:
                    log(f"  Cloudflare hesap listesi alınamadı ({r.status_code}): {r.text[:200]}")
            except Exception as e:
                log(f"  Cloudflare hesap kontrolü hatası: {e}")
            self._cf_acc = acc
        acc = getattr(self, "_cf_acc", acc)
        style = self.cfg["images"].get("style_prompt", "")
        full = f"{prompt}. {style}".strip()[:2000]
        model = self.cfg["images"].get("cf_model", "@cf/black-forest-labs/flux-1-schnell")
        url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}"
        for attempt in range(3):
            try:
                r = requests.post(url, headers={"Authorization": f"Bearer {tok}"},
                                  json={"prompt": full, "steps": 8,
                                        "seed": abs(hash(prompt)) % 2_000_000}, timeout=120)
                if r.ok and r.headers.get("content-type", "").startswith("image"):
                    data = r.content
                elif r.ok:
                    import base64
                    data = base64.b64decode((r.json().get("result") or {}).get("image") or "")
                else:
                    data = b""
                    txt = r.text[:300]
                    if r.status_code in (401, 403) or "allocation" in txt.lower() or "4006" in txt:
                        self.dead.add("cloudflare")
                        log(f"  Cloudflare kullanılamıyor ({r.status_code}): {txt}. Kalan sahnelerde fotoğraf kullanılacak.")
                        return False
                    log(f"  Cloudflare hatası ({r.status_code}): {txt}")
                if data:
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    fit_16_9(img, style=False).save(path, "PNG")
                    return True
            except Exception as e:
                log(f"  Cloudflare görsel hatası: {e}")
            time.sleep(5 * (attempt + 1))
        return False

    # ---------------- Ücretsiz görsel (Pollinations, anahtar gerektirmez) ----------------
    def free_image(self, prompt: str, path: Path) -> bool:
        if "pollinations" in self.dead:
            return False
        full = (f"{prompt}, cinematic, photorealistic, highly detailed, dramatic lighting, "
                "no text, no watermark")
        url = "https://image.pollinations.ai/prompt/" + quote(full[:900])
        params = {"width": 1920, "height": 1080, "nologo": "true",
                  "model": self.cfg["images"].get("free_model", "flux"),
                  "seed": abs(hash(prompt)) % 1_000_000}
        for attempt in range(3):
            try:
                r = requests.get(url, params=params, timeout=180)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    fit_16_9(img).save(path, "PNG")
                    return True
                log(f"  ücretsiz görsel servisi cevap vermedi ({r.status_code})")
                if r.status_code in (401, 402, 403):
                    self.dead.add("pollinations")
                    log("  Ücretsiz yapay zeka görsel servisi artık ücretli; bu video için devre dışı.")
                    return False
            except Exception as e:
                log(f"  ücretsiz görsel hatası: {e}")
            time.sleep(5 * (attempt + 1))
        return False

    # ---------------- Ana fonksiyon ----------------
    def _finish(self, path: Path, idx: int, keep: bool = True) -> Path:
        """Ham görseli saklar ve kanal çerçevesini (kâğıt kolaj) uygular."""
        raw = path.with_name(path.stem + "_ham.png")
        img = Image.open(path).convert("RGB")
        img.save(raw, "PNG")
        if keep:
            self.found.append(raw)
        if self.frame == "kolaj":
            collage(img, idx).save(path, "PNG")
        return path

    def get(self, scene: dict, idx: int, seconds: float):
        """(dosya_yolu, 'video' | 'image') döndürür."""
        vid = self.out_dir / f"visual_{idx:03d}.mp4"
        img = self.out_dir / f"visual_{idx:03d}.png"
        if vid.exists():
            return vid, "video"
        if img.exists():
            return img, "image"

        jpg = self.out_dir / f"visual_{idx:03d}.jpg"
        cf_first = self.cfg["images"].get("provider") == "cloudflare" and "cloudflare" not in self.dead
        order = [("ai", img)] if cf_first else []
        order += [("commons", img)]
        if self.pexels_key and scene["visual"] != "ai":
            order += [("video", vid), ("photo", jpg)]
        order += [("openverse", img)] + ([] if cf_first else [("ai", img)])
        if self.pexels_key and scene["visual"] == "ai":
            order += [("video", vid), ("photo", jpg)]

        q = scene["query"]
        for kind, path in order:
            ok = (kind == "commons" and (self.commons_image(q, path) or
                                         (self.topic and self.commons_image(f"{self.topic} {q}", path)))) or \
                 (kind == "openverse" and self.openverse_image(q, path)) or \
                 (kind == "ai" and self.ai_image(scene["prompt"], path)) or \
                 (kind == "video" and self.stock_video(q, path, seconds)) or \
                 (kind == "photo" and self.stock_photo(q, path))
            if ok:
                if kind == "photo":
                    fit_16_9(Image.open(jpg).convert("RGB")).save(img, "PNG")
                    jpg.unlink(missing_ok=True)
                    path = img
                if kind == "video":
                    return path, "video"
                return self._finish(path, idx), "image"

        # Bulunamazsa aramayı genişlet: sadeleştirilmiş arama, sahne tarifi, videonun genel konusu
        words = q.split()
        extra = []
        if len(words) > 2:
            extra += [" ".join(words[-2:]), " ".join(words[:2])]
        extra.append(" ".join((scene.get("prompt") or "").split()[:4]))
        if self.topic:
            extra.append(self.topic)
        for eq in dict.fromkeys(e.strip() for e in extra if e and e.strip()):
            if self.commons_image(eq, img) or self.openverse_image(eq, img):
                return self._finish(img, idx), "image"

        # Hâlâ yoksa: daha önce bulunan bir görseli farklı bir kadrajla yeniden kullan (yazı ekranı yok)
        if self.found:
            src = self.found[idx % len(self.found)]
            log(f"  sahne {idx}: yeni görsel bulunamadı, önceki bir görsel farklı kadrajla kullanılıyor")
            recrop(Image.open(src).convert("RGB"), idx).save(img, "PNG")
            return self._finish(img, idx, keep=False), "image"

        log(f"  sahne {idx}: hiç görsel bulunamadı, başlık kartı kullanılıyor")
        self.title_card(scene["text"], img, idx)
        return img, "image"


def _card_font(size: int):
    for p in ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def recrop(img: Image.Image, seed: int) -> Image.Image:
    """Aynı görselin farklı bir bölümünü yakınlaştırarak yeni bir kadraj üretir."""
    rnd = random.Random(seed)
    w, h = img.size
    z = rnd.uniform(1.35, 1.7)
    cw, ch = int(w / z), int(h / z)
    x, y = rnd.randint(0, w - cw), rnd.randint(0, h - ch)
    return img.crop((x, y, x + cw, y + ch)).resize((w, h), Image.LANCZOS)


def _vignette(width: int, height: int) -> Image.Image:
    mask = Image.new("L", (width // 8, height // 8), 0)
    d = ImageDraw.Draw(mask)
    mw, mh = mask.size
    d.ellipse((mw * 0.02, mh * 0.0, mw * 0.98, mh * 1.0), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(mw // 6)).resize((width, height), Image.BICUBIC)


_VIGNETTE = {}
PHOTO_STYLE = "kagit"     # fotoğraflara uygulanan kanal stili: "kagit" (kâğıt kesme) | "sinema"


def channel_style(img: Image.Image) -> Image.Image:
    """Kanalın sabit görsel stili: tüm kaynaklardan gelen görseller aynı sinematik belgesel
    tonuna getirilir (ayarlı kontrast, hafif soluk renk, sıcak-lacivert ton, kenar kararması)."""
    lo, hi = img.convert("L").getextrema()
    if hi - lo > 60:                      # düz/tek renkli görselleri bozmamak için
        img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Color(img).enhance(0.6)
    tone = ImageOps.colorize(img.convert("L"), black=(10, 20, 36), mid=(120, 108, 92), white=(250, 230, 200))
    img = Image.blend(img, tone, 0.55)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    key = img.size
    if key not in _VIGNETTE:
        _VIGNETTE[key] = _vignette(*key)
    dark = ImageEnhance.Brightness(img).enhance(0.35)
    return Image.composite(img, dark, _VIGNETTE[key])


def fit_16_9(img: Image.Image, width: int = 1920, height: int = 1080, style: bool = True) -> Image.Image:
    """Görseli bozmadan 16:9'a kırpar, boyutlandırır ve kanal stilini uygular."""
    target = width / height
    w, h = img.size
    if w / h > target:
        new_w = int(h * target)
        img = img.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    else:
        new_h = int(w / target)
        img = img.crop((0, (h - new_h) // 2, w, (h - new_h) // 2 + new_h))
    img = img.resize((width, height), Image.LANCZOS)
    if not style:
        return img
    return kagit_kesme(img) if PHOTO_STYLE == "kagit" else channel_style(img)
