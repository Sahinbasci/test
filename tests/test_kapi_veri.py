"""Kalite kapısı ve veri girişi: kaynaktan gelen biçim, değer ve doluluk hatası geceyi durdurur
ya da görünür olur; sessizce puanı değiştirmez."""
import pandas as pd

from avukat_perf import gozlem, kalite, kalite_iliski, sema
from hat import kaynak, model
from yardimci import params_yukle

KESIT = "2026-11-19"


def _satir(sonuc, kontrol):
    return sonuc.set_index("kontrol").loc[kontrol]


def _tablo(kaynak_adi, satirlar):
    return pd.DataFrame(satirlar, columns=sema.alanlar(kaynak_adi))


def _hata(fonk, *argumanlar):
    """Beklenen ValueError'ın iletisi; hata yoksa None."""
    try:
        fonk(*argumanlar)
    except ValueError as hata:
        return str(hata)
    return None


def _olcekli():
    params = params_yukle()
    params["kalite_davranis"]["olcek"] = {"en_dusuk": 1, "en_yuksek": 5}
    params["kalite_davranis"]["ters_yonlu"] = []
    return params


def test_tarih_bicimine_uymayan_deger_ay_gun_ters_okunmaz_kapi_durur():
    ham = pd.DataFrame({"dosya_no": ["D-1", "D-2", "D-3"], "avukat_kodu": ["AV-1"] * 3,
                        "atama_tarihi": ["05/01/2023 10:00:00", "05/01/2023",
                                         "12.04.2023 09:00:00"]})
    normal = kaynak.normalle("atama_log", ham, {"tarih_bicimi": "%d/%m/%Y %H:%M:%S"})
    temiz, sonuc = kalite.denetle("atama_log", normal, KESIT, params_yukle())
    assert _satir(sonuc, "TUR:atama_tarihi")["deger"] == 2 and kalite.karar(sonuc) == "KALDI"
    assert temiz["atama_tarihi"].iloc[0] == pd.Timestamp("2023-01-05 10:00")  # biçime uyan


def test_gozlem_kaynaginda_deger_alani_bos_gece_durur():
    params = params_yukle()
    esas = _tablo("esas_goruntu", [("D-1", None, None), ("D-2", "  ", None)])
    _, sonuc = kalite.denetle("esas_goruntu", esas, KESIT, params)
    assert _satir(sonuc, "DOLULUK:esas_no")["durum"] == "KALDI"
    eksik = pd.DataFrame({"dosya_no": ["D-1"], "kaynak_tarihi": ["2026-11-01"]})  # sütun yok
    assert kalite.karar(kalite.denetle("esas_goruntu", eksik, KESIT, params)[1]) == "KALDI"
    dolu = _tablo("esas_goruntu", [("D-1", None, None), ("D-2", "2026/1", None)])
    assert _satir(kalite.denetle("esas_goruntu", dolu, KESIT, params)[1],
                  "DOLULUK:esas_no")["durum"] == "GECTI"
    surec = _tablo("k2_goruntu", [("D-1", "ITIRAZ", "2026-01-01", None, None)])
    _, sonuc = kalite.denetle("k2_goruntu", surec, KESIT, params)
    assert _satir(sonuc, "DOLULUK:dava_esas_no")["durum"] == "KALDI"
    assert _satir(sonuc, "DOLULUK:surec_turu")["durum"] == "GECTI"
    takip = _tablo("takip", [("D-1", "ICRA", None, None, None)])
    assert _satir(kalite.denetle("takip", takip, KESIT, params)[1],
                  "DOLULUK:esas_no")["durum"] == "KALDI"


def test_bilinmeyen_brans_durur_deger_eslemesiyle_cevrilir():
    ham = pd.DataFrame({"dosya_no": ["D-1", "D-2"], "brans": ["Trafik", " Kasko"],
                        "rucu_kodu": ["R11", "R11"], "rucu_tutari": ["10", "20"],
                        "rucuya_verilis_tarihi": ["2025-01-01", "2025-01-01"]})
    params = params_yukle()
    assert _satir(kalite.denetle("dosya", kaynak.normalle("dosya", ham, {}), KESIT, params)[1],
                  "DEGER:brans")["durum"] == "KALDI"
    ayar = {"deger_eslemesi": {"brans": {"Trafik": "TRAFIK", "Kasko": "KASKO"}}}
    temiz, sonuc = kalite.denetle("dosya", kaynak.normalle("dosya", ham, ayar), KESIT, params)
    assert list(temiz["brans"]) == ["TRAFIK", "KASKO"] and kalite.karar(sonuc) == "GECTI"


def test_olcek_denetimi_yalniz_tanimli_alt_basliklarda():
    params = _olcekli()
    satirlar = [("AV-1", "2026-10-01", "eksik_hatali_islem", 4, "IA-1"),
                ("AV-1", "2026-10-01", "brans_yetkinligi", 80, "IA-1"),  # mevcut alan
                ("AV-1", "2019-01-01", "dosyaya_hakimiyet", 3, "IA-1")]
    _, sonuc = kalite.denetle("degerlendirme", _tablo("degerlendirme", satirlar), KESIT, params)
    assert _satir(sonuc, "OLCEK:puan")["deger"] == 0 and kalite.karar(sonuc) == "GECTI"
    satirlar.append(("AV-1", "2019-01-01", "dosyaya_hakimiyet", 7, "IA-2"))  # eski ama tanımlı
    _, sonuc = kalite.denetle("degerlendirme", _tablo("degerlendirme", satirlar), KESIT, params)
    assert _satir(sonuc, "OLCEK:puan")["durum"] == "KALDI"


def test_ingilizce_sayi_bicimi_uygulanir_belirsiz_ileti_yonlendirmez():
    ham = _tablo("dosya", [("D-1", "TRAFIK", "R11", "83,763.14", None, "2025-01-01"),
                           ("D-2", "TRAFIK", "R11", "83,763", None, "2025-01-01"),
                           ("D-3", "TRAFIK", "R11", "12.500", None, "2025-01-01")])
    temiz, sonuc = kalite.denetle("dosya", kaynak.normalle("dosya", ham, {"sayi_bicimi": "en"}),
                                  KESIT, params_yukle())
    assert list(temiz["rucu_tutari"]) == [83763.14, 83763.0, 12.5]
    assert kalite.karar(sonuc) == "GECTI"
    _, sonuc = kalite.denetle("dosya", ham, KESIT, params_yukle())
    aciklama = _satir(sonuc, "SAYI_BICIMI:rucu_tutari")["aciklama"]
    assert "belirsiz" in aciklama and "en" in aciklama.split("sayi_bicimi")[1]


def test_hareket_turu_suzgeci_disarida_kalani_gosterir():
    params = params_yukle()
    params["hazirlik"]["tahsilat_hareket_turleri"] = ["TAHSILAT"]
    hareket = _tablo("tahsilat_hareketi", [("D-1", "2026-10-01", 100, "TAHSILAT", None),
                                          ("D-1", "2026-10-02", -100, "TERS_KAYIT", None)])
    _, sonuc = kalite.denetle("tahsilat_hareketi", hareket, KESIT, params)
    assert tuple(_satir(sonuc, "DEGER:hareket_turu")[["durum", "deger"]]) == ("UYARI", 1)
    assert tuple(_satir(sonuc, "DISARIDA_TERS_KAYIT")[["durum", "deger"]]) == ("UYARI", 1)
    hepsi = hareket.assign(hareket_turu="Tahsilat")
    assert _satir(kalite.denetle("tahsilat_hareketi", hepsi, KESIT, params)[1],
                  "DEGER:hareket_turu")["durum"] == "KALDI"


def test_degerlendirme_cift_kaydi_tanimsiz_kod_ve_pencere_disi():
    params = params_yukle()
    cift = [("AV-1", "2026-03-06", "eksik_hatali_islem", 4, "IA-2")] * 2
    _, sonuc = kalite.denetle("degerlendirme", _tablo("degerlendirme", cift), KESIT, params)
    assert _satir(sonuc, "YINELENEN:degerlendiren")["durum"] == "KALDI"
    anonim = [("AV-1", "2026-03-06", "eksik_hatali_islem", 4, None)] * 2
    _, sonuc = kalite.denetle("degerlendirme", _tablo("degerlendirme", anonim), KESIT, params)
    assert kalite.karar(sonuc) == "GECTI"  # değerlendirici yokken aynı gün iki değerlendirme
    satirlar = [("AV-1", "2026-03-06", "Eksik_Hatali_Islem", 4, None),
                ("AV-1", "2026-03-06", "durustluk_duzeyi", 80, None),
                ("AV-1", "2022-03-28", "dosyaya_hakimiyet", 4, None)]
    _, sonuc = kalite.denetle("degerlendirme", _tablo("degerlendirme", satirlar), KESIT, params)
    assert tuple(_satir(sonuc, "DEGER:alt_baslik")[["durum", "deger"]]) == ("UYARI", 1)
    assert tuple(_satir(sonuc, "PENCERE_DISI")[["durum", "deger"]]) == ("UYARI", 1)
    ekran = [("AV-1", "2026-03-06", "Eksik veya hatalı işlemler", 4, None)]
    assert _satir(kalite.denetle("degerlendirme", _tablo("degerlendirme", ekran), KESIT,
                                 params)[1], "DEGER:alt_baslik")["durum"] == "KALDI"


def test_genis_degerlendirmede_eksik_esleme_sutunu_puanlanmamis():
    ayar = {"genis_degerlendirme": {"AlanA": "eksik_hatali_islem", "AlanB": "dosyaya_hakimiyet"}}
    ham = pd.DataFrame({"avukat_kodu": ["AV-1"], "degerlendirme_tarihi": ["2026-10-01"],
                        "AlanA": [4]})
    uzun = kaynak.normalle("degerlendirme", ham, ayar)
    assert sorted(uzun["alt_baslik"]) == ["dosyaya_hakimiyet", "eksik_hatali_islem"]
    assert uzun.set_index("alt_baslik")["puan"].isna().to_dict() == {
        "eksik_hatali_islem": False, "dosyaya_hakimiyet": True}
    bos = ham.drop(columns="AlanA")
    assert "hiçbiri yok" in (_hata(kaynak.normalle, "degerlendirme", bos, ayar) or "")


def test_alan_eslemesinden_sonra_cift_sutun_adini_soyler():
    ham = pd.DataFrame({"dosya_no": ["D-1"], "brans": ["TRAFIK"], "BRANS_KODU": ["ZZ"]})
    hata = _hata(kaynak.normalle, "dosya", ham, {"alan_eslemesi": {"BRANS_KODU": "brans"}})
    assert "yinelenen sütun: brans" in (hata or "")


def test_tarih_turunde_gelen_rapor_donemi_yerel_aya_duser():
    donem = pd.Series(pd.to_datetime(["2026-10-31 21:00"])).dt.tz_localize("UTC")
    rapor = pd.DataFrame({"avukat_kodu": ["AV-1"], "donem": donem, "tahsilat_toplami": [50.0]})
    temiz, sonuc = kalite.denetle("rapor_avukat_toplam", rapor, KESIT, params_yukle())
    assert kalite.karar(sonuc) == "GECTI" and temiz["donem"].iloc[0] == "2026-11-01"
    assert kalite_iliski._donem("2026-10-31T21:00:00Z") == "2026-11"
    hareket = _tablo("tahsilat_hareketi", [("D-1", "2026-11-05", 50.0, None, None)])
    hareket["hareket_tarihi"] = pd.to_datetime(hareket["hareket_tarihi"])
    mut = kalite_iliski.mutabakat(hareket, temiz, params_yukle())
    assert list(mut["kontrol"]) == ["TAHSILAT:2026-11"] and mut["durum"].iloc[0] == "GECTI"


def test_string_ve_category_turunde_kapi_ayni_davranir():
    params = params_yukle()
    dosya = _tablo("dosya", [("D-1", "TRAFIK", "R06", "10", "  ", "2025-01-01")])
    for tur in ("string", "category"):
        _, sonuc = kalite.denetle("dosya", dosya.astype(tur), KESIT, params)
        assert kalite.karar(sonuc) == "GECTI", tur
        assert _satir(sonuc, "TUR:acik_bakiye")["deger"] == 0, tur


def test_tarih_ve_sayi_iletisi_nedeni_ayirir():
    params = params_yukle()
    log = _tablo("atama_log", [("D-1", "AV-1", "2026-01-10", "9999-12-31", None, None, None)])
    _, sonuc = kalite.denetle("atama_log", log, KESIT, params)
    assert "sınır" in _satir(sonuc, "TUR:iptal_tarihi")["aciklama"]
    dosya = _tablo("dosya", [("D-1", "TRAFIK", "R06", "3.667", None, "2025-01-01")])
    _, sonuc = kalite.denetle("dosya", dosya, KESIT, params)
    assert "belirsiz" in _satir(sonuc, "SAYI_BICIMI:rucu_tutari")["aciklama"]


def test_takipte_dosya_basina_cok_satir_durdurmaz_en_erken_esas_gozleme_girer():
    params = params_yukle()
    takip = _tablo("takip", [("D-1", "DAVA", "2025/9", None, "2025-06-01"),
                             ("D-1", "ICRA", "2025/4", None, "2025-04-13"),
                             ("D-1", "ICRA", None, None, "2025-01-01")])
    temiz, sonuc = kalite.denetle("takip", takip, KESIT, params)
    assert _satir(sonuc, "YINELENEN")["durum"] == "UYARI" and kalite.karar(sonuc) == "GECTI"
    dosya = _tablo("dosya", [("D-1", "TRAFIK", "R06", 10.0, None, "2025-01-01")])
    tanimlar = {ad: (goruntu, deger, tarih) for ad, goruntu, _, deger, tarih in
                model._gozlem_tanimlari({"takip": temiz, "dosya": dosya}, params)}
    goruntu, deger, tarih = tanimlar["gozlem_esas_yedek"]
    sonuc = gozlem.guncelle(None, goruntu, "dosya_no", deger, KESIT, None, tarih)
    assert len(sonuc) == 1 and sonuc["ilk_tarih"].iloc[0] == pd.Timestamp("2025-04-13")
