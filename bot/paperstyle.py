"""Kanal görsel stili: fotoğrafları kat kat kesilmiş renkli kâğıt (papercut) görünümüne çevirir."""
import cv2
import numpy as np
from PIL import Image


def kagit_kesme(img, levels=5, seed=3):
    """Kat kat kesilmiş renkli kâğıt (papercut): sabit kanal paleti, katlar arası gölge, kâğıt dokusu."""
    a = np.asarray(img.convert("RGB"))
    h, w = a.shape[:2]
    sm = cv2.bilateralFilter(a, 9, 75, 75)
    sm = cv2.bilateralFilter(sm, 9, 75, 75)
    sm = cv2.medianBlur(sm, 7)
    g = cv2.cvtColor(sm, cv2.COLOR_RGB2GRAY)
    g = cv2.createCLAHE(2.0, (8, 8)).apply(g).astype(np.float32) / 255
    hsv = cv2.cvtColor(sm, cv2.COLOR_RGB2HSV).astype(np.float32)
    warm = (((hsv[..., 0] < 8) | (hsv[..., 0] > 168)) & (hsv[..., 1] > 150) & (hsv[..., 2] > 70)).astype(np.uint8)
    # katlar: koyudan açığa (arkadan öne)
    pal = [(36, 32, 30), (92, 70, 58), (158, 128, 100), (210, 190, 160), (243, 234, 216)]
    qs = np.quantile(g, np.linspace(0, 1, levels + 1)[1:-1])
    def clean(m, k):
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
        m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.2)
        return (m > 0.5).astype(np.float32)
    k = max(5, w // 220)
    rng = np.random.default_rng(seed)
    def tex(color, s):
        n = cv2.GaussianBlur(rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32), (0, 0), 1)
        n = cv2.resize(n, (w, h))
        fib = cv2.resize(cv2.GaussianBlur(rng.normal(0, 1, (h // 10, w // 10)).astype(np.float32), (0, 0), 1.5), (w, h))
        t = 1 + 0.03 * n + 0.035 * fib
        return np.array(color, np.float32)[None, None, :] * t[..., None]
    out = tex(pal[0], 0)
    layers = [clean((g >= q).astype(np.uint8), k) for q in qs]
    layers.append(clean(warm, k))   # kırmızı kâğıt en üstte
    colors = pal[1:] + [(184, 30, 42)]
    for m, c in zip(layers, colors):
        if m.sum() < 50:
            continue
        sh = cv2.GaussianBlur(m, (0, 0), 6)
        M = np.float32([[1, 0, 5], [0, 1, 7]])
        sh = cv2.warpAffine(sh, M, (w, h))
        out = out * (1 - 0.45 * sh[..., None] * (1 - m[..., None]))
        # kesik kenarda ince açık kâğıt kenarı
        edge = np.clip(m - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1)
        layer = tex(c, 0) * (1 - 0.18 * edge[..., None]) + 255 * 0.18 * edge[..., None]
        out = out * (1 - m[..., None]) + layer * m[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def kagit_baski(img):
    """Fotoğrafı okunaklı tutan kâğıt baskı görünümü: ayrıntı korunur, sıcak sepya-krem ton,
    kâğıt dokusu ve hafif kenar kararması (kolaj çerçevesiyle birlikte kanal tarzına uyar)."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255
    h, w = a.shape[:2]
    g = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    g = cv2.createCLAHE(1.6, (8, 8)).apply(g).astype(np.float32) / 255
    # iki tonlu baskı: koyu kahve -> krem; orijinal rengin %35'i korunur (nesneler tanınsın)
    dark, light = np.array([46, 36, 30], np.float32) / 255, np.array([244, 234, 214], np.float32) / 255
    duo = dark[None, None, :] * (1 - g[..., None]) + light[None, None, :] * g[..., None]
    out = duo * 0.65 + a * 0.35
    # güçlü kırmızılar kanal rengi olarak kalsın
    hsv = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    red = (((hsv[..., 0] < 8) | (hsv[..., 0] > 168)) & (hsv[..., 1] > 140) & (hsv[..., 2] > 70)).astype(np.float32)
    red = cv2.GaussianBlur(red, (0, 0), 2)[..., None]
    out = out * (1 - 0.5 * red) + a * 0.5 * red
    # kâğıt dokusu (çarpma) + yumuşak vinyet
    rng = np.random.default_rng(5)
    n = cv2.resize(cv2.GaussianBlur(rng.normal(0, 1, (h // 3, w // 3)).astype(np.float32), (0, 0), 1), (w, h))
    out = out * (1 + 0.035 * n[..., None])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - 0.22 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    out = out * np.clip(v, 0.7, 1)[..., None]
    # hafif keskinlik: kâğıt üzerinde baskı netliği
    out8 = np.clip(out * 255, 0, 255).astype(np.uint8)
    blur = cv2.GaussianBlur(out8, (0, 0), 1.5)
    out8 = cv2.addWeighted(out8, 1.4, blur, -0.4, 0)
    return Image.fromarray(out8)
