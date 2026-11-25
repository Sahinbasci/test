"""Kalite ve davranış sütun puanı testleri. Kesit 2026-11-19; pencere (2025-11-19, 2026-11-19].

Testler 1-5 ölçeği kullanır: 1 -> 0, 2 -> 25, 3 -> 50, 4 -> 75, 5 -> 100.
"""
import pandas as pd

from avukat_perf import kalite_davranis
from yardimci import hata_bekle, params_yukle

KESIT = "2026-11-19"
TARIH = "2026-06-01"
SUTUNLAR = ["avukat_kodu", "degerlendirme_tarihi", "alt_baslik", "puan"]


def _params(ters=(), **degisiklik):
    params = params_yukle()
    params["kalite_davranis"].update(olcek={"en_dusuk": 1, "en_yuksek": 5}, ters_yonlu=list(ters))
    params["kalite_davranis"].update(degisiklik)
    return params


def _kodlar(sutun):
    return params_yukle()["kalite_davranis"]["alt_basliklar"][sutun]


def _calistir(satirlar, params=None):
    tablo = pd.DataFrame(satirlar, columns=SUTUNLAR)
    sutun, alt = kalite_davranis.puanla(tablo, KESIT, params or _params())
    return sutun.set_index(["avukat_kodu", "sutun"]), alt


def _puanlar(avukat, sutun, degerler, tarih=TARIH):
    """Alt başlıkları sırayla degerler listesindeki puanlarla doldurur."""
    return [(avukat, tarih, kod, deger) for kod, deger in zip(_kodlar(sutun), degerler)]


def test_teyit_gelmeden_hesap_durur():
    tablo = pd.DataFrame(_puanlar("AV-1", "kalite", [4] * 6), columns=SUTUNLAR)
    assert hata_bekle(ValueError, kalite_davranis.puanla, tablo, KESIT, params_yukle())
    for eksik in ({"olcek": {"en_dusuk": 1, "en_yuksek": None}}, {"ters_yonlu": None}):
        params = _params()
        params["kalite_davranis"].update(eksik)
        assert hata_bekle(ValueError, kalite_davranis.puanla, tablo, KESIT, params)


def test_olcek_donusumu_ve_ters_yon():
    satirlar = _puanlar("AV-1", "kalite", [1, 2, 3, 4, 5, 5])
    _, alt = _calistir(satirlar, _params(ters=[_kodlar("kalite")[5]]))
    puan = alt.set_index("alt_baslik")["puan"]
    assert [puan[kod] for kod in _kodlar("kalite")] == [0.0, 25.0, 50.0, 75.0, 100.0, 0.0]


def test_kalite_ucte_iki_siniri_4_6_gecer_3_6_gecmez():
    sutun, _ = _calistir(_puanlar("AV-1", "kalite", [4, 4, 5, 5])
                         + _puanlar("AV-2", "kalite", [4, 4, 4]))
    assert sutun.loc[("AV-1", "kalite"), "durum"] == "GECERLI"
    assert sutun.loc[("AV-1", "kalite"), "puan"] == 87.5
    assert sutun.loc[("AV-2", "kalite"), "durum"] == "EKSIK_DEGERLENDIRME"
    assert pd.isna(sutun.loc[("AV-2", "kalite"), "puan"])
    assert sutun.loc[("AV-2", "kalite"), "puanlanan"] == 3
    assert sutun.loc[("AV-2", "kalite"), "toplam"] == 6


def test_davranis_ucte_iki_siniri_5_7_gecer_4_7_gecmez():
    sutun, _ = _calistir(_puanlar("AV-1", "davranis", [3] * 5)
                         + _puanlar("AV-2", "davranis", [3] * 4))
    assert sutun.loc[("AV-1", "davranis"), "durum"] == "GECERLI"
    assert sutun.loc[("AV-2", "davranis"), "durum"] == "EKSIK_DEGERLENDIRME"
    # Ekran yeterlilik eşiğini parametreden değil bu sütundan gösterir.
    assert sutun.loc[("AV-1", "davranis"), "gereken"] == 5
    assert sutun.loc[("AV-1", "kalite"), "gereken"] == 4


def test_gereken_sayi_yeterlilik_parametresinden():
    satirlar = _puanlar("AV-1", "davranis", [3] * 4) + _puanlar("AV-1", "kalite", [3] * 3)
    sutun, _ = _calistir(satirlar, _params(yeterlilik=[1, 2]))  # yarısı: 4/7 ve 3/6 geçer
    assert list(sutun.loc[[("AV-1", "davranis"), ("AV-1", "kalite")], "gereken"]) == [4, 3]
    assert set(sutun.loc[[("AV-1", "davranis"), ("AV-1", "kalite")], "durum"]) == {"GECERLI"}


def test_yeterlilik_orani_parametredir():
    sutun, _ = _calistir(_puanlar("AV-1", "kalite", [4] * 3), _params(yeterlilik=[1, 2]))
    assert sutun.loc[("AV-1", "kalite"), "durum"] == "GECERLI"


def test_puanlanmamis_alt_baslik_ortalamaya_girmez():
    satirlar = _puanlar("AV-1", "kalite", [5, 5, 5, 5, 1, None])
    sutun, alt = _calistir(satirlar)
    assert sutun.loc[("AV-1", "kalite"), "puanlanan"] == 5
    assert sutun.loc[("AV-1", "kalite"), "puan"] == 80.0
    assert len(alt) == 5


def test_her_avukat_icin_iki_sutun_da_yer_alir():
    sutun, _ = _calistir(_puanlar("AV-1", "kalite", [4] * 6))
    assert list(sutun.index) == [("AV-1", "kalite"), ("AV-1", "davranis")]
    assert sutun.loc[("AV-1", "davranis"), "durum"] == "EKSIK_DEGERLENDIRME"
    assert sutun.loc[("AV-1", "davranis"), "puanlanan"] == 0


def test_birden_cok_degerlendirme_ortalama_kurali():
    kod = _kodlar("kalite")[0]
    satirlar = [("AV-1", "2026-01-01", kod, 2), ("AV-1", "2026-05-01", kod, 4),
                ("AV-1", "2026-05-01", kod, 5)]
    _, alt = _calistir(satirlar)
    assert abs(alt["puan"].iloc[0] - (25 + 75 + 100) / 3) < 1e-9
    assert alt["degerlendirme_sayisi"].iloc[0] == 3


def test_birden_cok_degerlendirme_son_kurali():
    kod = _kodlar("kalite")[0]
    satirlar = [("AV-1", "2026-01-01", kod, 2), ("AV-1", "2026-05-01", kod, 4),
                ("AV-1", "2026-05-01", kod, 5), ("AV-1", "2026-07-01", kod, None)]
    _, alt = _calistir(satirlar, _params(coklu_degerlendirme="son"))
    assert alt["puan"].iloc[0] == 87.5 and alt["degerlendirme_sayisi"].iloc[0] == 3


def test_pencere_sinirlari():
    kod = _kodlar("kalite")[0]
    satirlar = [("AV-1", "2025-11-19", kod, 1), ("AV-1", "2025-11-20", kod, 5),
                ("AV-1", "2026-11-20", kod, 1), ("AV-2", "2025-11-19", kod, 3)]
    sutun, alt = _calistir(satirlar)
    assert list(alt["avukat_kodu"]) == ["AV-1"] and alt["puan"].iloc[0] == 100.0
    assert "AV-2" not in sutun.index.get_level_values(0)


def test_tanimsiz_kod_ve_eski_alanlar_yok_sayilir():
    satirlar = [("AV-1", TARIH, "eski_brans_yetkinligi", 3),
                ("AV-2", TARIH, "eski_durustluk_duzeyi", 3)] + _puanlar("AV-2", "kalite", [4])
    sutun, alt = _calistir(satirlar)
    assert sorted(set(sutun.index.get_level_values(0))) == ["AV-2"]
    assert list(alt["alt_baslik"]) == [_kodlar("kalite")[0]]


def test_metin_puan_sayiya_cevrilir_hatali_girdi_hata_verir():
    sutun, _ = _calistir([(a, t, k, str(p)) for a, t, k, p in _puanlar("AV-1", "kalite",
                                                                       [4] * 6)])
    assert sutun.loc[("AV-1", "kalite"), "puan"] == 75.0
    params = _params()
    for satirlar in (_puanlar("AV-1", "kalite", [6]), _puanlar("AV-1", "kalite", [0]),
                     _puanlar("AV-1", "kalite", ["dört"]), [("AV-1", None, "x", 3)]):
        tablo = pd.DataFrame(satirlar, columns=SUTUNLAR)
        assert hata_bekle(ValueError, kalite_davranis.puanla, tablo, KESIT, params), satirlar
    eksik = pd.DataFrame(_puanlar("AV-1", "kalite", [4]), columns=SUTUNLAR).drop(columns="puan")
    assert hata_bekle(ValueError, kalite_davranis.puanla, eksik, KESIT, params)


def test_bos_girdi_bos_sonuc_verir():
    sutun, alt = _calistir([])
    assert sutun.empty and alt.empty and "durum" in sutun.columns


def test_mevcut_alanlar_bilgi_amacli_ve_olcek_teyidi_gerektirmez():
    params = params_yukle()  # ölçek ve yön null: sütun puanı yok, mevcut alanlar gösterilir
    tablo = pd.DataFrame([("AV-1", "2026-06-01", "brans_yetkinligi", 4.0),
                          ("AV-1", "2026-09-01", "brans_yetkinligi", 2.0),
                          ("AV-1", "2026-09-01", "cozum_yetenegi", None),
                          ("AV-1", "2025-01-01", "ulasilabilirlik", 5.0),
                          ("AV-1", "2026-09-01", "dosyaya_hakimiyet", 1.0),
                          ("AV-2", "2026-10-01", "durustluk_duzeyi", 3.0)], columns=SUTUNLAR)
    sonuc = kalite_davranis.mevcut_alanlar(tablo, KESIT, params).set_index(
        ["avukat_kodu", "alt_baslik"])
    # Pencere dışı, boş puan ve alt başlık kodu sayılmaz; ölçek çevrilmez.
    assert sorted(sonuc.index) == [("AV-1", "brans_yetkinligi"), ("AV-2", "durustluk_duzeyi")]
    assert sonuc.loc[("AV-1", "brans_yetkinligi"), "puan"] == 3.0
    assert sonuc.loc[("AV-1", "brans_yetkinligi"), "degerlendirme_sayisi"] == 2
    assert sonuc.loc[("AV-1", "brans_yetkinligi"), "son_degerlendirme"] == pd.Timestamp(
        "2026-09-01")
