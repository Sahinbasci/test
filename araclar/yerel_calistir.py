"""Sentetik veriyle uçtan uca yerel çalışma: gecelik akış ve son üç dönemin yayını.

Ayarlar Dataiku'daki gibi kurulur (hat.ayar): dataiku/degiskenler/params.json ve kaynaklar.json
üzerine sentetik/params_ek.json ve sentetik/kaynaklar_ek.json birleştirilir. Ek dosyalar yalnız bu
prova içindir: değerlendirme ölçeği, gölge mod, sulh kodları; bütün sistemler sentetik/veri
altındaki CSV'lerden (dosya yöntemi).
Senaryolar: "tam" (bütün kaynaklar, prova parametreleri) ve "acilis" (canlıya geçiş günü:
yalnız çekirdek sistem, tahsilat raporu ve değerlendirme sistemi bağlı; dava takip ve haklı bekleme
bekleniyor; params.json olduğu gibi, yani değerlendirme ölçeği teyitsiz ve gölge mod açık) ve "bos"
(kurulum günü: hiçbir kaynak bağlı değil).
Kullanım: python araclar/yerel_calistir.py [calisma_klasoru] [tam|acilis|bos]
"""
import json
import os
import shutil
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "dataiku", "kutuphane"))

from hat import akis, ayar, donem_akisi  # noqa: E402
from hat.ortam import YerelOrtam  # noqa: E402

SIMDI = "2026-11-19 02:00:00"
DONEMLER = ("2026-08", "2026-09", "2026-10")


def _json(*parcalar):
    with open(os.path.join(KOK, *parcalar), encoding="utf-8") as dosya:
        return json.load(dosya)


def prova_ayari(ad):
    """ad (params ya da kaynaklar): depodaki varsayılan + sentetik ek dosyası."""
    return ayar.birlestir(_json("dataiku", "degiskenler", ad + ".json"),
                          _json("sentetik", ad + "_ek.json"))


ACILISTA_BAGLI = ("dosya", "atama_log", "takip", "tahsilat_hareketi", "rapor_avukat_toplam",
                  "degerlendirme", "avukat")


def senaryo_ayarlari(senaryo):
    """(kaynak ayarları, parametreler) senaryoya göre."""
    ayarlar = prova_ayari("kaynaklar")
    if senaryo == "tam":
        return ayarlar, prova_ayari("params")
    if senaryo not in ("acilis", "bos"):
        raise ValueError("bilinmeyen senaryo: " + str(senaryo))
    for ad, ayar in ayarlar["kaynaklar"].items():
        if senaryo == "bos" or ad not in ACILISTA_BAGLI:
            ayar["yontem"] = "bekliyor"
    return ayarlar, _json("dataiku", "degiskenler", "params.json")


CALISMA_ICERIGI = {"tablolar", "ham", "ayarlar", "veri_kumeleri",  # YerelOrtam'ın klasörleri
                   ".DS_Store"}  # macOS'un klasöre bıraktığı dosya


def _sifirla(klasor):
    """Klasör yalnız yerel ortamın kendi klasörlerini içeriyorsa silinir; yanlış verilen bir yolu
    (ör. depo kökü) silmemek için başka içerik varsa durur."""
    if not os.path.isdir(klasor):
        return
    yabanci = sorted(set(os.listdir(klasor)) - CALISMA_ICERIGI)
    if yabanci:
        raise SystemExit("{} yerel çalışma klasörü değil (içinde: {}); silinmedi".format(
            klasor, ", ".join(yabanci[:5])))
    shutil.rmtree(klasor)


def calistir(klasor, yazdir=True, senaryo="tam"):
    """Klasörü sıfırlar, gecelik akışı ve dönem yayınlarını çalıştırır; ortamı döndürür.
    Senaryo adı klasör silinmeden önce doğrulanır (yazım hatası önizleme verisini silmesin)."""
    ayarlar, params = senaryo_ayarlari(senaryo)
    _sifirla(klasor)
    ortam = YerelOrtam(klasor, kaynak_kok=KOK)
    ozet = akis.gecelik(ortam, ayarlar, params, simdi=SIMDI)
    if yazdir:
        print("gecelik:", ozet)
    for donem in DONEMLER:
        sonuc = donem_akisi.calistir(ortam, params, donem, simdi=SIMDI)
        if yazdir:
            print("dönem {}: {}".format(donem, sonuc))
    return ortam


if __name__ == "__main__":
    if any(arg.startswith("-") for arg in sys.argv[1:]):  # "--help" klasör adı sanılmasın
        sys.exit("Kullanım: python araclar/yerel_calistir.py [hedef_klasör] [senaryo]")
    HEDEF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KOK, "onizleme", "calisma")
    calistir(HEDEF, senaryo=sys.argv[2] if len(sys.argv) > 2 else "tam")
