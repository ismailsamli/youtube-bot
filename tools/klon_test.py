"""Ses klonu denemesi (Chatterbox Multilingual, MIT lisanslı, Türkçe destekli) — ekran kartı OLMADAN (CPU) hız ve kalite testi.
Referans ses varsa (assets/ses/referans.wav veya .mp3/.m4a) o sesle konuşur; yoksa modelin hazır sesiyle.
Çıktı: ses_ornekleri/klon_test.mp3 + süre ölçümü (log)."""
import glob
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METIN = ("1912 yılının soğuk bir nisan gecesinde, dünyanın en büyük yolcu gemisi Atlantik'in ortasında ilerliyordu. "
         "Kaptan, buz dağı uyarılarını almıştı ama gemi yavaşlamadı. Saat on bir buçukta gözcü bağırdı: tam önümüzde buz dağı! "
         "Sadece otuz yedi saniye sonra gemi buza sürtündü. Kimse henüz farkında değildi ama geminin kaderi o an belirlenmişti. "
         "Peki dünyanın batmaz denen gemisi neden sadece iki saat kırk dakikada sulara gömüldü? Bu hikâyenin tamamı Kırmızı Kravat kanalında.")


def main():
    import torch
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.set_num_threads(max(1, torch.get_num_threads()))
    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    print(f"Model yüklendi: {time.time() - t0:.0f} sn")
    ref = None
    for pat in ("assets/ses/referans.*",):
        found = sorted(glob.glob(str(ROOT / pat)))
        if found:
            src = Path(found[0])
            ref = ROOT / "assets" / "ses" / "_referans.wav"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "24000", str(ref)], check=True)
            print(f"Referans ses: {src.name}")
    out_dir = ROOT / "ses_ornekleri"
    out_dir.mkdir(exist_ok=True)
    parts = [s.strip() + "." for s in METIN.split(".") if s.strip()]
    wavs, t1 = [], time.time()
    for i, p in enumerate(parts):
        kw = {"language_id": "tr"}
        if ref:
            kw["audio_prompt_path"] = str(ref)
        wav = model.generate(p, **kw)
        f = out_dir / f"_klon_{i:02d}.wav"
        ta.save(str(f), wav, model.sr)
        wavs.append(f)
        print(f"  parça {i + 1}/{len(parts)}: {time.time() - t1:.0f} sn")
    gen = time.time() - t1
    lst = out_dir / "_list.txt"
    lst.write_text("".join(f"file '{w.name}'\n" for w in wavs))
    mp3 = out_dir / ("klon_test_referans.mp3" if ref else "klon_test_hazir_ses.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ar", "44100",
                    "-b:a", "160k", str(mp3)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                               capture_output=True, text=True).stdout)
    for w in wavs:
        w.unlink()
    lst.unlink()
    print(f"SONUÇ: {dur:.0f} sn ses, {gen:.0f} sn'de üretildi (oran {gen / dur:.1f}x). "
          f"7,5 dk'lık video sesi ≈ {gen / dur * 450 / 60:.0f} dk sürer.")


if __name__ == "__main__":
    sys.exit(main())
