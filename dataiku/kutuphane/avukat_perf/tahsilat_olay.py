"""Tahsilat puanının sayım bileşenleri: sıklık ve güncellik (avukat × branş başına O ve E).

Kişi-zaman yöntemi (dolaylı standardizasyon): gerçekleşen O, avukatın tahsilat yaptığı dosya-ay
sayısıdır; beklenen E = Σ avukatın maruziyeti (dosya-yıl) × aynı dosya grubundaki hız. Grup
(tahsilat.gruplama) branş, o günkü dosya yaşı bandı ve tutar bandıdır; hız aynı gruptaki diğer
avukatların olay ÷ maruziyetidir (referans), avukatın kendi olayı beklentisine girmez.
Dosyanın el değiştirmesi olay üretmez, kısa ya da uzun tutmak tek başına avantaj değildir (bkz.
tahsilat_maruz). Kapanan dosyanın süresi kapandığı gün biter.
- Sıklık: olgun dosyalar, rücuya verilişten kesite.
- Güncellik: bütün dosyalar, (kesit − guncellik_pencere_ay ay, kesit] penceresinde.
"""
import pandas as pd

from avukat_perf.ortak import BIR_GUN
from avukat_perf.pencere import sinirlar
from avukat_perf.tahsilat_maruz import kapanis_ustu, maruziyet, olaylar
from avukat_perf.referans import tahsilat_orani

ANAHTAR = ["avukat_kodu", "brans"]


def _say(dosya, donem, hareket, tah, ad):
    """dosya: dosya_no, brans, tutar_bandi, rucuya_verilis_tarihi, alt, ust."""
    dosya = dosya[dosya["ust"].notna() & (dosya["ust"] > dosya["alt"])]
    grup = list(tah["gruplama"])
    ek = dosya[["dosya_no", "brans", "tutar_bandi"]]
    maruz = maruziyet(donem, dosya, tah).merge(ek, on="dosya_no")
    olay = olaylar(hareket, dosya, tah).merge(ek, on="dosya_no")
    hiz = maruz.groupby(grup)["maruz"].sum().to_frame().join(
        olay.groupby(grup)["olay"].sum(), how="left").fillna(0.0)
    hiz[ad + "_hizi"] = hiz["olay"] / hiz["maruz"]  # grup tablosunda gösterilen genel hız
    anahtar = ["avukat_kodu"] + grup + [ad for ad in ("brans",) if ad not in grup]
    hucre = maruz.groupby(anahtar)["maruz"].sum().to_frame().join(
        olay.groupby(anahtar)["olay"].sum(), how="left").fillna(0.0).reset_index()
    hucre["e"] = hucre["maruz"] * tahsilat_orani(hucre, grup, "olay", "maruz", False)
    sonuc = hucre.groupby(ANAHTAR)[["e", "olay"]].sum()
    sonuc = sonuc.rename(columns={"olay": ad + "_o", "e": ad + "_e"}).reset_index()
    return sonuc[ANAHTAR + [ad + "_o", ad + "_e"]], hiz.reset_index()


def sayimlar(olgun, dosya, donem, hareket, kesit, tah, kapanis):
    """(sıklık tablosu, güncellik tablosu, sıklık grup hızları)."""
    ust = kapanis_ustu(olgun, hareket, kapanis, kesit).values
    s, hiz = _say(olgun.assign(alt=olgun["rucuya_verilis_tarihi"], ust=ust), donem, hareket,
                  tah, "siklik")
    pencere_bas, _ = sinirlar(kesit, tah["guncellik_pencere_ay"])
    ilk = pencere_bas + BIR_GUN
    verilis = dosya["rucuya_verilis_tarihi"]
    pencere = dosya.assign(alt=verilis.where(verilis > ilk, ilk),
                           ust=kapanis_ustu(dosya, hareket, kapanis, kesit).values)
    g, _ = _say(pencere, donem, hareket, tah, "guncellik")
    return s, g, hiz
