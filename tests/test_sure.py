"""Süre puanı ve süre özeti testleri. Kesit 2026-11-19; pencere (2025-11-19, 2026-11-19]."""
import pandas as pd

from avukat_perf import sure_ozet, sure_puani
from yardimci import params_yukle

KESIT = "2026-11-19"
GIRDI = list(sure_puani.GIRDI)


def _tablo(satirlar, dosya_basina=1):
    """Dosya numarası olmayan dönem satırlarından girdi; her dosyada dosya_basina dönem."""
    tablo = pd.DataFrame(satirlar, columns=[ad for ad in GIRDI if ad != "dosya_no"])
    return tablo.assign(dosya_no=["D-{}".format(sira // dosya_basina)
                                  for sira in range(len(tablo))])[GIRDI]


def _params(golge=False, en_az_beklenen=5):
    params = params_yukle()
    params["uyari"]["golge_mod"] = golge
    params["sure_puani"]["en_az_beklenen"] = en_az_beklenen  # taban mekanizması da sınanır
    return params


def _donemler(avukat, adet, dusum, brans="TRAFIK", esik="2026-06-01"):
    """adet dönem; ilk 'dusum' tanesi düşüm almış, kalanı süresinde kapanmış."""
    return [(avukat, "K1", "ILK_ISLEM", brans, "TURUNCU" if sira < dusum else "KAPANDI",
             sira < dusum, esik) for sira in range(adet)]


def _kapsam(**oranlar):
    return pd.DataFrame(list(oranlar.items()), columns=["avukat_kodu", "kapsam"])


def test_puan_formulu_kontrol_degerleri():
    sp = params_yukle()["sure_puani"]
    assert sure_puani.puan_hesapla(0, 0, sp)[1] == 75.0
    assert abs(sure_puani.puan_hesapla(2, 0, sp)[1] - 65.0) < 1e-9
    assert round(sure_puani.puan_hesapla(1, 0.2, sp)[1], 1) == 71.1
    assert sure_puani.puan_hesapla(0, 10, sp) == (0.5, 100.0)
    assert sure_puani.puan_hesapla(40, 10, sp) == (2.5, 0.0)
    assert sure_puani.puan_hesapla(60, 10, sp)[1] == 0.0


def test_risk_altindaki_donemler():
    satirlar = _donemler("AV-1", 2, 1) + [
        ("AV-1", "K1", "ILK_ISLEM", "TRAFIK", "SONLANDI", False, "2026-06-01"),
        ("AV-1", "K1", "ILK_ISLEM", "TRAFIK", "KAPANDI", False, "2025-11-19"),
        ("AV-1", "K1", "ILK_ISLEM", "TRAFIK", "KAPANDI", False, "2025-11-20"),
        ("AV-1", "K1", "ILK_ISLEM", "TRAFIK", "KAPANDI", False, "2026-11-20"),
        ("AV-1", "K1", "ILK_ISLEM", "TRAFIK", "KAPSAM_DISI", False, None)]
    risk = sure_puani.risk_altindaki(_tablo(satirlar), KESIT, 12)
    assert len(risk) == 3 and int(risk["dusum"].sum()) == 1


def test_beklenen_diger_avukatlarin_oranindan_puan():
    """E: avukatın her risk dönemi için aynı gruptaki DİĞER avukatların düşüm oranı. AV-1'in 40
    dönemi × AV-2'nin oranı (12/40) = 12; AV-2'nin 40 dönemi × AV-1'in oranı (4/40) = 4."""
    satirlar = _donemler("AV-1", 40, 4) + _donemler("AV-2", 40, 12)
    sonuc = sure_puani.puanla(_tablo(satirlar), _kapsam(**{"AV-1": 1.0, "AV-2": 0.9}), KESIT,
                              _params(en_az_beklenen=0))
    sonuc = sonuc.set_index("avukat_kodu")
    assert list(sonuc["o"]) == [4, 12] and list(sonuc["e"].round(9)) == [12.0, 4.0]
    assert abs(sonuc.loc["AV-1", "puan"] - (75 + 50 * (1 - 14 / 22))) < 1e-9
    assert abs(sonuc.loc["AV-2", "puan"] - (75 + 50 * (1 - 22 / 14))) < 1e-9
    assert set(sonuc["durum"]) == {"GECERLI"}


def test_grup_brans_ve_surece_gore_ayrilir():
    satirlar = (_donemler("AV-1", 40, 20, "YANGIN") + _donemler("AV-3", 40, 20, "YANGIN")
                + _donemler("AV-2", 40, 8, "TRAFIK") + _donemler("AV-4", 40, 8, "TRAFIK"))
    kapsam = _kapsam(**{"AV-1": 1.0, "AV-2": 1.0, "AV-3": 1.0, "AV-4": 1.0})
    sonuc = sure_puani.puanla(_tablo(satirlar), kapsam, KESIT, _params())
    assert all(abs(puan - 75.0) < 1e-9 for puan in sonuc["puan"])


def test_tek_avukatli_grupta_once_kriter_ve_surec_sonra_butun_digerleri():
    """Grupta başka avukat yoksa aynı kriter ve süreçteki diğer avukatlar, onlar da yoksa
    bütün diğer avukatlar ölçüttür. Önceden tek avukatlı grupta E = O olur, avukat bütün
    dönemlerinde gecikse de 75 alırdı."""
    satirlar = (_donemler("AV-1", 40, 40, "HIRSIZLIK") + _donemler("AV-2", 40, 4, "TRAFIK")
                + [("AV-3", "K2", "ITIRAZ", "TRAFIK", "KAPANDI", False, "2026-06-01")] * 40)
    kapsam = _kapsam(**{"AV-1": 1.0, "AV-2": 1.0, "AV-3": 1.0})
    sonuc = sure_puani.puanla(_tablo(satirlar), kapsam, KESIT,
                              _params(en_az_beklenen=0)).set_index("avukat_kodu")
    # AV-1: aynı kriter ve süreçte (K1) AV-2'nin oranı 4/40; AV-3 (K2) yalnız: bütün diğerleri
    # (40 + 4) ÷ 80.
    assert sonuc["e"].round(9).to_dict() == {"AV-1": 4.0, "AV-2": 40.0, "AV-3": 22.0}
    assert sonuc.loc["AV-1", "puan"] < 75.0 and sonuc.loc["AV-2", "puan"] > 75.0


def test_yayin_tabani_ve_golge_mod():
    """AV-1: 29 dönem 9 dosyada (yeterli veri eşiği 10'un altında; puan geçerli). AV-2 ve AV-5:
    kaskoda diğerinin düşümü az, E < 5. AV-3: kapsam %79. AV-4: pencerede ölçülen Kriter 1 dönemi
    yok
    (kapsam satırı yok): tarihi bilinmeyen esas da yoktur, kapsam 1 (önceden KAPSAM_BILINMIYOR
    ile süre ve birleşik puan yayımlanmıyordu)."""
    satirlar = (_donemler("AV-1", 29, 10) + _donemler("AV-2", 40, 2, "KASKO")
                + _donemler("AV-5", 40, 0, "KASKO") + _donemler("AV-3", 40, 20, "YANGIN")
                + _donemler("AV-4", 40, 20, "NAKLIYAT"))
    tablo = _tablo(satirlar)
    av1 = tablo["avukat_kodu"] == "AV-1"
    tablo.loc[av1, "dosya_no"] = ["D-AV1-{}".format(sira % 9) for sira in range(int(av1.sum()))]
    kapsam = _kapsam(**{"AV-1": 1.0, "AV-2": 1.0, "AV-5": 1.0, "AV-3": 0.79})
    sonuc = sure_puani.puanla(tablo, kapsam, KESIT, _params()).set_index("avukat_kodu")
    assert sonuc["eksik_nedeni"].to_dict() == {
        "AV-1": None, "AV-2": "AZ_BEKLENEN", "AV-3": "KAPSAM_DUSUK", "AV-4": None,
        "AV-5": "AZ_BEKLENEN"}
    assert sonuc.loc["AV-4", "kapsam"] == 1.0 and sonuc.loc["AV-4", "durum"] == "GECERLI"
    assert sonuc.loc["AV-1", "durum"] == "GECERLI" and not sonuc.loc["AV-1", "yeterli"]
    assert pd.notna(sonuc.loc["AV-1", "puan"]) and sonuc.loc["AV-4", "yeterli"]
    assert sonuc.loc[["AV-2", "AV-3", "AV-5"], "puan"].isna().all()
    golge = sure_puani.puanla(tablo, kapsam, KESIT, _params(golge=True))
    assert set(golge["durum"]) == {"GOLGE_MOD"} and golge["r"].notna().all()


def test_kapsam_esas_tarihi_bilinenlerin_orani():
    k1 = pd.DataFrame({
        "avukat_kodu": ["AV-1"] * 4 + ["AV-2"],
        "atama_tarihi": ["2026-01-01"] * 4 + ["2025-01-01"],
        "kapsam_disi_nedeni": [None, None, "ESAS_TARIHI_BILINMIYOR", "SULH", None]})
    kapsam = sure_puani.kapsam_hesapla(k1, KESIT, 12)
    assert kapsam.to_dict("records") == [{"avukat_kodu": "AV-1", "kapsam": 2 / 3}]


def _ozet_girdisi():
    sutunlar = list(sure_ozet.GIRDI)
    satirlar = [
        ("AV-1", "K1", "D-1", "2026-11-01", "IZLENIYOR", False, None, 18, "2026-11-19",
         "2026-11-11", "2026-11-21"),
        ("AV-1", "K1", "D-2", "2026-09-01", "KIRMIZI", True, "2026-09-21", 79, "2026-11-19",
         "2026-09-11", "2026-09-21"),
        ("AV-1", "K1", "D-3", "2026-10-01", "SARI", False, None, 49, "2026-11-19",
         "2026-10-11", "2026-10-21"),
        ("AV-1", "K1", "D-4", "2026-01-01", "KAPANDI", False, None, 6, "2026-01-07",
         "2026-01-11", "2026-01-21"),
        ("AV-1", "K1", "D-5", "2026-02-01", "KAPANDI", True, "2026-02-21", 30, "2026-03-03",
         "2026-02-11", "2026-02-21"),
        ("AV-1", "K1", "D-6", "2024-01-01", "KAPANDI", True, "2024-01-21", 40, "2024-02-10",
         "2024-01-11", "2024-01-21"),
        ("AV-2", "K2", "D-7", "2026-01-01", "TURUNCU", True, "2026-07-01", 150, "2026-11-19",
         "2026-04-01", "2026-07-01")]
    return pd.DataFrame(satirlar, columns=sutunlar)


def test_sure_ozeti():
    ozet = sure_ozet.ozet(_ozet_girdisi(), KESIT, 12).set_index(["avukat_kodu", "kriter"])
    av1 = ozet.loc[("AV-1", "K1")]
    assert (av1["izleniyor"], av1["acik_sari"], av1["acik_kirmizi"]) == (1, 1, 1)
    assert av1["kapanan"] == 2 and av1["ort_sure_gun"] == 18.0
    assert av1["dusum_sayisi"] == 2
    assert ozet.loc[("AV-2", "K2"), "acik_turuncu"] == 1


def test_eposta_listesi_sirasi_ve_golge_mod():
    liste = sure_ozet.eposta_listesi(_ozet_girdisi(), _params(golge=True))
    assert list(liste["dosya_no"]) == ["D-2", "D-3", "D-7"]
    assert not liste["gonderilecek"].any()
    assert sure_ozet.eposta_listesi(_ozet_girdisi(), _params())["gonderilecek"].all()


def test_yayin_tabani_dosya_sayisiyla_sinanir():
    """18 risk dönemi ama 9 farklı dosya (her dosyada K1 ve K2): 'en az 10 dosya' yeterli veri
    eşiği dönemle değil dosyayla sınanır; altında puan geçerlidir, yeterli işareti yanlıştır."""
    tablo = _tablo(_donemler("AV-1", 18, 3), dosya_basina=2)
    sonuc = sure_puani.puanla(tablo, _kapsam(**{"AV-1": 1.0}), KESIT,
                              _params(en_az_beklenen=0)).iloc[0]
    assert sonuc["risk_donemi"] == 18 and sonuc["risk_dosya"] == 9
    assert sonuc["durum"] == "GECERLI" and pd.notna(sonuc["puan"]) and not sonuc["yeterli"]


def test_varsayilanda_kimse_gecikmezse_herkes_75_ve_yayimlanir():
    """Puan göreli: herkes zamanında işlem yapınca beklenen düşüm 0'dır. Varsayılan taban (0)
    puanı engellemez, herkes 75 alır; önceki taban 5 süre ve birleşik puanı hiç çıkarmıyordu."""
    satirlar = _donemler("AV-1", 40, 0) + _donemler("AV-2", 40, 0)
    kapsam = _kapsam(**{"AV-1": 1.0, "AV-2": 1.0})
    sonuc = sure_puani.puanla(_tablo(satirlar), kapsam, KESIT, _params(en_az_beklenen=0))
    assert list(sonuc["puan"]) == [75.0, 75.0] and set(sonuc["durum"]) == {"GECERLI"}
    varsayilan = params_yukle()["sure_puani"]["en_az_beklenen"]
    assert varsayilan == 0
