"""Yüklenmiş videoların kapaklarını kanal tarzında yeniden üretir ve YouTube'da değiştirir.
Liste: data/kapak_yenile.json  ->  [{"video_id", "text", "prompt"}]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from googleapiclient.http import MediaFileUpload  # noqa: E402

from bot import thumbnail, uploader  # noqa: E402
from bot.utils import load_config  # noqa: E402
from bot.visuals import VisualFinder  # noqa: E402

cfg = load_config()
items = json.loads(Path("data/kapak_yenile.json").read_text(encoding="utf-8"))
out = Path("kapaklar")
out.mkdir(exist_ok=True)
finder = VisualFinder(cfg, out / "_tmp")
yt = uploader.get_service()
for it in items:
    vid = it["video_id"]
    bg = out / "_tmp" / f"{vid}_{len(it['text'])}.png"
    if not finder.cloudflare_image(it["prompt"], bg):
        print(f"HATA {vid}: çizim üretilemedi")
        continue
    jpg = out / (it.get("dosya") or f"{vid}.jpg")
    jpg.parent.mkdir(parents=True, exist_ok=True)
    thumbnail.make_thumbnail(bg, it["text"], jpg)
    if it.get("sadece_dosya"):      # kapak testi seçeneği: YouTube'daki kapağa dokunma
        print(f"OK {vid}: dosya hazır ({jpg})")
        continue
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(jpg), mimetype="image/jpeg")).execute()
        print(f"OK {vid}: kapak değiştirildi")
    except Exception as e:
        print(f"HATA {vid}: {str(e)[:200]}")
