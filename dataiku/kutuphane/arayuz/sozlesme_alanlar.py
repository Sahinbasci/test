"""Sözleşmede birden çok bileşenin kullandığı sütun listeleri."""
K1_LISTE = ["dosya_no", "avukat_kodu", "brans", "atama_tarihi", "bitis_tarihi", "bitis_nedeni",
            "atama_ref", "esas_ilk_giris", "kapsam_disi_nedeni", "seviye", "en_yuksek_seviye",
            "dusum", "dusum_durumu", "sure_gun", "dusum_tarihi", "olcum_sonu", "esik_sari",
            "esik_turuncu", "esik_kirmizi"]
K2_LISTE = ["dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi", "brans", "surec_turu",
            "dava_ilk_giris", "kosul_kayip_tarihi", "rucu_kodu", "acik_bakiye",
            "kapsam_disi_nedeni", "seviye", "en_yuksek_seviye", "dusum", "dusum_durumu", "sure_gun",
            "surec_baslangici", "dusum_tarihi", "olcum_sonu", "esik_sari", "esik_turuncu",
            "esik_kirmizi"]
BIRLESIK = ["tahsilat", "sure", "kalite", "davranis", "birlesik_puan", "performans_notu",
            "genel_sira", "durum", "eksik_sutunlar"]
SURE_OZET = ["kriter", "izleniyor", "acik_sari", "acik_turuncu", "acik_kirmizi", "kapanan",
             "dusum_sayisi", "ort_sure_gun"]
OLAY = ["dosya_no", "avukat_kodu", "atama_tarihi", "kriter", "seviye", "olay_tarihi",
        "calisma_kimligi"]
YILLIK = ["avukat_kodu", "yil", "tutar", "yil_ici", "son_tarih", "onceki_ayni_donem", "degisim"]
MEVCUT = ["alt_baslik", "puan", "degerlendirme_sayisi", "son_degerlendirme"]
SURE_PUANI = ["risk_donemi", "risk_dosya", "o", "e", "kapsam", "r", "puan", "eksik_nedeni",
              "durum", "yeterli"]
AY = ["ilk_ay", "son_ay", "son_ay_kismi"]  # aylık grafiğin hesap anındaki ay ızgarası
