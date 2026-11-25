"""Ekran–veri sözleşmesinin dağılım grafikleri bölümü (sozlesme.BILESENLER'e eklenir).

Kutular arka uçta sayılır (arayuz/sunum_dagilim.py, arayuz/dagilim_sure.py); ekran yalnız
çizer.
"""
PUAN_KAYNAGI = {"sonuc_puan_guncel": ["avukat_kodu", "sutun", "puan", "durum"],
                "sonuc_birlesik": ["avukat_kodu", "birlesik_puan", "performans_notu", "durum"]}
KUTU = ["sutun", "alt", "ust", "adet", "not_adi", "ortanca", "toplam"]
KUTU_KONUM = [ad for ad in KUTU if ad != "not_adi"]  # konum şeridi notu göstermez


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


DAGILIM_BILESENLERI = {
    "genel.dagilim": _b("genel", PUAN_KAYNAGI, KUTU + ["taban"]),
    "genel.tahsilat_dosya": _b("genel", {"sonuc_tahsilat_avukat": ["avukat_kodu", "n", "puan",
                                                                  "durum"]},
                               ["avukat_kodu", "olgun_dosya", "puan", "durum", "taban"]),
    "genel.brans_oran": _b("genel", {"sonuc_tahsilat_brans": ["avukat_kodu", "brans", "oran",
                                                               "yeterli"]},
                           ["tur", "brans", "adet", "ceyrek_alt", "ortanca", "ceyrek_ust",
                            "biyik_alt", "biyik_ust", "disarida", "avukat_kodu", "oran"]),
    "avukat.konum": _b("avukat", PUAN_KAYNAGI, KUTU_KONUM + ["avukat_puani", "yuzdelik"]),
    "sure.ilk_islem_dagilim": _b("sure", {"sonuc_k1": ["seviye", "sure_gun", "en_yuksek_seviye",
                                                    "esik_kurali", "esik_gun_sari",
                                                    "esik_gun_turuncu"]},
                                 ["tur", "kural", "alt", "ust", "bayrak", "adet", "toplam",
                                  "ortanca"]),
}
