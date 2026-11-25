"""Kriter 1 testleri. Varsayılan kesit 2026-11-19; oto eşiği 20 gün, oto dışı 2 takvim ayı.

İlk sürümün on satırlık gerileme tablosu OTO / DIGER yazar; bunlar oto_branslar eşlemesinin
sonucudur. Burada OTO için TRAFIK, DIGER için YANGIN kullanılır.
"""
import pandas as pd

from avukat_perf import kriter1, olay
from yardimci import atama_tablosu, bekleme_tablosu, esas_tablosu, hata_bekle, params_yukle

KESIT = "2026-11-19"
BRANS = {"OTO": "TRAFIK", "DIGER": "YANGIN"}
# dosya_no, avukat_kodu, brans, atama_tarihi, esas_ilk_giris, seviye, dusum
GERILEME = [
    ("D-001", "AV-01", "OTO", "2026-11-10", None, "IZLENIYOR", False),
    ("D-002", "AV-01", "OTO", "2026-11-09", None, "SARI", False),
    ("D-003", "AV-02", "OTO", "2026-11-08", None, "SARI", False),
    ("D-004", "AV-02", "OTO", "2026-10-31", None, "SARI", False),
    ("D-005", "AV-03", "OTO", "2026-10-30", None, "TURUNCU", True),
    ("D-006", "AV-03", "OTO", "2026-10-29", None, "TURUNCU", True),
    ("D-007", "AV-01", "DIGER", "2026-10-05", None, "SARI", False),
    ("D-008", "AV-02", "DIGER", "2026-09-05", None, "TURUNCU", True),
    ("D-009", "AV-03", "OTO", "2026-10-20", "2026-10-25", "KAPANDI", False),
    ("D-010", "AV-01", "OTO", "2026-10-10", "2026-11-04", "KAPANDI", True),
]


def _g(metin):
    return pd.Timestamp(metin)


def _calistir(atamalar, esaslar=None, beklemeler=None, kesit=KESIT, params=None):
    return kriter1.degerlendir(atamalar, esas_tablosu(esaslar or {}), beklemeler, kesit,
                               params or params_yukle())


def _tek(satir, **secenek):
    """Tek atama dönemli çalıştırmanın sonucunu sözlük olarak döndürür."""
    esaslar = secenek.pop("esaslar", None)
    return _calistir(atama_tablosu([satir]), esaslar, **secenek).iloc[0].to_dict()


def _gerileme_girdisi():
    atamalar = atama_tablosu([(s[0], s[1], BRANS[s[2]], s[3]) for s in GERILEME])
    return atamalar, {s[0]: s[4] for s in GERILEME if s[4]}


def test_gerileme_tablosu():
    sonuc = _calistir(*_gerileme_girdisi())
    assert list(sonuc["dosya_no"]) == [s[0] for s in GERILEME]
    assert list(sonuc["seviye"]) == [s[5] for s in GERILEME]
    assert list(sonuc["dusum"]) == [s[6] for s in GERILEME]


def test_gerileme_sure_gun_ve_dusum_tarihi():
    sonuc = _calistir(*_gerileme_girdisi()).set_index("dosya_no")
    assert list(sonuc["sure_gun"]) == [9, 10, 11, 19, 20, 21, 45, 75, 5, 25]
    assert sonuc.loc["D-008", "dusum_tarihi"] == _g("2026-11-05")
    assert sonuc.loc["D-010", "dusum_tarihi"] == _g("2026-10-30")
    assert pd.isna(sonuc.loc["D-004", "dusum_tarihi"])


def test_kasko_oto_sayilir_diger_branslar_sayilmaz():
    assert _tek(("D-1", "AV-1", "KASKO", "2026-10-30"))["seviye"] == "TURUNCU"
    assert _tek(("D-1", "AV-1", "YANGIN", "2026-10-30"))["seviye"] == "SARI"


def test_oto_disi_ay_esigi_siniri():
    assert _tek(("D-1", "AV-1", "YANGIN", "2026-09-19"))["seviye"] == "TURUNCU"
    assert _tek(("D-1", "AV-1", "YANGIN", "2026-09-20"))["seviye"] == "SARI"


def test_ay_sonunda_ay_esigi_ayin_son_gunune_duser():
    satir = ("D-1", "AV-1", "YANGIN", "2026-12-31")
    sonuc = _tek(satir, kesit="2027-02-28")
    assert sonuc["esik_turuncu"] == _g("2027-02-28") and sonuc["seviye"] == "TURUNCU"
    assert _tek(satir, kesit="2027-02-27")["seviye"] == "SARI"


def test_kirmizi_dusumden_sonraki_ayin_ilk_gunu():
    satir = ("D-1", "AV-1", "TRAFIK", "2026-09-01")
    assert _tek(satir, kesit="2026-09-30")["seviye"] == "TURUNCU"
    sonuc = _tek(satir, kesit="2026-10-01")
    assert sonuc["seviye"] == "KIRMIZI" and sonuc["dusum"]
    assert sonuc["dusum_tarihi"] == _g("2026-09-21")


def test_kirmizi_yeni_dusum_dogurmaz():
    atamalar = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-09-01")])
    kayit = None
    for kesit in ("2026-09-25", "2026-10-15", "2026-11-19"):
        sonuc = _calistir(atamalar, kesit=kesit)
        assert sonuc["dusum_tarihi"].iloc[0] == _g("2026-09-21")
        kayit = olay.olay_birlestir(kayit, olay.olaylar(sonuc, "K1"))
    assert list(kayit["seviye"]) == ["SARI", "TURUNCU", "KIRMIZI"]


def test_gec_kapanan_dosyada_bayrak_ve_dusum_gecmisi_korunur():
    atamalar = atama_tablosu([("D-010", "AV-01", "TRAFIK", "2026-10-10")])
    esaslar = {"D-010": "2026-11-04"}
    once = _calistir(atamalar, esaslar, kesit="2026-11-02")
    sonra = _calistir(atamalar, esaslar)
    assert once["seviye"].iloc[0] == "KIRMIZI"
    assert sonra["seviye"].iloc[0] == "KAPANDI" and sonra["dusum"].iloc[0]
    assert sonra["en_yuksek_seviye"].iloc[0] == "KIRMIZI"
    kayit = olay.olay_birlestir(None, olay.olaylar(once, "K1"))
    yeni = olay.olaylar(sonra, "K1")
    assert len(olay.olay_birlestir(kayit, yeni)) == 3
    assert olay.celisen_olaylar(kayit, yeni, KESIT).empty
    tarihler = [_g(t) for t in ("2026-10-20", "2026-10-30", "2026-11-01")]
    assert list(yeni["olay_tarihi"]) == tarihler


def test_hakli_bekleme_gun_esigini_kaydirir():
    satir = ("D-1", "AV-1", "TRAFIK", "2026-11-01")
    bekleme = bekleme_tablosu([("D-1", "AV-1", "2026-11-05", "2026-11-09")])
    assert _tek(satir, kesit="2026-11-13")["seviye"] == "SARI"
    sonuc = _tek(satir, beklemeler=bekleme, kesit="2026-11-13")
    assert sonuc["seviye"] == "IZLENIYOR" and sonuc["sure_gun"] == 7
    assert sonuc["esik_sari"] == _g("2026-11-16")
    assert sonuc["esik_turuncu"] == _g("2026-11-26")
    # Eşik günü süreyle aynı ölçektedir: bekleme tarihi kaydırır, eşik günü değişmez.
    assert (sonuc["esik_gun_sari"], sonuc["esik_gun_turuncu"]) == (10, 20)
    assert sonuc["esik_kurali"] == "OTO"


def test_hakli_bekleme_ay_esigini_kaydirir():
    satir = ("D-1", "AV-1", "YANGIN", "2026-09-05")
    bekleme = bekleme_tablosu([("D-1", "AV-1", "2026-10-01", "2026-10-20")])
    assert _tek(satir)["seviye"] == "TURUNCU"
    sonuc = _tek(satir, beklemeler=bekleme)
    assert sonuc["esik_turuncu"] == _g("2026-11-25")
    assert sonuc["seviye"] == "SARI" and not sonuc["dusum"]
    # Takvim ayı kuralı: 5 Eylül + 2 ay = 5 Kasım, atamadan 61 gün sonra.
    assert (sonuc["esik_gun_sari"], sonuc["esik_gun_turuncu"]) == (10, 61)
    assert sonuc["esik_kurali"] == "OTO_DISI"
    kapsam_disi = _tek(("D-1", "AV-1", "YANGIN", "2026-09-05"), esaslar={"D-1": "2026-09-01"})
    assert pd.isna(kapsam_disi["esik_gun_sari"]) and pd.isna(kapsam_disi["esik_gun_turuncu"])
    assert pd.isna(kapsam_disi["esik_kurali"])


def test_cakisan_bekleme_bir_kez_sayilir():
    bekleme = bekleme_tablosu([("D-1", "AV-1", "2026-11-05", "2026-11-09"),
                               ("D-1", "AV-1", "2026-11-07", "2026-11-12")])
    sonuc = _tek(("D-1", "AV-1", "TRAFIK", "2026-11-01"), beklemeler=bekleme)
    assert sonuc["esik_sari"] == _g("2026-11-19")
    assert sonuc["seviye"] == "SARI" and sonuc["sure_gun"] == 10


def test_bekleme_yalniz_kendi_avukatina_uygulanir():
    bekleme = bekleme_tablosu([("D-1", "AV-9", "2026-11-05", "2026-11-09")])
    sonuc = _tek(("D-1", "AV-1", "TRAFIK", "2026-11-01"), beklemeler=bekleme)
    assert sonuc["esik_sari"] == _g("2026-11-11")


def test_bitisi_bos_bekleme_kesitte_kesilir():
    bekleme = bekleme_tablosu([("D-1", "AV-1", "2026-11-05", None)])
    sonuc = _tek(("D-1", "AV-1", "TRAFIK", "2026-11-01"), beklemeler=bekleme,
                 kesit="2026-11-13")
    assert sonuc["seviye"] == "IZLENIYOR" and sonuc["sure_gun"] == 4


def test_iadeden_once_olusan_dusum_korunur():
    sonuc = _tek(("D-1", "AV-1", "TRAFIK", "2026-10-01", "2026-10-25", "IADE"))
    assert sonuc["seviye"] == "SONLANDI" and sonuc["dusum"]
    assert sonuc["en_yuksek_seviye"] == "TURUNCU" and sonuc["sure_gun"] == 24


def test_dusum_korunmazsa_bayrak_gecmisi_yine_kalir():
    params = params_yukle()
    params["kriter1"]["sonlanan_atamada_dusum_korunur"] = False
    atamalar = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-10-01", "2026-10-25", "IADE")])
    sonuc = _calistir(atamalar, params=params)
    assert sonuc["seviye"].iloc[0] == "SONLANDI" and not sonuc["dusum"].iloc[0]
    assert pd.isna(sonuc["dusum_tarihi"].iloc[0])
    assert list(olay.olaylar(sonuc, "K1")["seviye"]) == ["SARI", "TURUNCU"]


def test_esikten_once_iade_bayraksiz_sonlanir():
    sonuc = _tek(("D-1", "AV-1", "TRAFIK", "2026-10-01", "2026-10-05", "IADE"))
    assert sonuc["seviye"] == "SONLANDI" and pd.isna(sonuc["en_yuksek_seviye"])
    assert not sonuc["dusum"]


def test_yeniden_atamada_sure_yeni_atamadan_baslar():
    atamalar = atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2026-09-01", "2026-09-25", "YENIDEN_ATAMA"),
        ("D-1", "AV-2", "TRAFIK", "2026-09-25")])
    sonuc = _calistir(atamalar, {"D-1": "2026-10-08"}).set_index("avukat_kodu")
    assert sonuc.loc["AV-1", "seviye"] == "SONLANDI" and sonuc.loc["AV-1", "dusum"]
    assert sonuc.loc["AV-2", "seviye"] == "KAPANDI" and not sonuc.loc["AV-2", "dusum"]
    assert sonuc.loc["AV-2", "en_yuksek_seviye"] == "SARI"
    assert sonuc.loc["AV-2", "sure_gun"] == 13


def test_esas_onceden_girilmisse_yeni_avukat_kapsam_disi():
    atamalar = atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2026-09-01", "2026-10-01", "YENIDEN_ATAMA"),
        ("D-1", "AV-2", "TRAFIK", "2026-10-01")])
    sonuc = _calistir(atamalar, {"D-1": "2026-09-05"}).set_index("avukat_kodu")
    assert sonuc.loc["AV-1", "seviye"] == "KAPANDI" and sonuc.loc["AV-1", "sure_gun"] == 4
    assert sonuc.loc["AV-2", "seviye"] == "KAPSAM_DISI"
    assert sonuc.loc["AV-2", "kapsam_disi_nedeni"] == "ESAS_ONCEDEN_VAR"
    assert not sonuc.loc["AV-2", "dusum"]


def test_sulh_ve_iptal_atamalari_kapsam_disi():
    atamalar = atama_tablosu([
        ("D-1", "AV-9", "TRAFIK", "2025-01-02 11:48:21", None, None, "SULH"),
        ("D-1", "AV-1", "TRAFIK", "2026-10-12 18:21:38"),
        ("D-2", "AV-2", "TRAFIK", "2026-09-01", "2026-09-02", "IPTAL")])
    sonuc = _calistir(atamalar, {"D-1": "2026-10-13"})
    tablo = sonuc.set_index("avukat_kodu")
    assert tablo.loc["AV-9", "kapsam_disi_nedeni"] == "SULH"
    assert tablo.loc["AV-2", "kapsam_disi_nedeni"] == "IPTAL"
    assert list(tablo.loc[["AV-9", "AV-2"], "seviye"]) == ["KAPSAM_DISI", "KAPSAM_DISI"]
    assert tablo.loc["AV-1", "seviye"] == "KAPANDI" and tablo.loc["AV-1", "sure_gun"] == 1
    assert olay.olaylar(sonuc, "K1").empty


def test_kesitten_sonraki_veri_henuz_bilinmiyor():
    atamalar = atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2026-10-01", "2026-11-25", "IADE"),
        ("D-2", "AV-1", "TRAFIK", "2026-10-01"),
        ("D-3", "AV-1", "TRAFIK", "2026-11-20")])
    sonuc = _calistir(atamalar, {"D-2": "2026-11-20"})
    assert list(sonuc["dosya_no"]) == ["D-1", "D-2"]
    assert list(sonuc["seviye"]) == ["KIRMIZI", "KIRMIZI"]


def test_ayni_kesitte_iki_kez_calistirma_cift_dusum_uretmez():
    birinci = _calistir(*_gerileme_girdisi())
    ikinci = _calistir(*_gerileme_girdisi())
    pd.testing.assert_frame_equal(birinci, ikinci)
    kayit = olay.olay_birlestir(None, olay.olaylar(birinci, "K1"))
    tekrar = olay.olay_birlestir(kayit, olay.olaylar(ikinci, "K1"))
    assert len(tekrar) == len(kayit)
    turuncu = tekrar[tekrar["seviye"] == "TURUNCU"]
    assert len(turuncu) == int(birinci["dusum"].sum()) == 4


def test_saatli_atama_tarihi_gune_cevrilir():
    sonuc = _tek(("D-1", "AV-1", "TRAFIK", "2026-10-30 18:21:38"))
    assert sonuc["atama_tarihi"] == _g("2026-10-30") and sonuc["seviye"] == "TURUNCU"


def test_esas_tarihi_bilinmeyen_donem_olculmez():
    esaslar = pd.DataFrame({"dosya_no": ["D-1", "D-2"], "esas_ilk_giris": [None, None],
                            "tarih_bilinmiyor": [True, None]})
    atamalar = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-01-01"),
                              ("D-2", "AV-1", "TRAFIK", "2026-01-01")])
    sonuc = kriter1.degerlendir(atamalar, esaslar, None, KESIT, params_yukle())
    assert list(sonuc["kapsam_disi_nedeni"].fillna("")) == ["ESAS_TARIHI_BILINMIYOR", ""]
    assert list(sonuc["seviye"]) == ["KAPSAM_DISI", "KIRMIZI"]


def test_arsivden_once_var_olan_esas_sonraki_atamada_onceden_var_sayilir():
    # Esas ilk çekimde (2026-01-10) zaten doluydu, tarihi bilinmiyor. O günden sonraki atamada
    # esasın atamadan önce var olduğu kesindir; aynı gün ya da önceki atamada bilinmez.
    esaslar = pd.DataFrame({"dosya_no": ["D-1", "D-2", "D-3"],
                            "esas_ilk_giris": [None, None, None],
                            "tarih_bilinmiyor": [True, True, True],
                            "ilk_gorulme": ["2026-01-10", "2026-01-10", "2026-01-10"]})
    atamalar = atama_tablosu([("D-1", "AV-2", "TRAFIK", "2026-06-01"),
                              ("D-2", "AV-2", "TRAFIK", "2026-01-10"),
                              ("D-3", "AV-2", "TRAFIK", "2025-12-01")])
    sonuc = kriter1.degerlendir(atamalar, esaslar, None, KESIT, params_yukle())
    assert list(sonuc["kapsam_disi_nedeni"]) == [
        "ESAS_ONCEDEN_VAR", "ESAS_TARIHI_BILINMIYOR", "ESAS_TARIHI_BILINMIYOR"]
    assert "esas_gorulme" not in sonuc.columns


def test_dosya_basina_en_erken_esas_tarihi_alinir():
    esaslar = pd.DataFrame({"dosya_no": ["D-1", "D-1"],
                            "esas_ilk_giris": ["2026-11-10", "2026-11-05"]})
    atamalar = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-11-01")])
    sonuc = kriter1.degerlendir(atamalar, esaslar, None, KESIT, params_yukle())
    assert sonuc["sure_gun"].iloc[0] == 4


def test_hatali_girdi_hata_verir():
    tam = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-10-30")])
    assert hata_bekle(ValueError, _calistir, tam.drop(columns="atama_turu"))
    assert hata_bekle(ValueError, _calistir, atama_tablosu([("D-1", "AV-1", "TRAFIK", None)]))
    yinelenen = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-10-30 09:00"),
                               ("D-1", "AV-1", "TRAFIK", "2026-10-30 17:00")])
    assert hata_bekle(ValueError, _calistir, yinelenen)


def test_bos_girdi_bos_sonuc_verir():
    sonuc = _calistir(atama_tablosu([]))
    assert sonuc.empty and "seviye" in sonuc.columns
    assert olay.olaylar(sonuc, "K1").empty


def test_string_turundeki_ters_tarih_haksiz_dusum_uretmez():
    """Atama 1 Mayıs, esas string türünde 11.05.2026: 5 Kasım okunup 188 gün ve düşüm üretmez."""
    atamalar = atama_tablosu([("D-001", "AV-01", "YANGIN", "2026-05-01")])
    esaslar = pd.DataFrame({"dosya_no": ["D-001"],
                            "esas_ilk_giris": pd.Series(["11.05.2026"], dtype="string")})
    assert hata_bekle(ValueError, kriter1.degerlendir, atamalar, esaslar, None, "2026-11-19",
                      params_yukle())
    esaslar["esas_ilk_giris"] = pd.Series(["2026-05-11"], dtype="string")
    satir = kriter1.degerlendir(atamalar, esaslar, None, "2026-11-19", params_yukle()).iloc[0]
    assert (satir["seviye"], int(satir["sure_gun"]), bool(satir["dusum"])) == ("KAPANDI", 10, False)
