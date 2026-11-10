"""Kesik kâğıt motoru (motor/ klasörü) ile görüntü üretimi.

Plan (sahne listesi + altyazı) tarayıcıda (headless Chromium) kare kare çizilir, FFmpeg ile MP4 yapılır.
Görseller dışarıdan alınmaz: her şey kodla çizilir. Birden çok tarayıcı sayfası paralel çalışır.
"""
import base64
import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .utils import ROOT, log, run

MOTOR = ROOT / "motor"


def _open(page_w: int, page_h: int):
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    b = pw.chromium.launch(args=["--allow-file-access-from-files", "--disable-gpu"])
    pg = b.new_page(viewport={"width": page_w, "height": page_h})
    logs = []
    pg.on("console", lambda m: logs.append(m.text))
    pg.on("pageerror", lambda e: logs.append("JS HATA: " + str(e)))
    pg.goto((MOTOR / "index.html").as_uri())
    pg.wait_for_function("typeof window.yukle === 'function'")
    return pw, b, pg, logs


def _chunk(args) -> str:
    """Bir işçi: [f0, f1) karelerini çizip kendi MP4 parçasına yazar."""
    plan, f0, f1, fps, out, quality = args
    pw, b, pg, logs = _open(plan["w"], plan["h"])
    try:
        pg.evaluate("p => window.yukle(p)", plan)
        ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(fps),
                               "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                               "-pix_fmt", "yuv420p", "-r", str(fps), str(out)], stdin=subprocess.PIPE)
        step = 15   # tarayıcıdan tek seferde alınan kare sayısı
        for a in range(f0, f1, step):
            frames = pg.evaluate(
                """([a, b, fps, q]) => { const c = document.getElementById('c'), out = [];
                     for (let i = a; i < b; i++) { seek(i / fps); out.push(c.toDataURL('image/jpeg', q).slice(23)); }
                     return out; }""", [a, min(f1, a + step), fps, quality])
            for fr in frames:
                ff.stdin.write(base64.b64decode(fr))
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError("ffmpeg kare kodlama hatası")
    finally:
        b.close(); pw.stop()
    errs = [l for l in logs if "HATA" in l]
    return "\n".join(errs[:5])


def render(plan: dict, out: Path, fps: int = 30, workers: int = None, quality: float = 0.9) -> Path:
    """Planı sessiz MP4'e çizer (ses ayrıca eklenir)."""
    out = Path(out)
    work = out.parent / (out.stem + "_parcalar")
    work.mkdir(parents=True, exist_ok=True)
    total = int(round(float(plan["sure"]) * fps))
    workers = workers or max(1, min(4, os.cpu_count() or 2))
    per = -(-total // workers)
    jobs = [(plan, k * per, min(total, (k + 1) * per), fps, work / f"p{k:02d}.mp4", quality)
            for k in range(workers) if k * per < total]
    log(f"  Kâğıt motoru: {total} kare, {len(jobs)} paralel çizici")
    with ProcessPoolExecutor(len(jobs)) as ex:
        for msg in ex.map(_chunk, jobs):
            if msg:
                log("  " + msg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{j[4].name}'\n" for j in jobs), encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", str(out.resolve())], cwd=work)
    for j in jobs:
        j[4].unlink(missing_ok=True)
    return out


def still(plan: dict, out: Path, scene: int = 0, frac: float = 0.8, kapak: bool = True, t: float = None) -> Path:
    """Tek kare PNG: kapak (yazısız sahne) ya da belirli bir an."""
    pw, b, pg, logs = _open(plan["w"], plan["h"])
    try:
        pg.evaluate("p => window.yukle(p)", plan)
        if t is not None:
            pg.evaluate(f"seek({t})")
        else:
            pg.evaluate(f"kapak({scene}, {frac})")
        data = pg.evaluate("() => document.getElementById('c').toDataURL('image/png').slice(22)")
        Path(out).write_bytes(base64.b64decode(data))
    finally:
        b.close(); pw.stop()
    return Path(out)


def contact(plan: dict, out: Path, times: list, cols: int = 3, width: int = 640) -> Path:
    """Kontrol için birden çok anın küçük resimlerinden tek görsel."""
    from PIL import Image
    import io
    pw, b, pg, logs = _open(plan["w"], plan["h"])
    try:
        pg.evaluate("p => window.yukle(p)", plan)
        tiles = []
        for t in times:
            pg.evaluate(f"seek({t})")
            data = pg.evaluate("() => document.getElementById('c').toDataURL('image/jpeg', 0.85).slice(23)")
            im = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
            tiles.append(im.resize((width, int(width * im.height / im.width))))
    finally:
        b.close(); pw.stop()
    w, h = tiles[0].size
    rows = -(-len(tiles) // cols)
    sheet = Image.new("RGB", (w * cols, h * rows), "white")
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(out, quality=85)
    if logs:
        log("  " + " | ".join(l for l in logs if "HATA" in l)[:500])
    return Path(out)
