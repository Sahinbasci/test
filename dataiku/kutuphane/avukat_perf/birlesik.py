"""Birleşik puan, performans notu ve genel sıralama.

Girdi uzun biçimdedir: avukat_kodu, sutun, puan, durum (puan_donem tablosundaki gibi).
Birleşik puana giren sütunlar params birlesik_sutunlar'dır (ilk fazda Süre ve Performans
girmez; ağırlıklar agirlik.py). Giren sütunların hepsi GECERLI olan avukat için birleşik puan
hesaplanır. Biri eksikse birleşik puan, not ve sıra yayımlanmaz; ağırlık diğer sütunlara
dağıtılmaz, eksik puan sıfır sayılmaz. Girmeyen sütunun puanı tabloda bilgi olarak durur.
Sütun puanları 2 ondalığa yuvarlanır; ağırlıklı toplam ondalık aritmetikle hesaplanıp yine 2
ondalığa yuvarlanır. Yuvarlama elle hesaptaki gibi yarım
yukarıdır; not yuvarlanmış puana göre verilir, böylece ekrandaki sayı ile not tutarlıdır.
Eşit puan aynı sırayı alır (1, 2, 2, 4); sıralama yalnız yayımlananlar arasındadır.
"""
from decimal import Decimal

import pandas as pd

from avukat_perf.ortak import (anahtar_kontrol, bos_kontrol, ondalik_yuvarla, sutun_kontrol,
                               yuvarla)
from avukat_perf import agirlik
from avukat_perf.params_sema import SUTUNLAR

GIRDI = ("avukat_kodu", "sutun", "puan", "durum")


def not_ver(puan, notlar):
    """Puanın eşiğine ulaştığı ilk not; notlar yüksekten düşüğe [ad, eşik] listesidir.

    Puan boşsa (NaN) hiçbir eşiğe ulaşmaz, sonuç None olur.
    """
    for ad, esik in notlar:
        if puan >= esik:
            return ad
    return None


def _gecerli_puanlar(sutun_puanlari):
    """GECERLI satırlar, puanı 2 ondalığa yuvarlanmış olarak."""
    sutun_kontrol(sutun_puanlari, GIRDI, "sutun_puanlari")
    bos_kontrol(sutun_puanlari, ("avukat_kodu", "sutun", "durum"), "sutun_puanlari")
    anahtar_kontrol(sutun_puanlari, ("avukat_kodu", "sutun"), "sutun_puanlari")
    if not sutun_puanlari["sutun"].isin(SUTUNLAR).all():
        raise ValueError("sutun_puanlari: tanımsız sütun adı var")
    gecerli = sutun_puanlari[sutun_puanlari["durum"] == "GECERLI"]
    puan = gecerli["puan"].astype(float)
    if (puan.isna() | (puan < 0) | (puan > 100)).any():
        raise ValueError("sutun_puanlari: GECERLI satırda puan boş ya da 0-100 dışında")
    return gecerli.assign(puan=puan.map(yuvarla))


def agirlikli_toplam(puanlar, agirliklar):
    """Σ ağırlık × puan, ondalık aritmetikle ve 2 ondalığa yarım yukarı: elle hesapla aynı.

    Kayan noktayla 0,35 × 85 + 0,25 × 85,58 + 0,30 × 84,5 + 0,10 × 85 = 84,9949… çıkar ve
    84,99 olurdu; doğru sonuç 84,995 → 85,00'tır.
    """
    toplam = sum(Decimal(repr(float(agirliklar[ad]))) * Decimal(repr(float(puan)))
                 for ad, puan in puanlar.items())
    return ondalik_yuvarla(toplam)


def birlestir(sutun_puanlari, params):
    """Avukat başına sütun puanları, birleşik puan, not, genel sıra ve yayın durumu."""
    gecerli = _gecerli_puanlar(sutun_puanlari)
    avukatlar = sorted(sutun_puanlari["avukat_kodu"].unique())
    genis = gecerli.pivot(index="avukat_kodu", columns="sutun", values="puan")
    genis = genis.reindex(index=avukatlar, columns=list(SUTUNLAR))
    etkin = list(agirlik.etkin_sutunlar(params))
    eksik = genis[etkin].isna()
    tam = ~eksik.any(axis=1)
    agirliklar = agirlik.sutun_agirliklari(params)
    birlesik = pd.Series([agirlikli_toplam(satir[etkin], agirliklar) if tamam else None
                          for (_, satir), tamam in zip(genis.iterrows(), tam)],
                         index=genis.index, dtype=float)
    sonuc = genis.assign(
        birlesik_puan=birlesik,
        performans_notu=[not_ver(puan, params["notlar"]) for puan in birlesik],
        genel_sira=birlesik.rank(method="min", ascending=False),
        durum=tam.map({True: "YAYIMLANDI", False: "EKSIK_SUTUN"}),
        eksik_sutunlar=[",".join(ad for ad in etkin if satir[ad])
                        for _, satir in eksik.iterrows()])
    return sonuc.rename_axis(columns=None).reset_index()
