"""Sonlu olmayan sayılar finansal toplam ve puan üretimine ulaşmamalıdır."""
import pandas as pd

from avukat_perf import kalite, sema
from yardimci import params_yukle


def test_butun_sayisal_alanlarda_sonsuz_deger_kapiyi_durdurur():
    params = params_yukle()
    for kaynak, tanim in sema.KAYNAKLAR.items():
        sayilar = [ad for ad, tur, _ in tanim["alanlar"] if tur == "sayi"]
        if not sayilar:
            continue
        ham = {ad: 1.0 if tur == "sayi" else
               "2026-01-01" if tur in ("tarih", "zaman") else "X"
               for ad, tur, _ in tanim["alanlar"]}
        ham.update({ad: deger for ad, deger in (("brans", "TRAFIK"),
                                                ("alt_baslik", "eksik_hatali_islem"))
                    if ad in ham})  # tanımlı kod: bilinmeyen değer kendisi KALDI verir
        _, normal = kalite.denetle(kaynak, pd.DataFrame([ham]), "2026-11-19", params)
        assert kalite.karar(normal) == "GECTI", kaynak
        for alan in sayilar:
            for deger in (float("inf"), float("-inf"), "Infinity", "-Infinity"):
                _, sonuc = kalite.denetle(kaynak, pd.DataFrame([dict(ham, **{alan: deger})]),
                                         "2026-11-19", params)
                assert kalite.karar(sonuc) == "KALDI", (kaynak, alan, deger)


def test_tahsilat_cekirdegi_dogrudan_sonsuz_hareketi_reddeder():
    from test_tahsilat_bilesen import ESKI, _hesapla, _parca
    for deger in (float("inf"), float("-inf"), "NaN"):
        a = _parca("AV-A", 30, 0,
                   {n: [("2026-06-20", deger if n == 0 else 100.0)] for n in range(30)}, **ESKI)
        b = _parca("AV-B", 30, 100,
                   {n: [("2026-06-20", 100.0)] for n in range(30)}, **ESKI)
        try:
            _hesapla([a, b])
        except ValueError:
            continue
        assert False, "gecersiz tutar puan uretememeli"


def test_sonlu_tutarlarin_toplami_tasiyorsa_cekirdek_durdurur():
    from test_tahsilat_bilesen import ESKI, _hesapla, _parca
    for sutun in ("hareket", "rucu"):
        a = _parca("AV-A", 30, 0,
                   {n: [("2026-06-20", 1e308 if sutun == "hareket" else 100.0)]
                    for n in range(30)}, rucu=1e308 if sutun == "rucu" else 1000.0, **ESKI)
        b = _parca("AV-B", 30, 100,
                   {n: [("2026-06-20", 100.0)] for n in range(30)}, **ESKI)
        try:
            _hesapla([a, b])
        except ValueError:
            continue
        assert False, "tasabilecek toplam puan uretememeli"


def test_sonsuz_tahsilat_geceyi_durdurur_son_gecerli_puan_korunur():
    import os
    import shutil
    from hat import akis, ayar
    from test_arayuz_etiket import _sozluk
    from yardimci import prova_ortami
    ortam, kaynaklar, params, kok = prova_ortami(200, 6)
    try:
        assert akis.gecelik(ortam, kaynaklar, params, "2026-11-19 02:00")["karar"] == "GECTI"
        once = ortam.tablo_oku("sonuc_birlesik")
        yol = ayar.kaynak_ayari(kaynaklar, "tahsilat_hareketi")["dosya"]["yol"]
        yol = os.path.join(kok, yol)
        hareket = pd.read_csv(yol)
        hareket.loc[0, "tutar"] = float("inf")
        hareket.to_csv(yol, index=False)
        assert akis.gecelik(ortam, kaynaklar, params, "2026-11-20 02:00")["karar"] == "KALDI"
        pd.testing.assert_frame_equal(once, ortam.tablo_oku("sonuc_birlesik"))
        kontroller = ortam.tablo_oku("kalite_sonucu")
        sonsuz = kontroller[kontroller["kontrol"] == "SONSUZ:tutar"]
        assert not sonsuz.empty and "KALDI" in set(sonsuz["durum"])
        assert "SONSUZ" in _sozluk("DENETIM")
    finally:
        shutil.rmtree(kok)
