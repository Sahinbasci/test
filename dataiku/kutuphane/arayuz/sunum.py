"""Sayfa verisi: sayfa adına göre bileşen kayıtlarını hazırlar (Genel Bakış ve ortak şerit).

sayfa(ad, tablolar, params, secim, okunamayan) -> {"sayfa": ad, "bilesenler": {kimlik: [kayıt]}}.
tablolar: sonuç tablosu adı -> DataFrame ya da None (henüz üretilmemiş); okunamayan: arka ucun
okuyamadığı tablo adları (şeride gelir). Parametre her yanıtta doğrulanır (gecenin kuralı).
Sayfalar: genel, avukat (secim["kod"]), sure, kurallar, veri. SECIMLER: sorgudan alınan
seçimler (avukat kodu ve Süre Takibi süzgeçleri); arka uç ve önizleme bunu kullanır.
"""
from avukat_perf.mantik import dogru_seri
from avukat_perf.params import dogrula
from avukat_perf.params_sema import SUTUNLAR
from avukat_perf.portfoy import ATANAMAYAN
from arayuz import (dagilim_brans, sunum_avukat, sunum_dagilim, sunum_kural, sunum_ortak,
                    sunum_siralama, sunum_sure, sunum_tahsilat)
from arayuz.sozlesme import BILESENLER
from arayuz.temel import (ay_izgarasi, guncel_tablolar, kayitlar, oran, seviye_sirala, tek,
                          topla)

BEKLEME = ("KAYNAK_BEKLENIYOR", "TEYIT_BEKLIYOR", "GOLGE_MOD")
TABLOLAR = sorted({tablo for bilesen in BILESENLER.values() for tablo in bilesen["kaynak"]})
SAYFALAR = ("genel", "avukat", "sure", "kurallar", "veri")
SECIMLER = ("kod",) + tuple(sunum_sure.FILTRE)


def _sutun_durumu(puan):
    satirlar = []
    for sutun in SUTUNLAR:
        parca = puan[puan["sutun"] == sutun]
        gecerli = parca[parca["durum"] == "GECERLI"]
        bekleyen = parca[parca["durum"].isin(BEKLEME)]
        bekleme = bekleyen["durum"].value_counts().index[0] if len(bekleyen) and \
            gecerli.empty else None
        satirlar.append({"sutun": sutun, "gecerli": len(gecerli),
                         "ortalama": gecerli["puan"].mean() if len(gecerli) else None,
                         "gecersiz": len(parca) - len(gecerli) - len(bekleyen),
                         "bekleme_nedeni": bekleme})
    return satirlar


def _yillik_sirasi(yillik):
    """İçinde bulunulan yılın tahsilatına göre azalan; avukata yazılamayan en sonda."""
    bu_yil = yillik[dogru_seri(yillik["yil_ici"])].set_index("avukat_kodu")["tutar"]
    sira = yillik["avukat_kodu"].map(bu_yil).where(yillik["avukat_kodu"] != ATANAMAYAN,
                                                   -float("inf"))
    return yillik.assign(_s=sira).sort_values(["_s", "avukat_kodu", "yil"],
                                               ascending=[False, True, True])


def genel(tablolar, params):
    t = tablolar.get
    portfoy, grup, ozet, birlesik = (t("sonuc_portfoy"), t("sonuc_tahsilat_grup"),
                                     t("sonuc_sure_ozet"), t("sonuc_birlesik"))
    yayin = None if birlesik is None else int((birlesik["durum"] == "YAYIMLANDI").sum())
    sonuc = {"genel.kpi": tek("genel.kpi", {
        "aktif_dosya": topla(portfoy, "aktif_dosya"),
        "aktif_rucu_tutari": topla(portfoy, "aktif_rucu_tutari"),
        "tahsilat_orani": oran(topla(grup, "atfedilen"), topla(grup, "rucu_toplami")),
        "atanamayan_tahsilat": topla(grup, "atanamayan"),
        "acik_sari": topla(ozet, "acik_sari"), "acik_turuncu": topla(ozet, "acik_turuncu"),
        "acik_kirmizi": topla(ozet, "acik_kirmizi"), "sure_verisi": ozet is not None,
        "yayimlanan": yayin, "avukat_sayisi": None if birlesik is None else len(birlesik)})}
    puan = t("sonuc_puan_guncel")
    sonuc["genel.sutun_durumu"] = [] if puan is None else [
        tek("genel.sutun_durumu", satir)[0] for satir in _sutun_durumu(puan)]
    sonuc["genel.dagilim"] = kayitlar("genel.dagilim", sunum_dagilim.puan_dagilimi(
        puan, birlesik, params))
    sonuc["genel.tahsilat_dosya"] = kayitlar("genel.tahsilat_dosya", sunum_dagilim.tahsilat_dosya(
        t("sonuc_tahsilat_avukat"), params))
    sonuc["genel.brans_oran"] = kayitlar("genel.brans_oran", dagilim_brans.oran_kutulari(
        t("sonuc_tahsilat_brans")))
    sonuc["genel.avukat_tablosu"] = sunum_siralama.avukat_tablosu(tablolar)
    if portfoy is not None:  # bant etiketleri hesap anındaki sınırlardan (sonuç tablosunda)
        brans = portfoy.groupby("brans", as_index=False)[["aktif_dosya", "aktif_rucu_tutari"]]
        sonuc["genel.brans"] = kayitlar("genel.brans", brans.sum().sort_values(
            "aktif_dosya", ascending=False))
        bant = portfoy.assign(bant_etiketi=portfoy.get("bant_etiketi")).groupby(
            "tutar_bandi", as_index=False).agg(
            aktif_dosya=("aktif_dosya", "sum"), bant_etiketi=("bant_etiketi", "first"))
        sonuc["genel.bant"] = kayitlar("genel.bant", bant)
    aylik = t("sonuc_tahsilat_aylik")
    if aylik is not None:
        yazilamayan = aylik["avukat_kodu"] == ATANAMAYAN
        ay = aylik.assign(yazilan=aylik["tutar"].where(~yazilamayan, 0.0),
                          yazilamayan=aylik["tutar"].where(yazilamayan, 0.0))
        sonuc["genel.aylik"] = kayitlar("genel.aylik", ay_izgarasi(
            aylik, ay, ["yazilan", "yazilamayan"]))
    yillik = t("sonuc_tahsilat_yillik")
    if yillik is not None:
        sonuc["genel.yillik"] = kayitlar("genel.yillik", _yillik_sirasi(yillik))
    eposta = t("sonuc_eposta")
    if eposta is not None:
        sonuc["genel.oncelikli"] = kayitlar("genel.oncelikli", seviye_sirala(eposta).head(8))
    sonuc["genel.gruplar"] = kayitlar("genel.gruplar", grup)
    sonuc["genel.aylik_avukat"] = sunum_tahsilat.aylik_tablo(aylik)
    return sonuc


def sayfa(ad, tablolar, params, secim=None, okunamayan=()):
    if ad not in SAYFALAR:
        raise ValueError("bilinmeyen sayfa")  # girdi iletiye konmaz
    secim, tablolar, hatalar = secim or {}, guncel_tablolar(tablolar), dogrula(params)
    if ad == "genel":
        bilesenler = genel(tablolar, params)
    elif ad == "avukat":
        bilesenler = sunum_avukat.avukat(tablolar, params, secim.get("kod"))
    elif ad == "sure":
        bilesenler = sunum_sure.sure(tablolar, secim)
    elif ad == "kurallar":
        bilesenler = sunum_kural.kurallar(params, hatalar)
    else:
        bilesenler = sunum_kural.veri(tablolar)
    bilesenler["ortak.durum"] = sunum_ortak.ortak_durum(tablolar, params, okunamayan, hatalar)
    bilesenler["ortak.adlar"] = sunum_ortak.adlar(params)
    return {"sayfa": ad, "bilesenler": bilesenler}
