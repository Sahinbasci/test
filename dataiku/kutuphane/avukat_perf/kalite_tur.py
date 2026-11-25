"""Kalite kapısının tür çevirisi: metin, sayı ve tarih alanlarının şemadaki türe getirilmesi.

Metin alanında tam sayı değerli ondalık (ör. 123.0) "123" olur; tarih türünde gelen metin alanı
(rapor dönemi) yerel güne çevrilir. Boş ya da yalnız boşluk olan metin boştur. Sayı kalıpları
burada tek yerdedir: TR_SAYI kapıda Türkçe ya da belirsiz biçimi yakalar, TR_KALIBI ve EN_KALIBI
kaynak ayarındaki sayi_bicimi ile çevrilen biçimlerdir (hat.kaynak).
"""
import pandas as pd

from avukat_perf.ortak import gun

TR_SAYI = r"^-?\d{1,3}(\.\d{3})+(,\d+)?$|^-?\d+,\d+$"  # Türkçe ya da belirsiz (1.234, 1,234)
TR_KALIBI = r"^\s*-?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?\s*$"  # sayi_bicimi tr: 1.234,56
EN_KALIBI = r"^\s*-?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?\s*$"  # sayi_bicimi en: 1,234.56
TARIH_TUR = ("çevrilemeyen değer: YYYY-AA-GG değil ya da tarih sınırı dışında (ör. 9999-12-31 "
             "açık uç yer tutucusu; veri hazırlığında boşa eşlenir)")


def _metin(deger):
    if isinstance(deger, float) and deger.is_integer():
        return str(int(deger))
    return str(deger).strip()


def cevir(seri, tur):
    if tur in ("tarih", "zaman"):
        return gun(seri, zorla=True, saat=tur == "zaman")
    if tur == "sayi":
        return pd.to_numeric(seri, errors="coerce")
    if pd.api.types.is_datetime64_any_dtype(seri):  # metin alanı tarih türünde (rapor dönemi)
        seri = gun(seri).dt.strftime("%Y-%m-%d").where(seri.notna())
    metin = seri.map(_metin, na_action="ignore")
    return metin.where(metin != "")


def bos_metin(seri):
    """Boş ya da yalnız boşluk olan metin boş değerdir (API "" ile gönderebilir). Tarih ve sayı
    dışındaki her tür (string, category) object'e çevrilir: ortak._tarih_disi_ayikla ile aynı."""
    if pd.api.types.is_datetime64_any_dtype(seri) or pd.api.types.is_numeric_dtype(seri):
        return seri
    seri = seri.astype(object).where(seri.notna(), None)
    return seri.where(~seri.map(lambda deger: isinstance(deger, str) and not deger.strip()))
