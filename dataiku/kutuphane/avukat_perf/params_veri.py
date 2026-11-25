"""Kalite kapısı ve veri hazırlığı parametrelerinin içerik kuralları; branş kodlarının üç yerde
(kalite.bilinen_branslar, kriter1.oto_branslar, tahsilat.olgunluk_ay) tutarlılığı.

Kod listelerinin öğeleri boş olmayan metindir: kapı kod alanlarını metne çevirdiği için listeye
sayı olarak yazılmış öğe hiçbir satırla eşleşmezdi. Branş kodu bilinen_branslar dışında olamaz:
yazım farkı oto eşiğini ve olgunluk süresini sessizce varsayılana düşürürdü. sulh_alani atama
logunun sözleşme alanlarından biridir (kapı şema dışı sütunu atar; ham kaynak adı her gece hesap
hatası verirdi); ayrım başka bir alandaysa atama_log şemasına isteğe bağlı alan eklenir.
"""
from datetime import datetime

from avukat_perf import sema

SULH_ALANLARI = [alan for alan in sema.alanlar("atama_log")
                 if alan not in ("dosya_no", "avukat_kodu", "atama_tarihi", "iptal_tarihi")]


def _metin_listesi(liste):
    return all(isinstance(oge, str) and oge.strip() for oge in liste)


def _gun_mu(metin):
    try:
        datetime.strptime(metin, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def kalite_hatalari(kal):
    hatalar = []
    if kal["satir_sapma_orani"] <= 0 or not 0 <= kal["mutabakat_tolerans"] < 1 \
            or kal["gelecek_tarih_gun"] < 0 or kal["sapma_en_az_satir"] < 0:
        hatalar.append("kalite: satir_sapma_orani > 0, 0 <= mutabakat_tolerans < 1, "
                       "gelecek_tarih_gun >= 0, sapma_en_az_satir >= 0 olmalı")
    if not _gun_mu(kal["en_eski_tarih"]) or not kal["bilinen_branslar"] \
            or not _metin_listesi(kal["bilinen_branslar"]):
        hatalar.append("kalite: en_eski_tarih geçerli bir YYYY-AA-GG günü, bilinen_branslar boş "
                       "olmayan metin listesi olmalı")
    if not 0 <= kal["iliski_en_cok_yetim_orani"] < 1:
        hatalar.append("kalite.iliski_en_cok_yetim_orani 0 ile 1 arasında olmalı (1 hariç)")
    return hatalar


def brans_hatalari(params):
    bilinen, hatalar = set(params["kalite"]["bilinen_branslar"]), []
    oto = params["kriter1"]["oto_branslar"]
    if not _metin_listesi(oto) or not set(oto) <= bilinen:
        hatalar.append("kriter1.oto_branslar yalnız kalite.bilinen_branslar kodlarını içerebilir")
    if set(params["tahsilat"]["olgunluk_ay"]) - bilinen - {"DIGER"}:
        hatalar.append("tahsilat.olgunluk_ay anahtarları kalite.bilinen_branslar kodları ya da "
                       "DIGER olmalı")
    return hatalar


def hazirlik_hatalari(hz):
    hatalar, turler = [], hz["tahsilat_hareket_turleri"]
    listeler = [hz["sulh_avukat_kodlari"], hz["sulh_degerleri"], turler or []]
    if not all(_metin_listesi(liste) for liste in listeler):
        hatalar.append("hazirlik: sulh_avukat_kodlari, sulh_degerleri ve tahsilat_hareket_turleri "
                       "öğeleri boş olmayan metin olmalı")
    if turler == []:
        hatalar.append("hazirlik.tahsilat_hareket_turleri boş liste olamaz (bütün hareketler "
                       "için null)")
    if hz["sulh_alani"] is not None and hz["sulh_alani"] not in SULH_ALANLARI:
        hatalar.append("hazirlik.sulh_alani null ya da atama logunun şu alanlarından biri olmalı: "
                       + ", ".join(SULH_ALANLARI))
    return hatalar


def veri_hatalari(params):
    """Kalite, branş tutarlılığı ve veri hazırlığı kuralları."""
    return (kalite_hatalari(params["kalite"]) + brans_hatalari(params)
            + hazirlik_hatalari(params["hazirlik"]))
