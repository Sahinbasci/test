"""Dağılım grafiklerinin verisi (arayuz/sunum_dagilim.py): kutu sınırları, not, yüzdelik, kuyruk."""
import pandas as pd

from arayuz import dagilim_brans as db
from arayuz import dagilim_sure as ds
from arayuz import sunum_dagilim as dg
from yardimci import params_yukle


def _puan(satirlar):
    return pd.DataFrame(satirlar, columns=["avukat_kodu", "sutun", "puan", "durum"])


def _birlesik(satirlar):
    return pd.DataFrame(satirlar, columns=["avukat_kodu", "birlesik_puan", "performans_notu",
                                           "durum"])


def _kutu(tablo, sutun, alt):
    return tablo[(tablo["sutun"] == sutun) & (tablo["alt"] == alt)].iloc[0]


def test_puan_kutulari_sinirlar_ve_bos_kutular():
    puan = _puan([("AV-1", "tahsilat", 0.0, "GECERLI"), ("AV-2", "tahsilat", 4.99, "GECERLI"),
                  ("AV-3", "tahsilat", 5.0, "GECERLI"), ("AV-4", "tahsilat", 100.0, "GECERLI"),
                  ("AV-5", "tahsilat", 50.0, "VERI_YETERSIZ"), ("AV-1", "kalite", 75.0, "GECERLI"),
                  ("AV-1", "sure", 60.0, "GECERLI")])
    tablo = dg.puan_dagilimi(puan, None, params_yukle())
    # Her sütunda 0-100 aralığının 20 kutusu; geçersiz puan sayılmaz; 100 son kutuda.
    assert list(tablo["sutun"].drop_duplicates()) == ["tahsilat", "sure", "kalite"]  # sabit sıra
    assert (tablo.groupby("sutun").size() == 20).all()
    assert _kutu(tablo, "tahsilat", 0)["adet"] == 2 and _kutu(tablo, "tahsilat", 5)["adet"] == 1
    assert _kutu(tablo, "tahsilat", 95)["adet"] == 1 and _kutu(tablo, "tahsilat", 50)["adet"] == 0
    assert _kutu(tablo, "tahsilat", 95)["ust"] == 100
    tah = tablo[tablo["sutun"] == "tahsilat"].iloc[0]
    assert tah["toplam"] == 4 and tah["ortanca"] == 4.995
    # Beklenen düzey yalnız göreli ölçülen sütunlarda (parametreden).
    params = params_yukle()
    assert tah["taban"] == params["tahsilat"]["taban"]
    assert tablo[tablo["sutun"] == "sure"].iloc[0]["taban"] == params["sure_puani"]["taban"]
    assert pd.isna(tablo[tablo["sutun"] == "kalite"].iloc[0]["taban"])


def test_birlesik_kutusunun_notu_sonuc_tablosundan():
    # Yayımlanmamış satırın puanı olsa da (savunma) dağılıma girmez; ekranda yalnız yayın var.
    birlesik = _birlesik([("AV-1", 85.0, "A", "YAYIMLANDI"), ("AV-2", 84.99, "B+", "YAYIMLANDI"),
                          ("AV-3", None, None, "EKSIK_SUTUN"), ("AV-4", 50.0, "C", "EKSIK_SUTUN")])
    tablo = dg.puan_dagilimi(None, birlesik, params_yukle())
    assert _kutu(tablo, "birlesik", 85)["not_adi"] == "A"
    assert _kutu(tablo, "birlesik", 80)["not_adi"] == "B+"
    assert pd.isna(_kutu(tablo, "birlesik", 50)["not_adi"])
    assert tablo["adet"].sum() == 2  # yayımlanmayan birleşik puan sayılmaz
    assert dg.puan_dagilimi(None, None, params_yukle()) is None


def test_tahsilat_portfoy_noktalari():
    tah = pd.DataFrame({"avukat_kodu": ["AV-1", "AV-2"], "n": [40.5, 12.0],
                        "puan": [81.0, None], "durum": ["GECERLI", "VERI_YETERSIZ"],
                        "oran": [1.2, None]})
    tablo = dg.tahsilat_dosya(tah, params_yukle())
    assert list(tablo.columns) == ["avukat_kodu", "olgun_dosya", "puan", "durum", "taban"]
    assert list(tablo["avukat_kodu"]) == ["AV-2", "AV-1"]  # az dosyadan çoğa
    assert dg.tahsilat_dosya(None, params_yukle()) is None


def test_avukatin_yuzdeligi_esitlikte_ayni():
    puan = _puan([("AV-1", "tahsilat", 50.0, "GECERLI"), ("AV-2", "tahsilat", 70.0, "GECERLI"),
                  ("AV-3", "tahsilat", 70.0, "GECERLI"), ("AV-4", "tahsilat", 90.0, "GECERLI"),
                  ("AV-1", "kalite", 60.0, "GECERLI"), ("AV-2", "sure", 10.0, "VERI_YETERSIZ")])

    def yer(kod, sutun):
        tablo = dg.konum(puan, None, kod)
        satir = tablo[tablo["sutun"] == sutun].iloc[0]
        return satir["avukat_puani"], satir["yuzdelik"]
    assert yer("AV-1", "tahsilat") == (50.0, 0.0)
    assert yer("AV-4", "tahsilat") == (90.0, 100.0)
    iki, uc = yer("AV-2", "tahsilat"), yer("AV-3", "tahsilat")
    assert iki == uc and iki[0] == 70.0 and abs(iki[1] - 200.0 / 3) < 1e-9  # eşitler aynı
    assert yer("AV-1", "kalite") == (60.0, 100.0)  # tek avukat en üstte sayılır
    # En yüksek puanı paylaşan iki avukat da 100 (önceden eşitlik en alt sırayı alıyordu).
    esit = _puan([("AV-1", "kalite", 80.0, "GECERLI"), ("AV-2", "kalite", 80.0, "GECERLI"),
                  ("AV-3", "kalite", 40.0, "GECERLI")])
    tablo = dg.konum(esit, None, "AV-2")
    assert tablo[tablo["sutun"] == "kalite"].iloc[0]["yuzdelik"] == 100.0
    assert all(pd.isna(deger) for deger in yer("AV-2", "kalite"))  # puanı yok
    assert set(dg.konum(puan, None, "AV-1")["sutun"]) == {"tahsilat", "kalite"}


def _k1(satirlar):
    return pd.DataFrame(satirlar, columns=["seviye", "sure_gun", "en_yuksek_seviye"])


def _kutu_satirlari(tablo):
    return tablo[tablo["tur"] == "KUTU"]


def test_ilk_islem_suresi_kutulari_ve_kuyruk():
    k1 = _k1([("KAPANDI", 0, None), ("KAPANDI", 4, None), ("KAPANDI", 12, "SARI"),
              ("KAPANDI", 24, "TURUNCU"), ("IZLENIYOR", 3, None), ("SONLANDI", 40, "KIRMIZI")])
    tablo = ds.k1_sure(k1)
    assert list(tablo.columns) == ds.SUTUNLAR
    # Eşik sütunu olmayan (eski) tabloda yalnız kutular var.
    assert set(tablo["tur"]) == {"KUTU"}
    # Yalnız kapanan dönemler; kutu 5 gün; her kutuda görülen her bayrak satırı var.
    assert set(tablo["bayrak"]) == {"YOK", "SARI", "TURUNCU"}
    sayim = tablo[tablo["adet"] > 0].set_index(["alt", "bayrak"])["adet"].to_dict()
    assert sayim == {(0, "YOK"): 2, (10, "SARI"): 1, (20, "TURUNCU"): 1}
    assert set(tablo["toplam"]) == {4} and set(tablo["ortanca"]) == {8.0}
    assert sorted(set(tablo["alt"])) == [0, 5, 10, 15, 20] and set(tablo["ust"]) == {
        5, 10, 15, 20, 25}
    # Uzun kuyruk 20. kutuda toplanır, üst sınırı açıktır.
    uzun = ds.k1_sure(_k1([("KAPANDI", 3, None), ("KAPANDI", 300, "KIRMIZI")]))
    son = uzun[uzun["alt"] == uzun["alt"].max()]
    assert uzun["alt"].max() == 95 and son["ust"].isna().all()
    assert son.set_index("bayrak")["adet"].to_dict() == {"KIRMIZI": 1, "YOK": 0}
    # Tam sınırda biten süre (20 kutuya sığan) açık uçlu değildir.
    sinir = ds.k1_sure(_k1([("KAPANDI", 99, None)]))
    assert sinir["alt"].max() == 95 and sinir["ust"].max() == 100
    assert ds.k1_sure(_k1([("IZLENIYOR", 3, None)])) is None and ds.k1_sure(None) is None
    # Sütunu taşımayan eski tabloda bayrak "yok" sayılır.
    eski = ds.k1_sure(pd.DataFrame({"seviye": ["KAPANDI"], "sure_gun": [7]}))
    assert set(eski["bayrak"]) == {"YOK"}


def test_ilk_islem_esikleri_sonuctan_ve_ay_kurali_aralik():
    # Oto 20. gün; oto dışı 2 takvim ayı (59-62 gün) tek aralık; uyarı her dönemde 10. gün.
    k1 = pd.DataFrame([("KAPANDI", 4, None, 10, 20), ("KAPANDI", 30, "TURUNCU", 10, 20),
                       ("KAPANDI", 15, "SARI", 10, 59), ("KAPANDI", 70, "TURUNCU", 10, 62),
                       ("KAPANDI", 40, "SARI", 10, 61), ("IZLENIYOR", 3, None, 10, 31)],
                      columns=["seviye", "sure_gun", "en_yuksek_seviye", "esik_gun_sari",
                               "esik_gun_turuncu"])
    esik = ds.k1_sure(k1)
    esik = esik[esik["tur"] == "ESIK"]
    assert esik[["bayrak", "alt", "ust"]].values.tolist() == [
        ["SARI", 10, 10], ["TURUNCU", 20, 20], ["TURUNCU", 59, 62]]  # açık dönemin 31'i sayılmaz
    # Eşik satırının adedi yoktur: ekranda gösterilmeyen alan üretilmez.
    assert esik["adet"].isna().all()
    assert _kutu_satirlari(ds.k1_sure(k1))["adet"].sum() == 5
    # Aralık sınırı: 3 günden uzak değerler ayrı eşiktir.
    ayri = ds.k1_sure(k1.assign(esik_gun_turuncu=[20, 20, 24, 24, 24, 0]))
    ayri = ayri[(ayri["tur"] == "ESIK") & (ayri["bayrak"] == "TURUNCU")]
    assert ayri[["alt", "ust"]].values.tolist() == [[20, 20], [24, 24]]
    bitisik = ds.k1_sure(k1.assign(esik_gun_turuncu=[20, 20, 23, 23, 23, 0]))
    bitisik = bitisik[(bitisik["tur"] == "ESIK") & (bitisik["bayrak"] == "TURUNCU")]
    assert bitisik[["alt", "ust"]].values.tolist() == [[20, 23]]


def test_brans_oran_kutulari_ceyrek_biyik_ve_aykiri():
    # TRAFIK: beş yeterli avukat (biri aykırı), biri tabanın altında; KASKO: yalnız tabanın altı.
    satirlar = [("AV-1", "TRAFIK", 0.8, True), ("AV-2", "TRAFIK", 0.9, True),
                ("AV-3", "TRAFIK", 1.0, True), ("AV-4", "TRAFIK", 1.1, True),
                ("AV-5", "TRAFIK", 3.0, True), ("AV-6", "TRAFIK", 9.0, False),
                ("AV-1", "KASKO", 1.2, False), ("AV-2", "YANGIN", None, True)]
    brans = pd.DataFrame(satirlar, columns=["avukat_kodu", "brans", "oran", "yeterli"])
    tablo = db.oran_kutulari(brans)
    assert list(tablo.columns) == db.SUTUNLAR
    kutu = tablo[tablo["tur"] == "KUTU"].set_index("brans")
    assert list(kutu.index) == ["TRAFIK", "KASKO", "YANGIN"]  # sayılan avukat çoktan aza
    trafik = kutu.loc["TRAFIK"]
    assert trafik["adet"] == 5 and trafik["disarida"] == 1
    assert (trafik["ceyrek_alt"], trafik["ortanca"], trafik["ceyrek_ust"]) == (0.9, 1.0, 1.1)
    # Tukey: 1,1 + 1,5 × 0,2 = 1,4; 3,0 bıyığın dışında, aykırıdır.
    assert (trafik["biyik_alt"], trafik["biyik_ust"]) == (0.8, 1.1)
    aykiri = tablo[tablo["tur"] == "AYKIRI"]
    assert aykiri[["brans", "avukat_kodu", "oran"]].values.tolist() == [["TRAFIK", "AV-5", 3.0]]
    # Tabanın altındaki ve oranı olmayan satır sayılmaz; kutu boş kalır.
    assert kutu.loc["KASKO", "adet"] == 0 and pd.isna(kutu.loc["KASKO", "ortanca"])
    assert kutu.loc["KASKO", "disarida"] == 1 and kutu.loc["YANGIN", "disarida"] == 1
    assert db.oran_kutulari(None) is None
    assert db.oran_kutulari(brans.drop(columns="yeterli")) is None  # eski biçim



def test_brans_kutusu_ara_degerli_ceyrekler_ve_tukey_siniri():
    # Yedi oran: çeyrekler veri noktası değil, doğrusal ara değer (1,3 ve 1,9; en yakın değer
    # 1,4 ve 1,8 verirdi). Açıklık 0,6: üst sınır 1,9 + 1,5 × 0,6 = 2,8; 2,9 aykırıdır (Tukey
    # katsayısı 3 olsaydı sınır 3,7 olur, 2,9 bıyığa girerdi).
    oranlar = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.9]
    brans = pd.DataFrame([("AV-{}".format(i), "TRAFIK", oran, True)
                          for i, oran in enumerate(oranlar, 1)],
                         columns=["avukat_kodu", "brans", "oran", "yeterli"])
    tablo = db.oran_kutulari(brans)
    kutu = tablo[tablo["tur"] == "KUTU"].iloc[0]
    assert abs(kutu["ceyrek_alt"] - 1.3) < 1e-9 and abs(kutu["ceyrek_ust"] - 1.9) < 1e-9
    assert abs(kutu["ortanca"] - 1.6) < 1e-9 and kutu["adet"] == 7
    assert (kutu["biyik_alt"], kutu["biyik_ust"]) == (1.0, 2.0)
    aykiri = tablo[tablo["tur"] == "AYKIRI"]
    assert aykiri[["avukat_kodu", "oran"]].values.tolist() == [["AV-7", 2.9]]


def test_ilk_islem_suresi_kurala_gore_ayri_sayilir():
    # Oto (20. gün) ve oto dışı (takvim ayı) dönemleri ayrı kutularda ve ayrı eşiklerle sayılır.
    k1 = pd.DataFrame([("KAPANDI", 4, None, "OTO", 10, 20),
                       ("KAPANDI", 24, "TURUNCU", "OTO", 10, 20),
                       ("KAPANDI", 40, "SARI", "OTO_DISI", 10, 61),
                       ("KAPANDI", 3, None, "OTO_DISI", 10, 59),
                       ("KAPANDI", 70, "TURUNCU", "OTO_DISI", 10, 62)],
                      columns=["seviye", "sure_gun", "en_yuksek_seviye", "esik_kurali",
                               "esik_gun_sari", "esik_gun_turuncu"])
    tablo = ds.k1_sure(k1)
    assert list(tablo["kural"].drop_duplicates()) == ["OTO", "OTO_DISI"]  # oto önce
    oto, disi = (tablo[tablo["kural"] == ad] for ad in ("OTO", "OTO_DISI"))
    assert set(oto["toplam"]) == {2} and set(disi["toplam"]) == {3}
    assert set(oto["ortanca"]) == {14.0} and set(disi["ortanca"]) == {40.0}
    kutu = oto[oto["tur"] == "KUTU"]
    assert kutu["adet"].sum() == 2 and kutu["alt"].max() == 20  # oto kuyruğu kendi kutularında
    esik = disi[disi["tur"] == "ESIK"][["bayrak", "alt", "ust"]].values.tolist()
    assert esik == [["SARI", 10, 10], ["TURUNCU", 59, 62]]
    assert oto[oto["tur"] == "ESIK"][["bayrak", "alt", "ust"]].values.tolist() == [
        ["SARI", 10, 10], ["TURUNCU", 20, 20]]
