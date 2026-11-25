"""Çalışma kaydı (yazma tarafı): her çalışmaya kimlik verilir; kaynak başına ve özet satırı.

durum: BASARILI, KALDI (son geçerli veri korundu), KAYNAK_BEKLENIYOR, HESAPLANMADI (zorunlu
başka kaynak bekleniyor). Özet satırı: uretilen ("tablo=satır" çiftleri), hesap_surumu,
hazirlik_surumu, golge (parametreyle açılan gölge mod; iki kriter), golge_zorunlu (yedek yolun
gölgesi; yalnız Kriter 1). Kayıttan türetilen
bilgiler (son başarılı gece, gölge aralıkları) hat/gecmis.py'de, yalnız eklenen tabloların
satır kaybı denetimi hat/butunluk.py'dedir. Zaman İstanbul saatidir.
"""
import uuid

import pandas as pd

from avukat_perf.ortak import SAAT_DILIMI

SUTUNLAR = ["calisma_kimligi", "tur", "kaynak", "yontem", "baslangic", "bitis",
            "cekim_tarihi", "satir_sayisi", "kalite_sonucu", "durum", "arsiv_yolu",
            "aciklama", "uretilen", "hesap_surumu", "hazirlik_surumu", "golge", "golge_zorunlu"]
OZET = "*"


def simdi():
    """İstanbul saatiyle şimdiki an, saat dilimsiz; sunucu UTC olsa da çekim günü doğru olur."""
    return pd.Timestamp.now(tz=SAAT_DILIMI).tz_localize(None)


def kimlik(zaman):
    """Örnek: C20261119020000-a1b2c3."""
    return "C" + pd.Timestamp(zaman).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]


def satir(calisma_kimligi, tur, kaynak, yontem, baslangic, cekim_tarihi):
    kayit = dict.fromkeys(SUTUNLAR)
    kayit.update(calisma_kimligi=calisma_kimligi, tur=tur, kaynak=kaynak, yontem=yontem,
                 baslangic=pd.Timestamp(baslangic), cekim_tarihi=pd.Timestamp(cekim_tarihi))
    return kayit


def tablo(satirlar):
    return pd.DataFrame(satirlar, columns=SUTUNLAR).astype({"satir_sayisi": float})


def kaydet(ortam, onceki, kayitlar, karar, ozet_satiri):
    """Kaynak satırlarına çalışma sonucunu işler, özet satırıyla kayda ekler."""
    durum = {"GECTI": "BASARILI", "KALDI": "KALDI",
             "KAYNAK_BEKLENIYOR": "HESAPLANMADI"}.get(karar, karar)
    for kayit in kayitlar:
        kayit["durum"] = kayit["durum"] or durum
        kayit["bitis"] = simdi()
    ozet = dict(ozet_satiri, durum=karar, kalite_sonucu=karar, bitis=simdi())
    if ozet.get("uretilen"):  # kaydın kendi satır sayısı da korunur (bkz. butunluk.veri_kaybi)
        toplam = (0 if onceki is None else len(onceki)) + len(kayitlar) + 1
        ozet["uretilen"] += ",calisma_kaydi={}".format(toplam)
    yeni = tablo(kayitlar + [ozet])
    ortam.tablo_yaz("calisma_kaydi", yeni if onceki is None else
                    pd.concat([onceki, yeni], ignore_index=True))


def kalite_ekle(ortam, sonuclar, cekim):
    """Kalite sonuçlarını önceki çalışmaların sonuçlarına ekler."""
    if not sonuclar:
        return
    eski = ortam.tablo_oku("kalite_sonucu")
    yeni = pd.concat(sonuclar, ignore_index=True).assign(cekim_tarihi=pd.Timestamp(cekim))
    ortam.tablo_yaz("kalite_sonucu", yeni if eski is None else
                    pd.concat([eski, yeni], ignore_index=True))
