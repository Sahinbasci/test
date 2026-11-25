"""Kurulum: hattın yazdığı veri kümelerini ve yönetilen klasörleri Dataiku projesinde oluşturur.

Bir Python not defterinde, kütüphane yapıştırıldıktan sonra çalıştırılır. Hücreler "# %%"
satırlarıyla ayrılır. Yalnız eksikleri oluşturur; var olan veri kümesine ve klasöre dokunmaz,
veri silmez. Adlar kütüphanedeki hat/veri_kumeleri.py dosyasından gelir.
Kullanılan API (DSS 9 ve sonrası): api_client().get_default_project(),
DSSProject.new_managed_dataset(ad).with_store_into(bağlantı).create(),
DSSProject.create_managed_folder(ad, folder_type, connection_name).
Bağlantı adları Dataiku yöneticisinden alınır; aşağıdaki ilk hücrede yazılır.
"""
# %% 1. Ayarlar (bağlantı adlarını doldurun)
import dataiku

from hat import veri_kumeleri

BAGLANTI = "minio_avukat_perf"   # yönetilen veri kümeleri ve klasörler (MinIO S3 bağlantısı)
KLASOR_TURU = "S3"               # BAGLANTI'nın türü; yerel dosya sistemiyse "Filesystem"
SQL_BAGLANTISI = None            # Grafana'nın okuyacağı SQL bağlantısı; None ise BAGLANTI.
#                                 İlk geceden ÖNCE kararlaştırılır: izleme tabloları sonradan
#                                 SQL'e taşınırsa çalışma geçmişi taşınmadan kaybolur (README).
DOSYA_KAYNAGI_VAR = False        # yöntemi "dosya" olan kaynak varsa True (kaynak_dosyalari)

proje = dataiku.api_client().get_default_project()


def _ad(oge):
    return oge["name"] if isinstance(oge, dict) else getattr(oge, "name", None)


var_olan_kumeler = {_ad(oge) for oge in proje.list_datasets()}
var_olan_klasorler = {_ad(oge) for oge in proje.list_managed_folders()}
print("projedeki veri kümesi:", len(var_olan_kumeler), "· klasör:", len(var_olan_klasorler))

# %% 2. Eksik veri kümeleri
def kume_olustur(ad, baglanti):
    try:
        yardimci = proje.new_managed_dataset(ad)
    except AttributeError:  # çok eski sürüm
        yardimci = proje.new_managed_dataset_creation_helper(ad)
    yardimci.with_store_into(baglanti)
    yardimci.create()


istenen = list(veri_kumeleri.CIKTI) + list(veri_kumeleri.KONTROL)
for ad in istenen:
    if ad in var_olan_kumeler:
        print("var:", ad)
        continue
    sql = ad in veri_kumeleri.IZLEME or ad == veri_kumeleri.KONTROL_SQL
    baglanti = (SQL_BAGLANTISI or BAGLANTI) if sql else BAGLANTI
    kume_olustur(ad, baglanti)
    print("oluşturuldu:", ad, "·", baglanti)

# %% 3. Eksik yönetilen klasörler
klasorler = list(veri_kumeleri.KLASORLER)
if DOSYA_KAYNAGI_VAR:
    klasorler.append(veri_kumeleri.DOSYA_KLASORU)
for ad in klasorler:
    if ad in var_olan_klasorler:
        print("var:", ad)
        continue
    proje.create_managed_folder(ad, folder_type=KLASOR_TURU, connection_name=BAGLANTI)
    print("oluşturuldu:", ad)
print("Elle yapılacak: ham_arsiv klasörünün ayarlarında kova avukat-perf-ham, diğerlerinde "
      "avukat-perf-islenmis seçilir (minio/README.md).")

# %% 4. Kaynak veri kümeleri (yalnız yöntemi "dataiku" olan kaynaklar)
# Ayar dosyası henüz yüklenmediyse hücre atlanır; yükledikten sonra yeniden çalıştırılır.
from hat import ayar as ayar_modulu
from hat.dataiku_ortam import DataikuOrtam

kurulum_ortami = DataikuOrtam()
if kurulum_ortami.ayar_oku_varsa("kaynaklar.json") is None:
    print("ayarlar klasöründe kaynaklar.json yok: kaynak veri kümeleri denetlenmedi")
else:
    ayarlar = ayar_modulu.yukle(kurulum_ortami, "kaynaklar")  # BOM'lu dosya da okunur
    for ad in veri_kumeleri.kaynak_veri_kumeleri(ayarlar):
        durum = "var" if ad in var_olan_kumeler else "EKSİK, kaynağa bağlı olarak oluşturun"
        print(durum + ": " + ad)
print("Sonraki adım: ayarlar klasörüne params.json ve kaynaklar.json yüklenmediyse yükleyin "
      "(klasör > Dosya ekle) ve bu hücreyi yeniden çalıştırın, ardından aktarim_kontrol.py.")
