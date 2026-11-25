"""Kriter 1'in rastgele vakalarda bağımsız bir uygulamayla karşılaştırılması (haklı bekleme dahil).

Bağımsız uygulama kuralı başka bir yoldan kurar: atamadan itibaren gün gün yürür, haklı bekleme
günlerini saymaz ("saat durur"). Eşik, sayılan gün sayısı eşiğin gün sayısına ulaştığı gündür;
süre, ölçüm sonuna kadar sayılan gündür. Kesitten sonraki bekleme bilinmiyor sayılır.
Tohum sabittir; her çalıştırmada aynı vakalar denenir.
"""
import calendar
import datetime as dt
import random

import pandas as pd

from avukat_perf import kriter1
from yardimci import atama_tablosu, bekleme_tablosu, params_yukle

KESIT = dt.date(2026, 11, 19)
BIR = dt.timedelta(days=1)


def _ay_ekle(gun, ay):
    yil, ay_no = divmod(gun.month - 1 + ay, 12)
    yil, ay_no = gun.year + yil, ay_no + 1
    return dt.date(yil, ay_no, min(gun.day, calendar.monthrange(yil, ay_no)[1]))


def _bekleme_gunleri(araliklar):
    gunler = set()
    for bas, son in araliklar:
        if bas > KESIT:
            continue
        son = min(son or KESIT, KESIT)
        while bas <= son:
            gunler.add(bas)
            bas += BIR
    return gunler


def _esik(atama, gun_sayisi, bekleme):
    sayilan, gun = 0, atama
    while sayilan < gun_sayisi:
        sayilan += gun not in bekleme
        gun += BIR
    return gun


def _bagimsiz(atama, brans, esas, bitis, araliklar):
    bekleme = _bekleme_gunleri(araliklar)
    esas = esas if esas and esas <= KESIT else None
    bitis = bitis if bitis and bitis <= KESIT else None
    if esas and esas < atama:
        return None
    if esas and (bitis is None or esas <= bitis):
        son, kapanis = esas, "KAPANDI"
    elif bitis:
        son, kapanis = bitis, "SONLANDI"
    else:
        son, kapanis = KESIT, None
    turuncu_gun = 20 if brans == "TRAFIK" else (_ay_ekle(atama, 2) - atama).days
    sari, turuncu = _esik(atama, 10, bekleme), _esik(atama, turuncu_gun, bekleme)
    kirmizi = dt.date(turuncu.year + (turuncu.month == 12), turuncu.month % 12 + 1, 1)
    esik = {"SARI": sari, "TURUNCU": turuncu, "KIRMIZI": kirmizi}
    olusan = [ad for ad in ("SARI", "TURUNCU", "KIRMIZI") if esik[ad] <= son]
    sure = sum(1 for i in range((son - atama).days) if atama + i * BIR not in bekleme)
    return (kapanis or (olusan[-1] if olusan else "IZLENIYOR"), "TURUNCU" in olusan, sure,
            sari, turuncu, kirmizi)


def _vakalar(adet, tohum=7):
    rnd = random.Random(tohum)
    for sira in range(adet):
        atama = KESIT - dt.timedelta(days=rnd.randint(0, 200))
        brans = rnd.choice(["TRAFIK", "YANGIN"])
        esas = atama + dt.timedelta(days=rnd.randint(-5, 220)) if rnd.random() < 0.6 else None
        bitis = atama + dt.timedelta(days=rnd.randint(1, 200)) if rnd.random() < 0.3 else None
        araliklar = []
        for _ in range(rnd.choice([0, 1, 1, 2, 3])):
            bas = atama + dt.timedelta(days=rnd.randint(-15, 120))
            son = None if rnd.random() < 0.15 else bas + dt.timedelta(days=rnd.randint(0, 40))
            araliklar.append((bas, son))
        yield "D-{:05d}".format(sira), atama, brans, esas, bitis, araliklar


def test_kriter1_rastgele_vakalarda_bagimsiz_hesapla_ayni():
    vakalar = list(_vakalar(600))
    atamalar = atama_tablosu([(no, "AV-1", brans, str(atama)) + (
        (str(bitis), "IADE") if bitis else ()) for no, atama, brans, _, bitis, _ in vakalar])
    esaslar = pd.DataFrame([(no, str(esas) if esas else None) for no, _, _, esas, _, _ in vakalar],
                           columns=["dosya_no", "esas_ilk_giris"])
    bekleme = bekleme_tablosu([(no, "AV-1", str(bas), str(son) if son else None)
                               for no, _, _, _, _, araliklar in vakalar for bas, son in araliklar])
    sonuc = kriter1.degerlendir(atamalar, esaslar, bekleme, str(KESIT),
                                params_yukle()).set_index("dosya_no")
    farklar = []
    for no, atama, brans, esas, bitis, araliklar in vakalar:
        beklenen = _bagimsiz(atama, brans, esas, bitis, araliklar)
        satir = sonuc.loc[no]
        if beklenen is None:
            assert satir["kapsam_disi_nedeni"] == "ESAS_ONCEDEN_VAR", no
            continue
        sistem = (satir["seviye"], bool(satir["dusum"]), int(satir["sure_gun"]),
                  satir["esik_sari"].date(), satir["esik_turuncu"].date(),
                  satir["esik_kirmizi"].date())
        if sistem != beklenen:
            farklar.append((no, beklenen, sistem))
    assert not farklar, farklar[:3]
