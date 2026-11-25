"""Tahsilat bileşenlerinin sunumu: avukat kartındaki branş tablosu ve aylık tahsilat tablosu."""
import pandas as pd

from avukat_perf.mantik import dogru_mu
from avukat_perf.portfoy import ATANAMAYAN
from arayuz.temel import kayitlar, secili

AYLIK_TABLO_AY = 12  # tabloda gösterilen son ay sayısı (sütun)


def brans_tablosu(tablolar, kod):
    """Avukatın branş satırları (olgun dosya sayısına göre azalan) ve bütün dosyaları için
    toplam satırı (toplam=True; avukatın tahsilat sonucundan)."""
    brans = secili(tablolar.get("sonuc_tahsilat_brans"), "avukat_kodu", kod)
    if brans is None or brans.empty:
        return []
    parcalar = [brans.sort_values(["n", "brans"], ascending=[False, True]).assign(toplam=False)]
    genel = secili(tablolar.get("sonuc_tahsilat_avukat"), "avukat_kodu", kod)
    if genel is not None and not genel.empty:
        parcalar.append(genel.assign(brans=None, toplam=True))
    return kayitlar("avukat.brans", pd.concat(parcalar, ignore_index=True, sort=False))


def aylik_tablo(aylik):
    """Avukat × ay tahsilatı: hesap anındaki ay ızgarasının son AYLIK_TABLO_AY ayı, tahsilatsız ay
    sıfır. toplam: avukatın bu aylardaki toplamı (sıralama için); avukata yazılamayan en sonda."""
    if aylik is None or aylik.empty or "ilk_ay" not in aylik.columns:
        return []
    ilk, son = aylik["ilk_ay"].iloc[0], aylik["son_ay"].iloc[0]
    aylar = [str(ay) for ay in pd.period_range(ilk, son, freq="M")][-AYLIK_TABLO_AY:]
    kismi = son if dogru_mu(aylik["son_ay_kismi"].iloc[0]) else None
    tutar = aylik[aylik["ay"].isin(aylar)].groupby(["avukat_kodu", "ay"])["tutar"].sum()
    izgara = pd.MultiIndex.from_product([sorted(aylik["avukat_kodu"].unique()), aylar],
                                        names=["avukat_kodu", "ay"])
    tablo = tutar.reindex(izgara, fill_value=0.0).reset_index()
    tablo["toplam"] = tablo.groupby("avukat_kodu")["tutar"].transform("sum")
    sira = tablo["toplam"].where(tablo["avukat_kodu"] != ATANAMAYAN, -float("inf"))
    tablo = tablo.assign(kismi=tablo["ay"] == kismi, _s=sira)
    return kayitlar("genel.aylik_avukat", tablo.sort_values(
        ["_s", "avukat_kodu", "ay"], ascending=[False, True, True]))
