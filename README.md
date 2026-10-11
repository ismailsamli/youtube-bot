# YouTube Video Botu (Bulut Sürümü)

Bu bot her gün kendiliğinden çalışır ve 8–10 dakikalık Türkçe bilgi videoları üretir. Videoyu YouTube'a yükler ve akşam 19:00'da yayına girecek şekilde planlar.

- **Bilgisayar gerekmez:** Bot GitHub'ın sunucularında çalışır.
- **Ücretsizdir:** Gerekli tüm servislerin ücretsiz katmanları kullanılır.
- **Telefondan kurulur:** Tüm adımlar telefondan yapılabilir.

> Evdeki bilgisayarda çalıştırmak istersen: `README_BILGISAYAR.md`

---

## Kurulum (bir kez, yaklaşık 30 dakika)

Kurulumdaki tüm adımları GitHub mobil uygulamasında değil, **tarayıcıda** (Chrome veya Safari) yap.

### 1. Ücretsiz anahtarları al

| Anahtar | Nereden |
|---|---|
| Gemini | aistudio.google.com/apikey → **Create API key** |
| Pexels | pexels.com/api → ücretsiz hesap aç → **Your API Key** |

### 2. YouTube için Google Cloud projesi

1. console.cloud.google.com adresinde yeni bir proje oluştur. Adı örneğin `youtube-bot` olabilir.
2. **APIs & Services → Library** bölümünde **YouTube Data API v3**'ü bul ve **Enable** de.
3. **Google Auth Platform / OAuth consent screen** bölümünde:
   - User type olarak **External** seç.
   - Uygulamaya bir ad ver ve e-postanı yaz.
   - **Audience** bölümünde **Publish app** ile durumu **In production** yap. Bu adımı atlarsan izin 7 günde bir sona erer.
4. **Clients / Credentials** bölümünde **Create client** de. Uygulama türü olarak **Desktop app** seç.
5. **Download JSON** ile dosyayı indir. Dosyayı bir metin uygulamasıyla açıp içeriğin tamamını kopyala; bir sonraki adımda lazım olacak.

### 3. Anahtarları GitHub'a kaydet

Repo sayfasında **Settings → Secrets and variables → Actions → New repository secret** yolunu izle. Şu üç secret'ı ekle:

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | Gemini anahtarı |
| `PEXELS_API_KEY` | Pexels anahtarı |
| `YOUTUBE_CLIENT_SECRET` | İndirdiğin JSON dosyasının **tüm içeriği** |

### 4. YouTube izni (tek seferlik)

1. Repoda **Actions** sekmesine gir. Solda **YouTube İzni (tek seferlik)** → **Run workflow** yolunu izle ve **1 - İzin bağlantısı oluştur** seçeneğini çalıştır.
2. İşlem bitince üzerine tıkla. Özetteki **Google izin sayfasını aç** bağlantısını aç.
3. Kanalının bağlı olduğu Google hesabını seç ve izin ver.
   - *"Google bu uygulamayı doğrulamadı"* uyarısı çıkarsa **Gelişmiş → devam et** de. Uygulama senin kendi projen olduğu için güvenli.
4. İzin verdikten sonra **açılmayan bir sayfa** göreceksin. Bu normal.
5. Adres çubuğundaki tam adresi kopyala. Adres `http://localhost:8080/?state=...&code=...` şeklinde olmalı.
6. **YouTube İzni** işlemini tekrar çalıştır. Bu kez **2 - İzni kaydet** seç ve kopyaladığın adresi kutuya yapıştır.

İzin şifrelenerek repoya kaydedilir ve sadece senin secret'ınla açılabilir.

### 5. İlk deneme

1. **Actions → Video Üret → Run workflow** yolunu izle.
2. **"YouTube'a yüklensin mi?"** kutusundaki işareti kaldır ve çalıştır.
3. İşlem 20–40 dakika sürer. Bitince işlemin sayfasında en alttaki **Artifacts → videolar** bölümünden videoyu indirip izleyebilirsin.

Video iyi görünüyorsa kurulum tamam. Bundan sonra bot **her sabah 06:13'te** kendiliğinden bir video üretir ve **19:00'a planlar**.

---

## Günlük kullanım

| İstediğin | Yapman gereken |
|---|---|
| Ekstra video | **Actions → Video Üret → Run workflow** (adet ve konu seçebilirsin) |
| Belirli bir konu | Aynı ekranda **konu** kutusuna yaz |
| Botu durdurmak | **Actions → Video Üret → ⋯ → Disable workflow** |
| Saat, ses, süre değiştirmek | `config.yaml` dosyasını düzenle (GitHub'da kalem ikonu) |
| Günlük video sayısını değiştirmek | `config.yaml` → `publish_times` ve `.github/workflows/video-uret.yml` → `cron` |

Bir işlem başarısız olursa GitHub sana e-posta gönderir.

---

## Bilinmesi gerekenler

- **Ücretsiz çalışma süresi:** Gizli repolarda GitHub ayda 2000 dakika ücretsiz çalışma süresi verir. Video başına yaklaşık 20–40 dakika gittiği için günde 1 video rahat sığar. Dakikalar dolarsa bot ay sonuna kadar durur; ücret çıkmaz.
- **Videoların "özel" kalması:** YouTube, denetimden geçmemiş Google projeleriyle yüklenen videoları "özel" olarak kilitleyebilir. Videon 19:00'da herkese açılmazsa Google'ın **"YouTube API Services – Audit and Quota Extension Form"** formunu doldur. Bu, kendi kanalın için tek seferlik bir onaydır.
- **Kapak fotoğrafı:** Özel kapak yükleyebilmek için kanalın telefonla doğrulanmış olması gerekir. Doğrulamayı youtube.com/verify adresinden yapabilirsin.
- **İlk videoları kontrol et:** Videolar yayından saatler önce yüklendiği için YouTube Studio uygulamasından kontrol edip gerekirse düzeltebilir ya da silebilirsin.
- **Kalite ve para kazanma:** YouTube, toplu ve tekrarlı üretilen içerikleri para kazanma programından çıkarabilir. Günde 1–2 videoyla başla.
- **Secret güvenliği:** Secret'ları kimseyle paylaşma. Repo **Private** (gizli) kalmalı.
