"""Atama geçmişi: kapsam, kesitte bilinen atama dönemleri, elde tutma payı ve atıf.

Atama dönemi [atama_tarihi, bitis_tarihi) aralığıdır; bitiş günü dosya artık o avukatta
değildir. Sulh amaçlı ve hatalı girilip iptal edilen atamalar kapsam dışıdır. Kapsamdaki
dönemler aynı dosyada çakışamaz; yeniden atamada önceki dönemin bitişi veri hazırlığında
yazılır.
"""
import math

import pandas as pd

from avukat_perf.ortak import (BIR_GUN, anahtar_kontrol, bos_kontrol, gun, sutun_kontrol,
                               tek_gun)

SUTUNLAR = ("dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi", "bitis_nedeni",
            "atama_turu")
ANAHTAR = ("dosya_no", "avukat_kodu", "atama_tarihi")


def kapsam_belirle(atamalar):
    """Sulh amaçlı ve hatalı girilip iptal edilen atamalara neden yazar; satır silmez."""
    tablo = atamalar.copy()
    neden = pd.Series(None, index=tablo.index, dtype=object)
    neden.loc[tablo["bitis_nedeni"] == "IPTAL"] = "IPTAL"
    neden.loc[tablo["atama_turu"] == "SULH"] = "SULH"
    tablo["kapsam_disi_nedeni"] = neden
    return tablo


def donemler(atamalar, kesit):
    """Kesitte bilinen, kapsamdaki atama dönemleri; kesitten sonraki bitiş boş sayılır."""
    sutun_kontrol(atamalar, SUTUNLAR, "atamalar")
    bos_kontrol(atamalar, ANAHTAR, "atamalar")
    kesit = tek_gun(kesit)
    tablo = kapsam_belirle(atamalar).assign(atama_tarihi=gun(atamalar["atama_tarihi"]),
                                            bitis_tarihi=gun(atamalar["bitis_tarihi"]))
    anahtar_kontrol(tablo[tablo["kapsam_disi_nedeni"].isna()], ANAHTAR, "atamalar")
    secili = tablo["kapsam_disi_nedeni"].isna() & (tablo["atama_tarihi"] <= kesit)
    tablo = tablo.loc[secili, list(SUTUNLAR[:4])]
    tablo = tablo.assign(bitis_tarihi=tablo["bitis_tarihi"].where(tablo["bitis_tarihi"] <= kesit))
    tablo = tablo[~(tablo["bitis_tarihi"] <= tablo["atama_tarihi"])]  # boş dönem: tutulan gün yok
    tablo = tablo.sort_values(["dosya_no", "atama_tarihi"]).reset_index(drop=True)
    onceki_bitis = tablo.groupby("dosya_no")["bitis_tarihi"].shift()
    onceki_acik = tablo.duplicated("dosya_no") & onceki_bitis.isna()
    cakisma = onceki_acik | (tablo["atama_tarihi"] < onceki_bitis)
    if cakisma.any():
        raise ValueError("atamalar: kapsamdaki {} dönem öncekiyle çakışıyor".format(
            int(cakisma.sum())))
    return tablo


def tutulan_gunler(donem, baslangiclar, kesit):
    """(dosya, avukat) başına [baslangic, kesit] içinde dosyanın elde tutulduğu gün sayısı ve
    dosyanın aralıkta ilk tutulduğu gün (ilk). Aralıkta dosyayı hiç tutmamış avukat sonuca girmez.

    baslangiclar: dosya_no, baslangic.
    """
    sinir = tek_gun(kesit) + BIR_GUN
    tablo = donem.merge(baslangiclar, on="dosya_no")
    bas = tablo["atama_tarihi"].where(tablo["atama_tarihi"] >= tablo["baslangic"],
                                      tablo["baslangic"])
    son = tablo["bitis_tarihi"].fillna(sinir)
    son = son.where(son <= sinir, sinir)
    tablo = tablo.assign(gun=(son - bas).dt.days.clip(lower=0), ilk=bas)
    tablo = tablo[tablo["gun"] > 0]
    tablo = tablo.assign(ilk=tablo.groupby("dosya_no")["ilk"].transform("min"))
    return tablo.groupby(["dosya_no", "avukat_kodu", "ilk"], as_index=False)["gun"].sum()


def elde_tutma_paylari(donem, baslangiclar, kesit, payda):
    """Dosya başına avukatların elde tutma payı; gün sayısı [baslangic, kesit] içinde sayılır.

    payda ilk_atamadan: avukatın günü ÷ dosyanın aralıktaki ilk atamasından kesite kadarki gün;
    iade sonrası ve iki atama arasındaki boşluk hiçbir avukata yazılmaz (kısa süre tutulup iade
    edilen dosya beklentiye tam dosya girmez), tek avukatın tuttuğu dosya 1 sayılır. payda
    avukat_gunleri: avukatın günü ÷ avukatların günleri toplamı; paylar toplamı 1'dir.
    """
    tablo = tutulan_gunler(donem, baslangiclar, kesit)
    bolen = ((tek_gun(kesit) + BIR_GUN - tablo["ilk"]).dt.days if payda == "ilk_atamadan"
             else tablo.groupby("dosya_no")["gun"].transform("sum"))
    tablo = tablo.assign(pay=tablo["gun"] / bolen)
    return tablo[["dosya_no", "avukat_kodu", "pay"]].reset_index(drop=True)


def hareket_atfet(hareketler, donem, kesit):
    """Her hareketi, hareket tarihinde dosyayı elinde tutan avukata yazar.

    Kesitten sonraki hareket alınmaz. Kapsamdaki bir döneme düşmeyen hareketin
    avukat_kodu boş kalır: bu tutar avukata yazılamayan tahsilattır.
    """
    zorunlu = ("dosya_no", "hareket_tarihi", "tutar")
    sutun_kontrol(hareketler, zorunlu, "hareketler")
    bos_kontrol(hareketler, zorunlu, "hareketler")
    tablo = hareketler[list(zorunlu)].assign(hareket_tarihi=gun(hareketler["hareket_tarihi"]),
                                             tutar=hareketler["tutar"].astype(float))
    try:
        toplam = math.fsum(tablo["tutar"].abs())
    except OverflowError:
        toplam = float("inf")
    if not math.isfinite(toplam):
        raise ValueError("hareketler: tutar sonlu değil ya da toplam sayısal aralığı aşıyor")
    tablo = tablo[tablo["hareket_tarihi"] <= tek_gun(kesit)].reset_index(drop=True)
    eslesme = tablo[["dosya_no", "hareket_tarihi"]].reset_index().merge(
        donem[["dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi"]], on="dosya_no")
    tarih = eslesme["hareket_tarihi"]
    icinde = (tarih >= eslesme["atama_tarihi"]) & (
        eslesme["bitis_tarihi"].isna() | (tarih < eslesme["bitis_tarihi"]))
    avukat = eslesme.loc[icinde].set_index("index")["avukat_kodu"]
    # Hiçbir hareket eşleşmese de sütun metin türünde kalır (birleştirmeler tür uyuşmazlığına
    # düşmez).
    return tablo.assign(avukat_kodu=pd.Series(tablo.index.map(avukat), index=tablo.index,
                                              dtype=object))
