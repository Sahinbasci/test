"""Ölçüm penceresi: (kesit − n ay, kesit] aralığı.

Pencereyi kullanan bütün hesaplar (süre puanı ve özeti, kalite ve davranış, tahsilat güncelliği)
aralığı buradan alır; sınır kuralı tek yerde tanımlıdır. haric verilirse o gün aralıklarına
düşen tarih pencerede sayılmaz: gölge gecelerinin kapsadığı günlerdeki düşüm puana girmez.
Aylık grafik takvim aylarıyla çalışır (takvim_aylari): kesitin ayıyla biten n ay; ilk ay ayın
1'inden başlar, son ay kesite kadardır.
"""
import pandas as pd

from avukat_perf.ortak import tek_gun


def sinirlar(kesit, ay):
    """(bas, son): pencerede olan tarih bas < tarih <= son."""
    son = tek_gun(kesit)
    return son - pd.DateOffset(months=ay), son


def aralik_disinda(tarih, haric, kriter=None):
    """Tarih serisinden hiçbir hariç aralığa (alt < gün <= ust; alt None: sınırsız) düşmeyenler.

    haric {kriter: aralıklar} ise her satır kendi kriterinin aralıklarıyla sınanır (kriter
    serisi gerekir): yedek yolun zorunlu gölgesi yalnız Kriter 1'in günlerini kapsar."""
    if isinstance(haric, dict):
        if kriter is None:
            raise ValueError("kriter bazında hariç aralık için kriter sütunu gerekir")
        sonuc = pd.Series(True, index=tarih.index)
        for ad, araliklar in haric.items():
            sonuc = sonuc & (aralik_disinda(tarih, araliklar) | (kriter != ad))
        return sonuc
    sonuc = pd.Series(True, index=tarih.index)
    for alt, ust in haric or []:
        icinde = tarih <= ust
        if alt is not None:
            icinde = icinde & (tarih > alt)
        sonuc = sonuc & ~icinde
    return sonuc


def takvim_aylari(kesit, ay):
    """(ilk gün, ["YYYY-AA", ...]): kesitin ayıyla biten ay adet takvim ayı."""
    son = tek_gun(kesit)
    ilk = (son - pd.DateOffset(months=ay - 1)).replace(day=1)
    return ilk, [str(donem) for donem in pd.period_range(ilk, son, freq="M")]


def ay_sonu_mu(kesit):
    """Kesit ayın son günü mü (son ay tam mı)."""
    gun = tek_gun(kesit)
    return gun + pd.offsets.MonthEnd(0) == gun


def icinde(tarih, kesit, ay, haric=None, kriter=None):
    """Tarih serisinden pencerede olanlar (bool); boş tarih ve hariç aralıktaki tarih değildir."""
    bas, son = sinirlar(kesit, ay)
    return (tarih > bas) & (tarih <= son) & aralik_disinda(tarih, haric, kriter)
