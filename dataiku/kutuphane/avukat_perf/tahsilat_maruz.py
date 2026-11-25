"""Sayım bileşenlerinin kişi-zamanı: maruziyet (dosya-yıl) ve olay (tahsilat yapılan dosya-ay).

Maruziyet: avukatın dosyayı elinde tuttuğu günler ÷ 365, dosyanın aralık başından (dahil)
bitişine (hariç) kadar; her gün o günkü dosya yaşının bandına yazılır (yas_bantlari, rücuya
verilişten geçen ay). Olay: avukata yazılan net tahsilatı (ters kayıt düşülmüş) yarım kuruştan
büyük olan takvim ayı (avukat, dosya, ay); bandı o aydaki ilk pozitif tahsilatın günündeki yaştır.
Yalnız dosyanın aralığındaki hareketler sayılır; böylece her olay avukatın maruziyeti içindedir.
"""
import pandas as pd

from avukat_perf.ortak import BIR_GUN
from avukat_perf.tahsilat_evren import yas_bandi, yas_sinirlari
from avukat_perf.tahsilat_puan import YARIM_KURUS

YIL = 365.0
CIFT = ["avukat_kodu", "dosya_no"]


def maruziyet(donem, dosya, tah):
    """(avukat, dosya, yas_bandi) başına dosya-yıl.

    dosya: dosya_no, rucuya_verilis_tarihi, alt (aralık başı, dahil), ust (bitiş, hariç).
    """
    tablo = donem.merge(dosya[["dosya_no", "rucuya_verilis_tarihi", "alt", "ust"]], on="dosya_no")
    bas = tablo["atama_tarihi"].where(tablo["atama_tarihi"] >= tablo["alt"], tablo["alt"])
    son = tablo["bitis_tarihi"].where(tablo["bitis_tarihi"] < tablo["ust"], tablo["ust"])
    son = son.fillna(tablo["ust"])
    sinirlar = yas_sinirlari(tablo["rucuya_verilis_tarihi"], tah)
    parcalar = []
    for bant in range(len(sinirlar) + 1):
        alt = bas if bant == 0 else bas.where(bas >= sinirlar[bant - 1], sinirlar[bant - 1])
        ust = son if bant == len(sinirlar) else son.where(son <= sinirlar[bant], sinirlar[bant])
        gun = (ust - alt).dt.days.clip(lower=0)
        parcalar.append(tablo[CIFT].assign(yas_bandi=bant, maruz=gun / YIL))
    sonuc = pd.concat(parcalar, ignore_index=True)
    sonuc = sonuc[sonuc["maruz"] > 0]
    return sonuc.groupby(CIFT + ["yas_bandi"], as_index=False)["maruz"].sum()


def olaylar(hareket, dosya, tah):
    """(avukat, dosya, yas_bandi) başına olay sayısı. hareket: avukata yazılmış hareketler."""
    tablo = hareket[hareket["avukat_kodu"].notna()].merge(
        dosya[["dosya_no", "rucuya_verilis_tarihi", "alt", "ust"]], on="dosya_no")
    tarih = tablo["hareket_tarihi"]
    tablo = tablo[(tarih >= tablo["alt"]) & (tarih < tablo["ust"])]
    # Bant ayın ilk pozitif tahsilatından: 0 TL ya da ters kayıt olayı başka yaş bandına taşımaz.
    tablo = tablo.assign(ay=tablo["hareket_tarihi"].dt.strftime("%Y-%m"),
                         pozitif=tablo["hareket_tarihi"].where(tablo["tutar"] > YARIM_KURUS))
    ay = tablo.groupby(CIFT + ["ay"], as_index=False).agg(
        tutar=("tutar", "sum"), tarih=("pozitif", "min"),
        rucuya_verilis_tarihi=("rucuya_verilis_tarihi", "first"))
    ay = ay[ay["tutar"] > YARIM_KURUS]
    sinirlar = yas_sinirlari(ay["rucuya_verilis_tarihi"], tah)
    ay = ay.assign(yas_bandi=yas_bandi(ay["tarih"], sinirlar))
    return ay.groupby(CIFT + ["yas_bandi"]).size().rename("olay").reset_index()


def kapanis_ustu(dosya, hareket, kapanis, kesit):
    """Dosya başına aralık bitişi (hariç): açık dosyada kesitin ertesi günü; kapanış günü
    biliniyorsa onun ertesi günü (kapanış günü dahil: dosyayı kapatan tahsilat o gün gelir);
    bilinmiyorsa (arşiv öncesi kapanmış) son pozitif tahsilatın ertesi günü, hiç tahsilatı
    yoksa NaT (dosya sayılmaz).

    kapanis: dosya_no -> kesitte tahsile kapalı dosyanın kapanış günü (bilinmiyorsa NaT).
    """
    sinir = kesit + BIR_GUN
    kapanis = (kapanis if kapanis is not None else pd.Series(dtype="datetime64[ns]"))
    kapali = dosya["dosya_no"].isin(kapanis.index)
    gun = pd.to_datetime(dosya["dosya_no"].map(kapanis)) + BIR_GUN
    son = hareket[hareket["tutar"] > YARIM_KURUS].groupby("dosya_no")["hareket_tarihi"].max()
    tahmin = pd.to_datetime(dosya["dosya_no"].map(son)) + BIR_GUN
    ust = gun.where(gun.notna(), tahmin).where(kapali, sinir)
    return ust.where(ust.isna() | (ust <= sinir), sinir)
