# Grafana

Grafana yalnız operasyonel izleme içindir: çalışma durumu, veri tazeliği, kalite sonuçları,
alarm. Hukuk dashboard'u değildir; puan ve avukat bilgisi göstermez.

## Ön koşul

Pano iki Dataiku veri kümesini okur: `calisma_kaydi` ve `kalite_sonucu`. Bu ikisi, Grafana'nın
bağlanabildiği bir SQL bağlantısında (PostgreSQL) tutulmalıdır. Dataiku'da veri kümesi >
Ayarlar > Bağlantı bölümünden SQL bağlantısı seçilir; kod değişmez. Diğer veri kümeleri
MinIO'da kalır.

Grafana tarafında bu veritabanı için salt okunur bir kullanıcı yeterlidir.

## Kurulum

1. Grafana > Bağlantılar > Veri kaynakları > PostgreSQL: veritabanı adresi ve salt okunur
   kullanıcı.
2. Grafana > Panolar > İçe aktar > `grafana/pano.json`.
3. Pano üstündeki değişkenler:
   - Veri kaynağı: 1. adımdaki PostgreSQL kaynağı.
   - Çalışma kaydı tablosu ve kalite sonucu tablosu: Dataiku'daki gerçek tablo adı
     (veri kümesi > Ayarlar > Bağlantı > Tablo). Dataiku çoğunlukla proje anahtarını önek
     ekler, ör. `"AVUKAT_PERF_calisma_kaydi"`; büyük harf varsa çift tırnakla yazılır.
4. Panoyu kaydedin.

## Paneller

| Panel | Sorgu | Ne gösterir |
|---|---|---|
| Son gecelik çalışma | P1 | Son gecenin kararı (geçti, kaynak bekleniyor, kaldı) ve kimliği |
| Kaynak tazeliği | P2 | Her kaynağın son başarılı çekimi ve üzerinden geçen gün |
| Gece kararları | P3 | Seçili aralıkta gece gece karar çizelgesi |
| Kaynak başına satır sayısı | P4 | Ani düşüş ya da artış (kalite kapısındaki satır sapması) |
| Geçmeyen kalite denetimleri | P5 | Son gecede uyarı ve kalan denetimler, açıklamalarıyla |

Sorguların tamamı `grafana/sorgular.sql` dosyasındadır; pano bu dosyadan üretilmiştir
(`tests/test_izleme.py` ikisinin aynı kaldığını denetler).

## Alarmlar

Grafana > Uyarılar > Uyarı kuralları > Yeni kural; sorgu `sorgular.sql` içinden alınır.
**Sorgudaki `${calisma_tablosu}` yerine gerçek tablo adı yazılır** (3. adımdaki ad, ör.
`"AVUKAT_PERF_calisma_kaydi"`): uyarı kuralları panodan bağımsız çalışır ve pano değişkenini
çözmez; değişkenle bırakılan sorgu sözdizimi hatası verir ve kural hata durumunda kalır. Kural
önizlemesi tek satır döndürmelidir. Değerlendirme aralığı kural grubunda saatte birdir; gece
çalışması sürerken (00:00–07:00) bildirim istenmiyorsa bu saatler için susturma zamanlaması
(mute timing) tanımlanır.

| Kural | Sorgu | Koşul |
|---|---|---|
| Tamamlanan gece yok | A1 | sonuç = 0 |
| Kalite kapısı geçmedi | A2 | sonuç = 1 |
| Bayat kaynak | A3 | sonuç > 0 |

Bildirim kanalı (e-posta ya da kurum içi mesajlaşma) Grafana yöneticisiyle belirlenir.
Kaynak bağlantısı beklenirken (`KAYNAK_BEKLENIYOR`) alarm üretilmez: A1 bu geceleri tamamlanmış
sayar, A3 yalnız daha önce okunup kendi kapısını geçmiş kaynakları izler. Kaynaklar bağlanana
kadar beklenen durum budur; kurulumdan sonra gece hiç çalışmazsa ya da kalırsa alarm gelir.
A3 kaynağın kendi kapı sonucuna (`kalite_sonucu`) bakar: bir kaynak geceyi durdurduğunda kapıdan
geçmiş diğer kaynaklar bayat sayılmaz, yalnız kalan kaynak sayılır. Geçmeyen kalite denetimleri
panelinde (P5) geceyi durduran `KALDI` satırları uyarılardan önce gelir.

Ayrıca Dataiku senaryosu hata verdiğinde Dataiku'nun kendi bildirimi (senaryo > Bildirimler)
açılmalıdır; kod çökerse `calisma_kaydi`'na satır yazılamayabilir.
