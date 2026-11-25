"""Tahsilat puanının bileşenleri: dosya yaşı bandı, sıklık, güncellik, birleşim ve branş puanı.

Örnekler elle hesaplanmıştır. Kesit 19.11.2026; güncellik penceresi (19.11.2025, 19.11.2026],
365 gün. Sıklık ve güncellik kişi-zaman sayımıdır: gerçekleşen, tahsilat yapılan dosya-ay;
beklenen, elde tutulan dosya-yıl × grup hızı (grup: branş, o günkü yaş bandı, tutar bandı).
"""
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from avukat_perf import gozlem, tahsilat, tahsilat_evren, tahsilat_maruz, tahsilat_puan
from yardimci import atama_tablosu, params_yukle

KESIT = "2026-11-19"
SUTUN = ["dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi"]
ONCE, PENCEREDE = "2024-01-01", "2026-03-01"  # pencereden önce ve pencere içinde tahsilat günü


def _parca(avukat, adet, ilk_no, tahsilatlar, verilis="2023-01-01", atama="2023-02-01",
           brans="TRAFIK", rucu=1000.0):
    """adet dosya; tahsilatlar: {sıra (0'dan): [(tarih, tutar), ...]}."""
    nolar = ["D-{:05d}".format(ilk_no + sira) for sira in range(adet)]
    return ([(no, brans, rucu, verilis) for no in nolar],
            [(no, avukat, brans, atama) for no in nolar],
            [(nolar[sira], tarih, tutar) for sira, liste in tahsilatlar.items()
             for tarih, tutar in liste])


def _hesapla(parcalar, params=None, kapanis=None):
    dosya, atamalar, hareket = [], [], []
    for d, a, h in parcalar:
        dosya, atamalar, hareket = dosya + d, atamalar + a, hareket + h
    avukat, grup, brans = tahsilat.hesapla(
        pd.DataFrame(dosya, columns=SUTUN), atama_tablosu(atamalar),
        pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]), KESIT,
        params or params_yukle(), kapanis)
    return avukat.set_index("avukat_kodu"), grup, brans.set_index(["avukat_kodu", "brans"])


def _params(**tahsilat_degisikligi):
    params = params_yukle()
    params["tahsilat"].update(tahsilat_degisikligi)
    return params


def _yuvarla(deger):
    return float(Decimal(repr(deger)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def test_yas_bandi_tamamlanan_sinir_sayisi_sinir_gunu_dahil():
    verilis = ["2025-11-20", "2025-11-19", "2024-11-19", "2023-11-20", "2019-11-19", "2019-11-20"]
    dosyalar = pd.DataFrame([("D-{}".format(i), "TRAFIK", 1.0, gun)
                             for i, gun in enumerate(verilis)], columns=SUTUN)
    tah = params_yukle()["tahsilat"]
    assert tah["yas_bantlari"] == [12, 24, 36, 48, 60, 84]
    bant = tahsilat_evren.bantli_dosyalar(dosyalar, KESIT, tah)["yas_bandi"]
    assert list(bant) == [0, 1, 2, 2, 6, 5]
    etiket = tahsilat_evren.yas_etiketleri(tah)
    assert etiket[0] == "0–12 ay" and etiket[5] == "60–84 ay" and etiket[6] == "84+ ay"
    assert len(etiket) == 7
    assert tahsilat_evren.yas_etiketleri(dict(tah, yas_bantlari=[])) == {0: "Tüm yaşlar"}
    tek = tahsilat_evren.bantli_dosyalar(dosyalar, KESIT, dict(tah, yas_bantlari=[]))
    assert set(tek["yas_bandi"]) == {0}


def test_dosya_yasi_beklentiye_girer_eski_ve_yeni_portfoy_ayni_puani_alir():
    """Tahsilat dosyanın ömrüne yayılır: her dosya altı aylıkken bir kez tahsilat alır ve eski
    dosyalar zamanla daha çok toplamıştır (kesitte 6 yaşındaki dosyada rücunun %40'ı, 2
    yaşındakinde %10'u). Herkes aynı başarıda; yaş bandı gruplamadayken portföyü eski, yeni ve
    karma olan üç avukat da üç bileşende 75 alır. Yaş bandı olmasa eski portföy ödüllendirilir."""
    def dosyalar(avukat, adet, ilk_no, verilis, ilk_tahsilat, oran):
        return _parca(avukat, adet, ilk_no, {s: [(ilk_tahsilat, 1000.0 * oran)]
                                             for s in range(adet)}, verilis, verilis)
    parcalar = [dosyalar("AV-ESKI", 30, 0, "2020-06-01", "2020-12-01", 0.40),
                dosyalar("AV-YENI", 30, 100, "2024-06-01", "2024-12-01", 0.10),
                dosyalar("AV-KARMA", 20, 200, "2020-06-01", "2020-12-01", 0.40),
                dosyalar("AV-KARMA", 20, 300, "2024-06-01", "2024-12-01", 0.10)]
    avukat, grup, _ = _hesapla(parcalar)
    assert sorted(grup["yas_bandi"]) == [2, 5]
    for ad in ("puan_tutar", "puan_siklik", "puan_guncellik", "puan"):
        assert list(avukat[ad]) == [75.0] * 3, ad
    yassiz, _, _ = _hesapla(parcalar, _params(gruplama=["brans"]))
    assert yassiz.loc["AV-ESKI", "puan_tutar"] > 90 and yassiz.loc["AV-YENI", "puan_tutar"] < 60
    assert yassiz.loc["AV-KARMA", "puan_tutar"] == 75.0


def test_siklik_tahsilat_yapilan_dosya_ay_sayisi_beklenene_gore():
    """AV-1 ve AV-2 30'ar dosyayı aynı süre tutar; AV-1 24, AV-2 12 dosya-ayda tahsilat yaptı.
    Maruziyetler eşit; beklenti diğer avukatın hızından: AV-1 için 12, AV-2 için 24. Aynı ay
    içinde ters kayıtla neti sıfırlanan ay tahsilat yapılmış sayılmaz."""
    bir = {s: [(ONCE, 100.0)] for s in range(25)}
    bir[24] = [(ONCE, 100.0), ("2024-01-20", -100.0)]
    avukat, _, _ = _hesapla([_parca("AV-1", 30, 0, bir),
                             _parca("AV-2", 30, 100, {s: [(ONCE, 100.0)] for s in range(12)})])
    assert list(avukat["siklik_o"]) == [24.0, 12.0]
    assert [round(e, 9) for e in avukat["siklik_e"]] == [12.0, 24.0]
    # R = (24 + 10) ÷ (12 + 10) = 1,545 → 100 (kırpma); R = (12 + 10) ÷ 34 = 0,6471 → 57,35
    assert list(avukat["puan_siklik"]) == [100.0, 57.35]
    # Tutar: AV-1 2.400 ÷ 1.200 = 2 → R = (60 + 10) ÷ 40 = 1,75 → 100; AV-2 0,5 → R = 0,625
    # → 56,25. Güncellik 75 (pencerede tahsilat yok, beklenen 0).
    assert list(avukat["puan_tutar"]) == [100.0, 56.25]
    assert list(avukat["puan_guncellik"]) == [75.0] * 2
    # 0,6 × 100 + 0,2 × 100 + 0,2 × 75 = 95; 0,6 × 56,25 + 0,2 × 57,35 + 15 = 60,22
    assert list(avukat["puan"]) == [95.0, 60.22]
    # Bir dosyada üç ayda tahsilat üç olaydır; aynı ayın iki tahsilatı bir olay.
    uc, _, _ = _hesapla([_parca("AV-1", 30, 0, {0: [(ONCE, 1.0), ("2024-02-03", 1.0),
                                                    ("2024-02-20", 1.0), ("2024-03-01", 1.0)]})])
    assert list(uc["siklik_o"]) == [3.0]


def test_taksitli_adil_dunyada_sayim_bilesenleri_75():
    """Her dosya elinde bulunduğu her ay (ayın 15'inde) tahsilat alır; herkes aynı başarıda.
    AV-TEK dosyalarını sürekli tutar, AV-KISA 6 ay tutup AV-UZUN'a devreder (ay başında). Dosyayı
    kısa ya da uzun tutmak puanı değiştirmez (dosya başına 'tahsilat var mı'
    sayımı kısa tutanı 13 puana kadar kayırıyordu). Ay uzunluğu farkından kalan sapma küçüktür."""
    aylar = [str(gun.date()) for gun in pd.date_range("2023-02-01", "2026-11-01", freq="MS")
             + pd.Timedelta(days=14)]
    tek = _parca("AV-TEK", 30, 0, {s: [(ay, 10.0) for ay in aylar] for s in range(30)},
                 verilis="2023-01-01", atama="2023-02-01")
    nolar = ["D-{:05d}".format(500 + s) for s in range(30)]
    devir = ([(no, "TRAFIK", 1000.0, "2023-01-01") for no in nolar],
             [(no, "AV-KISA", "TRAFIK", "2023-02-01", "2023-08-01", "YENIDEN_ATAMA")
              for no in nolar] + [(no, "AV-UZUN", "TRAFIK", "2023-08-01") for no in nolar],
             [(no, ay, 10.0) for no in nolar for ay in aylar])
    avukat, _, _ = _hesapla([tek, devir])
    assert list(avukat.loc[["AV-KISA", "AV-TEK", "AV-UZUN"], "siklik_o"]) == [180, 1380, 1200]
    oran = avukat["siklik_o"] / avukat["siklik_e"]
    assert ((oran - 1).abs() < 0.03).all(), oran.to_dict()
    for ad in ("puan_siklik", "puan_guncellik"):
        assert (avukat[ad].dropna() - 75).abs().max() < 0.8, avukat[ad].to_dict()


ESKI = {"verilis": "2018-01-01", "atama": "2018-02-01"}  # pencerede yaş bandı sınırı yok (84+ ay)


def _guncellik_parcalari():
    return [_parca("AV-1", 20, 0, {s: [(PENCEREDE, 50.0)] for s in range(8)}, **ESKI),
            _parca("AV-2", 20, 100, {s: [(PENCEREDE, 50.0)] for s in range(2)}, **ESKI)]


def test_guncellik_pencerede_tahsilat_gelen_dosya_ay_beklenene_gore():
    """İki avukat 20'şer dosyayı pencere boyunca tutuyor; AV-1'in 8, AV-2'nin 2 dosya-ayında
    tahsilat var. Beklenti diğer avukatın hızından: AV-1 için 20 × 2/20 = 2, AV-2 için 8."""
    avukat, _, _ = _hesapla(_guncellik_parcalari())
    assert list(avukat["guncellik_o"]) == [8.0, 2.0]
    assert [round(e, 9) for e in avukat["guncellik_e"]] == [2.0, 8.0]
    # R = (8 + 10) ÷ (2 + 10) = 1,5 → 100; R = (2 + 10) ÷ 18 = 0,6667 → 58,33
    assert list(avukat["puan_guncellik"]) == [100.0, 58.33]


def test_kapanan_dosyanin_suresi_kapandigi_gun_biter():
    """AV-2'nin tahsilat gelmeyen 10 dosyası 01.01.2026'da kapandı (koşul kaybı): pencerede bu
    dosyaların süresi 43 gündür (20.11.2025–01.01.2026, kapanış günü dahil). Arşiv öncesi
    kapanmış (günü bilinmeyen) dosyanın süresi son tahsilatında biter, hiç tahsilatı yoksa dosya
    sayılmaz."""
    kapali = ["D-{:05d}".format(110 + s) for s in range(10)]
    kapanis = pd.Series(pd.Timestamp("2026-01-01"), index=kapali)
    avukat, _, _ = _hesapla(_guncellik_parcalari(), kapanis=kapanis)
    maruz_2 = 10 + 10 * 43 / 365.0  # beklenti diğer avukatın hızından
    assert abs(avukat.loc["AV-2", "guncellik_e"] - maruz_2 * 8 / 20.0) < 1e-9
    assert abs(avukat.loc["AV-1", "guncellik_e"] - 20 * 2 / maruz_2) < 1e-9
    bilinmeyen, _, _ = _hesapla(_guncellik_parcalari(),
                                kapanis=pd.Series(pd.NaT, index=kapali, dtype="datetime64[ns]"))
    # AV-2'nin tahsilatsız 10 dosyası sayılmaz: maruziyeti 10, hızı 2 ÷ 10.
    assert abs(bilinmeyen.loc["AV-2", "guncellik_e"] - 10 * 8 / 20.0) < 1e-9
    assert abs(bilinmeyen.loc["AV-1", "guncellik_e"] - 20 * 2 / 10.0) < 1e-9
    hepsi_acik, _, _ = _hesapla(_guncellik_parcalari())
    assert list(hepsi_acik["puan_guncellik"]) == [100.0, 58.33]
    # Kesitten sonraki kapanış günü kesitte bilinmez: dosya kesitte açık sayılır.
    sonra, _, _ = _hesapla(_guncellik_parcalari(),
                           kapanis=pd.Series(pd.Timestamp("2026-12-01"), index=kapali))
    assert abs(sonra.loc["AV-2", "guncellik_e"] - hepsi_acik.loc["AV-2", "guncellik_e"]) < 1e-12


def test_guncellikte_maruziyet_pencerede_elde_tutulan_suredir():
    """AV-2 dosyaları 08.09.2026'da aldı: pencerenin 73 günü (0,2 yıl). Aynı hızda (dosya-yıl
    başına 0,5) tahsilat yapan iki avukat 75 alır; kısa tutmak tek başına avantaj değildir."""
    parcalar = [_parca("AV-1", 20, 0, {s: [(PENCEREDE, 50.0)] for s in range(10)}, **ESKI),
                _parca("AV-2", 20, 100, {s: [("2026-10-01", 50.0)] for s in range(2)},
                       verilis="2018-01-01", atama="2026-09-08")]
    avukat, _, _ = _hesapla(parcalar)
    assert abs(avukat.loc["AV-2", "guncellik_e"] - 2.0) < 1e-9
    assert list(avukat["puan_guncellik"]) == [75.0, 75.0]
    iyi, _, _ = _hesapla([parcalar[0], _parca("AV-2", 20, 100, {s: [("2026-10-01", 50.0)]
                                                                 for s in range(6)},
                                              verilis="2018-01-01", atama="2026-09-08")])
    # Beklenti diğer avukatın hızından: AV-1 için 6 ÷ 4 dosya-yıl, AV-2 için 10 ÷ 20.
    beklenen = [_yuvarla(75 + 50 * ((o + 10) / (e + 10) - 1))
                for o, e in ((10, 20 * 6 / 4.0), (6, 4 * 10 / 20.0))]
    assert list(iyi["puan_guncellik"]) == beklenen and beklenen[0] < 75 < beklenen[1]


def test_guncellik_penceresi_rucuya_verilisten_baslar():
    """AV-2'nin dosyaları 20.05.2026'da rücuya verildi ama atama kaydı 01.03.2026 (verilişten
    önce): pencerede dosya ancak verilişten sonra tahsil edilebilir, maruziyet 184 gündür. İki
    avukatın dosyaları da bir yaşından küçük (aynı yaş bandı); AV-1'inki 354 gün."""
    parcalar = [_parca("AV-1", 20, 0, {s: [(PENCEREDE, 50.0)] for s in range(5)},
                       verilis="2025-12-01", atama="2025-12-01"),
                _parca("AV-2", 20, 100, {s: [("2026-09-01", 50.0)] for s in range(5)},
                       verilis="2026-05-20", atama="2026-03-01")]
    avukat, _, _ = _hesapla(parcalar)
    maruz_1, maruz_2 = 20 * 354 / 365.0, 20 * 184 / 365.0  # beklenti diğer avukatın hızından
    assert abs(avukat.loc["AV-1", "guncellik_e"] - maruz_1 * 5 / maruz_2) < 1e-9
    assert abs(avukat.loc["AV-2", "guncellik_e"] - maruz_2 * 5 / maruz_1) < 1e-9


def test_kapanis_gunleri_kesitte_bilinenler():
    gozlem_tablosu = pd.DataFrame({
        "anahtar": ["D-1", "D-2", "D-3"], "dayanak": ["KAYNAK_TARIHI", "ARSIV_ONCESI",
                                                     "KAYNAK_TARIHI"],
        "ilk_gorulme": pd.to_datetime(["2026-10-03", "2025-01-10", "2026-12-02"]),
        "ilk_tarih": [pd.Timestamp("2026-10-01"), pd.NaT, pd.Timestamp("2026-12-01")]})
    # D-2 arşiv öncesi (günü bilinmiyor, kesitte zaten kapalı); D-3 kesitten sonra kapandı.
    kapanis = gozlem.kapanislar(gozlem_tablosu, KESIT)
    assert list(kapanis.index) == ["D-1", "D-2"] and kapanis["D-1"] == pd.Timestamp("2026-10-01")
    assert pd.isna(kapanis["D-2"])
    assert list(gozlem.kapanislar(gozlem_tablosu, "2026-12-01").index) == ["D-1", "D-2", "D-3"]
    assert gozlem.kapanislar(None, KESIT).empty


def test_olay_araligi_ve_ay_neti():
    dosya = pd.DataFrame({"dosya_no": ["D-1", "D-2", "D-3", "D-4"],
                          "rucuya_verilis_tarihi": pd.Timestamp("2025-01-01"),
                          "alt": pd.Timestamp("2025-11-20"), "ust": pd.Timestamp("2026-11-20")})
    hareket = pd.DataFrame([("AV-1", "D-1", "2025-11-19", 10.0),
                            ("AV-1", "D-2", "2025-11-20", 10.0),
                            ("AV-1", "D-3", "2026-01-01", 10.0),
                            ("AV-1", "D-3", "2026-01-05", -10.0),
                            (None, "D-4", "2026-01-01", 10.0)],
                           columns=["avukat_kodu", "dosya_no", "hareket_tarihi", "tutar"])
    hareket["hareket_tarihi"] = pd.to_datetime(hareket["hareket_tarihi"])
    olay = tahsilat_maruz.olaylar(hareket, dosya, params_yukle()["tahsilat"])
    # Aralık başından önceki gün dışarıda; ay neti sıfır ve avukata yazılamayan olay değildir.
    assert list(olay["dosya_no"]) == ["D-2"] and list(olay["yas_bandi"]) == [0]


def test_tahsilat_puani_yuvarlanmis_bilesenlerin_agirlikli_toplami():
    parcalar = [_parca("AV-1", 30, 0, {s: [(ONCE, 130.0)] for s in range(21)}),
                _parca("AV-1", 5, 50, {s: [(PENCEREDE, 70.0)] for s in range(4)}),
                _parca("AV-2", 40, 100, {s: [(ONCE, 90.0)] for s in range(17)})]
    avukat, _, _ = _hesapla(parcalar)
    for s in avukat.itertuples():
        beklenen = _yuvarla(float(Decimal("0.6") * Decimal(repr(s.puan_tutar))
                                  + Decimal("0.2") * Decimal(repr(s.puan_siklik))
                                  + Decimal("0.2") * Decimal(repr(s.puan_guncellik))))
        assert s.puan == beklenen and s.puan != s.puan_tutar
    yalniz_tutar, _, _ = _hesapla(parcalar, _params(
        bilesen_agirliklari={"tutar": 1.0, "siklik": 0.0, "guncellik": 0.0}))
    assert list(yalniz_tutar["puan"]) == list(yalniz_tutar["puan_tutar"])
    assert list(yalniz_tutar["puan_tutar"]) == list(avukat["puan_tutar"])


def test_olay_puani_az_veride_beklenen_duzeye_yaklasir():
    tah = params_yukle()["tahsilat"]
    assert tahsilat_puan.olay_puani(0, 0, tah) == (1.0, 75.0)
    az = tahsilat_puan.olay_puani(2, 1, tah)[1]    # gözlenen beklenenin iki katı, az veri
    cok = tahsilat_puan.olay_puani(200, 100, tah)[1]
    assert 75 < az < 80 < cok == 100.0
    assert tahsilat_puan.olay_puani(0, 1000, tah)[1] < 26


def test_yeterli_veri_esiginin_altinda_bilesen_puanlari_uretilir_uyari_isaretlenir():
    """9 olgun dosya: üç bileşen ve tahsilat puanı üretilir, durum geçerli, yeterli yanlış."""
    avukat, _, brans = _hesapla([_parca("AV-1", 9, 0, {0: [(ONCE, 10.0)]}),
                                 _parca("AV-2", 25, 100, {0: [(ONCE, 10.0)]})])
    az = avukat.loc["AV-1"]
    assert pd.isna(az["eksik_nedeni"]) and az["durum"] == "GECERLI" and not bool(az["yeterli"])
    assert pd.notna(az[["puan", "puan_tutar", "puan_siklik", "puan_guncellik"]]).all()
    assert az["siklik_o"] == 1.0 and not bool(brans.loc[("AV-1", "TRAFIK"), "yeterli"])
    assert bool(avukat.loc["AV-2", "yeterli"]) and bool(brans.loc[("AV-2", "TRAFIK"), "yeterli"])


def test_brans_puani_o_bransin_dosyalariyla_ve_gostergeler():
    """AV-1: trafikte 25 dosya (oran 0,024), kaskoda 5 dosya (0,03); AV-2 trafikte 25 dosya
    (0,02). AV-1'in trafik beklentisi AV-2'nin oranı (0,02); kaskoda başka avukat olmadığından
    bütün diğer avukatların oranı (0,02). Kaskoda 5 dosya yeterli veri eşiğinin altında: branş
    puanı yine üretilir, yeterli yanlış."""
    def dosyalar(avukat, adet, ilk_no, brans, oran):
        return _parca(avukat, adet, ilk_no, {s: [(ONCE, 1000.0 * oran)] for s in range(adet)},
                      brans=brans)
    avukat, _, brans = _hesapla([dosyalar("AV-1", 25, 0, "TRAFIK", 0.024),
                                 dosyalar("AV-1", 5, 50, "KASKO", 0.03),
                                 dosyalar("AV-2", 25, 100, "TRAFIK", 0.02)])
    trafik = brans.loc[("AV-1", "TRAFIK")]
    assert abs(trafik["tahsilat_orani"] - 0.024) < 1e-12
    assert abs(trafik["beklenen_oran"] - 0.02) < 1e-12 and abs(trafik["dosya_basina"] - 24.0) < 1e-9
    # R = (25 × 1,2 + 10) ÷ 35 = 1,1429 → 82,14; sıklık ve güncellik 75 → 79,28
    assert trafik["puan_tutar"] == 82.14 and trafik["puan"] == 79.28 and bool(trafik["yeterli"])
    kasko = brans.loc[("AV-1", "KASKO")]
    assert not bool(kasko["yeterli"]) and pd.notna(kasko["puan"]) and kasko["n"] == 5.0
    # R = (5 × 0,03/0,02 + 10) ÷ 15 = 1,1667 → 83,33; sıklık ve güncellik 75.
    assert kasko["puan_tutar"] == 83.33
    # Avukatın puanı bütün dosyalarından: n = 30, G = 600 + 150 = 750, B = 500 + 100 = 600.
    assert avukat.loc["AV-1", "puan_tutar"] == _yuvarla(75 + 50 * ((30 * 1.25 + 10) / 40.0 - 1))
    assert avukat.loc["AV-1", "puan"] != trafik["puan"]


def test_girdideki_fazla_sutunlar_hesabi_degistirmez():
    """Kaynak tablolar başka sütunlar da taşıyabilir (rapordaki avukat kodu, branş, açık
    bakiye...). Hesap yalnız kendi sütunlarını alır; sonuç fazla sütunlarla aynıdır."""
    parcalar = [_parca("AV-1", 25, 0, {s: [("2025-03-01", 100.0)] for s in range(10)}),
                _parca("AV-2", 25, 100, {s: [("2025-03-01", 100.0)] for s in range(5)})]
    dosya, atamalar, hareket = [], [], []
    for d, a, h in parcalar:
        dosya, atamalar, hareket = dosya + d, atamalar + a, hareket + h
    dosya = pd.DataFrame(dosya, columns=SUTUN)
    hareket = pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"])
    taban = tahsilat.hesapla(dosya, atama_tablosu(atamalar), hareket, KESIT, params_yukle())[0]
    for ek_dosya, ek_hareket in (
            (dosya.assign(avukat_kodu="AV-X", yas_bandi=9, alt="2000-01-01", acik_bakiye=1.0),
             hareket),
            (dosya, hareket.assign(avukat_kodu="AV-X", brans="KASKO", hareket_turu="T"))):
        sonuc = tahsilat.hesapla(ek_dosya, atama_tablosu(atamalar), ek_hareket, KESIT,
                                 params_yukle())[0]
        pd.testing.assert_frame_equal(sonuc, taban)


def test_dosyayi_kapatan_tahsilat_kapanis_gununde_sayilir():
    """Gözlem kapanış gününü bakiyenin sıfırlandığı gün olarak verir; dosyayı kapatan tahsilat da
    o gün gelir. AV-KAPATAN 30 dosyasını 10.03.2026'da tam tahsil edip kapatır: 30 dosya-ay olayı
    sayılır (önceden kapanış günü aralık dışında kaldığı için 0 sayılıyordu)."""
    parcalar = [_parca("AV-KAPATAN", 30, 0, {s: [("2026-03-10", 1000.0)] for s in range(30)},
                       atama="2025-12-01"),
                _parca("AV-ACIK", 30, 100, {s: [("2026-03-10", 300.0)] for s in range(30)},
                       atama="2025-12-01")]
    kapanis = pd.Series(pd.Timestamp("2026-03-10"), index=["D-{:05d}".format(s) for s in range(30)])
    avukat, _, _ = _hesapla(parcalar, kapanis=kapanis)
    assert list(avukat["siklik_o"]) == [30.0, 30.0] and list(avukat["guncellik_o"]) == [30.0, 30.0]
    assert avukat.loc["AV-KAPATAN", "puan_siklik"] > avukat.loc["AV-ACIK", "puan_siklik"]


def test_bos_atama_donemi_satir_sirasindan_bagimsiz():
    """Aynı gün başlayıp biten (boş) dönem hiçbir gün tutulmaz; satır sırası sonucu değiştirmez
    (önceden boş dönem sonra gelince 'öncekiyle çakışıyor' hatası veriyordu)."""
    dosya = pd.DataFrame([("D-1", "TRAFIK", 1000.0, "2022-01-01")], columns=SUTUN)
    hareket = pd.DataFrame([("D-1", "2025-03-01", 100.0)],
                           columns=["dosya_no", "hareket_tarihi", "tutar"])
    bos = ("D-1", "AV-A", "TRAFIK", "2023-01-01", "2023-01-01", "IADE", "NORMAL")
    dolu = ("D-1", "AV-B", "TRAFIK", "2023-01-01", None, None, "NORMAL")
    sonuclar = [tahsilat.hesapla(dosya, atama_tablosu(sira), hareket, KESIT, params_yukle())[0]
                for sira in ([bos, dolu], [dolu, bos])]
    pd.testing.assert_frame_equal(sonuclar[0], sonuclar[1])
    assert list(sonuclar[0]["avukat_kodu"]) == ["AV-B"]


def test_sifir_tl_hareket_olayin_yas_bandini_degistirmez():
    """Aynı ayda gerçek tahsilattan önce gelen 0 TL kaydı olayı başka yaş bandına taşıyıp grup
    hızlarını ve başka avukatın puanını değiştiriyordu (bant ayın en erken hareketinden
    alınıyordu). Bant ayın ilk pozitif tahsilatındandır; 0 TL kayıtları puanı değiştirmez."""
    parcalar = [_parca("AV-A", 30, 0, {s: [("2026-03-20", 300.0)] for s in range(15)},
                       verilis="2023-03-15", atama="2024-04-01"),
                _parca("AV-B", 30, 100, {s: [("2026-01-10", 300.0)] for s in range(15)},
                       verilis="2024-03-15", atama="2024-04-01")]
    once, _, _ = _hesapla(parcalar)
    sifir = [([], [], [("D-{:05d}".format(s), "2026-03-02", 0.0) for s in range(15)])]
    sonra, _, _ = _hesapla(parcalar + sifir)
    pd.testing.assert_frame_equal(once, sonra)


def _dosyalar(avukat, adet, ilk_no, oran, brans="TRAFIK", rucu=1000.0, tarih=ONCE):
    return _parca(avukat, adet, ilk_no, {s: [(tarih, rucu * oran)] for s in range(adet)},
                  brans=brans, rucu=rucu)


def test_fazla_tahsilat_puani_dusurmez():
    """Avukatın kendi tahsilatı kendi beklentisine girmez. AV-A nakliyatta yalnız; oraya eklenen
    tahsilat önceden beklentisini de aynı oranda artırıp puanını düşürüyordu (87,86 → 78,67)."""
    sonuclar = []
    for ek in (0.0, 100.0, 500.0):
        nakliyat = _parca("AV-A", 30, 200, {s: [("2025-07-10", ek)] for s in range(30)} if ek
                          else {}, brans="NAKLIYAT")
        avukat, _, _ = _hesapla([_dosyalar("AV-A", 30, 0, 0.3), _dosyalar("AV-B", 30, 100, 0.1),
                                 nakliyat])
        sonuclar.append(avukat)
    for ad in ("puan_tutar", "puan_siklik", "puan_guncellik", "puan"):
        dizi = [a.loc["AV-A", ad] for a in sonuclar]
        assert dizi == sorted(dizi), (ad, dizi)
    assert len({a.loc["AV-B", "puan"] for a in sonuclar}) == 1  # öteki avukat etkilenmez


def test_tek_avukatli_grupta_once_brans_sonra_butun_diger_avukatlar():
    """AV-1 küçük tutar bandında yalnız: beklentisi aynı branştaki diğer avukatın (AV-2) oranından.
    AV-3 kaskoda yalnız: branşta da başka avukat yok, bütün diğer avukatların oranından."""
    avukat, _, _ = _hesapla([_dosyalar("AV-1", 20, 0, 0.3, rucu=10000.0),
                             _dosyalar("AV-2", 20, 100, 0.1, rucu=200000.0),
                             _dosyalar("AV-3", 20, 200, 0.5, brans="KASKO", rucu=10000.0)])
    assert abs(avukat.loc["AV-1", "beklenen"] - 200000.0 * 0.1) < 1e-6
    diger = (20 * 10000.0 * 0.3 + 20 * 200000.0 * 0.1) / (20 * 10000.0 + 20 * 200000.0)
    assert abs(avukat.loc["AV-3", "beklenen"] - 200000.0 * diger) < 1e-6


def test_digerlerinin_net_tahsilati_eksiyse_beklenen_sifir():
    """Diğer avukatın grupta yalnız ters kaydı var (net eksi): ölçüt yok, üst katmanlara geçilir;
    başka avukat olmadığı için hepsinde ölçüt yok, beklenti eksiye dönmez, sıfırdır."""
    avukat, _, _ = _hesapla([_dosyalar("AV-1", 25, 0, 0.3), _dosyalar("AV-2", 25, 100, -0.1)])
    assert avukat.loc["AV-1", "beklenen"] == 0.0
    assert avukat.loc["AV-1", "eksik_nedeni"] == "BEKLENEN_SIFIR"


def test_grup_tablosu_oran_ve_siklik_hizi_grubun_kendi_toplamlarindan():
    """Ekrandaki grup tablosu: oran ve sıklık hızı her grubun kendi toplamıdır. Trafikte 30
    dosyanın 10'unda, kaskoda 20 dosyanın 4'ünde bir tahsilat ayı var; elde tutma süresi aynı,
    hızların oranı (10/30) ÷ (4/20). Kaskoda bir dosyada yalnız ters kayıt: net eksi, oran 0."""
    trafik = _parca("AV-A", 30, 0, {s: [("2025-06-10", 100.0)] for s in range(10)}, **ESKI)
    kasko_odeme = {s: [("2025-06-10", 100.0)] for s in range(4)}
    kasko_odeme[4] = [("2025-07-10", -500.0)]
    kasko = _parca("AV-B", 20, 100, kasko_odeme, brans="KASKO", **ESKI)
    _, grup, _ = _hesapla([trafik, kasko])
    grup = grup.set_index("brans")
    assert abs(grup.loc["TRAFIK", "oran"] - 1000.0 / 30000.0) < 1e-12
    assert grup.loc["KASKO", "atfedilen"] == -100.0 and grup.loc["KASKO", "oran"] == 0.0
    hiz = grup.loc["TRAFIK", "siklik_hizi"] / grup.loc["KASKO", "siklik_hizi"]
    assert abs(hiz - (10 / 30) / (4 / 20)) < 1e-9
