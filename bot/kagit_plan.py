"""Kesik kâğıt motoru için: senaryo kuralları, sahne denetimi, plan kurma ve sesli bölüm üretimi.

Akış: Gemini her sahneye bir "kalip" (kalıp) ve "p" (parametreler) yazar → normalize() bunu denetler ve
gerekirse güvenli bir kalıba çevirir → segment() sahneleri klon sesle eşleyip motorda çizer ve sesi ekler.
"""
import re
from pathlib import Path

from . import kagit_motor
from .editor import ENCODE, _chunks
from .utils import log, media_duration, run

ICONS = ("dunya,gezegen,halkali,gunes,ay,roket,uydu,kara_delik,yildiz,ucak,gemi,yuk_gemisi,araba,tren,denizalti,"
         "bina,banka,ev,fabrika,saray,hapishane,mahkeme,para,banknot,altin,kripto,cuzdan,kasa,grafik_dusus,"
         "grafik_artis,petrol,elmas,tac,belge,gazete,mektup,kitap,harita,anahtar,kilit,terazi,kelepce,insan,kadin,"
         "kalabalik,polis,bilim_insani,asker,saat,kum_saati,takvim,bilgisayar,telefon,sunucu,kamera,ampul,beyin,"
         "kalp,dna,hucre,virus,ilac,mikroskop,termometre,ates,damla,simsek,dag,agac,dalga,buz,kafatasi,soru,unlem,"
         "carpi,tik,hedef,bayrak,zincir,kalkan,ok_yukari,ok_asagi").split(",")
KALIPLAR = ["baslik", "nesne", "sayi", "karsilastirma", "zaman", "rota", "grafik", "liste", "gazete", "yigin",
            "gosterge", "kisi", "ortam", "soru", "yuzde", "akis"]
ORTAMLAR = ["sehir", "deniz", "okyanus", "uzay", "gece", "col", "dag", "buz", "orman", "ofis"]
ARACLAR = ["ucak", "gemi", "yuk_gemisi", "araba", "tren", "denizalti", "roket", "insan"]

RULES = f"""GÖRSELLER (her sahne için "kalip" ve "p" yaz). Görüntüler kesik kâğıt bilgi grafiği olarak KODLA çizilir;
fotoğraf yok. Her sahne için anlatılanı en iyi gösteren kalıbı seç ve parametrelerini doldur:
- "nesne": bir nesne + en fazla 3 kısa etiket. p: {{"ikon": "...", "baslik": "isteğe bağlı 2-4 kelime", "etiketler": ["2-5 kelime", ...]}}
- "sayi": sahnede SÖYLENEN tek çarpıcı sayı. p: {{"deger": 32, "birim": "milyar dolar", "etiket": "kısa açıklama", "ikon": "..."}}
- "karsilastirma": sahnede SÖYLENEN iki değer. p: {{"baslik": "...", "sol": {{"etiket": "Dünya", "deger": 1, "ikon": "dunya"}}, "sag": {{"etiket": "Venüs", "deger": 92, "ikon": "gezegen"}}, "birim": "bar"}}
- "zaman": 2-5 tarihli olay. p: {{"baslik": "...", "olaylar": [{{"yil": 1975, "metin": "3-6 kelime"}}]}}
- "rota": bir yerden bir yere yolculuk/transfer. p: {{"nereden": "Londra", "nereye": "Honduras", "arac": "{'|'.join(ARACLAR)}", "baslik": "..."}}
- "grafik": metinde geçen en az 3 değerin değişimi. p: {{"baslik": "...", "degerler": [22, 15, 3], "etiketler": ["Ekim", "Kasım", "Aralık"], "birim": "$"}}
- "liste": 2-4 madde (adımlar, nedenler, işaretler). p: {{"baslik": "...", "maddeler": [{{"metin": "3-8 kelime", "ikon": "..."}}]}}
- "gazete": bir haber/duyuru/manşet anı. p: {{"manset": "4-8 kelime", "tarih": "11 Kasım 2022", "kaynak": "genel ad, gerçek gazete adı YAZMA", "ikon": "..."}}
- "yigin": büyük para/altın/belge/insan miktarı. p: {{"ikon": "banknot|para|altin|belge|insan", "metin": "32 milyar dolar", "etiket": "..."}}
- "gosterge": sıcaklık, basınç, hız, oran gibi bir ölçüm. p: {{"deger": 475, "min": 0, "max": 500, "birim": "°C", "etiket": "...", "isaretler": [{{"deger": 327, "metin": "Kurşun 327°C'de erir"}}]}}
- "kisi": bir kişiyi tanıtırken (yüz çizilmez, siluet). p: {{"isim": "Ad Soyad", "rol": "kısa tanım", "not": "isteğe bağlı", "ikon": "insan|kadin|polis|bilim_insani|asker"}}
- "ortam": bir yerin/atmosferin genel görünüşü. p: {{"ortam": "{'|'.join(ORTAMLAR)}", "ikon": "hareket eden nesne (ör. gemi, ucak)", "baslik": "isteğe bağlı", "etiket": "ör. Londra, 1820'ler"}}
- "soru": izleyiciye gerçek bir soru sorulan sahne. p: {{"soru": "..."}}
- "yuzde": bir oran/yüzde. p: {{"yuzde": 70, "etiket": "..."}}
- "akis": bir sürecin/paranın adım adım akışı (2-4 adım). p: {{"baslik": "...", "adimlar": ["...", "..."], "ikonlar": ["cuzdan", "bina", "ates"]}}
- "baslik": bölüm geçişi veya güçlü tek cümle. p: {{"baslik": "2-5 kelime", "alt": "isteğe bağlı", "ikon": "..."}}
KULLANILABİLEN İKONLAR (sadece bunlar): {", ".join(ICONS)}
KURALLAR: Ekrandaki her sayı, tarih ve isim O SAHNENİN METNİNDE geçmeli; metinde olmayan bilgi UYDURMA.
Ardışık sahnelerde aynı kalıbı üst üste kullanma; videoda kalıpları çeşitlendir (en çok nesne, kisi, ortam, sayi,
zaman, liste, akis). Ekran yazıları kısa olsun (etiketler 2-6 kelime). Yazılar Türkçe."""

SCENE_JSON = '{"text": "...", "kalip": "nesne", "p": {"ikon": "...", "etiketler": ["..."]}}'


def _digits(v) -> str:
    try:
        f = float(str(v).replace(",", "."))
        return str(int(f)) if f == int(f) else str(f).replace(".", ",")
    except Exception:
        return ""


def _said(v, text: str) -> bool:
    """Sayı sahnenin metninde geçiyor mu? (1.500 / 1500 / 1,5 biçimleri)"""
    d = _digits(v)
    if not d:
        return False
    flat = text.replace(".", "").replace(" ", "")
    return d in flat or d.replace(",", ".") in text


KEYWORDS = [  # metne göre ikon tahmini (yedek)
    (r"dolar|lira|para|servet|milyon|milyar|euro|sterlin", "banknot"), (r"altın", "altin"), (r"kripto|bitcoin|token|coin", "kripto"),
    (r"banka", "banka"), (r"borsa|hisse|çök|iflas", "grafik_dusus"), (r"uçak|uçuş|pilot", "ucak"), (r"gemi|deniz|liman", "gemi"),
    (r"denizaltı", "denizalti"), (r"roket|fırlat", "roket"), (r"uzay|yörünge|uydu", "uydu"), (r"gezegen|venüs|mars|jüpiter", "gezegen"),
    (r"dünya", "dunya"), (r"güneş", "gunes"), (r"kara delik", "kara_delik"), (r"yıldız|galaksi", "yildiz"), (r"ay\b", "ay"),
    (r"mahkeme|dava|yargı|hakim", "terazi"), (r"hapis|cezaevi|tutuklan", "hapishane"), (r"polis|gözaltı", "polis"),
    (r"yakalan|kelepçe", "kelepce"), (r"beyin|zihin|hafıza", "beyin"), (r"kalp", "kalp"), (r"dna|gen", "dna"), (r"virüs|salgın", "virus"),
    (r"hücre", "hucre"), (r"ilaç|tedavi", "ilac"), (r"bilim|deney|laboratuvar", "mikroskop"), (r"sıcak|derece", "termometre"),
    (r"ateş|yangın|yan", "ates"), (r"su\b|okyanus|dalga", "dalga"), (r"dağ", "dag"), (r"buz|kar\b", "buz"), (r"orman|ağaç", "agac"),
    (r"bilgisayar|internet|site", "bilgisayar"), (r"telefon|mesaj", "telefon"), (r"sunucu|veri", "sunucu"), (r"kamera|fotoğraf", "kamera"),
    (r"saat|dakika|zaman", "saat"), (r"takvim|gün\b", "takvim"), (r"mektup", "mektup"), (r"gazete|haber", "gazete"), (r"kitap", "kitap"),
    (r"harita|ülke|toprak", "harita"), (r"belge|sözleşme|evrak|senet", "belge"), (r"kral|prens|taç", "tac"), (r"elmas", "elmas"),
    (r"petrol", "petrol"), (r"fabrika", "fabrika"), (r"şirket|ofis", "bina"), (r"ev\b|konut", "ev"), (r"saray", "saray"),
    (r"kalabalık|halk|yatırımcı|insanlar", "kalabalik"), (r"asker|savaş", "asker"), (r"kilit|şifre|gizli", "kilit"),
    (r"anahtar", "anahtar"), (r"soru|neden|nasıl", "soru"), (r"tehlike|dikkat", "unlem"), (r"ölüm|öldü|ceset", "kafatasi"),
]


def guess_icon(text: str) -> str:
    t = text.lower()
    for pat, ic in KEYWORDS:
        if re.search(pat, t):
            return ic
    return "belge"


def _ic(v, text):
    return v if v in ICONS else guess_icon(text)


def _short(s, n=60):
    s = str(s or "").strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0]


def normalize(scene: dict, prev: str = None) -> tuple:
    """(kalip, p) döndürür; eksik/yanlış/uydurma riskli parametreleri güvenli hale getirir.
    "dogrula": Short sahnelerinde parametreler uzun videodaki kaynak sahnenin metniyle denetlenir."""
    import copy
    text = scene.get("dogrula") or scene.get("text", "")
    scene = copy.deepcopy(scene)
    k = scene.get("kalip") if scene.get("kalip") in KALIPLAR else None
    p = scene.get("p") if isinstance(scene.get("p"), dict) else {}
    fallback = ("nesne", {"ikon": guess_icon(text)})
    try:
        if k is None:
            return fallback
        if k in ("nesne", "baslik"):
            p["ikon"] = _ic(p.get("ikon"), text) if (k == "nesne" or p.get("ikon")) else None
            p["etiketler"] = [_short(e, 40) for e in (p.get("etiketler") or []) if e][:3]
            if k == "baslik" and not p.get("baslik"):
                return fallback
        elif k == "sayi":
            if not _said(p.get("deger"), text):
                return "nesne", {"ikon": _ic(p.get("ikon"), text), "etiketler": [_short(p.get("etiket"), 40)] if p.get("etiket") else []}
            p["ikon"] = _ic(p.get("ikon"), text)
        elif k == "karsilastirma":
            a, b = p.get("sol") or {}, p.get("sag") or {}
            if not (_said(a.get("deger"), text) and _said(b.get("deger"), text)):
                return fallback
            for c in (a, b):
                if c.get("ikon") and c["ikon"] not in ICONS:
                    c.pop("ikon")
        elif k == "zaman":
            ev = [e for e in (p.get("olaylar") or []) if isinstance(e, dict) and str(e.get("yil", "")) and str(e.get("yil")) in text][:5]
            if len(ev) < 2:
                return fallback
            p["olaylar"] = [{"yil": e["yil"], "metin": _short(e.get("metin"), 50)} for e in ev]
        elif k == "rota":
            if not (p.get("nereden") and p.get("nereye")):
                return fallback
            p["arac"] = p.get("arac") if p.get("arac") in ARACLAR else "ucak"
        elif k == "grafik":
            vals = [v for v in (p.get("degerler") or []) if _digits(v)]
            if len(vals) < 3 or sum(_said(v, text) for v in vals) < 2:
                down = re.search(r"düş|çök|eri|kayb|azal", text.lower())
                return "nesne", {"ikon": "grafik_dusus" if down else "grafik_artis", "baslik": _short(p.get("baslik"), 30)}
        elif k == "liste":
            items = [m if isinstance(m, dict) else {"metin": str(m)} for m in (p.get("maddeler") or [])][:4]
            items = [{"metin": _short(m.get("metin"), 60), **({"ikon": m["ikon"]} if m.get("ikon") in ICONS else {})} for m in items if m.get("metin")]
            if len(items) < 2:
                return fallback
            p["maddeler"] = items
        elif k == "gazete":
            if not p.get("manset"):
                return fallback
            if p.get("tarih") and not any(x in text for x in re.findall(r"\d{4}", str(p["tarih"]))):
                p["tarih"] = ""   # metinde olmayan tarih gösterilmez
            p["ikon"] = _ic(p.get("ikon"), text)
        elif k == "yigin":
            p["ikon"] = p.get("ikon") if p.get("ikon") in ("banknot", "para", "altin", "belge", "insan") else "banknot"
            if p.get("metin") and re.search(r"\d", str(p["metin"])) and not any(_said(n, text) for n in re.findall(r"\d+(?:[.,]\d+)?", str(p["metin"]))):
                p["metin"] = ""
        elif k == "gosterge":
            if not _said(p.get("deger"), text):
                return fallback
            p["isaretler"] = [m for m in (p.get("isaretler") or []) if isinstance(m, dict) and _said(m.get("deger"), text)][:3]
        elif k == "kisi":
            if not p.get("isim") or p["isim"].split()[0] not in text:
                p["isim"] = ""
                if not p.get("rol"):
                    return fallback
            p["ikon"] = p.get("ikon") if p.get("ikon") in ("insan", "kadin", "polis", "bilim_insani", "asker") else "insan"
        elif k == "ortam":
            p["ortam"] = p.get("ortam") if p.get("ortam") in ORTAMLAR else "sehir"
            if p.get("ikon") and p["ikon"] not in ICONS:
                p.pop("ikon")
        elif k == "soru":
            if not p.get("soru"):
                p["soru"] = _short(text, 90)
        elif k == "yuzde":
            if not _said(p.get("yuzde"), text):
                return fallback
        elif k == "akis":
            st = [_short(s, 50) for s in (p.get("adimlar") or []) if s][:4]
            if len(st) < 2:
                return fallback
            p["adimlar"] = st
            p["ikonlar"] = [i if i in ICONS else None for i in (p.get("ikonlar") or [])][:4]
        if k == prev and k not in ("nesne",):   # aynı kalıp üst üste gelmesin
            return fallback
        return k, p
    except Exception:
        return fallback


# ------------------------------------------------------------------ plan ve bölüm üretimi
def build_plan(scenes: list, durs: list, w: int, h: int, cfg: dict, seri: str = None, ust: str = None) -> dict:
    sub_words = cfg["video"].get("subtitle_words", 7)
    plan = {"w": w, "h": h, "seri": seri, "ust_baslik": ust, "sahneler": [], "altyazi": []}
    t, prev_k, prev_sec = 0.0, None, None
    pad = float(cfg["video"].get("scene_padding", 0.2))
    for i, (sc, d) in enumerate(zip(scenes, durs)):
        k, p = normalize(sc, prev_k)
        gecis = "yaprak" if (i > 0 and sc.get("section") != prev_sec) else "kaydir"
        plan["sahneler"].append({"kalip": k, "p": p, "sure": d, "bas": t, "gecis": gecis})
        # altyazı: konuşma süresine (pad hariç) harf oranıyla dağıtılır
        speak = max(0.5, d - pad)
        parts = _chunks(sc.get("text", ""), sub_words)
        total = sum(len(x) for x in parts) or 1
        a = t
        for x in parts:
            b = a + speak * len(x) / total
            plan["altyazi"].append({"a": round(a, 3), "b": round(b, 3), "metin": x})
            a = b
        t += d
        prev_k, prev_sec = k, sc.get("section")
    plan["sure"] = t
    return plan


KREM = "0xF3EBDD"   # kâğıt zemin rengi (motor/kagit.js > P.cream)


def segment(scenes: list, audios: list, work: Path, name: str, cfg: dict, w: int = 1920, h: int = 1080,
            seri: str = None, ust: str = None, pad: float = None, fade_in: float = 0,
            fade_out: float = 0) -> Path:
    """Sahneleri motorla çizer, sahne seslerini (aralarında boşlukla) ekler → sesli MP4.
    fade_in/fade_out: başta/sonda krem kâğıt rengine yumuşak geçiş (jenerik ve bitiş ekranı öncesi/sonrası)."""
    work.mkdir(parents=True, exist_ok=True)
    pad = float(cfg["video"].get("scene_padding", 0.2)) if pad is None else pad
    durs = [media_duration(a) + pad for a in audios]
    plan = build_plan(scenes, durs, w, h, cfg, seri, ust)
    import json
    (work / f"{name}_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    silent = kagit_motor.render(plan, work / f"{name}_sessiz.mp4", fps=int(cfg["video"].get("fps", 30)))
    # ses: her sahne kendi süresine tamamlanıp art arda eklenir
    inputs, flt = [], []
    for i, (a, d) in enumerate(zip(audios, durs)):
        inputs += ["-i", str(a)]
        flt.append(f"[{i + 1}:a]aresample=44100,aformat=channel_layouts=stereo,apad=whole_dur={d:.3f},atrim=0:{d:.3f}[a{i}]")
    af = ""
    if fade_out:
        af = f",afade=t=out:st={plan['sure'] - min(fade_out, 0.3):.3f}:d={min(fade_out, 0.3):.3f}"
    flt.append("".join(f"[a{i}]" for i in range(len(audios))) + f"concat=n={len(audios)}:v=0:a=1{af}[aud]")
    vf = []
    if fade_in:
        vf.append(f"fade=t=in:st=0:d={fade_in:.2f}:color={KREM}")
    if fade_out:
        vf.append(f"fade=t=out:st={plan['sure'] - fade_out:.3f}:d={fade_out:.2f}:color={KREM}")
    flt.append(f"[0:v]{','.join(vf) or 'null'},format=yuv420p[vid]")
    out = work / f"{name}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), *inputs, "-filter_complex", ";".join(flt),
         "-map", "[vid]", "-map", "[aud]", *ENCODE, "-t", f"{plan['sure']:.3f}", str(out)])
    silent.unlink(missing_ok=True)
    return out


def kapak_bg(scenes: list, out: Path, w: int = 1920, h: int = 1080, skip: int = 0) -> Path:
    """Kapak arka planı: videonun en belirgin nesnesi sağda büyük (sol tarafa kapak yazısı gelir)."""
    from collections import Counter
    icons = []
    prev = None
    for sc in scenes:
        k, p = normalize(sc, prev)
        prev = k
        for key in ("ikon",):
            if p.get(key) in ICONS and p[key] not in ("soru", "unlem", "tik", "carpi", "ok_yukari", "ok_asagi"):
                icons.append(p[key])
        if k == "kisi":
            icons.append(p.get("ikon") or "insan")
    ranked = [i for i, _ in Counter(icons).most_common()] or [guess_icon(" ".join(s.get("text", "") for s in scenes[:5]))]
    main = ranked[min(skip, len(ranked) - 1)]
    second = next((i for i in ranked if i != main), None)
    plan = {"w": w, "h": h, "sahneler": [{"kalip": "kapak", "p": {"ikon": main, "ikon2": second}, "sure": 6, "bas": 0}],
            "altyazi": [], "sure": 6}
    return kagit_motor.still(plan, out, 0, 1.0)


def assemble(script: dict, audios: list, work: Path, final: Path, cfg: dict, intro: Path = None,
             outro: Path = None) -> Path:
    """Uzun video: soğuk açılış → jenerik → ana bölüm → kapanış. Görüntüler kâğıt motorundan."""
    import json
    from .editor import concat
    work.mkdir(parents=True, exist_ok=True)
    scenes = script["scenes"]
    cold = [(s, a) for s, a in zip(scenes, audios) if s.get("cold")]
    main = [(s, a) for s, a in zip(scenes, audios) if not s.get("cold")]
    seri = None
    if script.get("series"):
        seri = f"{script['series']['name']} · {script['series'].get('episode')}"
    clips, mute, t = [], [], 0.0
    if cold:
        log(f"  Soğuk açılış çiziliyor ({len(cold)} sahne)...")
        # kanca bitince görüntü krem zemine yumuşakça söner, jenerik oradan açılır
        a = segment([s for s, _ in cold], [x for _, x in cold], work, "bolum_a", cfg,
                    fade_out=0.45 if intro is not None else 0)
        clips.append(a); t += media_duration(a)
    if intro is not None:
        d = media_duration(intro)
        mute.append((t, t + d)); clips.append(intro); t += d
    log(f"  Ana bölüm çiziliyor ({len(main)} sahne)...")
    clips.append(segment([s for s, _ in main], [x for _, x in main], work, "bolum_b", cfg, seri=seri,
                         fade_in=0.35 if intro is not None else 0, fade_out=0.5 if outro is not None else 0))
    if outro is not None:
        clips.append(outro)
    used = concat(clips, work, final, cfg, mute)
    (final.parent / "muzik.json").write_text(json.dumps(used, ensure_ascii=False), encoding="utf-8")
    log(f"Video hazır: {final} ({media_duration(final) / 60:.1f} dk)")
    return final
