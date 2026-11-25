"""Tahsilat puanının rastgele vakalarda bağımsız bir uygulamayla karşılaştırılması.

Vakalar: yeniden atama ve boşluk, iade, sulh ve iptal edilmiş atama, rücuya verilişten önce
başlayan atama, atamadan önce, boşlukta ya da kesitten sonra yapılan tahsilat, ters kayıt,
kesitte tahsile kapalı dosyalar (kapanış günü bilinen ve bilinmeyen), rücu tutarı sıfır
dosyalar. İki elde tutma paydası da (ilk_atamadan, avukat_gunleri) denenir. Bağımsız uygulama
yalnız standart kitaplıkla gün sayarak elde tutma payını, atfı, dosya grubunu (branş, yaş bandı,
tutar bandı), tutarın gerçekleşen ve beklenenini, sıklık ve güncelliğin kişi-zamanını (dosya-yıl
maruziyeti günün yaş bandına bölünerek; olay olarak net tahsilatı pozitif dosya-ay), bileşen
puanlarını ve tahsilat puanını kurar; avukat × branş kırılımını da ayrıca hesaplar. Beklenti
aynı gruptaki diğer avukatlardan (grupta yoksa branştaki, o da yoksa bütün diğerlerinden)
kurulur; tutarda diğerlerinin oranı 0 ya da eksiyse üst katmana geçilir. Tutar da sıklık gibi
rücuya verilişten önceki tahsilatı saymaz.
"""
import bisect
import calendar
import datetime as dt
import random
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from avukat_perf import tahsilat
from yardimci import atama_tablosu, params_yukle

KESIT = dt.date(2026, 11, 19)
OLGUNLUK = {"TRAFIK": 24, "KASKO": 24}
BANT = [50000.0, 250000.0]
YAS = [12, 24, 36, 48, 60, 84]
AGIRLIK = {"tutar": "0.6", "siklik": "0.2", "guncellik": "0.2"}
PENCERE_BAS = dt.date(2025, 11, 19)  # kesitten 12 ay önce; pencere bu günden sonra başlar
ALANLAR = ("n", "gerceklesen", "beklenen", "siklik_o", "siklik_e", "guncellik_o", "guncellik_e")
PUANLAR = ("puan_tutar", "puan_siklik", "puan_guncellik", "puan")


def _ay_ekle(gun, ay):
    yil, ay_no = divmod(gun.month - 1 + ay, 12)
    yil, ay_no = gun.year + yil, ay_no + 1
    return dt.date(yil, ay_no, min(gun.day, calendar.monthrange(yil, ay_no)[1]))


def _vakalar(adet, tohum):
    rnd = random.Random(tohum)
    dosyalar, atamalar, hareketler = [], [], []
    for sira in range(adet):
        no = "D-{:05d}".format(sira)
        brans = rnd.choice(["TRAFIK", "KASKO", "YANGIN"])
        verilis = dt.date(2020, 1, 1) + dt.timedelta(days=rnd.randint(0, 2000))
        tutar = round(rnd.choice([20000, 90000, 400000]) * rnd.uniform(0.5, 1.5), 2)
        dosyalar.append((no, brans, 0.0 if rnd.random() < 0.05 else tutar, verilis))
        bas = verilis + dt.timedelta(days=rnd.randint(-60, 300))
        for _ in range(rnd.choice([1, 1, 2, 3])):
            sure = rnd.randint(30, 700)
            bitis = bas + dt.timedelta(days=sure) if rnd.random() < 0.6 else None
            tur = rnd.choice(["NORMAL"] * 8 + ["SULH"])
            neden = "IPTAL" if bitis and rnd.random() < 0.1 else ("IADE" if bitis else None)
            atamalar.append((no, "AV-{}".format(rnd.randint(1, 6)), brans, bas, bitis, neden, tur))
            if bitis is None:
                break
            bas = bitis + dt.timedelta(days=rnd.choice([0, 0, 0, 20]))
        for _ in range(rnd.randint(0, 5)):
            tarih = verilis + dt.timedelta(days=rnd.randint(-30, 2600))
            tutar = round(rnd.uniform(-2000, 30000), 2)
            hareketler.append((no, tarih, tutar))
    return dosyalar, atamalar, hareketler


def _yuvarla(deger):
    return Decimal(repr(float(deger))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _puanlar(n, gercek, beklenen, f_o, f_e, g_o, g_e):
    """(tutar, sıklık, güncellik, tahsilat puanı) ya da bir olgun dosyanın altında dört None."""
    if round(n, 9) < 1 or beklenen < 0.005:
        return (None,) * 4
    r = (n * gercek / beklenen + 10) / (n + 10)
    bilesen = {"tutar": _yuvarla(min(max(75 + 50 * (r - 1), 0.0), 100.0))}
    for ad, o, e in (("siklik", f_o, f_e), ("guncellik", g_o, g_e)):
        bilesen[ad] = _yuvarla(min(max(75 + 50 * ((o + 10) / (e + 10) - 1), 0.0), 100.0))
    toplam = sum(Decimal(AGIRLIK[ad]) * bilesen[ad] for ad in AGIRLIK)
    return tuple(float(bilesen[ad]) for ad in ("tutar", "siklik", "guncellik")) + (
        float(toplam.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),)


def _bant(verilis, gun):
    return sum(1 for ay in YAS if _ay_ekle(verilis, ay) <= gun)


def _kisi_zaman(dosya, donem, atif, ust, alt_gun, secili):
    """{(avukat, dosya, grup): [dosya-yıl, olay]}; aralık alt günden (dahil) üst güne (hariç)."""
    parca = defaultdict(lambda: [0.0, 0])
    for no in secili:
        brans, tutar, verilis = dosya[no][:3]
        alt, son = alt_gun(verilis), ust[no]
        if son is None or son <= alt:
            continue
        bant_tutar = bisect.bisect_right(BANT, tutar)
        yas_sinirlari = [_ay_ekle(verilis, ay) for ay in YAS]
        for bas, bitis, avukat in donem[no]:  # maruziyet: her gün o günkü yaş bandına
            a, b = max(bas, alt), min(bitis or son, son)
            kesim = [a] + [s for s in yas_sinirlari if a < s < b] + [b]
            for x, y in zip(kesim, kesim[1:]):
                if y > x:
                    parca[(avukat, no, (brans, _bant(verilis, x), bant_tutar))][0] += \
                        (y - x).days / 365.0
        aylik = defaultdict(lambda: [0.0, None])  # (avukat, yıl, ay) -> [net, ilk gün]
        for avukat, tarih, tutar_h in atif[no]:
            if alt <= tarih < son:
                kayit = aylik[(avukat, tarih.year, tarih.month)]
                kayit[0] += tutar_h
                if tutar_h > 0.005:  # bant ayın ilk pozitif tahsilatından
                    kayit[1] = tarih if kayit[1] is None else min(kayit[1], tarih)
        for (avukat, _, _), (net, ilk) in aylik.items():
            if net > 0.005:
                parca[(avukat, no, (brans, _bant(verilis, ilk), bant_tutar))][1] += 1
    return parca


def _digerleri(hucre, sifir_olcut_degil=False):
    """{(avukat, grup): oran}: aynı gruptaki DİĞER avukatların pay ÷ payda oranı; grupta başka
    avukat yoksa (sifir_olcut_degil iken oranları 0 ya da eksiyse de) aynı branştakilerin
    (grup[0]), o da yoksa bütün diğerlerinin; yoksa 0. hucre: {(avukat, grup): [pay, payda]}."""
    def katman(anahtar):
        toplam, kendi, avukatlar = (defaultdict(lambda: [0.0, 0.0]),
                                    defaultdict(lambda: [0.0, 0.0]), defaultdict(set))
        for (avukat, grup), (pay_, payda) in hucre.items():
            k = anahtar(grup)
            for hedef in (toplam[k], kendi[(avukat, k)]):
                hedef[0] += pay_
                hedef[1] += payda
            avukatlar[k].add(avukat)
        sonuc = {}
        for avukat, grup in hucre:
            k = anahtar(grup)
            diger = toplam[k][1] - kendi[(avukat, k)][1]
            deger = (toplam[k][0] - kendi[(avukat, k)][0]) / diger if diger > 0 else 0.0
            if len(avukatlar[k]) > 1 and diger > 0 and (deger > 0 or not sifir_olcut_degil):
                sonuc[(avukat, grup)] = deger
        return sonuc
    oran = {}
    for anahtar in (lambda g: g, lambda g: g[0], lambda g: 0):
        for k, v in katman(anahtar).items():
            oran.setdefault(k, v)
    return {k: max(0.0, oran.get(k, 0.0)) for k in hucre}


def _gerceklesen_beklenen(parca):
    """{(avukat, branş): [O, E]}; E = dosya-yıl × diğer avukatların olay ÷ dosya-yıl hızı."""
    hucre = defaultdict(lambda: [0.0, 0.0])  # (avukat, grup): [olay, maruz]
    for (avukat, _, grup), (maruz, olay) in parca.items():
        hucre[(avukat, grup)][0] += olay
        hucre[(avukat, grup)][1] += maruz
    oran = _digerleri(hucre)
    sonuc = defaultdict(lambda: [0.0, 0.0])
    for (avukat, grup), (olay, maruz) in hucre.items():
        sonuc[(avukat, grup[0])][0] += olay
        sonuc[(avukat, grup[0])][1] += maruz * oran[(avukat, grup)]
    return sonuc


def _bagimsiz(dosyalar, atamalar, hareketler, payda, kapanis):
    """({(avukat, branş): [n, G, B, sıklık O, E, güncellik O, E]}, net tahsilatı eksi
    grupların tahsilat toplamı); bütün toplamlar elle."""
    dosya, sinir = {}, KESIT + dt.timedelta(days=1)
    for no, brans, tutar, verilis in dosyalar:
        yas = _bant(verilis, KESIT)
        olgun = _ay_ekle(verilis, OLGUNLUK.get(brans, 36)) <= KESIT
        dosya[no] = (brans, tutar, verilis, (brans, yas, bisect.bisect_right(BANT, tutar)), olgun)
    donem = defaultdict(list)
    for no, avukat, _, bas, bitis, neden, tur in atamalar:
        if tur == "SULH" or neden == "IPTAL" or bas > KESIT:
            continue
        donem[no].append((bas, bitis if bitis and bitis <= KESIT else None, avukat))

    def gunler(no, alt):
        """Avukat başına [alt, kesit] içinde tutulan gün ve dosyanın ilk tutulduğu gün."""
        gun, ilk = defaultdict(int), None
        for bas, bitis, avukat in donem[no]:
            g = max(0, (min(bitis or sinir, sinir) - max(bas, alt)).days)
            gun[avukat] += g
            if g:
                ilk = max(bas, alt) if ilk is None else min(ilk, max(bas, alt))
        return {avukat: g for avukat, g in gun.items() if g}, ilk

    net, atif, son_tahsilat = defaultdict(float), defaultdict(list), {}
    for no, tarih, tutar in hareketler:
        if tarih > KESIT:
            continue
        if tutar > 0.005:
            son_tahsilat[no] = max(son_tahsilat.get(no, tarih), tarih)
        kim = [avukat for bas, bitis, avukat in donem[no]
               if bas <= tarih and (bitis is None or tarih < bitis)]
        if kim:
            atif[no].append((kim[0], tarih, tutar))
            if tarih >= dosya[no][2]:  # tutar rücuya verilişten önceki tahsilatı saymaz
                net[(kim[0], no)] += tutar
    sonuc = defaultdict(lambda: [0.0] * 7)
    # Tutar: olgun dosyalar, elde tutma payıyla; beklenti diğer avukatların oranından.
    pay, hucre = {}, defaultdict(lambda: [0.0, 0.0])  # (avukat, grup): [tahsilat, maruziyet]
    for no, (_, _, verilis, _, olgun) in dosya.items():
        gun, ilk = gunler(no, verilis)
        toplam = (sinir - ilk).days if payda == "ilk_atamadan" and ilk else sum(gun.values())
        if olgun and toplam:
            pay[no] = {avukat: g / toplam for avukat, g in gun.items()}
    for (avukat, no), tutar in net.items():
        if no in pay:
            if dosya[no][1] > 0:  # sıfır rücu tutarlı dosyanın tahsilatı ölçüt payına girmez
                hucre[(avukat, dosya[no][3])][0] += tutar
            sonuc[(avukat, dosya[no][0])][1] += tutar
    for no, paylar in pay.items():
        for avukat, oran in paylar.items():
            hucre[(avukat, dosya[no][3])][1] += oran * dosya[no][1]
            sonuc[(avukat, dosya[no][0])][0] += oran
    diger = _digerleri(hucre, True)  # diğerlerinin net tahsilatı 0 ya da eksiyse üst katman
    for (avukat, g), (_, maruz) in hucre.items():
        sonuc[(avukat, g[0])][2] += maruz * diger[(avukat, g)]
    # Sıklık ve güncellik: kişi-zaman. Kapanan dosyanın süresi kapandığı gün biter; kapanış
    # günü bilinmiyorsa son pozitif tahsilatın ertesi günü, tahsilatı yoksa dosya sayılmaz.
    ust = {}
    for no in dosya:
        if no not in kapanis:
            ust[no] = sinir
        elif kapanis[no] is not None:  # kapanış günü dahil
            ust[no] = min(kapanis[no] + dt.timedelta(days=1), sinir)
        else:
            ust[no] = son_tahsilat[no] + dt.timedelta(days=1) if no in son_tahsilat else None
    ilk_gun = PENCERE_BAS + dt.timedelta(days=1)
    olgunlar = [no for no in dosya if dosya[no][4]]
    for sira, parca in ((3, _kisi_zaman(dosya, donem, atif, ust, lambda v: v, olgunlar)),
                        (5, _kisi_zaman(dosya, donem, atif, ust, lambda v: max(v, ilk_gun),
                                        list(dosya)))):
        for anahtar, (o, e) in _gerceklesen_beklenen(parca).items():
            sonuc[anahtar][sira] += o
            sonuc[anahtar][sira + 1] += e
    return dict(sonuc)


def _calistir(tohum, payda):
    dosyalar, atamalar, hareketler = _vakalar(400, tohum)
    rnd = random.Random(tohum + 1000)
    kapanis = {}  # kesitte tahsile kapalı dosyalar; kapanış günü bilinmeyen None
    for no, _, _, verilis in dosyalar:
        if rnd.random() < 0.2:
            kapanis[no] = None if rnd.random() < 0.3 else min(
                KESIT, verilis + dt.timedelta(days=rnd.randint(-30, 2400)))
    params = params_yukle()
    params["tahsilat"].update(tutar_bantlari=BANT, elde_tutma_paydasi=payda)
    assert params["tahsilat"]["yas_bantlari"] == YAS
    avukat, _, brans = tahsilat.hesapla(
        pd.DataFrame([(no, b, t, str(v)) for no, b, t, v in dosyalar],
                     columns=["dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi"]),
        atama_tablosu([(no, a, b, str(bas), str(bt) if bt else None, ne, tu)
                       for no, a, b, bas, bt, ne, tu in atamalar]),
        pd.DataFrame([(no, str(t), tu) for no, t, tu in hareketler],
                     columns=["dosya_no", "hareket_tarihi", "tutar"]), str(KESIT), params,
        pd.Series(pd.to_datetime([str(g) if g else None for g in kapanis.values()]),
                  index=list(kapanis), dtype="datetime64[ns]"))
    return (avukat.set_index("avukat_kodu"), brans.set_index(["avukat_kodu", "brans"]),
            _bagimsiz(dosyalar, atamalar, hareketler, payda, kapanis))


def _yakin(a, b):
    return abs(a - b) <= 1e-6 * max(1.0, abs(b))


def _karsilastir(satir, degerler, anahtar):
    for ad, deger in zip(ALANLAR, degerler):
        assert _yakin(satir[ad], deger), (anahtar, ad, satir[ad], deger)
    for ad, puan in zip(PUANLAR, _puanlar(*degerler)):
        assert (puan is None) == pd.isna(satir[ad]), (anahtar, ad)
        assert puan is None or abs(satir[ad] - puan) < 1e-9, (anahtar, ad, satir[ad], puan)
    return _puanlar(*degerler)[3] is not None


def test_tahsilat_rastgele_vakalarda_bagimsiz_hesapla_ayni():
    gorulen = set()
    for tohum, payda in ((11, "ilk_atamadan"), (12, "ilk_atamadan"), (13, "avukat_gunleri"),
                         (14, "avukat_gunleri")):
        avukat, brans, bagimsiz = _calistir(tohum, payda)
        assert sorted(brans.index) == sorted(bagimsiz), tohum
        toplam = defaultdict(lambda: [0.0] * 7)
        for (kod, _), degerler in bagimsiz.items():
            toplam[kod] = [a + b for a, b in zip(toplam[kod], degerler)]
        assert sorted(avukat.index) == sorted(toplam), tohum
        puanli = [_karsilastir(avukat.loc[kod], degerler, (tohum, kod))
                  for kod, degerler in toplam.items()]
        assert sum(puanli) >= 4, tohum  # karşılaştırma boş değerler üzerinden yapılmadı
        for anahtar, degerler in bagimsiz.items():
            satir = brans.loc[anahtar]
            _karsilastir(satir, degerler, (tohum,) + anahtar)
            gorulen.add(bool(satir["yeterli"]))
            assert bool(satir["yeterli"]) == (round(degerler[0], 9) >= 10), (tohum, anahtar)
            if degerler[2] < tahsilat.YARIM_KURUS:
                assert pd.isna(satir["oran"]), (tohum, anahtar)
            else:
                assert _yakin(satir["oran"], degerler[1] / degerler[2]), (tohum, anahtar)
        # Beklenti diğer avukatlardan: toplamlar eşit olmak zorunda değil, ama boş da değil.
        assert (avukat["beklenen"] > 0).any() and (avukat["siklik_e"] > 0).any(), tohum
        assert avukat["guncellik_o"].sum() > 20 and avukat["siklik_o"].sum() > 100, tohum
    assert gorulen == {True, False}  # yeterli veri eşiğinin altında ve üstünde satırlar sınandı
