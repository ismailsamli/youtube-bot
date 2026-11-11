# CLAUDE.md — youtube-bot

Kullanıcıyla **Türkçe** ve basit bir dille konuş. Kullanıcı yazılımcı değil; teknik terimleri kısaca açıkla.

## Proje ne yapıyor?

"**Kırmızı Kravat**" adlı Türkçe bilgi/belgesel YouTube kanalı için videoları baştan sona otomatik üreten bir bot.
Normalde **GitHub Actions** üzerinde (bulutta) çalışır; bilgisayarda çalıştırmak isteğe bağlıdır.

Günlük akış (`run.py`):
1. **Konu seçimi** — sıra: `konular.yaml`'daki o yayın gününe yazılmış konu → konu avcısının önerisi
   (`data/konu_onerileri.json`, iki günde bir) → Gemini'nin kendi seçtiği konu (`config.yaml > channel.topic_pool`).
2. **Senaryo** — Gemini (ücretsiz) ~7,5 dk'lık, sahnelere bölünmüş senaryo yazar (`bot/script_writer.py`).
3. **Seslendirme** — Gemini TTS, olmazsa Piper (çevrimdışı yedek) (`bot/tts.py`). Ses, faster-whisper ile sahnelere hizalanır.
4. **Görseller** — Cloudflare Workers AI ile "kâğıt kesme" tarzı çizimler; kota biterse Wikimedia/Openverse fotoğrafları (`bot/visuals.py`).
5. **Montaj** — FFmpeg: sahneler + altyazı + giriş/bitiş jeneriği + arka plan müziği (`bot/editor.py`, `bot/mixer.py`, `bot/branding.py`).
6. **Kapak** — 3 kapak seçeneği (A/B/C), Studio'daki "Test ve karşılaştır" için (`bot/thumbnail.py`).
7. **Yükleme** — YouTube'a "özel" yükler, 19:00'a (TR) planlar; ertesi gün için 3 Short üretip planlar (`bot/uploader.py`, `bot/shorts.py`).
8. **Kanal bakımı** — oynatma listesine ekleme, ilk yorum, filigran, izleyici yorumlarına yapay zekâ cevabı (`run.py > channel_upkeep`).

Zamanlama: `video-uret.yml` her gün **11:13 TR** (08:13 UTC) çalışır. Sırada zaten 2 video varsa yeni video üretmez.

## Dosyalar ne işe yarıyor?

### Ana dosyalar
| Dosya | Görevi |
|---|---|
| `run.py` | Ana program. Tüm akışı yönetir. `--count`, `--topic`, `--no-upload`, `--resume`, `--upload-only`, `--keep-files`, `--max-queue` |
| `config.yaml` | **Tüm ayarlar**: kanal konuları, video süresi, ses, yapay zekâ modelleri, görsel stili, Shorts, yayın saatleri, oynatma listeleri |
| `konular.yaml` | Kullanıcının elle seçtiği konular. Anahtar = **yayın tarihi** (YYYY-AA-GG). "Vurgun Dosyaları" serisi burada |
| `youtube_yetki.py` | Tek seferlik YouTube izni alma (link → kod). İzni şifreleyip `data/youtube_token.enc`'e yazar |
| `requirements.txt` | Python paketleri (`httplib2<0.32` sınırı bilerek konmuş, kaldırma) |
| `baslat.bat` | Windows'ta çift tıklayıp `run.py`'yi çalıştırmak için |
| `.env.example` | Bilgisayarda çalıştırma için anahtar şablonu (`.env` git'e girmez) |

### `bot/` — videoyu üreten parçalar
| Dosya | Görevi |
|---|---|
| `script_writer.py` | Konu seçimi, senaryo, başlık/açıklama/etiket yazımı. `LLM` sınıfı Gemini/Claude arasında geçiş yapar, model kapanırsa yedeğe düşer |
| `tts.py` | Seslendirme motorları (gemini / google / piper / edge), kota takibi, whisper ile hizalama |
| `visuals.py` | Sahne görsellerini bulur/çizer, lisans atıflarını toplar |
| `paperstyle.py` | Fotoğraflara kâğıt kesme / kâğıt baskı efekti |
| `collage.py` | Kanal kimliği çerçevesi (kâğıt zemin, yırtık kenar, kırmızı bant) |
| `editor.py` | FFmpeg montajı ve altyazı (.ass) |
| `mixer.py` | Müzik altlığı, konuşurken müziği kısma, -14 LUFS ses seviyesi, müzik atıfları |
| `branding.py` | Giriş jeneriği ve 12 sn'lik bitiş ekranı, kapanış cümlesi |
| `thumbnail.py` | Kapak görseli (yazı + arka plan) |
| `shorts.py` | Uzun videodan dikey Shorts üretimi ve yayın saatleri |
| `uploader.py` | YouTube API: yükleme, planlama, kapak, oynatma listesi, yorum, filigran |
| `secure.py` | YouTube iznini şifreleme/çözme |
| `utils.py` | Ortak yardımcılar (log, config okuma, ffmpeg çalıştırma, süre ölçme, slug) |

### `tools/` — ayrı, elle çalıştırılan araçlar (her birinin bir workflow'u var)
| Dosya | Görevi |
|---|---|
| `konu_avcisi.py` | İngilizce kanallarda patlamış videoların **konularını** bulur → `data/konu_onerileri.json` (her pazartesi otomatik) |
| `istatistik.py` | YouTube Analytics → `data/istatistik.json` |
| `baslik_degistir.py` | Yüklenmiş videonun başlığını değiştirir |
| `kapak_yenile.py` | `data/kapak_yenile.json`'daki videoların kapaklarını yeniler |
| `kanal_ayarlari.py` | Kanal anahtar kelimeleri, ülke, dil |
| `tek_short.py` | Uzun videoya bağlı olmayan tek Short |
| `muzik_indir.py` | CC BY lisanslı müzikleri `assets/music`'e indirir, `kaynaklar.json`'a atıf yazar |
| `ses_ornekleri.py` / `gorsel_ornekleri.py` | Ses ve çizim tarzı denemeleri |
| `intro_kagit.py` | `assets/intro_animasyon.mp4` kâğıt tarzı girişi (4,2 sn, krem zemine yumuşak geçişli) üretir. Eski çizgi film girişi: `intro_animasyon.py` |
| `ffmpeg_kur.sh` | GitHub sunucusunda FFmpeg ve font kurulumu |

### Diğer klasörler
- `.github/workflows/` — GitHub Actions işleri. Ana iş: `video-uret.yml`. Diğerleri araçları elle tetiklemek için.
- `assets/` — font, müzik, filigran, giriş animasyonu.
- `data/` — botun hafızası (aşağıya bak).
- `kapaklar/` — her videonun kapak seçenekleri, önizleme ve senaryo kopyası (yayından önce kontrol için).
- `onizleme_kesit/`, `ses_ornekleri/`, `gorsel_ornekleri/` — telefondan kontrol için üretilmiş örnek çıktılar.
- `output/` — yerelde üretilen videolar (git'e girmez).

## DOKUNULMAMASI gerekenler ⚠️

1. **`data/youtube_token.enc`** — Şifreli YouTube izni. Silinir/bozulursa kullanıcı izni baştan almak zorunda kalır. Asla değiştirme.
2. **`bot/secure.py`'deki anahtar üretimi** (`_key`) — Değişirse mevcut token çözülemez.
3. **`data/history.json`** — Hangi videoların üretildiği/yüklendiği, video ID'leri, yayın saatleri. Bot bununla
   aynı konuyu tekrar etmemeyi, yayın saatini çakıştırmamayı ve yorum/oynatma listesi işlerini takip eder.
   Elle düzenleme; gerekiyorsa önce kullanıcıya sor.
4. **`data/kanal_durumu.json`, `data/konu_onerileri.json`, `data/istatistik.json`** — Bot ve GitHub Actions bunları
   her gün güncelleyip commit'liyor. Elle düzenlersen çakışma olur.
5. **Gizli anahtarlar** — `.env`, `client_secret.json`, `token.json` asla git'e eklenmemeli, içerikleri ekrana yazılmamalı.
   Secret'lar GitHub'da: `GEMINI_API_KEY`, `YOUTUBE_CLIENT_SECRET`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`
   (isteğe bağlı: `PEXELS_API_KEY`, `GOOGLE_TTS_KEY`, `ANTHROPIC_API_KEY`).
6. **Müzik ve görsel atıfları** (`assets/music/kaynaklar.json`, açıklamaya eklenen "Müzik:" / "Görsel kaynakları" blokları) —
   CC BY lisansı gereği zorunlu. Kaldırma.
7. **`config.yaml > upload.synthetic_media: true`** — YouTube'a yapay zekâ içeriği bildirimi. Kapatma.
8. **Workflow zamanlamaları ve kota mantığı** — 11:13 saati Gemini ücretsiz kotasının yenilenmesine göre seçildi;
   `gemini_group_words`, `cf_steps`, `fact_check: false` gibi ayarlar ücretsiz kotaya sığmak için. Kullanıcı istemeden değiştirme.
9. **`konular.yaml`'daki `notlar` alanları** — Gerçek kişiler (dolandırıcılık davaları) hakkında hukuki/etik sınırlar içerir. Yumuşatma, silme.
10. **Yayın sırası** — Planlanmış videoları etkileyen bir şey (yükleme, silme, başlık değiştirme) yapmadan önce mutlaka kullanıcıya sor.

## Çalışma kuralları

- **İşe başlamadan önce `git pull`** yap: GitHub Actions her gün repoya commit atıyor ("Video geçmişi güncellendi", "İstatistik" vb.).
- Yerelde deneme yaparken **`python run.py --no-upload`** kullan; yanlışlıkla YouTube'a yükleme yapma.
- Commit/push sadece kullanıcı isterse. Push edilen değişiklik bir sonraki günlük çalışmada **canlıya çıkar**.
- Kodda yorumlar ve log mesajları Türkçe; aynı tarzı sürdür.
- Hatalar video üretimini durdurmamalı: kanal bakımı, Shorts, önizleme gibi yan işler `try/except` ile sarılı. Bu yapıyı koru.
- `README_BILGISAYAR.md` kısmen eski (Edge sesi, Pexels anlatıyor); güncel davranış için `config.yaml` ve kod esas.
- Yerelde çalıştırmak için gerekli: Python 3.11+, FFmpeg (PATH'te), `pip install -r requirements.txt`, `.env` dosyası.
