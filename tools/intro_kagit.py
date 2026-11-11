"""Kâğıt tarzı kanal girişi (jenerik) üretir → assets/intro_animasyon.mp4

Görüntü: motor/kaliplar.js > KALIP.intro (kırmızı disk, kâğıt kravat, "KIRMIZI KRAVAT" şeridi).
Ses: kâğıt hışırtısı + kravat oturunca yumuşak vuruş + isimde hafif çan; sonda krem zemine yumuşak sönme.
Kullanım: python tools/intro_kagit.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import kagit_motor  # noqa: E402

SURE = 4.2
KREM = "0xF3EBDD"


def main():
    out = ROOT / "assets" / "intro_animasyon.mp4"
    tmp = ROOT / "output" / "intro_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    plan = {"w": 1920, "h": 1080, "yazisiz": True, "sure": SURE, "sahneler": [{"kalip": "intro", "sure": SURE, "bas": 0, "p": {}}]}
    sessiz = kagit_motor.render(plan, tmp / "intro_sessiz.mp4", fps=30)
    # ses katmanları (lavfi ile sentez; telifsiz)
    whoosh = ("anoisesrc=d=0.9:c=pink:a=0.6:r=44100,highpass=f=350,lowpass=f=5000,"
              "afade=t=in:d=0.35,afade=t=out:st=0.4:d=0.5,volume=0.55")
    whoosh2 = ("anoisesrc=d=0.6:c=pink:a=0.5:r=44100,highpass=f=900,lowpass=f=6000,"
               "afade=t=in:d=0.2,afade=t=out:st=0.25:d=0.35,volume=0.35")
    thump = "sine=f=85:d=0.45:r=44100,afade=t=out:st=0.02:d=0.43,volume=0.9"
    chime = ("sine=f=659:d=1.6:r=44100[c1];sine=f=988:d=1.6:r=44100[c2];[c1][c2]amix=inputs=2,"
             "afade=t=in:d=0.02,afade=t=out:st=0.05:d=1.5,volume=0.22")
    fc = (f"{whoosh},adelay=100|100[w];{whoosh2},adelay=1150|1150[w2];{thump},adelay=900|900[t];"
          f"{chime},adelay=1500|1500[ch];"
          f"[w][w2][t][ch]amix=inputs=4:normalize=0,volume=4,apad=whole_dur={SURE},atrim=0:{SURE},"
          f"afade=t=out:st={SURE - 0.6}:d=0.6,aformat=channel_layouts=stereo[a];"
          f"[0:v]fade=t=out:st={SURE - 0.55}:d=0.55:color={KREM},format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(sessiz), "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-t", f"{SURE}", str(out)], check=True)
    print(f"Intro hazır: {out}")


if __name__ == "__main__":
    main()
