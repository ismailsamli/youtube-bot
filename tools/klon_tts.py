"""Klon ses (Chatterbox Multilingual, MIT) ile metinleri okur — ayrı Python ortamında çalışır (bağımlılık çakışmasın diye).
Kullanım: <klon-python> tools/klon_tts.py is.json referans_ses
is.json = [{"text": "...", "out": "/yol/audio_000.wav"}, ...]"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def main():
    job, ref_src = Path(sys.argv[1]), Path(sys.argv[2])
    items = json.loads(job.read_text(encoding="utf-8"))
    import torch
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.set_num_threads(max(1, torch.get_num_threads()))
    ref = job.with_name("_referans.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ref_src), "-ac", "1", "-ar", "24000", str(ref)], check=True)
    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    print(f"klon: model {time.time() - t0:.0f} sn", flush=True)
    for i, it in enumerate(items):
        out = Path(it["out"])
        if out.exists() and out.stat().st_size > 2000:
            continue
        parcalar = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", it["text"]) if p.strip()] or [it["text"]]
        wav = torch.cat([model.generate(p, language_id="tr", audio_prompt_path=str(ref)) for p in parcalar], dim=-1)
        ta.save(str(out), wav, model.sr)
        print(f"klon: {i + 1}/{len(items)} ({time.time() - t0:.0f} sn)", flush=True)


if __name__ == "__main__":
    main()
