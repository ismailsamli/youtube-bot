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
            max_output_tokens=max(max_tokens * 3, 16384),
            response_mime_type="application/json",
            temperature=0.8,
        )
        for attempt in range(6):
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
                if ("404" in msg or "NOT_FOUND" in msg) and len(self.candidates) > 1:
                    old = self.candidates.pop(0)
                    self.model = self.candidates[0]
                    log(f"  {old} modeli kullanılamıyor, {self.model} modeline geçiliyor.")
                    continue
                transient = ("429", "RESOURCE_EXHAUSTED", "500", "502", "503", "504", "INTERNAL",
                             "UNAVAILABLE", "DEADLINE", "boş cevap", "disconnected", "Disconnected",
                             "timed out", "Timeout", "timeout", "Connection", "RemoteProtocolError",
                             "ReadError")
                busy = any(k in msg or k in type(e).__name__ for k in transient)
                if not busy or attempt == 5:
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


SECTIONS = 6


def _visual_rules(ai_ratio: float) -> str:
    return f"""GÖRSELLER (her sahne için):
- "visual": "stock" ya da "ai". Sahnelerin yaklaşık %{int(ai_ratio * 100)} kadarı "ai", gerisi "stock".
- "query": Pexels'te aranacak, kameraya çekilebilir somut bir şey anlatan 2-4 kelimelik İNGİLİZCE arama
  (ör. "ancient stone ruins", "starry night sky timelapse").
- "prompt": sahneyi anlatan detaylı İNGİLİZCE görsel tarifi; sinematik, gerçekçi, 16:9.
  Görselde YAZI, logo ve tanınmış gerçek kişilerin yüzü OLMASIN.
- Her sahneye "query" ve "prompt" alanlarının ikisini de yaz."""


def write_outline(llm, cfg: dict, topic: dict) -> dict:
    prompt = f"""Şu konu için {cfg['video']['target_minutes']} dakikalık bir YouTube videosunun PLANINI çıkar.

KONU: {topic['topic']}
BAKIŞ AÇISI: {topic.get('angle', '')}
ARAMA İFADELERİ: {', '.join(topic.get('search_terms', []))}

Video tam olarak {SECTIONS} bölümden oluşacak:
- 1. bölüm: güçlü bir kanca (şaşırtıcı soru/bilgi) ve videoda ne öğrenileceği vaadi.
- Ortadaki bölümler: konuyu mantıklı sırayla, her bölümde yeni bir merak noktası açarak anlat.
- Son bölüm: konuyu bağla, kısa kapanış ve doğal bir abone olma çağrısı.

Her bölüm için "heading" (kısa başlık), "goal" (bölümün amacı, 1 cümle) ve
"facts" (bölümde anlatılacak 3-5 doğrulanabilir somut bilgi) yaz.

PAKETLEME:
- "title": en fazla 70 karakter, merak uyandıran ama dürüst, arama ifadesini içeren Türkçe başlık
- "description": 3 kısa paragraf Türkçe açıklama (ilk 2 satır aramada görünecek şekilde güçlü), ardından 3-5 hashtag
- "tags": 10-15 Türkçe etiket
- "thumbnail_text": kapakta yazacak 2-4 kelimelik, başlığı tekrar ETMEYEN çarpıcı Türkçe ifade
- "thumbnail_prompt": kapak arka planı için İNGİLİZCE görsel tarifi; tek, net, dramatik bir odak nesnesi;
  sol tarafta yazı için sade alan; yazı içermeyen

Sadece şu JSON'u döndür:
{{"title": "...", "description": "...", "tags": ["..."], "thumbnail_text": "...", "thumbnail_prompt": "...",
  "sections": [{{"heading": "...", "goal": "...", "facts": ["..."]}}]}}"""
    log("Video planı yazılıyor...")
    outline = _parse_json(llm.ask(_system(cfg), prompt, 4000))
    if not outline.get("sections"):
        raise ValueError("Video planında bölüm yok.")
    return outline


def write_section(llm, cfg: dict, outline: dict, idx: int, scene_count: int,
                  words_per_scene: int, previous_text: str) -> list:
    sections = outline["sections"]
    sec = sections[idx]
    plan = "\n".join(f"{i + 1}. {s.get('heading', '')}: {s.get('goal', '')}" for i, s in enumerate(sections))
    position = ("Bu videonun İLK bölümü: ilk sahne güçlü bir kanca olsun, 'merhaba arkadaşlar' gibi boş "
                "girişler kullanma; ikinci sahnede videoda ne öğrenileceğini vaat et."
                if idx == 0 else
                "Bu videonun SON bölümü: konuyu bağla, son sahnede kısa bir kapanış ve doğal bir "
                "'ilginç bulduysan abone olmayı unutma' çağrısı yap."
                if idx == len(sections) - 1 else
                "Bu bir ara bölüm: bir önceki bölümden doğal bir geçişle başla, selamlama veya kapanış yapma.")
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
Sadece doğrulanabilir bilgiler kullan; emin olmadığın sayı, tarih veya alıntıyı yazma.

{_visual_rules(cfg['video'].get('ai_image_ratio', 0.35))}

Sadece şu JSON'u döndür:
{{"scenes": [{{"text": "...", "visual": "stock", "query": "...", "prompt": "..."}}]}}"""
    data = _parse_json(llm.ask(_system(cfg), prompt, 6000))
    return data.get("scenes", [])


def write_script(llm, cfg: dict, topic: dict) -> dict:
    minutes = cfg["video"]["target_minutes"]
    total_words = int(minutes * WORDS_PER_MINUTE)
    total_scenes = max(20, round(minutes * 60 / SECONDS_PER_SCENE))
    words_per_scene = round(total_words / total_scenes)

    outline = write_outline(llm, cfg, topic)
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
    if forced_topic:
        topic = {"topic": forced_topic, "angle": "", "search_terms": []}
    else:
        topic = pick_topic(llm, cfg, past_titles)
    script = write_script(llm, cfg, topic)
    if cfg["llm"].get("fact_check", True):
        try:
            script = fact_check(llm, cfg, script)
        except Exception as e:
            log(f"  Doğruluk kontrolü yapılamadı, ilk senaryoyla devam ediliyor: {e}")
    script["topic"] = topic
    words = sum(len(s["text"].split()) for s in script["scenes"])
    log(f"Senaryo hazır: {len(script['scenes'])} sahne, {words} kelime "
        f"(~{words / WORDS_PER_MINUTE:.1f} dk)")
    return script
