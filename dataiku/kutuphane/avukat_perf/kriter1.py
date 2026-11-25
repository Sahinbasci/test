"""Kriter 1: İlk İşlem Süresi. Atama dönemi başına seviye, düşüm ve süre.

Başlangıç atama tarihi, bitiş dosyanın esas numarasının ilk giriş tarihidir. Eşik günü
dahildir: süre >= eşik ise bayrak oluşur. Haklı bekleme eşik tarihini ileri kaydırır.
KIRMIZI: düşüm ayından sonraki ayın ilk günü dosya hâlâ açıksa; yeni düşüm doğurmaz.
Kesitten sonraki tarihler henüz bilinmiyor sayılır; aynı veri ve kesitle sonuç aynıdır.
esik_kurali (OTO: gün kuralı, OTO_DISI: takvim ayı kuralı), esik_gun_sari ve esik_gun_turuncu
eşiğin atamadan kaçıncı gün olduğudur (bekleme hariç; süreyle aynı ölçek): kural bilgisi hesap
anında sonuca yazılır, ekran eşiği buradan çizer. Branşı boş dönem (dosya tablosunda olmayan
dosya) ölçülmez: DOSYA_YOK; oto dışı eşikle ölçülmesi düşümü yanlış güne kaydırırdı.
"""
import pandas as pd

from avukat_perf import atama as atama_gecmisi
from avukat_perf import bayrak, bekleme
from avukat_perf.ortak import anahtar_kontrol, bos_kontrol, gun, sutun_kontrol, tek_gun

ATAMA_SUTUNLARI = atama_gecmisi.SUTUNLAR + ("brans",)
ANAHTAR = atama_gecmisi.ANAHTAR
TARIH_SONUCLARI = ("dusum_tarihi", "olcum_sonu", "esik_sari", "esik_turuncu", "esik_kirmizi")
SONUC_SUTUNLARI = ("kapsam_disi_nedeni", "seviye", "en_yuksek_seviye", "dusum",
                   "sure_gun", "esik_kurali", "esik_gun_sari", "esik_gun_turuncu") + TARIH_SONUCLARI


def esikler(atama, oto, aralik_listesi, k1):
    """Bekleme kaydırması uygulanmış SARI, TURUNCU ve KIRMIZI eşik tarihleri."""
    sari = atama + pd.Timedelta(days=k1["uyari_gun"])
    if oto:
        turuncu = atama + pd.Timedelta(days=k1["dusum_gun_oto"])
    else:
        turuncu = atama + pd.DateOffset(months=k1["dusum_ay_diger"])
    sari = bekleme.kaydir(sari, atama, aralik_listesi)
    turuncu = bekleme.kaydir(turuncu, atama, aralik_listesi)
    return bayrak.esikler(sari, turuncu)


def _donem_sonucu(kayit, kesit, k1, araliklar):
    """Tek atama dönemi için SONUC_SUTUNLARI değerleri."""
    sonuc = dict.fromkeys(SONUC_SUTUNLARI)
    atama = kayit["atama_tarihi"]
    bitis = kayit["bitis_tarihi"] if kayit["bitis_tarihi"] <= kesit else None
    esas = kayit["esas_ilk_giris"] if kayit["esas_ilk_giris"] <= kesit else None
    neden = kayit["kapsam_disi_nedeni"]
    if pd.isna(neden) and pd.isna(kayit["brans"]):  # dosya tablosunda yok: eşik kuralı bilinmez
        neden = "DOSYA_YOK"
    if pd.isna(neden) and esas is not None and esas < atama:
        neden = "ESAS_ONCEDEN_VAR"
    if pd.isna(neden) and esas is None and kayit["esas_tarihi_bilinmiyor"]:
        gorulme = kayit["esas_gorulme"]
        onceden = not pd.isna(gorulme) and gorulme < atama
        neden = "ESAS_ONCEDEN_VAR" if onceden else "ESAS_TARIHI_BILINMIYOR"
    if not pd.isna(neden):
        sonuc.update(kapsam_disi_nedeni=neden, seviye="KAPSAM_DISI", dusum=False)
        return sonuc
    if esas is not None and (bitis is None or esas <= bitis):
        son, kapanis = esas, "KAPANDI"
    elif bitis is not None:
        son, kapanis = bitis, "SONLANDI"
    else:
        son, kapanis = kesit, None
    aralik_listesi = araliklar.get((kayit["dosya_no"], kayit["avukat_kodu"]), [])
    oto = kayit["brans"] in k1["oto_branslar"]
    esik, olagan = esikler(atama, oto, aralik_listesi, k1), esikler(atama, oto, [], k1)
    seviye, en_yuksek, dusum = bayrak.degerlendir(esik, son, kapanis,
                                                  k1["sonlanan_atamada_dusum_korunur"])
    gecen = (son - atama).days - bekleme.gun_sayisi(atama, son, aralik_listesi)
    sonuc.update(seviye=seviye, en_yuksek_seviye=en_yuksek,
                 dusum=dusum, dusum_tarihi=esik["TURUNCU"] if dusum else None,
                 sure_gun=gecen, olcum_sonu=son, esik_sari=esik["SARI"],
                 esik_kurali="OTO" if oto else "OTO_DISI",
                 esik_gun_sari=(olagan["SARI"] - atama).days,
                 esik_gun_turuncu=(olagan["TURUNCU"] - atama).days,
                 esik_turuncu=esik["TURUNCU"], esik_kirmizi=esik["KIRMIZI"])
    return sonuc


def degerlendir(atamalar, esaslar, beklemeler, kesit, params):
    """Kesit tarihinde her atama dönemi için seviye, düşüm ve süre.

    atamalar: ATAMA_SUTUNLARI; bitis_nedeni IADE, YENIDEN_ATAMA, IPTAL ya da boş;
    atama_turu NORMAL ya da SULH. esaslar: dosya_no, esas_ilk_giris; dosya başına en
    erken tarih alınır. İsteğe bağlı tarih_bilinmiyor sütunu True ise esas arşivden önce
    girilmiş, tarihi bilinmiyordur: dönem ölçülmez (ESAS_TARIHI_BILINMIYOR). İsteğe bağlı
    ilk_gorulme o esasın ilk görüldüğü çekim günüdür; atama bu günden sonraysa esas atamadan
    önce vardı (ESAS_ONCEDEN_VAR).
    beklemeler: bekleme.SUTUNLAR ya da None. Kesitten sonra başlayan atama sonuca girmez.
    """
    sutun_kontrol(atamalar, ATAMA_SUTUNLARI, "atamalar")
    sutun_kontrol(esaslar, ("dosya_no", "esas_ilk_giris"), "esaslar")
    bos_kontrol(atamalar, ANAHTAR, "atamalar")
    kesit = tek_gun(kesit)
    tablo = atama_gecmisi.kapsam_belirle(atamalar)
    tablo["atama_tarihi"] = gun(tablo["atama_tarihi"])
    tablo["bitis_tarihi"] = gun(tablo["bitis_tarihi"])
    anahtar_kontrol(tablo[tablo["kapsam_disi_nedeni"].isna()], ANAHTAR, "atamalar")
    tablo = tablo[tablo["atama_tarihi"] <= kesit].reset_index(drop=True)
    ilk_esas = gun(esaslar["esas_ilk_giris"]).groupby(esaslar["dosya_no"]).min()
    tablo["esas_ilk_giris"] = pd.to_datetime(tablo["dosya_no"].map(ilk_esas))
    isaret = pd.Series(False, index=esaslar.index)
    if "tarih_bilinmiyor" in esaslar.columns:
        isaret = esaslar["tarih_bilinmiyor"].astype(object).eq(True)
    gorulme = (gun(esaslar["ilk_gorulme"]) if "ilk_gorulme" in esaslar.columns
               else pd.Series(pd.NaT, index=esaslar.index, dtype="datetime64[ns]"))
    gorulme = gorulme[isaret].groupby(esaslar.loc[isaret, "dosya_no"]).min()
    tablo["esas_tarihi_bilinmiyor"] = tablo["dosya_no"].isin(set(gorulme.index))
    tablo["esas_gorulme"] = pd.to_datetime(tablo["dosya_no"].map(gorulme))
    araliklar = bekleme.araliklar(beklemeler, kesit)
    satirlar = [_donem_sonucu(kayit, kesit, params["kriter1"], araliklar)
                for kayit in tablo.to_dict("records")]
    sonuc = pd.DataFrame(satirlar, columns=list(SONUC_SUTUNLARI))
    for sutun in TARIH_SONUCLARI:
        sonuc[sutun] = pd.to_datetime(sonuc[sutun])
    sonuc["dusum"] = sonuc["dusum"].astype(bool)
    return pd.concat([tablo.drop(columns=["kapsam_disi_nedeni", "esas_gorulme"]), sonuc], axis=1)
