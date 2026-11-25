# Sözleşmeli Avukat Performans Sistemi

Rücu dosyalarını yürüten sözleşmeli avukatların performansını dört sütunda hesaplar:
Süre ve Performans (Kriter 1 ilk işlem, Kriter 2 dava açma), Tahsilat, Hukuki Kalite,
Davranış ve İletişim. Sonuçlar bir Dataiku web uygulamasında
gösterilir; operasyonel izleme Grafana'dadır.

Kod saf Python ve pandas'tır (Python 3.7+, pandas 1.x). İş kuralları kütüphanededir; Dataiku
adımları yalnız kütüphaneyi çağırır. Eşik ve ağırlıkların hepsi `params.json` içindedir.

## Klasörler

```
kurulum/                 adım adım kurulum rehberi (README.md) ve çalıştırılacak kodlar (adim_*.py)
dataiku/                 Dataiku'ya girecek her şey
  kutuphane/             proje kütüphanesi (Libraries > python)
    avukat_perf/         iş kuralları ve puan motoru
    hat/                 entegrasyon: kaynak okuma, API, arşiv, gecelik ve dönem sonu akışı
    arayuz/              ekran–veri sözleşmesi ve sayfa verisi
  degiskenler/           varsayılan ayar: params.json (kurallar), kaynaklar.json (bağlantılar)
  tarifler/              senaryo adımları: gecelik_calisma.py, donem_sonu.py
  webapp/                web uygulaması: index.html, stil.css, uygulama.js, backend.py
  kontrol/               kurulum.py, aktarim_kontrol.py (not defteri hücreleri)
minio/                   kova kurulumu ve klasör düzeni (MinIO'da kod çalışmaz)
grafana/                 izleme panosu ve alarm sorguları
sentetik/                sentetik veri üreticisi, hazır CSV'ler, prova ekleri (*_ek.json)
tests/                   testler (pytest ya da araclar/test_kos.py)
araclar/                 yerel araçlar: önizleme, yerel çalıştırma, özet, paketleme, mutasyon
```

## Yerelde çalıştırma

Yerel ortam Python 3.8–3.10 ile `gereksinim_yerel.txt` (pandas 1.4, Dataiku'daki olası en eski
sürüme yakın), Python 3.11 ve sonrasında `gereksinim_yerel_yeni.txt` (pandas 2.2) ile kurulur;
pandas 1.4'ün yeni Python için paketi yoktur. Testler iki ortamda da geçer.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r gereksinim_yerel.txt
```

| İş | Komut |
|---|---|
| Testler | `.venv/bin/python -m pytest -q` |
| Testler (pytest olmadan) | `.venv/bin/python araclar/test_kos.py` |
| Test gücü (bilinçli hata ekler, testler yakalamalı) | `.venv/bin/python araclar/mutasyon.py --paralel 8` |
| Sentetik veriyle uçtan uca çalışma | `.venv/bin/python araclar/yerel_calistir.py` |
| Arayüz önizlemesi | `.venv/bin/python araclar/onizleme.py` → http://127.0.0.1:8771 |
| Kod ve ayar özeti (aktarım denetimi) | `.venv/bin/python araclar/ozet.py` |

Önizleme, Dataiku arka ucunun kullandığı sunum katmanını yerel bir sunucuda çalıştırır;
ekrandaki her sayı sentetik veriden hesaplanır. Sorgudan alınan seçimler (`kod` ve Süre Takibi
süzgeçleri) tek yerde, `arayuz.sunum.SECIMLER`'dedir; `backend.py` ve önizleme bunu kullanır.
`--yenile` hattı baştan çalıştırır.
`--senaryo` üç durumu gösterir:

| Senaryo | Ne gösterir |
|---|---|
| `tam` (varsayılan) | Bütün kaynaklar bağlı, prova parametreleri |
| `acilis` | Canlıya geçiş günü: çekirdek sistem, tahsilat raporu ve değerlendirme sistemi bağlı; dava takip sistemi yok; değerlendirme ölçeği teyitsiz; gölge mod açık. |
| `bos` | Kurulum günü: hiçbir kaynak bağlı değil |

Testlerde uyarılar hata sayılır (`pytest.ini`). Kod pandas 1.x ve 2.x, numpy 1.x ve 2.x ile
sınanmıştır; iki pandas sürümünde aynı sentetik veriden çıkan tablolar birebir aynıdır.
Mutasyon denetimi önce mutasyonsuz kopyada testlerin geçtiğini doğrular; iki mutasyon ("pandas
2 karışık tarih biçimi", "boş tablo birleştirmeye girer") yalnız pandas 2 ortamında ayrışır,
orada koşturulur. Koşuda satır ve modül uzunluğu testleri, aktarım özetinin ve mutasyon
listesinin güncelliği sayılmaz; yazım kurallarının geri kalanı (3.7 söz dizimi, adlar,
bağımlılıklar) sayılır. Test koşusu 3600 saniyeyi aşan mutasyon "ZAMAN AŞIMI" ile sorunlu sayılır.

Ölçek denemesi (1000 avukat, 150 bin dosya, 254 bin tahsilat hareketi, yerel CSV ortamı):
gecelik akış ve üç dönem yayını 65 saniye, en yüksek bellek 0,9 GB; puanlar bağımsız bir
hesapla birebir aynı. Arayüzün en ağır sayfası 0,05 saniyede hazırlanır.

## GitHub'a aktarım

Depoda yalnız kod, ayar varsayılanları ve sentetik veri bulunur; kurum adı, iç sistem adları,
gerçek veri ve kurum belgeleri bulunmaz (`tests/test_gizlilik.py` denetler).
`.gitignore` çalışma notlarını, `docs/` klasörünü ve yerel dosyaları dışarıda bırakır.

```bash
git init
```

```bash
git add .
```

```bash
git status
```

`git status` çıktısında yerel çalışma notları ve `docs/`, `.venv/`, `onizleme/` klasörleri olmamalı.

```bash
git commit -m "Hesaplama çekirdeği, entegrasyon katmanı ve arayüz"
```

GitHub'da depo açıp `git remote add origin ...` ve `git push -u origin main` ile
gönderin.

## Şirket bilgisayarına aktarım (kopyala-yapıştır)

**Adım adım kurulum rehberi ve çalıştırılacak kodlar `kurulum/` klasöründedir**
(`kurulum/README.md`). Kütüphane dosya dosya yapıştırılmak zorunda değildir: Dataiku'nun
kütüphane API'si varsa `kurulum/adim_02_kutuphane_*.py` paketleri (üç not defteri hücresi)
dosyaları kütüphaneye yazar ve doğrular; ayar dosyaları ve sentetik prova verisi
`kurulum/adim_04_ayarlar_ve_sentetik_veri.py` ile yüklenir. Paketleri `araclar/paketle.py`
üretir; kod değişince yeniden üretilir (`tests/test_kurulum.py` eskimeyi yakalar).

Elle aktarımda kod GitHub'dan dosya dosya kopyalanıp Dataiku'ya yapıştırılır. Her dosyada:

1. GitHub'da dosyayı açın, **Raw** düğmesine basın, bütün metni seçip kopyalayın. Önizleme
   ekranından seçmek girintiyi ve boş satırları bozabilir.
2. Dataiku'da hedefe yapıştırıp kaydedin.

| Depodaki dosya | Dataiku'daki yeri |
|---|---|
| `dataiku/kutuphane/avukat_perf/*.py` | Kod > Kütüphaneler > `python/avukat_perf/`, aynı adla |
| `dataiku/kutuphane/hat/*.py` | `python/hat/` |
| `dataiku/kutuphane/arayuz/*.py` | `python/arayuz/` |
| `dataiku/degiskenler/params.json`, `kaynaklar.json` | `ayarlar` yönetilen klasörü, olduğu gibi (dosya yükleyin ya da yeni dosya açıp yapıştırın) |
| `dataiku/tarifler/gecelik_calisma.py` | `AVUKAT_PERF_GECELIK` senaryosu, "Python kodu çalıştır" adımı |
| `dataiku/tarifler/donem_sonu.py` | `AVUKAT_PERF_DONEM_SONU` senaryosu, aynı adım türü |
| `dataiku/webapp/index.html`, `stil.css`, `uygulama.js`, `backend.py` | Web uygulamasının HTML, CSS, JS ve Python sekmeleri |
| `dataiku/kontrol/kurulum.py`, `aktarim_kontrol.py` | Python not defteri; `# %%` satırlarıyla ayrılan her bölüm ayrı hücre |

Aktarılan dosyaların listesi ve özetleri `aktarim_ozeti.txt`'dedir: kütüphane paketleri
(`dataiku/kutuphane` altında `__init__.py` taşıyan her klasör), web uygulaması, senaryo adımları,
kontrol not defterleri ve varsayılan ayar dosyaları (`degiskenler/`; şirkete özgü `_ek`
dosyaları depoda yoktur). Paket ve betik listeleri klasörlerden türetilir; yeni bir paket
kendiliğinden listeye girer. `__init__.py` dosyaları da aktarılır; `avukat_perf/__init__.py`
boş değildir, kitaplığın sürüm numarası oradadır.

**Şirkete özgü ayarlar depoya girmez.** `params.json` ve `kaynaklar.json` depodaki varsayılandır
ve Dataiku'da elle değiştirilmez. Şirkette değişen her değer (gerçek sistem adları, API adresi,
gizli adları, kaynak alan adları, teyit edilen parametreler) aynı klasörde `params_ek.json` ya da
`kaynaklar_ek.json` dosyasına yalnız farkı olarak yazılır. Hat ikisini birleştirir (ekteki değer
kazanır; `hat/ayar.py`). Böylece GitHub'dan gelen yeni varsayılan dosya yapıştırılınca şirket
ayarı kaybolmaz ve bir değer projede tek yerden değişir. Örnek:

```json
{
  "sistemler": {
    "cekirdek": {
      "yontem": "api",
      "api": {"adres_koku": "https://API-ADRESI/v1",
              "kimlik": {"tur": "bearer", "gizli": "API_CEKIRDEK_ANAHTARI"}}
    }
  },
  "kaynaklar": {
    "atama_log": {"alan_eslemesi": {"AV_KOD": "avukat_kodu"}}
  }
}
```

**Aktarımın denetimi.** `aktarim_kontrol.py` 1. hücresi kütüphanedeki her dosyanın, web
uygulamasının dört sekmesinin ve iki senaryo adımının kısa özetini yazar; 2. hücresi `ayarlar`
klasöründeki varsayılan `params.json` ve `kaynaklar.json`'un özetini (`degiskenler/` satırları;
ek dosyalar hariç; anahtar sırası ve girinti etkilemez) ve `hesap_surumu`'nu yazar. Depo
kökündeki `aktarim_ozeti.txt`'nin her satırı bu çıktıda aynen bulunmalıdır. Farklı satır, o
dosyanın eksik ya da hatalı yapıştırıldığını gösterir; yalnız o dosya yeniden yapıştırılır.
Özette olmayan fazladan bir kütüphane satırı, depodan kaldırılmış bir dosyadır: Dataiku
kütüphanesinden de silinir. `kontrol/` satırları (iki not defteri) Dataiku'da dosya olarak
okunamadığı için çıktıda yoktur; değişip değişmediği GitHub farkından görülür. Satır sonu
boşlukları ve dosya sonundaki boş satırlar özeti etkilemez. `hesap_surumu` satırı şirkette
`params_ek.json` bir kural değerini değiştirdiğinde (ör. değerlendirme ölçeği, tutar bantları)
farklı olur; bu beklenir.

Dataiku kütüphaneyi depodan çekebiliyorsa (Kütüphaneler > Git'ten içe aktar) kütüphane için
kopyala-yapıştır gerekmez; denetim aynı biçimde yapılır.

## Dataiku kurulumu

Sıra önemlidir; her adımın sonunda belirtilen kontrol yapılır.

1. **Proje.** Yeni proje, anahtar `AVUKAT_PERF`. Bir Python not defteri açıp
   `import sys, pandas; print(sys.version, pandas.__version__)` çalıştırın; Python 3.7+ ve
   pandas 1.x ya da üstü olmalı. Sürümü not edin.
2. **Kütüphane.** Kod > Kütüphaneler > `python` altında `avukat_perf`, `hat`, `arayuz`
   klasörlerini ve içindeki her `.py` dosyasını (`__init__.py` dahil) aynı adla oluşturup
   içeriği yapıştırın. Dataiku depoya erişebiliyorsa Kütüphaneler > Git'ten içe aktar
   seçeneğiyle `dataiku/kutuphane` yolu doğrudan bağlanabilir; elle yapıştırmaktan güvenlidir.
3. **Veri kümeleri ve klasörler.** `dataiku/kontrol/kurulum.py` 1-3. hücrelerini bir not
   defterinde çalıştırın (1. hücrede bağlantı adlarını yazın; yöntemi `dosya` olan kaynak
   varsa `DOSYA_KAYNAGI_VAR = True`). Hattın yazdığı bütün veri kümelerini (liste
   `hat/veri_kumeleri.py`), iki kontrol tablosunu ve yönetilen klasörleri (`ayarlar`,
   `ham_arsiv`, gerekiyorsa `kaynak_dosyalari`) oluşturur; var olanlara dokunmaz. `ham_arsiv`
   klasörünün kovası (`avukat-perf-ham`) klasör ayarlarından elle seçilir; diğerleri
   bağlantının varsayılan kovasına (`avukat-perf-islenmis`) düşer (bkz. `minio/README.md`).
   **`SQL_BAGLANTISI` ilk geceden önce yazılır.** İzleme tabloları (`calisma_kaydi`,
   `kalite_sonucu`) ve `kontrol_tablo_sql` bu bağlantıda kurulur; Grafana onları buradan okur.
   Sonradan taşımak çalışma kaydını boş tabloyla başlatır: hat önceki başarılı geceyi, ilk
   görülme günlerini ve gölge gecelerini bu kayıttan bulduğu için sonuçlar değişir. Taşımak
   zorunlu olursa önce eski tablolar yeni bağlantıya kopyalanır (Dataiku eşitleme tarifi),
   sonra veri kümesi ayarı değiştirilir.
4. **Ayarlar.** `ayarlar` klasörüne depodaki `params.json` ve `kaynaklar.json` olduğu gibi
   yüklenir (klasör > Dosya ekle). Şirkete özgü değerler aynı klasörde `params_ek.json` ve
   `kaynaklar_ek.json` dosyalarına yazılır (bkz. Şirket bilgisayarına aktarım). Ek dosya yoksa
   yalnız varsayılan kullanılır. Ardından `kurulum.py` 4. hücresi yeniden çalıştırılır: yöntemi
   `dataiku` olan kaynakların veri kümelerini denetler (ayar yüklenmeden çalışırsa atlar, hata
   vermez).
5. **Aktarım kontrolü.** `dataiku/kontrol/aktarim_kontrol.py` hücrelerini çalıştırın. 1. ve 2.
   hücrenin çıktısı yerelde `python araclar/ozet.py` çıktısının satırlarını (`kontrol/` hariç)
   aynen içermeli.
   Tarih gidiş-dönüş satırlarının hepsi, iki kontrol tablosunda da `True` olmalı.
6. **Senaryolar.** Hat, tarif (recipe) olarak değil senaryonun "Python kodu çalıştır"
   adımı olarak çalışır: Dataiku tariflerde bildirilmemiş veri kümesine yazmaya izin vermez
   ve bir veri kümesi aynı tarifin hem girdisi hem çıktısı olamaz; hattın yalnız ekleme
   yapılan tabloları (gözlem, bayrak olayı, çalışma kaydı) önce okuyup sonra yazması gerekir.
   - `AVUKAT_PERF_GECELIK`: zaman tetikleyicisi her gün 02:00; tek adım "Python kodu
     çalıştır", içerik `dataiku/tarifler/gecelik_calisma.py`.
   - `AVUKAT_PERF_DONEM_SONU`: her ayın 1'i 06:00; içerik `dataiku/tarifler/donem_sonu.py`.
   - İkisinde de Bildirimler > senaryo başarısız olunca e-posta.
7. **Web uygulaması.** Yeni web uygulaması > Kod web uygulaması > Standard, adı
   `avukat_performans` (aktarım kontrolü bu adla bulur). HTML sekmesine
   `index.html`, CSS sekmesine `stil.css`, JS sekmesine `uygulama.js`, Python sekmesine
   `backend.py` yapıştırılır; arka uç açık olmalı. Kaydedip başlatın. Gecelik çalışmadan
   hemen sonra güncel veriyi görmek için arka uç önbelleği `/api/yenile` ile boşaltılır
   (önbellek beş dakika).
8. **İzleme.** Grafana'yı 3. adımdaki SQL bağlantısına bağlayıp panoyu kurun
   (`grafana/README.md`). Alarm kurallarına yapıştırılan sorgularda pano değişkeni yerine gerçek
   tablo adı yazılır; uyarı kuralları pano değişkenini çözmez. Kaynaklar bağlanana kadar
   (`KAYNAK_BEKLENIYOR`) alarm gelmez.

### Güncelleme (ikinci ve sonraki aktarımlar)

1. Senaryolar çalışırken yapılmaz (gecelik 02:00, dönem sonu ayın 1'i 06:00); arada yarım
   kalan aktarımla çalışan bir gece eski ve yeni kodu karıştırır.
2. Değişen dosyalar `aktarim_ozeti.txt`'nin önceki ve yeni hâli arasındaki farklı satırlardır
   (GitHub'da commit karşılaştırması). Yalnız onlar yeniden yapıştırılır. Yeni hâlde olmayan
   satırın dosyası (depodan kaldırılmış modül) Dataiku kütüphanesinden de silinir; kalırsa
   aktarım kontrolünün 1. hücresinde fazladan satır olarak görünür.
3. `degiskenler/params.json` ya da `degiskenler/kaynaklar.json` satırı değiştiyse o dosya
   `ayarlar` klasörüne yeniden yüklenir; `_ek` dosyalarına dokunulmaz. `kontrol/` satırı
   değiştiyse not defteri yeniden yapıştırılır.
4. **Web uygulaması arka ucu yeniden başlatılır** (web uygulaması > Arka uç > Yeniden başlat).
   Arka uç süreci kütüphaneyi bellekte tutar; yalnız kütüphane değişse de yeniden
   başlatılmadan eski kodla çalışır. Not defterlerinde çekirdek yeniden başlatılır.
   Senaryo adımının her çalışmada yeni süreçte açıldığı ilk güncellemede bir kez doğrulanır
   (aşağıdaki listede 10).
5. `aktarim_kontrol.py` çalıştırılır; 1. ve 2. hücrenin çıktısı `aktarim_ozeti.txt`'deki
   satırları (`kontrol/` hariç) aynen içermeli.
6. Kod ya da kural değiştiyse `hesap_surumu` değişir ve üst şeritte "Kurallar değişti"
   görünür; ilk gece yeni sürümle hesaplar. Yayımlanmış dönemler değişmez; bir dönem yeniden
   yayımlanırsa düzeltme sürümü açılır.

### İlk kurulumda Dataiku'da doğrulanacaklar

Kütüphanenin Dataiku'ya dokunan kısmı (`hat/dataiku_ortam.py`) burada sahte bir Dataiku
modülüyle sınanır. Gerçek sürümde aşağıdakiler bir kez denenir; çoğunu `aktarim_kontrol.py`
gösterir. Uyuşmazlıkta yalnız `hat/dataiku_ortam.py` (ya da ilgili hücre) değişir.

1. Hiç yazılmamış veri kümesinde `read_schema(raise_if_empty=False)` boş liste döner mi
   (ilk gece buna dayanır; 5. hücre yazmadan önce bunu da gösterir).
2. `get_dataframe(infer_with_pandas=False)` boş değerli tamsayı ya da mantıksal sütunda hata
   veriyor mu; veriyorsa `int_as_float` ve `bool_as_str` parametreleri bu sürümde var mı. Üç
   seçenek de olmazsa okuma hata verir (pandas tahminine düşülmez; kimliklerin baştaki sıfırları
   silinirdi).
3. SQL bağlantısındaki saat dilimsiz zaman damgası UTC mi sayılıyor (5. hücredeki tarih günü
   satırı `True` olmalı).
4. `write_with_schema` SQL tablosunu düşürüp yeniden kuruyorsa Grafana'nın salt okur yetkisi
   kaybolur; veritabanında varsayılan yetki (ALTER DEFAULT PRIVILEGES) tanımlanır.
5. Senaryo adımında `get_auth_info(with_secrets=True)` senaryoyu çalıştıran kullanıcının
   gizlilerini döndürüyor mu (3. hücre not defterinde dener; senaryoda da bir kez bakılmalı).
6. Senaryodaki Python adımının kod ortamı not defteriyle aynı mı (1. adımdaki sürüm denetimi
   senaryo adımında da yapılır).
7. `ham_arsiv` klasörüne MinIO hizmet hesabının en az yetkili politikasıyla (silme yok) yazılıyor
   mu (4. hücre).
8. `aktarim_kontrol.py` 1. hücresi web uygulaması ve senaryo kodunu Dataiku API'siyle okur
   (`get_settings().get_raw()`, `raw_steps`); bu sürümde okunamazsa hücre bunu yazar ve o
   satırlar elle karşılaştırılır.
9. Gecelik (02:00) ve dönem sonu (06:00) senaryoları aynı anda çalışmamalıdır: ikisi de çalışma
   kaydına yazar.
10. Kütüphane güncellendikten sonraki ilk gecelik çalışmanın günlüğündeki `hesap_surumu`,
   `aktarim_kontrol.py` 2. hücresinin yazdığıyla aynı olmalı; farklıysa senaryo eski kodu
   kullanıyordur (kod ortamı ya da süreç yeniden başlatılır).
11. `dataiku` yöntemli kaynakta tarih alanının türü: 6. hücre her bağlı kaynağın tarih
   alanlarının ham türünü yazar. Saat dilimli geliyorsa (`datetime64[ns, UTC]`) bilinen bir
   akşam kaydının (ör. 22:30) okunan günü kaynak sistemdeki günle karşılaştırılır. Kaynak
   veritabanı yerel saati saat dilimsiz tutup Dataiku bunu UTC etiketiyle veriyorsa 21:00'den
   sonraki kayıt ertesi güne kayar (esas bir gün geç, ay sonu tahsilatı sonraki aya); kayma
   varsa sütun türü saat dilimsiz yapılır ya da bağlantının saat dilimi İstanbul olur.

Kaynak bağlantıları yokken gecelik çalışma `KAYNAK_BEKLENIYOR` yazar ve hesap yapmaz; bu bir
hata değildir. Web uygulaması bu durumda bileşenlerde "kaynak bekleniyor" gösterir.

### Sentetik veriyle Dataiku provası

Prova **ayrı bir Dataiku projesinde** yapılır (ör. `AVUKAT_PERF_TEST`); canlı projenin veri
kümelerine ve arşivine dokunmaz, bitince proje silinir. Kurulum canlı projeyle aynıdır (1-7);
tek fark `kurulum.py` 1. hücresinde `DOSYA_KAYNAGI_VAR = True` yazılmasıdır (prova bütün
kaynakları dosyadan okur; `kaynak_dosyalari` klasörü ancak bu ayarla kurulur). Ayar dosyalarında
hiçbir şey elle değiştirilmez:

1. `ayarlar` klasörüne depodaki `params.json` ve `kaynaklar.json`, ek olarak
   `sentetik/params_ek.json` ve `sentetik/kaynaklar_ek.json` aynı adlarla yüklenir. Ekler bütün
   sistemleri dosya yöntemine alır ve prova parametrelerini verir (değerlendirme ölçeği, gölge
   mod kapalı, sulh kodları; tahsilat ayarları üretim varsayılanıdır); alan eşlemesi ve tarih,
   sayı biçimleri hazırdır.
2. `kaynak_dosyalari` klasörüne `sentetik/veri/*.csv` dosyaları `sentetik/veri/` alt yoluyla
   yüklenir (ör. `sentetik/veri/kaynak_cekirdek_dosya.csv`).
3. `aktarim_kontrol.py` çalıştırılır: "ek ayar dosyaları: params_ek.json, kaynaklar_ek.json" ve
   "kaynaklar: geçerli" satırları görülmeli.
4. Gecelik senaryo elle çalıştırılır, ardından dönem sonu senaryosu `donem` proje değişkeniyle
   (ör. `2026-10`).

Prova canlı projede yapılmak zorunda kalınırsa bitince iki ek dosya ve `kaynak_dosyalari`
içeriği silinir, hattın yazdığı **bütün** veri kümeleri silinip `kurulum.py` ile yeniden
oluşturulur (`calisma_kaydi`, `kalite_sonucu`, `gozlem_*`, `bayrak_olay`, `olay_celiski`,
`puan_donem`, `birlesik_donem`, `model_*`, `sonuc_*`; listesi `hat/veri_kumeleri.py`) ve
`ham_arsiv` klasöründeki prova dosyaları silinir. Kalırsa ilk canlı gece prova çalışmasını
"önceki başarılı çekim" sayar ve esasların ilk görülme gününü prova gününe yazar.

## Ekran adları

Ekranda görünen adlar **yalnız** `dataiku/degiskenler/params.json` içindeki `gorunum`
bölümünde tanımlıdır. Bölüm dört ad tablosu taşır:

```json
"gorunum": {
  "sistem_adlari": {
    "cekirdek": "Çekirdek sistem",
    "tahsilat_raporu": "Tahsilat raporu",
    "degerlendirme": "Değerlendirme sistemi",
    "dava_takip": "Dava takip sistemi",
    "duzeltme": "Düzeltme kayıtları"
  },
  "brans_adlari": [["TRAFIK", "Trafik"], ["KASKO", "Kasko"], ...],
  "alt_baslik_adlari": {"eksik_hatali_islem": "Eksik veya hatalı işlemler", ...},
  "mevcut_alan_adlari": {"brans_yetkinligi": "Branş yetkinliği", ...}
}
```

- `sistem_adlari`: kaynak sistemlerin adları. Soldaki kodlar kodun her yerinde kullanılır ve
  **değişmez**; yalnız sağdaki adları değiştirin.
- `brans_adlari`: `[[kod, ad], ...]` listesi. Listedeki sıra branşın renk paletindeki yeridir
  (`stil.css` → `--brans-1` … `--brans-7`; sırayla doğrulanmış komşu renkler, yedinci gri
  "Diğer"). Liste ek dosyada bütünüyle değişir: gerçek branş kodları gelince yalnız bu liste ve
  `kalite.bilinen_branslar` yazılır; `uygulama.js` ve `stil.css` değişmez. Listede olmayan ya
  da paletin dışında kalan (8. ve sonrası) branş ekranda kendi koduyla ve nötr renkle
  (`--brans-bilinmeyen`) görünür.
- `alt_baslik_adlari`, `mevcut_alan_adlari`: `{kod: ad}`; kalite ve davranış alt başlıklarının
  ve mevcut dört değerlendirme alanının ekran adları.
- Arayüz dosyalarında sistem, branş, alt başlık ve mevcut alan adı ya da kodu yazılı değildir
  (`tests/test_tek_kaynak.py`, `tests/test_arayuz_metin.py` denetler); adlar `ortak.adlar`
  bileşeniyle (`arayuz/sunum_ortak.py`) her yanıtta gelir.
- Bu bölüm hesaplamayı ve hesap sürümünü etkilemez; ad değiştirmek yalnız ekranı değiştirir.
- Şirkette gerçek adlar `ayarlar` klasöründeki `params_ek.json` dosyasına yazılır
  (`{"gorunum": {"sistem_adlari": {"cekirdek": "..."}}}`); web uygulaması beş dakika içinde ya
  da arka uçtaki `/api/yenile` çağrısıyla yeni adları gösterir.
- Bir sistem kodu eksik bırakılırsa, bir ad boş yazılırsa ya da `brans_adlari`'nda bir kod iki
  kez geçerse parametre doğrulaması hata verir ve gecelik çalışma başlamaz.

## Veri entegrasyonu

Kaynaklara hangi yolla bağlanılacağı henüz belli değil. Kod bu yüzden yönteme bağlı değildir:
her kaynağın yöntemi `kaynaklar.json` içinde tanımlanır. Bağlantı gelince yalnız ayar
dosyası değişir; kod değişmez.

| Yöntem | Ne zaman | Gereken |
|---|---|---|
| `bekliyor` | Bağlantı henüz yok | — |
| `api` | Kaynak ekibi REST/JSON servis verirse | `api.adres_koku` (sistem) + `api.yol` (kaynak) |
| `dataiku` | Kaynak Dataiku'da veri kümesi olarak tanımlanırsa (SQL görünümü, dosya, Excel, paylaşılan proje) | `dataiku.veri_kumesi` |
| `dosya` | Kaynak ekibi her gün CSV bırakırsa | `dosya.yol` (Dataiku'da `kaynak_dosyalari` klasöründeki yol) |

`dosya` yönteminde isteğe bağlı `dosya.ayirici` (varsayılan `,`; ör. `;`) ve `dosya.kodlama`
(varsayılan `utf-8`; ör. `cp1254`) verilir, ör. `"dosya": {"yol": "gunluk/dosya.csv",
"ayirici": ";", "kodlama": "cp1254"}`. Bütün sütunlar metin olarak okunur; tür dönüşümü
`tarih_bicimi` ve `sayi_bicimi` ile kalite kapısında yapılır.

`kaynaklar.json` iki bölümdür:

- `sistemler`: sistem başına ortak ayar (`cekirdek`, `tahsilat_raporu`, `degerlendirme`,
  `dava_takip`, `duzeltme`): `yontem`, `api` (adres kökü, kimlik, sayfalama, kayıt yolu,
  zaman aşımı), `sayi_bicimi`, `tarih_bicimi`. Bir sistemin bütün kaynakları bu ayarı alır.
- `kaynaklar`: kaynağa özgü ayar: `api.yol`, `dataiku.veri_kumesi`, `dosya.yol`,
  `alan_eslemesi`, `deger_eslemesi`. Burada verilen her değer sistemdeki değeri ezer (ör. tek bir kaynağı
  `"yontem": "bekliyor"` ile kapatmak ya da tam `api.adres` vermek).

Kaynağın etkin ayarı sistem ayarı + kaynak ayarıdır; adres `adres_koku` + `/` + `yol` olarak
kurulur (yolun başındaki `/` önemsizdir). Ek dosya derin birleştirilir; yalnız `sayfalama` bloğu
(liste gibi) bütünüyle değişir: ekte sayfalama yazılırsa tamamı yazılır, depodaki alanlar miras
kalmaz (ör. imleç kipine geçince depodaki sayfa boyutu). Ayar her gece okunmadan önce doğrulanır
(`hat/ayar.py`, alt bloklar `hat/ayar_alan.py`): bilinmeyen anahtar (yazım hatası; `sayfalama`,
`kimlik`, `dosya` ve `dataiku` bloklarının içinde de), bilinmeyen sistem ya da kaynak, eksik
kaynak, geçersiz yöntem, yöntemin gerektirdiği alanın eksikliği, sayfalama türünün gerektirdiği
alanın eksikliği, geçersiz `sayi_bicimi`, sistemin kaynaklarında olmayan `deger_eslemesi` alanı
ve depodaki yer tutucu adresin (`...-ADRESI-BEKLENIYOR`) değiştirilmeden `api` yöntemine
geçilmesi geceyi başlatmaz; hata hangi anahtarda olduğunu söyler. Yazım hatası sessizce
"bekliyor" sayılmaz. Ayar dosyasında aynı düzeyde iki kez yazılmış anahtar da hatadır (JSON
okuyucu ilk bloğu sessizce atardı).

**Bir sistemi bağlamak (ör. çekirdek sistem API'si geldiğinde):**

1. `kaynaklar_ek.json`'a sistemin bloğu yazılır: `yontem`, `api.adres_koku`, `api.kimlik`
   (gizli değerin **adı**), `api.sayfalama` bloğunun tamamı ve gerekiyorsa `api.kayit_yolu`.
   Depodaki sayfalamada ilk sayfa numarası (`baslangic`) bilerek yoktur: API ilk sayfayı 0 mı
   1 mi sayıyor, servis belgesinden yazılır (yanlış seçim ilk sayfayı sessizce atlardı).
2. Kaynakların yolu depodaki varsayılandan farklıysa her kaynak için `kaynaklar.<ad>.api.yol`;
   alan adları sözleşmedekinden farklıysa `kaynaklar.<ad>.alan_eslemesi`; kod değerleri
   farklıysa (ör. branş `Trafik`) `deger_eslemesi`.
3. Gizli değerin kendisi Dataiku'da Profil > Ayarlar > Gizliler'e aynı adla girilir.
4. `aktarim_kontrol.py` 3. hücresi her kaynağın etkin yöntemini (veri kümesi adı; API'de
   gizlinin adı ve tanımlı olup olmadığı; adres yazılmaz, çıktı paylaşılabilir kalsın), 6.
   hücresi her kaynağın kuru okumasını gösterir: kaynak bir kez okunur, kalite denetiminden
   geçer, hiçbir yere yazılmaz.

Şirkete ya da iç sistemlere özgü bilgi (adres, alan adı, sistem adı) yalnız ek dosyaya yazılır;
depoya girmez. API'nin biçimi (sayfalama türü, kayıt yolu) kesinleşip depodaki varsayılan
güncellenirse şirkette yalnız `kaynaklar.json` yeniden yapıştırılır; ek dosya aynen kalır.

Her kaynak her gece **tam görüntü** vermelidir: yalnız değişen kayıtlar değil, o anki bütün
kayıtlar. Esasın ilk görüldüğü gün ve satır sayısı denetimi buna dayanır; artımlı (yalnız
değişenler) çekim ilk görülme gününü ve hesapları bozar.

Yöntemi `dataiku` olan kaynakta kimlik alanları (dosya no, avukat kodu) veri kümesi
şemasında **metin** olmalıdır. Kütüphane Dataiku veri kümesini şema türleriyle okur; şemada
sayı olarak tanımlanmış `000123` gibi bir dosya numarası baştaki sıfırlarını kaybeder.

Zorunlu kaynaklar: `dosya` (çekirdek sistem rücu dosyası) ve `atama_log` (çekirdek sistem avukat
logları). Bunlar gelmeden hesap yapılmaz; bu gecelerde gözlem tabloları da güncellenmez, dava takip
sistemi zorunlu kaynaklardan önce bağlanırsa ilk görülme günü ilk başarılı geceden başlar.
Diğerleri geldikçe ilgili sütun açılır: dosya bazında tarihli tahsilat hareketi
(`tahsilat_hareketi`) gelince Tahsilat, değerlendirme sistemi gelince Hukuki Kalite ve Davranış,
dava takip sistemi gelince Süre. Tahsilat hareketi gelmezse yalnız Tahsilat sütunu ve tahsilat
tabloları "kaynak bekleniyor" kalır (rapor toplamlarından yedek puan yoktur; mutabakat yapılmaz,
kapıda `TAHSILAT_HAREKETI_YOK` uyarısı); portföy, Kriter 1, Kriter 2 ve kalite/davranış üretilir,
birleşik puan puana giren sütunların hepsini istediği için yayımlanmaz.

### Ortak ayarlar

- `alan_eslemesi`: kaynaktaki alan adını sözleşmedeki ada eşler, ör.
  `{"AV_KOD": "avukat_kodu"}`. Sözleşmedeki adlar aşağıdaki tablodadır. Eşlemeden sonra aynı
  adlı iki sütun kalırsa (kaynakta hem `brans` hem eşlenen `BRANS_KODU` varsa) kaynak okunmaz;
  ileti sütun adını söyler.
- `deger_eslemesi`: kaynaktaki kod değerini sözleşme koduna çevirir, ör.
  `{"brans": {"Trafik": "TRAFIK", "Kasko": "KASKO"}}` ya da `{"alt_baslik": {...}}`,
  `{"surec_turu": {...}}`. Eşlemede olmayan değer olduğu gibi kalır; branşta bilinmeyen değer
  geceyi durdurur (aşağıda). Değerlendirme sistemi çalışma durumunu E/H verirse
  `{"calisma_durumu": {"E": "DEVAM", "H": "AYRILDI"}}` yazılır; arayüz değişmez
  (`tests/test_arayuz_inceleme.py::test_calisma_durumu_kaynak_degeri_eslenir`).
- `tarih_bicimi`: metin tarih biçimi, ör. `"%d/%m/%Y %H:%M:%S"`. Biçime uymayan değer (ör.
  saati düşmüş `01/02/2024`) metin kalır ve kapıda durdurulur; ay-gün sırası tahmin edilmez.
  Boşsa yalnız ISO biçimi
  (`2026-11-19`, saatli ya da saat dilimli olabilir) kabul edilir. Gün/ay sırası ve sayı
  olarak gelen tarih (epoch) tahmin edilmez: `05.11.2026` gibi bir değer biçim verilmeden
  kalite kapısında "çevrilemeyen değer" olarak durdurulur. Kural sütunun pandas türünden
  bağımsızdır (`object`, `string`, `category`; pandas 3'te metin varsayılan olarak `string`).
- `sayi_bicimi`: `"tr"` ise metin olarak gelen `1.234,56`, `"en"` ise `1,234.56` çevrilir
  (yalnız kalıba uyan metin); sayı olarak gelen değer (JSON sayısı, Dataiku double) olduğu gibi
  kalır. Değer `null`, `tr` ya da `en` olur. Bu ayar verilmeden Türkçe ya da belirsiz biçimli
  metin (`12.000`, `45,678`, `1.234`: binlik mi ondalık mı) gelirse kapı durdurur; ileti
  kaynağın biçiminin teyit edilmesini ister (yanlış seçim tutarı bin kat değiştirirdi).
- `genis_degerlendirme`: değerlendirme sistemi alt başlık başına sütun verirse `{"Alan adı": "alt_baslik_kodu"}`.
  Eşlemedeki bir sütun yanıtta yoksa (henüz puanlanmamış alt başlık, null alanı yazmayan API)
  o alt başlık puanlanmamış sayılır; eşleme sütunlarının hiçbiri yoksa kaynak okunmaz.

### API

Sistem bloğunda ortak kısım, kaynak bloğunda yalnız yol:

```json
"sistemler": {"cekirdek": {"yontem": "api", "api": {
  "adres_koku": "https://servis/rucu",
  "http_yontemi": "GET",
  "basliklar": {"Accept": "application/json"},
  "sorgu": {"durum": "tum"},
  "kimlik": {"tur": "bearer", "gizli": "API_CEKIRDEK_ANAHTARI"},
  "sayfalama": {"tur": "sayfa", "sayfa_parametresi": "page", "boyut_parametresi": "size",
                "boyut": 1000, "baslangic": 1, "toplam_yolu": "meta.total"},
  "kayit_yolu": "data",
  "zaman_asimi_sn": 60, "deneme": 3, "bekleme_sn": 2
}}},
"kaynaklar": {"dosya": {"api": {"yol": "/dosyalar"}}}
```

- `kimlik.tur`: `yok`, `bearer`, `basic` (gizli değer `kullanici:sifre`), `baslik`
  (`baslik_adi` ile özel başlık), `sorgu` (anahtarı adres sorgusunda isteyen API; `parametre`,
  ör. `api_key`: anahtar `sorgu` bölümüne yazılmaz, gizliden eklenir), `oauth2` (istemci kimlik
  bilgileriyle jeton; `jeton_adresi`, gizli değer `istemci_kimligi:istemci_sirri`, isteğe bağlı
  `kapsam`). Tür ve türün gerektirdiği alanlar gece başlamadan doğrulanır. `sorgu` türünde
  anahtar adreste taşındığı için hata iletisinde maskelenir (`***`); ileti çalışma kaydına ve
  izleme panosuna bu hâliyle yazılır. API adresi `http://` ya da `https://` ile başlamalı,
  boşluk içermemelidir (doğrulama denetler).
- `kimlik.gizli`: anahtarın kendisi değil, **Dataiku kullanıcı gizlisinin adıdır**
  (Profil > Ayarlar > Gizliler). Anahtar hiçbir dosyaya yazılmaz.
- `sayfalama.tur`: `yok`, `sayfa` (`sayfa_parametresi`, `boyut_parametresi`, `baslangic`: ilk
  sayfanın numarası, 0 ya da 1, açıkça yazılır), `ofset` (`ofset_parametresi`,
  `boyut_parametresi`), `imlec` (`imlec_parametresi`, `sonraki_imlec_yolu`). Türün gerektirdiği
  alan ve bilinmeyen anahtar (ör. `toplam_yol`) gece başlamadan yakalanır. Okuma boş sayfada ya da imleç bitince biter;
  sunucu sayfa boyutunu kısıtlayabildiği için kısa sayfa son sayılmaz. İmleç alanı dolu bir
  sayfada yanıtta yoksa okuma hata verir (yol yanlış yazılmıştır). Yanıtta toplam KAYIT sayısı
  varsa `toplam_yolu` verilir: okuma sonunda okunan kayıt sayısıyla karşılaştırılır, tutmazsa
  hata (ör. toplam sayfa sayısını gösteren alan). Son sayfadan sonrasını isteyince hata veren
  sunucuda ayrıca `"toplam_ile_dur": true`. Aynı sayfa ya da imleç yeniden gelirse okuma durur.
  Sayfalı API tekil bir alana göre kararlı sıralama vermelidir (ofset sayfalamasında okuma
  sırasında değişen liste kaydı çift saydırabilir).
- `http_yontemi`: `GET` ya da `POST`.
- `ca_dosyasi`: kurum içi sertifika otoritesi kullanılıyorsa sertifika dosyasının Dataiku
  sunucusundaki yolu; boşsa sistemin sertifikaları kullanılır.
- `kayit_yolu`: yanıtta kayıt listesine giden noktalı yol (ör. `data.items`); sayısal parça
  liste indeksidir (`results.0.rows`); anahtar nokta içeriyorsa liste biçiminde yazılır
  (`["@odata.value"]`). Boşsa yanıtın kendisi liste olmalıdır. Yol yanıtta yoksa ya da liste
  göstermiyorsa okuma hata verir (sessizce boş dönmez); yalnız açık `null` boş sayılır. İç içe
  alanlar düzleştirilir (`ic.tutar` gibi), eşleme o adla yapılır.
- `adres_koku` sonundaki ve `yol` başındaki `/` önemsizdir; kaynağın tam adresi farklıysa kaynak bloğunda
  `api.adres` verilir (kök kullanılmaz). Sistem bloğunda `api.adres` verilmez: bütün kaynaklar
  aynı adrese giderdi, doğrulama durdurur.
- Sorgu ve gövdede `{kesit}` ve `{cekim_tarihi}` yer tutucuları kullanılabilir (`hat/okuma.baglam`).
  Önceki çekimin tarihi sunulmaz: kaynak her gece tam görüntü verir.
- 5xx, 429 (`Retry-After` başlığına uyarak) ve bağlantı hataları (kopan bağlantı dahil) artan
  beklemeyle yeniden denenir; diğer hatalarda o gece durur ve `calisma_kaydi`'na hata türü
  yazılır. OAuth2 jetonu okuma sırasında süresi dolarsa (401) bir kez yenilenir; jeton ucu da
  aynı durumlarda (5xx, 429, zaman aşımı, bağlantı hatası) yeniden denenir. Kimlik başlığı yönlendirmede başka adrese gönderilmez.


### Sözleşmedeki alanlar

`*` zorunlu alan. Tür: metin, sayı, tarih, zaman (saatiyle; aynı günün atama kayıtlarını
sıralar: kaynak yalnız gün verirse aynı gün yeniden atamada sıra bilinmez, kapı
`SAATSIZ_ATAMA` uyarısı verir). Tablo `avukat_perf/sema.py` ile testle aynı tutulur.

| Kaynak | Alanlar |
|---|---|
| `dosya` | dosya_no\*, brans\*, rucu_kodu\*, rucu_tutari\* (sayı), acik_bakiye (sayı), rucuya_verilis_tarihi\* (tarih) |
| `atama_log` | dosya_no\*, avukat_kodu\*, atama_tarihi\* (zaman, saatiyle), iptal_tarihi (zaman, saatiyle), atama_ref, grup, tipi |
| `takip` | dosya_no\*, takip_tipi, esas_no, mahkeme, islem_tarihi (tarih) |
| `tahsilat_hareketi` | dosya_no\*, hareket_tarihi\* (tarih), tutar\* (sayı), hareket_turu, hareket_no |
| `rapor_avukat_toplam` | avukat_kodu\*, donem\*, tahsilat_toplami\* (sayı), brans |
| `degerlendirme` | avukat_kodu\*, degerlendirme_tarihi\* (tarih), alt_baslik\*, puan (sayı), degerlendiren |
| `avukat` | avukat_kodu\*, unvan, calisma_durumu |
| `esas_goruntu` | dosya_no\*, esas_no, kaynak_tarihi (tarih) |
| `k2_goruntu` | dosya_no\*, surec_turu, baslangic_tarihi (tarih), dava_esas_no, dava_kaynak_tarihi (tarih) |
| `bekleme` | dosya_no\*, avukat_kodu\*, baslangic\* (tarih), bitis (tarih) |

`rapor_avukat_toplam.donem` biçimi `YYYY-AA`, `YYYY-AA-GG`, `YYYYAA` ya da `AA.YYYY`
olabilir (saatli tarih yerel güne çevrilir); başka biçim eşleşmez ve mutabakatta fark olarak
görünür. Rapor `brans` kırılımıyla gelirse mutabakat ay toplamını karşılaştırır.
`tahsilat_hareketi.hareket_no` kaynağın tekil hareket kimliğidir: verilirse aynı numaralı iki
hareket kapıda durdurulur (`YINELENEN:hareket_no`). `atama_log` tarihleri saatiyle istenir.

Sistemler arası eşleştirme avukat koduyla yapılır; ad ve soyad kullanılmaz.

## Gecelik ve dönem sonu çalışma

- **Gecelik:** çekim → ham arşiv (MinIO, değiştirilmez) → kalite kapısı → ortak model →
  puanlar → sonuç veri kümeleri. Herhangi bir kaynakta kalite kapısı geçmezse o gece hesap
  yapılmaz, son geçerli sonuç korunur, alarm üretilir. Aynı gece ikinci çalışma aynı sonucu
  verir; çift kayıt oluşmaz. Bütün yazımlar hesap bittikten sonra yapılır; sonuc_ ve model_
  tabloları çalışma kimliğiyle etiketlenir. Arayüz ve dönem sonu yalnız son başarılı gecenin
  kimliğini taşıyan tabloyu kullanır: yazımı yarıda kesilen bir gecenin tabloları başka bir
  geceninkilerle yan yana gösterilmez. Hiç başarılı gece yoksa (ilk gece yarıda kaldıysa) hiçbir
  sonuç gösterilmez ve dönem sonu yayın yapmaz. Gözlem ve olay tabloları en son yazılır;
  `bayrak_olay` satırlarından yalnız başarılı gecelerde yazılanlar okunur, kalan gecenin
  olayları bir sonraki başarılı gecede yeniden yazılır. Gece kaydının `uretilen` alanı her
  tablonun yazılan satır sayısını tutar; ekran yalnız o sayıyla tutan tabloyu gösterir.
- **Gözlemler (ilk görülme günü):** dava takip esası (`gozlem_esas`), çekirdek sistemin takip
  bilgisi (`gozlem_esas_yedek`), dava esası ve Kriter 2 koşulu ayrı tablolardadır. Yedek yoldan
  sabitlenen tarih dava takip sistemi bağlanınca kullanılmaz; o sistemin gözlemi kendi ilk
  görüntüsünden kurulur. Bayrak olayı da esasın kaynağını taşır (`esas_kaynagi`: `dava_takip`
  ya da `yedek`; sütunu olmayan eski satır `dava_takip` sayılır): yedek yolun olayları kayıtta
  kalır ama çelişki aramasına ve Süre Takibi'ne yalnız dönemin bugünkü kaynağındaki olaylar
  girer. Gözlem kaynağının (esas, süreç, takip görüntüsü) boş gelmesi ve daha
  önce dolu gelmiş isteğe bağlı bir kaynağın boş gelmesi geceyi durdurur. Tablo dolu gelip
  değer alanı (esas no; süreç türü ve dava esası) hiçbir satırda dolu değilse de gece durur
  (`DOLULUK`): alan eşlemesi yanlış ya da alan gelmiyordur; gece geçseydi ertesi gece bütün
  değerler o gün "ilk görülür", haksız düşüm doğardı. Kaynakta gerçekten veri yoksa (ör. takip
  bilgisinde esas no hiç doldurulmuyorsa) o kaynağın yöntemi `bekliyor` yapılır. Takip
  bilgisinde dosya başına birden çok satır (icra, dava) uyarıdır; gözleme esası dolu satırlar
  içinde işlem tarihi en erken olan girer (açık karar, Parametreler ve açık kararlar).
- **Yalnız eklenen tablolar:** gözlem, `bayrak_olay`, `calisma_kaydi`, `puan_donem` ve
  `birlesik_donem` her çalışmada baştan yazılır. Okunan tablo son başarılı çalışmanın yazdığından
  azsa (kesik yazım, elle temizleme) çalışma `VERI_KAYBI` ile durur ve üzerine yazmaz. Ne
  yapılır: Dataiku'da veri kümesinin geçmiş sürümü ya da yedeği geri yüklenir; geri
  yüklenemiyorsa durum proje sorumlusuyla değerlendirilir (gözlem tabloları ham arşivden yeniden
  kurulabilir). Bir veri kümesi elle temizlenmemelidir. Beklenen satır sayısı tablonun son
  yazıldığı başarılı çalışmadandır: araya o tabloyu yazmayan bir gece (ör. kaynağı beklenen
  gözlem) girse de denetim sürer. `calisma_kaydi` boş okunurken bu tablolardan biri doluysa da
  gecelik ve dönem sonu çalışma kayda yazmadan `VERI_KAYBI` ile durur: kayıt kaybolmuştur, hat
  ilk geceymiş gibi sürmez (gölge düşümleri canlı sayılırdı). Kayıt geri yüklenir.
- **Gölge ve canlı geceler:** her başarılı gece, önceki gecenin çekim gününden sonraki günleri
  kendi çekim gününe kadar kapsar (ilk gece öncesini de). Gölge kriter bazındadır: parametreyle
  açılan gölge mod iki kriteri, yedek yolun zorunlu gölgesi yalnız Kriter 1'i kapsar. Gölge
  gecesinin kapsadığı günlerdeki o kriterin düşümü avukata bildirilmediği için puana girmez; ekranda "Gölge
  döneminde, puana girmez" yazar. Canlı gecelerin düşümü, araya sonradan gölge gecesi girse de
  sayılmaya devam eder. Dönem sonu, dönemi kendi kesit gününün gölge ya da canlı durumuyla
  hesaplar ve sürümler: gölge modu sonradan açmak ya da kapatmak yayımlanmış dönemi değiştirmez.
- **Aynı gün yeniden çalıştırma:** gözlem tabanı bu çalışmadan önce başlamış son başarılı
  çekimdir. 02:00 çekiminde olmayıp 10:00'daki yeniden çalışmada görülen değer gün içinde
  girilmiştir; ilk görülme günü o gündür.
- **Haklı bekleme:** kaynak bir kez okunduktan sonra bağlantısı kaldırılırsa Kriter 1
  hesaplanmaz (beklemesiz düşüm haksız olurdu); boş gelirse gece durur.
- **Süre puanı:** Kriter 1 ve Kriter 2'nin ikisinin de kaynağı bağlıyken üretilir. Biri eksikse
  süre sütunu "kaynak bekleniyor" olur (Süre puana giriyorsa birleşik puan da yayımlanmaz);
  eksik kriterle puan hesaplanmaz. Esas bilgisi dava takip sistemi yerine çekirdek sistemin takip bilgilerinden
  geliyorsa (yedek yol) Kriter 1 parametreden bağımsız gölge modda çalışır: Kriter 1 e-postası
  gönderilmez, süre puanı yayımlanmaz. Kriter 2'nin verisi yedek yola bağlı olmadığından Kriter 2
  canlı kalır: e-postası gönderilir, düşümü sonraki canlı gecelerde puana girer. Dava kaydı olup ilk giriş günü bilinmeyen (arşiv öncesi)
  dönem Kriter 2'de ölçülmez.
- **Dönem sonu:** bir önceki ay, ayın son günü kesitiyle hesaplanır ve sürümlü yayımlanır.
  Birleşik puan ve not yayın anında, o günün kurallarıyla hesaplanıp sürümüyle saklanır;
  sonradan ağırlık ya da not eşiği değişse de yayımlanmış dönem değişmez. Bir dönem yeniden
  hesaplatılırsa (proje değişkeni `donem`) ve içerik ya da kurallar değiştiyse yeni sürüm
  eklenir; Not Geçmişi son sürümü ve sürüm numarasını gösterir. Değişkeni silmek unutulsa da
  yeni ay yayımlanır. Ay sonunu kapsayan başarılı bir gecelik çalışma yoksa yayın yapılmaz.
  Yayımlanmayan her çalışma da `calisma_kaydi`'nda `DONEM_SONU` satırıyla görülür: kontrol
  geçmediyse (`KALDI`), son gecenin yazdığı bir model ya da gözlem tablosu (isteğe bağlı
  olanlar dahil) okunamıyor ya da kesikse (`KALDI`, `VERI_KAYBI`; denetim `MODEL_TABLOSU`) ve
  hesap ya da yayın hata verdiyse (`KALDI`, `HESAP_HATASI`) nedeni `kalite_sonucu`'nda aynı
  çalışma kimliğiyle de yazılır; zorunlu model tablosu hiç yazılmadıysa durum
  `KAYNAK_BEKLENIYOR`'dur ve nedeni yalnız kaydın açıklamasındadır. Yayın yapılıp kayıt
  yazıldıktan sonraki bir hata yayının kaydını `KALDI`'ya çevirmez.
  Dönem sonu yalnız son başarılı gecede üretilmiş girdileri kullanır. Önce `puan_donem` (yayının
  kendisi), sonra `birlesik_donem` yazılır: Not Geçmişi yayımlanmamış bir sürümü göstermez.
  İkinci yazım yarıda kalırsa senaryo yeniden çalıştırılınca eksik birleşik sürüm, yayımlanan
  sürümün kendi satırları ve bilgileriyle tamamlanır. Hazırlık kuralı (`hazirlik` bölümü,
  `kriter2.rucu_kodu`) ya da kod son gecelik çalışmadan sonra değiştiyse dönem sonu yayın
  yapmaz (`HAZIRLIK_SURUMU`); önce gecelik senaryo çalıştırılır.
- **Kapı kalırsa:** ayrıntı `kalite_sonucu` veri kümesinde ve Veri Durumu sayfasındadır.
  Satır sayısı meşru olarak sıçradıysa (ör. kaynakta geçmiş veri yüklendi) kapı kendiliğinden
  açılmaz: `kalite.satir_sapma_orani` bir gece için yükseltilir, gece geçince eski değerine
  döndürülür. Gece hesap aşamasında hata verirse `calisma_kaydi`'na `HESAP_HATASI` ile
  yazılır ve senaryo başarısız olur; hata iletisi senaryo günlüğündedir.
- **Kapının alan ve ilişki denetimleri** (`avukat_perf/kalite_alan.py`, `kalite_iliski.py`):
  branş `kalite.bilinen_branslar`'da yoksa gece durur (yazım farkı oto eşiğini ve olgunluk
  süresini sessizce değiştirirdi; kaynak kodu `deger_eslemesi` ile çevrilir, yeni branş listeye
  eklenir). Hareket türü süzgeci (`hazirlik.tahsilat_hareket_turleri`) verilmişse listede olmayan
  hareketler ve aralarındaki eksi tutarlı (ters kayıt) hareketler sayılıp uyarılır; hiçbir hareket
  listeye uymuyorsa gece durur. Değerlendirmede alt başlıklarda ve mevcut alanlarda olmayan kod
  uyarı (hiçbiri tanımlı değilse durur), pencere dışında kalan puanlı satır uyarı, değerlendiren
  doluyken aynı (avukat, gün, alt başlık, değerlendiren) satırı çift kayıttır, durur. Ölçek
  denetimi yalnız tanımlı alt başlıklara uygulanır (hesapla aynı kural); mevcut alanlar kendi
  ölçeğindedir. Kaynaklar arası anahtar ilişkisinde eşleşmeyen oranı
  `kalite.iliski_en_cok_yetim_orani`'nı aşarsa (tahsilat hareketinde tutarla da tartılır) ya da
  hiçbir anahtar eşleşmiyorsa gece durur, altında uyarıdır; değer ilk gerçek çekimde ölçülerek
  belirlenir (teyit bekliyor). Haklı beklemenin (dosya, avukat) çifti ve avukat listesi atama
  loguyla karşılaştırılır; yalnız tümden uyuşmazlıkta durur. Tahsilat raporuyla mutabakatta kesit
  ayının (kısmi ay) farkı uyarıdır: rapor ve hareketler farklı saatlerde yenilenebilir. Ayın 1'i
  gecesinde biten ay kesit ayı değildir; farkı geceyi ve dolayısıyla o ayın dönem yayınını durdurur.

### Zamanlayıcı

Tek zamanlayıcı kullanılır. Varsayılan Dataiku senaryosunun zaman tetikleyicisidir. Kurum
standardı Airflow'u zorunlu kılarsa kod değişmez: iki senaryonun zaman tetikleyicisi kapatılır,
Airflow'da her senaryo için tek görev senaryoyu Dataiku API'siyle çalıştırır ve sonucunu bekler.
Senaryo başarısızsa görev de başarısız olur.

```python
import dataikuapi
from airflow.hooks.base import BaseHook

baglanti = BaseHook.get_connection("dataiku")  # adres ve API anahtarı Airflow bağlantısında durur
istemci = dataikuapi.DSSClient(baglanti.host, baglanti.password)
istemci.get_project("AVUKAT_PERF").get_scenario("AVUKAT_PERF_GECELIK").run_and_wait()
```

İki zamanlayıcı birlikte açık bırakılmaz; aynı gece iki çalışma çift kayıt üretmez ama gereksiz
çekim yapar. Dönem sonu görevi gecelik görevden sonra çalışmalıdır.

### İzleme

Operasyonel izleme Grafana'dadır ve `calisma_kaydi` ile `kalite_sonucu` veri kümelerini SQL'den
okur (`grafana/README.md`). Hat ayrı bir ölçü ucu açmaz; Prometheus gerekmez. Kurum alarmları
Prometheus Alertmanager üzerinden yönetiliyorsa Grafana alarmının bildirim kanalı oraya
yönlendirilir.

## Arayüz

Masaüstü öncelikli; 1024–1920 genişlikte sayfa yatay kaymaz, geniş tablolar kendi kartı içinde
kayar (tarayıcıda dört genişlikte ölçüldü). Sol menü üç grupta: Genel (Genel Bakış), Performans
(Avukatlar, Süre Takibi), Sistem (Puanlama Kuralları, Veri Durumu). Genel Bakış Özet, Sıralama,
Dağılımlar, Tahsilat ve Portföy; Süre Takibi Özet, Dönemler, Uyarı ve olaylar bölümlerine
ayrılır. Sayfa, bölüm, avukat ve kart sekmesi adres çubuğunda durur (`#genel/siralama`,
`#avukat/AV-08/tahsilat`): tarayıcının geri ve ileri tuşları çalışır, adres paylaşılabilir.
Bölüm sekmesine tıklama geçmişe girer, ok tuşlarıyla gezinti girmez; geçersiz bölüm adresi
(`#genel/xyz`) düzeltilir. Tablolarda sütun başlığına tıklayınca sıralanır; uzun tablolarda tek
sekme durağı vardır, satırlar arasında ok tuşlarıyla gezilir. Avukat kartı sekmelidir: Özet,
Tahsilat, Süre, Kalite ve Davranış, Not Geçmişi. Avukat başlığındaki "Neden bu puanı aldı?"
paneli önce birleşik puanı neyin düşürüp yükselttiğini tek cümleyle, sonra her sütunun puanını,
beklenen düzeye göre etkisini (ağırlık × (puan − taban); toplamları birleşik puan − tabandır, en
büyük kalanla yuvarlanır) ve tek cümlelik nedenini gösterir; formül adımları "Hesap adımlarını
göster" düğmesinin arkasındadır (`avukat_perf/aciklama_ozet.py`). Kart açıklamaları başlığın
yanındaki bilgi simgesindedir; sayfada yalnız veriyle değişen özet ve uyarılar yazılı durur. Bir sütun kaynak ya
da teyit beklediğinde Genel Bakış birleşik puanın neden hesaplanmadığını söyler. Gölge kriter
bazındadır: seviye rozetleri, bayrak şeridi, süre dağılımı ve notlar satırın kriterine göre nötr
renkte ve "bilgi amaçlı" notuyla gösterilir; zil sayacı ancak iki kriter de gölgedeyse nötrdür.
Hiç sonuç yoksa sayfa, kartlar yerine tek bir açıklama ve Veri Durumu bağlantısı gösterir.
Sayfa başlığındaki "Excel" ve "CSV" düğmeleri bulunulan sayfanın seçili bölümünde (avukat kartında
seçili sekmede) görünen tabloları indirir: başlıklar ve hücreler ekrandaki gibi, sayılar sayı olarak; arama ve süzgeçle
gizlenen satırlar girmez. Excel dosyası tarayıcıda, harici kütüphane olmadan kurulur. Dataiku
görünümünde indirme engellenirse web uygulaması yeni sekmede açılır. Tarayıcının yazdırması
(Ctrl+P) sayfayı menüsüz, bütün bölümleriyle basar. Avukatlar sayfasında liste avukat koduyla
aranır (AV-08, av08 ve 08 aynı avukatı bulur; Enter ilk sonucu açar).

- Puanlar iki ondalıkla gösterilir; birleşik puan ve not bu hassasiyette hesaplanır, ekrandaki
  sayı ile not her zaman tutarlıdır. Dağılım kutuları ve yüzdelikler de ekrandaki iki ondalıklı
  (yarım yukarı) puanla sayılır: "80,00" görünen puan 75–80 kutusuna düşmez.
- Gecelik puan ile dönem yayını ayrıdır: gecelik birleşik puanın durumu ekranda "Hesaplandı",
  sayısı "Puanı hesaplanan N / M"dir; "Yayımlandı" yalnız Not Geçmişi'nde (değişmeyen aylık
  dönem yayını) geçer. Not süzgecinde notu olmayanlar "Hesaplanmadı" diye seçilir.
- Üst şerit yalnız uyarı gösterir: veri okunamadı (ipucunda okunamayan tabloların adları),
  parametre dosyası geçersiz (gece bu dosyayla başlamaz; hatalar Puanlama Kuralları'nda), gölge
  mod (kriter bazında: yedek yol gecesinde "Kriter 1 · İlk işlem" gölgede, Kriter 2 canlı),
  "Kurallar değişti" (parametreler ya da hesap kodu son başarılı geceden sonra değiştiyse;
  ekrandaki sonuçlar ilk gecelik çalışmaya kadar önceki kurallarla hesaplanmış durumdadır), son
  gecelik çalışmanın kalması ve dönem yayınının kalması (son dönem sonu çalışması `KALDI`).
  Şeridin kesiti, gölge durumu ve hesap sürümü ekrandaki tabloları seçen tanımla aynı geceden
  gelir (`hat.gecmis.son_basarili_gece`). Odaklanan rozetin açıklaması ekran okuyucuya da
  gider. Kesit, son güncelleme ve hesap sürümü yalnız yazdırılan çıktıda yer alır; kesit son
  başarılı gecelik çalışmanındır. Sonuçla birlikte gösterilen kural bilgisi (tutar bandı adları,
  sütun ağırlıkları, Süre Takibi listesinin düşüm penceresi, yeterlilik için gereken alt başlık
  sayısı, Kriter 1 eşik günleri) hesap anında sonuç tablosuna yazılır; ekran bunları güncel
  parametreden üretmez. Yalnız Puanlama Kuralları sayfası güncel parametreyi gösterir.
- Geçersiz parametre: web uygulaması parametreyi gecenin kuralıyla (`params.dogrula`) doğrular;
  Puanlama Kuralları sayfasının başında hata listesi çıkar, ağırlık ve not kartları hesaplanmaz.
  Bilinmeyen sayfa adı HTTP 400 ve sabit ileti döner (girdi yanıta yansımaz); başka hata
  Flask'ın 500'üdür.
- Okuma kesintisi: arka uç bir tabloyu okuyamazsa önbellek beş dakika yerine 15 saniye
  (`backend.py` → `YENIDEN_SN`) tutulur, sonra yeniden okunur; şerit "Veri okunamadı" der ve boş
  sayfa açıklaması bunu kurulum günü gibi anlatmaz. Günlüğe hata türü ve iletisi yazılır.
- Eski biçimli sonuç tablosu: sözleşmenin okuduğu bir sütunu taşımayan `sonuc_`, `model_` ve
  `birlesik_donem` tablosu (kod aktarımından sonraki ilk geceye kadar) gösterilmez; sayfalar
  açılır, o bileşen "henüz üretilmedi" der. Kural tektir (`arayuz/temel.guncel_tablolar`);
  bileşen başına sütun koruması yoktur. İstisna: gruplamaya bağlı grup sütunları (`brans`,
  `yas_bandi`, `yas_etiketi`, `tutar_bandi`, `bant_etiketi`) `tahsilat.gruplama`'da olmayan boyut
  için yazılmaz; bunlar `sozlesme_tahsilat.SECIMLIK_SUTUNLAR`'dadır ve eksiklikleri tabloyu eski
  biçim yapmaz (yoksa yaş bandısız gruplamada Tahsilat oranı göstergesi ve Tahsilat Karşılaştırma
  Grupları kartı boşalırdı).
- Tahsilat hareketi bekleniyor: dosya bazında tahsilat hareketi bağlanmadıysa tahsilat
  bileşenleri (Genel Bakış'ın aylık, yıllık, aylık avukat, gruplar, saçılım ve kutu grafiği;
  avukat kartının tahsilat, branş ve aylık kartları) başlıklarıyla kalır, gövdede "Kaynak
  bekleniyor" der; Tahsilat oranı göstergesi de aynısını söyler. Hiçbir tablo ya da grafik
  kaldırılmaz. Kurulum günü sayfa açıklamasında zorunlu kaynaklar yalnız dosya ve atama
  loglarıdır.
- Mantıksal sütunlar: Dataiku boş değerli mantıksal sütunu metin okur ("true"/"false"); sunum ve
  gölge okuması tek çözücüyle yapılır (`avukat_perf/mantik.py`: true, 1, E ve evet doğru; boş ve
  başka her şey yanlış).
- Tarayıcı: Chrome ya da Edge (Chromium tabanlı, 2020 ve sonrası). Internet Explorer ve Edge'in
  IE modu desteklenmez. Yazı tipi ve kitaplık internetten yüklenmez (sistem yazı tipleri); kurum
  ağında çalışır.
- Genel Bakış sıralama tablosu `arayuz/sunum_siralama.py`'de hazırlanır. "Gerç./Bekl." sütunu
  (`gerceklesen_beklenen`) aşağı kesilerek yazılır: %99,6 kırmızı "%99" görünür, "%100" değil.
- Avukat kartındaki Tahsilat Performansı kartı tahsilat puanını ve üç bileşenini (tutar, sıklık,
  güncellik; her biri gerçekleşen / beklenen dayanağıyla) gösterir. Tahsilat sekmesindeki branş
  tablosu her branş için olgun dosya, rücu tutarı, tahsilat, tahsilat oranı ve beklenen oran,
  dosya başına tahsilat, üç bileşen ve branş puanını, son satırda avukatın bütün dosyalarını verir.
- Genel Bakış'ın Tahsilat bölümünde avukatları yan yana gösteren aylık tahsilat tablosu (son 12
  ay; açılışta son 12 ayın toplamına göre azalan, avukata yazılmayan en altta; sütun başlığıyla
  yeniden sıralanır) ve karşılaştırma grupları (`tahsilat.gruplama`; grup tahsilat oranı ve
  dosya-yıl başına tahsilat ayı; gruplamada olmayan boyutun sütunu gösterilmez) vardır.
- Genel Bakış'taki Yıllık Tahsilat tablosu avukat başına son üç takvim yılını
  (`tahsilat.yillik_yil_sayisi`) gösterir; içinde bulunulan yıl kesite kadardır ve önceki yılın
  aynı dönemiyle karşılaştırılır (değer 1 olsa da önceki yıl karşılaştırma için hesaplanır).
- Avukat kartının Kalite ve Davranış sekmesi, yeni alt başlıklar değerlendirme sistemine
  eklenene kadar mevcut dört alanı (`kalite_davranis.mevcut_alanlar`) bilgi amaçlı gösterir:
  sistemin kendi ölçeğinde ortalama, puana girmez. Değerlendirme sisteminin alan adları bu
  kodlara veri hazırlığında eşlenir (`genis_degerlendirme` ya da `alan_eslemesi`).
- Süre Takibi listesi en ağır 500 dönemi gösterir; sayaç filtreye uyan toplamı, avukat seçicisi
  ölçülen dönemi olan bütün avukatları, Son Bayrak Olayları filtreye uyan bütün dönemlerin en
  yeni 30 olayını verir; sayı ve sıra arka uçtadır (`sunum_sure.SON_OLAY`, `son_sira`), aynı
  günün olayları kalıcı anahtarla sıralanır. Seviye seçilince o seviyedeki bütün dönemler
  (kapanan, kapsam dışı ve nedeni) listelenir.
- Veri Durumu'ndaki Düzeltme İncelemesi en yeni 200 çelişkiyi (tespit, olay tarihi, sonra kalıcı
  anahtar sırasıyla) gösterir; başlıkta "En yeni 200 / N çelişki gösteriliyor" yazar.
- Aylık tahsilat grafiği kesitin ayıyla biten `tahsilat.aylik_pencere_ay` takvim ayını gösterir;
  tahsilatsız ay sıfırdır, kesit ayı "kesite kadar" diye belirtilir. Kesitte bitmeyen son ay
  aylık grafiklerin ve aylık avukat tablosunun görünür özetinde de yazılır.
- Tutar ekseninde iki buçukluk adımda etiket iki ondalıkla yazılır (1,25 Mn); yuvarlanınca sıfır
  olan eksi değer işaretsiz gösterilir.
- **Dağılım grafikleri** (veri arka uçta sayılır, `arayuz/sunum_dagilim.py`,
  `arayuz/dagilim_brans.py`, `arayuz/dagilim_sure.py`): Genel Bakış'ta puan dağılımı (sütun
  seçilir; tahsilat ve süre sütununda beklenen düzey çizgisi), tahsilat puanı – olgun dosya
  sayısı saçılımı ve branş bazında gerçekleşen / beklenen oranının kutu grafiği (çeyrekler,
  ortanca, Tukey bıyıkları, aykırı avukatlar; bilgi amaçlı); avukat kartında avukatın her
  sütundaki yeri ve yüzdeliği; Süre Takibi'nde kapanan Kriter 1 dönemlerinin süre dağılımı, oto
  ve oto dışı kural için ayrı panelde, kapanmadan önce ulaşılan bayrağa göre; uyarı ve düşüm
  bölgeleri sonuçtaki eşik günlerinden çizilir.
- **Renkler** yalnız `stil.css` → `:root` değişkenlerinden gelir. Puan taşıyan her öğe (gösterge,
  dağılım kutusu, sıralama çubuğu, saçılım noktası) on puanlık basamaklarla boyanır: 90 ve üstü
  koyu yeşil, 80–90 yeşil, 70–80 sarımsı yeşil, 60–70 sarı, 50–60 turuncu, 40–50 kırmızımsı
  turuncu, 40 altı kırmızı (`--skor-*`). Bu görsel ölçek not ölçeğinden bağımsızdır; not rozetleri
  notun rengini taşır. Bayraklar sarı, turuncu ve kırmızıdır. Puan taşımayan öğeler lacivert
  tonlarındadır. Branş rengi `gorunum.brans_adlari` listesindeki sırayla sıralı paletten gelir
  (`--brans-1` … `--brans-7`, listede olmayan `--brans-bilinmeyen`; bkz. Ekran adları): renk
  koda değil listedeki yere bağlıdır, aynı branş her grafikte aynı renktedir. Sütun renkleri
  `--sutun-*` değişkenlerindedir. Yan menünün rengi `--menu`, seçili menünün solundaki işaret
  `--menu-isaret`.

## Ekran–veri sözleşmesi

Web uygulamasındaki her bileşen sözleşmede tanımlıdır: hangi tablodan, hangi sütunlarla
beslendiği ve ekrana hangi alanları gönderdiği. Sözleşme `arayuz/sozlesme.py` ile
`sozlesme_ortak.py` (ortak şerit, Puanlama Kuralları, Veri Durumu), `sozlesme_dagilim.py` ve
`sozlesme_tahsilat.py`'dir. Ortak bileşenlerden `ortak.adlar` `tur, kod, ad, sira` alanlarını,
`kurallar.hatalar` parametre doğrulamasının hata iletilerini, `veri.celiski_ozet` çelişkilerin
toplamını ve gösterilen sayısını taşır. Testler şunları denetler:

- Hattın yazdığı her sonuç sütunu ya bir bileşende gösterilir ya `sozlesme_dislanan.py`
  içinde gerekçesiyle dışarıda bırakılır.
- Ekrandaki her alan arka uç çıktısında vardır; ekran sözleşme dışı alan isteyemez.
- Arayüz dosyalarında elle yazılmış rakam yoktur; her sayı arka uçtan gelir. Kural görünen
  öznitelikleri de (title, aria-label, placeholder, alt, data-ipucu) kapsar.
- Bir bileşen alanı kaynak tablonun bir sütunuyla aynı adı taşıyorsa bileşen o sütunu okur;
  aynı adın iki ayrı ölçü taşıması yakalanır (`tests/test_arayuz_inceleme.py`).
- Çiziciler veriye yalnız `al(kayit, "alan")` ile erişir; kayda doğrudan erişim ve biçimlendiriciye
  elle yazılmış sayı verilmesi testte yakalanır.

Arka uca yeni bir sütun eklenirse bu iki dosyadan biri güncellenmeden testler geçmez.

## Bilerek yapılmayanlar

Bu sürümde bilerek yapılmayanlar (kapsam büyütülmez; kural ya da kaynak gelince değerlendirilir):

- Pasif dosya, zamanaşımı riski ve iletişim problemi bayrakları: kural tanımı yok.
- Avukat bilgilerinden sözleşme başlangıcı, bölge ve yetkili avukat: kaynak yok. Büro adı unvandan gösterilir.
- Akıllı atama, finansal benzetim, tahmin modeli, uzlaşma hesabı; itiraz süreci, uyarı kapatma ve
  iç avukatlar için yeni veri girişi ya da onay adımı.
- Değerlendiriciler arası fark için istatistiksel düzeltme; tahsilat için ayrı finans kaynağı
  (kaynak tahsilat raporudur).
- Uyarı e-postasının gönderimi: bugün yalnız `sonuc_eposta` listesi üretilir; gönderim yolu ve
  avukat e-posta adresinin kaynağı dava takip sistemi bağlanınca belirlenir.

## Parametreler ve açık kararlar

Eşik, ağırlık ve formül katsayıları `dataiku/degiskenler/params.json` içindedir; `_not`
alanları açıklamadır. Hukuk onayı bekleyen değerler aynı dosyadaki `_teyit_bekleyen`
listesindedir ve "Puanlama Kuralları" sayfasında "Teyit bekliyor" olarak işaretlenir; bir karar
kesinleşince değer ve liste güncellenir (kod değişmez). Karar depoya da işlenecekse
`params.json`'da, yalnız şirkette geçerliyse `params_ek.json`'da yapılır; ekte verilen liste
depodakinin yerine geçer (birleştirilmez). `hesap_surumu` = kitaplık sürümü +
kod özeti + parametre özeti: kod ya da parametre değişince değişir; her sonuç hangi kural
sürümüyle hesaplandığını taşır. Kod özeti `avukat_perf` paketini ve hat'ın sonucu belirleyen
modüllerini (`surum.KOD_DOSYALARI`: akış, dönem akışı, geçmiş, hesap, kaynak okuma ve
normalleştirme, model) kapsar; yalnız okuyan, yazan ya da durduran modüller
(`surum.HAT_GIRIS_CIKIS`) kapsamaz. Parametre özetine `gorunum` (ekran adları) ve `kalite`
(kalite kapısı eşikleri; hiçbir puana girmez) bölümleri girmez: meşru bir sıçramada
`satir_sapma_orani` bir gece yükseltilince "Kurallar değişti" görünmez. Normalleştirmeyi
belirleyen kaynak ayarları (alan ve değer eşlemesi, geniş değerlendirme, tarih ve sayı biçimi)
her çekimde ham arşivin `bilgi.json`'una yazılır.

### Tahsilat puanı

Tahsilat puanı üç bileşenin ağırlıklı toplamıdır (`tahsilat.bilesen_agirliklari`, varsayılan
0,60 / 0,20 / 0,20). Üçü de avukatın gerçekleşenini aynı dosya grubundan beklenene oranlar;
dosya grubu `tahsilat.gruplama`: branş × dosya yaşı bandı (`yas_bantlari`, rücuya verilişten
kesite geçen ay) × tutar bandı (`tutar_bantlari`; başlangıç sınırları 40.000 ve 150.000 TL;
gerçek rücu verisi
üç eşit gruba bölünerek güncellenecek, boş liste tek bant demektir).

| Bileşen | Gerçekleşen | Beklenen | Güven ayarı |
|---|---|---|---|
| Tutar | Olgun dosyalarda avukata yazılan tahsilat | Gruptaki diğer avukatların tahsilat oranı × payla tartılmış rücu tutarı | R = (n × G/B + k) ÷ (n + k), k = `guven_sabiti` |
| Sıklık | Olgun dosyalarda tahsilat yapılan dosya-ay sayısı | Σ elde tutulan süre (dosya-yıl) × gruptaki diğer avukatların tahsilat ayı hızı | R = (O + k) ÷ (E + k), k = `olay_guven_sabiti` |
| Güncellik | Aynısı, son `guncellik_pencere_ay` ayda ve bütün dosyalarla (olgunluk şartı yok) | aynı | aynı |

Sıklık ve güncellik kişi-zamanla ölçülür (dolaylı standardizasyon): dosya-ay, avukata yazılan net
tahsilatı (ters kayıt düşülmüş) yarım kuruştan büyük olan takvim ayıdır; maruziyet avukatın
dosyayı elinde tuttuğu günler ÷ 365'tir ve her gün o günkü dosya yaşının bandına yazılır.

Beklenti (üç bileşende de) aynı gruptaki DİĞER avukatların oranından kurulur
(`avukat_perf/referans.py`; süre puanı da aynı yardımcıyı kullanır): avukatın kendi sonucu kendi
beklentisine girmez, bu yüzden fazla tahsilat puanı hiçbir zaman düşürmez; herkes aynı başarıdaysa
herkes 75 alır. Grupta başka avukat yoksa aynı branştaki, branşta da yoksa bütün diğer avukatların
oranı kullanılır. Tutar bileşeninde diğerlerinin oranı 0 ya da eksiyse (kimse tahsil etmedi, ters
kayıt) ölçüt yok sayılır ve üst katmana geçilir; hiçbir katmanda ölçüt yoksa beklenen sıfırdır
(`BEKLENEN_SIFIR`, puan yok). Sıklık ve güncellikte 0 geçerli bir ölçüttür (o yaş bandında kimseden
tahsilat beklenmez). İki avukatlı grupta her avukat yalnız ötekiyle karşılaştırılır. Üç bileşen
de [rücuya veriliş, kesit] aralığındaki tahsilatı sayar; verilişten önceki tahsilat tutara da
girmez. Rücu tutarı sıfır olan dosyanın tahsilatı sahibinin gerçekleşenine girer, ölçüt oranının
payına girmez (diğer avukatların beklentisini yükseltmez); bu dosyaların evrenden çıkarılması
Hukuk kararıdır (kapıda `SIFIR_RUCU` uyarısı).
Dosyanın el değiştirmesi olay üretmez; dosyayı kısa ya da uzun tutmak tek başına avantaj
değildir. Tahsilatın aylara yayılması ise sıklık ve güncellikte avantajdır: 30 dosyada aynı 300 TL'yi
tek seferde tahsil eden avukat 58,90, on iki aya yayan 85,00 alır (tutar ikisinde 75). Kesitte tahsile kapalı dosyanın süresi kapandığı gün
biter. Kapanış her gece gözlenir (`gozlem_kosul`): rücu kodu `kriter2.kapanis_kodlari`'nda
(varsayılan R06 ve R12, çekirdek sistem ekibinden teyit bekliyor) ya da Kriter 2 rücu kodunda açık
bakiye sıfır ya da eksi. Atama bekleyen ya da iade edilen dosyanın başka kodu kapanış sayılmaz.
Tahsilatta kapanış günü kapanışın görüldüğü çekim günüdür (en geç olası gün: araya kaçan gece
girse de dosyayı kapatan tahsilat sayılır); Kriter 2 bitişi en erken olası günü kullanır. Kapanış
günü bilinmiyorsa (arşiv öncesi) son pozitif tahsilatın ertesi günü, tahsilatı yoksa dosya
sayılmaz. Ters kayıt
yalnız kendi ayını netler; önceki aydaki tahsilatı geri almaz.

Her bileşen kırp(75 + 50 × (R − 1), 0, 100) ve iki ondalığa yuvarlanır; tahsilat puanı
yuvarlanmış bileşenlerin ağırlıklı toplamıdır. Puan en az `en_az_olgun_dosya` (1) olgun dosyada
hesaplanır; olgun dosya `yeterli_olgun_dosya`'nın (10) altındaysa puan geçerlidir, birleşik puana
girer ve ekranda kırmızı "Yeterli veri yok" uyarısıyla gösterilir (sonuçta `yeterli` sütunu).
Branş puanı aynı kuralla avukatın o branştaki dosyalarıyla hesaplanır.

### Süre puanı

O avukatın penceredeki düşüm sayısı, E her risk altındaki dönemi için aynı gruptaki (kriter ×
süreç × branş) DİĞER avukatların düşüm oranının toplamıdır; grupta başka avukat yoksa aynı kriter
ve süreçteki, o da yoksa bütün diğer avukatlar (`avukat_perf/referans.py`). Diğerlerinin düşüm
oranı 0 geçerli bir ölçüttür. R = (O + k) ÷ (E + k), puan = kırp(75 + 50 × (1 − R), 0, 100).
En az bir risk altındaki dönemi olan ve veri kapsamı `en_az_kapsam`'ı (%80) sağlayan avukatın
puanı hesaplanır ve geçerlidir; risk altındaki dönemlerdeki farklı dosya sayısı
`sure_puani.yeterli_dosya`'nın (10) altındaysa sonuçta `yeterli` yanlıştır ve puan "Yeterli veri
yok" uyarısıyla gösterilir (tahsilattaki gibi: Genel Bakış sıralama tablosunda, sütun
kadranında ve avukat kartının süre kartında kırmızı rozet). Pencerede ölçülen Kriter 1 dönemi
olmayan avukatta tarihi bilinmeyen esas da yoktur: kapsam 1 sayılır. Dosya tablosunda olmayan dosyanın
Kriter 1 dönemi ölçülmez (`DOSYA_YOK`; eşik kuralı branşa bağlıdır).

### Sütun ağırlıkları

`agirliklar` Hukuk'un ikili karşılaştırmalarıdır: `"a/b": oran`, a sütunu b sütununun kaç katı
önemli (her çift bir kez, yönü serbest, 1/9 ile 9 arası). Ağırlıklar Analitik Hiyerarşi Süreci
ile hesaplanır (`avukat_perf/agirlik.py`: satır geometrik ortalaması, tutarlılık oranı en çok
0,10, en büyük kalan yöntemiyle tam yüzde). Varsayılan karşılaştırmalar dört sütunda 35 / 30 / 25 / 10
verir (tutarlılık oranı yaklaşık 0); gerekçe `params.json`'daki `_not`'ta.

**İlk faz:** birleşik puana giren sütunlar `birlesik_sutunlar`'dır. Dava takip sistemi verisi
olmadığı için varsayılan `["tahsilat", "kalite", "davranis"]`: Süre ve Performans puana
girmez (Süre Takibi sayfası ve bayraklar bilgi olarak kalır). Ağırlıklar yalnız giren
sütunların karşılaştırmalarından hesaplanır; Süre'nin payı diğerlerine oranında dağılır:
50 / 36 / 14. Giren sütunların hepsi geçerli olmalıdır (`birlesik_puan_kosulu: tum_sutunlar`);
eksik puan sıfır sayılmaz. Süre geri eklenince ağırlıklar yeniden 35 / 30 / 25 / 10 olur. Hesaplanan ağırlık Puanlama Kuralları
sayfasında ve her sonuçta (`sonuc_puan_guncel.agirlik`) görünür.

### Diğer kararlar

`tahsilat.elde_tutma_paydasi` (teyit bekliyor): `ilk_atamadan` avukatın dosyayı tuttuğu günleri
dosyanın ilk atamasından kesite kadarki güne böler; iade sonrası ve iki atama arasındaki boşluk
kimseye yazılmaz (kısa süre tutulup iade edilen dosya beklentiye tam dosya girmez), tek
avukatın tuttuğu dosya 1 sayılır. `avukat_gunleri` önceki yöntemdir.

Bilinen sınırlama: tutar bileşeninde beklenti ilk atamadan sonraki
süre için avukatlar arasında elde tutma payıyla bölünür; rücuya verilişten ilk atamaya kadarki
süre kimseye yazılmaz ama beklentiden de düşülmez. Aynı beceriyle çalışan avukat geç atanan
portföyde tutarda düşük puan alır (beşer avukat, 30'ar dosyada 18 aylık gecikme yaklaşık 15 puan;
tahsilat puanında 0,6 × 15 ≈ 9, birleşik puanda ≈ 2,7: `tests/test_adalet.py`). Sıklık ve güncellik
kişi-zamanla ölçüldüğü için bu etkiyi taşımaz. Gerçek veride tutar R'si ile atama gecikmesi
arasındaki ilişki ölçülmelidir.

`hazirlik.ayni_avukata_yeniden_atama`: dosya araya başka avukat girmeden aynı avukata yeni bir
kayıtla yeniden atanırsa `surer` (varsayılan) dönemi sürdürür; Kriter 1 ve Kriter 2 süresi ilk
atamadan işler, dosyada tek düşüm olur. Gerekçe: süre yalnız başka bir
avukata atamada yeni atama tarihinden başlar ve aynı dosya için bir defalık kesinti yapılır.
`yeni_donem` yeni atama dönemi açar (süre yeni kayıttan başlar, aynı dosyada ikinci düşüm
doğabilir); yalnız Hukuk bunu açıkça isterse seçilir. Sulh amaçlı atama ve `hatali_iptal`
kipinde iptal edilmiş (hatalı) kayıt araya girse de dönem kesilmez; iptal ya da iade ile
oluşan boşluktan sonraki kayıt her iki kipte de yeni dönemdir.

Kriter 2 koşul kaybı arşiv öncesindeyse (ilk gecede dosya zaten kapalı, günü bilinmiyor) ilk
kalkış kalıcıdır: dosya sonra R11'e ve pozitif bakiyeye dönse de dönemler `KOSUL_SAGLANMIYOR` ile
ölçülmez, günü bilinen kayıpla aynı kural. Yeniden açılan dosyanın nasıl ölçüleceği açık karardır.
Dosyanın bugünkü kodu kapanış dışı başka bir kodsa (iade sonrası, atama bekleyen; ör. R10) koşul
gözlemine kapanış olarak girmez: sürmekte olan dönem `KOSUL_SAGLANMIYOR` ile ölçülmez, sona ermiş
dönem bitişine kadar ölçülür ve oluşmuş düşümü korunur (`sonlanan_atamada_dusum_korunur`).

`hazirlik.sulh_alani` (teyit bekliyor): sulh amaçlı atamanın ayrıldığı alan, atama logunun
sözleşme alanlarından biridir (`atama_ref`, `grup`, `tipi`); kaynaktaki ham ad (ör. eşlemeden
önceki sütun adı) yazılırsa doğrulama durdurur (kapı şema dışı sütunu atar, gece her seferinde
hesap hatası verirdi). Ayrım başka bir alandaysa `atama_log` şemasına isteğe bağlı alan eklenir.
`tahsilat_hareket_turleri` verilirse ters kayıt (eksi tutarlı) türü de listeye yazılır; boş liste
geçersizdir (bütün hareketler için `null`). Kod listelerinin öğeleri metindir; `kriter1.oto_branslar`
ve `tahsilat.olgunluk_ay` anahtarları `kalite.bilinen_branslar` kodlarından (olgunlukta ayrıca
`DIGER`) olmalıdır.

Değerlendirme tarihi (açık karar, değerlendirme sistemi ekibinden teyit bekliyor): sistemdeki
tarih alanı kayıt yerinde güncelleniyorsa değerlendirme tarihi değildir ve 12 aylık pencere (`kalite_davranis.pencere_ay`) güncel puanları dışarıda
bırakır. Kapı pencere dışında kalan puanlı satırları sayar (`PENCERE_DISI` uyarısı).

Takip bilgisinde dosya başına birden çok satır (açık karar, çekirdek sistem ekibi ve Hukuk
teyidi bekliyor): yedek yol gözlemine esası dolu satırlar içinde işlem tarihi en erken olan girer.
Yedek yol yalnız gölge modda kullanıldığı için puanı etkilemez; veri sözleşmesinde satır anlamı
(icra, dava) netleşince kural gözden geçirilir.
