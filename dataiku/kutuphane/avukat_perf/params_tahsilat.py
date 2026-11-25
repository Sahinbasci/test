"""Tahsilat bölümünün içerik kuralları: olgunluk, gruplama, bantlar, pencereler ve bileşen
ağırlıkları."""
from avukat_perf.params_kural import tur_uygun
from avukat_perf.params_sema import TAHSILAT_BILESENLERI, TAHSILAT_GRUPLARI


def _artan_pozitif(liste, tur):
    return all(tur_uygun(sinir, tur) and sinir > 0 for sinir in liste) and all(
        alt < ust for alt, ust in zip(liste, liste[1:]))


def tahsilat_hatalari(tah):
    hatalar = []
    olgunluk = tah["olgunluk_ay"]
    gecerli_ay = all(tur_uygun(ay, "tam") and ay > 0 for ay in olgunluk.values())
    if "DIGER" not in olgunluk or not gecerli_ay:
        hatalar.append("tahsilat.olgunluk_ay: DIGER bulunmalı, aylar pozitif tam sayı olmalı")
    if tah["en_az_olgun_dosya"] < 1 or tah["guven_sabiti"] < 0 or tah["egim"] <= 0:
        hatalar.append("tahsilat: en_az_olgun_dosya, guven_sabiti ya da egim geçersiz")
    if tah["yeterli_olgun_dosya"] < tah["en_az_olgun_dosya"]:
        hatalar.append("tahsilat.yeterli_olgun_dosya en_az_olgun_dosya'dan küçük olamaz")
    if tah["olay_guven_sabiti"] <= 0:
        hatalar.append("tahsilat.olay_guven_sabiti pozitif olmalı")
    if tah["guncellik_pencere_ay"] < 1 or tah["yillik_yil_sayisi"] < 1 \
            or tah["aylik_pencere_ay"] < 1:
        hatalar.append("tahsilat.guncellik_pencere_ay, aylik_pencere_ay ve yillik_yil_sayisi "
                       "pozitif olmalı")
    grup = tah["gruplama"]
    if not grup or not all(ad in TAHSILAT_GRUPLARI for ad in grup) or len(set(grup)) < len(grup):
        hatalar.append("tahsilat.gruplama yalnız brans, yas_bandi ve tutar_bandi içerebilir, "
                       "tekrarsız")
    if not _artan_pozitif(tah["tutar_bantlari"], "sayi"):
        hatalar.append("tahsilat.tutar_bantlari artan pozitif sayılar olmalı")
    if not _artan_pozitif(tah["yas_bantlari"], "tam"):
        hatalar.append("tahsilat.yas_bantlari artan pozitif tam sayılar (ay) olmalı")
    if tah["enflasyon_duzeltme"]:
        hatalar.append("tahsilat.enflasyon_duzeltme henüz uygulanmadı; false olmalı")
    agirlik = tah["bilesen_agirliklari"]
    gecerli = sorted(agirlik) == sorted(TAHSILAT_BILESENLERI) and all(
        tur_uygun(deger, "sayi") and deger >= 0 for deger in agirlik.values())
    if not gecerli or abs(sum(agirlik.values()) - 1.0) > 1e-9:
        hatalar.append("tahsilat.bilesen_agirliklari: tutar, siklik ve guncellik için negatif "
                       "olmayan sayı; toplamı 1")
    return hatalar
