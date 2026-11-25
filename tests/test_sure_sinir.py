"""Süre puanı ve bilgi amaçlı pencerelerin sınır testleri.

Kesit 2026-11-19; 12 aylık pencere (2025-11-19, 2026-11-19]: 2025-11-19 dışarıda, 2025-11-20 ve
kesit günü içeride, 2026-11-20 dışarıda. Yayın tabanı: E >= 5 (testte), kapsam >= 0,80; en az
30 dosyanın altında puan geçerlidir, yeterli işareti yanlıştır. Beklenen düşüm diğer
avukatlardan kurulur.
Kriter 2 dönemleri: atama 2025-12-01, süreç başlangıcı 2026-01-10, düşüm eşiği 2026-07-10.
"""
import pandas as pd

from avukat_perf import kalite_davranis, kriter2, sure_ozet, sure_puani
from hat import hesap_sure
from yardimci import atama_tablosu, params_yukle

KESIT = "2026-11-19"
GIRDI = list(sure_puani.GIRDI)
K2_ATAMA, K2_BASLANGIC = "2025-12-01", "2026-01-10"
GEC_DAVA, ZAMANINDA_DAVA = "2026-08-15", "2026-03-01"


def _params():
    params = params_yukle()
    params["uyari"]["golge_mod"] = False
    return params


def _donemler(avukat, adet, dusum, brans="TRAFIK", esik="2026-06-01"):
    """adet dönem; ilk 'dusum' tanesi düşüm almış, kalanı süresinde kapanmış."""
    return [(avukat, "K1", "ILK_ISLEM", brans, "TURUNCU" if sira < dusum else "KAPANDI",
             sira < dusum, esik) for sira in range(adet)]


def _tablo(satirlar):
    """Dosya numarası olmayan dönem satırlarından girdi; her dönem ayrı dosyada."""
    tablo = pd.DataFrame(satirlar, columns=[ad for ad in GIRDI if ad != "dosya_no"])
    return tablo.assign(dosya_no=["D-{:04d}".format(no + 1) for no in range(len(tablo))])[GIRDI]


def _kapsam(oranlar):
    return pd.DataFrame(list(oranlar.items()), columns=["avukat_kodu", "kapsam"])


def _puanla(satirlar, oranlar):
    params = _params()
    params["sure_puani"]["en_az_beklenen"] = 5  # taban mekanizması sınanır (varsayılan 0)
    sonuc = sure_puani.puanla(_tablo(satirlar), _kapsam(oranlar), KESIT, params)
    return sonuc.set_index("avukat_kodu")


def _tarihler(seri):
    return [str(tarih.date()) for tarih in seri]


# Madde 2: yayın tabanı ve pencere sınır günleri

def test_yeterli_dosya_tam_10_yeterli_9_uyarili():
    """AV-03'ün 10 dönemi 9 dosyada (bir dosyada iki atama dönemi): yeterli veri eşiği (10) dosyayla
    sınanır. Eşiğin altında puan yine hesaplanır ve geçerlidir (ekranda 'Yeterli veri yok')."""
    satirlar = (_donemler("AV-01", 10, 4) + _donemler("AV-02", 9, 4, brans="KASKO")
                + _donemler("AV-03", 10, 4, brans="YANGIN"))
    tablo = _tablo(satirlar)
    tablo.loc[len(tablo) - 1, "dosya_no"] = tablo.loc[len(tablo) - 2, "dosya_no"]
    kapsam = _kapsam({"AV-01": 1.0, "AV-02": 1.0, "AV-03": 1.0})
    sonuc = sure_puani.puanla(tablo, kapsam, KESIT, _params()).set_index("avukat_kodu")
    assert sonuc["risk_dosya"].to_dict() == {"AV-01": 10, "AV-02": 9, "AV-03": 9}
    assert sonuc["risk_donemi"].to_dict() == {"AV-01": 10, "AV-02": 9, "AV-03": 10}
    assert sonuc["yeterli"].to_dict() == {"AV-01": True, "AV-02": False, "AV-03": False}
    assert set(sonuc["durum"]) == {"GECERLI"} and sonuc["eksik_nedeni"].isna().all()
    assert sonuc["puan"].notna().all()


def test_beklenen_tabani_tam_5_gecer_4_99_gecmez():
    """AV-01'in 30 dönemi, aynı gruptaki AV-09'un 3000 dönemi: E = 30 × AV-09'un düşümü ÷ 3000
    (avukatın kendi dönemleri beklentisine girmez)."""
    tam = _puanla(_donemler("AV-01", 30, 5) + _donemler("AV-09", 3000, 500),
                  {"AV-01": 1.0, "AV-09": 1.0}).loc["AV-01"]
    assert abs(tam["e"] - 5.0) < 1e-9 and tam["o"] == 5
    assert tam["durum"] == "GECERLI" and abs(tam["puan"] - 75.0) < 1e-9
    alti = _puanla(_donemler("AV-01", 30, 5) + _donemler("AV-09", 3000, 499),
                   {"AV-01": 1.0, "AV-09": 1.0}).loc["AV-01"]
    assert abs(alti["e"] - 4.99) < 1e-9 and alti["risk_dosya"] == 30
    assert alti["eksik_nedeni"] == "AZ_BEKLENEN" and pd.isna(alti["puan"])
    # 2521 dönem × 5/2521: E matematik olarak 5, kayan noktada 4,999999999999999 çıkar; tabanı
    # geçmelidir (oranların toplamı yuvarlanarak karşılaştırılır).
    kenar = _puanla(_donemler("AV-01", 2521, 5) + _donemler("AV-09", 2521, 5),
                    {"AV-01": 1.0, "AV-09": 1.0}).loc["AV-01"]
    assert kenar["e"] < 5.0 and abs(kenar["e"] - 5.0) < 1e-9 and kenar["risk_dosya"] == 2521
    assert kenar["durum"] == "GECERLI" and abs(kenar["puan"] - 75.0) < 1e-9


def _k1_kapsam_girdisi(avukat, satirlar):
    """(atama tarihi, kapsam dışı nedeni) satırlarından Kriter 1 sonucu biçiminde tablo."""
    return pd.DataFrame([(avukat, atama, neden) for atama, neden in satirlar],
                        columns=["avukat_kodu", "atama_tarihi", "kapsam_disi_nedeni"])


def test_kapsam_tabani_tam_yuzde_80_gecer_altinda_gecmez():
    bilinmiyor = "ESAS_TARIHI_BILINMIYOR"
    k1 = pd.concat([
        _k1_kapsam_girdisi("AV-01", [("2026-06-01", None)] * 4 + [("2026-06-01", bilinmiyor)]),
        _k1_kapsam_girdisi("AV-02", [("2026-06-01", None)] * 79
                           + [("2026-06-01", bilinmiyor)] * 21)], ignore_index=True)
    kapsam = sure_puani.kapsam_hesapla(k1, KESIT, 12)
    assert kapsam.set_index("avukat_kodu")["kapsam"].to_dict() == {"AV-01": 0.8, "AV-02": 0.79}
    satirlar = _donemler("AV-01", 30, 10) + _donemler("AV-02", 30, 10, brans="KASKO")
    sonuc = sure_puani.puanla(_tablo(satirlar), kapsam, KESIT, _params()).set_index(
        "avukat_kodu")
    assert sonuc.loc["AV-01", "durum"] == "GECERLI" and pd.notna(sonuc.loc["AV-01", "puan"])
    assert sonuc.loc["AV-02", "eksik_nedeni"] == "KAPSAM_DUSUK"
    assert pd.isna(sonuc.loc["AV-02", "puan"])


def test_kapsam_penceresinin_iki_ucu():
    """Kapsam atama tarihi (kesit − 12 ay, kesit] olan dönemlerden hesaplanır."""
    bilinmiyor = "ESAS_TARIHI_BILINMIYOR"
    k1 = pd.concat([
        _k1_kapsam_girdisi("AV-01", [("2025-11-19", bilinmiyor), ("2025-11-20", None),
                                     ("2026-06-01", None), ("2026-11-19", bilinmiyor),
                                     ("2026-11-20", bilinmiyor)]),
        _k1_kapsam_girdisi("AV-02", [("2025-11-19", None), ("2025-11-20", bilinmiyor),
                                     ("2026-11-19", None), ("2026-11-20", None)]),
        _k1_kapsam_girdisi("AV-03", [("2025-11-19", None), ("2026-11-20", None)])],
        ignore_index=True)
    kapsam = sure_puani.kapsam_hesapla(k1, KESIT, 12).set_index("avukat_kodu")["kapsam"]
    # AV-01: 2025-11-20, 2026-06-01 bilinen; kesit günü bilinmiyor. AV-03 pencerede yok.
    assert kapsam.to_dict() == {"AV-01": 2 / 3, "AV-02": 0.5}


def test_esik_kesit_gunundeyse_risk_altinda():
    """Eşiği kesitten sonra olan dönem süresinde kapanmış olsa da henüz risk altında değildir."""
    satirlar = [("AV-01", "K1", "ILK_ISLEM", "TRAFIK", "TURUNCU", True, tarih)
                for tarih in ("2025-11-19", "2025-11-20", "2026-11-19")]
    satirlar.append(("AV-01", "K1", "ILK_ISLEM", "TRAFIK", "KAPANDI", False, "2026-11-20"))
    risk = sure_puani.risk_altindaki(_tablo(satirlar), KESIT, 12)
    assert _tarihler(risk["esik_turuncu"]) == ["2025-11-20", "2026-11-19"]
    sonuc = _puanla(satirlar, {"AV-01": 1.0}).loc["AV-01"]
    assert (sonuc["risk_donemi"], sonuc["o"]) == (2, 2)


def test_golge_araligi_sinirlari_pencere_ve_dusum_durumuyla_tutarli():
    """Gölge gecesinin kapsadığı gün aralığı (alt hariç, üst dahil) içindeki düşüm pencerede
    sayılmaz ve GOLGE_DONEMI yazılır; aralığın iki yanındaki günler sayılır."""
    haric = [(pd.Timestamp("2026-02-27"), pd.Timestamp("2026-02-28"))]
    gunler = ("2026-02-27", "2026-02-28", "2026-03-01")
    satirlar = [("AV-01", "K1", "ILK_ISLEM", "TRAFIK", "KIRMIZI", True, tarih) for tarih in gunler]
    risk = sure_puani.risk_altindaki(_tablo(satirlar), KESIT, 12, haric)
    assert _tarihler(risk["esik_turuncu"]) == ["2026-02-27", "2026-03-01"]
    tablo = pd.DataFrame({"dusum": [True] * 3, "dusum_tarihi": list(gunler)})
    pencerede = sure_ozet.pencerede_dusum(tablo, KESIT, 12, haric)
    durum = sure_ozet.dusum_durumu(tablo, False, haric)
    assert list(pencerede) == [True, False, True]
    assert list(durum) == ["UYGULANDI", "GOLGE_DONEMI", "UYGULANDI"]
    # Alt sınırı olmayan aralık (ilk gece gölge) baştan itibaren bütün günleri kapsar.
    bastan = sure_ozet.dusum_durumu(tablo, False, [(None, pd.Timestamp("2026-02-28"))])
    assert list(bastan) == ["GOLGE_DONEMI", "GOLGE_DONEMI", "UYGULANDI"]
    assert list(sure_ozet.dusum_durumu(tablo, True, haric)) == ["GOLGE"] * 3


# Madde 3 ve 5: Kriter 2 dönemlerinden süre puanı

def _surec(dosya, tur="ITIRAZ", dava=None, kayip=None, kod="R11", bakiye=1000.0):
    return (dosya, "TRAFIK", tur, K2_BASLANGIC, dava, kayip, kod, bakiye)


def _k2(surecler, atamalar):
    tablo = pd.DataFrame(surecler, columns=list(kriter2.SUREC_SUTUNLARI))
    return kriter2.degerlendir(atama_tablosu(atamalar), tablo, KESIT, _params())


def test_beklenen_dusum_surec_bazinda_gruplanir():
    """Aynı kriter ve branşta itirazda düşüm oranı %50, arabuluculukta %20; her süreçte iki
    avukat (AV-01 ve AV-03 itiraz, AV-02 ve AV-04 arabuluculuk). Her avukat kendi sürecindeki
    diğer avukatın oranıyla ölçülür ve ortalama başarıdadır (75). Süreç ayrılmasaydı oran %35
    olur, itirazdaki avukat 62,5, arabuluculuktaki 87,5 alırdı."""
    surecler, atamalar = [], []
    for no in range(160):
        dosya, itiraz, sira = "D-{:03d}".format(no + 1), no % 80 < 40, no % 40
        gec = sira < 20 if itiraz else sira < 8
        surecler.append(_surec(dosya, "ITIRAZ" if itiraz else "ARABULUCULUK",
                               dava=GEC_DAVA if gec else ZAMANINDA_DAVA))
        avukat = ("AV-01", "AV-02", "AV-03", "AV-04")[no // 40]
        atamalar.append((dosya, avukat, "TRAFIK", K2_ATAMA))
    girdi = hesap_sure.sure_girdisi(None, _k2(surecler, atamalar))
    assert sorted(set(zip(girdi["surec"], girdi["brans"]))) == [
        ("ARABULUCULUK", "TRAFIK"), ("ITIRAZ", "TRAFIK")]
    kapsam = _kapsam({"AV-01": 1.0, "AV-02": 1.0, "AV-03": 1.0, "AV-04": 1.0})
    sonuc = sure_puani.puanla(girdi, kapsam, KESIT, _params()).set_index("avukat_kodu")
    assert sonuc["o"].to_dict() == {"AV-01": 20, "AV-02": 8, "AV-03": 20, "AV-04": 8}
    assert sonuc["e"].round(9).to_dict() == {"AV-01": 20.0, "AV-02": 8.0, "AV-03": 20.0,
                                             "AV-04": 8.0}
    assert all(abs(puan - 75.0) < 1e-9 for puan in sonuc["puan"])
    assert set(sonuc["durum"]) == {"GECERLI"}


def test_kosul_kaybiyla_suresinden_once_biten_k2_donemi_risk_disinda():
    surecler = [
        _surec("D-001", kayip="2026-05-01", kod="R06"),  # rücu kodu eşikten önce değişti
        _surec("D-002", kayip="2026-07-09", bakiye=0.0),  # bakiye eşikten bir gün önce sıfır
        _surec("D-003", kayip="2026-07-20", bakiye=0.0),  # eşikten sonra: düşüm oluşmuştu
        _surec("D-004", dava=ZAMANINDA_DAVA),  # süresinde kapandı
        _surec("D-005"),  # atama eşikten önce iadeyle bitti
        _surec("D-006", dava=GEC_DAVA), _surec("D-007", dava=ZAMANINDA_DAVA)]
    atamalar = [(dosya, "AV-01", "TRAFIK", K2_ATAMA) for dosya in ("D-001", "D-002", "D-003",
                                                                    "D-004")]
    atamalar += [("D-005", "AV-01", "TRAFIK", K2_ATAMA, "2026-05-01", "IADE"),
                 ("D-006", "AV-02", "TRAFIK", K2_ATAMA), ("D-007", "AV-02", "TRAFIK", K2_ATAMA)]
    k2 = _k2(surecler, atamalar)
    sirali = k2.set_index("dosya_no").sort_index()
    assert list(sirali["seviye"]) == ["KOSUL_DISI"] * 3 + ["KAPANDI", "SONLANDI", "KAPANDI",
                                                           "KAPANDI"]
    assert list(sirali["dusum"]) == [False, False, True, False, False, True, False]
    assert _tarihler(sirali["esik_turuncu"].iloc[:3]) == ["2026-07-10"] * 3
    girdi = hesap_sure.sure_girdisi(None, k2)
    risk = sure_puani.risk_altindaki(girdi, KESIT, 12)
    assert sorted(risk["dosya_no"]) == ["D-003", "D-004", "D-006", "D-007"]
    sonuc = sure_puani.puanla(girdi, _kapsam({"AV-01": 1.0, "AV-02": 1.0}), KESIT, _params())
    sonuc = sonuc.set_index("avukat_kodu")
    # Grup oranı 2 ÷ 4: koşul dışı ve iade dönemleri ne paydaya ne beklenene girer.
    assert sonuc.loc["AV-01", ["risk_donemi", "risk_dosya", "o"]].tolist() == [2, 2, 1]
    assert sonuc["e"].round(9).to_dict() == {"AV-01": 1.0, "AV-02": 1.0}


# Madde 18: bilgi amaçlı pencereler

def _ozet_satiri(avukat, dosya, atama, seviye, olcum_sonu):
    """Oto branşta Kriter 1 dönemi: uyarı atama + 10 gün, düşüm atama + 20 gün."""
    atama_gunu = pd.Timestamp(atama)
    turuncu = atama_gunu + pd.Timedelta(days=20)
    dusum = seviye in ("TURUNCU", "KIRMIZI")
    return (avukat, "K1", dosya, atama, seviye, dusum, turuncu if dusum else None,
            (pd.Timestamp(olcum_sonu) - atama_gunu).days, olcum_sonu,
            atama_gunu + pd.Timedelta(days=10), turuncu)


def _ozet_girdisi():
    satirlar = [
        _ozet_satiri("AV-01", "D-01", "2025-08-21", "KAPANDI", "2025-11-19"),  # 90 gün, dışarıda
        _ozet_satiri("AV-01", "D-02", "2025-11-10", "KAPANDI", "2025-11-20"),  # 10 gün
        _ozet_satiri("AV-01", "D-03", "2026-11-04", "KAPANDI", KESIT),  # 15 gün
        _ozet_satiri("AV-01", "D-04", "2026-11-01", "KAPANDI", "2026-11-20"),  # kesitten sonra
        _ozet_satiri("AV-01", "D-05", "2026-01-01", "SONLANDI", "2026-03-01"),
        _ozet_satiri("AV-01", "D-06", "2026-11-10", "IZLENIYOR", KESIT),
        _ozet_satiri("AV-02", "D-11", "2025-10-30", "KIRMIZI", KESIT),  # düşüm 2025-11-19
        _ozet_satiri("AV-02", "D-12", "2025-10-31", "KIRMIZI", KESIT),  # düşüm 2025-11-20
        _ozet_satiri("AV-02", "D-13", "2026-10-30", "TURUNCU", KESIT)]  # düşüm kesit günü
    return pd.DataFrame(satirlar, columns=list(sure_ozet.GIRDI))


def test_ortalama_ilk_islem_suresi_olcum_sonuna_gore_pencere_ucleri():
    ozet = sure_ozet.ozet(_ozet_girdisi(), KESIT, 12).set_index("avukat_kodu")
    av1 = ozet.loc["AV-01"]
    # Pencerede kapanan D-02 (atama pencereden önce) ve D-03 (kesit günü): (10 + 15) ÷ 2.
    assert (av1["kapanan"], av1["izleniyor"], av1["dusum_sayisi"]) == (2, 1, 0)
    assert av1["ort_sure_gun"] == 12.5
    av2 = ozet.loc["AV-02"]
    assert (av2["acik_kirmizi"], av2["acik_turuncu"], av2["kapanan"]) == (2, 1, 0)
    assert pd.isna(av2["ort_sure_gun"]) and av2["dusum_sayisi"] == 2


def test_ozet_dusum_sayisi_golge_araliginin_ust_gunu_dahil():
    girdi = _ozet_girdisi()
    sayi = {}
    for ust in ("2025-11-19", "2025-11-20"):  # gölge gecesi 19 ya da 20 Kasım'ı kapsıyor
        ozet = sure_ozet.ozet(girdi, KESIT, 12, [(None, pd.Timestamp(ust))])
        sayi[ust] = ozet.set_index("avukat_kodu").loc["AV-02", "dusum_sayisi"]
    assert sayi == {"2025-11-19": 2, "2025-11-20": 1}


def test_mevcut_alanlar_pencere_ucleri_ve_pencere_parametresi():
    params = params_yukle()  # ölçek teyidi beklenirken de çalışır
    tablo = pd.DataFrame([
        ("AV-01", "2025-11-19", "brans_yetkinligi", 1.0),
        ("AV-01", "2025-11-20", "brans_yetkinligi", 3.0),
        ("AV-01", "2026-11-19", "brans_yetkinligi", 5.0),
        ("AV-01", "2026-11-20", "brans_yetkinligi", 1.0),
        ("AV-02", "2026-05-19", "cozum_yetenegi", 2.0),
        ("AV-02", "2026-05-20", "cozum_yetenegi", 4.0)],
        columns=["avukat_kodu", "degerlendirme_tarihi", "alt_baslik", "puan"])
    sonuc = kalite_davranis.mevcut_alanlar(tablo, KESIT, params).set_index("avukat_kodu")
    av1 = sonuc.loc["AV-01"]
    assert (av1["puan"], av1["degerlendirme_sayisi"]) == (4.0, 2)
    assert av1["son_degerlendirme"] == pd.Timestamp("2026-11-19")
    assert (sonuc.loc["AV-02", "puan"], sonuc.loc["AV-02", "degerlendirme_sayisi"]) == (3.0, 2)
    params["kalite_davranis"]["pencere_ay"] = 6  # (2026-05-19, 2026-11-19]
    alti_ay = kalite_davranis.mevcut_alanlar(tablo, KESIT, params).set_index("avukat_kodu")
    assert (alti_ay.loc["AV-02", "puan"], alti_ay.loc["AV-02", "degerlendirme_sayisi"]) == (4.0, 1)
    assert alti_ay.loc["AV-02", "son_degerlendirme"] == pd.Timestamp("2026-05-20")
    assert alti_ay.loc["AV-01", "puan"] == 5.0
