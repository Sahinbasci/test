"""Veri kalite kapısı: şema, tür, boşluk, anahtar, satır sayısı ve tarih (ilişki ve mutabakat
kalite_iliski.py'de). Hukuki Kalite sütun puanı bu modülde değil, kalite_davranis.py'dedir.

Her denetim bir satır üretir: kaynak, kontrol, durum (GECTI, UYARI, KALDI), deger, esik,
aciklama. Bir KALDI varsa o gecenin hesabı yapılmaz, son geçerli veri korunur (karar).
denetle tabloyu şemadaki türlere çevirir (kalite_tur.py) ve yalnız şema alanlarını bırakır;
çevrilemeyen değer KALDI sayılır. Türkçe ya da belirsiz biçimli metin sayı (15.000, 83,763)
kaynak ayarında sayi_bicimi (tr ya da en) verilmemişse KALDI: tutar bin kat yanlış okunurdu.
Boş tablo zorunlu kaynakta, gözlem kaynağında (esas, süreç, takip görüntüsü) ve önceki
başarılı çekimi dolu olan isteğe bağlı kaynakta KALDI, ilk kez boş gelen isteğe bağlıda UYARI.
Satır sapması önceki çekimi sapma_en_az_satir'dan küçük tabloda denetlenmez; meşru sıçramada
oran bir gece yükseltilir.
"""
import re

import pandas as pd

from avukat_perf import kalite_alan
from avukat_perf.kalite_tur import TARIH_TUR, TR_SAYI, bos_metin, cevir
from avukat_perf.ortak import tek_gun
from avukat_perf.sema import KAYNAKLAR

SONUC = ["kaynak", "kontrol", "durum", "deger", "esik", "aciklama"]


def satir(kaynak, kontrol, deger, esik=0, aciklama="", uyari=False):
    """Bir denetim satırı: değer eşiği aşmıyorsa GECTI, aşıyorsa UYARI ya da KALDI."""
    durum = "GECTI" if deger <= esik else ("UYARI" if uyari else "KALDI")
    return (kaynak, kontrol, durum, deger, esik, aciklama)


def denetle(kaynak, tablo, kesit, params, onceki_satir=None):
    """(temiz tablo ya da None, sonuç tablosu). Zorunlu sütun eksikse temiz tablo None.

    İsteğe bağlı alan sütun olarak gelmezse boş sütun eklenir, EKSIK_ALAN uyarısı verilir."""
    tanim, sonuclar = KAYNAKLAR[kaynak], []
    eksik = [ad for ad, _, zorunlu in tanim["alanlar"] if zorunlu and ad not in tablo.columns]
    sonuclar.append(satir(kaynak, "ZORUNLU_SUTUN", len(eksik), aciklama=", ".join(eksik)))
    if eksik:
        return None, pd.DataFrame(sonuclar, columns=SONUC)
    istege = [ad for ad, _, _ in tanim["alanlar"] if ad not in tablo.columns]
    sonuclar.append(satir(kaynak, "EKSIK_ALAN", len(istege), aciklama=", ".join(istege),
                          uyari=True))
    temiz = tablo.assign(**{ad: None for ad in istege})[[ad for ad, _, _ in tanim["alanlar"]]]
    temiz = temiz.apply(bos_metin)
    sinir = tek_gun(kesit) + pd.Timedelta(days=params["kalite"]["gelecek_tarih_gun"])
    for ad, tur, zorunlu in tanim["alanlar"]:
        dolu = temiz[ad].notna()
        if tur == "sayi":
            yerel = temiz[ad].map(lambda d: isinstance(d, str) and bool(re.match(TR_SAYI,
                                                                                 d.strip())))
            sonuclar.append(satir(kaynak, "SAYI_BICIMI:" + ad, int(yerel.sum()),
                                   aciklama="Türkçe ya da belirsiz biçimli metin sayı (1.234 ya "
                                            "da 1,234: binlik mi ondalık mı); kaynağın biçimini "
                                            "teyit edip kaynak ayarında sayi_bicimi tr ya da en "
                                            "verin"))
        temiz[ad] = cevir(temiz[ad], tur)
        if tur == "sayi":
            sonsuz = temiz[ad].isin([float("inf"), float("-inf")])
            sonuclar.append(satir(kaynak, "SONSUZ:" + ad, int(sonsuz.sum()),
                                   aciklama="sonlu olmayan sayısal değer"))
        if tur != "metin":
            bozuk = int((dolu & temiz[ad].isna()).sum())
            sonuclar.append(satir(kaynak, "TUR:" + ad, bozuk, aciklama=TARIH_TUR if tur in (
                "tarih", "zaman") else "çevrilemeyen değer"))
        if zorunlu:
            sonuclar.append(satir(kaynak, "BOS:" + ad, int(temiz[ad].isna().sum())))
        if tur in ("tarih", "zaman"):
            ileri = int((temiz[ad].dt.normalize() > sinir).sum())
            sonuclar.append(satir(kaynak, "GELECEK_TARIH:" + ad, ileri, uyari=True))
    anahtar = tanim["anahtar"] or list(temiz.columns)
    yinelenen = int(temiz.duplicated(subset=anahtar, keep=False).sum())
    sonuclar.append(satir(kaynak, "YINELENEN", yinelenen,
                           uyari=not tanim["anahtar"] or tanim.get("yinelenen_uyari", False)))
    sonuclar += [satir(kaynak, kontrol, deger, aciklama=aciklama, uyari=uyari) for
                 kontrol, deger, uyari, aciklama in kalite_alan.denetimler(kaynak, temiz, params,
                                                                        kesit)]
    bos_uyari = tanim.get("istege_bagli") and not tanim.get("gozlem") and not onceki_satir
    sonuclar.append(satir(kaynak, "BOS_TABLO", int(temiz.empty), uyari=bool(bos_uyari)))
    if onceki_satir and onceki_satir >= params["kalite"]["sapma_en_az_satir"]:
        sapma = abs(len(temiz) - onceki_satir) / float(onceki_satir)
        sonuclar.append(satir(kaynak, "SATIR_SAPMASI", round(sapma, 4),
                               params["kalite"]["satir_sapma_orani"],
                               "önceki başarılı çekim: {} satır".format(onceki_satir)))
    return temiz, pd.DataFrame(sonuclar, columns=SONUC)


def cekim_hatasi(kaynak, ileti):
    """Kaynak okunamadı (bağlantı, yetki, biçim): KALDI satırı."""
    return pd.DataFrame([satir(kaynak, "CEKIM_HATASI", 1, aciklama=ileti)], columns=SONUC)


def karar(*sonuclar):
    """Sonuç tablolarından biri KALDI içeriyorsa KALDI, yoksa GECTI."""
    kaldi = any((tablo["durum"] == "KALDI").any() for tablo in sonuclar if tablo is not None)
    return "KALDI" if kaldi else "GECTI"
