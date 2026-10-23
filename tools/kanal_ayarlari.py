"""Kanal ayarlarını günceller: anahtar kelimeler, ülke, varsayılan dil (diğer marka ayarları korunur)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import uploader  # noqa: E402

KELIMELER = ['"ilginç bilgiler"', '"bilinmeyen gerçekler"', "belgesel", "gizemler", '"çözülemeyen gizemler"',
             "tarih", '"tarihin karanlık sırları"', '"hayatta kalma hikayeleri"', '"gerçek hikayeler"', "bilim",
             '"insan vücudu"', "beyin", "uzay", '"doğal afetler"', '"dolandırıcılık hikayeleri"',
             '"vurgun dosyaları"', '"genel kültür"', '"Kırmızı Kravat"']

yt = uploader.get_service()
ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
b = ch.get("brandingSettings", {})
c = b.get("channel", {})
print("ÖNCE: anahtar kelimeler =", (c.get("keywords") or "")[:300])
print("ÖNCE: ülke =", c.get("country"), "| dil =", c.get("defaultLanguage"))
c["keywords"] = " ".join(KELIMELER)
c["country"] = "TR"
c["defaultLanguage"] = "tr"
body = {"id": ch["id"], "brandingSettings": {"channel": c}}
if b.get("watch"):
    body["brandingSettings"]["watch"] = b["watch"]
yt.channels().update(part="brandingSettings", body=body).execute()
after = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]["brandingSettings"]["channel"]
print("SONRA: anahtar kelimeler =", after.get("keywords"))
print("SONRA: ülke =", after.get("country"), "| dil =", after.get("defaultLanguage"))
