"""Cloudflare ile kanal tarzında birkaç örnek çizim üretir (gorsel_ornekleri/ klasörüne)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.utils import load_config  # noqa: E402
from bot.visuals import VisualFinder  # noqa: E402
from bot.collage import collage  # noqa: E402
from PIL import Image  # noqa: E402

ORNEKLER = [
    "a box jellyfish with long trailing tentacles drifting in deep blue ocean water",
    "a tall Soviet drilling tower standing alone in a snowy northern landscape",
    "an overturned tugboat lying on the dark sea floor with a small air pocket inside",
    "Ottoman ships being pulled over a green hill on wooden rails at dawn",
]
cfg = load_config()
out = Path("gorsel_ornekleri")
out.mkdir(exist_ok=True)
f = VisualFinder(cfg, out / "_tmp")
for i, p in enumerate(ORNEKLER):
    path = out / f"ornek_{i + 1}.png"
    ok = f.cloudflare_image(p, path)
    print(("OK " if ok else "HATA ") + p)
    if ok:
        img = Image.open(path).convert("RGB")
        collage(img, i).resize((1280, 720)).save(out / f"ornek_{i + 1}_kolaj.jpg", quality=88)
        img.resize((1280, 720)).save(out / f"ornek_{i + 1}.jpg", quality=88)
        path.unlink()
