"""Bayrak olay kaydı: türetme, yalnız ekleyerek birleştirme ve çelişki tespiti.

Olay tarihi eşik tarihidir, çalışma tarihi değil. Aynı veri ve kesitle iki kez çalışmak
aynı satırları üretir; birleştirme anahtarı bu yüzden çift kaydı önler. Kayıtlı olay
silinmez ve değiştirilmez; yeni hesapla çelişen olay düzeltme incelemesine gider.
Anahtar esasın kaynağını da taşır (esas_kaynagi: dava_takip ya da yedek; değerlendirmede
sütun yoksa dava_takip): yedek yoldan dava takibe geçişte yedek yolun olayları kalır ama yeni
kaynağın hesabıyla karşılaştırılmaz (çelişki sayılmaz). Sütunu taşımayan eski kayıt dava_takip
sayılır.
"""
import pandas as pd

from avukat_perf.bayrak import BAYRAKLAR
from avukat_perf.ortak import gun, tek_gun

DONEM_ANAHTARI = ["dosya_no", "avukat_kodu", "atama_tarihi"]
ANAHTAR = DONEM_ANAHTARI + ["kriter", "seviye", "esas_kaynagi"]
DAVA_TAKIP, YEDEK = "dava_takip", "yedek"


def kaynakli(tablo):
    """esas_kaynagi sütunu olmayan ya da boş olan (eski) satırlar dava_takip sayılır."""
    kaynak = tablo["esas_kaynagi"] if "esas_kaynagi" in tablo.columns else None
    return tablo.assign(esas_kaynagi=DAVA_TAKIP if kaynak is None else kaynak.fillna(DAVA_TAKIP))


def olaylar(degerlendirme, kriter):
    """Değerlendirme tablosundaki oluşmuş bayrakları olay satırlarına çevirir.

    Gereken sütunlar: dönem anahtarı, olcum_sonu, esik_sari, esik_turuncu, esik_kirmizi.
    """
    parcalar, degerlendirme = [], kaynakli(degerlendirme)
    for bayrak in BAYRAKLAR:
        esik = degerlendirme["esik_" + bayrak.lower()]
        secili = degerlendirme[esik <= degerlendirme["olcum_sonu"]]
        parcalar.append(secili[DONEM_ANAHTARI + ["esas_kaynagi"]].assign(
            kriter=kriter, seviye=bayrak, olay_tarihi=esik[secili.index]))
    tablo = pd.concat(parcalar, ignore_index=True)[
        DONEM_ANAHTARI + ["kriter", "seviye", "olay_tarihi", "esas_kaynagi"]]
    return tablo.sort_values(DONEM_ANAHTARI + ["olay_tarihi"]).reset_index(drop=True)


def _hizala(tablo):
    return kaynakli(tablo).assign(atama_tarihi=gun(tablo["atama_tarihi"]),
                                  olay_tarihi=gun(tablo["olay_tarihi"]))


def olay_birlestir(mevcut, yeni):
    """Yalnız ekler: anahtarı kayıtlı olan olay yeniden yazılmaz, kayıtlı olay silinmez."""
    yeni = _hizala(yeni)
    if mevcut is None or mevcut.empty:
        return yeni.reset_index(drop=True)
    mevcut = _hizala(mevcut)
    birlesim = yeni.merge(mevcut[ANAHTAR].drop_duplicates(), on=ANAHTAR, how="left",
                          indicator=True)
    eklenecek = birlesim[birlesim["_merge"] == "left_only"].drop(columns="_merge")
    return pd.concat([mevcut, eklenecek], ignore_index=True)


def celisen_olaylar(mevcut, yeni, kesit):
    """Kesite kadar kayda geçmiş olup yeni hesapta çıkmayan ya da tarihi değişen olaylar.

    Boş olmayan sonuç, kaynak veride geriye dönük değişiklik olduğunu gösterir.
    """
    sutunlar = ANAHTAR + ["olay_tarihi", "olay_tarihi_yeni"]
    if mevcut is None or mevcut.empty:
        return pd.DataFrame(columns=sutunlar)
    mevcut, yeni = _hizala(mevcut), _hizala(yeni)
    eski = mevcut[mevcut["olay_tarihi"] <= tek_gun(kesit)]
    karsilastirma = eski.merge(yeni[ANAHTAR + ["olay_tarihi"]], on=ANAHTAR, how="left",
                               suffixes=("", "_yeni"))
    farkli = karsilastirma["olay_tarihi_yeni"] != karsilastirma["olay_tarihi"]
    return karsilastirma[farkli].reset_index(drop=True)
