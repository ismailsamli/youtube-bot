# YouTube Video Botu

**Tamamen ücretsiz çalışır.** Varsayılan ayarlarla hiçbir servise para ödemezsin ve kart bilgisi girmen gerekmez.

Bu bot sıfırdan 8–10 dakikalık, 16:9 formatında Türkçe bilgi videoları üretir ve YouTube'a yükleyip yayın saatini planlar.

**Botun yaptığı işler, sırasıyla:**

1. **Konu seçer.** Gemini (ücretsiz), daha önce yapılan videoları tekrar etmeyen yeni bir konu bulur.
2. **Senaryo yazar.** Gemini yaklaşık 45 sahnelik bir senaryo yazar, ardından bilgileri ikinci kez kontrol eder.
3. **Seslendirir.** Microsoft'un ücretsiz Türkçe sesi kullanılır.
4. **Görselleri bulur.** Pexels'ten ücretsiz stok videolar gelir. Stokta bulunamayacak sahneler için ücretsiz bir servisle yapay zeka görseli üretilir.
5. **Montaj yapar.** FFmpeg sahneleri birleştirir, altyazı ekler ve görsellere yakınlaşma efekti verir.
6. **Kapak hazırlar.** Büyük, Türkçe yazılı bir kapak fotoğrafı oluşturur.
7. **Yükler ve planlar.** YouTube'a yükler ve belirlediğin saatte yayına girecek şekilde planlar.

---

## 1. Kurulum (bir kez yapılır, yaklaşık 30 dakika)

### a) Python
1. https://www.python.org/downloads/ adresinden Python 3.11 veya daha yeni bir sürümü indir.
2. Kurulumda **"Add Python to PATH"** kutusunu mutlaka işaretle.

### b) FFmpeg
1. https://www.gyan.dev/ffmpeg/builds/ adresinden **ffmpeg-release-essentials.zip** dosyasını indir.
2. Zip'i `C:\ffmpeg` klasörüne çıkar. İçinde `C:\ffmpeg\bin\ffmpeg.exe` dosyası olmalı.
3. Başlat menüsüne **"ortam değişkenleri"** yazıp aç.
4. **Path** satırını seç, **Düzenle** > **Yeni** de ve `C:\ffmpeg\bin` yaz.
5. Yeni bir CMD penceresi aç ve `ffmpeg -version` yaz. Bir sürüm yazısı görüyorsan kurulum tamam.

### c) Botun paketleri
1. Bu klasörün adres çubuğuna `cmd` yazıp Enter'a bas.
2. Açılan pencerede şunu çalıştır:
```
pip install -r requirements.txt
```

### d) API anahtarları
1. `.env.example` dosyasının adını `.env` olarak değiştir.
2. Not Defteri ile aç ve aşağıdaki anahtarları yapıştır:

| Anahtar | Nereden alınır | Ücret |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com/apikey > Create API key | Ücretsiz, kart istemez |
| `PEXELS_API_KEY` | pexels.com/api | Ücretsiz |
| `ANTHROPIC_API_KEY` | Boş bırak | Sadece ileride Claude'a geçersen gerekir |

> Gemini'nin ücretsiz katmanında dakikalık ve günlük istek sınırı var. Sınıra takılırsa bot kendiliğinden bekleyip devam eder; bir video için birkaç istek yeterli.
> Ücretsiz katmanda Google, gönderdiğin metinleri ürünlerini geliştirmek için kullanabilir. Senaryo üretiminde bu sorun değil, ama kişisel bilgi yazma.

### e) YouTube bağlantısı
1. https://console.cloud.google.com adresinde yeni bir proje oluştur.
2. **APIs & Services** > **Library** bölümünde **YouTube Data API v3**'ü bul ve **Enable** de.
3. **OAuth consent screen** bölümünde:
   - User Type olarak **External** seç.
   - Uygulamaya bir ad ver ve e-postanı yaz.
   - **Test users** kısmına kendi Gmail adresini ekle.
   - Son olarak **Publish app** ile uygulamayı **In production** durumuna al.
   - Bu adımı atlarsan giriş izni 7 günde bir sona erer ve bot her hafta yeniden giriş ister.
4. **Credentials** > **Create credentials** > **OAuth client ID** yolunu izle. Uygulama türü olarak **Desktop app** seç.
5. Oluşan JSON dosyasını indir. Adını `client_secret.json` yapıp bu klasöre koy.
6. Botu ilk çalıştırdığında tarayıcı açılır. YouTube kanalının bağlı olduğu Google hesabıyla giriş yap. "Google bu uygulamayı doğrulamadı" uyarısı çıkarsa **Gelişmiş** > **devam et** de; uygulama kendi hesabına ait olduğu için bu güvenlidir.

---

## 2. Kullanım

| Komut | Ne yapar |
|---|---|
| `python run.py` | 1 video üretir, yükler ve planlar |
| `python run.py --count 3` | 3 video üretir |
| `python run.py --topic "Piri Reis haritası"` | Belirli bir konuda video üretir |
| `python run.py --no-upload` | Sadece üretir, yüklemez. İlk denemede böyle başla. |
| `python run.py --resume "output\KLASÖR"` | Hata alınan videoya kaldığı yerden devam eder |
| `python run.py --upload-only "output\KLASÖR"` | Hazır bir videoyu yükler |

Alternatif olarak `baslat.bat` dosyasına çift tıklayarak 1 video üretip yükleyebilirsin.

Her video `output` klasöründe kendi klasörüne kaydedilir. Klasörde şunlar bulunur:
- `video.mp4`
- `thumbnail.jpg`
- `senaryo.txt`
- `youtube_bilgileri.txt`

Bir video yaklaşık 15–40 dakikada hazırlanır. Süre bilgisayarının hızına bağlıdır.

### Her gün otomatik çalıştırma
1. Windows'ta **Görev Zamanlayıcı**'yı aç ve **Temel Görev Oluştur** de.
2. Tetikleyici olarak **Günlük**'ü seç ve bir saat belirle (örneğin 03:00).
3. Eylem olarak **Program başlat** de ve bu klasördeki `baslat.bat` dosyasını seç.
4. **Başlangıç konumu** kutusuna bu klasörün yolunu yaz.

Bilgisayar o saatte açık olmalıdır.

---

## 3. Ayarlar (`config.yaml`)

- **Konular:** `topic_pool`
- **Video süresi:** `target_minutes`
- **Yapay zeka görsellerinin oranı:** `ai_image_ratio`
- **Ses:**
  - Erkek ses: `tr-TR-AhmetNeural`
  - Kadın ses: `tr-TR-EmelNeural`
- **Yapay zeka:** `llm.provider` ayarı `"gemini"` (ücretsiz) olarak gelir. İleride kanal büyür ve daha kaliteli Türkçe senaryo istersen `"claude"` yapıp `.env`'ye Claude API anahtarı eklersin.
- **Yapay zeka görselleri:** `images.provider` ayarı:
  - `"free"`: ücretsiz servis, varsayılan
  - `"gemini"`: Nano Banana, ücretli
  - `"none"`: sadece stok görsel
  - Ücretsiz servis yavaşlarsa veya cevap vermezse bot otomatik olarak stok görsele geçer.
- **Yayın saatleri:** `publish_times`. Örneğin `["12:00", "19:00"]` yazarsan günde iki video yayınlanır.
- **Arka plan müziği:** `assets/music` klasörüne telifsiz bir mp3 koyarsan videolara otomatik eklenir. YouTube Ses Kitaplığı'ndan ücretsiz müzik indirebilirsin.

---

## 4. Önemli notlar

- **Doğrulanmamış Google projesi:** YouTube, doğrulanmamış Google projeleriyle yüklenen videoları "özel" olarak kilitleyebilir. Videon planlanan saatte herkese açılmazsa şu formu doldurman gerekir: "YouTube API Services – Audit and Quota Extension Form". Bu, kendi kanalın için tek seferlik bir onaydır.
- **Günlük yükleme kotası:** API'nin günlük kotası sınırlıdır ve günde yalnızca birkaç video yüklenebilir. Kota dolarsa video kaydedilir; ertesi gün `--upload-only` komutuyla yüklersin.
- **Kapak fotoğrafı:** Özel kapak yükleyebilmek için kanalın telefonla doğrulanmış olması gerekir. Doğrulamayı youtube.com/verify adresinden yapabilirsin.
- **Kalite ve para kazanma:**
  - YouTube, toplu üretilen ve birbirinin tekrarı olan videoları para kazanma programından çıkarabilir.
  - Bu yüzden günde 1–2 video ile başla.
  - İlk videoları yayından önce izle; senaryo ve görselleri kontrol et.
  - Videolar planlı yüklendiği için yayın saatine kadar YouTube Studio'dan düzeltebilir ya da silebilirsin.
- **Yapay zeka etiketi:** Bot videoları "yapay zeka içerir" olarak işaretler. YouTube bunu gerçekçi sentetik içerik için zorunlu tutuyor.
- **Dosya güvenliği:** `.env`, `client_secret.json` ve `token.json` dosyalarını kimseyle paylaşma.
