"""Kanal vitrini: kanal açıklaması + kanal sayfası bölümleri (seriler önde).
Kullanım: python tools/kanal_vitrini.py [goster|uygula]
- goster: mevcut açıklamayı, oynatma listelerini ve bölümleri yazar (hiçbir şey değiştirmez)
- uygula: data/kanal_aciklama.txt'yi kanal açıklaması yapar; seri oynatma listelerini kanal sayfasına bölüm olarak ekler
Anahtar kelimelere, ülkeye, dile dokunmaz."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import uploader  # noqa: E402

SERILER = ["Vurgun Dosyaları", "İnsan Vücudu ve Beynin Tuhaflıkları", "Çözülemeyen Gizemler"]   # kanal sayfasında bu sırayla


def main():
    mod = sys.argv[1] if len(sys.argv) > 1 else "goster"
    yt = uploader.get_service()
    ch = yt.channels().list(part="brandingSettings,snippet", mine=True).execute()["items"][0]
    c = ch.get("brandingSettings", {}).get("channel", {})
    print("AÇIKLAMA (şimdiki):", (ch["snippet"].get("description") or "(boş)")[:600])
    lists, tok = {}, None
    while True:
        r = yt.playlists().list(part="snippet,contentDetails", mine=True, maxResults=50, pageToken=tok).execute()
        for p in r.get("items", []):
            lists[p["snippet"]["title"]] = (p["id"], p["contentDetails"]["itemCount"])
        tok = r.get("nextPageToken")
        if not tok:
            break
    print("OYNATMA LİSTELERİ:", "; ".join(f"{k} ({v[1]})" for k, v in lists.items()))
    secs = yt.channelSections().list(part="snippet,contentDetails", mine=True).execute().get("items", [])
    print("BÖLÜMLER:", "; ".join(f"{s['snippet']['type']}:{s['snippet'].get('title', '')}"
                                 f"{s.get('contentDetails', {}).get('playlists', '')}" for s in secs) or "(yok)")
    if mod != "uygula":
        return
    yeni = (ROOT / "data" / "kanal_aciklama.txt").read_text(encoding="utf-8").strip()
    c["description"] = yeni
    body = {"id": ch["id"], "brandingSettings": {"channel": c}}
    if ch["brandingSettings"].get("watch"):
        body["brandingSettings"]["watch"] = ch["brandingSettings"]["watch"]
    yt.channels().update(part="brandingSettings", body=body).execute()
    print("Açıklama güncellendi.")
    var = {pid for s in secs for pid in s.get("contentDetails", {}).get("playlists", [])}
    for i, ad in enumerate(SERILER):
        if ad not in lists or lists[ad][0] in var or lists[ad][1] == 0:
            continue
        try:
            yt.channelSections().insert(part="snippet,contentDetails", body={
                "snippet": {"type": "singlePlaylist", "position": i},
                "contentDetails": {"playlists": [lists[ad][0]]}}).execute()
            print(f"Kanal sayfasına bölüm eklendi: {ad}")
        except Exception as e:
            print(f"Bölüm eklenemedi ({ad}): {str(e)[:200]}")


if __name__ == "__main__":
    main()
