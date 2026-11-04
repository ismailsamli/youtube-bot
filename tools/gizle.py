"""Planlı/yayındaki videoları 'özel' yapar ve planlı yayını iptal eder (SİLMEZ). Sadece kullanıcı onayıyla çalıştırılır.
Kullanım: python tools/gizle.py VIDEO_ID [VIDEO_ID ...]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import uploader  # noqa: E402

YAZILABILIR = ("privacyStatus", "embeddable", "license", "publicStatsViewable", "selfDeclaredMadeForKids",
               "containsSyntheticMedia")

yt = uploader.get_service()
for vid in sys.argv[1:]:
    items = yt.videos().list(part="status,snippet", id=vid).execute().get("items", [])
    if not items:
        print(f"{vid}: bulunamadı")
        continue
    st = items[0]["status"]
    print(f"{vid} ({items[0]['snippet']['title'][:50]}): önce {st.get('privacyStatus')} / plan {st.get('publishAt')}")
    yeni = {k: st[k] for k in YAZILABILIR if k in st}
    yeni["privacyStatus"] = "private"
    yeni["publishAt"] = None                   # planlı yayını açıkça iptal et (alanı göndermemek yetmiyor)
    yt.videos().update(part="status", body={"id": vid, "status": yeni}).execute()
    st2 = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    if st2.get("publishAt"):
        # Hâlâ planlıysa: "liste dışı" yapılınca plan silinir (plan sadece özel videoda olabilir), hemen geri özel yapılır
        print(f"{vid}: plan hâlâ duruyor, liste dışı → özel ile siliniyor")
        yeni.pop("publishAt", None)
        yt.videos().update(part="status", body={"id": vid, "status": {**yeni, "privacyStatus": "unlisted"}}).execute()
        yt.videos().update(part="status", body={"id": vid, "status": {**yeni, "privacyStatus": "private"}}).execute()
        st2 = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    print(f"{vid}: şimdi {st2.get('privacyStatus')} / plan {st2.get('publishAt') or 'YOK (yayına girmeyecek)'}")
