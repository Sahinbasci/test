"""Tahsilat puanının tutar bileşeni: grup tahsilat oranı ve avukatın beklenen tahsilatı.

Oranlar yalnız avukata yazılan tahsilattan hesaplanır (Σ yazılan tahsilat ÷ Σ payla tartılmış
rücu tutarı). Grup tablosu grubun bütün oranını gösterir; avukatın beklentisi aynı gruptaki
diğer avukatların oranından kurulur (referans). Rücu tutarı sıfır olan dosyanın tahsilatı
sahibinin gerçekleşenine girer, ölçüt oranının payına girmez (paydada karşılığı yoktur; girseydi
diğer avukatların beklentisini yükseltirdi). Bu dosyaların evrenden çıkarılması Hukuk kararıdır.
"""
import pandas as pd

from avukat_perf.referans import tahsilat_orani


def grup_tablosu(pay, hareket, grup):
    """Grup başına dosya sayısı, rücu toplamı, avukata yazılan ve yazılamayan tahsilat."""
    tablo = pay.groupby(grup).agg(dosya_sayisi=("pay", "sum"),
                                  rucu_toplami=("maruziyet", "sum"))
    yazilan = hareket["avukat_kodu"].notna()
    tablo["atfedilen"] = hareket[yazilan].groupby(grup)["tutar"].sum()
    tablo["atanamayan"] = hareket[~yazilan].groupby(grup)["tutar"].sum()
    tablo = tablo.fillna(0.0)
    # Ekranda gösterilen grup oranı; beklenti diğer avukatların oranından gelir
    # (referans). Net tahsilatı eksi olan grupta (ör. ters kayıt) oran 0 gösterilir.
    oran = (tablo["atfedilen"] / tablo["rucu_toplami"]).where(
        (tablo["rucu_toplami"] > 0) & (tablo["atfedilen"] > 0), 0.0)
    return tablo.assign(oran=oran).reset_index()


def tutar(pay, hareket, grup, kirilim):
    """(grup tablosu, avukat × branş başına n, maruziyet, gerceklesen, beklenen).

    kirilim: grup sütunları ve brans. Beklenen = Σ diğer avukatların grup oranı × payla
    tartılmış rücu tutarı. hareket: kirilim ve rucu_tutari sütunlarıyla.
    """
    gruplar = grup_tablosu(pay, hareket, grup)
    anahtar = ["avukat_kodu"] + kirilim
    tablo = pd.concat([
        pay.groupby(anahtar).agg(n=("pay", "sum"), maruziyet=("maruziyet", "sum")),
        hareket.groupby(anahtar)["tutar"].sum().rename("gerceklesen"),
        hareket[hareket["rucu_tutari"] > 0].groupby(anahtar)["tutar"].sum().rename("referans")],
        axis=1).fillna(0.0)
    tablo = tablo.reset_index()
    oran = tahsilat_orani(tablo, grup, "referans", "maruziyet", True)  # 0 ya da eksi: ölçüt yok
    tablo["beklenen"] = tablo["maruziyet"] * oran
    return gruplar, tablo.groupby(["avukat_kodu", "brans"], as_index=False)[
        ["n", "maruziyet", "gerceklesen", "beklenen"]].sum()
