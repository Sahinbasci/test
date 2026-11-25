"""Olay kaydı testleri: yalnız ekleme, çelişki tespiti, saat dilimi."""
from avukat_perf import kriter1, olay
from yardimci import atama_tablosu, bekleme_tablosu, esas_tablosu, params_yukle

KESIT = "2026-11-19"


def _olaylar(beklemeler=None, kesit=KESIT):
    atamalar = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-10-01")])
    sonuc = kriter1.degerlendir(atamalar, esas_tablosu({}), beklemeler, kesit, params_yukle())
    return olay.olaylar(sonuc, "K1")


def _utc(seri):
    """Dataiku'nun tarihi UTC an olarak saklamasının benzeri."""
    return seri.dt.tz_localize("Europe/Istanbul").dt.tz_convert("UTC")


def test_olay_tarihi_esik_tarihidir():
    tablo = _olaylar()
    assert list(tablo["seviye"]) == ["SARI", "TURUNCU", "KIRMIZI"]
    assert [str(t.date()) for t in tablo["olay_tarihi"]] == [
        "2026-10-11", "2026-10-21", "2026-11-01"]
    assert set(tablo["kriter"]) == {"K1"}


def test_kayitli_olay_silinmez_ve_degistirilmez():
    kayit = olay.olay_birlestir(None, _olaylar()).assign(calisma_kimligi="C-1")
    yeni = _olaylar().assign(calisma_kimligi="C-2")
    birlesik = olay.olay_birlestir(kayit, yeni)
    assert len(birlesik) == 3 and set(birlesik["calisma_kimligi"]) == {"C-1"}


def test_yeni_olay_eklenir():
    kayit = olay.olay_birlestir(None, _olaylar(kesit="2026-10-15"))
    birlesik = olay.olay_birlestir(kayit, _olaylar())
    assert list(birlesik["seviye"]) == ["SARI", "TURUNCU", "KIRMIZI"]


def test_geriye_donuk_bekleme_celiski_olarak_yakalanir():
    kayit = olay.olay_birlestir(None, _olaylar())
    bekleme = bekleme_tablosu([("D-1", "AV-1", "2026-10-03", "2026-10-07")])
    yeni = _olaylar(bekleme)
    celisen = olay.celisen_olaylar(kayit, yeni, KESIT)
    assert list(celisen["seviye"]) == ["SARI", "TURUNCU"]
    assert [str(t.date()) for t in celisen["olay_tarihi_yeni"]] == ["2026-10-16", "2026-10-26"]
    assert len(olay.olay_birlestir(kayit, yeni)) == 3


def test_eski_kesitle_yeniden_hesap_celiski_uretmez():
    kayit = olay.olay_birlestir(None, _olaylar())
    eski = _olaylar(kesit="2026-10-25")
    assert olay.celisen_olaylar(kayit, eski, "2026-10-25").empty


def test_kayit_yokken_celiski_bos():
    assert olay.celisen_olaylar(None, _olaylar(), KESIT).empty


def test_utc_saklanan_kayitla_birlestirme_cift_uretmez():
    kayit = olay.olay_birlestir(None, _olaylar())
    utc = kayit.assign(atama_tarihi=_utc(kayit["atama_tarihi"]),
                       olay_tarihi=_utc(kayit["olay_tarihi"]))
    assert len(olay.olay_birlestir(utc, _olaylar())) == 3
    assert olay.celisen_olaylar(utc, _olaylar(), KESIT).empty
