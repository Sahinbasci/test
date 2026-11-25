"""Dataiku'da önceden oluşturulacak veri kümeleri ve yönetilen klasörler.

Kurulum not defteri (dataiku/kontrol/kurulum.py) bu adları oluşturur. Hattın yazdığı
tabloların bu listeyle aynı olduğu testle denetlenir; ad değişirse liste de değişir.
Kaynak veri kümeleri (kaynak_*) kaynaklar.json'dan okunur, yalnız yöntemi "dataiku" olan
kaynaklar için gerekir.
"""
from avukat_perf.sema import KAYNAKLAR
from hat.ayar import kaynak_ayari

KAYIT = ("calisma_kaydi", "kalite_sonucu")
GOZLEM = ("gozlem_esas", "gozlem_esas_yedek", "gozlem_dava", "gozlem_kosul")
MODEL = ("model_dosya", "model_atama_donemi", "model_hareket", "model_bekleme",
         "model_degerlendirme", "model_avukat", "model_k2_goruntu")
SONUC = ("sonuc_tahsilat_avukat", "sonuc_tahsilat_grup", "sonuc_tahsilat_brans",
         "sonuc_portfoy",
         "sonuc_tahsilat_aylik", "sonuc_tahsilat_yillik", "sonuc_mevcut_degerlendirme",
         "sonuc_k1", "sonuc_k2", "sonuc_sure", "sonuc_sure_ozet", "sonuc_eposta",
         "sonuc_kalite_davranis_sutun", "sonuc_kalite_davranis_alt",
         "sonuc_puan_guncel", "sonuc_birlesik", "sonuc_aciklama")
OLAY = ("bayrak_olay", "olay_celiski")
DONEM = ("puan_donem", "birlesik_donem")
CIKTI = KAYIT + GOZLEM + MODEL + SONUC + OLAY + DONEM
KONTROL = ("kontrol_tablo", "kontrol_tablo_sql")  # aktarım kontrolünün gidiş-dönüş tabloları
KONTROL_SQL = "kontrol_tablo_sql"  # izleme tablolarıyla aynı (SQL) bağlantıda kurulur
AYAR_KLASORU = "ayarlar"  # params.json, kaynaklar.json ve ek dosyaları
ARSIV_KLASORU = "ham_arsiv"  # S3 (MinIO) bağlantılı ham arşiv
KLASORLER = (AYAR_KLASORU, ARSIV_KLASORU)
DOSYA_KLASORU = "kaynak_dosyalari"  # yalnız yöntemi "dosya" olan kaynak varsa gerekir
IZLEME = KAYIT  # Grafana okur; SQL bağlantısında tutulur


def kaynak_veri_kumeleri(ayarlar):
    """kaynaklar.json içinde yöntemi "dataiku" olan kaynakların veri kümesi adları."""
    secili = [kaynak_ayari(ayarlar, ad) for ad in KAYNAKLAR]
    return sorted(ayar["dataiku"]["veri_kumesi"] for ayar in secili
                  if ayar.get("yontem") == "dataiku")
