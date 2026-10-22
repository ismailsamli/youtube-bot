"""Kanal istatistikleri (YouTube Analytics): son N günde her video/Short için izlenme, ortalama izleme yüzdesi,
kazanılan abone. Sonuç data/istatistik.json'a yazılır ve ekrana basılır.

Kullanım: python tools/istatistik.py [gün=14]
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot import uploader  # noqa: E402
from bot.utils import load_json  # noqa: E402

ANALYTICS = "https://www.googleapis.com/auth/yt-analytics.readonly"


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    yt = uploader.get_service()
    if ANALYTICS not in uploader._STATE["scopes"]:
        print("HATA: İstatistik izni yok. YouTube izni yenilenmeli (YouTube İzni iş akışı).")
        return
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_file(str(uploader.TOKEN))
    ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    end, start = date.today(), date.today() - timedelta(days=days)
    hist = {h.get("video_id"): h for h in load_json(ROOT / "data" / "history.json", []) if h.get("video_id")}

    res = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end),
                             metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                                     "subscribersGained,likes,comments,shares",
                             dimensions="video", sort="-views", maxResults=50).execute()
    cols = [c["name"] for c in res.get("columnHeaders", [])]
    rows = [dict(zip(cols, r)) for r in res.get("rows", [])]
    tot = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end),
                             metrics="views,subscribersGained,subscribersLost,estimatedMinutesWatched").execute()
    tcols = [c["name"] for c in tot.get("columnHeaders", [])]
    total = dict(zip(tcols, (tot.get("rows") or [[0] * len(tcols)])[0]))
    try:   # abone kaynağı: hangi video abone getirdi + trafik kaynağı (Shorts akışı vb.)
        src = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end),
                                 metrics="views", dimensions="insightTrafficSourceType", sort="-views").execute()
        sources = {r[0]: r[1] for r in src.get("rows", [])}
    except Exception as e:
        sources = {"hata": str(e)[:100]}

    try:   # günlük seyir
        dd = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end),
                                metrics="views,subscribersGained,subscribersLost,estimatedMinutesWatched",
                                dimensions="day", sort="day").execute()
        daily = dd.get("rows", [])
    except Exception as e:
        daily = [["hata", str(e)[:100]]]
    out = {"from": str(start), "to": str(end), "total": total, "traffic": sources, "daily": daily, "videos": []}
    for r in daily:
        print("GÜN " + " ".join(str(x) for x in r))
    print(f"KANAL {start}..{end}: izlenme {total.get('views')}, +abone {total.get('subscribersGained')}, "
          f"-abone {total.get('subscribersLost')}, izlenme dk {total.get('estimatedMinutesWatched')}")
    print("TRAFİK: " + ", ".join(f"{k}={v}" for k, v in sources.items()))
    for r in rows:
        h = hist.get(r["video"], {})
        kind = "SHORT" if h.get("type") == "short" else "VIDEO"
        r.update({"type": kind, "title": h.get("title", "?")})
        out["videos"].append(r)
        print(f"{kind} {r['video']} | {r['views']} izl | %{r['averageViewPercentage']:.0f} izlenme | "
              f"{r['averageViewDuration']} sn | +{r['subscribersGained']} abone | {h.get('title', '?')[:50]}")
    (ROOT / "data" / "istatistik.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
