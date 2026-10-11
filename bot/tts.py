"""Ücretsiz Microsoft Edge Türkçe sesleriyle seslendirme."""
import asyncio
import time
from pathlib import Path

import edge_tts

from .utils import log


async def _save(text: str, voice: str, rate: str, path: Path) -> None:
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def synthesize(text: str, voice: str, rate: str, path: Path, retries: int = 4) -> None:
    last = None
    for attempt in range(retries):
        try:
            asyncio.run(_save(text, voice, rate, path))
            if path.exists() and path.stat().st_size > 1000:
                return
        except Exception as e:  # ağ hataları vb.
            last = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Seslendirme başarısız: {last}")


def voice_scenes(scenes: list, cfg: dict, out_dir: Path) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    voice, rate = cfg["voice"]["name"], cfg["voice"]["rate"]
    paths = []
    for i, scene in enumerate(scenes):
        path = out_dir / f"audio_{i:03d}.mp3"
        if not path.exists():
            synthesize(scene["text"], voice, rate, path)
        paths.append(path)
        if (i + 1) % 10 == 0 or i + 1 == len(scenes):
            log(f"  seslendirme {i + 1}/{len(scenes)}")
    return paths
