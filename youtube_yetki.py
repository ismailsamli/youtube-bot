"""
YouTube izni (tek seferlik) - bilgisayar gerekmeden, telefondan yapılabilir.

1. adım:  python youtube_yetki.py link
          -> Google izin bağlantısını üretir.
2. adım:  python youtube_yetki.py kod "<izin verdikten sonra adres çubuğundaki tam adres>"
          -> izni şifreleyip data/youtube_token.enc dosyasına kaydeder
             (bilgisayarda çalıştırılırsa ayrıca token.json oluşturur).
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google_auth_oauthlib.flow import Flow

from bot.secure import encrypt_token

ROOT = Path(__file__).resolve().parent
# upload: video yükleme · force-ssl: oynatma listesi, ilk yorum ve filigran
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
REDIRECT = "http://localhost:8080/"


def client_config() -> dict:
    raw = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    if not raw and (ROOT / "client_secret.json").exists():
        raw = (ROOT / "client_secret.json").read_text(encoding="utf-8")
    if not raw:
        sys.exit("HATA: YOUTUBE_CLIENT_SECRET bulunamadı.")
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit("HATA: YOUTUBE_CLIENT_SECRET geçerli bir JSON değil. İndirdiğin dosyanın "
                 "içeriğini olduğu gibi kopyaladığından emin ol.")
    if "installed" not in cfg:
        sys.exit("HATA: OAuth istemcisi 'Desktop app' (Masaüstü uygulaması) türünde olmalı.")
    return cfg


def make_flow() -> Flow:
    return Flow.from_client_config(client_config(), scopes=SCOPES, redirect_uri=REDIRECT,
                                   autogenerate_code_verifier=False)


def link() -> str:
    url, _ = make_flow().authorization_url(access_type="offline", prompt="consent",
                                           include_granted_scopes="true")
    return url


def exchange(pasted: str) -> str:
    pasted = pasted.strip()
    code = pasted
    if pasted.startswith("http"):
        qs = parse_qs(urlparse(pasted).query)
        if "error" in qs:
            sys.exit(f"HATA: Google izni reddetti: {qs['error'][0]}")
        if "code" not in qs:
            sys.exit("HATA: Yapıştırılan adreste 'code=' bulunamadı. Adres çubuğundaki tam adresi kopyala.")
        code = qs["code"][0]
    flow = make_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    if not creds.refresh_token:
        sys.exit("HATA: Kalıcı izin alınamadı. myaccount.google.com/permissions adresinden "
                 "uygulamanın iznini kaldırıp 1. adımdan tekrar başla.")
    return creds.to_json()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "link":
        print(link())
    elif len(sys.argv) >= 3 and sys.argv[1] == "kod":
        token = exchange(sys.argv[2])
        enc = ROOT / "data" / "youtube_token.enc"
        enc.parent.mkdir(exist_ok=True)
        enc.write_bytes(encrypt_token(token, json.dumps(client_config())))
        if not os.getenv("GITHUB_ACTIONS"):
            (ROOT / "token.json").write_text(token, encoding="utf-8")
        print("YouTube izni alındı ve şifreli olarak kaydedildi.")
    else:
        print(__doc__)
