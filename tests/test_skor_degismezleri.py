"""Sabit dosya/sorumluluk döneminde skorun nedensel ve sıralamadan bağımsız davranışı."""
import copy
import random

import pandas as pd

from test_tahsilat_bilesen import ESKI, _hesapla, _parca
from yardimci import params_yukle


def _dunya(seed):
    rastgele = random.Random(seed)
    parcalar = []
    for avukat in range(4):
        for sira, brans in enumerate(("TRAFIK", "KASKO")):
            ilk = 1000 * avukat + 100 * sira
            odeme = {n: [("2026-06-20", float(rastgele.randint(10, 300)))]
                     for n in range(22)}
            parcalar.append(_parca("AV-" + str(avukat), 22, ilk, odeme, brans=brans,
                                    rucu=rastgele.choice((30000.0, 75000.0, 200000.0)), **ESKI))
    return parcalar


def test_ek_tahsilat_sabit_portfoyde_kendi_beklentisini_ve_notunu_bozmaz():
    for seed in range(8):
        parcalar = _dunya(seed)
        yeni = copy.deepcopy(parcalar)
        for parca in yeni[:2]:
            parca[2][:] = [(dosya, tarih, tutar + 100.0) for dosya, tarih, tutar in parca[2]]
        for grup in (["brans", "yas_bandi", "tutar_bandi"], ["tutar_bandi"]):
            params = params_yukle()
            params["tahsilat"]["gruplama"] = grup
            once = _hesapla(parcalar, params)[0].loc["AV-0"]
            sonra = _hesapla(yeni, params)[0].loc["AV-0"]
            assert abs(once.beklenen - sonra.beklenen) < 1e-6, (seed, grup)
            assert sonra.puan_tutar >= once.puan_tutar, (seed, grup)
            assert sonra.puan >= once.puan, (seed, grup)


def test_kayit_sirasi_skoru_degistirmez():
    for seed in range(4):
        parcalar = _dunya(seed)
        yeni = copy.deepcopy(parcalar)
        rastgele = random.Random(seed + 100)
        rastgele.shuffle(yeni)
        for parca in yeni:
            for tablo in parca:
                rastgele.shuffle(tablo)
        once = _hesapla(parcalar)[0].sort_index()
        sonra = _hesapla(yeni)[0].sort_index()
        pd.testing.assert_frame_equal(once, sonra)
