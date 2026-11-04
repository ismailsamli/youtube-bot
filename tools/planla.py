"""Özel (gizli) videoları yeniden planlar: belirtilen saatte otomatik herkese açılır. Sadece kullanıcı onayıyla.
Kullanım: python tools/planla.py "VIDEO_ID=2026-11-04 19:00" ["VIDEO_ID=2026-11-05 12:00" ...]   (Türkiye saati)"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import uploader  # noqa: E402

YAZILABILIR = ("embeddable", "license", "publicStatsViewable", "selfDeclaredMadeForKids", "containsSyntheticMedia")
TR = ZoneInfo("Europe/Istanbul")

yt = uploader.get_service()
for arg in sys.argv[1:]:
    vid, zaman = arg.split("=", 1)
    when = datetime.strptime(zaman.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=TR)
    if when <= datetime.now(TR):
        print(f"{vid}: {zaman} geçmiş bir saat, atlandı")
        continue
    items = yt.videos().list(part="status,snippet", id=vid).execute().get("items", [])
    if not items:
        print(f"{vid}: bulunamadı")
        continue
    st = items[0]["status"]
    print(f"{vid}: şu an {st.get('privacyStatus')} / yayın {st.get('publishAt')}")
    yeni = {k: st[k] for k in YAZILABILIR if k in st}
    yeni["privacyStatus"] = "private"
    yeni["publishAt"] = when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    yt.videos().update(part="status", body={"id": vid, "status": yeni}).execute()
    import time
    time.sleep(5)
    st2 = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    print(f"{vid} ({items[0]['snippet']['title'][:45]}): {st2.get('privacyStatus')} / yayın {st2.get('publishAt')}")
