"""Süre takibi özeti ve gecikme e-posta listesi (arayüz ve uyarı için).

Girdi Kriter 1 ve Kriter 2 değerlendirmelerinin birleşimidir; kriter sütunu K1 ya da K2.
Özet, avukat ve kriter başına: izlenen ve açık bayraklı dönem sayıları, pencerede kapanan
dönemler ve ortalama süreleri, penceredeki düşüm sayısı. Pencere (kesit − ay, kesit];
düşüm sayısında gölge gecelerinin kapsadığı günler sayılmaz (haric). Düşüm durumu: UYGULANDI,
GOLGE (bu hesap gölge modda: uygulanmadı) ya da GOLGE_DONEMI (gölge gecesinin kapsadığı günde
oluştu, bildirilmedi, puana girmez).
E-posta listesi açık dönemlerden SARI, TURUNCU ve KIRMIZI olanlardır. Gönderim bu modülün
işi değildir; gölgedeki kriterin satırları listede kalır ama gonderilecek False olur.
"""
import pandas as pd

from avukat_perf.ortak import gun, sutun_kontrol
from avukat_perf.pencere import aralik_disinda, icinde

GIRDI = ("avukat_kodu", "kriter", "dosya_no", "atama_tarihi", "seviye", "dusum",
         "dusum_tarihi", "sure_gun", "olcum_sonu", "esik_sari", "esik_turuncu")
ACIK = {"KIRMIZI": 0, "TURUNCU": 1, "SARI": 2}


def golge_kriterleri(params):
    """Kriter başına gölge: golge_mod iki kriteri, golge_k1 (yedek yol; parametre dosyasında
    yok, hesap anında verilir) yalnız Kriter 1'i kapsar."""
    uyari = params["uyari"]
    return {"K1": bool(uyari["golge_mod"] or uyari.get("golge_k1")),
            "K2": bool(uyari["golge_mod"])}


def pencerede_dusum(degerlendirmeler, kesit, pencere_ay, haric=None):
    """Düşüm tarihi pencerede (ve gölge gününde değil) olan dönemler (bool)."""
    tarih = gun(degerlendirmeler["dusum_tarihi"])
    return degerlendirmeler["dusum"].astype(bool) & icinde(
        tarih, kesit, pencere_ay, haric, degerlendirmeler.get("kriter"))


def dusum_durumu(degerlendirmeler, golge, haric=None):
    """Düşümü olan dönemde düşümün puana girip girmediği; düşümsüz dönemde boş."""
    tarih = gun(degerlendirmeler["dusum_tarihi"])
    golgede = ~aralik_disinda(tarih, haric, degerlendirmeler.get("kriter")) & tarih.notna()
    durum = pd.Series("UYGULANDI", index=degerlendirmeler.index).where(~golgede, "GOLGE_DONEMI")
    if golge:
        durum = pd.Series("GOLGE", index=degerlendirmeler.index)
    return durum.where(degerlendirmeler["dusum"].astype(bool))


def ozet(degerlendirmeler, kesit, pencere_ay, haric=None):
    """Avukat ve kriter başına süre özeti."""
    sutun_kontrol(degerlendirmeler, GIRDI, "degerlendirmeler")
    tablo = degerlendirmeler
    seviye = tablo["seviye"]
    kapanan = (seviye == "KAPANDI") & icinde(gun(tablo["olcum_sonu"]), kesit, pencere_ay)
    yardimci = pd.DataFrame({
        "avukat_kodu": tablo["avukat_kodu"], "kriter": tablo["kriter"],
        "izleniyor": seviye == "IZLENIYOR", "acik_sari": seviye == "SARI",
        "acik_turuncu": seviye == "TURUNCU", "acik_kirmizi": seviye == "KIRMIZI",
        "kapanan": kapanan,
        "kapanan_sure": tablo["sure_gun"].astype(float).where(kapanan),
        "dusum_sayisi": pencerede_dusum(tablo, kesit, pencere_ay, haric)})
    anahtar = ["avukat_kodu", "kriter"]
    sayilar = yardimci.drop(columns="kapanan_sure").groupby(anahtar).sum().astype(int)
    ortalama = yardimci.groupby(anahtar)["kapanan_sure"].mean().rename("ort_sure_gun")
    return pd.concat([sayilar, ortalama], axis=1).reset_index()


def eposta_listesi(degerlendirmeler, params):
    """Avukat başına açık gecikmeler; en ağır seviye ve en uzun süre önce."""
    sutun_kontrol(degerlendirmeler, GIRDI, "degerlendirmeler")
    tablo = degerlendirmeler[degerlendirmeler["seviye"].isin(list(ACIK))]
    sutunlar = ["avukat_kodu", "kriter", "dosya_no", "atama_tarihi", "seviye", "sure_gun",
                "esik_sari", "esik_turuncu"]
    golge = golge_kriterleri(params)
    tablo = tablo[sutunlar].assign(sira=tablo["seviye"].map(ACIK),
                                   gonderilecek=~tablo["kriter"].map(golge).astype(bool))
    tablo = tablo.sort_values(["avukat_kodu", "sira", "sure_gun"],
                              ascending=[True, True, False])
    return tablo.drop(columns="sira").reset_index(drop=True)
