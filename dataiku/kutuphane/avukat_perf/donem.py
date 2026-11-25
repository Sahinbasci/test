"""Dönem sonu: kesit, dönem puan tablosu, sonuç kontrolleri ve sürümlü yayın.

Dönem YYYY-AA biçimindedir; kesit dönemin son günüdür. Dönem puan tablosu uzun biçimdedir
(avukat, dönem, sütun, puan, durum). Kaynağı henüz gelmeyen sütun KAYNAK_BEKLENIYOR,
kaynağı gelip o avukatı içermeyen sütun VERI_YOK durumundadır.
Yayımlanan dönem değiştirilmez: aynı dönem yeniden yayımlanırken içerik ve hesap sürümü
(kurallar) aynıysa tablo değişmez (DEGISMEDI), biri farklıysa yeni yayın sürümü eklenir
(DUZELTME). Birleşik puan da yayın anında, o sürümün kurallarıyla bir kez hesaplanır ve
sürümüyle saklanır (surum_ekle). Arayüz son sürümü okur.
"""
import re

import pandas as pd

from avukat_perf.kalite import SONUC
from avukat_perf.ortak import birlestir, yuvarla
from avukat_perf.params_sema import SUTUNLAR

ICERIK = ["avukat_kodu", "sutun", "puan", "durum"]
SIRA = ["avukat_kodu", "donem", "sutun", "puan", "durum"]


def kesit(donem):
    """'2026-10' -> 2026-10-31."""
    if not re.match(r"^\d{4}-\d{2}$", str(donem)):
        raise ValueError("dönem YYYY-AA biçiminde olmalı")
    return (pd.Timestamp(donem + "-01") + pd.offsets.MonthEnd(1)).normalize()


def onceki_donem(tarih):
    """Tarihten bir önceki takvim ayı: 2026-11-01 -> '2026-10'."""
    return (pd.Timestamp(tarih).normalize().replace(day=1) - pd.Timedelta(days=1)).strftime(
        "%Y-%m")


def veri_kapsami(son_cekim, donem):
    """Dönem sonunu kapsayan başarılı gecelik çekim var mı (kesitten sonraki bir günde)."""
    eski = son_cekim is None or pd.Timestamp(son_cekim).normalize() <= kesit(donem)
    aciklama = "son başarılı gecelik çekim: {}".format(
        "yok" if son_cekim is None else pd.Timestamp(son_cekim).date())
    return pd.DataFrame([("donem", "VERI_KAPSAMI", "KALDI" if eski else "GECTI", int(eski), 0,
                          aciklama)], columns=SONUC)


def puan_tablosu(donem, sutun_tablolari, avukatlar, bekleme_nedeni=None):
    """sutun_tablolari: {sütun: (avukat_kodu, puan, durum) tablosu ya da None}.

    bekleme_nedeni: tablosu None olan sütunun durumu (varsayılan KAYNAK_BEKLENIYOR;
    ör. değerlendirme ölçeği teyit beklerken TEYIT_BEKLIYOR).
    """
    parcalar = []
    for sutun in SUTUNLAR:
        tablo = sutun_tablolari.get(sutun)
        durum = (bekleme_nedeni or {}).get(sutun, "KAYNAK_BEKLENIYOR") if tablo is None \
            else "VERI_YOK"
        parca = pd.DataFrame(columns=["avukat_kodu", "puan", "durum"]) if tablo is None \
            else tablo[["avukat_kodu", "puan", "durum"]]
        eksik = sorted(set(avukatlar) - set(parca["avukat_kodu"]))
        ek = pd.DataFrame({"avukat_kodu": eksik, "puan": float("nan"), "durum": durum})
        parca = birlestir([parca, ek], ["avukat_kodu", "puan", "durum"])
        parcalar.append(parca.assign(sutun=sutun))
    tablo = pd.concat(parcalar, ignore_index=True).assign(donem=donem)
    tablo["puan"] = tablo["puan"].astype(float)
    return tablo[SIRA].sort_values(["avukat_kodu", "sutun"]).reset_index(drop=True)


def sonuc_kontrolleri(tablo):
    """Yayından önce: puan aralığı, sütun tamlığı ve anahtar tekilliği (KALDI ise yayın yok)."""
    gecerli = tablo[tablo["durum"] == "GECERLI"]["puan"]
    aralik_disi = int((gecerli.isna() | (gecerli < 0) | (gecerli > 100)).sum())
    # Her avukatın sütunları tam olarak dört sütun adıdır (sayı değil ad karşılaştırılır).
    kume = tablo.groupby("avukat_kodu")["sutun"].agg(lambda s: frozenset(s))
    eksik_sutun = int((kume != frozenset(SUTUNLAR)).sum())
    yinelenen = int(tablo.duplicated(["avukat_kodu", "donem", "sutun"]).sum())
    satirlar = [("sonuc", "PUAN_ARALIGI", aralik_disi), ("sonuc", "SUTUN_TAMLIGI", eksik_sutun),
                ("sonuc", "YINELENEN", yinelenen)]
    return pd.DataFrame([(k, ad, "GECTI" if deger == 0 else "KALDI", deger, 0, "")
                         for k, ad, deger in satirlar], columns=SONUC)


def _icerik(tablo):
    """Puan, birleşik puanın ve notun kullandığı değerle (2 ondalık, yarım yukarı)."""
    secili = tablo[ICERIK].sort_values(["avukat_kodu", "sutun"]).reset_index(drop=True)
    return secili.assign(puan=secili["puan"].astype(float).map(yuvarla))


def yayinla(mevcut, yeni, donem, ek_bilgi):
    """(tablo, sonuç). ek_bilgi: calisma_kimligi, hesap_surumu, yayin_zamani sözlüğü."""
    yeni = yeni.assign(**ek_bilgi)
    if mevcut is None or mevcut.empty:
        return yeni.assign(yayin_surumu=1), "YENI"
    onceki = mevcut[mevcut["donem"] == donem]
    if onceki.empty:
        return pd.concat([mevcut, yeni.assign(yayin_surumu=1)], ignore_index=True), "YENI"
    son = onceki[onceki["yayin_surumu"] == onceki["yayin_surumu"].max()]
    ayni_kural = set(son["hesap_surumu"]) == {ek_bilgi["hesap_surumu"]}
    if ayni_kural and _icerik(son).equals(_icerik(yeni)):
        return mevcut, "DEGISMEDI"
    surum = int(onceki["yayin_surumu"].max()) + 1
    return pd.concat([mevcut, yeni.assign(yayin_surumu=surum)], ignore_index=True), "DUZELTME"


def surum_ekle(mevcut, yeni, donem, surum):
    """Bir dönemin yeni yayın sürümünün satırlarını ekler; önceki sürümlere dokunmaz.

    Aynı dönem ve sürümde, yarıda kesilmiş bir denemeden kalan satırlar önce çıkarılır.
    """
    if mevcut is None or mevcut.empty:
        return yeni.reset_index(drop=True)
    kalan = mevcut[~((mevcut["donem"] == donem) & (mevcut["yayin_surumu"] == surum))]
    return pd.concat([kalan, yeni], ignore_index=True)


def son_surum(tablo):
    """Her dönemin son yayın sürümü."""
    if tablo is None or tablo.empty:
        return tablo
    en_son = tablo.groupby("donem")["yayin_surumu"].transform("max")
    return tablo[tablo["yayin_surumu"] == en_son].reset_index(drop=True)
