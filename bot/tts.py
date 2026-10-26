"""Seslendirme motorları: Gemini TTS (ücretsiz katman, doğal Türkçe), Google Cloud, Edge ve Piper (yedek).

Bir videonun tamamı tek bir sesle okunur: seçili motor çalışmazsa tüm video Piper ile seslendirilir.
"""
import asyncio
import base64
import difflib
import json
import os
import re
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


# ---------------- Gemini TTS (ücretsiz katman) ----------------
GEMINI_TTS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_STYLE = ("Türkçe belgesel anlatıcısı: sıcak, güven veren, merak uyandıran; doğal vurgular, "
                "canlı ve akıcı tempo, cümle sonlarında doğal duraklar. Abartılı oyunculuk yok.")


class QuotaError(RuntimeError):
    """Günlük ücretsiz kota doldu: bu çalışmada Gemini sesi tekrar denenmez."""


_gemini_dead = {"reason": None}


def _find_audio(obj):
    """Cevap JSON'unun içindeki base64 ses verisini bulur (API biçimi değişse de çalışsın)."""
    if isinstance(obj, dict):
        typ = str(obj.get("type", "")) + str(obj.get("mime_type", "")) + str(obj.get("mimeType", ""))
        if isinstance(obj.get("data"), str) and len(obj["data"]) > 1000 and ("audio" in typ or "wav" in typ or not typ):
            return obj["data"], typ
        for v in obj.values():
            found = _find_audio(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_audio(v)
            if found:
                return found
    return None


def gemini_synthesize(text: str, cfg: dict, wav: Path, style: str = None, retries: int = 4) -> Path:
    """Metni Gemini TTS ile okur, 24 kHz mono WAV yazar."""
    if _gemini_dead["reason"]:
        raise QuotaError(_gemini_dead["reason"])
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil")
    v = cfg["voice"]
    models = list(dict.fromkeys([v.get("gemini_model", "gemini-3.8-flash-tts")]
                                + list(v.get("gemini_fallbacks") or ["gemini-3.8-flash-lite-tts"])))
    errors = []
    for model in models:
        body = {"model": model,
                "input": [{"type": "user_input", "content": [{
                    "type": "text", "text": text,
                    "annotations": [{"type": "speech_metadata", "style": style or v.get("gemini_style") or GEMINI_STYLE}]}]}],
                "response_format": {"type": "audio"},
                "generation_config": {"speech_config": [{"voice": v.get("gemini_voice", "Charon")}]}}
        last = None
        for attempt in range(retries):
            try:
                r = requests.post(GEMINI_TTS_URL, headers={"x-goog-api-key": key}, json=body, timeout=300)
            except Exception as e:
                last = e
                time.sleep(5 * (attempt + 1))
                continue
            if r.ok:
                found = _find_audio(r.json())
                if not found:
                    last = "cevapta ses yok"
                    continue
                data = base64.b64decode(found[0])
                wav.parent.mkdir(parents=True, exist_ok=True)
                if data[:4] == b"RIFF":
                    wav.write_bytes(data)
                else:                               # başlıksız PCM: 24 kHz, 16 bit, mono
                    with wave.open(str(wav), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(data)
                return wav
            txt = r.text[:400]
            if r.status_code == 429:
                if "PerDay" in txt or "per day" in txt.lower() or "daily" in txt.lower():
                    _gemini_dead["reason"] = f"{model}: günlük kota doldu"
                    last = _gemini_dead["reason"]
                    break                           # bu model bitti: sıradaki modeli dene
                m = re.search(r'"retryDelay":\s*"(\d+)', r.text)
                time.sleep(min(90, int(m.group(1)) + 2) if m else 20 * (attempt + 1))
                last = f"429 {txt[:150]}"
                continue
            if r.status_code in (400, 404):
                last = f"{r.status_code}: {txt[:200]}"
                break
            if r.status_code in (401, 403):
                raise RuntimeError(f"Gemini ses yetki hatası {r.status_code}: {txt[:300]}")
            last = f"{r.status_code}: {txt[:150]}"
            time.sleep(8 * (attempt + 1))
        errors.append(f"{model} -> {last}")
    if all("kota" in e for e in errors):
        raise QuotaError(" | ".join(errors))
    _gemini_dead["reason"] = None
    raise RuntimeError("Gemini seslendirme başarısız: " + " | ".join(errors))


# ---------------- Hizalama (Whisper): bölüm sesini sahnelere böler ----------------
_whisper = {}
_TRL = str.maketrans({"I": "ı", "İ": "i"})


def _norm(w: str) -> str:
    return re.sub(r"[^0-9a-zçğıöşü]", "", w.translate(_TRL).lower())


def _whisper_words(wav: Path, cfg: dict) -> list:
    from faster_whisper import WhisperModel
    name = cfg["voice"].get("whisper_model", "base")
    if name not in _whisper:
        log(f"  Hizalama modeli yükleniyor (faster-whisper {name})")
        _whisper[name] = WhisperModel(name, device="cpu", compute_type="int8")
    segs, _ = _whisper[name].transcribe(str(wav), language="tr", word_timestamps=True,
                                        vad_filter=False, beam_size=1, condition_on_previous_text=False)
    out = []
    for sg in segs:
        for w in (sg.words or []):
            out.append((w.word.strip(), float(w.start), float(w.end)))
    return out


def _quiet_point(samples, rate: int, t: float, span: float = 0.35) -> float:
    """t civarındaki en sessiz anı bulur (kesim kelimenin ortasına denk gelmesin)."""
    import numpy as np
    a, b = max(0, int((t - span) * rate)), min(len(samples), int((t + span) * rate))
    if b - a < rate // 20:
        return t
    win = max(1, rate // 50)                          # 20 ms
    seg = samples[a:b].astype(np.float32)
    n = len(seg) // win
    if n < 3:
        return t
    e = (seg[:n * win].reshape(n, win) ** 2).mean(axis=1)
    k = int(e.argmin())
    return (a + k * win + win / 2) / rate


def _align_and_cut(wav: Path, scenes: list, idxs: list, out_dir: Path, cfg: dict) -> None:
    """Bölüm sesini Whisper ile hizalar, her sahneyi audio_XXX.mp3 olarak keser, kelime zamanlarını yazar."""
    import numpy as np
    with wave.open(str(wav), "rb") as wf:
        rate = wf.getframerate()
        ch = wf.getnchannels()
        samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    if ch > 1:
        samples = samples.reshape(-1, ch).mean(axis=1)
    total = len(samples) / rate
    script = []                                       # (normal kelime, orijinal kelime, sahne sırası)
    for k, i in enumerate(idxs):
        for w in scenes[i]["text"].split():
            if _norm(w):
                script.append((_norm(w), w, k))
    heard = [(_norm(w), s, e) for w, s, e in _whisper_words(wav, cfg) if _norm(w)]
    if not heard or not script:
        raise RuntimeError("hizalama: kelime bulunamadı")
    ratio = len(heard) / len(script)
    sm = difflib.SequenceMatcher(None, [x[0] for x in script], [x[0] for x in heard], autojunk=False)
    times = [None] * len(script)
    for blk in sm.get_matching_blocks():
        for j in range(blk.size):
            _, s0, e0 = heard[blk.b + j]
            times[blk.a + j] = (s0, e0)
    matched = sum(1 for t in times if t)
    if matched / len(script) < 0.55 or not 0.7 <= ratio <= 1.45:
        raise RuntimeError(f"hizalama zayıf (eşleşme %{100 * matched / len(script):.0f}, kelime oranı {ratio:.2f})")
    # eşleşmeyen kelimelerin zamanı komşularından tahmin edilir
    known = [n for n, t in enumerate(times) if t]
    for n in range(len(times)):
        if times[n]:
            continue
        prev = max((k for k in known if k < n), default=None)
        nxt = min((k for k in known if k > n), default=None)
        if prev is None:
            t1 = times[nxt][0]
            times[n] = (max(0.0, t1 - 0.4 * (nxt - n)), max(0.0, t1 - 0.4 * (nxt - n) + 0.3))
        elif nxt is None:
            t0 = times[prev][1]
            times[n] = (min(total, t0 + 0.4 * (n - prev - 1)), min(total, t0 + 0.4 * (n - prev)))
        else:
            a, b = times[prev][1], times[nxt][0]
            f0, f1 = (n - prev) / (nxt - prev + 1), (n - prev + 1) / (nxt - prev + 1)
            times[n] = (a + (b - a) * f0, a + (b - a) * f1)
    # sahne sınırları
    first = {}
    last = {}
    for n, (_, _, k) in enumerate(script):
        first.setdefault(k, n)
        last[k] = n
    cuts = [max(0.0, times[first[0]][0] - 0.15)]
    for k in range(1, len(idxs)):
        e_prev, s_next = times[last[k - 1]][1], times[first[k]][0]
        guess = (e_prev + s_next) / 2 if s_next >= e_prev else s_next
        cuts.append(_quiet_point(samples, rate, guess))
    cuts.append(min(total, times[last[len(idxs) - 1]][1] + 0.3))
    for k in range(len(idxs)):
        if cuts[k + 1] - cuts[k] < 0.6:
            raise RuntimeError(f"hizalama: {k}. sahne çok kısa çıktı")
    for k, i in enumerate(idxs):
        a, b = cuts[k], cuts[k + 1]
        path = out_dir / f"audio_{i:03d}.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                        f"atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,"
                        f"afade=t=out:st={max(0.0, b - a - 0.03):.3f}:d=0.03",
                        "-ar", "44100", "-b:a", "160k", str(path)], check=True)
        words = [{"w": script[n][1], "s": round(times[n][0] - a, 3), "e": round(times[n][1] - a, 3)}
                 for n in range(first[k], last[k] + 1)]
        (out_dir / f"words_{i:03d}.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")


def _groups(scenes: list, max_words: int) -> list:
    """Aynı bölümdeki ardışık sahneler tek istekte okunur (ücretsiz günlük istek sınırı için)."""
    out, cur, words, key = [], [], 0, None
    for i, sc in enumerate(scenes):
        k = (bool(sc.get("cold")), sc.get("section"))
        n = len(sc["text"].split())
        if cur and (k != key or words + n > max_words):
            out.append(cur)
            cur, words = [], 0
        cur.append(i)
        words += n
        key = k
    if cur:
        out.append(cur)
    return out


def _tempo(wav: Path, words: int, cfg: dict) -> None:
    """Okuma hızı hedefin altındaysa (perdeyi bozmadan) hafifçe hızlandırır."""
    target = float(cfg["voice"].get("gemini_wpm", 158))
    with wave.open(str(wav), "rb") as wf:
        secs = wf.getnframes() / wf.getframerate()
    wpm = words / max(secs / 60, 0.01)
    if wpm < target * 0.95:
        k = min(1.18, target / wpm)
        tmp = wav.with_name(wav.stem + "_hiz.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", f"atempo={k:.3f}",
                        str(tmp)], check=True)
        tmp.replace(wav)


def gemini_voice_scenes(scenes: list, cfg: dict, out_dir: Path) -> None:
    """Tüm sahneleri Gemini ile seslendirir (bölüm bölüm). Hata olursa RuntimeError fırlatır."""
    max_words = int(cfg["voice"].get("gemini_group_words", 260))
    groups = _groups(scenes, max_words)
    done = 0
    for g, idxs in enumerate(groups):
        if all((out_dir / f"audio_{i:03d}.mp3").exists() for i in idxs):
            continue
        text = "\n\n".join(scenes[i]["text"] for i in idxs)
        words = len(text.split())
        wav = out_dir / f"bolum_{g:02d}.wav"
        err = None
        for attempt in range(2):
            try:
                if not wav.exists() or attempt:
                    gemini_synthesize(text, cfg, wav)
                    _tempo(wav, words, cfg)
                _align_and_cut(wav, scenes, idxs, out_dir, cfg)
                err = None
                break
            except QuotaError:
                raise
            except Exception as e:                    # bozuk okuma: bir kez yeniden okut
                err = e
                log(f"  bölüm {g + 1}: {str(e)[:160]} — tekrar deneniyor")
        if err:
            # son çare: bu bölümün sahneleri tek tek okunur
            log(f"  bölüm {g + 1} sahne sahne okunuyor")
            for i in idxs:
                w1 = out_dir / f"tek_{i:03d}.wav"
                gemini_synthesize(scenes[i]["text"], cfg, w1)
                _tempo(w1, len(scenes[i]["text"].split()), cfg)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(w1), "-af",
                                "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                                "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                                "-ar", "44100", "-b:a", "160k", str(out_dir / f"audio_{i:03d}.mp3")], check=True)
                w1.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
        done += len(idxs)
        log(f"  seslendirme {done}/{len(scenes)} (gemini, {g + 1}/{len(groups)}. istek grubu)")


def say(text: str, cfg: dict, path: Path, out_dir: Path) -> Path:
    """Tek bir cümleyi videonun geri kalanıyla aynı sesle okur (kapanış jeneriği için)."""
    engine_file = out_dir / "motor.txt"
    engine = engine_file.read_text().strip() if engine_file.exists() else cfg["voice"].get("engine", "piper")
    rate = cfg["voice"]["rate"]
    if path.exists() and path.stat().st_size > 1000:
        return path
    if engine == "gemini":
        try:
            wav = path.with_suffix(".wav")
            gemini_synthesize(text, cfg, wav)
            _tempo(wav, len(text.split()), cfg)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ar", "44100", "-b:a", "160k",
                            str(path)], check=True)
            wav.unlink(missing_ok=True)
            return path
        except Exception as e:
            log(f"  Gemini sesi kullanılamadı ({str(e)[:120]}), Piper ile okunuyor")
            engine = "piper"
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

    if engine == "gemini":
        try:
            gemini_voice_scenes(scenes, cfg, out_dir)
        except Exception as e:
            log(f"  Gemini sesi kullanılamıyor ({str(e)[:200]}). Video Piper sesiyle seslendirilecek.")
            for f in list(out_dir.glob("audio_*.mp3")) + list(out_dir.glob("words_*.json")) \
                    + list(out_dir.glob("bolum_*.wav")) + list(out_dir.glob("tek_*.wav")):
                f.unlink(missing_ok=True)       # tek ses kuralı: yarım Gemini sesleri silinir
            engine = "piper"

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
            if engine in ("piper", "gemini"):     # gemini'de eksik sahne kalmaz; kalırsa Piper okur
                piper_synthesize(scene["text"], rate, path)
            elif engine == "google":
                google_synthesize(scene["text"], cfg, path)
            else:
                synthesize(scene["text"], voice, rate, path)
        paths.append(path)
        if (i + 1) % 10 == 0 or i + 1 == len(scenes):
            log(f"  seslendirme {i + 1}/{len(scenes)} ({engine})")
    return paths
