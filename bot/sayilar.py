"""Metindeki sayıları Türkçe okunuşa çevirir (klon ses rakamları ve tarihleri yanlış okuyor).
Örnek: "1929'da %40 düştü, 3,5 milyon kişi" → "bin dokuz yüz yirmi dokuzda yüzde kırk düştü, üç virgül beş milyon kişi"."""
import re

BIR = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
ON = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
BUYUK = [(10 ** 12, "trilyon"), (10 ** 9, "milyar"), (10 ** 6, "milyon"), (1000, "bin")]


def _uc(n: int) -> list:
    out = []
    y, n = divmod(n, 100)
    if y:
        out += ([BIR[y]] if y > 1 else []) + ["yüz"]
    o, b = divmod(n, 10)
    out += [w for w in (ON[o], BIR[b]) if w]
    return out


def oku(n: int) -> str:
    if n == 0:
        return "sıfır"
    out = []
    for deger, ad in BUYUK:
        k, n = divmod(n, deger)
        if k:
            out += ([] if (k == 1 and ad == "bin") else _uc(k) if k < 1000 else oku(k).split()) + [ad]
    out += _uc(n)
    return " ".join(out)


SIRA = {"bir": "birinci", "iki": "ikinci", "üç": "üçüncü", "dört": "dördüncü", "beş": "beşinci", "altı": "altıncı",
        "yedi": "yedinci", "sekiz": "sekizinci", "dokuz": "dokuzuncu", "on": "onuncu", "yirmi": "yirminci",
        "otuz": "otuzuncu", "kırk": "kırkıncı", "elli": "ellinci", "altmış": "altmışıncı", "yetmiş": "yetmişinci",
        "seksen": "sekseninci", "doksan": "doksanıncı", "yüz": "yüzüncü", "bin": "bininci", "milyon": "milyonuncu",
        "milyar": "milyarıncı"}


def _sira(m) -> str:
    w = oku(int(m.group(1) or m.group(2))).split()
    return " ".join(w[:-1] + [SIRA.get(w[-1], w[-1])])


def _sayi(s: str) -> int:
    return int(s.replace(".", ""))


def cevir(text: str) -> str:
    t = text
    # yüzde: %40 / % 40
    t = re.sub(r"%\s?(\d+(?:,\d+)?)", r"yüzde \1", t)
    # saat: 01.23 / 21:00
    t = re.sub(r"\b([01]?\d|2[0-3])[.:]([0-5]\d)\b(?:['’](\w+))?",
               lambda m: f"{oku(int(m.group(1)))} {oku(int(m.group(2))) if int(m.group(2)) else 'sıfır sıfır'}"
               + (m.group(3) or ""), t)
    # sıra sayısı: "19. yüzyıl" (küçük harf) ya da "2. Dünya Savaşı" (büyük harf, yalnız 1-99; "1986. Sonra" yıl kalır)
    t = re.sub(r"\b(\d{1,4})\.(?=\s+[a-zçğıöşü])|\b(\d{1,2})\.(?=\s+[A-ZÇĞİÖŞÜ])", _sira, t)
    # ondalık: 3,5
    t = re.sub(r"\b(\d+),(\d+)\b", lambda m: f"{oku(int(m.group(1)))} virgül {oku(int(m.group(2)))}"
               if not m.group(2).startswith("0") else f"{oku(int(m.group(1)))} virgül "
               + " ".join(oku(int(c)) for c in m.group(2)), t)
    # binlik ayraçlı veya düz tam sayı (+ kesme işaretli ek: 1929'da)
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})+|\d+)(?:['’](\w+))?",
               lambda m: oku(_sayi(m.group(1))) + (m.group(2) or ""), t)
    return re.sub(r"\s{2,}", " ", t)


if __name__ == "__main__":
    for s in ["1929'da borsa %40 düştü.", "2. Dünya Savaşı ve 19. yüzyıl", "3,5 milyon kişi, 1.500.000 lira",
              "Thodex 2021'de kapandı; 11.000 yıl, 0,05 saniye", "26 Nisan 1986 gecesi saat 01.23'te", "Yıl 1986. Sonra her şey değişti.", "3. Selim ve 100 yıl"]:
        print(s, "→", cevir(s))
