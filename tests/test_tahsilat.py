"""Tahsilat sütun puanı testleri. Kesit 2026-11-19.

Portföy yardımcısı olgun dosyalar üretir: rücuya veriliş 2023-01-01, atama 2023-02-01,
tek tahsilat 2024-01-01. Dosyanın tahsilatı rücu tutarının verilen oranı kadardır.
"""
import pandas as pd

from avukat_perf import tahsilat, tahsilat_evren
from yardimci import atama_tablosu, hata_bekle, params_yukle

KESIT = "2026-11-19"
DOSYA_SUTUNLARI = ["dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi"]


def _yakin(deger, beklenen, tolerans=1e-6):
    return abs(deger - beklenen) < tolerans


def _params(**tahsilat_degisikligi):
    params = params_yukle()
    params["tahsilat"].update(tahsilat_degisikligi)
    return params


def _portfoy(avukat, adet, brans, rucu, oran, ilk_no):
    nolar = ["D-{:05d}".format(ilk_no + sira) for sira in range(adet)]
    return ([(no, brans, rucu, "2023-01-01") for no in nolar],
            [(no, avukat, brans, "2023-02-01") for no in nolar],
            [(no, "2024-01-01", rucu * oran) for no in nolar])


def _calistir(parcalar, params=None, kesit=KESIT, hareket_ek=()):
    dosya, atama_satiri, hareket = [], [], list(hareket_ek)
    for dosya_parca, atama_parca, hareket_parca in parcalar:
        dosya += dosya_parca
        atama_satiri += atama_parca
        hareket += hareket_parca
    avukat, grup = tahsilat.puanla(
        pd.DataFrame(dosya, columns=DOSYA_SUTUNLARI), atama_tablosu(atama_satiri),
        pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]),
        kesit, params or params_yukle())
    return avukat.set_index("avukat_kodu"), grup


def test_puan_formulu_kontrol_degerleri():
    tah = params_yukle()["tahsilat"]
    r, puan, neden = tahsilat.puan_hesapla(20, 150.0, 100.0, tah)
    assert _yakin(r, 40 / 30) and _yakin(puan, 75 + 50 / 3) and neden is None
    assert tahsilat.puan_hesapla(20, 100.0, 100.0, tah)[1] == 75.0
    assert tahsilat.puan_hesapla(20, 300.0, 100.0, tah)[1] == 100.0


def test_guven_ayari_az_dosyada_r_yi_bire_yaklastirir():
    tah = params_yukle()["tahsilat"]
    az = tahsilat.puan_hesapla(20, 150.0, 100.0, tah)[0]
    cok = tahsilat.puan_hesapla(200, 150.0, 100.0, tah)[0]
    assert 1.0 < az < cok < 1.5


def test_puan_alt_siniri_varsayilan_parametrede_25():
    tah = params_yukle()["tahsilat"]
    assert _yakin(tahsilat.puan_hesapla(10 ** 9, 0.0, 100.0, tah)[1], 25.0)
    dik = dict(tah, egim=100)
    assert tahsilat.puan_hesapla(10 ** 9, 0.0, 100.0, dik)[1] == 0.0


def test_ayni_beceri_farkli_portfoy_ve_brans_hepsi_75():
    avukat, _ = _calistir([
        _portfoy("AV-1", 25, "TRAFIK", 10000.0, 0.30, 0),
        _portfoy("AV-2", 200, "YANGIN", 100000.0, 0.10, 1000),
        _portfoy("AV-3", 15, "TRAFIK", 10000.0, 0.30, 2000),
        _portfoy("AV-3", 15, "YANGIN", 100000.0, 0.10, 3000)])
    assert all(_yakin(puan, 75.0) for puan in avukat["puan"])
    assert set(avukat["durum"]) == {"GECERLI"}
    ham_oran = avukat["gerceklesen"] / pd.Series({"AV-1": 25e4, "AV-2": 2e7, "AV-3": 165e4})
    assert _yakin(ham_oran["AV-1"], 0.30) and _yakin(ham_oran["AV-2"], 0.10)


def test_iyi_avukat_75_ustu_zayif_avukat_alti_digerleriyle_kiyaslanir():
    avukat, grup = _calistir([_portfoy("AV-1", 30, "TRAFIK", 10000.0, 0.36, 0),
                              _portfoy("AV-2", 30, "TRAFIK", 10000.0, 0.24, 100)])
    assert _yakin(grup["oran"].iloc[0], 0.30)  # grup tablosu grubun bütün oranını gösterir
    # Beklenti diğer avukattan: AV-1 için 0,24 (oran 1,5; R = (30 × 1,5 + 10) ÷ 40 = 1,375),
    # AV-2 için 0,36 (oran 2/3; R = 0,75).
    assert _yakin(avukat.loc["AV-1", "beklenen"], 300000 * 0.24)
    assert avukat.loc["AV-1", "puan_tutar"] == 93.75 and avukat.loc["AV-2", "puan_tutar"] == 62.5
    # İkisi de bütün dosyalarında tahsilat yaptı (sıklık 75), pencerede tahsilat yok (güncellik
    # 75): tahsilat puanı = 0,6 × tutar + 0,2 × 75 + 0,2 × 75.
    assert list(avukat["puan_siklik"]) == [75.0, 75.0] == list(avukat["puan_guncellik"])
    assert avukat.loc["AV-1", "puan"] == 86.25 and avukat.loc["AV-2", "puan"] == 67.5


def test_az_dosyada_puan_uyariyla_uretilir_sifir_olcut_ust_katmana_gecer():
    """Olgun dosya yeterli veri eşiğinin (10) altındaysa puan yine üretilir ve geçerlidir;
    yeterli işareti yanlıştır (ekranda 'Yeterli veri yok'). Tam 10 dosya yeterlidir. Yangında
    diğer avukatın (AV-4) tahsilatı yok: ölçüt yok sayılır, AV-3'ün beklentisi bütün diğer
    avukatların oranından gelir (önceden beklenen sıfır ve puan yoktu)."""
    avukat, _ = _calistir([_portfoy("AV-1", 9, "TRAFIK", 10000.0, 0.30, 0),
                           _portfoy("AV-2", 10, "TRAFIK", 10000.0, 0.30, 100),
                           _portfoy("AV-3", 25, "YANGIN", 10000.0, 0.0, 200),
                           # AV-4: yangında tahsilat yok
                           _portfoy("AV-4", 25, "YANGIN", 10000.0, 0.0, 300)])
    assert avukat.loc["AV-1", "durum"] == "GECERLI" and avukat.loc["AV-1", "puan"] == 75.0
    assert pd.isna(avukat.loc["AV-1", "eksik_nedeni"]) and not bool(avukat.loc["AV-1", "yeterli"])
    assert avukat.loc["AV-2", "durum"] == "GECERLI" and bool(avukat.loc["AV-2", "yeterli"])
    assert pd.isna(avukat.loc["AV-3", "eksik_nedeni"]) and avukat.loc["AV-3", "durum"] == "GECERLI"
    # Bütün diğerleri: AV-1 ve AV-2 rücunun %30'unu, AV-4 hiç tahsil etmedi (19 × 0,3 ÷ 44).
    beklenen = 25 * 10000.0 * (19 * 3000.0) / (44 * 10000.0)
    assert abs(avukat.loc["AV-3", "beklenen"] - beklenen) < 1e-6


def test_yeniden_atanan_dosya_iki_avukata_bolunur():
    dosya = ([("D-1", "TRAFIK", 1000.0, "2023-01-01")], [
        ("D-1", "AV-9", "TRAFIK", "2023-01-10", "2023-02-01", None, "SULH"),
        ("D-1", "AV-1", "TRAFIK", "2023-02-01", "2024-02-01", "YENIDEN_ATAMA"),
        ("D-1", "AV-2", "TRAFIK", "2024-02-01")], [
        ("D-1", "2023-01-15", 30.0), ("D-1", "2023-06-01", 100.0),
        ("D-1", "2024-02-01", 50.0), ("D-1", "2025-01-01", 70.0),
        ("D-1", "2025-02-01", -20.0), ("D-1", "2026-12-01", 999.0)])
    avukat, grup = _calistir([dosya])
    gun1 = (pd.Timestamp("2024-02-01") - pd.Timestamp("2023-02-01")).days
    gun2 = (pd.Timestamp("2026-11-20") - pd.Timestamp("2024-02-01")).days
    assert list(avukat.index) == ["AV-1", "AV-2"]
    assert avukat.loc["AV-1", "gerceklesen"] == 100.0 and avukat.loc["AV-2", "gerceklesen"] == 100.0
    assert _yakin(avukat.loc["AV-1", "n"], gun1 / (gun1 + gun2))
    # Beklenti diğer avukatın oranından: AV-2 100 TL'yi payıyla tuttuğu rücuda topladı.
    assert _yakin(avukat.loc["AV-1", "beklenen"], 100.0 * gun1 / gun2)
    assert grup["atfedilen"].iloc[0] == 200.0 and grup["atanamayan"].iloc[0] == 30.0
    assert _yakin(grup["oran"].iloc[0], 0.20)


def test_grup_orani_yalniz_olgun_dosyalardan_ve_tum_avukatlardan():
    genc = ([("D-9", "TRAFIK", 10000.0, "2026-01-01")],
            [("D-9", "AV-1", "TRAFIK", "2026-01-05")], [("D-9", "2026-03-01", 9000.0)])
    avukat, grup = _calistir([_portfoy("AV-1", 20, "TRAFIK", 10000.0, 0.30, 0),
                              _portfoy("AV-2", 20, "TRAFIK", 10000.0, 0.10, 100), genc])
    assert _yakin(grup["oran"].iloc[0], 0.20) and _yakin(grup["dosya_sayisi"].iloc[0], 40)
    assert _yakin(avukat.loc["AV-1", "gerceklesen"], 60000.0)
    assert _yakin(avukat.loc["AV-1", "oran"], 3.0)  # beklenti diğer avukatın oranından (0,10)


def test_tutar_bandi_ayri_grup_olusturur():
    # Her bantta aynı başarıda iki avukat: karşılaştırma bant içindeki diğer avukatla yapılır.
    parcalar = [_portfoy("AV-1", 20, "TRAFIK", 10000.0, 0.30, 0),
                _portfoy("AV-3", 20, "TRAFIK", 10000.0, 0.30, 200),
                _portfoy("AV-2", 20, "TRAFIK", 100000.0, 0.10, 100),
                _portfoy("AV-4", 20, "TRAFIK", 100000.0, 0.10, 300)]
    tek_bant, _ = _calistir(parcalar, _params(tutar_bantlari=[]))
    iki_bant, grup = _calistir(parcalar, _params(tutar_bantlari=[50000]))
    varsayilan, _ = _calistir(parcalar)  # varsayılan sınırlar (40 bin, 150 bin) iki dosyayı ayırır
    assert all(_yakin(puan, 75.0) for puan in varsayilan["puan"])
    assert tek_bant.loc["AV-1", "puan"] > 75 > tek_bant.loc["AV-2", "puan"]
    assert all(_yakin(puan, 75.0) for puan in iki_bant["puan"])
    assert list(grup["tutar_bandi"]) == [0, 1]


def test_bant_siniri_ust_banda_girer():
    dosyalar = pd.DataFrame([("D-1", "TRAFIK", 49999.99, "2023-01-01"),
                             ("D-2", "TRAFIK", 50000.0, "2023-01-01"),
                             ("D-3", "TRAFIK", 0.0, "2023-01-01")], columns=DOSYA_SUTUNLARI)
    tah = _params(tutar_bantlari=[50000, 250000])["tahsilat"]
    assert list(tahsilat_evren.olgun_dosyalar(dosyalar, KESIT, tah)["tutar_bandi"]) == [0, 1, 0]


def test_olgunluk_siniri_brans_suresine_gore_ve_dahil():
    dosyalar = pd.DataFrame([
        ("D-1", "TRAFIK", 1.0, "2024-11-19"), ("D-2", "TRAFIK", 1.0, "2024-11-20"),
        ("D-3", "KASKO", 1.0, "2024-11-19"), ("D-4", "YANGIN", 1.0, "2023-11-19"),
        ("D-5", "YANGIN", 1.0, "2023-11-20"), ("D-6", "YANGIN", 1.0, "2024-11-19")],
        columns=DOSYA_SUTUNLARI)
    olgun = tahsilat_evren.olgun_dosyalar(dosyalar, KESIT, params_yukle()["tahsilat"])
    assert list(olgun["dosya_no"]) == ["D-1", "D-3", "D-4"]


def test_hatali_girdi_ve_uygulanmamis_secenek_hata_verir():
    negatif = pd.DataFrame([("D-1", "TRAFIK", -1.0, "2023-01-01")], columns=DOSYA_SUTUNLARI)
    bos = pd.DataFrame([("D-1", "TRAFIK", None, "2023-01-01")], columns=DOSYA_SUTUNLARI)
    tah = params_yukle()["tahsilat"]
    assert hata_bekle(ValueError, tahsilat_evren.olgun_dosyalar, negatif, KESIT, tah)
    assert hata_bekle(ValueError, tahsilat_evren.olgun_dosyalar, bos, KESIT, tah)
    assert hata_bekle(ValueError, _calistir, [], _params(enflasyon_duzeltme=True))


def test_metin_tutar_sayiya_cevrilir_gecersiz_metin_hata_verir():
    dosya, atama_satiri, hareket = _portfoy("AV-1", 20, "TRAFIK", 10000.0, 0.30, 0)
    metin = ([(no, brans, str(rucu), tarih) for no, brans, rucu, tarih in dosya],
             atama_satiri, [(no, tarih, str(tutar)) for no, tarih, tutar in hareket])
    avukat, _ = _calistir([metin])
    assert _yakin(avukat.loc["AV-1", "gerceklesen"], 60000.0)
    bozuk = (dosya, atama_satiri, hareket + [("D-00000", "2024-02-01", "on bin")])
    assert hata_bekle(ValueError, _calistir, [bozuk])


def test_bos_girdi_bos_sonuc_verir():
    avukat, grup = _calistir([])
    assert avukat.empty and grup.empty and "puan" in avukat.columns


def test_kesirli_n_esikte_kayan_nokta_artigiyla_dusmez():
    # 100 dosyada 0,1 elde tutma payı: matematiksel olarak n = 10, kayan noktayla 9,999…; 10
    # dosyada 0,1 pay: n = 1, kayan noktayla 0,999…
    tah = params_yukle()["tahsilat"]
    assert tah["en_az_olgun_dosya"] == 1 and tah["yeterli_olgun_dosya"] == 10
    n = sum([0.1] * 100)
    assert n < 10 and tahsilat.yeterli_mi(n, tah) and not tahsilat.yeterli_mi(9.99, tah)
    bir = sum([0.1] * 10)
    assert bir < 1 and tahsilat.puan_hesapla(bir, 100.0, 100.0, tah)[2] is None
    assert tahsilat.puan_hesapla(0.99, 100.0, 100.0, tah)[2] == "AZ_DOSYA"


def test_kayan_nokta_artigi_beklenen_sayilmaz():
    """Net sıfır hareket dizisi (13033,45 − 11730,90 − 1302,55) 1e-12 artık bırakır; beklenen
    sıfır sayılır, sahte geçerli puan üretilmez."""
    tah = params_yukle()["tahsilat"]
    artik = 13033.45 - 11730.90 - 1302.55
    assert artik != 0 and tahsilat.puan_hesapla(25, 0.0, artik, tah)[2] == "BEKLENEN_SIFIR"


def test_brans_kirilimi_avukat_toplamini_boler_puana_girmez():
    # AV-1: trafikte 25 dosya oran 0,04, kaskoda 5 dosya oran 0,10; AV-2 trafikte 25 dosya 0,02.
    parcalar = [_portfoy("AV-1", 25, "TRAFIK", 1000.0, 0.04, 0),
                _portfoy("AV-1", 5, "KASKO", 1000.0, 0.10, 100),
                _portfoy("AV-2", 25, "TRAFIK", 1000.0, 0.02, 200)]
    dosya, atama_satiri, hareket = [], [], []
    for d, a, h in parcalar:
        dosya, atama_satiri, hareket = dosya + d, atama_satiri + a, hareket + h
    girdi = (pd.DataFrame(dosya, columns=DOSYA_SUTUNLARI), atama_tablosu(atama_satiri),
             pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]))
    for gruplama in (["brans", "tutar_bandi"], ["tutar_bandi"]):
        params = _params(gruplama=gruplama)
        avukat, _, brans = tahsilat.hesapla(*girdi, kesit=KESIT, params=params)
        toplam = brans.groupby("avukat_kodu")[["n", "gerceklesen", "beklenen"]].sum()
        for ad in ("n", "gerceklesen", "beklenen"):
            assert all(_yakin(toplam.loc[k, ad], avukat.set_index("avukat_kodu").loc[k, ad])
                       for k in ("AV-1", "AV-2")), (gruplama, ad)
        satir = brans.set_index(["avukat_kodu", "brans"])
        assert satir.loc[("AV-1", "TRAFIK"), "n"] == 25.0
        assert bool(satir.loc[("AV-1", "TRAFIK"), "yeterli"])
        assert not bool(satir.loc[("AV-1", "KASKO"), "yeterli"])  # 5 dosya < 10
    # Trafikte her avukat diğeriyle kıyaslanır: AV-1 0,04 ÷ 0,02 = 2, AV-2 0,02 ÷ 0,04 = 0,5.
    # Kaskoda AV-1 yalnız; branşta da başka avukat yok, bütün diğer avukatların oranı (0,02).
    _, _, brans = tahsilat.hesapla(*girdi, kesit=KESIT, params=params_yukle())
    satir = brans.set_index(["avukat_kodu", "brans"])
    assert _yakin(satir.loc[("AV-1", "TRAFIK"), "oran"], 2.0)
    assert _yakin(satir.loc[("AV-2", "TRAFIK"), "oran"], 0.5)
    assert _yakin(satir.loc[("AV-1", "KASKO"), "oran"], 5.0)


def _kirilim(parcalar):
    dosya, atama_satiri, hareket = [], [], []
    for d, a, h in parcalar:
        dosya, atama_satiri, hareket = dosya + d, atama_satiri + a, hareket + h
    return tahsilat.hesapla(pd.DataFrame(dosya, columns=DOSYA_SUTUNLARI),
                            atama_tablosu(atama_satiri),
                            pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]),
                            KESIT, params_yukle())[2].set_index(["avukat_kodu", "brans"])


def test_brans_yeterliligi_tabanin_tam_sinirinda_ve_yarim_kurusta_oran_yok():
    # Trafikte tam 10 olgun dosya yeterlidir (n >= 10); 9 dosya değildir ama branş puanı yine
    # üretilir.
    brans = _kirilim([_portfoy("AV-1", 10, "TRAFIK", 1000.0, 0.04, 0),
                      _portfoy("AV-2", 9, "TRAFIK", 1000.0, 0.02, 100)])
    assert bool(brans.loc[("AV-1", "TRAFIK"), "yeterli"])
    assert not bool(brans.loc[("AV-2", "TRAFIK"), "yeterli"])
    assert pd.notna(brans.loc[("AV-2", "TRAFIK"), "puan"])
    # Branşın bütün tahsilatı 0,001 TL: yarım kuruşu aşmayan tahsilat ölçüt sayılmaz, beklenen
    # yarım kuruşun altında kalır ve oran üretilmez (kayan nokta artığı sahte 1,0 oran vermez).
    brans = _kirilim([_portfoy("AV-1", 25, "KASKO", 1000.0, 0.001 / 25000.0, 0),
                      _portfoy("AV-2", 25, "KASKO", 1000.0, 0.001 / 25000.0, 100)])
    satir = brans.loc[("AV-1", "KASKO")]
    assert satir["beklenen"] < tahsilat.YARIM_KURUS and pd.isna(satir["oran"])
