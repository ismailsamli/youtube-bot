"""Ses miksi: arka plan müziği altlığı + konuşurken müziği kısma (ducking) + YouTube ses seviyesi (-14 LUFS).

- assets/music klasöründeki parçalar karıştırılıp yumuşak geçişlerle (crossfade) video boyunca çalar.
- Anlatıcı konuşurken müzik otomatik kısılır, sessiz anlarda geri gelir.
- Jenerik animasyonu sırasında müzik susar (animasyonun kendi sesi var).
- Son ses iki geçişli loudnorm ile -14 LUFS'a çekilir (YouTube'un hedef seviyesi).
- Kullanılan parçalar muzik.json'a yazılır; açıklamaya kaynak olarak eklenir (CC BY lisansı bunu şart koşar).
"""
import json
import random
import re
from pathlib import Path

from .utils import ROOT, log, media_duration, run

MUSIC_DIR = ROOT / "assets" / "music"
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".ogg", ".oga", ".flac")
XFADE = 4.0          # parçalar arası geçiş (sn)


def tracks() -> list:
    return sorted(p for p in MUSIC_DIR.glob("*") if p.suffix.lower() in AUDIO_EXT)


def credits_for(names: list) -> list:
    """kaynaklar.json içinden kullanılan parçaların atıf satırları."""
    src = MUSIC_DIR / "kaynaklar.json"
    if not src.exists():
        return []
    try:
        info = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for n in names:
        line = (info.get(n) or {}).get("attribution")
        if line and line not in out:
            out.append(line)
    return out


def build_bed(duration: float, out: Path, seed: int) -> list:
    """Süreyi dolduran müzik altlığı (wav). Kullanılan parça adlarını döndürür."""
    pool = tracks()
    if not pool:
        return []
    rnd = random.Random(seed)
    rnd.shuffle(pool)
    seq, total, k = [], 0.0, 0
    while total < duration + 2 and k < 40:
        t = pool[k % len(pool)]
        d = media_duration(t)
        if d < XFADE * 3:
            k += 1
            if k > len(pool) * 2 and not seq:
                return []
            continue
        seq.append(t)
        total += d - (XFADE if len(seq) > 1 else 0)
        k += 1
    inputs, parts = [], []
    for i, t in enumerate(seq):
        inputs += ["-i", str(t)]
        # her parça önce aynı ses seviyesine çekilir (parçalar arası seviye farkı olmasın)
        parts.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                     f"loudnorm=I=-20:TP=-2:LRA=11,aresample=44100[t{i}]")
    chain, last = [], "t0"
    for i in range(1, len(seq)):
        chain.append(f"[{last}][t{i}]acrossfade=d={XFADE}:c1=tri:c2=tri[x{i}]")
        last = f"x{i}"
    fade_out = max(0.0, duration - 5)
    tail = (f"[{last}]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d=2,afade=t=out:st={fade_out:.3f}:d=5[bed]")
    run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex", ";".join(parts + chain + [tail]),
         "-map", "[bed]", "-ac", "2", "-ar", "44100", str(out)])
    return [t.name for t in seq]


def _integrated(path: Path) -> float:
    """Dosyanın sesinin ortalama yüksekliği (LUFS). Ölçülemezse -20."""
    import subprocess
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    try:
        val = float(m[-1])
        return val if val > -70 else -20.0
    except (IndexError, ValueError):
        return -20.0


def _loudnorm_args(path: Path) -> str:
    """1. geçiş: ölç; 2. geçiş için doğrusal loudnorm parametreleri."""
    import subprocess
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    if not m:
        return "loudnorm=I=-14:TP=-1.5:LRA=11"
    j = json.loads(m.group(0))
    return ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
            f"measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
            f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}")


def mix(video: Path, final: Path, cfg: dict, work: Path, mute: list = None, seed: int = 0) -> list:
    """video'nun sesine müzik altlığı ekler, -14 LUFS'a çeker ve final'a yazar.
    mute: müziğin susacağı (başlangıç, bitiş) aralıkları. Kullanılan parça adlarını döndürür."""
    v = cfg["video"]
    level = float(v.get("music_volume", 0.08))
    dur = media_duration(video)
    used = []
    bed = work / "muzik_altlik.wav"
    if level > 0:
        try:
            used = build_bed(dur, bed, seed)
        except RuntimeError as e:
            log(f"  Müzik altlığı hazırlanamadı, müziksiz devam: {str(e)[:200]}")
            used = []
    mixed = work / "karisik_ses.wav"
    if used:
        # Müzik, anlatıcı sesinin ölçülen seviyesine göre ayarlanır: konuşma aralarında sesin
        # music_below_voice_db kadar altında, konuşurken ducking ile ~15 dB daha kısık.
        voice_i = _integrated(video)
        below = float(v.get("music_below_voice_db", 12))
        gain = 10 ** (((voice_i - below) - (-20.0)) / 20) * (level / 0.4)
        gain = max(0.02, min(gain, 2.0))
        env = ""
        if mute:
            # her sessiz aralığın önünde/arkasında 0,6 sn'lik yumuşak iniş-çıkış (birden kesilmez)
            R = 0.6
            env = ",volume='" + "*".join(f"clip(max(({a:.2f}-t)/{R},(t-{b:.2f})/{R}),0,1)" for a, b in mute) + "':eval=frame"
        duck = v.get("music_duck", {}) or {}
        # eşik anlatıcının seviyesine göre: konuşma başlayınca müzik ~15 dB kısılır
        lvl_sc = min(64.0, max(0.02, 10 ** ((-20.0 - voice_i) / 20)))   # anlatıcı -20 seviyesine çekilerek ölçülür
        thr = 10 ** ((-20.0 - float(duck.get('threshold_below_voice_db', 18))) / 20)
        fc = (f"[1:a]volume={gain:.3f}{env}[m];"
              f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[v][sc];"
              f"[m][sc]sidechaincompress=threshold={thr:.5f}:level_sc={lvl_sc:.4f}:"
              f"ratio={duck.get('ratio', 12)}:attack={duck.get('attack', 20)}:"
              f"release={duck.get('release', 450)}[md];"
              f"[v][md]amix=inputs=2:duration=first:normalize=0[a]")
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(video), "-i", str(bed), "-filter_complex", fc,
             "-map", "[a]", "-ar", "44100", "-ac", "2", str(mixed)])
        log(f"  Arka plan müziği: {', '.join(used)}")
    else:
        if level > 0:
            log("  assets/music boş: video müziksiz (sadece ses seviyesi düzeltilecek)")
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(video), "-vn", "-ar", "44100", "-ac", "2", str(mixed)])
    ln = _loudnorm_args(mixed)
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(video), "-i", str(mixed),
         "-filter_complex", f"[1:a]{ln},aresample=44100[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(final)])
    for f in (bed, mixed):
        f.unlink(missing_ok=True)
    return used
