"""Tahsilat evreni: dosya tablosunun denetimi, olgun dosyalar, rücu tutarı ve dosya yaşı bandı.

Olgun dosya: kesitte rücuya verilişten bu yana branşının izleme süresini (olgunluk_ay)
doldurmuş dosya; olgunluk günü dahildir. Bant sınırına eşit tutar üst banda girer. Yaş bandı,
dosyanın kesitte tamamladığı yaş sınırı (yas_bantlari, ay) sayısıdır: 0 ilk sınırdan genç dosya;
sınır günü dahildir. Tahsilat dosyanın ömrüne yayıldığı için beklenen değerler aynı yaştaki
dosyalardan kurulur; yoksa portföyü yeni olan avukat eski olana göre düşük görünür.
"""
import math

import pandas as pd

from avukat_perf.ortak import anahtar_kontrol, bos_kontrol, gun, sutun_kontrol, tek_gun

DOSYA_SUTUNLARI = ("dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi")
SONSUZ = float("inf")


def dosyalari_hazirla(dosyalar):
    """Dosya tablosunu denetler; tarihi güne, rücu tutarını sayıya çevirir."""
    sutun_kontrol(dosyalar, DOSYA_SUTUNLARI, "dosyalar")
    bos_kontrol(dosyalar, DOSYA_SUTUNLARI, "dosyalar")
    anahtar_kontrol(dosyalar, ("dosya_no",), "dosyalar")
    tablo = dosyalar[list(DOSYA_SUTUNLARI)].assign(
        rucuya_verilis_tarihi=gun(dosyalar["rucuya_verilis_tarihi"]),
        rucu_tutari=dosyalar["rucu_tutari"].astype(float))
    try:
        toplam = math.fsum(tablo["rucu_tutari"].abs())
    except OverflowError:
        toplam = float("inf")
    if not math.isfinite(toplam):
        raise ValueError("dosyalar: rücu tutarı sonlu değil ya da toplam sayısal aralığı aşıyor")
    if (tablo["rucu_tutari"] < 0).any():
        raise ValueError("dosyalar: rücu tutarı negatif olan satır var")
    return tablo


def bantli_dosyalar(dosyalar, kesit, tah):
    """Denetlenmiş dosyalar, tutar_bandi ve yas_bandi sütunlarıyla."""
    return yas_bandi_ekle(tutar_bandi_ekle(dosyalari_hazirla(dosyalar), tah), kesit, tah)


def olgun_dosyalar(dosyalar, kesit, tah):
    """Kesitte olgunlaşmış dosyalar, tutar_bandi ve yas_bandi sütunlarıyla.

    Olgunluk günü dahildir. Bant sınırına eşit tutar üst banda girer; sınır yoksa tek bant.
    """
    return olgunlar(bantli_dosyalar(dosyalar, kesit, tah), kesit, tah)


def olgunlar(tablo, kesit, tah):
    """Bantlı dosya tablosundan kesitte olgunlaşmış olanlar."""
    aylar = tablo["brans"].map(tah["olgunluk_ay"]).fillna(tah["olgunluk_ay"]["DIGER"])
    sinir = [tarih + pd.DateOffset(months=int(ay))
             for tarih, ay in zip(tablo["rucuya_verilis_tarihi"], aylar)]
    olgun = pd.Series(sinir, index=tablo.index, dtype="datetime64[ns]") <= tek_gun(kesit)
    return tablo[olgun].reset_index(drop=True)


def tutar_bandi_ekle(tablo, tah):
    """Rücu tutarına göre bant numarası (0'dan); sınıra eşit tutar üst banda girer."""
    bantlar = [-SONSUZ] + list(tah["tutar_bantlari"]) + [SONSUZ]
    bant = pd.cut(tablo["rucu_tutari"], bantlar, right=False, labels=False)
    return tablo.assign(tutar_bandi=bant.astype("int64"))


def yas_sinirlari(verilis, tah):
    """Her yaş sınırı için dosya başına sınır günü (Series listesi): rücuya veriliş + n ay."""
    tekil = list(verilis.drop_duplicates())
    return [pd.to_datetime(verilis.map({v: v + pd.DateOffset(months=int(ay)) for v in tekil}))
            for ay in tah["yas_bantlari"]]


def yas_bandi(tarih, sinirlar):
    """Tarihte dosyanın tamamladığı yaş sınırı sayısı; sınır günü dahildir. Tutar grubundaki
    (kesitte) ve sıklık ile güncellikteki (her gün, olay günü) yaş bandının tek tanımı."""
    bant = pd.Series(0, index=tarih.index, dtype="int64")
    for sinir in sinirlar:
        bant = bant + (sinir <= tarih).astype("int64")
    return bant


def yas_bandi_ekle(tablo, kesit, tah):
    """Kesitte dosya yaşı bandı: rücuya verilişten bu yana tamamlanan sınır (ay) sayısı."""
    kesit = pd.Series(tek_gun(kesit), index=tablo.index)
    sinirlar = yas_sinirlari(tablo["rucuya_verilis_tarihi"], tah)
    return tablo.assign(yas_bandi=yas_bandi(kesit, sinirlar))


def yas_etiketleri(tah):
    """Yaş bandı numarası -> etiket ("0–12 ay", ..., "84+ ay"); sınır yoksa tek etiket."""
    sinirlar = [0] + [int(ay) for ay in tah["yas_bantlari"]]
    etiket = {sira: "{}–{} ay".format(alt, ust)
              for sira, (alt, ust) in enumerate(zip(sinirlar, sinirlar[1:]))}
    etiket[len(sinirlar) - 1] = "{}+ ay".format(sinirlar[-1]) if len(sinirlar) > 1 else "Tüm yaşlar"
    return etiket
