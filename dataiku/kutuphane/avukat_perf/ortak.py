"""Modüllerin ortak yardımcıları: girdi denetimi ve tarih biçimi.

Hata iletileri satır değeri içermez; yalnız sütun adı ve satır sayısı verir.
Metin olarak gelen tarih (object, string ya da category türü) YYYY-AA-GG biçiminde olmalıdır
(saatli ya da saatsiz, karışık olabilir); başka biçim (ör. 05.11.2026) ve sayı (ör. epoch) tahmin
edilmez, hata sayılır. pandas 2.x biçimi ilk satırdan tahmin ettiği için karışık biçim bildirilir.
Yuvarlama elle hesaptaki gibi yarım yukarıdır (bkz. yuvarla).
"""
import re
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

SAAT_DILIMI = "Europe/Istanbul"
BIR_GUN = pd.Timedelta(days=1)
KARISIK_BICIM = {"format": "mixed"} if int(pd.__version__.split(".")[0]) >= 2 else {}
ISO_TARIH = r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$"


def sutun_kontrol(tablo, sutunlar, ad):
    """Eksik sütun varsa ValueError verir."""
    eksik = [sutun for sutun in sutunlar if sutun not in tablo.columns]
    if eksik:
        raise ValueError("{}: eksik sütun: {}".format(ad, ", ".join(eksik)))


def bos_kontrol(tablo, sutunlar, ad):
    """Zorunlu sütunlarda boş değer varsa ValueError verir."""
    for sutun in sutunlar:
        sayi = int(tablo[sutun].isna().sum())
        if sayi:
            raise ValueError("{}: {} sütununda {} boş satır var".format(ad, sutun, sayi))


def anahtar_kontrol(tablo, anahtar, ad):
    """Anahtar sütunlarında yinelenen satır varsa ValueError verir."""
    sayi = int(tablo.duplicated(subset=list(anahtar), keep=False).sum())
    if sayi:
        raise ValueError("{}: anahtarı yinelenen {} satır var".format(ad, sayi))


def _tarih_disi_ayikla(seri, zorla):
    """YYYY-AA-GG olmayan metni ve sayıyı boşaltır (zorla) ya da hata verir; boş metin boştur."""
    if pd.api.types.is_numeric_dtype(seri) and not pd.api.types.is_bool_dtype(seri):
        bozuk = seri.notna()
    elif not pd.api.types.is_datetime64_any_dtype(seri):
        seri = seri.astype(object).where(seri.notna(), None)  # string türü de denetlenir
        metin = seri.map(lambda deger: isinstance(deger, str))
        seri = seri.where(~metin, seri.where(metin, "").astype(str).str.strip())
        seri = seri.where(seri != "")
        metin = seri.map(lambda deger: isinstance(deger, str))
        sayi = seri.map(lambda deger: isinstance(deger, (int, float)) and not pd.isna(deger))
        bozuk = sayi | (metin & ~seri.where(metin, "").astype(str).str.match(ISO_TARIH))
    else:
        return seri
    if bozuk.any() and not zorla:
        raise ValueError("tarih: {} değer YYYY-AA-GG biçiminde değil".format(int(bozuk.sum())))
    return seri.where(~bozuk) if bozuk.any() else seri


def _dilimli_metin(deger):
    return isinstance(deger, str) and re.search(r"(Z|[+-]\d{2}:?\d{2})$", deger) is not None


def _yerel_an(deger, zorla):
    """Tek değer: saat dilimliyse yerel saate çevrilip dilimi kaldırılır."""
    try:
        an = pd.Timestamp(deger)
    except ValueError:
        if zorla:
            return pd.NaT
        raise
    return an.tz_convert(SAAT_DILIMI).tz_localize(None) if an.tzinfo is not None else an


def gun(seri, zorla=False, saat=False):
    """Tarih sütununu saatsiz yerel güne çevirir (saat True ise yerel anı korur); boş NaT olur.

    Saat dilimli değer önce yerel saate çevrilir: UTC saklanmış yerel gece yarısı (ör.
    2026-10-11T21:00Z) bir önceki güne kaymaz. zorla True ise çevrilemeyen değer NaT olur.
    """
    seri, kip = _tarih_disi_ayikla(seri, zorla), "coerce" if zorla else "raise"
    if seri.dtype == object and seri.map(_dilimli_metin).any():
        # Saat dilimli metin (karışık dilim olabilir) tek tek yerel saate çevrilir.
        tarih = pd.to_datetime(seri.map(lambda deger: _yerel_an(deger, zorla),
                                        na_action="ignore"), errors=kip)
    else:
        tarih = pd.to_datetime(seri, errors=kip, **(KARISIK_BICIM if seri.dtype == object else {}))
    if tarih.dt.tz is not None:
        tarih = tarih.dt.tz_convert(SAAT_DILIMI).dt.tz_localize(None)
    return tarih if saat else tarih.dt.normalize()


def birlestir(tablolar, sutunlar):
    """Boş tabloları dışarıda bırakarak alt alta ekler; hepsi boşsa sütunlu boş tablo."""
    dolu = [tablo for tablo in tablolar if tablo is not None and not tablo.empty]
    if not dolu:
        return pd.DataFrame(columns=sutunlar)
    return pd.concat(dolu, ignore_index=True)[sutunlar]


def tek_gun(deger):
    """Tek bir tarih değerini gun() kuralıyla çevirir."""
    return gun(pd.Series([deger])).iloc[0]


def ondalik_yuvarla(deger, ondalik=2):
    """Decimal değeri yarım yukarı yuvarlar ve float döndürür."""
    return float(deger.quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_HALF_UP))


def yuvarla(deger, ondalik=2):
    """Elle hesaptaki gibi yarım yukarı yuvarlar (74,065 → 74,07); boş değer NaN olur.

    round() ikili gösterimdeki değeri yuvarlar (74,065 → 74,06); not eşiğinde bu, elle
    yapılan hesaptan farklı not verebilir.
    """
    if deger is None or pd.isna(deger):
        return float("nan")
    return ondalik_yuvarla(Decimal(repr(float(deger))), ondalik)
