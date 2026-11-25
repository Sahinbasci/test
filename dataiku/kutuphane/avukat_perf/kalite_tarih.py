"""Tarih anlamı denetimleri (kalite_alan'ın parçası): yer tutucu tarih, ters tarih ve saatsiz
aynı gün ataması.

- ESKI_TARIH: kalite.en_eski_tarih'ten eski tarih (ör. boş yerine 1900-01-01): KALDI.
- TERS_TARIH: atama logunda iptal günü atama gününden önce (aynı gün değil): dönem boş sayılıp
  çıkar, UYARI. Haklı beklemede bitiş başlangıçtan önce: KALDI (bekleme hesaplanamaz).
- SAATSIZ_ATAMA: atama logunda aynı dosyada aynı gün birden çok atama var ve o günün bütün
  atama zamanları 00:00: UYARI. Aynı gün yeniden atamada sıra saatle belirlenir; kaynak yalnız
  gün veriyorsa dosya avukat koduna göre sıralanıp yanlış avukata yazılabilir. Veri sözleşmesi
  atama ve iptal zamanını saatiyle ister.
"""
import pandas as pd


def _sayi(maske):
    return int(maske.sum())


def _saatsiz_ayni_gun(temiz):
    """Aynı dosyada aynı gün birden çok ataması olan ve o günün saatleri hepsi 00:00 satırlar."""
    secili = temiz[temiz["atama_tarihi"].notna()]
    gun = secili["atama_tarihi"].dt.normalize()
    grup = pd.DataFrame({"dosya": secili["dosya_no"], "gun": gun,
                         "saatsiz": secili["atama_tarihi"] == gun}).groupby(["dosya", "gun"])
    sayi = grup["saatsiz"].transform("size")
    return _sayi((sayi > 1) & grup["saatsiz"].transform("all").astype(bool))


def denetimler(kaynak, temiz, en_eski):
    """[(kontrol, değer, uyarı mı, açıklama), ...]."""
    sonuc = []
    for ad in temiz.columns:
        if pd.api.types.is_datetime64_any_dtype(temiz[ad]):
            sonuc.append(("ESKI_TARIH:" + ad, _sayi(temiz[ad] < en_eski), False,
                          "kalite.en_eski_tarih'ten eski tarih (yer tutucu olabilir)"))
    if kaynak == "atama_log":
        ters = temiz["iptal_tarihi"].dt.normalize() < temiz["atama_tarihi"].dt.normalize()
        sonuc.append(("TERS_TARIH", _sayi(ters), True,
                      "iptal günü atama gününden önce; dönem boş sayılıp çıkarılır"))
        sonuc.append(("SAATSIZ_ATAMA", _saatsiz_ayni_gun(temiz), True,
                      "aynı dosyada aynı gün birden çok atama saatsiz (00:00); sıra bilinmez, "
                      "kaynak atama zamanını saatiyle vermeli"))
    if kaynak == "bekleme":
        sonuc.append(("TERS_TARIH", _sayi(temiz["bitis"] < temiz["baslangic"]), False,
                      "bekleme bitişi başlangıcından önce"))
    return sonuc
