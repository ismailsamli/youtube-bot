"""Kaggle ekran kartında klon ses denemesi: kısa bir metni okutur → ses_ornekleri/kaggle_klon_deneme.mp3"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import kaggle_ses  # noqa: E402
from bot.sayilar import cevir  # noqa: E402

METIN = [
    "26 Nisan 1986 gecesi, saat 01.23'te Çernobil'deki 4 numaralı reaktör patladı.",
    "Patlamanın ardından 2. Dünya Savaşı'ndan bu yana Avrupa'nın gördüğü en büyük tahliye başladı.",
    "Bugün, yani 40 yıl sonra bile, bölgenin yaklaşık %30'u hâlâ yasak bölge.",
]


def main():
    out = ROOT / "output" / "kaggle_test"
    out.mkdir(parents=True, exist_ok=True)
    ref = next(iter(sorted((ROOT / "assets" / "ses").glob("referans.*"))))
    t0 = time.time()
    wavs = kaggle_ses.seslendir([cevir(t) for t in METIN], ref, out, 60)
    liste = out / "liste.txt"
    liste.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
    hedef = ROOT / "ses_ornekleri" / "kaggle_klon_deneme.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(liste), "-ar", "44100",
                    "-b:a", "160k", str(hedef)], check=True)
    print(f"Kaggle klon ses tamam: toplam {(time.time() - t0) / 60:.1f} dk → {hedef.name}")


if __name__ == "__main__":
    main()
