"""Ekran–veri sözleşmesi: her bileşenin sayfası, beslendiği tablo sütunları ve aldığı alanlar.

kaynak: {tablo: [sütunlar]}; alanlar: bileşene gönderilen kayıt anahtarları (parametreden
beslenende kaynak boş). Ortak listeler sozlesme_alanlar.py, dışlananlar sozlesme_dislanan.py;
dağılım grafikleri sozlesme_dagilim.py, tahsilat bileşenleri sozlesme_tahsilat.py; ortak şerit,
Puanlama Kuralları ve Veri Durumu sozlesme_ortak.py. SECIMLIK_SUTUNLAR: okunan ama tabloda
bulunmayabilen (gruplamaya bağlı) sütunlar.
"""
from arayuz.sozlesme_dagilim import DAGILIM_BILESENLERI
from arayuz.sozlesme_ortak import ORTAK_BILESENLER
from arayuz.sozlesme_alanlar import (AY, BIRLESIK, K1_LISTE, K2_LISTE, MEVCUT, OLAY, SURE_OZET,
                                     SURE_PUANI, YILLIK)
from arayuz.sozlesme_tahsilat import SECIMLIK_SUTUNLAR, TAHSILAT_BILESENLERI  # noqa: F401


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


BILESENLER = {
    "genel.kpi": _b("genel", {
        "sonuc_portfoy": ["aktif_dosya", "aktif_rucu_tutari"],
        "sonuc_tahsilat_grup": ["atfedilen", "rucu_toplami", "atanamayan"],
        "sonuc_sure_ozet": ["acik_sari", "acik_turuncu", "acik_kirmizi"],
        "sonuc_birlesik": ["durum"]},
        ["aktif_dosya", "aktif_rucu_tutari", "tahsilat_orani", "atanamayan_tahsilat",
         "acik_sari", "acik_turuncu", "acik_kirmizi", "sure_verisi", "yayimlanan",
         "avukat_sayisi"]),
    "genel.sutun_durumu": _b("genel", {"sonuc_puan_guncel": ["sutun", "puan", "durum"]},
                             ["sutun", "gecerli", "ortalama", "gecersiz", "bekleme_nedeni"]),
    "genel.avukat_tablosu": _b("genel", {
        "sonuc_birlesik": ["avukat_kodu"] + BIRLESIK,
        "sonuc_tahsilat_avukat": ["oran", "yeterli"], "sonuc_portfoy": ["aktif_dosya"],
        "sonuc_sure": ["avukat_kodu", "yeterli"], "model_avukat": ["unvan"]},
        ["avukat_kodu", "unvan", "aktif_dosya", "gerceklesen_beklenen", "tahsilat_yeterli",
         "sure_yeterli"] + BIRLESIK),
    "genel.brans": _b("genel", {"sonuc_portfoy": ["brans", "aktif_dosya", "aktif_rucu_tutari"]},
                      ["brans", "aktif_dosya", "aktif_rucu_tutari"]),
    "genel.bant": _b("genel", {"sonuc_portfoy": ["tutar_bandi", "bant_etiketi", "aktif_dosya"]},
                     ["tutar_bandi", "bant_etiketi", "aktif_dosya"]),
    "genel.aylik": _b("genel", {"sonuc_tahsilat_aylik": ["avukat_kodu", "ay", "tutar"] + AY},
                      ["ay", "yazilan", "yazilamayan", "kismi"]),
    "genel.yillik": _b("genel", {"sonuc_tahsilat_yillik": YILLIK}, YILLIK),
    "genel.oncelikli": _b("genel", {"sonuc_eposta": ["avukat_kodu", "kriter", "dosya_no",
                                                     "seviye", "sure_gun"]},
                          ["kriter", "dosya_no", "avukat_kodu", "seviye", "sure_gun"]),
    "avukat.liste": _b("avukat", {"sonuc_birlesik": ["avukat_kodu", "birlesik_puan",
                                                     "performans_notu", "durum"],
                                  "model_avukat": ["avukat_kodu", "unvan"]},
                       ["avukat_kodu", "unvan", "birlesik_puan", "performans_notu", "durum"]),
    "avukat.baslik": _b("avukat", {
        "model_avukat": ["avukat_kodu", "unvan", "calisma_durumu"],
        "sonuc_birlesik": ["birlesik_puan", "performans_notu", "genel_sira", "durum",
                           "eksik_sutunlar"]},
        ["avukat_kodu", "unvan", "calisma_durumu", "birlesik_puan", "performans_notu",
         "genel_sira", "durum", "eksik_sutunlar", "yayimlanan"]),
    "avukat.sutunlar": _b("avukat", {"sonuc_puan_guncel": ["avukat_kodu", "sutun", "puan",
                                                           "durum", "agirlik"],
                                     "sonuc_tahsilat_avukat": ["avukat_kodu", "yeterli"],
                                     "sonuc_sure": ["avukat_kodu", "yeterli"]},
                          ["sutun", "puan", "durum", "agirlik", "yeterli"]),
    "avukat.aciklama": _b("avukat", {
        "sonuc_aciklama": ["avukat_kodu", "sutun", "sira", "tur", "metin", "etki"],
        "sonuc_puan_guncel": ["avukat_kodu", "sutun", "puan", "agirlik"],
        "sonuc_birlesik": ["avukat_kodu", "birlesik_puan", "performans_notu"]},
        ["sutun", "sira", "tur", "metin", "etki", "puan", "agirlik", "performans_notu"]),
    "avukat.kalite_davranis": _b("avukat", {"sonuc_kalite_davranis_sutun": [
        "avukat_kodu", "sutun", "puanlanan", "toplam", "gereken", "puan", "durum"]},
                       ["sutun", "puanlanan", "toplam", "gereken", "puan", "durum"]),
    "avukat.alt_basliklar": _b("avukat", {"sonuc_kalite_davranis_alt": [
        "avukat_kodu", "sutun", "alt_baslik", "puan", "degerlendirme_sayisi"]},
        ["sutun", "alt_baslik", "puan", "degerlendirme_sayisi"]),
    "avukat.mevcut_degerlendirme": _b("avukat", {"sonuc_mevcut_degerlendirme": [
        "avukat_kodu"] + MEVCUT}, MEVCUT),
    "avukat.portfoy": _b("avukat", {"sonuc_portfoy": ["avukat_kodu", "brans", "aktif_dosya",
                                                      "toplam_dosya", "aktif_rucu_tutari"]},
                         ["brans", "aktif_dosya", "toplam_dosya", "aktif_rucu_tutari"]),
    "avukat.sure": _b("avukat", {"sonuc_sure": ["avukat_kodu"] + SURE_PUANI}, SURE_PUANI),
    "avukat.sure_ozet": _b("avukat", {"sonuc_sure_ozet": ["avukat_kodu"] + SURE_OZET},
                           SURE_OZET),
    "avukat.aylik": _b("avukat", {"sonuc_tahsilat_aylik": ["avukat_kodu", "ay", "tutar",
                                                           "hareket_sayisi"] + AY},
                       ["ay", "tutar", "hareket_sayisi", "kismi"]),
    "avukat.gecmis": _b("avukat", {"birlesik_donem": [
        "avukat_kodu", "donem"] + BIRLESIK + ["yayin_surumu", "yayin_zamani", "hesap_surumu"]},
        ["donem"] + BIRLESIK + ["yayin_surumu", "yayin_zamani", "hesap_surumu"]),
    "sure.seviyeler": _b("sure", {"sonuc_k1": ["seviye"], "sonuc_k2": ["seviye"]},
                         ["kriter", "seviye", "adet"]),
    "sure.filtre": _b("sure", {"sonuc_k1": ["avukat_kodu", "pencerede_dusum"],
                               "sonuc_k2": ["avukat_kodu", "pencerede_dusum"]},
                      ["toplam", "gosterilen", "avukatlar"]),
    "sure.liste": _b("sure", {"sonuc_k1": K1_LISTE, "sonuc_k2": K2_LISTE},
                     ["kriter"] + K1_LISTE + [ad for ad in K2_LISTE if ad not in K1_LISTE]),
    "sure.olaylar": _b("sure", {"bayrak_olay": OLAY}, OLAY + ["son_sira"]),
    "sure.eposta": _b("sure", {"sonuc_eposta": ["avukat_kodu", "seviye", "dosya_no",
                                                "gonderilecek"]},
                      ["avukat_kodu", "sari", "turuncu", "kirmizi", "toplam", "gonderilecek"]),
}
BILESENLER.update(ORTAK_BILESENLER)
BILESENLER.update(DAGILIM_BILESENLERI)
BILESENLER.update(TAHSILAT_BILESENLERI)
