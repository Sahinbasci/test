"""Çalışma kaydından türetilen geçmiş bilgisi (yalnız okur, hesap yapmaz).

Son başarılı çekim ve gece, o gecenin yazdığı tablolar ve satır sayıları, kimlik, gölge
durumu ve gölge gecelerinin kapsadığı günler (tablo korunması hat/butunluk.py). Özet satırının
uretilen alanı "tablo=satır" çiftleridir; eski kayıtlarda yalnız tablo adı olabilir (sayı
bilinmez). Kayıt SQL'de durabilir; satır sırası garanti olmadığı için zamana göre sıralanır.
"""
import pandas as pd

from avukat_perf.mantik import dogru_mu as _dogru  # "true", True, E, 1: tek çözücü
from hat.calisma import OZET


def son_basarili(kayit, kaynak, once):
    """'once' anından önce başlamış son başarılı çekimin (günü, satır sayısı); yoksa (None, None).

    once bu çalışmanın başlangıç anıdır: aynı gün yeniden çalıştırmada taban aynı günün önceki
    (ör. 02:00) çekimidir, gün içinde girilen değerin ilk görülme günü bugün olur. Gözlem
    kaynağının boş görüntüsü kapıda durduğu için başarılı çekim hiçbir zaman boş değildir.
    """
    if kayit is None or kayit.empty:
        return None, None
    secili = kayit[(kayit["kaynak"] == kaynak) & (kayit["durum"] == "BASARILI")]
    secili = secili.assign(_gun=pd.to_datetime(secili["cekim_tarihi"]),
                           _bas=pd.to_datetime(secili["baslangic"]))
    secili = secili[secili["_bas"] < pd.Timestamp(once)].sort_values(["_bas", "_gun"])
    if secili.empty:
        return None, None
    en_son = secili.iloc[-1]
    return pd.Timestamp(en_son["cekim_tarihi"]), int(float(en_son["satir_sayisi"]))


def basarili_calismalar(kayit, tur="GECELIK"):
    """Başarılı gecelik (ya da DONEM_SONU) çalışmaların özet satırları, başlangıç sırasıyla."""
    if kayit is None or kayit.empty or "uretilen" not in kayit.columns:
        return None
    secili = kayit[(kayit["kaynak"] == OZET) & (kayit["tur"] == tur) &
                   kayit["uretilen"].notna() & (kayit["durum"] == "GECTI")]
    return secili.assign(_bas=pd.to_datetime(secili["baslangic"])).sort_values("_bas")


def son_basarili_gece(kayit):
    """Son başarılı gecenin özet satırı; yoksa None."""
    gece = basarili_calismalar(kayit)
    return None if gece is None or gece.empty else gece.iloc[-1]


def sayilar(satir):
    """Özet satırının uretilen alanı: {tablo: satır sayısı ya da None (eski kayıt)}."""
    if satir is None or pd.isna(satir.get("uretilen")):
        return {}
    sonuc = {}
    for parca in str(satir["uretilen"]).split(","):
        ad, _, sayi = parca.partition("=")
        sonuc[ad] = int(sayi) if sayi else None
    return sonuc


def son_sayilar(kayit, tur="GECELIK"):
    """Son başarılı çalışmanın yazdığı tablolar ve satır sayıları."""
    secili = basarili_calismalar(kayit, tur)
    return {} if secili is None or secili.empty else sayilar(secili.iloc[-1])


def son_uretilen(kayit):
    """Son başarılı gecelik çalışmanın yazdığı tablo adları; hiç başarılı gece yoksa None."""
    son = son_basarili_gece(kayit)
    return None if son is None else set(sayilar(son))


def son_kimlik(kayit):
    """Son başarılı gecelik çalışmanın kimliği; yoksa None."""
    son = son_basarili_gece(kayit)
    return None if son is None else str(son["calisma_kimligi"])


def son_golge_zorunlu(kayit):
    """Son başarılı gece Kriter 1'i yedek yoldan (zorunlu gölge mod) mu hesapladı."""
    son = son_basarili_gece(kayit)
    return son is not None and _dogru(son.get("golge_zorunlu"))


def son_golge(kayit):
    """Son başarılı gece gölge modda mı hesaplandı (parametre ya da yedek yol)."""
    son = son_basarili_gece(kayit)
    return son is not None and (_dogru(son.get("golge")) or _dogru(son.get("golge_zorunlu")))


def golge_araliklari(kayit, kriter="K1"):
    """Kriterin gölge gecelerinin kapsadığı günler: [(alt, ust)], alt < gün <= ust (alt None:
    sınırsız). Her başarılı gece önceki gecenin çekim gününden sonraki günleri kendi çekim
    gününe kadar kapsar (ilk gece öncesini de). Gölge gecesinin günündeki düşüm bildirilmediği
    için puana girmez; aralıklar geçmişe dönük değişmez. Parametreyle açılan gölge (golge) iki
    kriteri, yedek yolun zorunlu gölgesi (golge_zorunlu) yalnız Kriter 1'i kapsar.
    """
    gece = basarili_calismalar(kayit)
    if gece is None or gece.empty:
        return []
    bos = pd.Series(None, index=gece.index, dtype=object)
    golge = gece.get("golge", bos).map(_dogru)
    if kriter == "K1":
        golge = golge | gece.get("golge_zorunlu", bos).map(_dogru)
    araliklar, onceki = [], None
    for cekim, golgede in zip(gece["cekim_tarihi"], golge):
        gun = pd.Timestamp(cekim).normalize()
        if golgede and araliklar and araliklar[-1][1] == onceki:
            araliklar[-1] = (araliklar[-1][0], gun)  # art arda gölge geceleri tek aralık
        elif golgede:
            araliklar.append((onceki, gun))
        onceki = gun if onceki is None else max(onceki, gun)
    return araliklar


def golgede_mi(kayit, gun, kriter="K1"):
    """Gün kriterin bir gölge gecesinin kapsadığı aralıkta mı (dönem kendi kesitinin durumuyla)."""
    gun, araliklar = pd.Timestamp(gun).normalize(), golge_araliklari(kayit, kriter)
    return any((alt is None or gun > alt) and gun <= ust for alt, ust in araliklar)
