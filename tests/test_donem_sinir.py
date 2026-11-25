"""Dönem ve kapı sınırları: son başarılı çekim ve gece seçimi, parametre kuralları, dönem sonuç
kontrolleri, rücu toplamı sıfır tahsilat grubu ve mutabakat toleransı.

Her kural sınırın iki yanında denenir. Tarihler sabittir; testler bugünün tarihine bağlı değildir.
"""
import math

import pandas as pd

from avukat_perf import agirlik, donem, kalite, kalite_iliski, tahsilat
from avukat_perf import params as pr
from hat import calisma, gecmis
from yardimci import (agirlik_karsilastirmasi, atama_tablosu, dort_sutunlu, hata_bekle,
                      params_yukle)

KESIT = "2026-11-19"


# --- Son başarılı çekim ve son başarılı gece (hat/gecmis.py) ---

def _kaynak_satiri(kimlik, kaynak, baslangic, durum, sayi):
    """Bir kaynağın çalışma kaydı satırı; çekim günü başlangıcın günüdür (hat/akis.py)."""
    gun = pd.Timestamp(baslangic).normalize()
    return dict(calisma.satir(kimlik, "GECELIK", kaynak, "dosya", baslangic, gun),
                durum=durum, satir_sayisi=sayi)


def _ozet_satiri(kimlik, baslangic, durum, uretilen, tur="GECELIK"):
    gun = pd.Timestamp(baslangic).normalize()
    return dict(calisma.satir(kimlik, tur, calisma.OZET, "", baslangic, gun),
                durum=durum, uretilen=uretilen)


def test_son_basarili_cekim_gunu_kesin_once_ve_kaldi_atlanir():
    # Satır sayısı zamanla azalır (C2 < C1): dönen sayı en büyük değil, en son çekiminkidir.
    satirlar = [_kaynak_satiri("C1", "esas_goruntu", "2026-11-16 02:00", "BASARILI", 40),
                _kaynak_satiri("C2", "esas_goruntu", "2026-11-17 02:00", "BASARILI", 38),
                _kaynak_satiri("C3", "esas_goruntu", "2026-11-18 02:00", "KALDI", 0),
                _kaynak_satiri("C4", "esas_goruntu", "2026-11-19 02:00", "BASARILI", 45),
                _kaynak_satiri("C5", "dosya", "2026-11-18 02:00", "BASARILI", 9)]
    for sira in (satirlar, satirlar[::-1]):  # SQL'de satır sırası garanti değil
        kayit = calisma.tablo(sira)
        # 'once' günü dahil değil; KALDI satır (boş görüntü kapıda durdu) taban olamaz.
        assert gecmis.son_basarili(kayit, "esas_goruntu", "2026-11-19") == (
            pd.Timestamp("2026-11-17"), 38)
        assert gecmis.son_basarili(kayit, "esas_goruntu", "2026-11-20") == (
            pd.Timestamp("2026-11-19"), 45)
        assert gecmis.son_basarili(kayit, "esas_goruntu", "2026-11-17") == (
            pd.Timestamp("2026-11-16"), 40)
        assert gecmis.son_basarili(kayit, "esas_goruntu", "2026-11-16") == (None, None)
        assert gecmis.son_basarili(kayit, "dosya", "2026-11-19") == (pd.Timestamp("2026-11-18"), 9)
    assert gecmis.son_basarili(None, "dosya", KESIT) == (None, None)
    assert gecmis.son_basarili(calisma.tablo([]), "dosya", KESIT) == (None, None)


def _metin(kayit):
    """Kaydın metin olarak okunmuş hâli: boş değer boş kalır, diğerleri metin olur."""
    return kayit.apply(lambda sutun: sutun.map(lambda deger: None if pd.isna(deger)
                                                else str(deger)))


def test_son_basarili_cekim_metin_olarak_okunan_kayitta_da_dogru():
    # Kayıt SQL ya da CSV'den metin türünde okunabilir: gün ve satır sayısı yine çözülür.
    kayit = _metin(calisma.tablo([
        _kaynak_satiri("C1", "takip", "2026-11-09 02:00", "BASARILI", 7),
        _kaynak_satiri("C2", "takip", "2026-11-10 02:00", "BASARILI", 12)]))
    assert gecmis.son_basarili(kayit, "takip", "2026-11-11") == (pd.Timestamp("2026-11-10"), 12)
    assert gecmis.son_basarili(kayit, "takip", "2026-11-10") == (pd.Timestamp("2026-11-09"), 7)


def test_ayni_gunde_iki_basarili_cekimde_gunun_son_cekimi_taban():
    # Aynı gün iki başarılı çekim: satır sırasından bağımsız olarak günün son çekimi tabandır.
    # Önceden günün ilk çekimi (0 satır) seçiliyordu; ertesi gece boş gelen isteğe bağlı kaynak
    # KALDI yerine UYARI oluyor, Kriter 1 haklı beklemesiz hesaplanıyordu.
    satirlar = [_kaynak_satiri("C1", "bekleme", "2026-11-18 02:00", "BASARILI", 0),
                _kaynak_satiri("C2", "bekleme", "2026-11-18 03:00", "BASARILI", 5)]
    for sira in (satirlar, satirlar[::-1]):
        assert gecmis.son_basarili(calisma.tablo(sira), "bekleme", "2026-11-19") == \
            (pd.Timestamp("2026-11-18"), 5)


def _gece_kaydi():
    return [
        _ozet_satiri("G1", "2026-11-17 02:00", "GECTI", "sonuc_k1=10"),
        _ozet_satiri("G2", "2026-11-18 02:00", "GECTI", "sonuc_k1=11"),
        _ozet_satiri("G3", "2026-11-18 03:00", "GECTI", "sonuc_k1=12,calisma_kaydi=9"),
        _ozet_satiri("G4", "2026-11-18 04:00", "KALDI", "sonuc_k1=99"),
        _ozet_satiri("G5", "2026-11-18 05:00", "GECTI", None),
        _ozet_satiri("G6", "2026-11-18 06:00", "KAYNAK_BEKLENIYOR", None),
        _ozet_satiri("D1", "2026-11-18 07:00", "GECTI", "puan_donem=4", tur="DONEM_SONU"),
        _kaynak_satiri("G7", "dosya", "2026-11-18 08:00", "BASARILI", 3)]


def test_basarili_geceler_zamana_gore_siralanir_kaldi_ve_uretilensiz_atlanir():
    satirlar = _gece_kaydi()
    for sira in (satirlar, satirlar[::-1], satirlar[3:] + satirlar[:3]):
        kayit = calisma.tablo(sira)
        gece = gecmis.basarili_calismalar(kayit)
        assert list(gece["calisma_kimligi"]) == ["G1", "G2", "G3"]
        assert list(gecmis.basarili_calismalar(kayit, "DONEM_SONU")["calisma_kimligi"]) == ["D1"]
        # Aynı günün sonraki çalışması son gecedir; KALDI ve uretilen boş satır değildir.
        assert gecmis.son_basarili_gece(kayit)["calisma_kimligi"] == "G3"
        assert gecmis.son_kimlik(kayit) == "G3"
        assert gecmis.son_sayilar(kayit) == {"sonuc_k1": 12, "calisma_kaydi": 9}
        assert gecmis.son_uretilen(kayit) == {"sonuc_k1", "calisma_kaydi"}
        assert gecmis.son_sayilar(kayit, "DONEM_SONU") == {"puan_donem": 4}


def test_basarili_gece_yoksa_bos_doner():
    yalniz_kalan = calisma.tablo([_ozet_satiri("G4", "2026-11-18 04:00", "KALDI", "a=1"),
                                  _ozet_satiri("G5", "2026-11-18 05:00", "GECTI", None)])
    assert gecmis.basarili_calismalar(yalniz_kalan).empty
    assert gecmis.son_basarili_gece(yalniz_kalan) is None
    assert gecmis.son_kimlik(yalniz_kalan) is None and gecmis.son_uretilen(yalniz_kalan) is None
    assert gecmis.son_sayilar(yalniz_kalan) == {}
    assert gecmis.basarili_calismalar(None) is None
    assert gecmis.son_basarili_gece(calisma.tablo([])) is None
    eski = calisma.tablo(_gece_kaydi()).drop(columns="uretilen")  # alan yokken
    assert gecmis.son_basarili_gece(eski) is None


def test_metin_olarak_okunan_gece_kaydinda_sira_ve_secim_ayni():
    # Kayıt SQL ya da CSV'den metin okunursa boş değer NaN kalır, diğerleri metin olur.
    kayit = _metin(calisma.tablo(_gece_kaydi()[::-1]))
    assert list(gecmis.basarili_calismalar(kayit)["calisma_kimligi"]) == ["G1", "G2", "G3"]
    assert gecmis.son_kimlik(kayit) == "G3"
    assert gecmis.son_sayilar(kayit) == {"sonuc_k1": 12, "calisma_kaydi": 9}


# --- Parametre doğrulaması: haksız düşüme ya da yanlış birleşik puana kapı açan kurallar ---

def _hatalar(bolum, **alanlar):
    params = params_yukle()
    params[bolum].update(alanlar)
    return pr.dogrula(params)


def _egim_hatalari(bolum, egim):
    """Tek bölümde eğim değişince "taban ve egim aynı olmalı" kuralı da düşer
    (test_params.test_tahsilat_ve_sure_puani_olcegi_ayni_olmali); burada yalnız eğimin kendi
    sınırı sınanır."""
    return [hata for hata in _hatalar(bolum, egim=egim) if "taban ve egim" not in hata]


K1_SIRA = "kriter1: 0 < uyari_gun < dusum_gun_oto olmalı"
K2_SIRA = "kriter2: 0 < uyari_ay < dusum_ay olmalı"


def test_kriter1_uyari_ve_dusum_sirasi_sinirin_iki_yani():
    # Eşik günleri tasarım değeridir (Hukuk teyidi): iki alan da açıkça verilir.
    for uyari, dusum, beklenen in ((0, 20, [K1_SIRA]), (-1, 20, [K1_SIRA]), (1, 20, []),
                                   (19, 20, []), (20, 20, [K1_SIRA]), (21, 20, [K1_SIRA]),
                                   (10, 10, [K1_SIRA]), (10, 11, [])):
        assert _hatalar("kriter1", uyari_gun=uyari, dusum_gun_oto=dusum) == beklenen, uyari
    hata = ["kriter1: dusum_ay_diger sıfırdan büyük olmalı"]
    assert _hatalar("kriter1", dusum_ay_diger=0) == hata  # atama günü düşüm olurdu
    assert _hatalar("kriter1", dusum_ay_diger=-1) == hata
    assert _hatalar("kriter1", dusum_ay_diger=1) == []


def test_kriter2_uyari_ve_dusum_sirasi_sinirin_iki_yani():
    # Düşüm ayı açık karardır (4 ya da 6): iki alan da açıkça verilir.
    for uyari, dusum, beklenen in ((0, 6, [K2_SIRA]), (-1, 6, [K2_SIRA]), (1, 6, []),
                                   (3, 3, [K2_SIRA]), (3, 4, []), (5, 6, []),
                                   (4, 4, [K2_SIRA]), (5, 4, [K2_SIRA])):
        assert _hatalar("kriter2", uyari_ay=uyari, dusum_ay=dusum) == beklenen, uyari


def test_oto_branslari_liste_olmali():
    # Tek metin verilseydi branş alt dizgi olarak aranırdı ("RAF" oto sayılırdı).
    for deger in ("TRAFIK", None, {"TRAFIK": True}, 1):
        assert _hatalar("kriter1", oto_branslar=deger) == [
            "liste olmalı: kriter1.oto_branslar"], deger
    assert _hatalar("kriter1", oto_branslar=["TRAFIK"]) == []


def test_sure_puani_kapsam_ve_taban_sinirlari():
    hata = ["sure_puani: en_az_kapsam 0 ile 1 arasında olmalı"]
    assert _hatalar("sure_puani", en_az_kapsam=0) == hata
    assert _hatalar("sure_puani", en_az_kapsam=-0.1) == hata
    assert _hatalar("sure_puani", en_az_kapsam=0.0001) == []
    assert _hatalar("sure_puani", en_az_kapsam=1) == []
    assert _hatalar("sure_puani", en_az_kapsam=1.0001) == hata
    assert _hatalar("sure_puani", en_az_kapsam=80) == hata  # yüzde olarak yazılmış
    taban = ["sure_puani: guven_sabiti ve egim > 0, yeterli_dosya >= 1, en_az_beklenen >= 0 olmalı"]
    assert _hatalar("sure_puani", en_az_beklenen=-0.5) == taban
    assert _hatalar("sure_puani", en_az_beklenen=0) == []
    assert _hatalar("sure_puani", yeterli_dosya=1) == []
    assert _hatalar("sure_puani", guven_sabiti=0.001) == []
    assert _egim_hatalari("sure_puani", 0) == taban


def test_agirliklar_ikili_karsilastirmadan_tutarlilik_denetimiyle():
    params = dort_sutunlu()
    assert agirlik.sutun_agirliklari(params) == {"tahsilat": 0.35, "sure": 0.3, "kalite": 0.25,
                                                 "davranis": 0.1}
    assert agirlik.ham_agirliklar(params["agirliklar"])[1] < 1e-6  # tutarlı (1,17 ≈ 35/30)
    # Yön serbest: "kalite/davranis": 2,5 ile "davranis/kalite": 0,4 aynı ağırlığı verir.
    ters = dict(params["agirliklar"])
    del ters["kalite/davranis"]
    ters["davranis/kalite"] = 0.4
    assert agirlik.sutun_agirliklari(dict(params, agirliklar=ters)) == agirlik.sutun_agirliklari(
        params)
    # Çelişkili karşılaştırma (tahsilat > süre > kalite ama kalite > tahsilat) kabul edilmez.
    celiski = agirlik_karsilastirmasi(30, 30, 25, 15)
    celiski.update({"tahsilat/sure": 3, "sure/kalite": 3, "tahsilat/kalite": 1 / 3.0})
    hata = pr.dogrula(dict(params, agirliklar=celiski))
    assert len(hata) == 1 and hata[0].startswith("agirliklar: karşılaştırmalar tutarsız"), hata
    # Saaty örneği: hafif tutarsızlık (CR ≈ 0,017) kabul edilir.
    hafif = {"tahsilat/sure": 1, "tahsilat/kalite": 2, "tahsilat/davranis": 3, "sure/kalite": 1,
             "sure/davranis": 2, "kalite/davranis": 2}
    assert pr.dogrula(dict(params, agirliklar=hafif)) == []
    # 36,47 / 27,66 / 23,34 / 12,53 → taban 36 / 27 / 23 / 12; kalan 2 puan en büyük kesirlere
    # (süre 0,66; davranış 0,53).
    assert agirlik.sutun_agirliklari(dict(params, agirliklar=hafif)) == {
        "tahsilat": 0.36, "sure": 0.28, "kalite": 0.23, "davranis": 0.13}


def test_agirlik_karsilastirmasi_eksiksiz_tekrarsiz_ve_sinirda():
    def hatalar(karsilastirma):
        return pr.dogrula(dict(dort_sutunlu(), agirliklar=karsilastirma))
    tam = agirlik_karsilastirmasi(30, 30, 25, 15)
    eksik = dict(tam)
    del eksik["sure/davranis"]
    assert hatalar(eksik) == ["agirliklar: eksik çift sure/davranis"]
    assert hatalar(dict(tam, **{"davranis/sure": 0.5})) == [
        "agirliklar: davranis/sure çifti iki kez yazılmış"]
    assert hatalar(dict(tam, **{"tahsilat/tahsilat": 1})) == [
        "agirliklar: bilinmeyen çift tahsilat/tahsilat"]
    for oran in (0, -2, 10, 1 / 10.0, "2", True):
        assert hatalar(dict(tam, **{"tahsilat/sure": oran})) == [
            "agirliklar: tahsilat/sure oranı 1/9 ile 9 arasında sayı olmalı"], oran
    assert hatalar(dict(tam, **{"tahsilat/sure": float("nan")})) == [
        "sonlu bir sayı olmalı (NaN ya da sonsuz olamaz): agirliklar.tahsilat/sure"]
    assert pr.dogrula(dict(params_yukle(), agirliklar=[1, 2])) == ["sözlük olmalı: agirliklar"]
    assert hata_bekle(ValueError, agirlik.sutun_agirliklari, dict(dort_sutunlu(), agirliklar=eksik))


def test_agirlik_yuvarlamasi_tam_yuzde_toplam_yuz():
    # Üç sütun eşit, davranış yarısı: 28,57 / 28,57 / 28,57 / 14,29 → 29 / 29 / 28 / 14.
    params = dict(dort_sutunlu(), agirliklar=agirlik_karsilastirmasi(2, 2, 2, 1))
    assert agirlik.sutun_agirliklari(params) == {"tahsilat": 0.29, "sure": 0.29, "kalite": 0.28,
                                                 "davranis": 0.14}
    for hedef in ((35, 25, 30, 10), (35, 30, 25, 10), (40, 20, 30, 10), (45, 5, 45, 5)):
        sonuc = agirlik.sutun_agirliklari(dict(params, agirliklar=agirlik_karsilastirmasi(*hedef)))
        assert [round(100 * x) for x in sonuc.values()] == list(hedef), hedef


def test_birlesik_puan_kosulu_yalniz_tum_sutunlar():
    """Puana giren sütunların hepsi geçerli olmalı; başka koşul (ör. eksikte ağırlığı dağıtmak)
    kabul edilmez. Hangi sütunların gireceği birlesik_sutunlar'dadır."""
    hata = ["birlesik_puan_kosulu yalnız tum_sutunlar olabilir"]
    params = params_yukle()
    params["birlesik_puan_kosulu"] = "dort_sutun"
    assert pr.dogrula(params) == hata
    del params["birlesik_puan_kosulu"]
    assert pr.dogrula(params) == hata


def test_ilk_fazda_agirliklar_sureyi_oraninda_dagitir():
    """Varsayılan ilk faz: 35 / 25 / 10 oranı korunur → 50 / 35,71 / 14,29 → tam yüzde 50 / 36 / 14
    (kalan kaliteye). Karşılaştırmalar bütün sütunlarla da tutarlı olmalı."""
    params = params_yukle()
    assert params["birlesik_sutunlar"] == ["tahsilat", "kalite", "davranis"]
    assert agirlik.sutun_agirliklari(params) == {"tahsilat": 0.5, "sure": 0.0, "kalite": 0.36,
                                                 "davranis": 0.14}
    uc_sutun = ("tahsilat", "kalite", "davranis")
    assert agirlik.ham_agirliklar(params["agirliklar"], uc_sutun)[1] < 1e-6
    celiski = dict(params["agirliklar"], **{"tahsilat/sure": 9, "sure/kalite": 9})
    assert any("tutarsız" in h for h in pr.dogrula(dict(params, agirliklar=celiski)))
    tek = dict(params, birlesik_sutunlar=["tahsilat"])
    assert pr.dogrula(tek) == [] and agirlik.sutun_agirliklari(tek)["tahsilat"] == 1.0

def _not_hatalari(notlar):
    params = params_yukle()
    params["notlar"] = notlar
    return pr.dogrula(params)


def test_not_olcegi_ilk_esik_100_son_esik_0():
    hata = ["notlar: [ad, eşik] listesi; adlar tekrarsız, eşikler 100'den 0'a azalan"]
    assert _not_hatalari([["A", 100], ["C", 0]]) == []
    assert _not_hatalari([["A", 100.5], ["C", 0]]) == hata
    assert _not_hatalari([["A", 85], ["C", 0.5]]) == hata  # 0,4 puan notsuz kalırdı
    assert _not_hatalari([["A", 85], ["C", -1]]) == hata
    assert _not_hatalari([["A", 85], ["B", 84.99], ["C", 0]]) == []


def test_tahsilat_ve_yeterlilik_kurallari_sinirin_iki_yani():
    hata = ["tahsilat: en_az_olgun_dosya, guven_sabiti ya da egim geçersiz"]
    assert _hatalar("tahsilat", en_az_olgun_dosya=0) == hata
    assert _hatalar("tahsilat", en_az_olgun_dosya=1) == []
    # Uyarı eşiği yayın tabanından küçük olamaz (eşitse uyarı hiç görünmez, geçerli).
    assert _hatalar("tahsilat", yeterli_olgun_dosya=0) == [
        "tahsilat.yeterli_olgun_dosya en_az_olgun_dosya'dan küçük olamaz"]
    assert _hatalar("tahsilat", yeterli_olgun_dosya=1) == []
    assert _hatalar("tahsilat", guven_sabiti=-0.5) == hata
    assert _hatalar("tahsilat", guven_sabiti=0.5) == []
    assert _egim_hatalari("tahsilat", -50) == hata
    assert _egim_hatalari("tahsilat", 0) == hata  # eğim 0: herkes 75, puan başarıdan bağımsız
    assert _egim_hatalari("tahsilat", 0.5) == []
    yeterlilik =["kalite_davranis.yeterlilik [pay, payda] tam sayı olmalı (ör. [2, 3]); "
                  "0 < pay <= payda"]
    # Pay 0 olsaydı hiç puanlanmamış sütun da yeterli sayılırdı.
    assert _hatalar("kalite_davranis", yeterlilik=[0, 3]) == yeterlilik
    assert _hatalar("kalite_davranis", yeterlilik=[1, 3]) == []
    assert _hatalar("kalite_davranis", yeterlilik=[3, 3]) == []
    assert _hatalar("kalite_davranis", yeterlilik=[4, 3]) == yeterlilik


def test_mutabakat_toleransi_sinirin_iki_yani():
    hata = ["kalite: satir_sapma_orani > 0, 0 <= mutabakat_tolerans < 1, gelecek_tarih_gun >= 0, "
            "sapma_en_az_satir >= 0 olmalı"]
    assert _hatalar("kalite", mutabakat_tolerans=-0.001) == hata
    assert _hatalar("kalite", mutabakat_tolerans=0) == []
    assert _hatalar("kalite", mutabakat_tolerans=0.999) == []
    assert _hatalar("kalite", mutabakat_tolerans=1) == hata


# --- Dönem sonuç kontrolleri (avukat_perf/donem.py) ---

def _donem_tablosu():
    """İki avukat, dört sütun, hepsi GECERLI ve aralıkta."""
    sutun = pd.DataFrame([("AV-01", 80.0, "GECERLI"), ("AV-02", 60.0, "GECERLI")],
                         columns=["avukat_kodu", "puan", "durum"])
    tablolar = dict.fromkeys(("tahsilat", "sure", "kalite", "davranis"), sutun)
    return donem.puan_tablosu("2026-10", tablolar, ["AV-01", "AV-02"])


def _kontroller(tablo):
    sonuc = donem.sonuc_kontrolleri(tablo).set_index("kontrol")
    return {ad: (sonuc.loc[ad, "durum"], int(sonuc.loc[ad, "deger"])) for ad in sonuc.index}


GECEN = {"PUAN_ARALIGI": ("GECTI", 0), "SUTUN_TAMLIGI": ("GECTI", 0), "YINELENEN": ("GECTI", 0)}


def _degistir(tablo, avukat, sutun, **alanlar):
    yeni = tablo.copy()
    secili = (yeni["avukat_kodu"] == avukat) & (yeni["sutun"] == sutun)
    for ad, deger in alanlar.items():
        yeni.loc[secili, ad] = deger
    return yeni


def test_sonuc_kontrolleri_tam_tabloda_gecer():
    tablo = _donem_tablosu()
    assert len(tablo) == 8 and _kontroller(tablo) == GECEN
    assert kalite.karar(donem.sonuc_kontrolleri(tablo)) == "GECTI"


def test_sonuc_kontrolleri_eksik_sutun():
    tablo = _donem_tablosu()
    eksik = tablo[~((tablo["avukat_kodu"] == "AV-02") & (tablo["sutun"] == "sure"))]
    assert _kontroller(eksik) == dict(GECEN, SUTUN_TAMLIGI=("KALDI", 1))
    iki = eksik[~((eksik["avukat_kodu"] == "AV-01") & (eksik["sutun"] == "kalite"))]
    assert _kontroller(iki)["SUTUN_TAMLIGI"] == ("KALDI", 2)
    assert kalite.karar(donem.sonuc_kontrolleri(eksik)) == "KALDI"
    # Tanımsız beşinci sütun da tamlığı bozar: avukatın tam olarak dört sütunu olmalı.
    fazla = pd.concat([tablo, tablo.iloc[[0]].assign(sutun="ek_sutun")], ignore_index=True)
    assert _kontroller(fazla) == dict(GECEN, SUTUN_TAMLIGI=("KALDI", 1))
    # Sayı dört ama bir sütun yerine tanımsız ad: önceden yalnız sayı denetlendiği için geçiyordu.
    yerine = eksik.copy()
    yerine = pd.concat([yerine, tablo[(tablo["avukat_kodu"] == "AV-02") & (
        tablo["sutun"] == "sure")].assign(sutun="sure_eski")], ignore_index=True)
    assert _kontroller(yerine) == dict(GECEN, SUTUN_TAMLIGI=("KALDI", 1))


def test_sonuc_kontrolleri_yinelenen_satir():
    tablo = _donem_tablosu()
    # Aynı avukat, dönem ve sütunda farklı puanlı ikinci satır: hangisinin yayımlanacağı belirsiz.
    cift = pd.concat([tablo, tablo.iloc[[0]].assign(puan=10.0)], ignore_index=True)
    assert _kontroller(cift) == dict(GECEN, YINELENEN=("KALDI", 1))
    # Başka dönemin aynı avukat ve sütunu yinelenen değildir.
    diger = pd.concat([tablo, tablo.iloc[[0]].assign(donem="2026-09")], ignore_index=True)
    assert _kontroller(diger)["YINELENEN"] == ("GECTI", 0)


def test_sonuc_kontrolleri_gecerli_satirda_bos_puan():
    tablo = _donem_tablosu()
    bos = _degistir(tablo, "AV-01", "kalite", puan=float("nan"))
    assert _kontroller(bos) == dict(GECEN, PUAN_ARALIGI=("KALDI", 1))
    # Puanı olmayan VERI_YOK satırı olağandır, kontrolü düşürmez.
    veri_yok = _degistir(tablo, "AV-01", "kalite", puan=float("nan"), durum="VERI_YOK")
    assert _kontroller(veri_yok) == GECEN


def test_sonuc_kontrolleri_puan_araligi_sinirlari():
    tablo = _donem_tablosu()
    for puan, beklenen in ((0.0, ("GECTI", 0)), (-0.01, ("KALDI", 1)), (-50.0, ("KALDI", 1)),
                           (100.0, ("GECTI", 0)), (100.01, ("KALDI", 1))):
        degisen = _degistir(tablo, "AV-02", "tahsilat", puan=puan)
        assert _kontroller(degisen)["PUAN_ARALIGI"] == beklenen, puan
    iki = _degistir(_degistir(tablo, "AV-02", "sure", puan=-1.0), "AV-01", "sure",
                    puan=float("nan"))
    assert _kontroller(iki)["PUAN_ARALIGI"] == ("KALDI", 2)


# --- Rücu toplamı sıfır olan tahsilat grubu (avukat_perf/tahsilat.py) ---

def _tahsilat_portfoyu(avukat, adet, brans, rucu, tahsilat_tutari, ilk_no):
    """Olgun dosyalar: rücuya veriliş 2023-01-01, atama 2023-02-01, tek tahsilat 2024-01-01."""
    nolar = ["D-{:03d}".format(ilk_no + sira) for sira in range(adet)]
    dosya = [(no, brans, rucu, "2023-01-01") for no in nolar]
    atama = [(no, avukat, brans, "2023-02-01") for no in nolar]
    hareket = [(no, "2024-01-01", tahsilat_tutari) for no in nolar if tahsilat_tutari]
    return dosya, atama, hareket


def _tahsilat_puanla(*portfoyler):
    dosya = [satir for parca in portfoyler for satir in parca[0]]
    atama = [satir for parca in portfoyler for satir in parca[1]]
    hareket = [satir for parca in portfoyler for satir in parca[2]]
    avukat, grup = tahsilat.puanla(
        pd.DataFrame(dosya, columns=["dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi"]),
        atama_tablosu(atama),
        pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]),
        KESIT, params_yukle())
    return avukat.set_index("avukat_kodu"), grup.set_index("brans")


def test_rucu_toplami_sifir_grupta_oran_sifir_ve_puan_yok():
    avukat, grup = _tahsilat_puanla(
        _tahsilat_portfoyu("AV-01", 25, "YANGIN", 0.0, None, 0),
        _tahsilat_portfoyu("AV-02", 25, "KASKO", 0.0, 100.0, 100))
    for brans, atfedilen in (("YANGIN", 0.0), ("KASKO", 2500.0)):
        assert grup.loc[brans, "rucu_toplami"] == 0.0
        assert grup.loc[brans, "atfedilen"] == atfedilen
        assert grup.loc[brans, "oran"] == 0.0  # 0 / 0 ya da 2500 / 0 değil
    for kod, gerceklesen in (("AV-01", 0.0), ("AV-02", 2500.0)):
        satir = avukat.loc[kod]
        assert satir["beklenen"] == 0.0 and satir["gerceklesen"] == gerceklesen
        assert satir["eksik_nedeni"] == "BEKLENEN_SIFIR" and satir["durum"] == "VERI_YETERSIZ"
        assert pd.isna(satir["puan"]) and pd.isna(satir["r"])
        assert pd.isna(satir["oran"])  # gerçekleşen / beklenen sonsuz yazılmaz
        assert abs(satir["n"] - 25) < 1e-9


def test_rucu_toplami_pozitif_grupta_oran_formulle():
    # Sınırın öbür yanı: çok küçük ama pozitif rücu toplamı oranı formülle verir.
    # İki avukat aynı oranda: beklenti diğer avukatın oranından (0,5).
    avukat, grup = _tahsilat_puanla(_tahsilat_portfoyu("AV-01", 25, "TRAFIK", 0.04, 0.02, 0),
                                    _tahsilat_portfoyu("AV-02", 25, "TRAFIK", 0.04, 0.02, 100))
    assert abs(grup.loc["TRAFIK", "rucu_toplami"] - 2.0) < 1e-9
    assert abs(grup.loc["TRAFIK", "oran"] - 0.5) < 1e-9
    satir = avukat.loc["AV-01"]
    assert abs(satir["beklenen"] - 0.5) < 1e-9 and satir["durum"] == "GECERLI"
    assert abs(satir["puan"] - 75.0) < 1e-9


def test_rucu_toplami_sifir_grup_beklenene_eklenmez():
    # AV-01'in olağan grubu ve rücu toplamı sıfır grubu var: beklenen yalnız olağan gruptan gelir
    # ve sonludur (sıfır grup 0 × sonsuz = NaN üretmez).
    avukat, grup = _tahsilat_puanla(
        _tahsilat_portfoyu("AV-01", 25, "TRAFIK", 1000.0, 300.0, 0),
        _tahsilat_portfoyu("AV-02", 25, "TRAFIK", 1000.0, 100.0, 100),
        _tahsilat_portfoyu("AV-01", 5, "YANGIN", 0.0, None, 200))
    assert abs(grup.loc["TRAFIK", "oran"] - 0.2) < 1e-12 and grup.loc["YANGIN", "oran"] == 0.0
    assert abs(avukat.loc["AV-01", "beklenen"] - 25 * 1000.0 * 0.1) < 1e-6  # diğer avukatın oranı
    assert math.isfinite(avukat.loc["AV-01", "puan"])
    assert avukat.loc["AV-01", "durum"] == "GECERLI"


# --- Mutabakat: göreli fark ve tolerans (avukat_perf/kalite_iliski.py) ---

def _mutabakat(bizim, rapor, tolerans=0.005):
    """bizim, rapor: {dönem: toplam}. Dönem başına (durum, fark). Tolerans açıkça verilir:
    varsayılan değer teyit edilmiş bir karar değildir."""
    params = params_yukle()
    params["kalite"]["mutabakat_tolerans"] = tolerans
    hareket = pd.DataFrame([(ay + "-15", tutar) for ay, tutar in bizim.items()],
                           columns=["hareket_tarihi", "tutar"])
    rapor_tablosu = pd.DataFrame([("AV-01", ay, tutar) for ay, tutar in rapor.items()],
                                 columns=["avukat_kodu", "donem", "tahsilat_toplami"])
    sonuc = kalite_iliski.mutabakat(hareket, rapor_tablosu, params).set_index("kontrol")
    return {ad.split(":")[1]: (sonuc.loc[ad, "durum"], sonuc.loc[ad, "deger"])
            for ad in sonuc.index}


def test_mutabakat_toleransin_tam_siniri_gecer_hemen_ustu_durur():
    sonuc = _mutabakat({"2026-07": 1005.0, "2026-08": 1005.01, "2026-09": 995.0,
                        "2026-10": 994.99},
                       {"2026-07": 1000.0, "2026-08": 1000.0, "2026-09": 1000.0,
                        "2026-10": 1000.0})
    assert sonuc["2026-07"] == ("GECTI", 0.005)
    assert sonuc["2026-08"][0] == "KALDI" and abs(sonuc["2026-08"][1] - 0.00501) < 1e-12
    # Hesaplanan rapordan az olsa da fark mutlak değerdir.
    assert sonuc["2026-09"] == ("GECTI", 0.005)
    assert sonuc["2026-10"][0] == "KALDI"


def test_mutabakat_tolerans_parametreden_gelir():
    rapor = {"2026-10": 1000.0}
    assert _mutabakat({"2026-10": 1009.99}, rapor)["2026-10"][0] == "KALDI"
    assert _mutabakat({"2026-10": 1009.99}, rapor, tolerans=0.01)["2026-10"][0] == "GECTI"
    assert _mutabakat({"2026-10": 1010.01}, rapor, tolerans=0.01)["2026-10"][0] == "KALDI"
    # Tolerans 0: yalnız tam eşitlik geçer.
    assert _mutabakat({"2026-10": 1000.0}, rapor, tolerans=0)["2026-10"] == ("GECTI", 0.0)
    assert _mutabakat({"2026-10": 1000.01}, rapor, tolerans=0)["2026-10"][0] == "KALDI"


def test_mutabakat_kucuk_ve_eksi_toplamda_payda():
    # Rapor toplamı 1'den küçükse fark mutlak tutardır (payda 1); sıfır toplamda bölme yok.
    sonuc = _mutabakat({"2026-07": 0.505, "2026-08": 0.506, "2026-09": 0.0},
                       {"2026-07": 0.5, "2026-08": 0.5, "2026-09": 0.0})
    assert sonuc["2026-07"][0] == "GECTI" and sonuc["2026-08"][0] == "KALDI"
    assert sonuc["2026-09"] == ("GECTI", 0.0)
    # Ters kayıtla eksi kapanan ay: payda raporun mutlak değeri.
    eksi = _mutabakat({"2026-10": -1005.0, "2026-11": -1006.0},
                      {"2026-10": -1000.0, "2026-11": -1000.0})
    assert eksi["2026-10"] == ("GECTI", 0.005) and eksi["2026-11"][0] == "KALDI"
    # Raporda olup bizde hareketi olmayan ay: hesaplanan 0, fark %100.
    assert _mutabakat({"2026-10": 1000.0}, {"2026-10": 1000.0, "2026-09": 400.0})[
        "2026-09"] == ("KALDI", 1.0)


def test_agirlik_yuvarlamasinda_esit_kalan_sutun_sirasiyla():
    """Süre ve Davranış'ın ağırlıkları matematiksel olarak eşit (%31,525...); kayan nokta
    artığı Davranış'ı öne geçiriyordu (22/31/15/32). Eşitlikte sütun sırası: 22/32/15/31."""
    params = dort_sutunlu()
    params["agirliklar"] = {"tahsilat/sure": 1, "tahsilat/kalite": 1, "tahsilat/davranis": 2 / 3,
                            "sure/kalite": 2, "sure/davranis": 1.5, "kalite/davranis": 1 / 3}
    ham = agirlik.ham_agirliklar(params["agirliklar"])[0]
    assert abs(ham["sure"] - ham["davranis"]) < 1e-12
    assert agirlik.sutun_agirliklari(params) == {"tahsilat": 0.22, "sure": 0.32, "kalite": 0.15,
                                                 "davranis": 0.31}


def test_uc_sutunda_tutarlilik_saaty_sabitiyle():
    """Üç sütunda RI 0,58: tahsilat kaliteden 2, kalite davranıştan 2 kat önemli ama tahsilat
    davranıştan yalnız 1,2 kat (tutarlı olsa 4) → CR 0,141, kabul edilmez. Dört sütunun sabitiyle
    (0,90) 0,091 çıkar ve yanlışlıkla geçerdi."""
    karsilastirma = {"tahsilat/kalite": 2, "kalite/davranis": 2, "tahsilat/davranis": 1.2}
    sutunlar = ("tahsilat", "kalite", "davranis")
    assert abs(agirlik.ham_agirliklar(karsilastirma, sutunlar)[1] - 0.1407) < 1e-3
    hata = agirlik.hatalar(karsilastirma, sutunlar)
    assert len(hata) == 1 and hata[0].startswith("agirliklar: karşılaştırmalar tutarsız")
