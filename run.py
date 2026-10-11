"""
YouTube Video Botu
------------------
Kullanım:
  python run.py                      -> 1 video üretir, YouTube'a yükler ve planlar
  python run.py --count 3            -> 3 video üretir
  python run.py --topic "Piri Reis haritasının sırrı"   -> belirli bir konu
  python run.py --no-upload          -> sadece videoyu üretir, yüklemez
  python run.py --resume output/KLASÖR       -> yarıda kalan bir videoya kaldığı yerden devam eder
  python run.py --upload-only output/KLASÖR  -> hazır bir videoyu yükler
"""
import argparse
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

from bot import editor, script_writer, thumbnail, tts, uploader
from bot.utils import ROOT, check_ffmpeg, load_config, load_json, log, media_duration, run, save_json, slugify
from bot.visuals import VisualFinder

HISTORY = ROOT / "data" / "history.json"
OUTPUT = ROOT / "output"
CURRENT = {"folder": None}


def load_history() -> list:
    return load_json(HISTORY, [])


def add_history(entry: dict) -> None:
    HISTORY.parent.mkdir(exist_ok=True)
    hist = load_history()
    hist = [h for h in hist if h.get("folder") != entry.get("folder")] + [entry]
    save_json(HISTORY, hist)


def produce(cfg: dict, folder: Path = None, topic: str = None) -> Path:
    """Senaryodan son videoya kadar her şeyi üretir. Var olan adımları atlar."""
    if folder is not None and (folder / "video.mp4").exists() and (folder / "thumbnail.jpg").exists():
        log(f"Video zaten hazır: {folder}")
        return folder
    if folder is None:
        past = [h["title"] for h in load_history()]
        script = script_writer.generate(cfg, past, topic)
        folder = OUTPUT / f"{datetime.now():%Y%m%d-%H%M}_{slugify(script['title'])}"
        folder.mkdir(parents=True, exist_ok=True)
        save_json(folder / "script.json", script)
        CURRENT["folder"] = folder
    else:
        script = load_json(folder / "script.json")
        if not script:
            sys.exit(f"HATA: {folder} içinde script.json yok.")
        log(f"Devam ediliyor: {script['title']}")

    add_history({"folder": folder.name, "title": script["title"], "status": "üretiliyor"})
    (folder / "senaryo.txt").write_text(
        f"{script['title']}\n\n" + "\n\n".join(s["text"] for s in script["scenes"]),
        encoding="utf-8")

    log("Seslendirme yapılıyor...")
    audios = tts.voice_scenes(script["scenes"], cfg, folder / "audio")

    log("Görseller hazırlanıyor...")
    finder = VisualFinder(cfg, folder / "visuals")
    t = script.get("topic") or {}
    finder.topic = (t.get("search_en") or t.get("topic") or "")[:60]
    visuals = []
    for i, (scene, audio) in enumerate(zip(script["scenes"], audios)):
        visuals.append(finder.get(scene, i, media_duration(audio)))
        if (i + 1) % 10 == 0 or i + 1 == len(audios):
            log(f"  görsel {i + 1}/{len(audios)}")

    log("Kapak fotoğrafı hazırlanıyor...")
    thumb_bg = folder / "visuals" / "thumb_bg.png"
    if not thumb_bg.exists() and not finder.ai_image(script["thumbnail_prompt"], thumb_bg):
        # Yapay zeka yoksa ilk görselden bir kare kullan
        first, kind = visuals[0]
        if kind == "video":
            run(["ffmpeg", "-y", "-ss", "1", "-i", str(first), "-frames:v", "1", str(thumb_bg)])
        else:
            shutil.copy(first, thumb_bg)
    thumbnail.make_thumbnail(thumb_bg, script.get("thumbnail_text", script["title"]),
                             folder / "thumbnail.jpg")

    log("Video montajı yapılıyor (bu adım birkaç dakika sürebilir)...")
    final = folder / "video.mp4"
    editor.assemble(script["scenes"], visuals, audios, folder / "scenes", final, cfg)

    # Lisanslı görsellerin kaynakları açıklamaya eklenir (CC lisansları bunu şart koşar)
    if finder.credits and "Görsel kaynakları" not in script["description"]:
        uniq = list(dict.fromkeys(finder.credits))
        block = "\n\nGörsel kaynakları (Wikimedia Commons / Openverse):\n" + "\n".join(f"• {c}" for c in uniq)
        script["description"] = (script["description"] + block)[:4900]
        save_json(folder / "script.json", script)
    meta = (f"BAŞLIK:\n{script['title']}\n\nAÇIKLAMA:\n{script['description']}\n\n"
            f"ETİKETLER:\n{', '.join(script.get('tags', []))}\n")
    (folder / "youtube_bilgileri.txt").write_text(meta, encoding="utf-8")
    add_history({"folder": folder.name, "title": script["title"], "status": "hazır"})
    return folder


def _script_from_meta(folder: Path) -> dict:
    """script.json yoksa youtube_bilgileri.txt'den başlık/açıklama/etiketleri okur."""
    text = (folder / "youtube_bilgileri.txt").read_text(encoding="utf-8")
    title = text.split("BAŞLIK:\n", 1)[1].split("\n\nAÇIKLAMA:\n", 1)[0].strip()
    desc = text.split("\n\nAÇIKLAMA:\n", 1)[1].rsplit("\n\nETİKETLER:\n", 1)[0].strip()
    tags = [t.strip() for t in text.rsplit("ETİKETLER:\n", 1)[1].split(",") if t.strip()]
    return {"title": title, "description": desc, "tags": tags}


def publish(cfg: dict, folder: Path) -> None:
    if (folder / "script.json").exists():
        script = load_json(folder / "script.json")
    else:
        script = _script_from_meta(folder)
    publish_at = None
    if cfg["upload"].get("schedule", True):
        taken = [h.get("publish_at") for h in load_history()]
        publish_at = uploader.next_publish_time(cfg, taken)
        log(f"Yayın zamanı: {publish_at:%d.%m.%Y %H:%M}")
    vid = uploader.upload(folder / "video.mp4", folder / "thumbnail.jpg", script, cfg, publish_at)
    add_history({"folder": folder.name, "title": script["title"], "status": "yüklendi",
                 "video_id": vid, "publish_at": publish_at.isoformat() if publish_at else None})


def cleanup(folder: Path) -> None:
    """Büyük ara dosyaları siler; video, kapak ve senaryo kalır."""
    for sub in ("scenes", "visuals", "audio"):
        shutil.rmtree(folder / sub, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="YouTube video botu")
    ap.add_argument("--count", type=int, default=1, help="Kaç video üretilsin")
    ap.add_argument("--topic", help="Belirli bir konu (verilmezse bot seçer)")
    ap.add_argument("--no-upload", action="store_true", help="YouTube'a yükleme")
    ap.add_argument("--resume", help="Yarıda kalan video klasörü")
    ap.add_argument("--upload-only", help="Hazır videoyu yükle")
    ap.add_argument("--keep-files", action="store_true", help="Ara dosyaları silme")
    args = ap.parse_args()

    cfg = load_config()
    check_ffmpeg()
    do_upload = cfg["upload"].get("enabled", True) and not args.no_upload

    if args.upload_only:
        publish(cfg, Path(args.upload_only))
        return

    failures = 0
    for n in range(args.count):
        log(f"========== Video {n + 1}/{args.count} ==========")
        folder = Path(args.resume) if args.resume and n == 0 else None
        CURRENT["folder"] = folder
        try:
            folder = produce(cfg, folder, args.topic if n == 0 else None)
            if do_upload:
                publish(cfg, folder)
            if not args.keep_files:
                cleanup(folder)
            log(f"Tamamlandı: {folder}")
        except KeyboardInterrupt:
            sys.exit("Durduruldu.")
        except SystemExit:
            raise
        except Exception as e:
            failures += 1
            log(f"HATA: {e}")
            traceback.print_exc()
            folder = CURRENT["folder"]
            if folder:
                log(f"Kaldığı yerden devam etmek için: python run.py --resume \"{folder}\"")
    if failures:
        sys.exit(f"{failures} video başarısız oldu.")


if __name__ == "__main__":
    main()
