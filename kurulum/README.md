# Kurulum rehberi (adım adım)

Bu rehber, depoyu indirmeden GitHub'dan kopyala-yapıştırla Dataiku'ya kurulum içindir. Önce
**prova projesi** (`AVUKAT_PERF_TEST`, sentetik veriyle), sonra **canlı proje** (`AVUKAT_PERF`)
kurulur. Her adımın sonunda bir kontrol vardır; kontrol tutmadan sonraki adıma geçmeyin.
Takıldığınız yerde hata iletisini (yalnız ileti; satır verisi değil) not edin.

**GitHub'dan kopyalama.** Dosyayı GitHub'da açın; sağ üstteki **Copy raw file** (ham dosyayı
kopyala) düğmesine basın ve Dataiku'da hedefe yapıştırın. Ekrandaki önizlemeden seçip kopyalamak
girintiyi bozabilir. Büyük dosyalarda (kütüphane paketleri) de aynı düğme kullanılır.

| Adım | Ne yapılır | Kullanılan dosya |
|---|---|---|
| 0 | Ön hazırlık | — |
| 1 | Proje ve sürüm kontrolü | `kurulum/adim_01_surum_kontrolu.py` |
| 2 | Kütüphane | `kurulum/adim_02_kutuphane_avukat_perf.py`, `_hat.py`, `_arayuz.py` |
| 3 | Veri kümeleri ve klasörler | `kurulum/adim_03_veri_kumeleri.py` |
| 4 | Ayarlar ve sentetik veri | `kurulum/adim_04_ayarlar_ve_sentetik_veri.py` |
| 5 | Aktarım kontrolü | `kurulum/adim_05_aktarim_kontrolu.py`, `aktarim_ozeti.txt` |
| 6 | Senaryolar | `dataiku/tarifler/gecelik_calisma.py`, `donem_sonu.py` |
| 7 | Web uygulaması | `dataiku/webapp/index.html`, `stil.css`, `uygulama.js`, `backend.py` |
| 8 | Provayı çalıştırma | — |
| 9 | Gerçek veriyle deneme (isteğe bağlı) | — |
| 10 | Canlı proje | — |

---

## 0. Ön hazırlık

| Ne | Kimden | Prova için gerekli mi |
|---|---|---|
| Dataiku'da proje açma ve kod kütüphanesi yazma yetkisi | Dataiku yöneticisi | Evet |
| Yazılabilir bir bağlantı (Dataiku'nun kendi dosya sistemi bağlantısı yeterli) | Dataiku yöneticisi | Evet |
| MinIO'da iki kova ve S3 bağlantısı (`minio/README.md`) | MinIO ve Dataiku yöneticisi | Hayır |
| Grafana'nın okuyacağı SQL bağlantısı (`grafana/README.md`) | Dataiku ve veritabanı yöneticisi | Hayır; canlıdan önce |

## 1. Proje ve sürüm kontrolü

1. Dataiku ana sayfası > **+ New Project > Blank project**. Proje anahtarı `AVUKAT_PERF_TEST`.
2. **Code (`</>`) > Notebooks > + New Notebook > Write your own > Python**; kod ortamı varsayılan.
3. `kurulum/adim_01_surum_kontrolu.py` dosyasını ilk hücreye yapıştırıp çalıştırın (Shift+Enter).

**Kontrol:** Python 3.7 ya da üstü; pandas 1.x ya da 2.x; `flask` satırında sürüm görünür.
`kütüphane API` satırı 2. adımdaki yolu belirler. `bağlantı` satırları 3. adımda yazılacak
bağlantı adını gösterir (liste okunamazsa ad Dataiku yöneticisinden alınır). Not defterinin
kod ortamının adını not edin: senaryolar ve web uygulaması da aynı ortamda çalışmalıdır.

## 2. Kütüphane

Üç yoldan biri. Hangisi olursa olsun sonunda proje kütüphanesinde (**Code > Libraries**)
`python/avukat_perf`, `python/hat` ve `python/arayuz` klasörleri bulunur.

**Yol A — Git'ten içe aktarma** (Dataiku sunucusu GitHub'a erişebiliyorsa en kolayı).
Code > Libraries > **Git** menüsünden içe aktarma: depo adresi `https://github.com/Sahinbasci/test.git`, dal `main`,
depodaki yol `dataiku/kutuphane`, hedef yol `python`. Erişim yoksa Yol B'ye geçin.

**Yol B — Yapıştırma paketleri** (1. adımda `kütüphane API: var` ise). Bir not defterinde
yeni bir hücreye sırayla şu üç dosyanın tamamını yapıştırıp çalıştırın:

1. `kurulum/adim_02_kutuphane_avukat_perf.py`
2. `kurulum/adim_02_kutuphane_hat.py`
3. `kurulum/adim_02_kutuphane_arayuz.py`

Her biri dosyaları kütüphaneye yazar, geri okuyup doğrular ve
"`<paket>`: N dosya yazıldı ve doğrulandı" yazar. Bir paket hata verirse yalnız o paketi yeniden
çalıştırın. Sonra not defterinin çekirdeğini yeniden başlatın (**Kernel > Restart**).

**Yol C — Elle.** Code > Libraries > `python` altında üç klasör açılır ve
`dataiku/kutuphane/<paket>/` içindeki her `.py` dosyası (`__init__.py` dahil) aynı adla
oluşturulup içeriği yapıştırılır.

**Kontrol:** 5. adımda (aktarım kontrolü) yapılır.

## 3. Veri kümeleri ve klasörler

`kurulum/adim_03_veri_kumeleri.py` (`dataiku/kontrol/kurulum.py` ile aynıdır) `# %%`
satırlarıyla hücrelere ayrılır; her bölümü ayrı hücreye yapıştırın.

1. 1. hücrede:
   - `BAGLANTI`: yazılabilir bağlantının adı (MinIO varsa `minio_avukat_perf`).
   - `KLASOR_TURU`: bağlantı MinIO (S3) ise `"S3"`, Dataiku'nun dosya sistemi ise `"Filesystem"`.
   - `SQL_BAGLANTISI`: varsa SQL bağlantısının adı, yoksa `None` (provada `None` olabilir).
   - Provada `DOSYA_KAYNAGI_VAR = True`.
2. 1–3. hücreleri çalıştırın.
3. S3 bağlantısında `ham_arsiv` klasörünün ayarlarından kovayı `avukat-perf-ham` seçin.

**Kontrol:** Flow'da `calisma_kaydi`, `kalite_sonucu`, `sonuc_*`, `model_*`, `gozlem_*` veri
kümeleri ve `ayarlar`, `ham_arsiv`, `kaynak_dosyalari` klasörleri görünür.

## 4. Ayarlar ve sentetik veri

1. `kurulum/adim_04_ayarlar_ve_sentetik_veri.py` dosyasının tamamını bir hücreye yapıştırıp
   çalıştırın (provada `PROVA = True` kalır). `ayarlar` klasörüne `params.json`,
   `kaynaklar.json` ve prova ek dosyaları; `kaynak_dosyalari` klasörüne `sentetik/veri/`
   altında on CSV yazılır.
2. `adim_03_veri_kumeleri.py` 4. hücresini yeniden çalıştırın.

**Kontrol:** Hücre "Ayarlar yüklendi ve sentetik veri yazıldı" der; 4. hücre hata vermez.

## 5. Aktarım kontrolü

1. `kurulum/adim_05_aktarim_kontrolu.py` hücrelerini yeni bir not defterinde sırayla çalıştırın.
2. 1. ve 2. hücrenin çıktısını depodaki `aktarim_ozeti.txt` ile karşılaştırın: her satır aynen
   bulunmalı (`kontrol/` satırları hariç).

**Kontrol:**
- Bütün özet satırları tutuyor. Farklı satır o dosyanın eksik ya da hatalı yapıştırıldığını
  gösterir; yalnız o dosya (ya da o paket) yeniden yapıştırılır.
- "ek ayar dosyaları: params_ek.json, kaynaklar_ek.json" ve "kaynaklar: geçerli" satırları görünür.
- Tarih gidiş-dönüş satırları `True`.

## 6. Senaryolar

İki senaryo açın; ikisinde de tek adım: **Execute Python code**.

| Senaryo | Adımın içeriği | Tetikleyici (yalnız canlıda) |
|---|---|---|
| `AVUKAT_PERF_GECELIK` | `dataiku/tarifler/gecelik_calisma.py` | Her gün 02:00 |
| `AVUKAT_PERF_DONEM_SONU` | `dataiku/tarifler/donem_sonu.py` | Her ayın 1'i 06:00 |

İkisinde de **Reporters**: senaryo başarısız olunca e-posta. Provada tetikleyici açılmaz.

## 7. Web uygulaması

1. **+ New Webapp > Code Webapp > Standard**, adı `avukat_performans`.
2. Sekmelere yapıştırın: HTML ← `dataiku/webapp/index.html`, CSS ← `stil.css`, JS ←
   `uygulama.js`, Python ← `backend.py`. Arka ucu (backend) açık bırakın, kaydedip başlatın.

**Kontrol:** Sayfa açılır. Veri yoksa bileşenlerde "kaynak bekleniyor" görünür; bu hata değildir.
Excel ya da CSV indirme Dataiku görünümünde engellenirse uygulama yeni sekmede açılır.

## 8. Provayı çalıştırma

1. `AVUKAT_PERF_GECELIK` senaryosunu elle çalıştırın.
2. Proje değişkenlerinde `donem` = `2026-10` yazıp `AVUKAT_PERF_DONEM_SONU` senaryosunu
   çalıştırın.
3. Web uygulamasını yenileyin (önbellek beş dakika; hemen görmek için arka ucun `/api/yenile`
   adresi).

**Kontrol:**
- `calisma_kaydi` içinde gecelik satırının kalite sonucu `GECTI`.
- Veri Durumu'nda tek uyarı: `AVUKAT_AVUKAT` (ataması olmayan iki sentetik avukat; beklenir).
- Genel Bakış'ta sıralama, notlar ve grafikler dolu; Avukatlar sayfasında arama ve "Neden bu
  puanı aldı?" paneli çalışır.

## 9. Gerçek veriyle deneme (isteğe bağlı, prova projesinde)

Tahsilat raporu ekranlarından Excel olarak dışa aktarılan tablolarla deneme. Önce 8. adım geçmiş
olmalıdır: aktarım doğrulanmış olur, çıkan sorun veriden kaynaklanır. Gerçek veri şirket
ortamından çıkmaz; dışarı yalnız şema özeti (alan adı, tür, satır sayısı, biçim) gider.

1. **Dışa aktarma.** Her tabloyu (dosya bazında liste, tahsilat hareketleri, avukat toplamları)
   tablo görselinin **…** menüsünden **Export data** ile Excel olarak alın. Sayfa ve görsel
   süzgeçlerini kaldırın (dönem: tümü). Rapor aracı dışa aktarmada satır sayısını sınırlayabilir;
   indirilen satır sayısını ekrandaki toplamla karşılaştırın.
2. **Yükleme.** Her Excel dosyasını **+ Dataset > Upload your files** ile ayrı bir veri kümesi
   olarak yükleyin (ör. `pbi_dosya`, `pbi_tahsilat`, `pbi_avukat_toplam`); doğru Excel sayfasını
   seçin. Veri kümesinin **Schema** sekmesinde dosya numarası ve avukat kodu sütunlarının türünü
   `string` yapın (baştaki sıfırlar kaybolmasın).
3. **Şema özeti.** `kurulum/sema_ozeti.py` dosyasını bir not defterine yapıştırın.
   `VERI_KUMELERI`'ne veri kümesi adlarını, `DEGER_LISTESI`'ne yalnız kod listesi sütunlarını
   (branş, hareket türü, dosya durumu) yazıp çalıştırın. Çıktıda satır değeri yoktur: satır
   sayısı, sütun adı, tür, boş oranı ve biçim maskesi (rakam 9, harf A/a) vardır. Okuyup
   paylaşın.
4. **Eşleme.** Şema özetine göre `kaynaklar_ek.json` hazırlanır: sütun adlarının hattın
   alanlarına eşlenmesi, tarih ve sayı biçimi, branş değerlerinin kodlara çevrilmesi, puana
   girecek hareket türleri ve kaynakların yöntemi (`dataiku`, veri kümesi adıyla). Dosya `ayarlar`
   klasörüne yüklenir; prova ek dosyasının yerine geçer.
5. **Eksik kaynaklar.** Rapor yalnız tahsilat tarafını verir; çekirdek sistemin dosya ve atama
   kaynakları zorunludur. Atama geçmişi yoksa deneme için her dosya bugünkü avukatına açılış
   tarihinden beri atanmış sayılır (yeniden atanan dosyada tahsilat yanlış avukata yazılabilir;
   bu denemenin puanları değerlendirmede kullanılmaz).
6. Gecelik senaryoyu çalıştırıp Veri Durumu sayfasındaki kalite kapısı sonuçlarına bakın.
   Deneme bitince prova projesi silinir.

## 10. Canlı proje

1. `AVUKAT_PERF` anahtarıyla 1, 2, 3, 5, 6 ve 7. adımlar tekrarlanır. Farklar:
   - 3. adımda `DOSYA_KAYNAGI_VAR` yalnız dosyadan okunan gerçek bir kaynak varsa `True`;
     `SQL_BAGLANTISI` ilk geceden önce mutlaka yazılır (sonradan taşımak çalışma kaydını sıfırlar).
   - 4. adımda `PROVA = False`: yalnız `params.json` ve `kaynaklar.json` yazılır.
2. Şirkete özgü değerler (`ayarlar` klasöründe yalnız fark olarak): gerçek sistem adları
   (`params_ek.json` > `gorunum.sistem_adlari`), API adresleri ve gizli adları, alan eşlemesi,
   branş değer eşlemesi, puana girecek hareket türleri (`kaynaklar_ek.json`).
3. Bağlanmayan kaynakların yöntemi `bekliyor` kalır; gece bu kaynaklar için
   `KAYNAK_BEKLENIYOR` yazar, hata değildir. Dava takip ve değerlendirme sistemleri bağlı
   değilken Tahsilat sütunu, portföy ve aylık/yıllık tahsilat çalışır; Kriter 1 çekirdek
   sistemin takip bilgisinden gölge modda (bayrak var, puan düşümü ve e-posta yok) hesaplanır.
   İlk fazda Süre ve Performans birleşik puana girmez (`birlesik_sutunlar`; ağırlıklar
   Tahsilat 50, Hukuki Kalite 36, Davranış 14). Değerlendirme sistemi bağlanana kadar Hukuki
   Kalite ve Davranış "kaynak bekleniyor" kalır; birleşik puan bu iki sütun gelince yayımlanır.
4. Grafana: SQL bağlantısına bağlanıp `grafana/pano.json` ve `grafana/sorgular.sql` kurulur.
5. Zaman tetikleyicileri açılır.

## Güncellemeler

1. Senaryolar çalışırken güncelleme yapılmaz.
2. GitHub'da iki sürüm arasında `aktarim_ozeti.txt` farkına bakın; değişen satırların dosyaları
   yeniden yapıştırılır. Kütüphanede değişen paket için o paketin `adim_02_*` dosyası yeniden
   çalıştırılır (bütün paketi yeniden yazar).
3. Web uygulamasının arka ucunu yeniden başlatın.
4. Aktarım kontrolünü (5. adım) yeniden çalıştırın.
