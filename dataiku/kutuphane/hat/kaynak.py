"""Kaynak okuma: her mantıksal kaynak, kaynaklar.json'daki yöntemle okunur.

Yöntemler: bekliyor (bağlantı henüz yok), dataiku (Dataiku veri kümesi), api (hat.api ile
genel REST okuyucu), dosya (CSV; sentetik veri provası ve yerel çalışma). Okunan ham tablo
arşive olduğu gibi yazılır; normalle ise alan adlarını eşler (alan_eslemesi; sonra aynı adlı iki
sütun kalırsa hata), değerlendirme sisteminin geniş biçimini uzun biçime alır
(genis_degerlendirme; kaynakta olmayan eşleme sütunu puanlanmamış sayılır), kaynak değerlerini
sözleşme kodlarına çevirir (deger_eslemesi, ör. {"brans": {"Trafik": "TRAFIK"}}), metin
tarihleri verilen biçimle çevirir (tarih_bicimi, ör. "%d.%m.%Y"; biçime uymayan değer metin
kalır, kapı KALDI verir) ve metin sayıyı kaynağın biçimiyle çevirir (sayi_bicimi tr: 1.234,56;
en: 1,234.56).
API ayarında {kesit} ve {cekim_tarihi} yer tutucuları kullanılabilir (hat.okuma.baglam).
"""
import re

import pandas as pd

from avukat_perf import hazirlik, sema
from avukat_perf.kalite_tur import EN_KALIBI, TR_KALIBI
from hat import api
from hat.ayar import YONTEMLER

# Normalleştirmeyi belirleyen kaynak ayarları: arşivin bilgi.json'una yazılır (yeniden üretim).
NORMALLEME = ("alan_eslemesi", "genis_degerlendirme", "deger_eslemesi", "tarih_bicimi",
              "sayi_bicimi")


def _yer_tut(deger, baglam):
    if isinstance(deger, dict):
        return {anahtar: _yer_tut(alt, baglam) for anahtar, alt in deger.items()}
    if isinstance(deger, list):
        return [_yer_tut(alt, baglam) for alt in deger]
    if isinstance(deger, str):
        for anahtar, metin in baglam.items():
            deger = deger.replace("{" + anahtar + "}", metin)
    return deger


def cek(ayar, ortam, baglam):
    """Ham tablo; yöntem 'bekliyor' ise None."""
    yontem = ayar.get("yontem", "bekliyor")
    if yontem not in YONTEMLER:
        raise ValueError("bilinmeyen yöntem: {} ({})".format(yontem, ", ".join(YONTEMLER)))
    if yontem == "bekliyor":
        return None
    if yontem == "dataiku":
        return ortam.veri_kumesi_oku(ayar["dataiku"]["veri_kumesi"])
    if yontem == "api":
        return api.oku(_yer_tut(ayar["api"], baglam), ortam.gizli)
    dosya = ayar["dosya"]
    return pd.read_csv(ortam.dosya_yolu(dosya["yol"]), dtype=str, sep=dosya.get("ayirici", ","),
                       encoding=dosya.get("kodlama", "utf-8"), keep_default_na=False,
                       na_values=[""])


def _sayi(seri, bicim):
    """Metin sayıyı kaynağın biçimiyle çevirir (tr '1.234,56', en '1,234.56' -> 1234.56); yalnız
    kalıba uyan metin çevrilir. Sayı olarak gelen değer (API, Dataiku double) ve kalıba uymayan
    metin olduğu gibi kapıya gider; nokta silinerek 10-100 kat büyütülmez."""
    kalip, binlik, ondalik = (TR_KALIBI, ".", ",") if bicim == "tr" else (EN_KALIBI, ",", ".")

    def cevir(deger):
        if isinstance(deger, str) and re.match(kalip, deger):
            return float(deger.strip().replace(binlik, "").replace(ondalik, "."))
        return deger
    return seri.map(cevir)


def _tarih(seri, bicim):
    """Biçime uyan değer tarih olur; uymayan metin metin kalır ve kapının ISO denetimine gider
    (where datetime64'e zorlasaydı dateutil ay-gün sırasını tahmin ederdi)."""
    tarih = pd.to_datetime(seri, format=bicim, errors="coerce")
    uymayan = tarih.isna() & seri.notna()
    return tarih.astype(object).where(~uymayan, seri) if uymayan.any() else tarih


def _deger_esle(seri, harita):
    return seri.map(lambda deger: harita.get(deger.strip(), deger) if isinstance(deger, str)
                    else deger)


def normalle(ad, ham, ayar):
    """Ham tabloyu veri sözleşmesindeki alan adlarına ve biçimlere getirir.

    Kayıtsız yanıt (ör. API'den boş liste) sözleşme sütunlarıyla boş tablo olur; boşluğu kalite
    kapısı değerlendirir (zorunlu kaynakta KALDI, isteğe bağlıda UYARI).
    """
    if ham.empty and len(ham.columns) == 0:
        return pd.DataFrame(columns=sema.alanlar(ad))
    tablo = ham.rename(columns=ayar.get("alan_eslemesi") or {})
    cift = sorted(set(str(sutun) for sutun in tablo.columns[tablo.columns.duplicated()]))
    if cift:
        raise ValueError("{}: alan eşlemesinden sonra yinelenen sütun: {}".format(
            ad, ", ".join(cift)))
    genis = ayar.get("genis_degerlendirme")
    if genis:
        if not any(alan in tablo.columns for alan in genis):
            raise ValueError("{}: genis_degerlendirme sütunlarının hiçbiri yok".format(ad))
        tablo = hazirlik.degerlendirme_uzun(tablo.assign(**{
            alan: None for alan in genis if alan not in tablo.columns}), genis)
    for alan, harita in (ayar.get("deger_eslemesi") or {}).items():
        if alan in tablo.columns:
            tablo[alan] = _deger_esle(tablo[alan], harita)
    for alan, tur, _ in sema.KAYNAKLAR[ad]["alanlar"]:
        if alan not in tablo.columns:
            continue
        if tur == "sayi" and ayar.get("sayi_bicimi") in ("tr", "en"):
            tablo[alan] = _sayi(tablo[alan], ayar["sayi_bicimi"])
        if tur in ("tarih", "zaman") and ayar.get("tarih_bicimi"):
            tablo[alan] = _tarih(tablo[alan], ayar["tarih_bicimi"])
    return tablo
