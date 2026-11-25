"""Kriter 1 ve Kriter 2 sınır günleri: koşul görüntüsünde rücu kodunun değişmesi, esas ve
davanın atama günü ya da bitiş günü girilmesi, Kriter 2'de KIRMIZI günü, kesit günü atama.

Tarihler sabittir; sonuç makinenin saat dilimine ve bugünün tarihine bağlı değildir.
"""
import pandas as pd

from avukat_perf import atama, gozlem, hazirlik, kriter1, kriter2, olay
from yardimci import atama_tablosu, esas_tablosu, params_yukle

SUREC_SUTUNLARI = list(kriter2.SUREC_SUTUNLARI)
K2 = params_yukle()["kriter2"]


def _g(metin):
    return pd.Timestamp(metin)


def _surec(dosya, baslangic, dava=None, kayip=None, kod="R11", bakiye=1000.0):
    return (dosya, "TRAFIK", "ITIRAZ", baslangic, dava, kayip, kod, bakiye)


def _k2(atamalar, surecler, kesit, params=None):
    tablo = pd.DataFrame(surecler, columns=SUREC_SUTUNLARI)
    return kriter2.degerlendir(atama_tablosu(atamalar), tablo, kesit, params or params_yukle())


def _k2_tek(surec, kesit, atama_tarihi="2025-12-01"):
    return _k2([(surec[0], "AV-01", "TRAFIK", atama_tarihi)], [surec], kesit).iloc[0]


def _k1(atamalar, esaslar, kesit="2026-11-19", params=None):
    return kriter1.degerlendir(atama_tablosu(atamalar), esas_tablosu(esaslar), None, kesit,
                               params or params_yukle())


def _dosya(kod, bakiye):
    return pd.DataFrame({"dosya_no": ["D-001"], "brans": ["TRAFIK"], "rucu_kodu": [kod],
                         "acik_bakiye": [bakiye]})


def _kosul_gozlemi(degisim_gecesi, kod_sonra="R06", bakiye=5000.0):
    """2026-08-01'den 2026-09-30'a her gece çekim; degisim_gecesi ve sonrasında rücu kodu
    kod_sonra, öncesinde R11. Açık bakiye hep pozitif."""
    mevcut, onceki = None, None
    for gece in pd.date_range("2026-08-01", "2026-09-30"):
        kod = kod_sonra if gece >= _g(degisim_gecesi) else "R11"
        goruntu = hazirlik.kosul_goruntusu(_dosya(kod, bakiye), K2)
        mevcut = gozlem.guncelle(mevcut, goruntu, "dosya_no", "kosul_kayip", gece, onceki)
        onceki = gece
    return mevcut


def _k2_surec_kosulla(degisim_gecesi):
    # İtiraz 2026-02-15: SARI 05-15, TURUNCU 08-15, KIRMIZI 09-01.
    k2 = pd.DataFrame({"dosya_no": ["D-001"], "surec_turu": ["ITIRAZ"],
                       "baslangic_tarihi": ["2026-02-15"]})
    return hazirlik.k2_surecleri(k2, _dosya("R06", 5000.0), None,
                                 _kosul_gozlemi(degisim_gecesi), None)


# 4) Koşul görüntüsünde rücu kodunun değişmesi (bakiye pozitifken)

def test_kosul_goruntusu_rucu_kodu_degisince_bakiye_pozitifken_kalkar():
    dosya = pd.DataFrame({"dosya_no": ["D-001", "D-002", "D-003", "D-004", "D-005"],
                          "rucu_kodu": ["R06", "R12", "R11", "R11", "R06"],
                          "acik_bakiye": [5000.0, 1.0, 5000.0, None, None]})
    kayip = hazirlik.kosul_goruntusu(dosya, K2).set_index("dosya_no")["kosul_kayip"]
    assert kayip.to_dict() == {"D-001": "EVET", "D-002": "EVET", "D-003": None,
                               "D-004": None, "D-005": "EVET"}


def test_rucu_kodu_degisince_olusmus_k2_dusumu_korunur_sonra_ceza_yok():
    # Rücu kodu R06 ilk kez 2026-08-21 gecesi görüldü: koşul en erken 08-20'de kalktı.
    surec = _k2_surec_kosulla("2026-08-21")
    assert surec["kosul_kayip_tarihi"].iloc[0] == _g("2026-08-20")
    atamalar = atama_tablosu([("D-001", "AV-01", "TRAFIK", "2026-01-05")])
    kayit, seviyeler = None, []
    for kesit in ("2026-08-14", "2026-08-15", "2026-08-20", "2026-09-01", "2026-09-30",
                  "2026-12-31"):
        sonuc = kriter2.degerlendir(atamalar, surec, kesit, params_yukle())
        seviyeler.append(sonuc["seviye"].iloc[0])
        kayit = olay.olay_birlestir(kayit, olay.olaylar(sonuc, "K2"))
    # Kesitten sonraki koşul kaybı bilinmez; kesit günündeki bilinir (dönem o gün kapanır).
    assert seviyeler == ["SARI", "TURUNCU"] + ["KOSUL_DISI"] * 4
    satir = sonuc.iloc[0]
    assert satir["seviye"] == "KOSUL_DISI" and satir["olcum_sonu"] == _g("2026-08-20")
    assert satir["dusum"] and satir["dusum_tarihi"] == _g("2026-08-15")
    assert satir["en_yuksek_seviye"] == "TURUNCU" and pd.isna(satir["kapsam_disi_nedeni"])
    assert list(kayit["seviye"]) == ["SARI", "TURUNCU"]
    assert list(kayit["olay_tarihi"]) == [_g("2026-05-15"), _g("2026-08-15")]
    # Düşümü yalnız iade ve yeniden atamada kaldıran parametre koşul kaybına uygulanmaz.
    params = params_yukle()
    params["kriter2"]["sonlanan_atamada_dusum_korunur"] = False
    assert kriter2.degerlendir(atamalar, surec, "2026-12-31", params)["dusum"].iloc[0]


def test_rucu_kodu_turuncu_gunu_kalkarsa_dusum_var_bir_gun_once_yok():
    # Eşik günü dahildir: koşul 08-15'te (turuncu günü) kalktıysa düşüm oluşmuştur.
    atamalar = atama_tablosu([("D-001", "AV-01", "TRAFIK", "2026-01-05")])
    gunu = kriter2.degerlendir(atamalar, _k2_surec_kosulla("2026-08-16"), "2026-09-30",
                               params_yukle()).iloc[0]
    assert gunu["seviye"] == "KOSUL_DISI" and gunu["dusum"]
    assert gunu["en_yuksek_seviye"] == "TURUNCU" and gunu["olcum_sonu"] == _g("2026-08-15")
    once =kriter2.degerlendir(atamalar, _k2_surec_kosulla("2026-08-15"), "2026-09-30",
                               params_yukle()).iloc[0]
    assert once["seviye"] == "KOSUL_DISI" and not once["dusum"]
    assert once["en_yuksek_seviye"] == "SARI" and once["olcum_sonu"] == _g("2026-08-14")


def test_kosul_kalktiktan_sonra_atanan_avukat_olculmez():
    # Kod R06'da kaldı (kapsam dışı kod); sonraki avukata ceza ve ölçüm yok.
    atamalar = atama_tablosu([
        ("D-001", "AV-01", "TRAFIK", "2026-01-05", "2026-09-10", "YENIDEN_ATAMA"),
        ("D-001", "AV-02", "TRAFIK", "2026-09-10")])
    sonuc = kriter2.degerlendir(atamalar, _k2_surec_kosulla("2026-08-21"), "2026-12-31",
                                params_yukle()).set_index("avukat_kodu")
    assert sonuc.loc["AV-01", "seviye"] == "KOSUL_DISI" and sonuc.loc["AV-01", "dusum"]
    assert sonuc.loc["AV-02", "seviye"] == "KAPSAM_DISI"
    assert sonuc.loc["AV-02", "kapsam_disi_nedeni"] == "KOSUL_SAGLANMIYOR"
    assert not sonuc.loc["AV-02", "dusum"]
    assert list(olay.olaylar(sonuc.reset_index(), "K2")["avukat_kodu"].unique()) == ["AV-01"]


# 9) Esasın atama bitiş günü, davanın atama günü girilmesi

def test_k1_esas_atama_bitis_gunu_girilirse_kapandi_ertesi_gun_sonlandi():
    # AV-01 10-01'de atandı (TRAFIK, turuncu 10-21), 10-25'te dosya AV-02'ye geçti.
    atamalar = [("D-001", "AV-01", "TRAFIK", "2026-10-01", "2026-10-25", "YENIDEN_ATAMA"),
                ("D-001", "AV-02", "TRAFIK", "2026-10-25")]
    gunu = _k1(atamalar, {"D-001": "2026-10-25"}).set_index("avukat_kodu")
    assert gunu.loc["AV-01", "seviye"] == "KAPANDI" and gunu.loc["AV-01", "sure_gun"] == 24
    assert gunu.loc["AV-01", "olcum_sonu"] == _g("2026-10-25") and gunu.loc["AV-01", "dusum"]
    ertesi = _k1(atamalar, {"D-001": "2026-10-26"}).set_index("avukat_kodu")
    assert ertesi.loc["AV-01", "seviye"] == "SONLANDI"
    assert ertesi.loc["AV-01", "olcum_sonu"] == _g("2026-10-25")
    assert ertesi.loc["AV-01", "dusum"] and ertesi.loc["AV-01", "sure_gun"] == 24
    # Sonlanan dönemde düşüm korunmazsa fark puana yansır: bitiş günü girilen esas kapanıştır.
    params = params_yukle()
    params["kriter1"]["sonlanan_atamada_dusum_korunur"] = False
    assert _k1(atamalar, {"D-001": "2026-10-25"}, params=params)["dusum"].iloc[0]
    assert not _k1(atamalar, {"D-001": "2026-10-26"}, params=params)["dusum"].iloc[0]


def test_k1_esas_yeni_atama_gunu_girilirse_yeni_avukat_olculur_bir_gun_once_olculmez():
    atamalar = [("D-001", "AV-01", "TRAFIK", "2026-10-01", "2026-10-25", "YENIDEN_ATAMA"),
                ("D-001", "AV-02", "TRAFIK", "2026-10-25")]
    gunu = _k1(atamalar, {"D-001": "2026-10-25"}).set_index("avukat_kodu")
    assert gunu.loc["AV-02", "seviye"] == "KAPANDI" and gunu.loc["AV-02", "sure_gun"] == 0
    assert not gunu.loc["AV-02", "dusum"] and pd.isna(gunu.loc["AV-02", "en_yuksek_seviye"])
    once = _k1(atamalar, {"D-001": "2026-10-24"}).set_index("avukat_kodu")
    assert once.loc["AV-02", "kapsam_disi_nedeni"] == "ESAS_ONCEDEN_VAR"
    assert once.loc["AV-01", "seviye"] == "KAPANDI" and once.loc["AV-01", "sure_gun"] == 23


def test_k2_dava_atama_gunu_girilirse_kapandi_bir_gun_once_onceden_var():
    surec = _surec("D-001", "2026-01-10", dava="2026-03-01")
    gunu = _k2_tek(surec, "2026-11-19", atama_tarihi="2026-03-01")
    assert gunu["seviye"] == "KAPANDI" and gunu["sure_gun"] == 0 and not gunu["dusum"]
    assert gunu["surec_baslangici"] == _g("2026-03-01")
    once = _k2_tek(surec, "2026-11-19", atama_tarihi="2026-03-02")
    assert once["seviye"] == "KAPSAM_DISI" and once["kapsam_disi_nedeni"] == "DAVA_ONCEDEN_VAR"
    assert not once["dusum"]


def test_k2_tarihi_bilinmeyen_dava_atama_gunu_gorulurse_tarihi_bilinmiyor():
    # Dava esası arşivin ilk gecesinde (2026-01-10) zaten doluydu; tarihi bilinmiyor.
    tablo = pd.DataFrame([_surec("D-00{}".format(sira), "2025-01-10") for sira in (1, 2, 3)],
                         columns=SUREC_SUTUNLARI)
    tablo["dava_gorulme"] = pd.to_datetime(["2026-01-10"] * 3)
    atamalar = atama_tablosu([("D-001", "AV-01", "TRAFIK", "2026-01-09"),
                              ("D-002", "AV-01", "TRAFIK", "2026-01-10"),
                              ("D-003", "AV-01", "TRAFIK", "2026-01-11")])
    sonuc = kriter2.degerlendir(atamalar, tablo, "2026-11-19", params_yukle())
    assert list(sonuc["kapsam_disi_nedeni"]) == [
        "DAVA_TARIHI_BILINMIYOR", "DAVA_TARIHI_BILINMIYOR", "DAVA_ONCEDEN_VAR"]
    assert set(sonuc["seviye"]) == {"KAPSAM_DISI"} and not sonuc["dusum"].any()
    assert olay.olaylar(sonuc, "K2").empty


def test_k2_dava_atama_bitis_gunu_girilirse_kapandi_ertesi_gun_sonlandi():
    # Bitiş adayları aynı günse sıra: dava (KAPANDI), atama bitişi (SONLANDI), koşul kaybı.
    atamalar = [("D-001", "AV-01", "TRAFIK", "2025-12-01", "2026-08-01", "YENIDEN_ATAMA"),
                ("D-001", "AV-02", "TRAFIK", "2026-08-01")]
    gunu = _k2(atamalar, [_surec("D-001", "2026-01-10", dava="2026-08-01",
                                 kayip="2026-08-01", kod="R06")], "2026-11-19")
    gunu = gunu.set_index("avukat_kodu")
    assert gunu.loc["AV-01", "seviye"] == "KAPANDI" and gunu.loc["AV-01", "dusum"]
    assert gunu.loc["AV-01", "en_yuksek_seviye"] == "KIRMIZI"
    assert gunu.loc["AV-02", "seviye"] == "KAPANDI" and gunu.loc["AV-02", "sure_gun"] == 0
    ertesi = _k2(atamalar, [_surec("D-001", "2026-01-10", dava="2026-08-02")], "2026-11-19")
    ertesi = ertesi.set_index("avukat_kodu")
    assert ertesi.loc["AV-01", "seviye"] == "SONLANDI"
    assert ertesi.loc["AV-01", "olcum_sonu"] == _g("2026-08-01")
    assert ertesi.loc["AV-02", "seviye"] == "KAPANDI" and ertesi.loc["AV-02", "sure_gun"] == 1
    # Dava yoksa atama bitişi aynı gün kalkan koşuldan önce gelir.
    kosul = _k2(atamalar, [_surec("D-001", "2026-01-10", kayip="2026-08-01", kod="R06")],
                "2026-11-19").set_index("avukat_kodu")
    assert kosul.loc["AV-01", "seviye"] == "SONLANDI" and kosul.loc["AV-01", "dusum"]
    assert kosul.loc["AV-01", "olcum_sonu"] == _g("2026-08-01")


# 11) Kriter 2'de KIRMIZI: düşüm ayından sonraki takvim ayının ilk günü dosya hâlâ açıksa

def test_k2_kirmizi_dusum_ayindan_sonraki_ayin_ilk_gunu():
    # Başlangıç -> düşüm günü -> KIRMIZI günü (ay sonu, ayın ilk günü ve yıl dönümü).
    vakalar = [("2026-03-31", "2026-09-30", "2026-10-01"),
               ("2026-03-01", "2026-09-01", "2026-10-01"),
               ("2026-06-15", "2026-12-15", "2027-01-01")]
    for baslangic, turuncu, kirmizi in vakalar:
        surec = _surec("D-001", baslangic)
        once = _k2_tek(surec, _g(kirmizi) - pd.Timedelta(days=1))
        gunu = _k2_tek(surec, kirmizi)
        assert once["seviye"] == "TURUNCU" and gunu["seviye"] == "KIRMIZI"
        assert gunu["esik_kirmizi"] == _g(kirmizi) and once["esik_kirmizi"] == _g(kirmizi)
        assert once["dusum"] and gunu["dusum"]
        assert once["dusum_tarihi"] == gunu["dusum_tarihi"] == _g(turuncu)


def test_k2_kirmizi_kapanis_kirmizi_gunundeyse_olusur_bir_gun_once_olusmaz():
    # Düşüm 2026-09-01, KIRMIZI 2026-10-01; dava, koşul kaybı ya da iade o gün ya da bir gün önce.
    for gun, beklenen in (("2026-09-30", "TURUNCU"), ("2026-10-01", "KIRMIZI")):
        dava = _k2_tek(_surec("D-001", "2026-03-01", dava=gun), "2026-11-19")
        kosul = _k2_tek(_surec("D-001", "2026-03-01", kayip=gun, kod="R06"), "2026-11-19")
        iade = _k2([("D-001", "AV-01", "TRAFIK", "2025-12-01", gun, "IADE")],
                   [_surec("D-001", "2026-03-01")], "2026-11-19").iloc[0]
        seviyeler = [dava["seviye"], kosul["seviye"], iade["seviye"]]
        assert seviyeler == ["KAPANDI", "KOSUL_DISI", "SONLANDI"]
        for satir in (dava, kosul, iade):
            assert satir["en_yuksek_seviye"] == beklenen and satir["dusum"]
            assert satir["dusum_tarihi"] == _g("2026-09-01")


def test_k2_kirmizi_yeni_dusum_dogurmaz_olay_tarihleri_esik_gunu():
    atamalar = atama_tablosu([("D-001", "AV-01", "TRAFIK", "2025-12-01")])
    surecler = pd.DataFrame([_surec("D-001", "2026-03-01")], columns=SUREC_SUTUNLARI)
    kayit = None
    for kesit in ("2026-09-01", "2026-09-30", "2026-10-01", "2026-11-19"):
        sonuc = kriter2.degerlendir(atamalar, surecler, kesit, params_yukle())
        assert sonuc["dusum_tarihi"].iloc[0] == _g("2026-09-01")
        kayit = olay.olay_birlestir(kayit, olay.olaylar(sonuc, "K2"))
    assert list(kayit["seviye"]) == ["SARI", "TURUNCU", "KIRMIZI"]
    tarihler = [_g(metin) for metin in ("2026-06-01", "2026-09-01", "2026-10-01")]
    assert list(kayit["olay_tarihi"]) == tarihler


# 12) atama.donemler: kesit günü başlayan atama dahil, ertesi gün hariç

def test_donemler_kesit_gunu_baslayan_atama_dahil_ertesi_gun_haric():
    tablo = atama.donemler(atama_tablosu([
        ("D-001", "AV-01", "TRAFIK", "2026-11-19"),
        ("D-002", "AV-01", "TRAFIK", "2026-11-20"),
        ("D-003", "AV-02", "TRAFIK", "2026-11-19 23:59:59"),
        ("D-004", "AV-02", "TRAFIK", "2026-11-20 00:00:00"),
        ("D-005", "AV-03", "TRAFIK", "2026-01-01", "2026-11-19", "IADE"),
        ("D-006", "AV-03", "TRAFIK", "2026-01-01", "2026-11-20", "IADE")]), "2026-11-19")
    tablo = tablo.set_index("dosya_no")
    assert list(tablo.index) == ["D-001", "D-003", "D-005", "D-006"]
    assert tablo.loc["D-003", "atama_tarihi"] == _g("2026-11-19")
    assert tablo.loc["D-005", "bitis_tarihi"] == _g("2026-11-19")
    assert pd.isna(tablo.loc["D-006", "bitis_tarihi"])


def test_kesit_gunu_yeniden_atamada_donem_ve_hareket_yeni_avukatta():
    kesit = "2026-11-19"
    gunu = atama.donemler(atama_tablosu([
        ("D-001", "AV-01", "TRAFIK", "2026-01-01", "2026-11-19", "YENIDEN_ATAMA"),
        ("D-001", "AV-02", "TRAFIK", "2026-11-19")]), kesit)
    assert list(gunu["avukat_kodu"]) == ["AV-01", "AV-02"]
    assert gunu["bitis_tarihi"].iloc[0] == _g("2026-11-19")
    hareket = pd.DataFrame({"dosya_no": ["D-001", "D-001"],
                            "hareket_tarihi": ["2026-11-18", "2026-11-19"],
                            "tutar": [10.0, 20.0]})
    assert list(atama.hareket_atfet(hareket, gunu, kesit)["avukat_kodu"]) == ["AV-01", "AV-02"]
    ertesi = atama.donemler(atama_tablosu([
        ("D-001", "AV-01", "TRAFIK", "2026-01-01", "2026-11-20", "YENIDEN_ATAMA"),
        ("D-001", "AV-02", "TRAFIK", "2026-11-20")]), kesit)
    assert list(ertesi["avukat_kodu"]) == ["AV-01"] and ertesi["bitis_tarihi"].isna().all()
    assert list(atama.hareket_atfet(hareket, ertesi, kesit)["avukat_kodu"]) == ["AV-01"] * 2


def test_kesit_gunu_atama_kriter_sonuclarina_girer():
    k2 = _k2([("D-001", "AV-01", "TRAFIK", "2026-11-19"),
              ("D-002", "AV-01", "TRAFIK", "2026-11-20")],
             [_surec("D-001", "2026-01-10"), _surec("D-002", "2026-01-10")], "2026-11-19")
    assert list(k2["dosya_no"]) == ["D-001"]
    assert k2["seviye"].iloc[0] == "IZLENIYOR" and k2["sure_gun"].iloc[0] == 0
    k1 = _k1([("D-001", "AV-01", "TRAFIK", "2026-11-19"),
              ("D-002", "AV-01", "TRAFIK", "2026-11-20")], {})
    assert list(k1["dosya_no"]) == ["D-001"]
    assert k1["seviye"].iloc[0] == "IZLENIYOR" and k1["sure_gun"].iloc[0] == 0
