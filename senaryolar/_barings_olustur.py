"""Barings (Vurgun Dosyaları #6) hazır senaryosunu senaryolar/2026-11-10.json olarak yazar.
Kaynak: Singapur Ulusal Kütüphanesi Infopedia, 'Collapse of Barings'; İngiltere Merkez Bankası raporu (1995)."""
import json
from pathlib import Path

C = lambda text, kalip, p: {"text": text, "kalip": kalip, "p": p, "cold": True, "section": -1}
S = []   # (bölüm, metin, kalıp, p, etiket)

def s(sec, text, kalip, p, key=None):
    S.append({"text": text, "kalip": kalip, "p": p, "section": sec, "_k": key})

cold = [
    C("23 Şubat 1995 gecesi, Singapur. Yirmi sekiz yaşında bir borsacı masasına kısa bir not bırakıp ortadan kayboluyor.",
      "ortam", {"ortam": "gece", "ikon": "ucak", "etiket": "Singapur, 23 Şubat 1995"}),
    C("Not tek bir kelimeden ibaret: Üzgünüm. Ekranlardaki gizli bir hesapta ise milyonlar eriyip gitmiş.",
      "nesne", {"ikon": "mektup", "etiketler": ["\"Üzgünüm\"", "Gizli hesap", "Eriyen milyonlar"]}),
    C("Üç gün sonra, 233 yıllık bir İngiliz bankası tek bir adamın yüzünden batmış olacak.",
      "sayi", {"deger": 233, "birim": "yıllık banka", "etiket": "Tek bir çalışan yüzünden batacak", "ikon": "banka"}),
    C("Her şey, kimsenin dikkat etmediği beş haneli bir hesap numarasıyla başladı.",
      "nesne", {"ikon": "kilit", "etiketler": ["Beş haneli hesap numarası"]}),
]

# ---- 0. bölüm
s(0, "Peki tek bir çalışan, iki yüzyılı aşkın geçmişi olan bir bankayı nasıl batırabildi? Cevap, Londra'nın en saygın bankalarından birinde başlıyor.",
  "soru", {"soru": "Tek bir çalışan, köklü bir bankayı nasıl batırır?"})
s(0, "Barings Bankası 1762'de Londra'da kuruldu. İngiltere'nin en eski yatırım bankalarından biriydi ve asırlar boyunca güvenin simgesi oldu.",
  "nesne", {"ikon": "banka", "baslik": "Barings Bankası", "etiketler": ["1762, Londra", "En eski yatırım bankalarından", "Güvenin simgesi"]})
s(0, "Banka o kadar güçlüydü ki 1803'te Amerika Birleşik Devletleri'nin Louisiana bölgesini satın almasının finansmanında rol oynadı.",
  "rota", {"nereden": "Londra", "nereye": "Louisiana", "arac": "gemi", "baslik": "1803: Louisiana alımı"})
s(0, "1762'de kurulan, 1803'te Louisiana alımına para bulan Barings, 1990'larda Asya piyasalarında hızla büyümek istiyordu.",
  "zaman", {"baslik": "Barings'in yolculuğu", "olaylar": [{"yil": 1762, "metin": "Londra'da kuruldu"}, {"yil": 1803, "metin": "Louisiana alımını finanse etti"}, {"yil": 1990, "metin": "Asya'da büyüme hamlesi"}]})
s(0, "Tam bu sırada sahneye Nick Leeson çıktı. İşçi bir ailede büyümüş, üniversite okumamış, son derece hırslı genç bir bankacıydı.",
  "kisi", {"isim": "Nick Leeson", "rol": "Barings'in genç ve hırslı bankacısı", "ikon": "insan"})
s(0, "Leeson daha önce bankanın Londra ve Jakarta ofislerinde operasyon tarafında çalışmış, işlemlerin arka planını çok iyi öğrenmişti.",
  "nesne", {"ikon": "bilgisayar", "etiketler": ["Londra ve Jakarta", "Operasyon deneyimi", "Arka ofisi iyi tanıyor"]})
s(0, "Leeson 1992 baharında Singapur'a gönderildi. Görevi, bankanın Singapur borsasındaki vadeli işlemlerini yönetmekti.",
  "rota", {"nereden": "Londra", "nereye": "Singapur", "arac": "ucak", "baslik": "1992: Singapur'a atama"})
s(0, "Kısa sürede yıldızı parladı. Raporlara göre Japon borsası üzerine yaptığı işlemlerle bankaya büyük kârlar kazandırıyordu.",
  "nesne", {"ikon": "grafik_artis", "baslik": "Yükselen yıldız", "etiketler": ["Japon borsası işlemleri", "Raporlarda büyük kâr"]})
s(0, "Ama bu parlak kârların arkasında, kimsenin görmediği bir hesap vardı.",
  "baslik", {"baslik": "Görünmeyen hesap", "alt": "Parlak kârların arkasında", "ikon": "kilit"})

# ---- 1. bölüm
s(1, "3 Temmuz 1992'de Leeson'ın ekibinde bir hata hesabı açıldı. Numarası 88888'di; Çin kültüründe sekiz, şansın ve bereketin sayısıdır.",
  "sayi", {"deger": 88888, "etiket": "Hata hesabının numarası", "ikon": "belge"}, "h88888")
s(1, "Bu tür hesaplar normalde küçük işlem hatalarını geçici olarak kaydetmek için kullanılır ve kısa sürede kapatılır.",
  "nesne", {"ikon": "belge", "etiketler": ["Hata hesabı", "Küçük işlem hataları", "Kısa sürede kapanır"]}, "hata")
s(1, "Ama 88888 hiç kapanmadı. Leeson, ekibin yaptığı hataları ve kendi zarar eden işlemlerini sessizce bu hesaba aktarmaya başladı.",
  "akis", {"baslik": "Zarar nereye gitti?", "adimlar": ["Zarar eden işlem", "88888 hesabına aktarılıyor", "Raporlarda görünmüyor"], "ikonlar": ["grafik_dusus", "kilit", "belge"]}, "akis")
s(1, "Böylece merkeze giden raporlarda sadece kâr görünüyordu; zararlar ise gizli hesapta sessizce birikiyordu.",
  "liste", {"baslik": "İki ayrı tablo", "maddeler": [{"metin": "Merkeze giden rapor: sadece kâr", "ikon": "grafik_artis"}, {"metin": "Gizli hesap: biriken zarar", "ikon": "grafik_dusus"}]}, "iki")
s(1, "Peki bunu neden kimse fark etmedi? Çünkü Leeson hem işlemleri yapan, hem de bu işlemlerin kaydını tutan kişiydi.",
  "kisi", {"isim": "Nick Leeson", "rol": "Hem işlemleri yapan hem kayıtları tutan", "not": "Kendi işini kendisi denetliyordu", "ikon": "insan", "damga": "ÇİFT ROL"})
s(1, "Bankacılıkta bu iki görevin aynı kişide toplanmaması en temel kurallardan biridir. Barings bu kuralı Singapur'da uygulamamıştı.",
  "nesne", {"ikon": "carpi", "baslik": "Temel kural", "etiketler": ["İşlem ve kayıt ayrı kişilerde olmalı", "Singapur'da uygulanmadı"]})
s(1, "Eylül 1992'nin sonunda gizli hesaptaki zarar şimdiden 8,8 milyon Singapur dolarıydı. Bu, yaklaşan felaketin yalnızca başlangıcıydı.",
  "sayi", {"deger": "8,8", "birim": "milyon Singapur doları", "etiket": "Eylül 1992 sonu: gizli zarar", "ikon": "banknot"})
s(1, "Leeson yıllar sonra yazdığı kitapta, zararı itiraf etmek yerine onu sessizce telafi etmeye çalıştığını anlattı. Bu karar her şeyi değiştirdi.",
  "nesne", {"ikon": "kitap", "etiketler": ["İtiraf yerine telafi", "Her şeyi değiştiren karar"]})

# ---- 2. bölüm
s(2, "Leeson zararları kapatmak için daha büyük riskler almaya başladı. Kaybettikçe işlemlerini büyüttü, büyüttükçe daha çok kaybetti.",
  "akis", {"baslik": "Kısır döngü", "adimlar": ["Zarar", "Daha büyük risk", "Daha büyük zarar"], "ikonlar": ["grafik_dusus", "ates", "grafik_dusus"]})
s(2, "Pozisyonları için para gerekiyordu. Leeson, teminat ihtiyacını müşteri işlemleri gibi göstererek Londra'dan yüz milyonlarca sterlin getirtti.",
  "rota", {"nereden": "Londra", "nereye": "Singapur", "arac": "ucak", "baslik": "Londra'dan gelen para"})
s(2, "Merkezdekiler bu paranın müşterilerin işlemleri için gittiğini sanıyordu. Kimse transferlerin neden bu kadar büyüdüğünü ciddi şekilde sorgulamadı.",
  "liste", {"baslik": "Londra ne sanıyordu?", "maddeler": [{"metin": "Müşteri işlemleri için para", "ikon": "kalabalik"}, {"metin": "Transferler büyüyor", "ikon": "ok_yukari"}, {"metin": "Kimse sorgulamıyor", "ikon": "soru"}]})
s(2, "Denetçiler soru sorduğunda sahte belgelere başvurdu. Daha sonra sahtecilik suçlamasını da mahkemede kabul edecekti.",
  "nesne", {"ikon": "belge", "baslik": "Sahte belgeler", "etiketler": ["Denetçilere sahte evrak", "Sahtecilik suçlaması"]})
s(2, "1994'ün sonunda gizli hesaptaki zarar 373,9 milyon Singapur dolarına ulaşmıştı. Ama Londra'ya giden raporlar hâlâ kâr gösteriyordu.",
  "sayi", {"deger": "373,9", "birim": "milyon Singapur doları", "etiket": "1994 sonu: gizli zarar", "ikon": "kasa"}, "z1994")
s(2, "Barings yönetimi ise Singapur'daki yıldızına güveniyordu. Leeson'ın 1994 yılı için yüklü bir ikramiye alması bekleniyordu.",
  "nesne", {"ikon": "para", "etiketler": ["Yönetim memnun", "Yüklü ikramiye beklentisi"]})
s(2, "Bu tür gerçek dolandırıcılık hikâyelerini seviyorsan, Vurgun Dosyaları'nın yenisi her hafta geliyor; kaçırmamak için abone ol.",
  "baslik", {"baslik": "Vurgun Dosyaları", "alt": "Her hafta yeni dosya · Abone ol", "ikon": "belge"})
s(2, "Leeson'ın tek umudu, Japon borsasının sakin kalmasıydı. Ama Ocak 1995'te doğa onun yerine karar verecekti.",
  "ortam", {"ortam": "sehir", "baslik": "Ocak 1995", "etiket": "Tek umut: sakin bir piyasa"})

# ---- 3. bölüm
s(3, "17 Ocak 1995 sabahı Japonya'nın Kobe şehrinde büyük bir deprem oldu. Binlerce insan hayatını kaybetti.",
  "gazete", {"manset": "Kobe'de büyük deprem", "tarih": "17 Ocak 1995", "kaynak": "Dünya Basını", "ikon": "bina"}, "kobe")
s(3, "Leeson, Japon borsasının belirli bir aralıkta sakin kalacağı üzerine büyük opsiyon işlemleri yapmıştı. Deprem bu sakinliği bir anda yok etti.",
  "akis", {"baslik": "Bozulan bahis", "adimlar": ["Bahis: sakin piyasa", "Kobe depremi", "Sert dalgalanma"], "ikonlar": ["terazi", "simsek", "grafik_dusus"]})
s(3, "Deprem, Japon borsasının ana endeksi Nikkei 225'i sert bir düşüşe soktu. Leeson'ın bütün hesabı ise endeksin yüksek kalmasına dayanıyordu.",
  "nesne", {"ikon": "grafik_dusus", "baslik": "Nikkei 225", "etiketler": ["Sert düşüş", "Leeson'ın bahsi: yükseliş"]}, "nikkei")
s(3, "Leeson geri çekilmedi. Tam tersine, piyasanın toparlanacağına inanarak çok daha büyük alımlar yaptı.",
  "liste", {"baslik": "Geri adım yok", "maddeler": [{"metin": "Geri çekilmedi", "ikon": "carpi"}, {"metin": "Toparlanmaya bahis", "ikon": "ok_yukari"}, {"metin": "Çok daha büyük alımlar", "ikon": "banknot"}]}, "alim")
s(3, "Pozisyonları öyle büyüdü ki, Singapur borsasındaki Japon vadeli işlemlerinin önemli bir kısmı tek başına ona aitti.",
  "nesne", {"ikon": "hedef", "etiketler": ["Dev pozisyonlar", "Piyasanın gözü üzerinde"]})
s(3, "23 Ocak'ta Nikkei 17.785 puana kadar geriledi. Leeson'ın açık pozisyonları artık bankanın kaldırabileceğinden çok daha büyüktü.",
  "gosterge", {"deger": 17785, "min": 15000, "max": 20000, "birim": "puan", "etiket": "Nikkei 225, 23 Ocak 1995"})
s(3, "Kayıplar katlanarak büyüdü. 23 Şubat 1995'e gelindiğinde gizli hesaptaki zarar 1,4 milyar Singapur dolarını bulmuştu.",
  "sayi", {"deger": "1,4", "birim": "milyar Singapur doları", "etiket": "23 Şubat 1995: gizli zarar", "ikon": "grafik_dusus"}, "z1995")
s(3, "Bu, bankanın sermayesinin yaklaşık iki katıydı. Barings aslında çoktan batmıştı ama Londra hâlâ bunu bilmiyordu.",
  "nesne", {"ikon": "kasa", "etiketler": ["Zarar: sermayenin ~2 katı", "Londra habersiz"]})
s(3, "Sonunda Singapur'daki ekip açıkları fark etmeye başladı. Rakamlar tutmuyor, cevapsız sorular birikiyordu.",
  "liste", {"maddeler": [{"metin": "Rakamlar tutmuyor", "ikon": "unlem"}, {"metin": "Cevapsız sorular birikiyor", "ikon": "soru"}]})

# ---- 4. bölüm
s(4, "23 Şubat 1995 gecesi Leeson, eşi Lisa ile birlikte Singapur'dan Malezya'nın başkenti Kuala Lumpur'a kaçtı.",
  "rota", {"nereden": "Singapur", "nereye": "Kuala Lumpur", "arac": "ucak", "baslik": "23 Şubat 1995 gecesi"})
s(4, "Arkasında bıraktığı notta yalnızca tek bir kelime vardı: Üzgünüm.",
  "nesne", {"ikon": "mektup", "etiketler": ["\"Üzgünüm\""]})
s(4, "Çift, Malezya'dan Borneo adasındaki Kota Kinabalu'ya geçti; oradan da uçakla Avrupa'ya doğru yola çıktı.",
  "rota", {"nereden": "Kuala Lumpur", "nereye": "Kota Kinabalu", "arac": "ucak", "baslik": "Kaçış rotası"})
s(4, "Londra'daki yöneticiler gerçeği öğrendiğinde şoka girdi. İngiltere Merkez Bankası, bankayı kurtarmak için hafta sonu acil toplantılar düzenledi.",
  "ortam", {"ortam": "ofis", "baslik": "Kurtarma toplantısı", "etiket": "Londra, acil hafta sonu"})
s(4, "Ama kimse bu kadar büyük ve hâlâ açık duran bir riski üstlenmek istemedi. Kurtarma girişimi başarısız oldu.",
  "nesne", {"ikon": "carpi", "etiketler": ["Kimse riski üstlenmedi", "Kurtarma başarısız"]})
s(4, "26 Şubat 1995'te Barings Bankası batık ilan edildi. 233 yıllık tarih, tek bir çalışanın gizli işlemleri yüzünden sona ermişti.",
  "gazete", {"manset": "Barings Bankası battı", "tarih": "26 Şubat 1995", "kaynak": "Finans Gazetesi", "ikon": "banka"}, "batti")
s(4, "Toplam zarar yaklaşık 827 milyon sterlindi; bu, o günkü kurla yaklaşık 1,4 milyar dolar ediyordu.",
  "yigin", {"ikon": "banknot", "metin": "827 milyon sterlin", "etiket": "≈ 1,4 milyar dolar"}, "toplam")
s(4, "Birkaç gün sonra Hollandalı ING grubu Barings'i sembolik olarak yalnızca 1 sterline satın aldı ve borçları üstlendi.",
  "sayi", {"deger": 1, "birim": "sterlin", "etiket": "ING'nin ödediği sembolik bedel", "ikon": "para"})
s(4, "Barings adı bir süre ING'nin içinde yaşadı; ama bağımsız ve köklü bir banka olarak hikâyesi orada bitmişti.",
  "nesne", {"ikon": "banka", "etiketler": ["ING bünyesine geçti", "Bağımsız hikâye bitti"]})

# ---- 5. bölüm
s(5, "Leeson'ın kaçışı uzun sürmedi. 2 Mart 1995'te Frankfurt Havalimanı'nda Alman polisi tarafından yakalandı.",
  "nesne", {"ikon": "kelepce", "baslik": "2 Mart 1995", "etiketler": ["Frankfurt Havalimanı", "Alman polisi"]})
s(5, "Kasım 1995'te Singapur'a iade edildi. Aralık ayında dolandırıcılık ve sahtecilik suçlamalarını kabul etti ve altı buçuk yıl hapis cezası aldı.",
  "kisi", {"isim": "Nick Leeson", "rol": "Dolandırıcılık ve sahtecilik suçlamalarını kabul etti", "not": "Altı buçuk yıl hapis", "ikon": "insan", "damga": "HÜKÜM"})
s(5, "Hapisteyken kalın bağırsak kanserine yakalandı. Temmuz 1999'da cezasında indirim yapılarak serbest bırakıldı.",
  "nesne", {"ikon": "hapishane", "etiketler": ["Temmuz 1999: tahliye"]})
s(5, "Tahliyeden sonra yaşadıklarını konferanslarda anlattı. Hikâyesi 1999'da Rogue Trader adıyla sinemaya da uyarlandı.",
  "nesne", {"ikon": "kamera", "etiketler": ["Konferanslar", "1999: Rogue Trader filmi"]})
s(5, "Resmî incelemeler asıl sorunu ortaya koydu: görevler ayrılmamış, denetim zayıf kalmış, olağanüstü kârlar ise hiç sorgulanmamıştı.",
  "liste", {"baslik": "Resmî incelemenin bulguları", "maddeler": [{"metin": "Görevler ayrılmamıştı", "ikon": "carpi"}, {"metin": "Denetim zayıftı", "ikon": "unlem"}, {"metin": "Olağanüstü kârlar sorgulanmadı", "ikon": "soru"}]})
s(5, "Bu hikâyenin bugüne kalan dersi basit: Gerçek olamayacak kadar iyi görünen kazançlar, çoğu zaman gizlenmiş bir zararın işaretidir.",
  "baslik", {"baslik": "Asıl ders", "alt": "Fazla iyi görünen kazancı sorgula", "ikon": "unlem"})
s(5, "Vurgun Dosyaları serisinin bir sonraki dosyası Cuma günü geliyor: 1980'lerde Türkiye'yi sarsan bankerler krizi ve Banker Kastelli.",
  "nesne", {"ikon": "belge", "baslik": "Sıradaki dosya", "etiketler": ["Cuma 19:00", "Banker Kastelli"]})
s(5, "Sence daha büyük hata hangisiydi: tek bir kişiye bu kadar yetki vermek mi, yoksa kimsenin onu sorgulamaması mı? Yorumlarda yaz.",
  "soru", {"soru": "Daha büyük hata: sınırsız yetki mi, sorgulanmamak mı?"})

scenes = cold + S
idx = {sc["_k"]: i for i, sc in enumerate(scenes) if sc.get("_k")}
for sc in scenes:
    sc.pop("_k", None)

shorts = [
    {"title": "88888: 233 Yıllık Bir Bankayı Batıran Gizli Hesap", "headline": "GİZLİ HESAP 88888",
     "comment": "Sence bu hesap neden yıllarca fark edilmedi?",
     "scenes": [
         {"text": "1992'de Singapur'da açılan bir banka hesabının numarası 88888'di.", "src": idx["h88888"]},
         {"text": "Küçük işlem hataları için açılmıştı ama hiç kapanmadı.", "src": idx["hata"]},
         {"text": "Genç borsacı Nick Leeson, zarar eden işlemlerini sessizce bu hesaba sakladı.", "src": idx["akis"]},
         {"text": "Londra'daki merkeze ise yalnızca kâr raporları gidiyordu.", "src": idx["iki"]},
         {"text": "1994'ün sonunda gizli zarar 373,9 milyon Singapur dolarına ulaşmıştı.", "src": idx["z1994"]},
         {"text": "Ve bu, 233 yıllık bir bankanın sonunun başlangıcıydı.", "src": 2},
         {"text": "Hikâyenin tamamı kanalda. Her gün yeni bir gerçek hikâye için abone ol.", "src": idx["batti"]},
     ]},
    {"title": "Bir Deprem 233 Yıllık Bankayı Nasıl Bitirdi?", "headline": "BİR DEPREM, BİR BANKA",
     "comment": "Sen Leeson'ın yerinde olsan geri çekilir miydin?",
     "scenes": [
         {"text": "17 Ocak 1995'te Japonya'nın Kobe şehrini büyük bir deprem vurdu.", "src": idx["kobe"]},
         {"text": "Japon borsası sert düştü ve Singapur'daki bir borsacının bütün hesabı çöktü.", "src": idx["nikkei"]},
         {"text": "Nick Leeson geri çekilmek yerine çok daha büyük alımlar yaptı.", "src": idx["alim"]},
         {"text": "Bir ay sonra gizli zarar 1,4 milyar Singapur dolarını bulmuştu.", "src": idx["z1995"]},
         {"text": "26 Şubat 1995'te 233 yıllık Barings Bankası batık ilan edildi.", "src": idx["batti"]},
         {"text": "Hikâyenin tamamı kanalda. Her gün yeni bir gerçek hikâye için abone ol.", "src": idx["toplam"]},
     ]},
]

sections = ["233 Yıllık Banka ve Genç Yıldız", "88888: Uğurlu Sayının Gizli Hesabı", "Kayıpları Saklama Sanatı",
            "Kobe Depremi ve Çaresiz Kumar", "Kaçış ve Çöküş", "Yakalanış ve Asıl Ders"]
script = {
    "title": "Tek Bir Çalışan 233 Yıllık Bankayı Nasıl BATIRDI? | Barings Skandalı",
    "description": (
        "1762'den beri ayakta duran Barings Bankası, 1995'te Singapur'daki tek bir çalışanın gizli işlemleri "
        "yüzünden battı. 88888 numaralı bir hata hesabı, Kobe depremi ve yaklaşık 827 milyon sterlinlik bir zarar: "
        "Nick Leeson skandalı adım adım.\n\n"
        "Bu videoda Barings'in yükselişini, gizli hesabın nasıl işlediğini, kayıpların nasıl saklandığını ve "
        "denetim eksikliğinin neden bu kadar pahalıya patladığını anlatıyoruz.\n\n"
        "Kaynaklar: Singapur Ulusal Kütüphanesi (Infopedia, Collapse of Barings); İngiltere Merkez Bankası "
        "inceleme raporu (1995).\n\n"
        "📁 Vurgun Dosyaları — Dosya #6\nYeni dosyalar her Salı ve Cuma 19:00'da. Serinin tamamı oynatma listesinde."),
    "tags": ["Barings Bankası", "Nick Leeson", "Barings skandalı", "rogue trader", "88888", "Kobe depremi",
             "Nikkei 225", "banka iflası", "finans skandalı", "dolandırıcılık", "Vurgun Dosyaları", "ekonomi tarihi"],
    "thumbnail_text": "GİZLİ HESAP 88888",
    "thumbnail_alt": [{"text": "BANKAYI TEK BAŞINA BATIRDI"}, {"text": "827 MİLYON NEREDE?"}],
    "thumbnail_prompt": "",
    "playlist": "Vurgun Dosyaları",
    "comment": "Sence daha büyük hata hangisiydi: tek kişiye sınırsız yetki vermek mi, kimsenin onu sorgulamaması mı?",
    "series": {"name": "Vurgun Dosyaları", "episode": 6},
    "sections": sections,
    "topic": {"topic": "Barings Bankası ve Nick Leeson", "angle": "", "search_en": "Barings Bank Nick Leeson"},
    "scenes": scenes,
    "hazir_shorts": shorts,
    "hazirlayan": "Claude (elle yazıldı ve kaynaklarla kontrol edildi)",
}
out = Path(__file__).resolve().parent / "2026-11-10.json"
out.write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
words = sum(len(x["text"].split()) for x in scenes)
print(f"{len(scenes)} sahne, {words} kelime (~{words / 112:.1f} dk klon ses) → {out}")
