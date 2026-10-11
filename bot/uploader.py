"""YouTube Data API ile video + kapak yükleme ve yayın planlama."""
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .utils import ROOT, log

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN = ROOT / "token.json"


def _materialize_from_env() -> None:
    """Bulutta (GitHub Actions) anahtarlar dosya yerine gizli ortam değişkenlerinden gelir."""
    import os
    cs = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    tk = os.getenv("YOUTUBE_TOKEN", "").strip()
    if cs and not CLIENT_SECRET.exists():
        CLIENT_SECRET.write_text(cs, encoding="utf-8")
    if tk and not TOKEN.exists():
        TOKEN.write_text(tk, encoding="utf-8")
    enc = ROOT / "data" / "youtube_token.enc"
    if not TOKEN.exists() and enc.exists() and CLIENT_SECRET.exists():
        from .secure import decrypt_token
        try:
            TOKEN.write_text(decrypt_token(enc.read_bytes(), CLIENT_SECRET.read_text(encoding="utf-8")),
                             encoding="utf-8")
        except Exception:
            log("Kayıtlı YouTube izni açılamadı (istemci anahtarı değişmiş olabilir).")


def get_service():
    import os
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    _materialize_from_env()
    if os.getenv("GITHUB_ACTIONS") and not TOKEN.exists():
        raise SystemExit("HATA: YouTube izni yok. Rehberdeki 'YouTube izni' adımını uygula.")
    if not CLIENT_SECRET.exists():
        raise SystemExit("HATA: client_secret.json bulunamadı. README'deki 'YouTube bağlantısı' adımını uygula.")
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if (not creds or not creds.valid) and os.getenv("GITHUB_ACTIONS"):
            raise SystemExit("HATA: YouTube izni geçersiz veya süresi dolmuş. Rehberdeki "
                             "'YouTube izni' adımlarını tekrar uygula.")
        if not creds or not creds.valid:
            log("Tarayıcıda Google hesabınla giriş yapıp izin vermen gerekiyor...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def next_publish_time(cfg: dict, taken: list) -> datetime:
    """config'teki saatlere göre, daha önce planlananlarla çakışmayan ilk boş zamanı bulur."""
    up = cfg["upload"]
    tz = ZoneInfo(up.get("timezone", "Europe/Istanbul"))
    times = sorted(up.get("publish_times") or ["19:00"])
    taken_set = {datetime.fromisoformat(t).astimezone(timezone.utc).replace(second=0, microsecond=0)
                 for t in taken if t}
    earliest = datetime.now(tz) + timedelta(hours=1)  # YouTube'un işlemesi için pay
    day = earliest.date()
    for _ in range(400):
        for t in times:
            hh, mm = map(int, t.split(":"))
            slot = datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
            if slot >= earliest and slot.astimezone(timezone.utc) not in taken_set:
                return slot
        day += timedelta(days=1)
    raise RuntimeError("Uygun yayın zamanı bulunamadı.")


def _trim_tags(tags: list) -> list:
    out, total = [], 0
    for t in tags:
        t = t.replace("<", "").replace(">", "").strip()[:60]
        if t and total + len(t) + 3 <= 480:
            out.append(t)
            total += len(t) + 3
    return out


def upload(video: Path, thumb: Path, script: dict, cfg: dict, publish_at: datetime = None) -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = get_service()
    up = cfg["upload"]
    status = {
        "privacyStatus": "private" if publish_at else "public",
        "selfDeclaredMadeForKids": bool(up.get("made_for_kids", False)),
    }
    if publish_at:
        status["publishAt"] = publish_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    if up.get("synthetic_media", True):
        status["containsSyntheticMedia"] = True

    body = {
        "snippet": {
            "title": script["title"][:100],
            "description": script["description"][:4900],
            "tags": _trim_tags(script.get("tags", [])),
            "categoryId": str(up.get("category_id", "27")),
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr",
        },
        "status": status,
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    log("YouTube'a yükleniyor...")
    response, retry = None, 0
    while response is None:
        try:
            status_obj, response = request.next_chunk()
            if status_obj:
                log(f"  yükleme %{int(status_obj.progress() * 100)}")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retry < 6:
                retry += 1
                time.sleep(2 ** retry + random.random())
                continue
            if "quotaExceeded" in str(e) or "uploadLimitExceeded" in str(e):
                raise RuntimeError("YouTube günlük yükleme kotası doldu. Video kaydedildi; yarın "
                                   "'python run.py --upload-only KLASÖR' ile yükleyebilirsin.")
            raise
    video_id = response["id"]
    log(f"Yüklendi: https://youtu.be/{video_id}")

    try:
        yt.thumbnails().set(videoId=video_id,
                            media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
        log("Kapak fotoğrafı yüklendi.")
    except HttpError as e:
        log(f"Kapak yüklenemedi (kanalın telefonla doğrulanmış olması gerekir): {e}")
    return video_id
