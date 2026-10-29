"""Uzun videolarda klon ses: metinleri Kaggle'ın ücretsiz ekran kartında (GPU) Chatterbox ile okutur.
GitHub'daki secret: KAGGLE_API_TOKEN (ya da eski tip KAGGLE_KEY). Kaggle hesabında telefon doğrulaması şart.
Akış: metinler + referans ses tek bir Kaggle betiğine gömülür → `kaggle kernels push` → bitmesi beklenir →
`kaggle kernels output` ile wav dosyaları indirilir."""
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from bot.utils import log

SLUG = "kirmizi-kravat-ses"
KULLANICI = "krmzkravat"       # Kaggle kullanıcı adı (gizli değil)

BETIK = r'''
import base64, json, os, re, subprocess, sys, time
t0 = time.time()
# chatterbox torch 2.6 istiyor; Kaggle'ın hazır torchvision'ı yeni torch'a göre → uyumlu sürüm de kurulur
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "chatterbox-tts", "torchvision==0.21.0"], check=True)
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
METINLER = json.loads(base64.b64decode("__METIN__").decode("utf-8"))
open("/kaggle/working/_ref.mp3", "wb").write(base64.b64decode("__REF__"))
REF = "/kaggle/working/_ref.wav"
if subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "/kaggle/working/_ref.mp3", "-ac", "1", "-ar", "24000", REF]).returncode:
    REF = "/kaggle/working/_ref.mp3"
dev = "cuda" if torch.cuda.is_available() else "cpu"
print("cihaz:", dev, "kurulum", int(time.time() - t0), "sn", flush=True)
model = ChatterboxMultilingualTTS.from_pretrained(device=dev)
os.makedirs("/kaggle/working/ses", exist_ok=True)
for i, text in enumerate(METINLER):
    parca = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text) if p.strip()] or [text]
    wav = torch.cat([model.generate(p, language_id="tr", audio_prompt_path=REF).cpu()
                     for p in parca], dim=-1)
    ta.save(f"/kaggle/working/ses/klon_{i:03d}.wav", wav, model.sr)
    print(f"{i + 1}/{len(METINLER)} ({int(time.time() - t0)} sn)", flush=True)
print("BITTI", int(time.time() - t0), "sn", flush=True)
'''


def hazir() -> bool:
    return bool(os.environ.get("KAGGLE_API_TOKEN") or os.environ.get("KAGGLE_KEY"))


def _kaggle(*args, timeout=600) -> str:
    env = {k: v for k, v in os.environ.items() if not (k.startswith("KAGGLE_") and not v.strip())}  # boş secret'lar
    env.setdefault("KAGGLE_USERNAME", KULLANICI)
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=timeout, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"kaggle {args[0]} {args[1] if len(args) > 1 else ''}: {(r.stdout + r.stderr)[-600:]}")
    return r.stdout


def seslendir(texts: list, ref: Path, out_dir: Path, bekle_dk: int = 75) -> list:
    """texts → out_dir/klon_000.wav ... ; wav yollarını döndürür."""
    if not hazir():
        raise RuntimeError("Kaggle secret'ları yok")
    user = os.environ.get("KAGGLE_USERNAME", "").strip() or KULLANICI
    work = out_dir / "_kaggle"
    work.mkdir(parents=True, exist_ok=True)
    refwav = work / "ref.mp3"       # küçük tutulur: Kaggle betik boyutunu sınırlıyor
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ref), "-t", "30", "-ac", "1", "-ar", "24000",
                    "-b:a", "64k", str(refwav)], check=True)
    kod = (BETIK.replace("__METIN__", base64.b64encode(json.dumps(texts, ensure_ascii=False).encode()).decode())
           .replace("__REF__", base64.b64encode(refwav.read_bytes()).decode()))
    (work / "ses.py").write_text(kod, encoding="utf-8")
    log(f"  Kaggle betiği {len(kod) // 1024} KB")
    meta = {"id": f"{user}/{SLUG}", "title": SLUG, "code_file": "ses.py", "language": "python",
            "kernel_type": "script", "is_private": "true", "enable_gpu": "true", "enable_internet": "true",
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (work / "kernel-metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    log(f"  Kaggle: {len(texts)} sahne ekran kartına gönderiliyor")
    _kaggle("kernels", "push", "-p", str(work))
    t0 = time.time()
    time.sleep(60)
    while True:
        st = _kaggle("kernels", "status", f"{user}/{SLUG}", timeout=120).lower()
        if "complete" in st:
            break
        if "error" in st or "cancel" in st:
            raise RuntimeError(f"Kaggle işi hata verdi: {st.strip()[-200:]}")
        if time.time() - t0 > bekle_dk * 60:
            raise RuntimeError("Kaggle işi zamanında bitmedi")
        time.sleep(45)
    log(f"  Kaggle: bitti ({(time.time() - t0) / 60:.0f} dk), sesler indiriliyor")
    dl = work / "cikti"
    _kaggle("kernels", "output", f"{user}/{SLUG}", "-p", str(dl), "-o", timeout=900)
    wavs = []
    for i in range(len(texts)):
        f = next(iter(dl.rglob(f"klon_{i:03d}.wav")), None)
        if not f or f.stat().st_size < 2000:
            raise RuntimeError(f"Kaggle sesi eksik: {i + 1}. sahne")
        wavs.append(f)
    return wavs
