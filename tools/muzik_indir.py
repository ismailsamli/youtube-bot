"""Arka plan müziklerini indirir: Kevin MacLeod (incompetech.com), CC BY 4.0 lisanslı.

Belgesel/gizem tonuna uyan seçilmiş parçalar assets/music klasörüne kaydedilir ve
assets/music/kaynaklar.json'a atıf satırı yazılır (bot bunu video açıklamasına ekler).
Kullanım:  python tools/muzik_indir.py [adet]
"""
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot.utils import slugify  # noqa: E402

MUSIC = ROOT / "assets" / "music"
HEADERS = {"User-Agent": "KirmiziKravatBot/1.0 (YouTube video botu; arka plan muzigi)"}

# Belgesel / gizem / gerilim tonunda, anlatının altında rahatsız etmeyen parçalar (öncelik sırasıyla)
TITLES = [
    "Lightless Dawn", "Long Note Two", "Investigations", "Echoes of Time v2", "Ossuary 6 - Air",
    "Darkest Child", "Dark Walk", "Gathering Darkness", "Long Note Three", "Atlantean Twilight",
    "Comfortable Mystery 4", "Despair and Triumph", "Floating Cities", "Spacial Harvest",
    "Stages of Grief", "Long Note Four", "Ossuary 5 - Rest", "Clean Soul", "Dreamy Flashback",
]
LICENSE = "Creative Commons: By Attribution 4.0 License http://creativecommons.org/licenses/by/4.0/"


def duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", str(p)], capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def from_incompetech(title: str, raw: Path) -> bool:
    for base in ("https://incompetech.com/music/royalty-free/mp3-royaltyfree/",
                 "https://incompetech.filmmusic.io/music/royalty-free/mp3-royaltyfree/"):
        try:
            r = requests.get(base + quote(title) + ".mp3", headers=HEADERS, timeout=120)
        except requests.RequestException as e:
            print(f"  ağ hatası: {e}")
            continue
        if r.ok and len(r.content) > 200_000 and r.content[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            raw.write_bytes(r.content)
            return True
        print(f"  {base[:40]}… -> {r.status_code}")
    return False


def from_commons(title: str, raw: Path) -> bool:
    """Yedek: Wikimedia Commons'taki aynı parça (Kevin MacLeod, CC BY)."""
    api = "https://commons.wikimedia.org/w/api.php"
    try:
        r = requests.get(api, headers=HEADERS, timeout=60, params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f'"{title}" Kevin MacLeod filetype:audio', "gsrlimit": 5,
            "prop": "imageinfo", "iiprop": "url|extmetadata"})
        pages = (r.json().get("query") or {}).get("pages") or {}
    except Exception as e:
        print(f"  Commons hatası: {e}")
        return False
    for p in pages.values():
        info = (p.get("imageinfo") or [{}])[0]
        lic = ((info.get("extmetadata") or {}).get("LicenseShortName") or {}).get("value", "")
        name = p.get("title", "").lower()
        if title.lower().split(" ")[0] not in name or not any(k in lic for k in ("CC BY", "CC0", "Public domain")) \
                or "SA" in lic:
            continue
        try:
            d = requests.get(info["url"], headers=HEADERS, timeout=120)
            if d.ok and len(d.content) > 200_000:
                raw.write_bytes(d.content)
                print(f"  Commons: {p['title']} ({lic})")
                return True
        except requests.RequestException:
            continue
    return False


def main(want: int = 8) -> None:
    MUSIC.mkdir(parents=True, exist_ok=True)
    src = MUSIC / "kaynaklar.json"
    info = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
    have = sum(1 for k in info if (MUSIC / k).exists())
    for title in TITLES:
        if have >= want:
            break
        name = slugify(title) + ".mp3"
        if (MUSIC / name).exists():
            continue
        print(f"İndiriliyor: {title}")
        raw = MUSIC / ("_ham_" + name)
        ok = from_incompetech(title, raw) or from_commons(title, raw)
        if not ok:
            print("  bulunamadı, atlandı")
            continue
        d = duration(raw)
        if not 75 <= d <= 900:
            print(f"  süre uygun değil ({d:.0f} sn), atlandı")
            raw.unlink(missing_ok=True)
            continue
        # depoda yer kaplamasın: 128 kbps stereo
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-ac", "2", "-ar", "44100",
                        "-b:a", "128k", str(MUSIC / name)], check=True)
        raw.unlink(missing_ok=True)
        info[name] = {"title": title, "artist": "Kevin MacLeod", "seconds": round(d),
                      "attribution": f"\"{title}\" Kevin MacLeod (incompetech.com) — Licensed under {LICENSE}"}
        have += 1
        print(f"  tamam: {name} ({d:.0f} sn)")
    src.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Toplam parça: {have}")
    if have == 0:
        sys.exit("HATA: hiç parça indirilemedi")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
