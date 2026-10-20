"""Uzun videoya bağlı olmayan tek bir Short üretir ve planlı yükler (ör. seri tanıtımı).

Kullanım: python tools/tek_short.py "konu" "2026-10-22 21:00" ["ek talimat"]
"""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import shorts, uploader  # noqa: E402
from bot.script_writer import LLM, _ask_json, _system, TR_HASSAS  # noqa: E402
from bot.utils import load_config, load_json, log, save_json, slugify  # noqa: E402
from bot.visuals import VisualFinder  # noqa: E402


def main():
    konu, zaman = sys.argv[1], sys.argv[2]
    ek = sys.argv[3] if len(sys.argv) > 3 else ""
    cfg = load_config()
    tz = ZoneInfo(cfg["upload"].get("timezone", "Europe/Istanbul"))
    when = datetime.strptime(zaman, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    folder = ROOT / "output" / f"short_{when:%Y%m%d}_{slugify(konu)[:40]}"
    (folder / "visuals").mkdir(parents=True, exist_ok=True)

    prompt = f"""KONU: {konu}
{ek}

Bu konu için tek bir YouTube Shorts senaryosu yaz:
- İlk cümle doğrudan kanca; 3-5 cümlede mini hikâye; sonu merak bırakan bir cümle.
- Toplam 125-145 kelime (EN AZ 125), 7-9 sahne (her sahne 14-20 kelime). Sadece doğrulanabilir bilgiler.
- Her sahne için "prompt": sahnenin çizilecek görüntüsünü anlatan 15-30 kelimelik İNGİLİZCE tarif
  (somut nesne/sahne; stil kelimesi, yazı, gerçek kişi yüzü YOK).
- "title": en fazla 70 karakter dürüst, merak uyandıran başlık; "headline": 2-5 kelimelik ekran başlığı;
  "comment": izleyiciye kısa bir soru.
Sadece JSON: {{"title": "...", "headline": "...", "comment": "...", "scenes": [{{"text": "...", "prompt": "..."}}]}}"""
    s = _ask_json(LLM(cfg), _system(cfg), prompt, 4000, "scenes")
    finder = VisualFinder(cfg, folder / "visuals")
    for i, sc in enumerate(s["scenes"]):
        raw = folder / "visuals" / f"visual_{i:03d}_ham.png"
        if not raw.exists():
            if not finder.ai_image(sc.get("prompt") or konu, raw):
                finder.commons_image(" ".join((sc.get("prompt") or konu).split()[:3]), raw)
        sc["src"] = i
    video = shorts.build_short(cfg, folder, s, 0)
    meta = {"title": (s["title"][:90] + " #shorts")[:100],
            "description": f"{s['title']}\n\nHer akşam 19:00'da yeni bir gerçek hikâye: Kırmızı Kravat.\n"
                           "#shorts #bilgi #ilginçbilgiler",
            "tags": ["shorts", "ilginç bilgiler", "tarih"]}
    vid = uploader.upload(video, None, meta, cfg, when)
    hist_path = ROOT / "data" / "history.json"
    hist = load_json(hist_path, [])
    hist.append({"folder": folder.name, "title": s["title"], "type": "short", "status": "yüklendi",
                 "video_id": vid, "publish_at": when.isoformat(), "comment": s.get("comment")})
    save_json(hist_path, hist)
    log(f"Tek Short yüklendi ve {when:%d.%m %H:%M} için planlandı: {vid}")


if __name__ == "__main__":
    main()
