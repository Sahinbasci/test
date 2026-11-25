"""Kalite ve davranış puanının rastgele vakalarda bağımsız bir uygulamayla karşılaştırılması.

İki çoklu değerlendirme kuralı (ortalama, son), ters yönlü alt başlıklar, boş puanlar, pencere
dışı değerlendirmeler ve tanımsız kodlar denenir. Yeterlilik üçte iki kuralıyla tam sayıda sınanır.
"""
import datetime as dt
import random
from collections import defaultdict

import pandas as pd

from avukat_perf import kalite_davranis
from yardimci import params_yukle

KESIT = dt.date(2026, 11, 19)
PENCERE_BAS = dt.date(2025, 11, 19)  # 12 ay; pencere (PENCERE_BAS, KESIT]


def _vakalar(tohum, kodlar):
    rnd = random.Random(tohum)
    satirlar = []
    for avukat in range(1, 41):
        for _ in range(rnd.randint(1, 4)):
            tarih = KESIT - dt.timedelta(days=rnd.randint(-5, 420))
            degerlendiren = "IA-{}".format(rnd.randint(1, 3))
            for kod in kodlar + ["tanimsiz_kod"]:
                puan = None if rnd.random() < 0.25 else float(rnd.randint(1, 5))
                satirlar.append(("AV-{:02d}".format(avukat), str(tarih), kod, puan, degerlendiren))
    return satirlar


def _bagimsiz(satirlar, alt_basliklar, ters, kural):
    sutun_kodu = {kod: ad for ad, liste in alt_basliklar.items() for kod in liste}
    puanlar, gorulen = defaultdict(list), set()
    for avukat, tarih, kod, puan, _ in satirlar:
        tarih = dt.date.fromisoformat(tarih)
        if kod not in sutun_kodu or not PENCERE_BAS < tarih <= KESIT:
            continue
        gorulen.add(avukat)
        if puan is not None:
            olcekli = (puan - 1) / 4 * 100
            puanlar[(avukat, kod)].append((tarih, 100 - olcekli if kod in ters else olcekli))
    sonuc = {}
    for avukat in gorulen:
        for sutun, liste in alt_basliklar.items():
            ortalamalar = []
            for kod in liste:
                kayitlar = puanlar.get((avukat, kod))
                if not kayitlar:
                    continue
                if kural == "son":
                    son = max(tarih for tarih, _ in kayitlar)
                    kayitlar = [k for k in kayitlar if k[0] == son]
                ortalamalar.append(sum(p for _, p in kayitlar) / len(kayitlar))
            yeterli = len(ortalamalar) * 3 >= len(liste) * 2
            sonuc[(avukat, sutun)] = sum(ortalamalar) / len(ortalamalar) if yeterli else None
    return sonuc


def test_kalite_davranis_rastgele_vakalarda_bagimsiz_hesapla_ayni():
    for tohum, kural in ((1, "ortalama"), (2, "son"), (3, "son"), (4, "ortalama")):
        params = params_yukle()
        kd = params["kalite_davranis"]
        kodlar = kd["alt_basliklar"]["kalite"] + kd["alt_basliklar"]["davranis"]
        ters = kodlar[::3]
        kd.update(olcek={"en_dusuk": 1, "en_yuksek": 5}, ters_yonlu=ters,
                   coklu_degerlendirme=kural)
        satirlar = _vakalar(tohum, kodlar)
        tablo = pd.DataFrame(satirlar, columns=["avukat_kodu", "degerlendirme_tarihi",
                                                "alt_baslik", "puan", "degerlendiren"])
        sutun, _ = kalite_davranis.puanla(tablo, str(KESIT), params)
        sistem = {(s.avukat_kodu, s.sutun): (None if pd.isna(s.puan) else s.puan)
                  for s in sutun.itertuples()}
        beklenen = _bagimsiz(satirlar, kd["alt_basliklar"], set(ters), kural)
        assert set(sistem) == set(beklenen), (tohum, kural)
        for anahtar, deger in beklenen.items():
            assert (deger is None) == (sistem[anahtar] is None), (tohum, kural, anahtar)
            assert deger is None or abs(deger - sistem[anahtar]) < 1e-9, (tohum, kural, anahtar)
