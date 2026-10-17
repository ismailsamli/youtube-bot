"""Seslendirme: ücretsiz Microsoft Edge Türkçe sesi; çalışmazsa çevrimdışı Piper Türkçe sesi (yedek).

Bir videonun tamamı tek bir sesle okunur: Edge ilk sahnede çalışmazsa tüm video Piper ile seslendirilir.
"""
import asyncio
import base64
import os
import subprocess
import time
import wave
from pathlib import Path

import edge_tts
import requests

from .utils import log

PIPER_VOICE = "tr_TR-dfki-medium"
PIPER_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/"
PIPER_DIR = Path(__file__).resolve().parent.parent / "data" / "piper"


# ---------------- Microsoft Edge ----------------
async def _save(text: str, voice: str, rate: str, path: Path) -> None:
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def synthesize(text: str, voice: str, rate: str, path: Path, retries: int = 4, wait: float = 2) -> None:
    last = None
    for attempt in range(retries):
        try:
            asyncio.run(_save(text, voice, rate, path))
            if path.exists() and path.stat().st_size > 1000:
                return
        except Exception as e:  # ağ hataları vb.
            last = e
        time.sleep(wait * (attempt + 1))
    path.unlink(missing_ok=True)          # yarım kalan dosya sonraki adımları bozmasın
    raise RuntimeError(f"Seslendirme başarısız: {last}")


# ---------------- Piper (çevrimdışı yedek) ----------------
_piper = None


def _piper_voice():
    global _piper
    if _piper is None:
        from piper import PiperVoice
        PIPER_DIR.mkdir(parents=True, exist_ok=True)
        for name in (f"{PIPER_VOICE}.onnx", f"{PIPER_VOICE}.onnx.json"):
            dest = PIPER_DIR / name
            if not dest.exists() or dest.stat().st_size < 100:
                log(f"  Piper ses modeli indiriliyor: {name}")
                r = requests.get(PIPER_URL + name, timeout=300)
                r.raise_for_status()
                dest.write_bytes(r.content)
        _piper = PiperVoice.load(str(PIPER_DIR / f"{PIPER_VOICE}.onnx"))
    return _piper


def _rate_to_length_scale(rate: str) -> float:
    try:
        pct = float(rate.strip().rstrip("%"))
    except ValueError:
        pct = 0
    return round(1 / (1 + pct / 100), 3)


def piper_synthesize(text: str, rate: str, path: Path) -> None:
    from piper import SynthesisConfig
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as wf:
        _piper_voice().synthesize_wav(text, wf, syn_config=SynthesisConfig(
            length_scale=_rate_to_length_scale(rate)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ar", "44100", "-b:a", "160k",
                    str(path)], check=True)
    wav.unlink(missing_ok=True)


# ---------------- Google Cloud Text-to-Speech ----------------
GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


def _rate_to_speaking_rate(rate: str) -> float:
    try:
        return round(1 + float(rate.strip().rstrip("%")) / 100, 2)
    except ValueError:
        return 1.0


_google_voice = None   # bu çalışmada çalıştığı doğrulanan ses


def google_synthesize(text: str, cfg: dict, path: Path, retries: int = 4) -> None:
    """Google Cloud TTS. Ses adı bulunamazsa sıradaki yedek sese geçer (Chirp 3 HD → WaveNet)."""
    global _google_voice
    key = os.environ.get("GOOGLE_TTS_KEY", "").strip()
    if not key:
        raise RuntimeError("GOOGLE_TTS_KEY tanımlı değil")
    v = cfg["voice"]
    wanted = v.get("google_voice", "tr-TR-Chirp3-HD-Charon")
    candidates = [_google_voice] if _google_voice else list(dict.fromkeys(
        ([wanted] if isinstance(wanted, str) else list(wanted)) + ["tr-TR-Wavenet-E", "tr-TR-Wavenet-B"]))
    errors = []
    for name in candidates:
        audio_cfg = {"audioEncoding": "MP3", "speakingRate": _rate_to_speaking_rate(v.get("rate", "+0%"))}
        last = None
        for attempt in range(retries):
            body = {"input": {"text": text}, "voice": {"languageCode": "tr-TR", "name": name}, "audioConfig": audio_cfg}
            try:
                r = requests.post(GOOGLE_TTS_URL, params={"key": key}, json=body, timeout=120)
            except Exception as e:          # ağ hatası: tekrar dene
                last = e
                time.sleep(3 * (attempt + 1))
                continue
            if r.ok:
                path.write_bytes(base64.b64decode(r.json()["audioContent"]))
                if path.stat().st_size > 1000:
                    if _google_voice != name:
                        log(f"  Google sesi: {name}")
                    _google_voice = name
                    return
                last = "boş ses"
            elif r.status_code == 400 and "speakingRate" in audio_cfg and "rate" in r.text.lower():
                audio_cfg.pop("speakingRate")   # bu ses hız ayarını desteklemiyor
                continue
            elif r.status_code in (400, 404):
                last = f"{r.status_code}: {r.text[:200]}"
                break                            # bu ses yok/uygun değil: sıradaki ses
            elif r.status_code in (401, 403):
                raise RuntimeError(f"Google ses yetki hatası {r.status_code}: {r.text[:300]}")
            else:
                last = f"{r.status_code}: {r.text[:200]}"
            time.sleep(3 * (attempt + 1))
        errors.append(f"{name} -> {last}")
        if _google_voice:                         # çalışan ses bir anda bozulduysa diğerlerini deneme
            break
    raise RuntimeError("Google seslendirme başarısız: " + " | ".join(errors))


def say(text: str, cfg: dict, path: Path, out_dir: Path) -> Path:
    """Tek bir cümleyi videonun geri kalanıyla aynı sesle okur (kapanış jeneriği için)."""
    engine_file = out_dir / "motor.txt"
    engine = engine_file.read_text().strip() if engine_file.exists() else cfg["voice"].get("engine", "piper")
    rate = cfg["voice"]["rate"]
    if path.exists() and path.stat().st_size > 1000:
        return path
    if engine == "google":
        google_synthesize(text, cfg, path)
    elif engine == "edge":
        synthesize(text, cfg["voice"]["name"], rate, path)
    else:
        piper_synthesize(text, rate, path)
    return path


# ---------------- Ana akış ----------------
def voice_scenes(scenes: list, cfg: dict, out_dir: Path) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    voice, rate = cfg["voice"]["name"], cfg["voice"]["rate"]
    engine_file = out_dir / "motor.txt"
    engine = engine_file.read_text().strip() if engine_file.exists() else cfg["voice"].get("engine", "edge")

    if engine == "google":
        first = out_dir / "audio_000.mp3"
        if not first.exists() or first.stat().st_size < 1000:
            try:
                google_synthesize(scenes[0]["text"], cfg, first)
            except RuntimeError as e:
                first.unlink(missing_ok=True)
                log(f"  Google sesi kullanılamıyor ({str(e)[:160]}). Video Piper sesiyle seslendirilecek.")
                engine = "piper"

    if engine == "edge":
        first = out_dir / "audio_000.mp3"
        if not first.exists() or first.stat().st_size < 1000:
            try:
                # Geçici engellere karşı ilk sahnede daha uzun bekleyerek dene (~2,5 dk)
                synthesize(scenes[0]["text"], voice, rate, first, retries=5, wait=10)
            except RuntimeError as e:
                log(f"  Edge sesi kullanılamıyor ({str(e)[:120]}). Video yedek Piper sesiyle seslendirilecek.")
                engine = "piper"
    engine_file.write_text(engine)

    paths = []
    for i, scene in enumerate(scenes):
        path = out_dir / f"audio_{i:03d}.mp3"
        if not path.exists() or path.stat().st_size < 1000:
            if engine == "piper":
                piper_synthesize(scene["text"], rate, path)
            elif engine == "google":
                google_synthesize(scene["text"], cfg, path)
            else:
                synthesize(scene["text"], voice, rate, path)
        paths.append(path)
        if (i + 1) % 10 == 0 or i + 1 == len(scenes):
            log(f"  seslendirme {i + 1}/{len(scenes)} ({engine})")
    return paths
