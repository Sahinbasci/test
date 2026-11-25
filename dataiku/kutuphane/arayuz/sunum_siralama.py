"""Genel Bakış'taki avukat sıralama tablosu ve avukat listesinin sırası.

Liste birleşik puana göre (puansız en sonda), tablo genel sıraya göre (sırasız en sonda).
gerceklesen_beklenen: tahsilat sonucunun gerçekleşen ÷ beklenen oranı (tahsilat ÷ rücu tutarı
olan tahsilat_orani ile karıştırılmasın). Yeterli veri işareti tahsilat ve süre sonucundan.
"""
from avukat_perf.mantik import dogru_mu
from arayuz.temel import kayitlar, secili


def _avukatlar(tablolar):
    birlesik, avukat = tablolar.get("sonuc_birlesik"), tablolar.get("model_avukat")
    if birlesik is None:
        return None
    if avukat is not None:
        birlesik = birlesik.merge(avukat[["avukat_kodu", "unvan", "calisma_durumu"]],
                                  on="avukat_kodu", how="left")
    puan = birlesik["birlesik_puan"].fillna(-1)
    return birlesik.assign(_puan=puan).sort_values(["_puan", "avukat_kodu"],
                                                   ascending=[False, True]).drop(columns="_puan")


YETERLI = {"tahsilat": "sonuc_tahsilat_avukat", "sure": "sonuc_sure"}  # yeterli veri işareti


def _yeterli(t, kod, tablo):
    """Avukatın sütun sonucundaki yeterli veri işareti (sonuç yoksa boş)."""
    sonuc = secili(t(tablo), "avukat_kodu", kod)
    return None if sonuc is None or sonuc.empty else dogru_mu(sonuc["yeterli"].iloc[0])


def avukat_tablosu(tablolar):
    tablo = _avukatlar(tablolar)
    if tablo is None:
        return []
    tahsilat, portfoy = tablolar.get("sonuc_tahsilat_avukat"), tablolar.get("sonuc_portfoy")
    if tahsilat is not None:  # gerçekleşen ÷ beklenen (tahsilat ÷ rücu değil: tahsilat_orani)
        tablo = tablo.merge(tahsilat[["avukat_kodu", "oran", "yeterli"]].rename(columns={
            "oran": "gerceklesen_beklenen", "yeterli": "tahsilat_yeterli"}), on="avukat_kodu",
            how="left")
    sure = tablolar.get("sonuc_sure")
    if sure is not None:
        tablo = tablo.merge(sure[["avukat_kodu", "yeterli"]].rename(columns={
            "yeterli": "sure_yeterli"}), on="avukat_kodu", how="left")
    if portfoy is not None:
        aktif = portfoy.groupby("avukat_kodu", as_index=False)["aktif_dosya"].sum()
        tablo = tablo.merge(aktif, on="avukat_kodu", how="left")
    sira = tablo["genel_sira"].fillna(10 ** 6)
    tablo = tablo.assign(_sira=sira).sort_values(["_sira", "avukat_kodu"]).drop(columns="_sira")
    return kayitlar("genel.avukat_tablosu", tablo)
