"""FFmpeg ile sahneleri, sesi ve altyazıyı birleştirip son videoyu üretir."""
import json
import math
import random
import re
from pathlib import Path

from .utils import ROOT, log, media_duration, run


# ---------------- Altyazı ----------------
def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _chunks(text: str, max_words: int = 7) -> list:
    """Metni ekranda okunabilir küçük parçalara böler, noktalama işaretlerinde kesmeyi tercih eder."""
    words = text.split()
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or (len(cur) >= 3 and re.search(r"[.!?,;:]$", w)):
            out.append(" ".join(cur))
            cur = []
    if cur:
        if out and len(cur) <= 2:
            out[-1] += " " + " ".join(cur)
        else:
            out.append(" ".join(cur))
    return out


def write_ass(text: str, duration: float, path: Path, cfg: dict) -> None:
    v = cfg["video"]
    font, size = v.get("subtitle_font", "Arial"), v.get("subtitle_size", 62)
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {v['width']}\nPlayResY: {v['height']}\nWrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,"
        f"-1,0,0,0,100,100,0,0,1,4,2,2,{v.get('subtitle_margin_lr', 160)},{v.get('subtitle_margin_lr', 160)},"
        f"{v.get('subtitle_margin_v', 70)},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    parts = _chunks(text, v.get("subtitle_words", 7))
    total_chars = sum(len(p) for p in parts) or 1
    t, lines = 0.0, []
    for p in parts:
        d = duration * len(p) / total_chars
        safe = p.replace("{", "(").replace("}", ")").replace("\\", "")
        lines.append(f"Dialogue: 0,{_ass_time(t)},{_ass_time(t + d)},Default,,0,0,0,,{safe}")
        t += d
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


# ---------------- Sahne klibi ----------------
ENCODE = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]


def build_scene(idx: int, visual: Path, kind: str, audio: Path, text: str,
                work: Path, cfg: dict) -> Path:
    out = work / f"scene_{idx:03d}.mp4"
    if out.exists():
        return out
    v = cfg["video"]
    W, H, fps = v["width"], v["height"], v["fps"]
    pad = v.get("scene_padding", 0.35)
    speech = media_duration(audio)
    dur = speech + pad
    ass = f"subs_{idx:03d}.ass"
    write_ass(text, speech, work / ass, cfg)

    if kind == "video":
        inputs = ["-stream_loop", "-1", "-i", str(visual.resolve())]
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"setsar=1,fps={fps},format=yuv420p,ass={ass}[v]")
    else:
        frames = math.ceil(dur * fps) + 5
        # Sırayla yakınlaşma / uzaklaşma (Ken Burns efekti)
        zm = v.get("zoom_max", 1.18)
        if idx % 2 == 0:
            zoom = f"min(zoom+0.0006,{zm})"
        else:
            zoom = f"if(eq(on,0),{zm},max(zoom-0.0006,1.0))"
        inputs = ["-i", str(visual.resolve())]
        vf = (f"[0:v]scale={W * 3 // 2}:{H * 3 // 2}:force_original_aspect_ratio=increase,"
              f"crop={W * 3 // 2}:{H * 3 // 2},"
              f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              f"d={frames}:s={W}x{H}:fps={fps},setsar=1,format=yuv420p,ass={ass}[v]")

    cmd = ["ffmpeg", "-y", "-hide_banner", *inputs, "-i", str(audio.resolve()),
           "-filter_complex", f"{vf};[1:a]apad=pad_dur={pad}[a]",
           "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}", *ENCODE, out.name]
    run(cmd, cwd=work)
    return out


# ---------------- Birleştirme ----------------
def concat(scene_files: list, work: Path, final: Path, cfg: dict, mute: list = None) -> list:
    """Sahneleri birleştirir; müzik altlığı, ducking ve ses seviyesi mixer'da. Kullanılan müzikleri döndürür."""
    from . import mixer
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in scene_files), encoding="utf-8")
    joined = work / "joined.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", lst.name,
         "-c", "copy", joined.name], cwd=work)
    try:
        return mixer.mix(joined, final, cfg, work, mute=mute, seed=len(scene_files))
    except RuntimeError as e:
        log(f"Ses miksi yapılamadı, müziksiz devam ediliyor: {str(e)[:300]}")
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(joined), "-c", "copy",
             "-movflags", "+faststart", str(final)])
        return []


def assemble(scenes: list, visuals: list, audios: list, work: Path, final: Path, cfg: dict,
             intro: Path = None, outro: Path = None) -> Path:
    """Sıra: soğuk açılış sahneleri -> kanal jeneriği (intro) -> video -> kapanış jeneriği (outro)."""
    work.mkdir(parents=True, exist_ok=True)
    clips, mute, t = [], [], 0.0
    n_cold = sum(1 for s in scenes if s.get("cold"))
    for i, (scene, (vis, kind), audio) in enumerate(zip(scenes, visuals, audios)):
        if intro is not None and i == n_cold:
            d = media_duration(intro)
            mute.append((t, t + d))          # jenerik animasyonunun kendi sesi var: müzik sussun
            clips.append(intro)
            t += d
        clip = build_scene(i, vis, kind, audio, scene["text"], work, cfg)
        clips.append(clip)
        t += media_duration(clip)
        if (i + 1) % 5 == 0 or i + 1 == len(scenes):
            log(f"  montaj {i + 1}/{len(scenes)}")
    if outro is not None:
        clips.append(outro)
    used = concat(clips, work, final, cfg, mute)
    (final.parent / "muzik.json").write_text(json.dumps(used, ensure_ascii=False), encoding="utf-8")
    log(f"Video hazır: {final} ({media_duration(final) / 60:.1f} dk)")
    return final
