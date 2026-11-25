"""Haklı bekleme yardımcılarının testleri."""
import pandas as pd

from avukat_perf import bekleme
from yardimci import bekleme_tablosu, hata_bekle

KESIT = pd.Timestamp("2026-11-19")


def _g(metin):
    return pd.Timestamp(metin)


def test_kayit_yoksa_aralik_yok():
    assert bekleme.araliklar(None, KESIT) == {}
    assert bekleme.araliklar(bekleme_tablosu([]), KESIT) == {}


def test_bitis_gunu_dahil_ve_bitisik_araliklar_birlesir():
    tablo = bekleme_tablosu([("D-1", "AV-1", "2026-11-04", "2026-11-05"),
                             ("D-1", "AV-1", "2026-11-01", "2026-11-03")])
    beklenen = {("D-1", "AV-1"): [[_g("2026-11-01"), _g("2026-11-06")]]}
    assert bekleme.araliklar(tablo, KESIT) == beklenen


def test_ayri_avukat_ayri_aralik():
    tablo = bekleme_tablosu([("D-1", "AV-1", "2026-11-01", "2026-11-01"),
                             ("D-1", "AV-2", "2026-11-01", "2026-11-01")])
    assert sorted(bekleme.araliklar(tablo, KESIT)) == [("D-1", "AV-1"), ("D-1", "AV-2")]


def test_bitisi_bos_ya_da_kesitten_sonra_olan_kesitte_kesilir():
    tablo = bekleme_tablosu([("D-1", "AV-1", "2026-11-10", None),
                             ("D-2", "AV-1", "2026-11-10", "2026-12-31")])
    sonuc = bekleme.araliklar(tablo, KESIT)
    assert sonuc[("D-1", "AV-1")] == [[_g("2026-11-10"), _g("2026-11-20")]]
    assert sonuc[("D-2", "AV-1")] == [[_g("2026-11-10"), _g("2026-11-20")]]


def test_kesitten_sonra_baslayan_bekleme_sayilmaz():
    tablo = bekleme_tablosu([("D-1", "AV-1", "2026-11-20", "2026-11-25")])
    assert bekleme.araliklar(tablo, KESIT) == {}


def test_hatali_bekleme_kaydi_hata_verir():
    ters = bekleme_tablosu([("D-1", "AV-1", "2026-11-05", "2026-11-01")])
    bos = bekleme_tablosu([("D-1", "AV-1", None, "2026-11-01")])
    assert hata_bekle(ValueError, bekleme.araliklar, ters, KESIT)
    assert hata_bekle(ValueError, bekleme.araliklar, bos, KESIT)


def test_esikten_sonra_baslayan_bekleme_esigi_kaydirmaz():
    aralik = [[_g("2026-11-11"), _g("2026-11-15")]]
    assert bekleme.kaydir(_g("2026-11-11"), _g("2026-11-01"), aralik) == _g("2026-11-11")


def test_atamadan_onceki_kisim_sayilmaz():
    atama = _g("2026-11-01")
    aralik = [[_g("2026-10-25"), _g("2026-11-04")]]
    assert bekleme.kaydir(_g("2026-11-11"), atama, aralik) == _g("2026-11-14")
    assert bekleme.gun_sayisi(atama, _g("2026-11-11"), aralik) == 3


def test_kaydirma_yeni_esigin_onune_dusen_beklemeyi_de_sayar():
    atama = _g("2026-11-01")
    aralik = [[_g("2026-11-05"), _g("2026-11-08")], [_g("2026-11-12"), _g("2026-11-14")]]
    assert bekleme.kaydir(_g("2026-11-11"), atama, aralik) == _g("2026-11-16")
    assert bekleme.gun_sayisi(atama, _g("2026-11-16"), aralik) == 5


def test_gun_sayisi_olcum_sonunda_kesilir():
    aralik = [[_g("2026-11-05"), _g("2026-11-15")]]
    assert bekleme.gun_sayisi(_g("2026-11-01"), _g("2026-11-08"), aralik) == 3
    assert bekleme.gun_sayisi(_g("2026-11-01"), _g("2026-11-03"), aralik) == 0
