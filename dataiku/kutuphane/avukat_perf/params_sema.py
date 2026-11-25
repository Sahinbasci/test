"""Parametre sözlüğünün şeması: bölümler, alanlar ve alan türleri.

Tür adları: sayi, tam, mantiksal, metin, liste, sozluk; liste_veya_bos ve metin_veya_bos
teyit bekleyen değer için null da kabul eder. Tür bir demetse alan yalnız o değerlerden birini
alır (seçenek). notlar bölüm değil listedir; params.py
ayrıca denetler.
"""
SUTUNLAR = ("tahsilat", "sure", "kalite", "davranis")
GORUNUM = "gorunum"  # yalnız ekranda görünen adlar; hesap sürümüne girmez
KALITE_DAVRANIS_SUTUNLARI = ("kalite", "davranis")
TAHSILAT_GRUPLARI = ("brans", "yas_bandi", "tutar_bandi")
TAHSILAT_BILESENLERI = ("tutar", "siklik", "guncellik")
COKLU_KURALLARI = ("ortalama", "son")
IPTAL_YORUMLARI = ("sonraki_atamaya_gore", "hatali_iptal")
ELDE_TUTMA_PAYDALARI = ("ilk_atamadan", "avukat_gunleri")
YENIDEN_ATAMA_KURALLARI = ("yeni_donem", "surer")
ALANLAR = {
    "kriter1": {"uyari_gun": "tam", "dusum_gun_oto": "tam", "dusum_ay_diger": "tam",
                "oto_branslar": "liste", "sonlanan_atamada_dusum_korunur": "mantiksal"},
    "kriter2": {"uyari_ay": "tam", "dusum_ay": "tam", "rucu_kodu": "metin",
                "kapanis_kodlari": "liste", "sonlanan_atamada_dusum_korunur": "mantiksal"},
    "tahsilat": {"gruplama": "liste", "tutar_bantlari": "liste", "yas_bantlari": "liste",
                 "olgunluk_ay": "sozluk", "en_az_olgun_dosya": "tam",
                 "yeterli_olgun_dosya": "tam", "guven_sabiti": "sayi",
                 "olay_guven_sabiti": "sayi", "taban": "sayi", "egim": "sayi",
                 "bilesen_agirliklari": "sozluk", "elde_tutma_paydasi": ELDE_TUTMA_PAYDALARI,
                 "enflasyon_duzeltme": "mantiksal", "guncellik_pencere_ay": "tam",
                 "aylik_pencere_ay": "tam", "yillik_yil_sayisi": "tam"},
    "kalite_davranis": {"yeterlilik": "liste", "alt_basliklar": "sozluk", "olcek": "sozluk",
              "ters_yonlu": "liste_veya_bos", "coklu_degerlendirme": COKLU_KURALLARI,
              "pencere_ay": "tam", "mevcut_alanlar": "liste"},
    "sure_puani": {"guven_sabiti": "sayi", "taban": "sayi", "egim": "sayi",
                   "yeterli_dosya": "tam", "en_az_beklenen": "sayi", "en_az_kapsam": "sayi",
                   "pencere_ay": "tam"},
    "uyari": {"golge_mod": "mantiksal"},
    "hazirlik": {"iptal_yorumu": IPTAL_YORUMLARI,
                 "ayni_avukata_yeniden_atama": YENIDEN_ATAMA_KURALLARI,
                 "sulh_avukat_kodlari": "liste",
                 "sulh_alani": "metin_veya_bos", "sulh_degerleri": "liste",
                 "tahsilat_hareket_turleri": "liste_veya_bos"},
    "kalite": {"satir_sapma_orani": "sayi", "sapma_en_az_satir": "tam",
               "mutabakat_tolerans": "sayi", "gelecek_tarih_gun": "tam",
               "en_eski_tarih": "metin", "bilinen_branslar": "liste",
               "iliski_en_cok_yetim_orani": "sayi"},
    GORUNUM: {"sistem_adlari": "sozluk", "brans_adlari": "liste", "alt_baslik_adlari": "sozluk",
              "mevcut_alan_adlari": "sozluk"},
}
TUR_ADI = {"sayi": "sayı", "tam": "tam sayı", "mantiksal": "true ya da false",
           "metin": "metin", "liste": "liste", "sozluk": "sözlük",
           "liste_veya_bos": "liste ya da null", "metin_veya_bos": "metin ya da null"}
