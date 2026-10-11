"""Sahne görselleri: Pexels'ten ücretsiz stok video/fotoğraf ve Gemini ile yapay zeka görseli."""
import io
import time
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

from .utils import env, log

PEXELS_VIDEO = "https://api.pexels.com/videos/search"
PEXELS_PHOTO = "https://api.pexels.com/v1/search"


class VisualFinder:
    def __init__(self, cfg: dict, out_dir: Path):
        self.cfg = cfg
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self.pexels_key = env("PEXELS_API_KEY")
        self.gemini_key = env("GEMINI_API_KEY", required=False)
        self.used_ids = set()
        self._gemini = None

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

    # ---------------- Gemini (Nano Banana) ----------------
    def ai_image(self, prompt: str, path: Path) -> bool:
        provider = self.cfg["images"].get("provider", "free")
        if provider == "none":
            return False
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

    # ---------------- Ücretsiz görsel (Pollinations, anahtar gerektirmez) ----------------
    def free_image(self, prompt: str, path: Path) -> bool:
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
            except Exception as e:
                log(f"  ücretsiz görsel hatası: {e}")
            time.sleep(5 * (attempt + 1))
        return False

    # ---------------- Ana fonksiyon ----------------
    def get(self, scene: dict, idx: int, seconds: float):
        """(dosya_yolu, 'video' | 'image') döndürür."""
        vid = self.out_dir / f"visual_{idx:03d}.mp4"
        img = self.out_dir / f"visual_{idx:03d}.png"
        if vid.exists():
            return vid, "video"
        if img.exists():
            return img, "image"

        jpg = self.out_dir / f"visual_{idx:03d}.jpg"
        if scene["visual"] == "ai":
            order = [("ai", img), ("video", vid), ("photo", jpg)]
        else:
            order = [("video", vid), ("photo", jpg), ("ai", img)]

        for kind, path in order:
            ok = (kind == "ai" and self.ai_image(scene["prompt"], path)) or \
                 (kind == "video" and self.stock_video(scene["query"], path, seconds)) or \
                 (kind == "photo" and self.stock_photo(scene["query"], path))
            if ok:
                if kind == "photo":
                    fit_16_9(Image.open(jpg).convert("RGB")).save(img, "PNG")
                    jpg.unlink(missing_ok=True)
                    return img, "image"
                return path, "video" if kind == "video" else "image"

        # Hiçbir şey bulunamazsa: düz koyu arka plan
        log(f"  sahne {idx}: görsel bulunamadı, düz arka plan kullanılıyor")
        Image.new("RGB", (1920, 1080), (18, 22, 32)).save(img, "PNG")
        return img, "image"


def fit_16_9(img: Image.Image, width: int = 1920, height: int = 1080) -> Image.Image:
    """Görseli bozmadan 16:9'a kırpar ve boyutlandırır."""
    target = width / height
    w, h = img.size
    if w / h > target:
        new_w = int(h * target)
        img = img.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    else:
        new_h = int(w / target)
        img = img.crop((0, (h - new_h) // 2, w, (h - new_h) // 2 + new_h))
    return img.resize((width, height), Image.LANCZOS)
