"""Tahsilat puanının aralık, kapanış ve ölçüt kuralları.

Kesit 19.11.2026. Her test, düzeltme öncesi kodda yanlış sonucu veren bir senaryodur.
"""
import random
from decimal import Decimal

import pandas as pd

from avukat_perf import aciklama, gozlem, hazirlik, kriter2, tahsilat, tahsilat_evren
from avukat_perf import tahsilat_maruz
from yardimci import atama_tablosu, params_yukle

KESIT = "2026-11-19"
SUTUN = ["dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi"]


def _hesapla(dosya, atamalar, hareket, kapanis=None, params=None):
    avukat, grup, _ = tahsilat.hesapla(
        pd.DataFrame(dosya, columns=SUTUN), atama_tablosu(atamalar),
        pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]), KESIT,
        params or params_yukle(), kapanis)
    return avukat.set_index("avukat_kodu"), grup


def _portfoy(avukat, harf, adet=20, verilis="2023-01-01", atama="2023-01-10", tutar=100.0,
             tarih="2024-06-01", rucu=10000.0, brans="TRAFIK"):
    nolar = ["{}-{:02d}".format(harf, sira) for sira in range(adet)]
    return ([(no, brans, rucu, verilis) for no in nolar],
            [(no, avukat, brans, atama) for no in nolar],
            [(no, tarih, tutar) for no in nolar] if tutar else [])


def _birlestir(*parcalar):
    return tuple(sum((list(parca[sira]) for parca in parcalar), []) for sira in range(3))


def _kosul_gozlemi(geceler, durum):
    """Her gece için durum(gece) -> [(dosya, rücu kodu, açık bakiye)]; gözlem yalnız ekler."""
    tablo, onceki, k2 = None, None, params_yukle()["kriter2"]
    for gece in geceler:
        goruntu = pd.DataFrame(durum(pd.Timestamp(gece)),
                               columns=["dosya_no", "rucu_kodu", "acik_bakiye"])
        tablo = gozlem.guncelle(tablo, hazirlik.kosul_goruntusu(goruntu, k2), "dosya_no",
                                "kosul_kayip", gece, onceki)
        onceki = gece
    return tablo


def test_atama_oncesi_kodu_kapanis_sayilmaz_tahsilat_yapmayan_gizlenmez():
    """Dosyalar 01.03.2023'te rücuya verilir, atama 01.10.2023'te tamamlanınca R11 olur; o güne
    kadar geceler başka kod (R10) görür. Önceden koşul gözlemi R11 dışı her kodu kapanış sayıyor,
    dosyalar sıklık ve güncellikten kalıcı olarak çıkıyordu: hiç tahsilat yapmayan avukat sıklıkta
    75 alıyordu. Kriter 2 dönemi de aynı nedenle kapsam dışı (KOSUL_SAGLANMIYOR) oluyordu."""
    nolar = {"AV-IYI": ["I-{:02d}".format(s) for s in range(20)],
             "AV-KOTU": ["K-{:02d}".format(s) for s in range(20)]}
    geceler = [str(gun.date()) for gun in pd.date_range("2023-01-10", "2026-11-10", freq="MS")]

    def durum(gece):
        kod = "R11" if gece > pd.Timestamp("2023-10-01") else "R10"
        return [] if gece < pd.Timestamp("2023-03-01") else [
            (no, kod, 1000.0) for liste in nolar.values() for no in liste]
    kosul = _kosul_gozlemi(geceler, durum)
    kapanis = gozlem.kapanislar(kosul, KESIT)
    assert kapanis.empty
    aylar = pd.date_range("2023-11-01", KESIT, freq="MS") + pd.Timedelta(days=4)
    dosya = [(no, "TRAFIK", 10000.0, "2023-03-01") for liste in nolar.values() for no in liste]
    atamalar = [(no, avukat, "TRAFIK", "2023-10-01") for avukat, liste in nolar.items()
                for no in liste]
    hareket = [(no, str(ay.date()), 50.0) for no in nolar["AV-IYI"] for ay in aylar]
    avukat, _ = _hesapla(dosya, atamalar, hareket, kapanis)
    assert avukat.loc["AV-KOTU", "puan_siklik"] < 75.0
    assert avukat.loc["AV-KOTU", "puan_guncellik"] < 75.0
    # Kriter 2: aynı gözlemle atanan dosyanın dönemi ölçülür (koşul kaybı yok).
    surec = hazirlik.k2_surecleri(
        pd.DataFrame({"dosya_no": ["I-00"], "surec_turu": ["ITIRAZ"],
                      "baslangic_tarihi": ["2025-01-10"]}),
        pd.DataFrame({"dosya_no": ["I-00"], "brans": ["TRAFIK"], "rucu_kodu": ["R11"],
                      "acik_bakiye": [1000.0]}), None, kosul, None)
    sonuc = kriter2.degerlendir(atama_tablosu([("I-00", "AV-IYI", "TRAFIK", "2023-10-01")]),
                                surec, KESIT, params_yukle()).iloc[0]
    assert sonuc["seviye"] == "KIRMIZI" and sonuc["dusum"]


def test_kapanis_kodu_ve_sifir_bakiye_kapanistir():
    k2 = params_yukle()["kriter2"]
    assert k2["kapanis_kodlari"] == ["R06", "R12"]
    dosya = pd.DataFrame({"dosya_no": ["D-1", "D-2", "D-3", "D-4", "D-5"],
                          "rucu_kodu": ["R06", "R12", "R11", "R10", "R10"],
                          "acik_bakiye": [500.0, 500.0, 0.0, 500.0, 0.0]})
    kayip = hazirlik.kosul_goruntusu(dosya, k2)["kosul_kayip"].notna()
    assert list(kayip) == [True, True, True, False, False]


def test_kacan_gecede_kapanis_gunu_en_gec_olasi_gundur():
    """02.03 ve 03.03 geceleri başarısız. AV-1 dosyalarını 02.03'te kapatan tahsilatla kapatır,
    AV-2 06.03'te; davranışları aynı. Kapanış en erken gün (01.03) alınınca AV-1'in kapatan
    tahsilatı sıklık ve güncellikte kayboluyordu (40 ve 0 yerine 60 ve 20)."""
    kapanis_gunu = {"A": "2026-03-02", "B": "2026-03-06"}
    nolar = ["A-{:02d}".format(s) for s in range(20)] + ["B-{:02d}".format(s) for s in range(20)]
    geceler = [str(gun.date()) for gun in pd.date_range("2026-02-20", "2026-03-10")
               if str(gun.date()) not in ("2026-03-02", "2026-03-03")]

    def durum(gece):
        return [(no, "R11", 0.0 if gece > pd.Timestamp(kapanis_gunu[no[0]]) else 500.0)
                for no in nolar]
    kosul = _kosul_gozlemi(geceler, durum)
    kapanis = gozlem.kapanislar(kosul, KESIT)
    assert kapanis["A-00"] == pd.Timestamp("2026-03-04")
    assert kapanis["B-00"] == pd.Timestamp("2026-03-07")
    # Kriter 2 bitişi en erken günü kullanmaya devam eder.
    assert gozlem.tarih_esle(kosul)["A-00"] == pd.Timestamp("2026-03-01")
    dosya = [(no, "TRAFIK", 10000.0, "2023-01-01") for no in nolar]
    atamalar = [(no, "AV-1" if no[0] == "A" else "AV-2", "TRAFIK", "2023-01-10") for no in nolar]
    hareket = [(no, gun, 500.0) for no in nolar for gun in ("2024-06-10", "2025-06-10")]
    hareket += [(no, kapanis_gunu[no[0]], 500.0) for no in nolar]
    avukat, _ = _hesapla(dosya, atamalar, hareket, kapanis)
    assert avukat.loc["AV-1", "siklik_o"] == 60 and avukat.loc["AV-1", "guncellik_o"] == 20


def test_rucuya_verilisten_onceki_tahsilat_tutara_girmez():
    """AV-X dosyaları rücuya verilişten (01.03.2023) önce tutup 20 × 500 TL tahsil eder. Tutar
    bileşeni de sıklık gibi [veriliş, kesit] aralığını sayar: AV-Y ve AV-Z'nin beklentisi 2000
    kalır (önceden 12000 olup puanları 58,33'e düşüyordu)."""
    x = ["X-{:02d}".format(s) for s in range(20)]
    z = ["Z-{:02d}".format(s) for s in range(20)]
    dosya = [(no, "TRAFIK", 10000.0, "2023-03-01") for no in x + z]
    atamalar = ([(no, "AV-X", "TRAFIK", "2023-01-01", "2023-02-16", "YENIDEN_ATAMA") for no in x]
                + [(no, "AV-Y", "TRAFIK", "2023-02-16") for no in x]
                + [(no, "AV-Z", "TRAFIK", "2023-03-01") for no in z])
    hareket = [(no, "2024-06-01", 100.0) for no in x + z] + [(no, "2023-02-01", 500.0) for no in x]
    avukat, grup = _hesapla(dosya, atamalar, hareket)
    for kod in ("AV-Y", "AV-Z"):
        assert abs(avukat.loc[kod, "beklenen"] - 2000.0) < 1e-6 and avukat.loc[kod, "puan"] == 75.0
    assert "AV-X" not in avukat.index or avukat.loc["AV-X", "gerceklesen"] == 0.0
    assert grup["atfedilen"].sum() == 4000.0


def test_digerlerinin_orani_sifirsa_ust_katmana_gecilir():
    """AV-A trafikte tahsil eder, aynı gruptaki AV-B hiç etmez; kaskoda AV-C tahsil eder. Diğerinin
    oranı 0 ölçüt sayılmaz: trafikte başka avukat yok (branş katmanı da AV-B), bütün diğerleri
    (AV-B ve AV-C) kullanılır. Önceden AV-A beklenen 0 ile puansız kalıyordu (BEKLENEN_SIFIR)."""
    parca = _birlestir(_portfoy("AV-A", "A", 25, tutar=300.0), _portfoy("AV-B", "B", 25, tutar=0),
                       _portfoy("AV-C", "C", 25, tutar=200.0, brans="KASKO"))
    avukat, _ = _hesapla(*parca)
    assert avukat.loc["AV-A", "durum"] == "GECERLI" and pd.isna(avukat.loc["AV-A", "eksik_nedeni"])
    beklenen = 25 * 10000.0 * (25 * 200.0) / (50 * 10000.0)
    assert abs(avukat.loc["AV-A", "beklenen"] - beklenen) < 1e-6
    # Kimsenin tahsilatı yoksa beklenen sıfır kalır.
    yalniz, _ = _hesapla(*_birlestir(_portfoy("AV-A", "A", 25, tutar=300.0),
                                     _portfoy("AV-B", "B", 25, tutar=0)))
    assert yalniz.loc["AV-A", "eksik_nedeni"] == "BEKLENEN_SIFIR"


def test_sifir_rucu_tutarli_dosyanin_tahsilati_olcut_payina_girmez():
    """AV-A'nın rücu tutarı 0 olan dosyasında 5000 TL tahsilat. AV-A'nın gerçekleşenine girer;
    diğer avukatların beklentisini yükseltmez (önceden AV-B ve AV-C 2000 yerine 4500)."""
    parca = _birlestir(_portfoy("AV-A", "A"), _portfoy("AV-B", "B"), _portfoy("AV-C", "C"))
    dosya, atamalar, hareket = parca
    dosya.append(("A-Z", "TRAFIK", 0.0, "2023-01-01"))
    atamalar.append(("A-Z", "AV-A", "TRAFIK", "2023-01-10"))
    hareket.append(("A-Z", "2024-06-01", 5000.0))
    avukat, _ = _hesapla(dosya, atamalar, hareket)
    for kod in ("AV-B", "AV-C"):
        assert abs(avukat.loc[kod, "beklenen"] - 2000.0) < 1e-6
    assert avukat.loc["AV-A", "gerceklesen"] == 7000.0


def test_bilesen_puani_tam_yarimda_yukari_yuvarlanir():
    """AV-A 30 dosyada 101 TL, AV-B 100 TL: R = 1,0075, tutar puanı tam 75,375 → 75,38 (kayan
    noktada 75,37499… olup 75,37 yazılıyordu)."""
    avukat, _ = _hesapla(*_birlestir(_portfoy("AV-A", "A", 30, tutar=101.0),
                                     _portfoy("AV-B", "B", 30, tutar=100.0)))
    assert avukat.loc["AV-A", "puan_tutar"] == 75.38


def test_hicbir_avukatin_tutmadigi_dosyanin_tahsilati_grupta_sayilmaz():
    """X-00 olgun ama verilişten sonra kapsamdaki hiçbir avukatta bulunmadı (yalnız sulh
    ataması): evrende değildir, tahsilatı grup tablosunda avukata yazılamayan olarak da görünmez."""
    dosya, atamalar, hareket = _portfoy("AV-Y", "Y")
    dosya.append(("X-00", "TRAFIK", 10000.0, "2023-01-01"))
    atamalar.append(("X-00", "AV-S", "TRAFIK", "2023-01-10", None, None, "SULH"))
    hareket += [("X-00", "2024-06-01", 5000.0), ("Y-00", "2023-01-05", 300.0)]
    _, grup = _hesapla(dosya, atamalar, hareket)
    assert list(grup["atanamayan"]) == [300.0] and list(grup["atfedilen"]) == [2000.0]


def test_yas_bandi_tutar_grubunda_ve_gunluk_maruziyette_ayni():
    """Yaş bandı kuralının (rücuya veriliş + n ay, sınır günü dahil) iki kullanımı aynı sonucu
    verir: tutar grubunun kesitteki bandı ile kesit gününün maruziyetinin bandı."""
    tah = params_yukle()["tahsilat"]
    rnd, verilis = random.Random(7), []
    for _ in range(300):
        verilis.append(pd.Timestamp("2018-01-01") + pd.Timedelta(days=rnd.randint(0, 3200)))
    verilis += [pd.Timestamp(gun) for gun in ("2024-02-29", "2023-11-30", "2025-11-19",
                                              "2019-11-19", "2018-05-31")]
    for kesit in ("2026-11-19", "2026-02-28", "2026-03-31"):
        dosya = pd.DataFrame({"dosya_no": ["D-{}".format(s) for s in range(len(verilis))],
                              "rucuya_verilis_tarihi": verilis})
        kesitte = tahsilat_evren.yas_bandi_ekle(dosya, kesit, tah).set_index("dosya_no")
        gun = pd.Timestamp(kesit)
        donem = pd.DataFrame({"dosya_no": dosya["dosya_no"], "avukat_kodu": "AV-1",
                              "atama_tarihi": gun, "bitis_tarihi": pd.NaT})
        aralik = dosya.assign(alt=gun, ust=gun + pd.Timedelta(days=1))
        gunluk = tahsilat_maruz.maruziyet(donem, aralik, tah).set_index("dosya_no")
        assert (gunluk["yas_bandi"] == kesitte.loc[gunluk.index, "yas_bandi"]).all(), kesit


def _sayi(metin):
    return float(Decimal(metin.replace(".", "").replace(",", ".")))


def test_aciklamadaki_sayilarla_elle_hesap_tutar():
    """Kesirli olgun dosyada (kısa tutulup iade edilen dosya) R satırındaki n kesilmez; ağırlıklar
    yuvarlanmaz; yuvarlanınca sıfır olan eksi '-0,00' yazılmaz."""
    dosya, atamalar, hareket = _portfoy("AV-1", "A", 12)
    dosya.append(("A-Z", "TRAFIK", 10000.0, "2023-01-01"))
    atamalar += [("A-Z", "AV-1", "TRAFIK", "2023-01-10", "2025-09-10", "IADE"),
                 ("A-Z", "AV-2", "TRAFIK", "2025-09-10")]
    dosya2, atamalar2, hareket2 = _portfoy("AV-2", "B", 20, tutar=60.0)
    params = params_yukle()
    params["tahsilat"]["bilesen_agirliklari"] = {"tutar": 0.625, "siklik": 0.1875,
                                                 "guncellik": 0.1875}
    avukat, _ = _hesapla(dosya + dosya2, atamalar + atamalar2, hareket + hareket2,
                         params=params)
    satir = avukat.reset_index()
    satir = satir[satir["avukat_kodu"] == "AV-1"]
    assert satir["n"].iloc[0] != round(satir["n"].iloc[0])
    metin = aciklama.uret(params, tahsilat=satir)
    satirlar = list(metin["metin"])
    r_satiri = [m for m in satirlar if m.startswith("R = (")][0]
    n, oran = (_sayi(parca) for parca in r_satiri[5:].split(" + ")[0].split(" × "))
    r = (n * oran + 10) / (n + 10)
    assert abs(r - _sayi(r_satiri.rsplit("= ", 1)[1])) < 1e-6, r_satiri
    toplam = [m for m in satirlar if m.startswith("Tahsilat puanı = ")][0]
    assert "0,625 × " in toplam and "0,1875 × " in toplam
    parcalar = toplam[len("Tahsilat puanı = "):].split(" = ")
    hesap = sum(_sayi(a) * _sayi(b) for a, b in (p.split(" × ") for p in parcalar[0].split(" + ")))
    assert abs(hesap - _sayi(parcalar[1])) <= 0.005 + 1e-9
    assert aciklama.sayi(-1.8e-12) == "0,00" and aciklama.sayi(1302.55 + 11730.90 - 13033.45) \
        == "0,00"
