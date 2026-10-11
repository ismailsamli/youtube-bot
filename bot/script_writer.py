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
            self.client = genai.Client(api_key=env("GEMINI_API_KEY"))
            first = cfg["llm"].get("gemini_model", "gemini-3.8-flash")
            # Google eski modelleri kapatırsa sıradakini dener
            self.candidates = [m for m in dict.fromkeys(
                [first, "gemini-3.8-flash", "gemini-flash-latest"]) if m]
            self.model = self.candidates[0]

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
            max_output_tokens=max(max_tokens, 8192) * 2,
            response_mime_type="application/json",
            temperature=0.8,
        )
        for attempt in range(6):
            try:
                resp = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config)
                if resp.text:
                    return resp.text
                raise RuntimeError("Gemini boş cevap döndürdü.")
            except Exception as e:
                msg = str(e)
                if ("404" in msg or "NOT_FOUND" in msg) and len(self.candidates) > 1:
                    old = self.candidates.pop(0)
                    self.model = self.candidates[0]
                    log(f"  {old} modeli kullanılamıyor, {self.model} modeline geçiliyor.")
                    continue
                busy = any(k in msg for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "boş cevap"))
                if not busy or attempt == 5:
                    raise
                wait = 65 if "429" in msg or "RESOURCE_EXHAUSTED" in msg else 15
                log(f"  Gemini ücretsiz limit/yoğunluk, {wait} sn bekleniyor...")
                time.sleep(wait)


def _parse_json(text: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Yapay zekadan JSON alınamadı.")
    return json.loads(text[start:end + 1])


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


def write_script(llm, cfg: dict, topic: dict) -> dict:
    minutes = cfg["video"]["target_minutes"]
    total_words = int(minutes * WORDS_PER_MINUTE)
    scenes = max(20, round(minutes * 60 / SECONDS_PER_SCENE))
    words_per_scene = round(total_words / scenes)
    ai_count = round(scenes * cfg["video"].get("ai_image_ratio", 0.35))

    prompt = f"""Şu konu için eksiksiz bir YouTube video senaryosu yaz.

KONU: {topic['topic']}
BAKIŞ AÇISI: {topic.get('angle', '')}
ARAMA İFADELERİ: {', '.join(topic.get('search_terms', []))}

UZUNLUK: Toplam yaklaşık {total_words} kelime, tam olarak {scenes} sahne,
her sahnede {words_per_scene - 5}-{words_per_scene + 5} kelime seslendirme metni.

YAPI:
- İlk sahne güçlü bir kanca olsun: ilk 10 saniyede izleyiciyi yakalayan şaşırtıcı bir soru ya da bilgi.
  "Merhaba arkadaşlar", "bu videoda" gibi boş girişler kullanma.
- 2. sahnede videoda ne öğrenileceğini tek cümleyle vaat et.
- Ortada bilgiyi mantıklı bir sırayla, her birkaç sahnede bir yeni bir merak noktası açarak anlat.
- Sondan bir önceki sahnede konuyu bağla; son sahnede kısa bir kapanış ve doğal bir
  "ilginç bulduysan abone olmayı unutma" çağrısı yap.
- Metinler sesli okunacak: kısaltma, parantez, emoji, madde işareti kullanma.
  Sayıları okunacağı gibi yazabilirsin (ör. "1453" uygundur).

GÖRSELLER:
- Her sahne için "visual" alanı "stock" ya da "ai" olsun. Yaklaşık {ai_count} sahne "ai", gerisi "stock".
- "stock" sahnelerde "query": Pexels'te aranacak, kameraya çekilebilir somut bir şey anlatan
  2-4 kelimelik İNGİLİZCE arama (ör. "ancient stone ruins", "starry night sky timelapse").
- "ai" sahnelerde "prompt": stok videoda bulunamayacak şeyler için (tarihi sahneler, bilimsel
  çizimler, uzay, temsilî canlandırmalar) detaylı İNGİLİZCE görsel tarifi; sinematik, gerçekçi,
  16:9. Görselde YAZI, logo ve tanınmış gerçek kişilerin yüzü OLMASIN.
- Her sahneye her iki alanı da yaz ("query" ve "prompt"), ama "visual" hangisinin kullanılacağını belirler.

PAKETLEME:
- "title": en fazla 70 karakter, merak uyandıran ama dürüst, arama ifadesini içeren Türkçe başlık
- "description": 3 kısa paragraf Türkçe açıklama (ilk 2 satır aramada görünecek şekilde güçlü),
  ardından 3-5 hashtag
- "tags": 10-15 Türkçe etiket
- "thumbnail_text": kapakta yazacak 2-4 kelimelik, başlığı tekrar ETMEYEN çarpıcı Türkçe ifade
- "thumbnail_prompt": kapak arka planı için İNGİLİZCE görsel tarifi; tek, net, dramatik bir odak
  nesnesi; sol tarafta yazı için sade alan bırakılmış; yazı içermeyen

Sadece şu JSON'u döndür:
{{"title": "...", "description": "...", "tags": ["..."], "thumbnail_text": "...",
  "thumbnail_prompt": "...",
  "scenes": [{{"text": "...", "visual": "stock", "query": "...", "prompt": "..."}}]}}"""

    log("Senaryo yazılıyor...")
    script = _parse_json(llm.ask(_system(cfg), prompt))
    return validate(script)


def fact_check(llm, cfg: dict, script: dict) -> dict:
    log("Doğruluk kontrolü yapılıyor...")
    prompt = (
        "Aşağıdaki YouTube senaryosunu titiz bir bilgi editörü olarak kontrol et.\n"
        "- Yanlış, şüpheli, abartılı veya doğrulanamayan her iddiayı düzelt ya da yumuşat.\n"
        "- Uydurma sayı, tarih, alıntı varsa çıkar veya doğrusuyla değiştir.\n"
        "- Başlık ve kapak yazısı videonun içeriğini dürüstçe yansıtmıyorsa düzelt.\n"
        "- Sahne sayısını, sahne uzunluklarını ve JSON yapısını AYNEN koru.\n"
        "- Yaptığın değişiklikleri kısa maddeler olarak \"fact_check_notes\" listesine yaz.\n\n"
        "Sadece düzeltilmiş tam JSON'u döndür.\n\n"
        + json.dumps(script, ensure_ascii=False)
    )
    checked = _parse_json(llm.ask(_system(cfg), prompt))
    checked = validate(checked)
    for note in checked.get("fact_check_notes", [])[:10]:
        log(f"  düzeltme: {note}")
    return checked


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
    if forced_topic:
        topic = {"topic": forced_topic, "angle": "", "search_terms": []}
    else:
        topic = pick_topic(llm, cfg, past_titles)
    script = write_script(llm, cfg, topic)
    if cfg["llm"].get("fact_check", True):
        script = fact_check(llm, cfg, script)
    script["topic"] = topic
    words = sum(len(s["text"].split()) for s in script["scenes"])
    log(f"Senaryo hazır: {len(script['scenes'])} sahne, {words} kelime "
        f"(~{words / WORDS_PER_MINUTE:.1f} dk)")
    return script
