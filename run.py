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

from bot import branding, editor, script_writer, shorts, thumbnail, tts, uploader
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
        extra = None
        if isinstance(topic, dict):
            topic, extra = topic["konu"], topic["extra"]
        script = script_writer.generate(cfg, past, topic, extra)
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
    # Kapak çizimi önce: günlük ücretsiz çizim kotası biterse en önemli görsel kapak olsun
    thumb_bg = folder / "visuals" / "thumb_bg.png"
    if not thumb_bg.exists():
        finder.ai_image(script["thumbnail_prompt"], thumb_bg)
    visuals = []
    for i, (scene, audio) in enumerate(zip(script["scenes"], audios)):
        visuals.append(finder.get(scene, i, media_duration(audio)))
        if (i + 1) % 10 == 0 or i + 1 == len(audios):
            log(f"  görsel {i + 1}/{len(audios)}")

    log(f"  Yapay zeka çizimi: {getattr(finder, 'cf_count', 0)}/{len(visuals)} sahne")
    log("Kapak fotoğrafı hazırlanıyor...")
    if not thumb_bg.exists():
        # Yapay zeka yoksa ilk görselden bir kare kullan
        first, kind = visuals[0]
        ham = first.with_name(first.stem + "_ham.png")
        if kind == "image" and ham.exists():
            first = ham       # kapakta kolaj çerçevesi değil, görselin kendisi kullanılır
        if kind == "video":
            run(["ffmpeg", "-y", "-ss", "1", "-i", str(first), "-frames:v", "1", str(thumb_bg)])
        else:
            shutil.copy(first, thumb_bg)
    badge = None
    if script.get("series"):
        badge = f"{script['series']['name']} #{script['series'].get('episode')}"
    thumbnail.make_thumbnail(thumb_bg, script.get("thumbnail_text", script["title"]),
                             folder / "thumbnail.jpg", badge)
    if cfg["upload"].get("thumbnail_variants", True):
        make_thumbnail_variants(cfg, script, folder, finder, thumb_bg)

    log("Video montajı yapılıyor (bu adım birkaç dakika sürebilir)...")
    final = folder / "video.mp4"
    intro = outro = None
    if cfg["video"].get("branding", True):
        try:
            intro = branding.make_intro(folder / "scenes", cfg)
            try:
                line = tts.say(branding.OUTRO_LINE, cfg, folder / "audio" / "outro.mp3", folder / "audio")
            except Exception as e:
                log(f"  Kapanış sesi okunamadı, sessiz devam: {e}")
                line = None
            outro = branding.make_outro(folder / "scenes", cfg, line)
        except Exception as e:
            log(f"  Jenerik hazırlanamadı, jeneriksiz devam ediliyor: {e}")
            intro = outro = None
    editor.assemble(script["scenes"], visuals, audios, folder / "scenes", final, cfg, intro, outro)
    try:   # kontrol için önizleme: açılış, jenerik, orta, bitiş ekranı karelerinden tek görsel (depoya kaydedilir)
        pad = float(cfg["video"].get("scene_padding", 0.2))
        cold = sum(media_duration(a) + pad for s, a in zip(script["scenes"], audios) if s.get("cold"))
        total = media_duration(final)
        times = [1.5, cold + 3.5 if intro else cold + 1, total / 2, total - 5]
        prev = ROOT / "kapaklar" / folder.name[:60]
        prev.mkdir(parents=True, exist_ok=True)
        tiles = []
        for k, t in enumerate(times):
            fr = folder / f"_onizleme_{k}.jpg"
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0, t):.2f}", "-i", str(final), "-frames:v", "1",
                 "-vf", "scale=640:360", str(fr)])
            tiles.append(fr)
        from PIL import Image as _I
        sheet = _I.new("RGB", (1280, 720))
        for k, fr in enumerate(tiles):
            sheet.paste(_I.open(fr), ((k % 2) * 640, (k // 2) * 360))
        sheet.save(prev / "onizleme.jpg", quality=80)
        log(f"  Önizleme kaydedildi (jenerik {'var' if intro else 'YOK'}, açılış {cold:.0f} sn)")
        # senaryo + başlık/açıklama da kaydedilir: yayından önce kontrol için (özellikle hassas bölümler)
        (prev / "senaryo.txt").write_text(
            f"BAŞLIK: {script['title']}\nKAPAK: {script.get('thumbnail_text', '')}\n\n"
            + "\n\n".join(s["text"] for s in script["scenes"]) + f"\n\nAÇIKLAMA:\n{script['description']}",
            encoding="utf-8")
    except Exception as e:
        log(f"  Önizleme alınamadı: {e}")

    # YouTube bölümleri (zaman damgaları): izleyici ve algoritma için "önemli anlar"
    if "Bölümler:" not in script["description"] and script.get("sections"):
        pad = float(cfg["video"].get("scene_padding", 0.2))
        t, starts = 0.0, {}
        intro_done = intro is None
        for sc, au in zip(script["scenes"], audios):
            if not intro_done and not sc.get("cold"):
                t += media_duration(intro)
                intro_done = True
            sec = sc.get("section")
            if sec is not None and sec not in starts:
                starts[sec] = t
            t += media_duration(au) + pad
        marks = sorted(starts.items(), key=lambda kv: kv[1])
        if marks and marks[0][1] < 5:             # ilk bölüm her zaman 00:00'da başlamalı
            marks[0] = (marks[0][0], 0.0)
        names = lambda k: "Giriş" if k == -1 else (script["sections"][k] if k < len(script["sections"]) else None)
        if len(marks) >= 3 and marks[0][1] == 0.0:
            lines = [f"{int(v // 60):02d}:{int(v % 60):02d} {names(k)}" for k, v in marks if names(k)]
            script["description"] = script["description"] + "\n\nBölümler:\n" + "\n".join(lines)
            save_json(folder / "script.json", script)

    # Kullanılan müziklerin kaynakları (CC BY lisansı atıf ister)
    try:
        from bot import mixer
        used = load_json(folder / "muzik.json", []) or []
        lines = mixer.credits_for(used)
        if lines and "Müzik:" not in script["description"]:
            script["description"] = (script["description"] + "\n\nMüzik:\n" + "\n".join(lines))[:4900]
            save_json(folder / "script.json", script)
    except Exception as e:
        log(f"  Müzik kaynakları eklenemedi: {e}")

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


def make_thumbnail_variants(cfg: dict, script: dict, folder: Path, finder, thumb_bg: Path) -> None:
    """Studio'daki 'Test ve karşılaştır' için 3 kapak: A (asıl), B (farklı yazı), C (farklı yazı + görsel).
    kapaklar/<tarih>_<başlık>/ klasörüne kaydedilir (depoya eklenir)."""
    try:
        alts = [a for a in (script.get("thumbnail_alt") or []) if isinstance(a, dict) and a.get("text")][:2]
        if not alts:
            return
        out = ROOT / "kapaklar" / folder.name[:60]
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy(folder / "thumbnail.jpg", out / "A.jpg")
        badge = f"{script['series']['name']} #{script['series'].get('episode')}" if script.get("series") else None
        thumbnail.make_thumbnail(thumb_bg, alts[0]["text"], out / "B.jpg", badge)
        if len(alts) > 1:
            bg_c = folder / "visuals" / "thumb_bg_c.png"
            if not bg_c.exists() and not (alts[1].get("prompt") and finder.ai_image(alts[1]["prompt"], bg_c)):
                bg_c = thumb_bg
            thumbnail.make_thumbnail(bg_c, alts[1]["text"], out / "C.jpg", badge)
        (out / "bilgi.txt").write_text(
            f"{script['title']}\nA: {script.get('thumbnail_text', '')}\n"
            + "\n".join(f"{'BC'[i]}: {a['text']}" for i, a in enumerate(alts)) + "\n", encoding="utf-8")
        log(f"  Kapak testi için 3 kapak hazır: kapaklar/{out.name}")
    except Exception as e:
        log(f"  Kapak seçenekleri üretilemedi: {e}")


def channel_upkeep(cfg: dict) -> None:
    """Hata olursa video üretimini asla durdurmaz."""
    try:
        _channel_upkeep(cfg)
    except Exception as e:
        log(f"  Kanal bakımı hata verdi, atlandı: {str(e)[:200]}")


def _channel_upkeep(cfg: dict) -> None:
    """Videoları oynatma listelerine ekler, yayına girmiş videolara ilk yorumu yazar, kanal filigranını
    bir kez ayarlar. Genişletilmiş YouTube izni yoksa atlar (izin yenilenince eksikleri tamamlar)."""
    up = cfg["upload"]
    if not (up.get("first_comment") or up.get("watermark") or up.get("playlists")):
        return
    try:
        yt = uploader.get_service()
    except BaseException as e:   # izin yoksa üretim yine de devam etsin
        log(f"  Kanal bakımı atlandı: {e}")
        return
    if not uploader.can_manage():
        log("  Yorum/filigran için YouTube izninin yenilenmesi gerekiyor (bir kez).")
        return
    state_file = ROOT / "data" / "kanal_durumu.json"
    state = load_json(state_file, {})
    if up.get("watermark") and not state.get("watermark"):
        if uploader.set_watermark(yt, ROOT / "assets" / "filigran.png"):
            state["watermark"] = datetime.now().isoformat(timespec="seconds")
            save_json(state_file, state)
    if up.get("playlists"):
        for h in load_history():
            if h.get("video_id") and h.get("playlist") and not h.get("playlist_done"):
                if uploader.add_to_playlist(yt, h["video_id"], h["playlist"], cfg):
                    add_history({**h, "playlist_done": True})
    if up.get("first_comment"):
        now = datetime.now().astimezone()
        for h in load_history():
            if (h.get("video_id") and h.get("comment") and not h.get("comment_done") and h.get("publish_at")
                    and datetime.fromisoformat(h["publish_at"]) <= now):
                if uploader.post_comment(yt, h["video_id"], h["comment"]):
                    log(f"  İlk yorum yazıldı: {h['title'][:50]}")
                    add_history({**h, "comment_done": True})
    if up.get("reply_comments", True):
        reply_to_comments(cfg, yt, state, state_file)


def reply_to_comments(cfg: dict, yt, state: dict, state_file: Path) -> None:
    """İzleyici yorumlarına kanal adına kısa, samimi cevap yazar (spam/hakaret/siyaset atlanır)."""
    try:
        ch = yt.channels().list(part="id", mine=True).execute()["items"][0]["id"]
        res = yt.commentThreads().list(part="snippet,replies", allThreadsRelatedToChannelId=ch,
                                       maxResults=50, order="time", textFormat="plainText").execute()
    except Exception as e:
        log(f"  Yorumlar okunamadı: {str(e)[:150]}")
        return
    done = set(state.get("cevaplanan", []))
    titles = {h.get("video_id"): h.get("title", "") for h in load_history()}
    todo = []
    for t in res.get("items", []):
        top = t["snippet"]["topLevelComment"]["snippet"]
        if t["id"] in done or (top.get("authorChannelId") or {}).get("value") == ch:
            continue
        if any((r["snippet"].get("authorChannelId") or {}).get("value") == ch
               for r in (t.get("replies") or {}).get("comments", [])):
            continue
        todo.append((t["id"], top.get("textDisplay", "")[:500], titles.get(t["snippet"].get("videoId"), "")))
    if not todo:
        return
    from bot.script_writer import LLM, _ask_json
    llm = LLM(cfg)
    system = ("Sen 'Kırmızı Kravat' adlı Türkçe bilgi kanalının samimi ama ölçülü sesisin. İzleyici yorumlarına "
              "kanal adına cevap yazıyorsun. Kurallar: 1-2 kısa cümle, doğal Türkçe, en fazla 1 emoji; teşekkür et, "
              "soru varsa videonun konusuna dayanarak kısa ve doğru cevap ver, emin değilsen uydurma; uygunsa "
              "sohbeti sürdüren kısa bir soru sor. Spam, link, reklam, hakaret, siyaset, din tartışması, kişisel "
              "bilgi isteyen veya anlamsız yorumlarda karar='atla' döndür. Sadece JSON döndür.")
    for tid, text, title in todo[:15]:
        try:
            d = _ask_json(llm, system, f'Video: "{title}"\nİzleyici yorumu: "{text}"\n'
                          'JSON: {"karar": "cevapla" veya "atla", "reply": "..."}', 400, "karar")
        except Exception as e:
            log(f"  Yorum cevabı yazılamadı: {str(e)[:120]}")
            continue
        if d.get("karar") == "cevapla" and (d.get("reply") or "").strip():
            try:
                yt.comments().insert(part="snippet", body={"snippet": {
                    "parentId": tid, "textOriginal": d["reply"].strip()[:500]}}).execute()
                log(f"  Yoruma cevap verildi: {text[:40]!r} -> {d['reply'][:60]!r}")
            except Exception as e:
                log(f"  Yoruma cevap gönderilemedi: {str(e)[:120]}")
                continue
        done.add(tid)
    state["cevaplanan"] = sorted(done)[-500:]
    save_json(state_file, state)


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
    entry = {"folder": folder.name, "title": script["title"], "status": "yüklendi",
             "video_id": vid, "publish_at": publish_at.isoformat() if publish_at else None,
             "comment": script.get("comment"), "playlist": script.get("playlist")}
    add_history(entry)
    publish_shorts(cfg, folder, script, entry)


def publish_shorts(cfg: dict, folder: Path, script: dict, entry: dict) -> None:
    """Uzun videodan Shorts üretip ertesi güne planlar. Hata olursa uzun video etkilenmez."""
    if not cfg.get("shorts", {}).get("enabled", True) or not script.get("scenes"):
        return
    if any(h.get("folder", "").startswith(folder.name + "#short") for h in load_history()):
        return
    try:
        def up(video, meta, when):
            log(f"Short yükleniyor: {meta['title'][:60]} ({when:%d.%m %H:%M})")
            return uploader.upload(video, None, meta, cfg, when)
        for e in shorts.make_and_upload(cfg, folder, script, entry, up):
            add_history(e)
    except Exception as e:
        log(f"Shorts atlandı: {e}")


def planned_topic(cfg: dict):
    """konular.yaml'da, sıradaki yayın gününe yazılmış bir konu varsa onu döndürür."""
    path = ROOT / "konular.yaml"
    if not path.exists():
        return None
    try:
        import yaml
        plan = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        taken = [h.get("publish_at") for h in load_history()]
        day = uploader.next_publish_time(cfg, taken).date().isoformat()
        topic = plan.get(day) or plan.get(str(day))
        if isinstance(topic, dict):      # seri bölümü
            topic = {"konu": topic.get("konu"), "extra": {
                "series": topic.get("seri"), "episode": topic.get("bolum"), "next": topic.get("sonraki") or "",
                "notes": topic.get("notlar") or "", "tr": bool(topic.get("tr"))}}
            if not topic["konu"]:
                return None
        if topic:
            log(f"Yayın günü {day} için seçilmiş konu: {topic if isinstance(topic, str) else topic['konu']}")
        return topic
    except Exception as e:
        log(f"  konular.yaml okunamadı: {e}")
        return None


def scout_topic(cfg: dict):
    """Konu avcısının (tools/konu_avcisi.py) kanıtlanmış konularından birini seçer; her gün değil,
    config'teki sıklıkla (varsayılan: iki günde bir), böylece kanalın kendi konu çeşitliliği de sürer."""
    sc = cfg.get("scout", {})
    if not sc.get("enabled", True):
        return None
    every = int(sc.get("every_n_days", 2))
    if datetime.now().timetuple().tm_yday % max(1, every):
        return None
    path = ROOT / "data" / "konu_onerileri.json"
    data = load_json(path, {})
    for o in data.get("oneriler", []):
        if not o.get("kullanildi") and o.get("konu"):
            o["kullanildi"] = True
            save_json(path, data)
            log(f"Konu avcısından kanıtlanmış konu: {o['konu']} (ilham: {o.get('kaynak_baslik', '')})")
            return {"konu": o["konu"], "extra": {
                "series": None, "episode": None, "next": "", "tr": False,
                "notes": (f"Bakış açısı: {o.get('aci', '')}. Bu konu İngilizce'de çok ilgi gören bir videodan "
                          "ilham alındı; SADECE konu fikrini kullan. İçeriği kendi bilgin ve güvenilir kaynaklarla "
                          "sıfırdan kur, hiçbir videonun metnini, yapısını veya başlığını kopyalama.")}}
    return None


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
    ap.add_argument("--max-queue", type=int, default=0,
                    help="Bu kadar video zaten yayın sırasındaysa yeni video üretme (0 = sınır yok)")
    args = ap.parse_args()

    cfg = load_config()
    check_ffmpeg()
    do_upload = cfg["upload"].get("enabled", True) and not args.no_upload

    if args.upload_only:
        publish(cfg, Path(args.upload_only))
        return

    if do_upload:
        channel_upkeep(cfg)

    if args.max_queue and not args.resume:
        now = datetime.now().astimezone()
        waiting = [h for h in load_history() if h.get("publish_at") and h.get("type") != "short"
                   and datetime.fromisoformat(h["publish_at"]) > now]
        if len(waiting) >= args.max_queue:
            log(f"Yayın sırasında zaten {len(waiting)} video var; bugün yeni video üretilmedi.")
            return

    failures = 0
    for n in range(args.count):
        log(f"========== Video {n + 1}/{args.count} ==========")
        folder = Path(args.resume) if args.resume and n == 0 else None
        CURRENT["folder"] = folder
        try:
            topic = args.topic if n == 0 else None
            if not topic and not folder:
                topic = planned_topic(cfg) or scout_topic(cfg)
            folder = produce(cfg, folder, topic)
            if do_upload:
                publish(cfg, folder)
                channel_upkeep(cfg)
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
