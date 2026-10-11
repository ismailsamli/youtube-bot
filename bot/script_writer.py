"""Konu seçimi, senaryo yazımı ve doğruluk kontrolü (Gemini ücretsiz katman veya Claude API)."""
import json
import random
import re
import time

from .utils import env, log

WORDS_PER_MINUTE = 135  # Türkçe yapay zeka sesi için yaklaşık konuşma hızı
SECONDS_PER_SCENE = 12


class LLM:
    """config.yaml'daki llm.provider'a göre Gemini (ücretsiz) veya Claude kullanır."""

    def __init__(self, cfg: dict):
        self.provider = cfg["llm"].get("provider", "gemini")
        if self.provider == "claude":
            import anthropic
            self.client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))
            self.model = cfg["llm"].get("claude_model", "claude-sonnet-5-5")
        else:
            from google import genai
            from google.genai import types as gtypes
            # 5 dakikada cevap gelmezse isteği kesip yeniden dener
            self.client = genai.Client(api_key=env("GEMINI_API_KEY"),
                                       http_options=gtypes.HttpOptions(timeout=300_000))
            first = cfg["llm"].get("gemini_model", "gemini-3.8-flash")
            # Google eski modelleri kapatırsa sıradakini dener
            # Model kapanırsa veya günlük ücretsiz kotası dolarsa sıradakine geçilir
            # (her modelin ücretsiz kotası ayrıdır)
            fallbacks = cfg["llm"].get("gemini_fallbacks") or [
                "gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]
            self.candidates = [m for m in dict.fromkeys([first, *fallbacks]) if m]
            self.model = self.candidates[0]
            self._last_call = 0.0

    def ask(self, system: str, prompt: str, max_tokens: int = 16000) -> str:
        if self.provider == "claude":
            with self.client.messages.stream(
                model=self.model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                msg = stream.get_final_message()
            return "".join(b.text for b in msg.content if b.type == "text")

        from google.genai import types
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max(max_tokens * 3, 16384),
            response_mime_type="application/json",
            temperature=0.8,
        )
        for attempt in range(8):
            # Dakikalık ücretsiz sınıra takılmamak için istekler arasında en az 13 sn
            gap = time.time() - self._last_call
            if gap < 13:
                time.sleep(13 - gap)
            self._last_call = time.time()
            try:
                t0 = time.time()
                # Akış halinde alınır: uzun cevaplarda bağlantı boşta kalıp kopmaz
                parts = []
                for chunk in self.client.models.generate_content_stream(
                        model=self.model, contents=prompt, config=config):
                    if chunk.text:
                        parts.append(chunk.text)
                text = "".join(parts)
                if text:
                    log(f"  Gemini cevabı {time.time() - t0:.0f} sn sürdü")
                    return text
                raise RuntimeError("Gemini boş cevap döndürdü.")
            except Exception as e:
                msg = str(e)
                gone = "404" in msg or "NOT_FOUND" in msg
                daily = "PerDay" in msg or "per day" in msg.lower()
                if gone or daily:
                    if len(self.candidates) > 1:
                        old = self.candidates.pop(0)
                        self.model = self.candidates[0]
                        why = "günlük ücretsiz kotası doldu" if daily else "kullanılamıyor"
                        log(f"  {old} modelinin {why}, {self.model} modeline geçiliyor.")
                        continue
                    if daily:
                        raise RuntimeError("Tüm Gemini modellerinin günlük ücretsiz kotası doldu; "
                                           "kota Türkiye saatiyle gece ~03:00'te sıfırlanır.") from e
                transient = ("429", "RESOURCE_EXHAUSTED", "500", "502", "503", "504", "INTERNAL",
                             "UNAVAILABLE", "DEADLINE", "boş cevap", "disconnected", "Disconnected",
                             "timed out", "Timeout", "timeout", "Connection", "RemoteProtocolError",
                             "ReadError")
                busy = any(k in msg or k in type(e).__name__ for k in transient)
                if not busy or attempt == 7:
                    raise
                wait = 65 if "429" in msg or "RESOURCE_EXHAUSTED" in msg else 20
                log(f"  Gemini geçici hata ({type(e).__name__}), {wait} sn sonra yeniden deneniyor...")
                time.sleep(wait)


def _parse_json(text: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Yapay zekadan JSON alınamadı.")
    chunk = text[start:end + 1]
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        # Kaçırılmamış tırnak, eksik virgül gibi küçük bozuklukları onar
        from json_repair import repair_json
        data = repair_json(chunk, return_objects=True)
        if not isinstance(data, dict) or not data:
            raise ValueError("Yapay zekanın JSON cevabı onarılamadı.")
        log("  Bozuk JSON cevabı onarıldı.")
        return data


def _ask_json(llm, system: str, prompt: str, max_tokens: int, required: str, tries: int = 3) -> dict:
    """JSON ister; bozuk/eksik gelirse aynı isteği yeniden dener."""
    last = None
    for i in range(tries):
        try:
            data = _parse_json(llm.ask(system, prompt, max_tokens))
            if data.get(required):
                return data
            last = ValueError(f"Cevapta '{required}' alanı yok.")
        except ValueError as e:
            last = e
        log(f"  Geçersiz cevap ({last}), yeniden isteniyor ({i + 2}/{tries})...")
    raise last


def _system(cfg: dict) -> str:
    ch = cfg["channel"]
    return (
        "Sen Türkçe bir YouTube bilgi kanalının baş senaristi ve editörüsün.\n"
        f"Kanal konusu: {ch['niche']}\nHedef kitle: {ch['audience']}\nÜslup: {ch['tone']}\n\n"
        "Temel kuralların:\n"
        "- Sadece iyi bilinen, güvenilir kaynaklarla doğrulanabilir bilgiler kullan. "
        "Emin olmadığın sayı, tarih veya iddiayı yazma; uydurma alıntı ve istatistik kullanma.\n"
        "- Tartışmalı ya da kanıtlanmamış konuları 'kesin' gibi sunma; 'bazı tarihçilere göre', "
        "'bir teoriye göre' gibi ifadelerle belirt.\n"
        "- Sağlık, finans ve hukuk konusunda tavsiye verme.\n"
        "- Clickbait yalan söyleme: başlık ve kapak, videoda gerçekten anlatılanı vaat etmeli.\n"
        "- Doğal, akıcı, konuşma dilinde Türkçe yaz; yapay zeka gibi kalıp cümleler kurma.\n"
        "- Her zaman sadece istenen JSON'u döndür."
    )


def pick_topic(llm, cfg: dict, past_titles: list) -> dict:
    pool = cfg["channel"].get("topic_pool") or []
    focus = random.choice(pool) if pool else "serbest"
    past = "\n".join(f"- {t}" for t in past_titles[-150:]) or "(henüz video yok)"
    prompt = (
        f"Kanal için yeni bir video konusu seç. Bu seferki alan: {focus}.\n\n"
        f"Daha önce yapılan videolar (bunları ve çok benzerlerini TEKRARLAMA):\n{past}\n\n"
        "Konu şu özelliklerde olmalı:\n"
        "- Türk izleyicinin YouTube'da arayabileceği, merak uyandıran, zamansız (evergreen) bir konu\n"
        "- 8-10 dakikada derinlemesine anlatılacak kadar zengin\n"
        "- Görsel olarak anlatılabilir (stok video ve çizimlerle desteklenebilir)\n"
        "- Gerçek ve doğrulanabilir bilgilere dayanan\n\n"
        'JSON döndür: {"topic": "konu", "angle": "videonun özgün bakış açısı / ana sorusu", '
        '"search_terms": ["insanların arayabileceği 3-5 Türkçe arama ifadesi"]}'
    )
    data = _parse_json(llm.ask(_system(cfg), prompt, 2000))
    log(f"Konu seçildi: {data['topic']}")
    return data


SECTIONS = 6


def _visual_rules(ai_ratio: float) -> str:
    return """GÖRSELLER (her sahne için):
- "query": Wikimedia Commons'ta aranacak 2-5 kelimelik İNGİLİZCE arama. Sahnede anlatılan şeyin GERÇEK
  fotoğrafını, haritasını, tarihi görselini ya da çizimini bulduracak şekilde yaz; mümkünse özel isim kullan
  (ör. "Voyager 1 spacecraft", "Golden Record cover", "Topkapi Palace", "common raven", "Mars surface").
  Soyut ifadeler ("success", "mystery", "time") YAZMA; somut bir nesne, yer, kişi veya olay yaz.
  Ardışık sahnelerde aynı aramayı tekrarlama; konuyu farklı açılardan gösteren çeşitli aramalar kullan.
  Görsel, sahnede söylenen şeyi DOĞRUDAN göstermeli. Konuyla ilgisiz genel sokak, kalabalık, düğün,
  otopark gibi aramalar YAZMA; soyut bir cümlede bile konuyla ilgili somut bir nesne seç
  (ör. zaman algısı için "hourglass", "human brain MRI", "pocket watch").
- "prompt": sahneyi anlatan kısa İNGİLİZCE görsel tarifi (yedek olarak kullanılır).
- "visual": "stock"."""


def write_outline(llm, cfg: dict, topic: dict = None, past_titles: list = None) -> dict:
    if topic:
        intro = (f"KONU: {topic['topic']}\nBAKIŞ AÇISI: {topic.get('angle', '')}\n"
                 f"ARAMA İFADELERİ: {', '.join(topic.get('search_terms', []))}")
    else:
        pool = cfg["channel"].get("topic_pool") or []
        focus = random.choice(pool) if pool else "serbest"
        past = "\n".join(f"- {t}" for t in (past_titles or [])[-150:]) or "(henüz video yok)"
        intro = (f"Önce kanal için YENİ ve VİRAL potansiyeli yüksek bir konu seç. Bu seferki alan: {focus}.\n"
                 f"Daha önce yapılan videolar (bunları ve çok benzerlerini TEKRARLAMA):\n{past}\n"
                 "Konu seçimi için önce aklında 5 aday konu düşün ve her birini şu ölçütlere göre puanla, "
                 "en yüksek puanlıyı seç:\n"
                 "- Merak boşluğu: başlığı okuyan 'bunu bilmiyordum, hemen öğrenmeliyim' demeli.\n"
                 "- Şaşırtıcılık: sezgilere ters düşen, 'gerçekten mi?' dedirten bir gerçek ya da soru.\n"
                 "- Geniş kitle: herkesin günlük hayatına, korkularına, merakına dokunan konular "
                 "(insan vücudu, felaketler, rekorlar, 'ya olsaydı' senaryoları, tarihin karanlık sırları, "
                 "uzayın korkutucu gerçekleri, gizemler, olağanüstü hayatta kalma hikâyeleri).\n"
                 "- Türk izleyicinin ilgisi: mümkünse Türkiye/Osmanlı/Anadolu bağlantısı veya Türkiye'de çok "
                 "konuşulan konular.\n"
                 "- Gerçeklik: konu tamamen gerçek ve doğrulanabilir bilgilere dayanmalı; uydurma yok.\n"
                 "Sıkıcı ansiklopedik konular yerine bir soru, sır, tehlike veya rekor etrafında kurulmuş, "
                 "8-10 dakikada anlatılabilecek bir konu seç.\n"
                 'JSON\'a ayrıca "topic" (konu) ve "angle" (videonun özgün, merak uyandıran bakış açısı) alanlarını ekle.')
    prompt = f"""{cfg['video']['target_minutes']} dakikalık bir YouTube videosunun PLANINI çıkar.

{intro}

Video tam olarak {SECTIONS} bölümden oluşacak:
- 1. bölüm: ilk 10 saniyede izleyiciyi yakalayan çok güçlü bir kanca (en şaşırtıcı bilgi, çarpıcı bir
  soru ya da gerilimli bir sahne) ve videonun sonunda neyin açıklanacağına dair net bir vaat.
- Ortadaki bölümler: konuyu mantıklı sırayla anlat; her bölüm yeni bir merak noktası açsın ve
  en çarpıcı bilgiyi videonun ortasına ve sonuna sakla ki izleyici sonuna kadar izlesin.
- Son bölüm: konuyu bağla, kısa kapanış ve doğal bir abone olma çağrısı.

Her bölüm için "heading" (kısa başlık), "goal" (bölümün amacı, 1 cümle) ve
"facts" (bölümde anlatılacak 3-5 doğrulanabilir somut bilgi) yaz.

PAKETLEME:
- "title": en fazla 65 karakter; tıklamak istetecek, merak boşluğu bırakan ama DÜRÜST Türkçe başlık.
  Etkili kalıplar: soru ("... Neden ...?"), şaşırtıcı iddia ("... Aslında ..."), rakam/rekor, "ya olsaydı"
  senaryosu. Büyük harfle tek bir vurgu kelimesi kullanabilirsin. Videoda olmayan bir şeyi vaat etme.
- "description": 3 kısa paragraf Türkçe açıklama (ilk 2 satır aramada görünecek şekilde güçlü), ardından 3-5 hashtag
- "tags": 10-15 Türkçe etiket
- "thumbnail_text": kapakta yazacak 2-3 kelimelik, başlığı tekrar ETMEYEN, duygusu güçlü çarpıcı
  Türkçe ifade (ör. "KİMSE BİLMİYOR", "5 DAKİKA KALDI")
- "search_en": videonun genel konusunu anlatan 2-3 kelimelik İNGİLİZCE görsel arama ifadesi
  (ör. "human brain", "Titanic wreck", "black hole"); sahne görseli bulunamazsa bununla aranır
- "thumbnail_prompt": kapak arka planı için İNGİLİZCE görsel tarifi; tek, net, dramatik bir odak nesnesi;
  sol tarafta yazı için sade alan; yazı içermeyen

Sadece şu JSON'u döndür:
{{"title": "...", "description": "...", "tags": ["..."], "thumbnail_text": "...", "search_en": "...", "thumbnail_prompt": "...",
  "sections": [{{"heading": "...", "goal": "...", "facts": ["..."]}}]}}"""
    log("Video planı yazılıyor...")
    return _ask_json(llm, _system(cfg), prompt, 4000, "sections")


def write_section(llm, cfg: dict, outline: dict, idx: int, scene_count: int,
                  words_per_scene: int, previous_text: str) -> list:
    sections = outline["sections"]
    sec = sections[idx]
    plan = "\n".join(f"{i + 1}. {s.get('heading', '')}: {s.get('goal', '')}" for i, s in enumerate(sections))
    position = ("Bu videonun İLK bölümü: ilk cümle doğrudan en şaşırtıcı bilgi veya çarpıcı bir soru olsun; "
                "'merhaba arkadaşlar', 'bu videoda' gibi boş girişler kullanma; ikinci sahnede videonun "
                "sonunda neyin açıklanacağını vaat et ve izleyiciyi sonuna kadar kalmaya teşvik et."
                if idx == 0 else
                "Bu videonun SON bölümü: konuyu bağla, son sahnede kısa bir kapanış ve doğal bir "
                "'ilginç bulduysan abone olmayı unutma' çağrısı yap."
                if idx == len(sections) - 1 else
                "Bu bir ara bölüm: bir önceki bölümden doğal bir geçişle başla, selamlama veya kapanış yapma. "
                "Bölümün son sahnesi bir sonraki bölüme merak bırakan kısa bir köprü cümlesiyle bitsin.")
    prompt = f"""Video başlığı: {outline.get('title', '')}

Videonun bölüm planı:
{plan}

Şimdi SADECE {idx + 1}. bölümü yaz: "{sec.get('heading', '')}"
Amaç: {sec.get('goal', '')}
Anlatılacak bilgiler: {'; '.join(sec.get('facts', []))}
{position}

Bir önceki bölümün son cümleleri (devamlılık için, tekrar etme): {previous_text[-400:] or '(yok)'}

UZUNLUK: tam olarak {scene_count} sahne, her sahnede {words_per_scene - 5}-{words_per_scene + 5} kelime
seslendirme metni. Metinler sesli okunacak: kısaltma, parantez, emoji, madde işareti kullanma.
DOĞRULUK: Sadece iyi bilinen, güvenilir kaynaklarla doğrulanabilir bilgiler kullan. Emin olmadığın
sayı, tarih, isim veya alıntıyı YAZMA; tartışmalı bilgileri "bir görüşe göre" diye belirt. Yazdıktan sonra
her cümleyi bir bilgi editörü gibi kontrol et ve şüpheli olanı düzelt.

{_visual_rules(cfg['video'].get('ai_image_ratio', 0.35))}

Sadece şu JSON'u döndür:
{{"scenes": [{{"text": "...", "visual": "stock", "query": "...", "prompt": "..."}}]}}"""
    data = _ask_json(llm, _system(cfg), prompt, 6000, "scenes")
    return data.get("scenes", [])


def write_script(llm, cfg: dict, topic: dict) -> dict:
    minutes = cfg["video"]["target_minutes"]
    total_words = int(minutes * WORDS_PER_MINUTE)
    total_scenes = max(20, round(minutes * 60 / SECONDS_PER_SCENE))
    words_per_scene = round(total_words / total_scenes)

    outline = write_outline(llm, cfg, topic if topic.get("topic") else None,
                            topic.get("past_titles"))
    sections = outline["sections"]
    per = max(3, round(total_scenes / len(sections)))
    scenes, previous = [], ""
    for i in range(len(sections)):
        log(f"Bölüm {i + 1}/{len(sections)} yazılıyor: {sections[i].get('heading', '')}")
        part = write_section(llm, cfg, outline, i, per, words_per_scene, previous)
        scenes.extend(part)
        previous = " ".join(s.get("text", "") for s in part[-2:])
    script = {k: outline.get(k) for k in ("title", "description", "tags", "thumbnail_text",
                                           "thumbnail_prompt")}
    script["scenes"] = scenes
    script["sections"] = [s.get("heading", "") for s in sections]
    script["topic"] = {"topic": outline.get("topic") or topic.get("topic"),
                       "angle": outline.get("angle") or topic.get("angle", ""),
                       "search_en": outline.get("search_en") or ""}
    return validate(script)


def fact_check(llm, cfg: dict, script: dict) -> dict:
    """Senaryoyu bölüm bölüm kontrol eder (büyük tek istek zaman aşımına düşmesin diye)."""
    log("Doğruluk kontrolü yapılıyor...")
    scenes = script["scenes"]
    chunk = 8
    checked_scenes = []
    for start in range(0, len(scenes), chunk):
        part = scenes[start:start + chunk]
        prompt = (
            f"Video başlığı: {script['title']}\n\n"
            "Aşağıdaki sahneleri titiz bir bilgi editörü olarak kontrol et.\n"
            "- Yanlış, şüpheli, abartılı veya doğrulanamayan iddiaları düzelt ya da yumuşat.\n"
            "- Uydurma sayı, tarih, alıntı varsa çıkar veya doğrusuyla değiştir.\n"
            "- Sahne sayısını, her sahnenin uzunluğunu ve tüm alanları AYNEN koru.\n"
            "- Değişiklikleri kısa maddeler olarak \"notes\" listesine yaz.\n\n"
            'Sadece şu JSON\'u döndür: {"scenes": [...], "notes": ["..."]}\n\n'
            + json.dumps({"scenes": part}, ensure_ascii=False)
        )
        try:
            data = _parse_json(llm.ask(_system(cfg), prompt, 6000))
            fixed = data.get("scenes") or []
            if len(fixed) != len(part):
                fixed = part
            for note in (data.get("notes") or [])[:5]:
                log(f"  düzeltme: {note}")
        except Exception as e:
            log(f"  {start + 1}-{start + len(part)}. sahneler kontrol edilemedi, olduğu gibi bırakıldı: {e}")
            fixed = part
        checked_scenes.extend(fixed)
    script["scenes"] = checked_scenes
    return validate(script)


def validate(script: dict) -> dict:
    for key in ("title", "description", "scenes"):
        if key not in script:
            raise ValueError(f"Senaryoda '{key}' alanı eksik.")
    clean = []
    for s in script["scenes"]:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        visual = s.get("visual") if s.get("visual") in ("stock", "ai") else "stock"
        clean.append({
            "text": text,
            "visual": visual,
            "query": (s.get("query") or "nature landscape").strip(),
            "prompt": (s.get("prompt") or s.get("query") or "cinematic landscape").strip(),
        })
    if len(clean) < 5:
        raise ValueError("Senaryoda yeterli sahne yok.")
    script["scenes"] = clean
    script["title"] = script["title"].strip()[:100]
    script["tags"] = [t.strip() for t in script.get("tags", []) if t.strip()]
    script.setdefault("thumbnail_text", script["title"][:30])
    script.setdefault("thumbnail_prompt", clean[0]["prompt"])
    return script


def generate(cfg: dict, past_titles: list, forced_topic: str = None) -> dict:
    llm = LLM(cfg)
    log(f"Yapay zeka: {llm.provider} ({llm.model})")
    # Konu seçimi plan isteğinin içinde yapılır (ücretsiz kotayı korumak için ayrı istek yok)
    topic = {"topic": forced_topic, "angle": "", "search_terms": []} if forced_topic \
        else {"topic": None, "past_titles": past_titles}
    script = write_script(llm, cfg, topic)
    log(f"Konu: {script['topic']['topic']}")
    if cfg["llm"].get("fact_check", False):
        try:
            script = fact_check(llm, cfg, script)
        except Exception as e:
            log(f"  Doğruluk kontrolü yapılamadı, ilk senaryoyla devam ediliyor: {e}")
    words = sum(len(s["text"].split()) for s in script["scenes"])
    log(f"Senaryo hazır: {len(script['scenes'])} sahne, {words} kelime "
        f"(~{words / WORDS_PER_MINUTE:.1f} dk)")
    return script
