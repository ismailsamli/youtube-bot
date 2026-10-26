"""Gemini TTS Türkçe ses örnekleri üretir (ses_ornekleri/ klasörüne). Aynı metin her sesle okunur."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import tts  # noqa: E402
from bot.utils import load_config  # noqa: E402

METIN = ("1970 yılında Sovyet bilim insanları, Dünya'nın kabuğunu delip geçmek için inanılmaz bir yolculuğa "
         "çıktı. Yirmi yıl boyunca kazdılar ve tam on iki bin metreye ulaştılar. Peki orada ne buldular? "
         "Cevap, bilim dünyasını bugün bile şaşırtıyor.")
SESLER = ["Charon", "Orus", "Algenib", "Iapetus", "Rasalgethi", "Sadaltager"]

cfg = load_config()
out = Path("ses_ornekleri")
out.mkdir(exist_ok=True)
for s in SESLER:
    cfg["voice"]["gemini_voice"] = s
    wav = out / f"gemini_{s}.wav"
    try:
        tts.gemini_synthesize(METIN, cfg, wav)
        tts._tempo(wav, len(METIN.split()), cfg)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "128k",
                        str(wav.with_suffix(".mp3"))], check=True)
        wav.unlink()
        print(f"OK gemini {s}")
    except Exception as e:
        print(f"HATA gemini {s}: {e}")
# karşılaştırma için şu anki Piper sesi
try:
    tts.piper_synthesize(METIN, cfg["voice"].get("rate", "+15%"), out / "piper_simdiki.mp3")
    print("OK piper")
except Exception as e:
    print(f"HATA piper: {e}")
