"""Ortak yardımcıların testleri."""
import pandas as pd

from avukat_perf.ortak import anahtar_kontrol, bos_kontrol, gun, sutun_kontrol, tek_gun
from yardimci import hata_bekle


def test_utc_saklanan_yerel_gece_yarisi_ayni_gune_cevrilir():
    seri = pd.Series(["2026-10-11T21:00:00Z", "2026-10-12T20:59:00Z", None])
    sonuc = gun(seri)
    assert list(sonuc[:2]) == [pd.Timestamp("2026-10-12"), pd.Timestamp("2026-10-12")]
    assert pd.isna(sonuc[2]) and sonuc.dt.tz is None


def test_saatli_deger_gune_indirgenir():
    assert tek_gun("2026-10-12 18:21:38") == pd.Timestamp("2026-10-12")
    assert tek_gun(pd.Timestamp("2026-10-12")) == pd.Timestamp("2026-10-12")


def test_bos_seri_tarih_turunde_kalir():
    sonuc = gun(pd.Series([], dtype=object))
    assert sonuc.empty and str(sonuc.dtype) == "datetime64[ns]"


def test_kontroller_hata_verir():
    tablo = pd.DataFrame({"a": [1, 1], "b": [2, None]})
    assert hata_bekle(ValueError, sutun_kontrol, tablo, ("a", "c"), "t")
    assert hata_bekle(ValueError, anahtar_kontrol, tablo, ("a",), "t")
    assert hata_bekle(ValueError, bos_kontrol, tablo, ("b",), "t")
    sutun_kontrol(tablo, ("a", "b"), "t")
    anahtar_kontrol(tablo, ("a", "b"), "t")
    bos_kontrol(tablo, ("a",), "t")


def test_hata_iletisi_satir_degeri_icermez():
    tablo = pd.DataFrame({"dosya_no": ["D-777", "D-777"]})
    try:
        anahtar_kontrol(tablo, ("dosya_no",), "atamalar")
    except ValueError as hata:
        assert str(hata) == "atamalar: anahtarı yinelenen 2 satır var"
    else:
        raise AssertionError("hata bekleniyordu")


def test_tarih_yalniz_iso_bicimde_kabul_edilir():
    # Biçim verilmemiş gün.ay.yıl ay-gün ters okunmaz, sayı (epoch) 1970 sayılmaz: hata.
    for bozuk in (["05.11.2026"], ["2026/11/05"], [1763510400000]):
        assert hata_bekle(ValueError, gun, pd.Series(bozuk, dtype=object))
        assert gun(pd.Series(bozuk, dtype=object), zorla=True).isna().all()
    assert hata_bekle(ValueError, gun, pd.Series([1763510400000]))
    karisik = pd.Series(["2026-11-05", " 2026-11-06 14:30:00 ", "", None,
                         "2026-11-19T21:00:00Z"], dtype=object)
    sonuc = gun(karisik)
    assert list(sonuc[:2]) == [pd.Timestamp("2026-11-05"), pd.Timestamp("2026-11-06")]
    assert sonuc[2:4].isna().all() and sonuc.iloc[4] == pd.Timestamp("2026-11-20")
    assert gun(pd.Series([float("nan"), float("nan")])).isna().all()


def test_string_ve_category_turundeki_tarih_de_denetlenir():
    # pandas string türünde gelen 11.05.2026 denetimsiz geçip 5 Kasım okunuyordu (Kriter 1'de
    # 1 Mayıs atamaya 188 gün ve haksız düşüm). Bütün metin türleri aynı kuraldan geçer.
    for tur in ("string", "category"):
        seri = pd.Series(["11.05.2026", "2026-05-11", None], dtype=tur)
        assert hata_bekle(ValueError, gun, seri), tur
        sonuc = gun(seri, zorla=True)
        assert pd.isna(sonuc[0]) and sonuc[1] == pd.Timestamp("2026-05-11") and pd.isna(sonuc[2])
    saatli = pd.Series(["2026-10-11T21:00:00Z", "2026-05-12 10:00"], dtype="string")
    assert list(gun(saatli)) == [pd.Timestamp("2026-10-12"), pd.Timestamp("2026-05-12")]
