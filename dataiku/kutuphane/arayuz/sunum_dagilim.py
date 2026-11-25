"""Dağılım grafiklerinin verisi: sonuç tablolarından sayım ve seçim (puan hesaplanmaz).

- Puan dağılımı: her sütun ve birleşik puan için 5 puanlık kutularda avukat sayısı (yalnız
  geçerli ve yayımlanan puanlar; ekrandaki ve birleşik puandaki gibi 2 ondalığa yarım yukarı
  yuvarlanmış). Birleşik puan kutusunun notu sonuç tablosundaki
  performans_notu'dur; not eşikleri 5'in katı olduğundan her kutu tek nota düşer. Sütun
  puanlarında not yoktur. 100 puan son kutudadır. taban: beklenen düzeyin puanı (göreli ölçülen
  tahsilat ve süre sütunlarında; parametreden), öteki sütunlarda boş.
- Tahsilat ve portföy: her avukatın olgun dosya sayısı ve tahsilat puanı (güven ayarının
  etkisi: az dosyada puan 75'e yakın). Puanı olmayan avukat puansız gelir.
- Avukatın konumu: seçili avukatın her sütundaki yüzdeliği ve o sütunun dağılımı. Yüzdelik,
  puanı avukatınkinden düşük ya da ona eşit olan öteki avukatların oranıdır: en yüksek puan
  (eşitlerle birlikte) 100, en düşük tek puan 0; tek avukat 100.
- Kriter 1 süre dağılımı: arayuz/dagilim_sure.py.
"""
import pandas as pd

from avukat_perf.ortak import yuvarla
from avukat_perf.params_sema import SUTUNLAR

KUTU = 5
BIRLESIK = "birlesik"


def _puanlar(puan, birlesik):
    """(sutun, avukat_kodu, puan, not_adi): geçerli sütun puanları ve yayımlanan birleşik puan."""
    parcalar = []
    if puan is not None and not puan.empty:
        gecerli = puan[puan["durum"] == "GECERLI"]
        parcalar.append(gecerli[["sutun", "avukat_kodu", "puan"]].assign(not_adi=None))
    if birlesik is not None and not birlesik.empty:
        yay = birlesik[birlesik["durum"] == "YAYIMLANDI"]
        parcalar.append(pd.DataFrame({"sutun": BIRLESIK, "avukat_kodu": yay["avukat_kodu"],
                                      "puan": yay["birlesik_puan"],
                                      "not_adi": yay["performans_notu"]}))
    if not parcalar:
        return None
    tablo = pd.concat(parcalar, ignore_index=True)
    tablo = tablo[tablo["puan"].notna()]
    return tablo.assign(puan=tablo["puan"].map(yuvarla))


def _kutular(tablo):
    """Sütun başına 0-100 aralığının bütün kutuları; boş kutu 0."""
    alt = (tablo["puan"] // KUTU * KUTU).clip(lower=0, upper=100 - KUTU).astype(int)
    sayim = tablo.assign(alt=alt).groupby(["sutun", "alt"]).agg(
        adet=("puan", "size"), not_adi=("not_adi", "first")).reset_index()
    sira = [ad for ad in SUTUNLAR + (BIRLESIK,) if ad in set(tablo["sutun"])]
    izgara = pd.MultiIndex.from_product([sira, range(0, 100, KUTU)], names=["sutun", "alt"])
    sayim = sayim.set_index(["sutun", "alt"]).reindex(izgara).reset_index()
    ozet = tablo.groupby("sutun")["puan"].agg(ortanca="median", toplam="size")
    sayim = sayim.join(ozet, on="sutun").assign(ust=sayim["alt"] + KUTU)
    return sayim.assign(adet=sayim["adet"].fillna(0).astype(int))


def tabanlar(params):
    """Göreli ölçülen sütunlarda beklenen düzeyin puanı."""
    return {"tahsilat": params["tahsilat"]["taban"], "sure": params["sure_puani"]["taban"]}


def puan_dagilimi(puan, birlesik, params):
    """Genel Bakış: sütun ve birleşik puan dağılımı (kutu kayıtları)."""
    tablo = _puanlar(puan, birlesik)
    if tablo is None or tablo.empty:
        return None
    sayim = _kutular(tablo)
    return sayim.assign(taban=sayim["sutun"].map(tabanlar(params)))


def tahsilat_dosya(tahsilat_avukat, params):
    """Her avukat: olgun dosya sayısı (n, elde tutma payıyla kesirli) ve tahsilat puanı."""
    if tahsilat_avukat is None or tahsilat_avukat.empty:
        return None
    tablo = tahsilat_avukat[["avukat_kodu", "n", "puan", "durum"]]
    tablo = tablo.sort_values(["n", "avukat_kodu"]).rename(columns={"n": "olgun_dosya"})
    return tablo.assign(taban=tabanlar(params)["tahsilat"])


def konum(puan, birlesik, kod):
    """Seçili avukatın her sütundaki puanı ve yüzdeliği, sütunun dağılımıyla."""
    tablo = _puanlar(puan, birlesik)
    if tablo is None or tablo.empty:
        return None
    sayim = _kutular(tablo)
    yuzdelik = tablo.groupby("sutun")["puan"].rank(method="max", pct=False) - 1
    adet = tablo.groupby("sutun")["puan"].transform("size")
    tablo = tablo.assign(yuzdelik=(yuzdelik / (adet - 1).where(adet > 1)).fillna(1.0) * 100)
    secili = tablo[tablo["avukat_kodu"] == kod].set_index("sutun")
    return sayim.assign(avukat_puani=sayim["sutun"].map(secili["puan"]),
                        yuzdelik=sayim["sutun"].map(secili["yuzdelik"]))
