"""Konu avcısı: İngilizce bilgi/gizem kanallarında kendi kanal ortalamasını katlayan (patlamış) videoları bulur,
Türk izleyiciye uygun olanları seçip Türkçe konu önerisine çevirir. Videolar kopyalanmaz; sadece KONU alınır,
bot konuyu kendi kaynaklarından sıfırdan araştırıp kendi tarzında anlatır.

Çıktı: data/konu_onerileri.json  (run.py boş günlerde buradan konu seçer)
Kullanım: python tools/konu_avcisi.py
"""
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import uploader  # noqa: E402
from bot.script_writer import LLM, _ask_json, _system  # noqa: E402
from bot.utils import load_config, load_json, log, save_json  # noqa: E402

ARAMALAR = [
    "survival story documentary", "unsolved mystery explained", "history dark secret documentary",
    "human body facts you didn't know", "brain tricks psychology explained", "biggest fraud scam story",
    "disaster what happened documentary", "strangest place on earth", "space scary facts",
    "ancient civilization mystery", "engineering failure disaster", "deadliest animal facts",
]
OUT = ROOT / "data" / "konu_onerileri.json"


def main():
    cfg = load_config()
    yt = uploader.get_service()
    since = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
    vids = {}
    for q in ARAMALAR:
        try:
            res = yt.search().list(part="snippet", q=q, type="video", order="viewCount", maxResults=25,
                                   publishedAfter=since, relevanceLanguage="en", videoDuration="medium").execute()
        except Exception as e:
            log(f"  arama hatası ({q}): {str(e)[:150]}")
            continue
        for it in res.get("items", []):
            vids[it["id"]["videoId"]] = {"title": it["snippet"]["title"], "channel": it["snippet"]["channelId"],
                                         "channel_title": it["snippet"]["channelTitle"]}
    log(f"{len(vids)} aday video bulundu")
    ids = list(vids)
    for i in range(0, len(ids), 50):
        for it in yt.videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute().get("items", []):
            vids[it["id"]]["views"] = int(it["statistics"].get("viewCount", 0))
    chans = list({v["channel"] for v in vids.values()})
    cstat = {}
    for i in range(0, len(chans), 50):
        for it in yt.channels().list(part="statistics", id=",".join(chans[i:i + 50])).execute().get("items", []):
            s = it["statistics"]
            n = max(1, int(s.get("videoCount", 1)))
            cstat[it["id"]] = {"avg": int(s.get("viewCount", 0)) / n, "subs": int(s.get("subscriberCount", 0) or 0)}
    adaylar = []
    for vid, v in vids.items():
        c = cstat.get(v["channel"])
        if not c or not v.get("views"):
            continue
        ratio = v["views"] / max(1, c["avg"])
        if v["views"] >= 100_000 and ratio >= 3:
            adaylar.append({**v, "id": vid, "ratio": round(ratio, 1), "subs": c["subs"],
                            "score": round(math.log10(v["views"]) * min(ratio, 50), 1)})
    adaylar.sort(key=lambda x: -x["score"])
    adaylar = adaylar[:60]
    log(f"{len(adaylar)} patlamış video (ortalamanın en az 3 katı, 100 bin+)")
    if not adaylar:
        return

    gecmis = [h["title"] for h in load_json(ROOT / "data" / "history.json", [])]
    liste = "\n".join(f"- {a['title']} ({a['views'] // 1000}K izlenme, kanal ortalamasının {a['ratio']} katı)"
                      for a in adaylar)
    prompt = f"""Aşağıda İngilizce YouTube'da son aylarda kanal ortalamasını katlayan, yani konusu kanıtlanmış ilgi
gören videoların başlıkları var. Bunlardan Türkçe bilgi kanalımız için en iyi 12 KONUYU seç.
Kurallar:
- Videoyu değil KONUYU alıyoruz; konu evrensel ve doğrulanabilir gerçeklere dayanmalı.
- Güncel siyaset, seçimler, partiler, terör, savaş propagandası, dini/etnik tartışma, ünlü dedikodusu, sağlık
  tavsiyesi YOK. Kanaldaki şu videolarla aynı konuyu tekrar etme: {"; ".join(gecmis[-40:])}
- Türk izleyicinin de merak edeceği konuları öne al.
- Her öneri için: "konu" (Türkçe, bot için net konu cümlesi), "aci" (özgün bakış açısı, 1 cümle),
  "kaynak_baslik" (ilham alınan İngilizce başlık, aynen), "neden" (neden tutar, kısa).
Adaylar:
{liste}

Sadece JSON: {{"oneriler": [{{"konu": "...", "aci": "...", "kaynak_baslik": "...", "neden": "..."}}]}}"""
    data = _ask_json(LLM(cfg), _system(cfg), prompt, 4000, "oneriler")
    by_title = {a["title"]: a for a in adaylar}
    old = load_json(OUT, {"oneriler": []})
    kullanilan = {o["konu"] for o in old.get("oneriler", []) if o.get("kullanildi")}
    yeni = []
    for o in data.get("oneriler", [])[:12]:
        a = by_title.get(o.get("kaynak_baslik", ""), {})
        o.update({"izlenme": a.get("views"), "kat": a.get("ratio"), "kaynak": a.get("id"),
                  "kullanildi": o.get("konu") in kullanilan, "tarih": datetime.now().strftime("%Y-%m-%d")})
        yeni.append(o)
    # eski kullanılmamış öneriler de havuzda kalsın (en fazla 30)
    havuz = yeni + [o for o in old.get("oneriler", []) if not o.get("kullanildi") and o["konu"] not in
                    {y["konu"] for y in yeni}]
    save_json(OUT, {"guncelleme": datetime.now().strftime("%Y-%m-%d"), "oneriler": havuz[:30]})
    for o in yeni:
        print(f"• {o['konu']}  ← \"{o.get('kaynak_baslik', '')}\" ({(o.get('izlenme') or 0) // 1000}K, "
              f"{o.get('kat')}x)")


if __name__ == "__main__":
    main()
