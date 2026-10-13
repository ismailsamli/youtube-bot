"""Google Chirp 3 HD Türkçe seslerinden kısa örnekler üretir (ses_ornekleri/ klasörüne)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import tts  # noqa: E402
from bot.utils import load_config  # noqa: E402

METIN = ("1970 yılında Sovyet bilim insanları, Dünya'nın kabuğunu delip geçmek için inanılmaz bir yolculuğa "
         "çıktı. Yirmi yıl boyunca kazdılar ve tam on iki bin metreye ulaştılar. Peki orada ne buldular?")
SESLER = ["Charon", "Fenrir", "Orus", "Puck", "Algenib", "Iapetus", "Kore", "Aoede"]

cfg = load_config()
out = Path("ses_ornekleri")
out.mkdir(exist_ok=True)
for s in SESLER:
    name = f"tr-TR-Chirp3-HD-{s}"
    cfg["voice"]["google_voice"] = name
    tts._google_voice = None
    path = out / f"{s}.mp3"
    try:
        tts.google_synthesize(METIN, cfg, path)
        print(f"OK {name} -> {tts._google_voice}")
    except Exception as e:
        print(f"HATA {name}: {e}")
