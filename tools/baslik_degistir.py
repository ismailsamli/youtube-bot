"""Yüklenmiş bir videonun başlığını değiştirir (videoya dokunmaz).
Kullanım: python tools/baslik_degistir.py VIDEO_ID "Yeni başlık"
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import uploader  # noqa: E402

vid, title = sys.argv[1], sys.argv[2][:100]
yt = uploader.get_service()
item = yt.videos().list(part="snippet", id=vid).execute()["items"][0]
sn = item["snippet"]
old = sn["title"]
sn["title"] = title
body = {"id": vid, "snippet": {k: sn[k] for k in ("title", "description", "categoryId", "tags",
                                                 "defaultLanguage", "defaultAudioLanguage") if k in sn}}
yt.videos().update(part="snippet", body=body).execute()
print(f"OK {vid}: '{old}' -> '{title}'")
h = ROOT / "data" / "history.json"
data = json.loads(h.read_text(encoding="utf-8"))
for x in data:
    if x.get("video_id") == vid:
        x["title"] = title.replace(" #shorts", "")
h.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
