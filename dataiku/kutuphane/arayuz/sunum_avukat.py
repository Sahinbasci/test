"""Avukat sayfası verisi (Genel Bakış'taki avukat tablosu sunum_siralama.py'de).

Avukat kodu verilmezse listedeki ilk avukat (en yüksek birleşik puan) seçilir. Alt başlıklar
parametredeki sırayla, açıklama satırları sütun ve sıra numarasıyla sıralanır.
"""
import pandas as pd

from avukat_perf import donem
from avukat_perf.ortak import birlestir, yuvarla
from avukat_perf.params_sema import SUTUNLAR
from arayuz import sunum_dagilim, sunum_tahsilat
from arayuz.sunum_siralama import YETERLI, _avukatlar, _yeterli
from arayuz.temel import ay_izgarasi, kayitlar, secili

ACIKLAMA_SIRASI = {ad: sira for sira, ad in enumerate(SUTUNLAR + ("birlesik",))}


def avukat(tablolar, params, kod):
    liste = _avukatlar(tablolar)
    if liste is None or liste.empty:
        return {"avukat.liste": []}
    kod = kod if kod in set(liste["avukat_kodu"]) else liste["avukat_kodu"].iloc[0]
    t = tablolar.get
    sonuc = {"avukat.liste": kayitlar("avukat.liste", liste)}
    baslik = liste[liste["avukat_kodu"] == kod].assign(
        yayimlanan=int((liste["durum"] == "YAYIMLANDI").sum()))
    sonuc["avukat.baslik"] = kayitlar("avukat.baslik", baslik)
    puan = secili(t("sonuc_puan_guncel"), "avukat_kodu", kod)
    if puan is not None:
        # Puan ekrandaki ve birleşik puandaki gibi 2 ondalık (rengi gösterilen değerden).
        puan = puan.assign(_s=puan["sutun"].map(ACIKLAMA_SIRASI), puan=puan["puan"].map(
            yuvarla)).sort_values("_s")
        puan = puan.assign(yeterli=puan["sutun"].map(
            {sutun: _yeterli(t, kod, ad) for sutun, ad in YETERLI.items()}))
        sonuc["avukat.sutunlar"] = kayitlar("avukat.sutunlar", puan)
    aciklama = secili(t("sonuc_aciklama"), "avukat_kodu", kod)
    if aciklama is not None:
        sonuc["avukat.aciklama"] = kayitlar("avukat.aciklama", _aciklama(
            aciklama, puan, secili(t("sonuc_birlesik"), "avukat_kodu", kod)))
    sonuc["avukat.brans"] = sunum_tahsilat.brans_tablosu(tablolar, kod)
    for bilesen, tablo in (("avukat.tahsilat", "sonuc_tahsilat_avukat"),
                           ("avukat.kalite_davranis", "sonuc_kalite_davranis_sutun"),
                           ("avukat.sure", "sonuc_sure"), ("avukat.sure_ozet", "sonuc_sure_ozet")):
        sonuc[bilesen] = kayitlar(bilesen, secili(t(tablo), "avukat_kodu", kod))
    alt = secili(t("sonuc_kalite_davranis_alt"), "avukat_kodu", kod)
    if alt is not None:
        kodlar = params["kalite_davranis"]["alt_basliklar"]
        sira = {ad: no for no, ad in enumerate(kodlar["kalite"] + kodlar["davranis"])}
        sonuc["avukat.alt_basliklar"] = kayitlar("avukat.alt_basliklar", alt.assign(
            _s=alt["alt_baslik"].map(sira)).sort_values("_s"))
    mevcut = secili(t("sonuc_mevcut_degerlendirme"), "avukat_kodu", kod)
    if mevcut is not None:
        sira = {ad: no for no, ad in enumerate(params["kalite_davranis"]["mevcut_alanlar"])}
        sonuc["avukat.mevcut_degerlendirme"] = kayitlar(
            "avukat.mevcut_degerlendirme",
            mevcut.assign(_s=mevcut["alt_baslik"].map(sira)).sort_values("_s"))
    portfoy = secili(t("sonuc_portfoy"), "avukat_kodu", kod)
    if portfoy is not None:
        portfoy = portfoy.groupby("brans", as_index=False)[
            ["aktif_dosya", "toplam_dosya", "aktif_rucu_tutari"]].sum()
        sonuc["avukat.portfoy"] = kayitlar("avukat.portfoy", portfoy.sort_values(
            "toplam_dosya", ascending=False))
    aylik = t("sonuc_tahsilat_aylik")
    if aylik is not None:  # tahsilatı olmayan avukatta da ızgara sıfırla çizilir
        sonuc["avukat.aylik"] = kayitlar("avukat.aylik", ay_izgarasi(
            aylik, secili(aylik, "avukat_kodu", kod), ["tutar", "hareket_sayisi"]))
    sonuc["avukat.gecmis"] = _gecmis(t("birlesik_donem"), kod)
    sonuc["avukat.konum"] = kayitlar("avukat.konum", sunum_dagilim.konum(
        t("sonuc_puan_guncel"), t("sonuc_birlesik"), kod))
    return sonuc


def _aciklama(aciklama, puan, birlesik):
    """Açıklama satırları sütun ve sıra numarasıyla; her satırda sütunun ekrandaki puanı ve
    ağırlığı, birleşik satırlarında birleşik puan ve not (sonuç tablolarından). Açıklama satırı
    olmayan sütun için içeriksiz bir YOK satırı eklenir: ekran sütunun puanını ve ağırlığını
    (ör. bu fazda puana girmediğini) yine bilir."""
    eksik = [ad for ad in SUTUNLAR if ad not in set(aciklama["sutun"])]
    if eksik:
        aciklama = birlestir([aciklama, pd.DataFrame({
            "avukat_kodu": aciklama["avukat_kodu"].iloc[0] if len(aciklama) else None,
            "sutun": eksik, "sira": 0, "tur": "YOK", "metin": "",
            "etki": [float("nan")] * len(eksik)})], list(aciklama.columns))
    puanlar, agirliklar, notu = {}, {}, None
    if puan is not None:
        puanlar = dict(zip(puan["sutun"], puan["puan"]))
        if "agirlik" in puan.columns:
            agirliklar = dict(zip(puan["sutun"], puan["agirlik"]))
    if birlesik is not None and len(birlesik):
        puanlar["birlesik"] = yuvarla(birlesik["birlesik_puan"].iloc[0])
        notu = birlesik["performans_notu"].iloc[0]
    aciklama = aciklama.assign(
        _s=aciklama["sutun"].map(ACIKLAMA_SIRASI), puan=aciklama["sutun"].map(puanlar),
        agirlik=aciklama["sutun"].map(agirliklar),
        performans_notu=[notu if sutun == "birlesik" else None for sutun in aciklama["sutun"]])
    return aciklama.sort_values(["_s", "sira"])


def _gecmis(birlesik_donem, kod):
    """Her dönemin son yayın sürümü; puan ve not o sürümün kurallarıyla hesaplanmıştır."""
    gecmis = secili(donem.son_surum(birlesik_donem), "avukat_kodu", kod)
    if gecmis is None:
        return []
    gecmis = gecmis.sort_values("donem")
    return kayitlar("avukat.gecmis", gecmis.assign(yayin_zamani=pd.to_datetime(
        gecmis["yayin_zamani"])))
