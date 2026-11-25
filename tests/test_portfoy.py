"""Portföy ve aylık tahsilat testleri. Kesit 2026-11-19."""
import pandas as pd

from arayuz import temel
from avukat_perf import portfoy
from yardimci import atama_tablosu, params_yukle

KESIT = "2026-11-19"
DOSYA = ["dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi"]


def _girdi():
    dosyalar = pd.DataFrame([("D-1", "TRAFIK", 10000.0, "2025-01-01"),
                             ("D-2", "TRAFIK", 80000.0, "2025-01-01"),
                             ("D-3", "KASKO", 5000.0, "2025-01-01"),
                             ("D-4", "TRAFIK", 7000.0, "2025-01-01")], columns=DOSYA)
    atamalar = atama_tablosu([
        ("D-1", "AV-1", "TRAFIK", "2025-02-01"),
        ("D-2", "AV-1", "TRAFIK", "2025-02-01", "2026-03-01", "YENIDEN_ATAMA"),
        ("D-2", "AV-2", "TRAFIK", "2026-03-01"),
        ("D-3", "AV-1", "KASKO", "2025-02-01", "2025-06-01", "IADE"),
        ("D-4", "AV-9", "TRAFIK", "2025-02-01", None, None, "SULH")])
    return dosyalar, atamalar


def test_aktif_ve_toplam_dosya():
    dosyalar, atamalar = _girdi()
    params = params_yukle()
    params["tahsilat"]["tutar_bantlari"] = []  # tek bant: avukat × branş başına bir satır
    ozet = portfoy.ozet(dosyalar, atamalar, KESIT, params)
    ozet = ozet.set_index(["avukat_kodu", "brans"])
    assert ozet.loc[("AV-1", "TRAFIK"), "toplam_dosya"] == 2
    assert ozet.loc[("AV-1", "TRAFIK"), "aktif_dosya"] == 1
    assert ozet.loc[("AV-1", "TRAFIK"), "aktif_rucu_tutari"] == 10000.0
    assert ozet.loc[("AV-1", "KASKO"), "aktif_dosya"] == 0
    assert ozet.loc[("AV-2", "TRAFIK"), "aktif_rucu_tutari"] == 80000.0
    assert "AV-9" not in ozet.index.get_level_values(0)


def test_tutar_bandina_gore_ayrilir():
    dosyalar, atamalar = _girdi()
    params = params_yukle()
    params["tahsilat"]["tutar_bantlari"] = [50000]
    ozet = portfoy.ozet(dosyalar, atamalar, KESIT, params)
    av1 = ozet[(ozet["avukat_kodu"] == "AV-1") & (ozet["brans"] == "TRAFIK")]
    assert sorted(av1["tutar_bandi"]) == [0, 1]


def test_aylik_tahsilat_avukata_ve_atanamayana_ayrilir():
    dosyalar, atamalar = _girdi()
    hareketler = pd.DataFrame([
        ("D-1", "2026-10-05", 100.0), ("D-1", "2026-10-20", 50.0), ("D-1", "2026-11-02", 30.0),
        ("D-2", "2026-02-10", 70.0), ("D-2", "2026-03-10", 40.0), ("D-4", "2026-05-01", 9.0),
        ("D-1", "2024-10-01", 999.0), ("D-1", "2026-11-20", 999.0)],
        columns=["dosya_no", "hareket_tarihi", "tutar"])
    aylik = portfoy.aylik_tahsilat(dosyalar, atamalar, hareketler, KESIT, params_yukle())
    tablo = aylik.set_index(["avukat_kodu", "ay"])["tutar"].to_dict()
    assert tablo == {("AV-1", "2026-10"): 150.0, ("AV-1", "2026-11"): 30.0,
                     ("AV-1", "2026-02"): 70.0, ("AV-2", "2026-03"): 40.0,
                     ("ATANAMAYAN", "2026-05"): 9.0}
    assert aylik.loc[aylik["ay"] == "2026-10", "hareket_sayisi"].iloc[0] == 2


def test_bos_girdi():
    dosyalar, atamalar = _girdi()
    ozet = portfoy.ozet(dosyalar.iloc[0:0], atamalar.iloc[0:0], KESIT, params_yukle())
    assert ozet.empty and "aktif_dosya" in ozet.columns
    hareket = pd.DataFrame([], columns=["dosya_no", "hareket_tarihi", "tutar"])
    aylik = portfoy.aylik_tahsilat(dosyalar, atamalar, hareket, KESIT, params_yukle())
    assert aylik.empty and "tutar" in aylik.columns


def test_yillik_tahsilat_ve_onceki_yilin_ayni_donemi():
    # Kesit 19.11.2026; 2025'in aynı dönemi 1 Ocak–19 Kasım 2025.
    dosyalar, atamalar = _girdi()
    hareketler = pd.DataFrame([
        ("D-1", "2025-03-01", 100.0), ("D-1", "2025-11-19", 20.0), ("D-1", "2025-12-01", 50.0),
        ("D-1", "2026-02-01", 90.0), ("D-1", "2026-11-20", 999.0), ("D-1", "2024-06-01", 999.0),
        ("D-2", "2025-05-01", 40.0), ("D-4", "2026-05-01", 9.0), ("D-9", "2026-05-01", 999.0)],
        columns=["dosya_no", "hareket_tarihi", "tutar"])
    params = params_yukle()
    params["tahsilat"]["yillik_yil_sayisi"] = 2
    tablo = portfoy.yillik_tahsilat(dosyalar, atamalar, hareketler, KESIT, params)
    satir = tablo.set_index(["avukat_kodu", "yil"])
    assert satir.loc[("AV-1", 2025), "tutar"] == 210.0  # 100 + 20 + 50 + D-2'deki 40
    assert satir.loc[("AV-1", 2025), "ayni_donem_tutar"] == 160.0  # 19 Kasım dahil
    assert satir.loc[("AV-1", 2026), "tutar"] == 90.0
    assert satir.loc[("AV-1", 2026), "onceki_ayni_donem"] == 160.0
    assert abs(satir.loc[("AV-1", 2026), "degisim"] - (90.0 / 160.0 - 1)) < 1e-12
    assert bool(satir.loc[("AV-1", 2026), "yil_ici"]) and not satir.loc[("AV-1", 2025), "yil_ici"]
    assert satir.loc[("AV-1", 2026), "son_tarih"] == pd.Timestamp(KESIT)
    assert satir.loc[("AV-1", 2025), "son_tarih"] == pd.Timestamp("2025-12-31")
    # Önceki yıl tahsilatı olmayan: değişim boş; bu yıl tahsilatı olmayan yıl sıfırdır.
    assert satir.loc[("ATANAMAYAN", 2025), "tutar"] == 0.0
    # Sulh dönemindeki D-4 yazılamayan sayılır; dosya tablosunda olmayan D-9 hiç sayılmaz.
    assert satir.loc[("ATANAMAYAN", 2026), "tutar"] == 9.0
    assert pd.isna(satir.loc[("ATANAMAYAN", 2026), "degisim"])
    assert set(tablo["yil"]) == {2025, 2026} and len(tablo) == 4
    bos = portfoy.yillik_tahsilat(dosyalar, atamalar, hareketler.iloc[0:0], KESIT, params)
    assert bos.empty and "degisim" in bos.columns
    # Yalnız içinde bulunulan yıl gösterilse de karşılaştırma önceki yıldan kurulur.
    params["tahsilat"]["yillik_yil_sayisi"] = 1
    tek = portfoy.yillik_tahsilat(dosyalar, atamalar, hareketler, KESIT, params)
    assert set(tek["yil"]) == {2026} and bool(tek["yil_ici"].all())
    tek = tek.set_index("avukat_kodu")
    assert tek.loc["AV-1", "onceki_ayni_donem"] == 160.0 and tek.loc["AV-1", "tutar"] == 90.0
    assert abs(tek.loc["AV-1", "degisim"] - (90.0 / 160.0 - 1)) < 1e-12


def test_aylik_pencere_takvim_aylari_ve_kismi_son_ay():
    dosyalar, atamalar = _girdi()
    hareketler = pd.DataFrame([
        ("D-1", "2024-11-30", 7.0), ("D-1", "2024-12-01", 5.0), ("D-1", "2026-11-19", 3.0)],
        columns=["dosya_no", "hareket_tarihi", "tutar"])
    params = params_yukle()
    params["tahsilat"]["aylik_pencere_ay"] = 24
    aylik = portfoy.aylik_tahsilat(dosyalar, atamalar, hareketler, KESIT, params)
    # 24 takvim ayı: kesitin ayı (2026-11) ve önceki 23 ay; ilk ay ayın 1'inden başlar.
    assert sorted(aylik["ay"]) == ["2024-12", "2026-11"]
    assert set(aylik["ilk_ay"]) == {"2024-12"} and set(aylik["son_ay"]) == {"2026-11"}
    assert set(aylik["son_ay_kismi"]) == {True}  # 19 Kasım kesiti: son ay kesite kadar
    ay_sonu = portfoy.aylik_tahsilat(dosyalar, atamalar, hareketler, "2026-10-31", params)
    assert set(ay_sonu["son_ay_kismi"]) == {False} and set(ay_sonu["son_ay"]) == {"2026-10"}


def test_ay_izgarasi_eski_tabloda_yalniz_kayitli_aylar():
    # Izgara sütunlarını taşımayan (aktarımdan önceki gecenin) tablo da çizilir.
    tablo = pd.DataFrame({"ay": ["2026-01", "2026-03"], "tutar": [1.0, 2.0]})
    sonuc = temel.ay_izgarasi(tablo, tablo, ["tutar"])
    assert list(sonuc["ay"]) == ["2026-01", "2026-03"] and not sonuc["kismi"].any()
    yeni = tablo.assign(ilk_ay="2026-01", son_ay="2026-04", son_ay_kismi=True)
    sonuc = temel.ay_izgarasi(yeni, yeni, ["tutar"])
    assert list(sonuc["ay"]) == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert list(sonuc["tutar"]) == [1.0, 0, 2.0, 0] and list(sonuc["kismi"]) == [
        False, False, False, True]


def test_yillik_ay_sonu_kesitinde_onceki_yilin_29_subati_ayni_donemde():
    # Kesit 28.02.2029 (ayın son günü); 2028 artık yıl: aynı dönem 1 Ocak–29 Şubat 2028.
    dosyalar, atamalar = _girdi()
    hareketler = pd.DataFrame([("D-1", "2028-02-27", 1.0), ("D-1", "2028-02-28", 10.0),
                               ("D-1", "2028-02-29", 5.0),
                               ("D-1", "2028-03-01", 7.0), ("D-1", "2029-02-28", 30.0)],
                              columns=["dosya_no", "hareket_tarihi", "tutar"])
    params = params_yukle()
    for kesit, onceki in (("2029-02-28", 16.0), ("2029-02-27", 1.0)):
        tablo = portfoy.yillik_tahsilat(dosyalar, atamalar, hareketler, kesit, params)
        satir = tablo.set_index(["avukat_kodu", "yil"])
        assert satir.loc[("AV-1", 2029), "onceki_ayni_donem"] == onceki, kesit



def test_yillik_30_ve_31_gunluk_ay_sonu_kesitinde_onceki_yilin_son_gunu_ayni_donemde():
    # Ay sonu kesitinde önceki yılın aynı ayı sonuna kadar sayılır (30 Nisan, 31 Mart); ay sonu
    # olmayan kesitte kesit gününe kadar.
    dosyalar, atamalar = _girdi()
    hareketler = pd.DataFrame([("D-1", "2028-03-30", 100.0), ("D-1", "2028-03-31", 1000.0),
                               ("D-1", "2028-04-29", 1.0), ("D-1", "2028-04-30", 10.0),
                               ("D-1", "2029-01-15", 5.0)],
                              columns=["dosya_no", "hareket_tarihi", "tutar"])
    params = params_yukle()
    for kesit, onceki in (("2029-04-30", 1111.0), ("2029-04-29", 1101.0),
                          ("2029-03-31", 1100.0), ("2029-03-30", 100.0)):
        tablo = portfoy.yillik_tahsilat(dosyalar, atamalar, hareketler, kesit, params)
        satir = tablo.set_index(["avukat_kodu", "yil"])
        assert satir.loc[("AV-1", 2029), "onceki_ayni_donem"] == onceki, kesit