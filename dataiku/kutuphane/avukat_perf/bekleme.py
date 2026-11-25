"""Haklı bekleme: avukattan kaynaklanmayan, Şirket'in uygun gördüğü bekleme süreleri.

Kayıtlar düzeltme tablosundan gelir. Başlangıç ve bitiş günü dahildir. Bitişi boş ya da
kesitten sonra olan bekleme kesitte kesilir; kesitten sonra başlayan bekleme sayılmaz.
Aralıklar [başlangıç, bitiş + 1 gün) biçiminde tutulur.
"""
from avukat_perf.ortak import BIR_GUN, bos_kontrol, gun, sutun_kontrol

SUTUNLAR = ("dosya_no", "avukat_kodu", "baslangic", "bitis")


def araliklar(beklemeler, kesit):
    """(dosya_no, avukat_kodu) başına çakışmaları birleştirilmiş, sıralı aralıklar."""
    sonuc = {}
    if beklemeler is None or beklemeler.empty:
        return sonuc
    sutun_kontrol(beklemeler, SUTUNLAR, "beklemeler")
    bos_kontrol(beklemeler, ("dosya_no", "avukat_kodu", "baslangic"), "beklemeler")
    tablo = beklemeler.assign(baslangic=gun(beklemeler["baslangic"]),
                              bitis=gun(beklemeler["bitis"]))
    tablo = tablo[tablo["baslangic"] <= kesit]
    if (tablo["bitis"] < tablo["baslangic"]).any():
        raise ValueError("beklemeler: bitişi başlangıcından önce olan satır var")
    tablo = tablo.assign(bitis=tablo["bitis"].fillna(kesit)).sort_values("baslangic")
    for anahtar, grup in tablo.groupby(["dosya_no", "avukat_kodu"]):
        birlesik = []
        for bas, son in zip(grup["baslangic"], grup["bitis"]):
            son = min(son, kesit) + BIR_GUN
            if birlesik and bas <= birlesik[-1][1]:
                birlesik[-1][1] = max(birlesik[-1][1], son)
            else:
                birlesik.append([bas, son])
        sonuc[anahtar] = birlesik
    return sonuc


def kaydir(esik, atama, aralik_listesi):
    """Atamadan sonra ve eşikten önce başlayan bekleme günleri kadar eşiği ileri atar.

    Kaydırma yeni eşiğin önüne düşen sonraki beklemeyi de sayar; liste sıralı olmalıdır.
    """
    for bas, son in aralik_listesi:
        bas = max(bas, atama)
        if bas < esik and son > bas:
            esik = esik + (son - bas)
    return esik


def gun_sayisi(atama, olcum_sonu, aralik_listesi):
    """[atama, olcum_sonu) içine düşen bekleme günü sayısı."""
    toplam = 0
    for bas, son in aralik_listesi:
        toplam += max((min(son, olcum_sonu) - max(bas, atama)).days, 0)
    return toplam
