"""Kriter 2 testleri. Kesit 2026-11-19; uyarı 3. ay, düşüm 6. ay (takvim ayı)."""
import pandas as pd

from avukat_perf import hazirlik, kriter2, olay
from yardimci import atama_tablosu, hata_bekle, params_yukle

KESIT = "2026-11-19"
SUTUNLAR = list(kriter2.SUREC_SUTUNLARI)


def _surec(dosya, tur="ITIRAZ", baslangic="2026-01-10", dava=None, kayip=None,
           kod="R11", bakiye=1000.0):
    return (dosya, "TRAFIK", tur, baslangic, dava, kayip, kod, bakiye)


def _calistir(atamalar, surecler, params=None):
    return kriter2.degerlendir(atama_tablosu(atamalar), pd.DataFrame(surecler, columns=SUTUNLAR),
                               KESIT, params or params_yukle())


def _tek(surec, atama_tarihi="2025-12-01"):
    sonuc = _calistir([(surec[0], "AV-1", "TRAFIK", atama_tarihi)], [surec])
    return sonuc.iloc[0].to_dict()


def _g(metin):
    return pd.Timestamp(metin)


def test_ay_esikleri_ve_sinir_gunu():
    assert _tek(_surec("D-1", baslangic="2026-08-19"))["seviye"] == "SARI"
    assert _tek(_surec("D-1", baslangic="2026-08-20"))["seviye"] == "IZLENIYOR"
    sonuc = _tek(_surec("D-1", baslangic="2026-05-19"))
    assert sonuc["seviye"] == "TURUNCU" and sonuc["dusum"]
    assert sonuc["dusum_tarihi"] == _g("2026-11-19")
    assert _tek(_surec("D-1", baslangic="2026-04-19"))["seviye"] == "KIRMIZI"


def test_dava_kaydi_aktif_gecikmeyi_kapatir_gecmisi_korur():
    gec = _tek(_surec("D-1", dava="2026-08-15"))
    assert gec["seviye"] == "KAPANDI" and gec["dusum"]
    assert gec["en_yuksek_seviye"] == "KIRMIZI"
    assert gec["sure_gun"] == (_g("2026-08-15") - _g("2026-01-10")).days
    zamaninda = _tek(_surec("D-1", dava="2026-03-01"))
    assert zamaninda["seviye"] == "KAPANDI" and not zamaninda["dusum"]
    assert pd.isna(zamaninda["en_yuksek_seviye"])


def test_kapsam_disi_surecler():
    beklenen = {"DOGRUDAN_DAVA": "SUREC_DOGRUDAN_DAVA", "KESINLESTI": "SUREC_KESINLESTI",
                None: "SUREC_YOK"}
    for tur, neden in beklenen.items():
        sonuc = _tek(_surec("D-1", tur=tur))
        assert sonuc["seviye"] == "KAPSAM_DISI" and sonuc["kapsam_disi_nedeni"] == neden
    assert _tek(_surec("D-1", baslangic=None))["kapsam_disi_nedeni"] == "BASLANGIC_YOK"
    arabuluculuk = _tek(_surec("D-1", tur="ARABULUCULUK", baslangic="2026-05-19"))
    assert arabuluculuk["seviye"] == "TURUNCU"


def test_kosul_bugun_saglanmiyorsa_ve_gunu_bilinmiyorsa_kapsam_disi():
    for surec in (_surec("D-1", kod="R06"), _surec("D-1", bakiye=0.0)):
        sonuc = _tek(surec)
        assert sonuc["kapsam_disi_nedeni"] == "KOSUL_SAGLANMIYOR" and not sonuc["dusum"]


def test_kosul_kalkinca_kapanir_ama_olusmus_dusum_korunur():
    sonuc = _tek(_surec("D-1", kayip="2026-09-01", kod="R06", bakiye=0.0))
    assert sonuc["seviye"] == "KOSUL_DISI" and sonuc["dusum"]
    assert sonuc["olcum_sonu"] == _g("2026-09-01")
    erken = _tek(_surec("D-1", kayip="2026-03-01", kod="R06"))
    assert erken["seviye"] == "KOSUL_DISI" and not erken["dusum"]


def test_kosul_kesitten_sonra_kalkarsa_kesitteki_dusum_korunur():
    # Dönem sonu kesitten sonra çalışır: ayın 1'i gecesi R06'ya geçen dosya kesitte R11'di.
    sonuc = _tek(_surec("D-1", baslangic="2026-04-01", kayip="2026-11-20", kod="R06",
                        bakiye=0.0))
    assert sonuc["seviye"] == "KIRMIZI" and sonuc["dusum"]
    assert pd.isna(sonuc["kapsam_disi_nedeni"])


def test_birden_cok_bitis_adayinda_en_erkeni_gecerli():
    sonuc = _tek(_surec("D-1", dava="2026-03-01", kayip="2026-09-01", kod="R06"))
    assert sonuc["seviye"] == "KAPANDI" and sonuc["olcum_sonu"] == _g("2026-03-01")
    atamalar = [("D-1", "AV-1", "TRAFIK", "2025-12-01", "2026-04-01", "IADE")]
    sonuc = _calistir(atamalar, [_surec("D-1", dava="2026-08-01")]).iloc[0]
    assert sonuc["seviye"] == "SONLANDI" and sonuc["olcum_sonu"] == _g("2026-04-01")


def test_yeniden_atamada_sure_yeni_atamadan_baslar():
    atamalar = [("D-1", "AV-1", "TRAFIK", "2025-12-01", "2026-06-01", "YENIDEN_ATAMA"),
                ("D-1", "AV-2", "TRAFIK", "2026-06-01")]
    sonuc = _calistir(atamalar, [_surec("D-1")]).set_index("avukat_kodu")
    assert sonuc.loc["AV-1", "seviye"] == "SONLANDI" and not sonuc.loc["AV-1", "dusum"]
    assert sonuc.loc["AV-1", "en_yuksek_seviye"] == "SARI"
    assert sonuc.loc["AV-2", "surec_baslangici"] == _g("2026-06-01")
    assert sonuc.loc["AV-2", "seviye"] == "SARI"


def test_sonlanan_donemde_dusum_parametresi():
    atamalar = [("D-1", "AV-1", "TRAFIK", "2025-12-01", "2026-08-01", "IADE")]
    assert _calistir(atamalar, [_surec("D-1")])["dusum"].iloc[0]
    params = params_yukle()
    params["kriter2"]["sonlanan_atamada_dusum_korunur"] = False
    assert not _calistir(atamalar, [_surec("D-1")], params)["dusum"].iloc[0]


def test_atama_sureci_kapsamiyorsa_ya_da_dava_onceden_varsa_kapsam_disi():
    once_biten = [("D-1", "AV-1", "TRAFIK", "2025-01-01", "2025-06-01", "IADE")]
    sonuc = _calistir(once_biten, [_surec("D-1", baslangic="2025-09-01")])
    assert sonuc["kapsam_disi_nedeni"].iloc[0] == "SUREC_ATAMA_DISI"
    yeni = [("D-1", "AV-2", "TRAFIK", "2026-03-01")]
    sonuc = _calistir(yeni, [_surec("D-1", baslangic="2026-01-01", dava="2026-02-01")])
    assert sonuc["kapsam_disi_nedeni"].iloc[0] == "DAVA_ONCEDEN_VAR"


def test_kesitten_sonraki_dava_bilinmiyor_ve_olaylar():
    sonuc = _calistir([("D-1", "AV-1", "TRAFIK", "2025-12-01")],
                      [_surec("D-1", baslangic="2026-04-19", dava="2026-11-20")])
    assert sonuc["seviye"].iloc[0] == "KIRMIZI"
    olaylar = olay.olaylar(sonuc, "K2")
    assert list(olaylar["seviye"]) == ["SARI", "TURUNCU", "KIRMIZI"]
    assert set(olaylar["kriter"]) == {"K2"}


def test_hatali_girdi_ve_bos_girdi():
    tam = pd.DataFrame([_surec("D-1")], columns=SUTUNLAR)
    atamalar = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2025-12-01")])
    params = params_yukle()
    assert hata_bekle(ValueError, kriter2.degerlendir, atamalar, tam.drop(columns="brans"),
                      KESIT, params)
    assert hata_bekle(ValueError, kriter2.degerlendir, atamalar, pd.concat([tam, tam]),
                      KESIT, params)
    bos = _calistir([], [])
    assert bos.empty and "seviye" in bos.columns


def test_dava_kaydi_var_tarihi_bilinmiyorsa_ceza_uretilmez():
    # Arşivin ilk gecesinde dava esası zaten doluydu, tarihi bilinmiyor (2026-01-10'da görüldü).
    # Tarihin bilinmemesi dava açılmadığı anlamına gelmez: dönem ölçülmez, düşüm yok.
    surecler = pd.DataFrame([_surec("D-1", baslangic="2025-01-10"),
                             _surec("D-2", baslangic="2025-01-10")], columns=SUTUNLAR)
    surecler["dava_gorulme"] = [pd.Timestamp("2026-01-10"), pd.Timestamp("2026-01-10")]
    sonuc = kriter2.degerlendir(atama_tablosu([("D-1", "AV-1", "TRAFIK", "2025-01-01"),
                                               ("D-2", "AV-2", "TRAFIK", "2026-03-01")]),
                                surecler, KESIT, params_yukle()).set_index("dosya_no")
    assert sonuc.loc["D-1", "kapsam_disi_nedeni"] == "DAVA_TARIHI_BILINMIYOR"
    assert sonuc.loc["D-2", "kapsam_disi_nedeni"] == "DAVA_ONCEDEN_VAR"
    assert not sonuc["dusum"].any() and "dava_gorulme" not in sonuc.columns
    assert olay.olaylar(sonuc.reset_index(), "K2").empty


def test_bos_bakiye_kosulu_bozmaz_olusmus_dusum_silinmez():
    """Açık bakiye bir gece boş gelirse koşul son bilinen durumla sürer: oluşmuş düşüm
    sonuçtan kalkmaz (önceden KOSUL_SAGLANMIYOR ile kapsam dışına düşüyordu); koşul gözlemi de
    boş bakiyeyi kapanış saymaz (hazirlik.kosul_goruntusu)."""
    dolu, bos = _tek(_surec("D-1")), _tek(_surec("D-1", bakiye=None))
    assert dolu["dusum"] and bos["dusum"] and bos["kapsam_disi_nedeni"] is None
    assert bos["seviye"] == dolu["seviye"]
    assert kriter2.kosul_kalkti("R11", float("nan"), "R11") is False
    assert kriter2.kosul_kalkti("R11", 0.0, "R11") and kriter2.kosul_kalkti("R06", 5.0, "R11")
    dosya = pd.DataFrame({"dosya_no": ["D-1", "D-2", "D-3"], "rucu_kodu": ["R11", "R11", "R06"],
                          "acik_bakiye": pd.Series([None, 0.0, 9.0], dtype=float)})
    kayip = hazirlik.kosul_goruntusu(dosya, params_yukle()["kriter2"])["kosul_kayip"]
    assert list(kayip.notna()) == [False, True, True]
