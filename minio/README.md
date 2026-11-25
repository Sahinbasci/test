# MinIO

MinIO'da kod çalışmaz. Arşive ve veri kümelerine yazan kod Dataiku'da çalışır; MinIO yalnız
depolamadır. Bu klasörde kova kurulumu ve klasör düzeni vardır.

## Kovalar

| Kova | İçerik | Dataiku'da karşılığı |
|---|---|---|
| `avukat-perf-ham` | Kaynaklardan gelen ham veri, değiştirilmeden | `ham_arsiv` yönetilen klasörü |
| `avukat-perf-islenmis` | Ortak veri modeli, sonuç ve kayıt tabloları | Yönetilen veri kümeleri, `ayarlar` klasörü |

Ham arşiv düzeni (kod `hat/arsiv.py` içinde üretir):

```
avukat-perf-ham/
  ham/kaynak=<kaynak>/cekim_tarihi=<YYYY-AA-GG>/calisma=<çalışma kimliği>/
      veri.parquet  (Parquet motoru yoksa veri.csv.gz)
      bilgi.json    (satır sayısı, sütunlar, biçim, yöntem)
```

- Her gece her kaynak kendi klasörüne yazılır. Var olan dosyanın üzerine yazılmaz; aynı gece
  ikinci çalışma yeni çalışma kimliğiyle ayrı klasöre yazar.
- Dataiku hizmet hesabının ham kovada silme yetkisi yoktur (`politika_dataiku.json`).
- Sürümleme açıktır; yanlışlıkla silinen ya da değişen nesne geri alınabilir.
- Değiştirilemezlik kilidi (object lock) isteğe bağlıdır. Saklama süresi kişisel veri saklama
  politikasına bağlı bir karardır; `KILIT_GUN` verilmezse kilit kurulmaz. Kilit yalnız kova
  ilk oluşturulurken açılabilir.

İşlenmiş kova, Dataiku'nun yönetilen veri kümelerini tuttuğu yerdir. Klasör adlarını Dataiku
belirler; elle düzenlenmez. Dataiku veri kümelerini her gece baştan yazdığı için sürümleme açık
bu kovada her gecenin kopyası eski sürüm olarak kalır. `ESKI_SURUM_GUN` verilirse eski sürümler
o kadar gün sonra silinir (yaşam döngüsü kuralı); verilmezse betik uyarı yazar ve eski sürümler
süresiz birikir. Süre kişisel veri saklama politikasına bağlı bir karardır.

## Kurulum

Komutları MinIO yöneticisi çalıştırır.

1. Hizmet hesabını oluşturun (gizli anahtarı yönetici belirler):

   ```bash
   mc admin user add kurum dataiku-avukat-perf GIZLI_ANAHTAR
   ```

2. Kovaları, sürümlemeyi ve yetkiyi kurun:

   ```bash
   MC_ALIAS=kurum sh minio/kurulum.sh
   ```

   Kilit isteniyorsa saklama süresi gün olarak verilir: `KILIT_GUN=<gün> MC_ALIAS=kurum sh minio/kurulum.sh`.
   İşlenmiş kovadaki eski sürümlerin saklama süresi aynı biçimde `ESKI_SURUM_GUN=<gün>` ile
   verilir. Betik yeniden çalıştırılabilir: var olan kova ve politika korunur, zaten bağlı
   politika yeniden bağlanmaz; yalnız `ESKI_SURUM_GUN` verildiyse yaşam döngüsü kuralı yeniden
   eklenir (`mc ilm rule ls` ile görülür, fazlası `mc ilm rule rm` ile silinir). Bir komut hata
   verirse ileti gizlenmez ve betik durur.

3. Dataiku yöneticisi bir S3 bağlantısı tanımlar (Yönetim > Bağlantılar > Yeni > Amazon S3):
   - Uç nokta: MinIO adresi; "path-style" erişim açık; bölge MinIO'daki değer (çoğunlukla
     `us-east-1`).
   - Kimlik: `dataiku-avukat-perf` erişim anahtarı ve gizli anahtarı.
   - Bağlantı adı önerisi: `minio_avukat_perf`.
   - Yönetilen veri kümeleri için varsayılan kova (bağlantı ayarlarında "Default bucket" ya da
     yönetilen veri kümesi yolu): `avukat-perf-islenmis`. Verilmezse `kurulum.py`'nin
     oluşturduğu veri kümeleri başka bir kovaya düşer.

4. Dataiku projesinde:
   - `ham_arsiv` yönetilen klasörü: bağlantı `minio_avukat_perf`, kova `avukat-perf-ham`,
     yol kökü `/`.
   - Yönetilen veri kümeleri ve `ayarlar` klasörü: bağlantı `minio_avukat_perf`, kova
     `avukat-perf-islenmis`.
   - `calisma_kaydi` ve `kalite_sonucu` Grafana'nın okuyabildiği bir SQL bağlantısında
     tutulur (bkz. `grafana/README.md`).

## Kontrol

Kurulumdan sonra Dataiku'da `dataiku/kontrol/aktarim_kontrol.py` not defteri çalıştırılır.
"Arşiv denemesi" adımı `ham_arsiv` klasörüne küçük bir deneme dosyası yazar ve geri okur.
