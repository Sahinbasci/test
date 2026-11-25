"""Ekran–veri sözleşmesinin tahsilat bölümü (sozlesme.BILESENLER'e eklenir).

Avukat kartı: tahsilat puanı ve üç bileşeni (tutar, sıklık, güncellik), branş tablosu (branş
satırları ve avukatın bütün dosyaları için toplam satırı). Genel Bakış: karşılaştırma grupları
ve avukat bazında aylık tahsilat tablosu (hesap anındaki ay ızgarasının son ayları).
"""
from arayuz.sozlesme_alanlar import AY

TAHSILAT = ["n", "gerceklesen", "beklenen", "oran", "r", "puan_tutar", "siklik_o", "siklik_e",
            "puan_siklik", "guncellik_o", "guncellik_e", "puan_guncellik", "puan", "eksik_nedeni",
            "durum", "yeterli"]
BRANS = ["n", "maruziyet", "gerceklesen", "tahsilat_orani", "beklenen_oran", "dosya_basina",
         "siklik_o", "siklik_e", "guncellik_o", "guncellik_e", "puan_tutar", "puan_siklik",
         "puan_guncellik", "puan", "eksik_nedeni", "yeterli"]
GRUP = ["dosya_sayisi", "rucu_toplami", "atfedilen", "atanamayan", "oran", "siklik_hizi"]
GRUP_ANAHTARI = ["brans", "yas_bandi", "yas_etiketi", "tutar_bandi", "bant_etiketi"]
# Gruplamada (tahsilat.gruplama) olmayan boyutun sütunu grup tablosunda üretilmez (hat/hesap):
# bu sütunlar olmadan da tablo gösterilir, eski biçim sayılmaz (temel.guncel_tablolar).
SECIMLIK_SUTUNLAR = {"sonuc_tahsilat_grup": GRUP_ANAHTARI}


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


TAHSILAT_BILESENLERI = {
    "avukat.tahsilat": _b("avukat", {"sonuc_tahsilat_avukat": ["avukat_kodu"] + TAHSILAT},
                          TAHSILAT),
    "avukat.brans": _b("avukat", {"sonuc_tahsilat_brans": ["avukat_kodu", "brans"] + BRANS,
                                  "sonuc_tahsilat_avukat": ["avukat_kodu"] + BRANS},
                       ["brans", "toplam"] + BRANS),
    "genel.gruplar": _b("genel", {"sonuc_tahsilat_grup": GRUP_ANAHTARI + GRUP},
                        GRUP_ANAHTARI + GRUP),
    "genel.aylik_avukat": _b("genel", {"sonuc_tahsilat_aylik": ["avukat_kodu", "ay", "tutar"] + AY},
                             ["avukat_kodu", "ay", "tutar", "kismi", "toplam"]),
}
