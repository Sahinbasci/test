"""Ekran–veri sözleşmesinin ortak şerit, Puanlama Kuralları ve Veri Durumu bölümü
(sozlesme.BILESENLER'e eklenir).

ortak.durum: üst şerit (arayuz/sunum_ortak.py); gölge kriter bazında (golge_ilk_islem,
golge_dava_acma), okunamayan tablolar, parametre hataları ve son gecede bağlantısı beklenen
kaynaklar dahil.
ortak.adlar: ekran adları (tur: sistem, brans, alt_baslik, mevcut_alan; branşta renk sırası).
kurallar.hatalar: gecenin reddedeceği parametre dosyasının hata iletileri.
"""
from arayuz.sozlesme_alanlar import OLAY


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


ORTAK_BILESENLER = {
    "ortak.durum": _b("ortak", {
        "calisma_kaydi": ["calisma_kimligi", "tur", "kaynak", "baslangic", "cekim_tarihi",
                          "bitis", "durum", "hesap_surumu", "golge", "golge_zorunlu"],
        "sonuc_sure_ozet": ["acik_kirmizi"]},
                      ["kesit", "son_guncelleme", "son_karar", "son_donem_karari",
                       "hesap_surumu", "golge_mod", "golge_ilk_islem", "golge_dava_acma",
                       "kural_degisti", "acik_kirmizi", "okunamayan", "parametre_hatasi",
                       "bekleyen_kaynaklar"]),
    "ortak.adlar": _b("ortak", {}, ["tur", "kod", "ad", "sira"]),
    "kurallar.hatalar": _b("kurallar", {}, ["hata"]),
    "kurallar.agirliklar": _b("kurallar", {}, ["sutun", "agirlik", "teyit_bekliyor", "aciklama"]),
    "kurallar.notlar": _b("kurallar", {}, ["not_adi", "esik", "teyit_bekliyor", "aciklama"]),
    "kurallar.parametreler": _b("kurallar", {}, ["bolum", "ad", "deger", "teyit_bekliyor"]),
    "kurallar.aciklamalar": _b("kurallar", {}, ["bolum", "aciklama"]),
    "veri.kaynaklar": _b("veri", {"calisma_kaydi": [
        "calisma_kimligi", "kaynak", "yontem", "cekim_tarihi", "satir_sayisi", "kalite_sonucu",
        "durum", "arsiv_yolu"]}, ["kaynak", "sistem", "yontem", "cekim_tarihi", "satir_sayisi",
                                  "kalite_sonucu", "durum", "arsiv_yolu", "son_basarili"]),
    "veri.calismalar": _b("veri", {"calisma_kaydi": [
        "calisma_kimligi", "tur", "baslangic", "bitis", "cekim_tarihi", "durum", "aciklama"]},
        ["calisma_kimligi", "tur", "baslangic", "bitis", "cekim_tarihi", "durum", "aciklama"]),
    "veri.kalite": _b("veri", {"kalite_sonucu": [
        "kaynak", "kontrol", "durum", "deger", "esik", "aciklama", "calisma_kimligi",
        "cekim_tarihi"]}, ["kaynak", "kontrol", "durum", "deger", "esik", "aciklama",
                           "calisma_kimligi", "cekim_tarihi"]),
    "veri.celiski_ozet": _b("veri", {"olay_celiski": []}, ["toplam", "gosterilen"]),
    "veri.celiski": _b("veri", {"olay_celiski": OLAY[:6] + [
        "olay_tarihi_yeni", "calisma_kimligi", "tespit_tarihi"]},
        OLAY[:6] + ["olay_tarihi_yeni", "calisma_kimligi", "tespit_tarihi"]),
}
