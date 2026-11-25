"""Parametre sözlüğünün doğrulanması.

Bu modül dosya okumaz. Sözlüğü çağıran taraf verir (hat.ayar: params.json + params_ek.json).
"_" ile başlayan anahtarlar açıklamadır, yok sayılır. Şemada olmayan anahtar hatadır: ek
dosyadaki bir yazım hatası (ör. uyari_gn) sessizce hiçbir şeyi değiştirmezdi.
"""
import math

import pandas as pd

from avukat_perf import agirlik
from avukat_perf.params_kural import (diger_hatalari, gorunum_hatalari, kalite_davranis_hatalari,
                                      not_hatalari, tur_uygun)
from avukat_perf.params_tahsilat import tahsilat_hatalari
from avukat_perf.params_sema import ALANLAR, TUR_ADI

UST_ALANLAR = set(ALANLAR) | {"notlar", "birlesik_puan_kosulu", "birlesik_sutunlar", "agirliklar"}


def _bilinmeyenler(blok, izinli, yer):
    return ["bilinmeyen anahtar: " + yer + str(ad) for ad in sorted(blok, key=str)
            if not str(ad).startswith("_") and ad not in izinli]


def _yapi_hatalari(params):
    hatalar = _bilinmeyenler(params, UST_ALANLAR, "")
    for bolum in sorted(ALANLAR):
        if not isinstance(params.get(bolum), dict):
            hatalar.append("eksik bölüm: " + bolum)
            continue
        hatalar += _bilinmeyenler(params[bolum], ALANLAR[bolum], bolum + ".")
        for alan, tur in sorted(ALANLAR[bolum].items()):
            if alan not in params[bolum]:
                hatalar.append("eksik alan: {}.{}".format(bolum, alan))
            elif not tur_uygun(params[bolum][alan], tur):
                ad = " ya da ".join(tur) if isinstance(tur, tuple) else TUR_ADI[tur]
                hatalar.append("{} olmalı: {}.{}".format(ad, bolum, alan))
            elif tur == "sozluk" and any(str(ad).startswith("_") for ad in params[bolum][alan]):
                hatalar.append("açıklama anahtarı (_) yalnız bölüm düzeyinde yazılır: {}.{}".format(
                    bolum, alan))
    if not isinstance(params.get("notlar"), list):
        hatalar.append("liste olmalı: notlar")
    if not isinstance(params.get("agirliklar"), dict):
        hatalar.append("sözlük olmalı: agirliklar")
    return hatalar


def en_kisa_ay_suresi(ay):
    """ay takvim ayının en kısa gün karşılığı (1 ay 28, 2 ay 59 gün): atama hangi gün olursa
    olsun oto dışı düşüm bu süreden önce gelmez. Artık yıl dahil dört yılın her günü denenir."""
    gunler = pd.date_range("2001-01-01", "2004-12-31", freq="D")
    return int(((gunler + pd.DateOffset(months=int(ay))) - gunler).days.min())


def _sonlu_olmayanlar(deger, yol=""):
    """NaN ve sonsuz hiçbir alanda kabul edilmez. JSON okuyucu NaN yazımını kabul eder ve NaN ile
    her karşılaştırma yanlış döndüğü için diğer kurallardan sessizce geçerdi (ör. ağırlık)."""
    if isinstance(deger, float) and not math.isfinite(deger):
        return ["sonlu bir sayı olmalı (NaN ya da sonsuz olamaz): " + yol]
    if isinstance(deger, dict):
        return [hata for ad, alt in sorted(deger.items()) if not str(ad).startswith("_")
                for hata in _sonlu_olmayanlar(alt, (yol + "." if yol else "") + str(ad))]
    if isinstance(deger, list):
        return [hata for sira, alt in enumerate(deger)
                for hata in _sonlu_olmayanlar(alt, "{}[{}]".format(yol, sira))]
    return []


def _teyit_hatalari(params):
    """_teyit_bekleyen listesindeki her anahtar (bölüm ya da bölüm.alan) parametrede olmalı."""
    hatalar, liste = [], params.get("_teyit_bekleyen", [])
    if not isinstance(liste, list):
        return ["_teyit_bekleyen liste olmalı"]
    for anahtar in liste:
        bolum, _, alan = str(anahtar).partition(".")
        if bolum not in params or (alan and alan not in params[bolum]):
            hatalar.append("_teyit_bekleyen: tanımsız anahtar " + str(anahtar))
    return hatalar


def _kural_hatalari(params):
    k1, k2, sure = params["kriter1"], params["kriter2"], params["sure_puani"]
    hatalar = (tahsilat_hatalari(params["tahsilat"])
               + kalite_davranis_hatalari(params["kalite_davranis"])
               + gorunum_hatalari(params["gorunum"])
               + not_hatalari(params["notlar"]) + diger_hatalari(params))
    if not 0 < k1["uyari_gun"] < k1["dusum_gun_oto"]:
        hatalar.append("kriter1: 0 < uyari_gun < dusum_gun_oto olmalı")
    if k1["dusum_ay_diger"] <= 0:
        hatalar.append("kriter1: dusum_ay_diger sıfırdan büyük olmalı")
    elif k1["uyari_gun"] >= en_kisa_ay_suresi(k1["dusum_ay_diger"]):
        hatalar.append("kriter1: uyari_gun oto dışı düşümden önce olmalı (dusum_ay_diger ayın "
                       "en kısa gün karşılığından küçük)")
    if not 0 < k2["uyari_ay"] < k2["dusum_ay"]:
        hatalar.append("kriter2: 0 < uyari_ay < dusum_ay olmalı")
    if not 0 < sure["en_az_kapsam"] <= 1:
        hatalar.append("sure_puani: en_az_kapsam 0 ile 1 arasında olmalı")
    if sure["guven_sabiti"] <= 0 or sure["egim"] <= 0 or sure["yeterli_dosya"] < 1 \
            or sure["en_az_beklenen"] < 0:
        hatalar.append("sure_puani: guven_sabiti ve egim > 0, yeterli_dosya >= 1, "
                       "en_az_beklenen >= 0 olmalı")
    return hatalar + agirlik.birlesik_hatalari(params)


def dogrula(params):
    """Hata iletilerinin listesini döndürür; liste boşsa sözlük geçerlidir."""
    hatalar = _yapi_hatalari(params) + _sonlu_olmayanlar(params)
    return hatalar if hatalar else _teyit_hatalari(params) + _kural_hatalari(params)


def dogrula_veya_dur(params):
    """Geçerliyse sözlüğü aynen döndürür, değilse ValueError verir."""
    hatalar = dogrula(params)
    if hatalar:
        raise ValueError("Geçersiz parametre: " + "; ".join(hatalar))
    return params
