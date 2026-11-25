"""Atama geçmişi testleri: dönemler, elde tutma payı, hareket atfı."""
import pandas as pd

from avukat_perf import atama
from yardimci import atama_tablosu, hata_bekle

KESIT = "2026-11-19"
ESKI = "avukat_gunleri"  # paylar avukatların günleri arasında bölünür


def _g(metin):
    return pd.Timestamp(metin)


def _gun(bas, son):
    return (_g(son) - _g(bas)).days


def _baslangic(satirlar):
    return pd.DataFrame(satirlar, columns=["dosya_no", "baslangic"]).assign(
        baslangic=lambda tablo: pd.to_datetime(tablo["baslangic"]))


def _hareket(satirlar):
    return pd.DataFrame(satirlar, columns=["dosya_no", "hareket_tarihi", "tutar"])


def test_donemler_kapsam_disini_ve_kesit_sonrasini_almaz():
    tablo = atama.donemler(atama_tablosu([
        ("D-1", "AV-9", "TRAFIK", "2025-01-02", None, None, "SULH"),
        ("D-1", "AV-1", "TRAFIK", "2026-01-01", "2026-12-01", "YENIDEN_ATAMA"),
        ("D-2", "AV-2", "TRAFIK", "2026-01-01", "2026-01-02", "IPTAL"),
        ("D-3", "AV-3", "TRAFIK", "2026-12-01")]), KESIT)
    assert list(tablo["avukat_kodu"]) == ["AV-1"]
    assert pd.isna(tablo["bitis_tarihi"].iloc[0])


def test_bitisik_donem_gecerli_cakisan_donem_hata_verir():
    bitisik = atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2026-01-01", "2026-03-01", "YENIDEN_ATAMA"),
        ("D-1", "AV-2", "TRAFIK", "2026-03-01")])
    assert len(atama.donemler(bitisik, KESIT)) == 2
    cakisan = atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2026-01-01", "2026-03-02", "YENIDEN_ATAMA"),
        ("D-1", "AV-2", "TRAFIK", "2026-03-01")])
    bitissiz = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-01-01"),
                              ("D-1", "AV-2", "TRAFIK", "2026-03-01")])
    assert hata_bekle(ValueError, atama.donemler, cakisan, KESIT)
    assert hata_bekle(ValueError, atama.donemler, bitissiz, KESIT)


def test_kapsam_disi_donem_cakisma_sayilmaz():
    tablo = atama_tablosu([("D-1", "AV-9", "TRAFIK", "2026-01-01", None, None, "SULH"),
                           ("D-1", "AV-1", "TRAFIK", "2026-02-01")])
    assert list(atama.donemler(tablo, KESIT)["avukat_kodu"]) == ["AV-1"]


def test_elde_tutma_payi_toplami_bir_ve_baslangicta_kesilir():
    donem = atama.donemler(atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2022-06-01", "2024-02-01", "YENIDEN_ATAMA"),
        ("D-1", "AV-2", "TRAFIK", "2024-02-01")]), KESIT)
    pay = atama.elde_tutma_paylari(donem, _baslangic([("D-1", "2023-01-01")]), KESIT, ESKI)
    gun1, gun2 = _gun("2023-01-01", "2024-02-01"), _gun("2024-02-01", "2026-11-20")
    assert abs(pay["pay"].sum() - 1.0) < 1e-12
    assert abs(pay["pay"].iloc[0] - gun1 / (gun1 + gun2)) < 1e-12


def test_pay_kesitten_sonraki_bitisi_kesitte_keser():
    donem = pd.DataFrame({"dosya_no": ["D-1", "D-1"], "avukat_kodu": ["AV-1", "AV-2"],
                          "atama_tarihi": [_g("2026-01-01"), _g("2026-11-10")],
                          "bitis_tarihi": [_g("2026-11-10"), _g("2027-06-01")]})
    pay = atama.elde_tutma_paylari(donem, _baslangic([("D-1", "2026-01-01")]), KESIT, ESKI)
    gun1, gun2 = _gun("2026-01-01", "2026-11-10"), _gun("2026-11-10", "2026-11-20")
    assert abs(pay["pay"].iloc[1] - gun2 / (gun1 + gun2)) < 1e-12


def test_hic_tutulmamis_dosya_paya_girmez():
    donem = atama.donemler(atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2022-01-01", "2022-06-01", "IADE")]), KESIT)
    pay = atama.elde_tutma_paylari(donem, _baslangic([("D-1", "2023-01-01")]), KESIT, ESKI)
    assert pay.empty


def test_donemi_araliktan_once_biten_avukat_paya_girmez():
    donem = atama.donemler(atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2022-01-01", "2023-06-01", "YENIDEN_ATAMA"),
        ("D-1", "AV-2", "TRAFIK", "2023-06-01")]), KESIT)
    pay = atama.elde_tutma_paylari(donem, _baslangic([("D-1", "2024-01-01")]), KESIT, ESKI)
    assert list(pay["avukat_kodu"]) == ["AV-2"] and pay["pay"].iloc[0] == 1.0


def test_hareket_tarihindeki_avukata_yazilir():
    donem = atama.donemler(atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2023-02-01", "2024-02-01", "IADE"),
        ("D-1", "AV-2", "TRAFIK", "2024-03-01")]), KESIT)
    tablo = atama.hareket_atfet(_hareket([
        ("D-1", "2023-01-31", 1.0), ("D-1", "2023-02-01", 2.0), ("D-1", "2024-01-31", 3.0),
        ("D-1", "2024-02-01", 4.0), ("D-1", "2024-03-01", 5.0), ("D-1", "2026-11-20", 6.0),
        ("D-9", "2024-01-01", 7.0)]), donem, KESIT)
    assert list(tablo["tutar"]) == [1.0, 2.0, 3.0, 4.0, 5.0, 7.0]
    beklenen = [None, "AV-1", "AV-1", None, "AV-2", None]
    assert [None if pd.isna(kod) else kod for kod in tablo["avukat_kodu"]] == beklenen


def test_hareket_hatali_girdi_hata_verir():
    donem = atama.donemler(atama_tablosu([]), KESIT)
    assert hata_bekle(ValueError, atama.hareket_atfet,
                      _hareket([("D-1", None, 1.0)]), donem, KESIT)
    assert hata_bekle(ValueError, atama.hareket_atfet,
                      _hareket([("D-1", "2024-01-01", None)]), donem, KESIT)


def test_hic_eslesmeyen_harekette_avukat_kodu_metin_turunde_kalir():
    # Atama dönemi olmayan dosyanın hareketi: avukat kodu boş ama sütun metin türünde kalmalı;
    # sayı türüne dönerse sonraki birleştirmeler tür uyuşmazlığıyla çöker.
    donem = atama.donemler(atama_tablosu([("D-1", "AV-1", "TRAFIK", "2023-02-01")]), KESIT)
    tablo = atama.hareket_atfet(_hareket([("D-2", "2026-01-15", 50.0)]), donem, KESIT)
    assert tablo["avukat_kodu"].dtype == object and tablo["avukat_kodu"].isna().all()
