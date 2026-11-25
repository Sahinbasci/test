"""Veri hattının saf modülleri: kalite kapısı, gözlem, veri hazırlığı, dönem yayını."""
import pandas as pd

from avukat_perf import donem, gozlem, hazirlik, kalite, kalite_iliski, kriter1, sema
from yardimci import esas_tablosu, params_yukle

KESIT = "2026-11-19"
K2 = params_yukle()["kriter2"]


def _durum(sonuc, kontrol):
    return sonuc.set_index("kontrol").loc[kontrol, "durum"]


def _dosya(satirlar):
    return pd.DataFrame(satirlar, columns=sema.alanlar("dosya"))


def test_kalite_gecen_tablo_turleri_cevirir():
    tablo = _dosya([(123.0, "TRAFIK", "R11", 1.234, 500, "2025-01-01"),
                    ("D-2", "KASKO", "R06", 2000, None, "2025-02-01")])
    temiz, sonuc = kalite.denetle("dosya", tablo.assign(fazla=1), KESIT, params_yukle())
    assert kalite.karar(sonuc) == "GECTI" and list(temiz.columns) == sema.alanlar("dosya")
    # Sayı olarak gelen 1.234 Türkçe biçim sayılmaz; yalnız metin denetlenir.
    assert _durum(sonuc, "SAYI_BICIMI:rucu_tutari") == "GECTI"
    # "15.000" sayi_bicimi tr verilmeden 15,0 okunurdu: kapı durdurur.
    _, yerel = kalite.denetle("dosya", tablo.assign(rucu_tutari=["15.000", "2.000,50"]), KESIT,
                              params_yukle())
    assert _durum(yerel, "SAYI_BICIMI:rucu_tutari") == "KALDI"
    assert list(temiz["dosya_no"]) == ["123", "D-2"]
    assert temiz["rucu_tutari"].iloc[1] == 2000.0
    assert str(temiz["rucuya_verilis_tarihi"].dtype) == "datetime64[ns]"
    # string türündeki gün.ay.yıl tarih de kapıda durur (ay-gün ters okunmaz).
    metin = tablo.assign(rucuya_verilis_tarihi=pd.Series(["11.05.2025", "2025-02-01"],
                                                         dtype="string"))
    _, ters = kalite.denetle("dosya", metin, KESIT, params_yukle())
    assert _durum(ters, "TUR:rucuya_verilis_tarihi") == "KALDI" and kalite.karar(ters) == "KALDI"


def test_kalite_kaldigi_durumlar():
    params = params_yukle()
    eksik = _dosya([("D-1", "TRAFIK", "R11", 1.0, 1.0, "2025-01-01")]).drop(columns="brans")
    temiz, sonuc = kalite.denetle("dosya", eksik, KESIT, params)
    assert temiz is None and kalite.karar(sonuc) == "KALDI"
    bozuk = _dosya([("D-1", "TRAFIK", "R11", "bin", 1.0, "2025-01-01"),
                    ("D-1", "TRAFIK", "R11", 1.0, 1.0, "tarih değil"),
                    (None, "TRAFIK", "R11", 1.0, 1.0, "2027-01-01")])
    _, sonuc = kalite.denetle("dosya", bozuk, KESIT, dict(params, kalite=dict(
        params["kalite"], sapma_en_az_satir=10)), onceki_satir=10)
    assert _durum(sonuc, "TUR:rucu_tutari") == "KALDI"
    assert _durum(sonuc, "TUR:rucuya_verilis_tarihi") == "KALDI"
    assert _durum(sonuc, "BOS:dosya_no") == "KALDI" and _durum(sonuc, "YINELENEN") == "KALDI"
    assert _durum(sonuc, "GELECEK_TARIH:rucuya_verilis_tarihi") == "UYARI"
    assert _durum(sonuc, "SATIR_SAPMASI") == "KALDI"
    _, bos = kalite.denetle("dosya", _dosya([]), KESIT, params)
    assert _durum(bos, "BOS_TABLO") == "KALDI"
    # İsteğe bağlı kaynakta boş tablo ve küçük tablodaki sapma geceyi durdurmaz.
    bekleme = pd.DataFrame([
        ("D-1", "AV-1", "2026-01-01", None), ("D-2", "AV-1", "2026-01-01", None)],
        columns=sema.alanlar("bekleme"))
    _, kucuk = kalite.denetle("bekleme", bekleme, KESIT, params, onceki_satir=1)
    assert kalite.karar(kucuk) == "GECTI" and "SATIR_SAPMASI" not in set(kucuk["kontrol"])
    _, bos = kalite.denetle("bekleme", bekleme.iloc[:0], KESIT, params)
    assert _durum(bos, "BOS_TABLO") == "UYARI"


def test_kalite_iliski_ve_mutabakat():
    params = params_yukle()
    ana = pd.DataFrame({"dosya_no": ["D-1"]})
    assert kalite_iliski.iliski("ATAMA_DOSYA", ana, pd.DataFrame({"dosya_no": ["D-1", "D-9"]}))[
        "durum"].iloc[0] == "UYARI"
    # Hiçbiri eşleşmiyorsa anahtar biçimi farklıdır (D-000001 / D000001): gece durur.
    assert kalite_iliski.iliski("ATAMA_DOSYA", ana, pd.DataFrame({"dosya_no": ["D1", "D9"]}))[
        "durum"].iloc[0] == "KALDI"
    hareket = pd.DataFrame({"hareket_tarihi": ["2026-10-01", "2026-10-15", "2026-09-01"],
                            "tutar": [100.0, 50.0, 10.0]})
    rapor = pd.DataFrame({"avukat_kodu": ["AV-1", "AV-2", "AV-1"],
                          "donem": ["2026-10", "2026-10", "2026-09"],
                          "tahsilat_toplami": [100.0, 50.0, 20.0]})
    sonuc = kalite_iliski.mutabakat(hareket, rapor, params).set_index("kontrol")["durum"]
    assert sonuc.to_dict() == {"TAHSILAT:2026-09": "KALDI", "TAHSILAT:2026-10": "GECTI"}


def _goruntu(satirlar):
    return pd.DataFrame(satirlar, columns=["dosya_no", "esas_no", "kaynak_tarihi"])


def test_gozlem_ilk_gorulme_ve_degismezlik():
    ilk = gozlem.guncelle(None, _goruntu([("D-1", "2026/1", "2026-01-05"),
                                          ("D-2", None, None), ("D-3", "2026/9", None)]),
                          "dosya_no", "esas_no", "2026-03-01", None, "kaynak_tarihi")
    assert list(ilk["anahtar"]) == ["D-1", "D-3"] and set(ilk["dayanak"]) == {"ARSIV_ONCESI"}
    assert list(ilk["tarih_bilinmiyor"]) == [False, True]
    # İlk çekimde kaynak tarihi çekimden sonraysa (kaynakta hatalı tarih) tarih bilinmiyor sayılır.
    gelecek = gozlem.guncelle(None, _goruntu([("D-9", "x", "2026-03-05")]), "dosya_no",
                              "esas_no", "2026-03-01", None, "kaynak_tarihi")
    assert gelecek["tarih_bilinmiyor"].iloc[0] and pd.isna(gelecek["ilk_tarih"].iloc[0])
    ikinci = gozlem.guncelle(ilk, _goruntu([("D-1", "2026/1-DÜZELTİLDİ", None),
                                            ("D-2", "2026/5", "2026-02-20"),
                                            ("D-4", " ", None)]),
                             "dosya_no", "esas_no", "2026-03-04", "2026-03-01", "kaynak_tarihi")
    yeni = ikinci.set_index("anahtar")
    assert list(yeni.index) == ["D-1", "D-3", "D-2"]
    assert yeni.loc["D-1", "ilk_deger"] == "2026/1"
    # Kaynak tarihi aralık dışında: en erken olası gün önceki çekimin kendi günüdür (02:00'dan
    # sonra girilmiş olabilir).
    assert yeni.loc["D-2", "ilk_tarih"] == pd.Timestamp("2026-03-01")
    ayni = gozlem.guncelle(ikinci, _goruntu([("D-2", "2026/5", None)]), "dosya_no", "esas_no",
                           "2026-03-04", "2026-03-01")
    assert len(ayni) == 3


def test_gozlem_kaynak_tarihi_aralikta_ise_kullanilir():
    tablo = gozlem.guncelle(None, _goruntu([("D-1", "x", "2026-03-03")]), "dosya_no",
                            "esas_no", "2026-03-04", "2026-03-01", "kaynak_tarihi")
    assert tablo["ilk_tarih"].iloc[0] == pd.Timestamp("2026-03-03")
    # Önceki çekim günü girilen değerin kaynak tarihi (en sık durum) kabul edilir.
    ayni_gun = gozlem.guncelle(None, _goruntu([("D-1", "x", "2026-03-01")]), "dosya_no",
                               "esas_no", "2026-03-02", "2026-03-01", "kaynak_tarihi")
    assert ayni_gun["ilk_tarih"].iloc[0] == pd.Timestamp("2026-03-01")


def _log(satirlar):
    return pd.DataFrame(satirlar, columns=sema.alanlar("atama_log")).assign(
        atama_tarihi=lambda t: pd.to_datetime(t["atama_tarihi"]),
        iptal_tarihi=lambda t: pd.to_datetime(t["iptal_tarihi"]))


def test_atama_donemleri_bitis_ve_neden():
    log = _log([("D-1", "SL-1", "2025-01-02", None, "AT1", "1", "N"),
                ("D-1", "AV-1", "2026-01-01", None, "AT2", "1", "N"),
                ("D-1", "AV-2", "2026-03-01", "2026-02-20", "AT3", "1", "N"),
                ("D-1", "AV-3", "2026-05-01", None, "AT4", "1", "N"),
                ("D-2", "AV-1", "2026-01-01", "2026-02-01", "AT5", "1", "N")])
    hz = dict(params_yukle()["hazirlik"], sulh_avukat_kodlari=["SL-1"])
    tablo = hazirlik.atama_donemleri(log, hz).set_index(["dosya_no", "avukat_kodu"])
    assert tablo.loc[("D-1", "SL-1"), "atama_turu"] == "SULH"
    assert tablo.loc[("D-1", "AV-1"), "bitis_tarihi"] == pd.Timestamp("2026-03-01")
    assert tablo.loc[("D-1", "AV-1"), "bitis_nedeni"] == "YENIDEN_ATAMA"
    # İptali atamadan önce olan kayıt boş dönemdir (dosyayı hiç tutmadı): çıkarılır.
    assert ("D-1", "AV-2") not in tablo.index
    assert pd.isna(tablo.loc[("D-1", "AV-3"), "bitis_tarihi"])
    assert tablo.loc[("D-2", "AV-1"), "bitis_nedeni"] == "IADE"
    hatali = hazirlik.atama_donemleri(log, dict(hz, iptal_yorumu="hatali_iptal"))
    assert hatali.set_index(["dosya_no", "avukat_kodu"]).loc[("D-2", "AV-1"),
                                                             "bitis_nedeni"] == "IPTAL"
    # Hatalı girilip ertesi gün iptal edilen atama, gerçek avukatın dönemini kesmez.
    yanlis = _log([("D-3", "AV-1", "2026-01-01", None, "AT6", "1", "N"),
                   ("D-3", "AV-2", "2026-03-01", "2026-03-02", "AT7", "1", "N")])
    yanlis = hazirlik.atama_donemleri(yanlis, dict(hz, iptal_yorumu="hatali_iptal"))
    yanlis = yanlis.set_index("avukat_kodu")
    assert pd.isna(yanlis.loc["AV-1", "bitis_tarihi"])
    assert yanlis.loc["AV-2", "bitis_nedeni"] == "IPTAL"
    # Aynı gün iptal edilip yeniden girilen atama: iptal edilen boş dönemdir, avukatın dönemi
    # yeniden girilen kayıttan sürer. Kayıtların geliş sırası sonucu değiştirmez.
    tekrar = [("D-4", "AV-1", "2026-01-01", None, "AT9", "1", "N"),
              ("D-4", "AV-1", "2026-01-01", "2026-01-01", "AT8", "1", "N")]
    for sira in (tekrar, tekrar[::-1]):
        donem = hazirlik.atama_donemleri(_log(sira), hz)
        assert len(donem) == 1 and donem["atama_ref"].iloc[0] == "AT9"
        assert pd.isna(donem["bitis_tarihi"].iloc[0])
    alan = hazirlik.atama_donemleri(log, dict(hz, sulh_avukat_kodlari=[], sulh_alani="atama_ref",
                                              sulh_degerleri=["AT1"]))
    assert list(alan["atama_turu"]).count("SULH") == 1


def test_ayni_avukata_kesintisiz_yeniden_atama_iki_kipte():
    # AV-1'e iki kez arka arkaya, araya sulh girerek bir kez daha; sonra AV-2 ve yine AV-1.
    log = _log([("D-1", "AV-1", "2026-01-01 09:00", None, "R1", "1", "N"),
                ("D-1", "AV-1", "2026-01-20 09:00", None, "R2", "1", "N"),
                ("D-1", "SL-1", "2026-02-01 09:00", None, "R3", "1", "N"),
                ("D-1", "AV-1", "2026-02-10 09:00", None, "R4", "1", "N"),
                ("D-1", "AV-2", "2026-03-01 09:00", None, "R5", "1", "N"),
                ("D-1", "AV-1", "2026-04-01 09:00", "2026-05-01", "R6", "1", "N"),
                ("D-2", "AV-1", "2026-01-01 09:00", "2026-01-10", "R7", "1", "N"),
                ("D-2", "AV-1", "2026-01-15 09:00", None, "R8", "1", "N")])
    hz = dict(params_yukle()["hazirlik"], sulh_avukat_kodlari=["SL-1"])
    yeni = hazirlik.atama_donemleri(log, dict(hz, ayni_avukata_yeniden_atama="yeni_donem"))
    assert list(yeni["atama_ref"]) == ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
    # Varsayılan surer: gereksinim süreyi yalnız başka avukata atamada yeniden başlatır.
    surer = hazirlik.atama_donemleri(log, hz)
    assert hz["ayni_avukata_yeniden_atama"] == "surer"
    # D-1: R1-R2-R4 tek dönem (sulh araya girmez), bitişi AV-2'nin ataması; AV-2'den sonraki
    # AV-1 ataması yeni dönemdir. D-2: iptalle biten ve aradan sonra gelen kayıt birleşmez.
    assert list(surer["atama_ref"]) == ["R1", "R3", "R5", "R6", "R7", "R8"]
    ilk = surer.set_index("atama_ref").loc["R1"]
    assert ilk["atama_tarihi"] == pd.Timestamp("2026-01-01")
    assert ilk["bitis_tarihi"] == pd.Timestamp("2026-03-01")
    assert ilk["bitis_nedeni"] == "YENIDEN_ATAMA"
    son = surer.set_index("atama_ref")
    assert son.loc["R6", "bitis_nedeni"] == "IADE" and pd.isna(son.loc["R8", "bitis_tarihi"])
    assert son.loc["R7", "bitis_tarihi"] == pd.Timestamp("2026-01-10")
    # Dönem en son kayıtta açık kalıyorsa birleşen dönem de açık kalır.
    acik = hazirlik.atama_donemleri(log[log["atama_ref"].isin(["R1", "R2"])],
                                    dict(hz, ayni_avukata_yeniden_atama="surer"))
    assert len(acik) == 1 and pd.isna(acik["bitis_tarihi"].iloc[0])
    assert pd.isna(acik["bitis_nedeni"].iloc[0])


def test_surer_kipinde_hatali_iptal_kaydi_donemi_kesmez():
    """hatali_iptal iken araya giren iptal edilmiş (hatalı) kayıt, aynı avukatın kesintisiz
    dönemini bölmez: tek dönem, tek düşüm. Önceden zincir iptal kaydında
    kırılıyor, AV-1'e iki dönem ve iki düşüm yazılıyordu."""
    log = _log([("D-1", "AV-1", "2026-01-01 09:00", None, "R1", "1", "N"),
                ("D-1", "AV-2", "2026-01-10 09:00", "2026-01-12", "R2", "1", "N"),
                ("D-1", "AV-1", "2026-01-20 09:00", None, "R3", "1", "N")])
    hz = dict(params_yukle()["hazirlik"], iptal_yorumu="hatali_iptal")
    tablo = hazirlik.atama_donemleri(log, hz).set_index("atama_ref")
    assert list(tablo.index) == ["R1", "R2"]
    assert pd.isna(tablo.loc["R1", "bitis_tarihi"]) and pd.isna(tablo.loc["R1", "bitis_nedeni"])
    assert tablo.loc["R2", "bitis_nedeni"] == "IPTAL"
    k1 = kriter1.degerlendir(tablo.reset_index().assign(brans="TRAFIK"), esas_tablosu({}), None,
                             "2026-04-30", params_yukle())
    assert int(k1["dusum"].astype(bool).sum()) == 1


def test_kalite_davranis_genis_bicim_ve_tahsilat_turu():
    genis = pd.DataFrame({"avukat_kodu": ["AV-1"], "degerlendirme_tarihi": ["2026-06-01"],
                          "EskiAlanA": [4], "EskiAlanB": [None]})
    uzun = hazirlik.degerlendirme_uzun(genis, {"EskiAlanA": "dosyaya_hakimiyet",
                                       "EskiAlanB": "sorumluluk_alma"})
    assert list(uzun["alt_baslik"]) == ["dosyaya_hakimiyet", "sorumluluk_alma"]
    assert uzun["degerlendiren"].isna().all()
    hareket = pd.DataFrame({"hareket_turu": ["TAHSILAT", "MASRAF"], "tutar": [1.0, 2.0]})
    hz = params_yukle()["hazirlik"]
    assert len(hazirlik.tahsilat_hareketleri(hareket, hz)) == 2
    hz = dict(hz, tahsilat_hareket_turleri=["TAHSILAT"])
    assert list(hazirlik.tahsilat_hareketleri(hareket, hz)["tutar"]) == [1.0]


def test_k2_surecleri_gozlemden_kurulur():
    dosya = pd.DataFrame({"dosya_no": ["D-1", "D-2", "D-3"], "brans": ["TRAFIK", "KASKO", "YANGIN"],
                          "rucu_kodu": ["R11", "R06", "R11"], "acik_bakiye": [10.0, 0.0, 0.0]})
    # R11'de kalmış ama açık bakiyesi tam sıfır olan dosyada koşul kalkmıştır (belge 4. bölüm).
    kayip = hazirlik.kosul_goruntusu(dosya, K2).set_index("dosya_no")["kosul_kayip"]
    assert kayip.to_dict() == {"D-1": None, "D-2": "EVET", "D-3": "EVET"}
    kosul = gozlem.guncelle(None, hazirlik.kosul_goruntusu(dosya, K2), "dosya_no",
                            "kosul_kayip", "2026-03-01", "2026-02-27")
    esas = gozlem.guncelle(None, _goruntu([("D-2", "2025/1", None)]), "dosya_no", "esas_no",
                           "2026-01-10", "2026-01-05")
    k2 = pd.DataFrame({"dosya_no": ["D-1", "D-2"], "surec_turu": ["ITIRAZ", "ARABULUCULUK"],
                       "baslangic_tarihi": ["2026-01-01", None]})
    # D-1'in dava esası ilk çekimde zaten doluydu, tarihi bilinmiyor: ilk görüldüğü gün aktarılır.
    dava = gozlem.guncelle(None, pd.DataFrame({"dosya_no": ["D-1"], "dava_esas_no": ["2025/9"]}),
                           "dosya_no", "dava_esas_no", "2026-01-10")
    surec = hazirlik.k2_surecleri(k2, dosya, dava, kosul, esas).set_index("dosya_no")
    assert surec.loc["D-1", "dava_gorulme"] == pd.Timestamp("2026-01-10")
    assert pd.isna(surec.loc["D-1", "dava_ilk_giris"]) and pd.isna(surec.loc["D-2", "dava_gorulme"])
    assert pd.isna(surec.loc["D-1", "kosul_kayip_tarihi"])
    # Bitiş için en erken olası gün (önceki başarılı çekim); başlangıç için en geç olası gün
    # (değerin görüldüğü çekim günü): kaçan gece avukatın aleyhine işlemez.
    assert surec.loc["D-2", "kosul_kayip_tarihi"] == pd.Timestamp("2026-02-27")
    assert surec.loc["D-2", "baslangic_tarihi"] == pd.Timestamp("2026-01-10")
    assert list(surec.reset_index().columns) == list(hazirlik.SUREC_SUTUNLARI) + [
        "dava_gorulme", "kosul_gorulme"]


def test_k1_esaslari():
    esas = gozlem.guncelle(None, _goruntu([("D-1", "x", None)]), "dosya_no", "esas_no",
                           "2026-01-10")
    tablo = hazirlik.k1_esaslari(esas)
    assert tablo.to_dict("records")[0]["tarih_bilinmiyor"]
    assert tablo.to_dict("records")[0]["ilk_gorulme"] == pd.Timestamp("2026-01-10")
    assert hazirlik.k1_esaslari(None).empty


def _sutun(satirlar):
    return pd.DataFrame(satirlar, columns=["avukat_kodu", "puan", "durum"])


def test_donem_puan_tablosu_ve_kontroller():
    assert donem.kesit("2026-02") == pd.Timestamp("2026-02-28")
    tablo = donem.puan_tablosu("2026-10", {"tahsilat": _sutun([("AV-1", 80.0, "GECERLI")]),
                                           "kalite": _sutun([]), "davranis": None},
                               ["AV-1", "AV-2"])
    durum = tablo.set_index(["avukat_kodu", "sutun"])["durum"]
    assert durum[("AV-2", "tahsilat")] == "VERI_YOK"
    assert durum[("AV-1", "sure")] == "KAYNAK_BEKLENIYOR" and len(tablo) == 8
    assert kalite.karar(donem.sonuc_kontrolleri(tablo)) == "GECTI"
    teyit = donem.puan_tablosu("2026-10", {}, ["AV-1"], {"kalite": "TEYIT_BEKLIYOR"})
    assert teyit.set_index("sutun")["durum"].to_dict() == {
        "davranis": "KAYNAK_BEKLENIYOR", "kalite": "TEYIT_BEKLIYOR",
        "sure": "KAYNAK_BEKLENIYOR", "tahsilat": "KAYNAK_BEKLENIYOR"}
    bozuk = tablo.copy()
    bozuk.loc[0, ["durum", "puan"]] = ["GECERLI", 120.0]
    assert kalite.karar(donem.sonuc_kontrolleri(bozuk)) == "KALDI"


def test_donem_yayini_surumlu_ve_degismez():
    tablo = donem.puan_tablosu("2026-10", {"tahsilat": _sutun([("AV-1", 80.0, "GECERLI")])},
                               ["AV-1"])
    bilgi = {"calisma_kimligi": "C-1", "hesap_surumu": "h", "yayin_zamani": "z"}
    ilk, sonuc = donem.yayinla(None, tablo, "2026-10", bilgi)
    assert sonuc == "YENI" and set(ilk["yayin_surumu"]) == {1}
    ayni, sonuc = donem.yayinla(ilk, tablo, "2026-10", dict(bilgi, calisma_kimligi="C-2"))
    assert sonuc == "DEGISMEDI" and len(ayni) == len(ilk)
    duzeltme = tablo.assign(puan=tablo["puan"].fillna(0) + 1)
    iki, sonuc = donem.yayinla(ayni, duzeltme, "2026-10", bilgi)
    assert sonuc == "DUZELTME" and sorted(set(iki["yayin_surumu"])) == [1, 2]
    assert set(donem.son_surum(iki)["yayin_surumu"]) == {2}
    baska, sonuc = donem.yayinla(iki, tablo.assign(donem="2026-11"), "2026-11", bilgi)
    assert sonuc == "YENI" and len(donem.son_surum(baska)) == 8


def test_onceki_donem_ve_veri_kapsami():
    assert donem.onceki_donem("2026-11-01 06:00:00") == "2026-10"
    assert donem.onceki_donem("2026-01-15") == "2025-12"
    assert list(donem.veri_kapsami(None, "2026-10")["durum"]) == ["KALDI"]
    assert list(donem.veri_kapsami("2026-10-31", "2026-10")["durum"]) == ["KALDI"]
    assert list(donem.veri_kapsami("2026-11-01", "2026-10")["durum"]) == ["GECTI"]



def test_degerlendirmede_yinelenen_anahtar_uyaridir():
    # Değerlendirici alanı gelmeyebilir; aynı gün iki değerlendirme geceyi durdurmamalı.
    tablo = pd.DataFrame([("AV-1", "2026-06-01", "dosyaya_hakimiyet", 4, None)] * 2,
                         columns=sema.alanlar("degerlendirme"))
    _, sonuc = kalite.denetle("degerlendirme", tablo, KESIT, params_yukle())
    assert _durum(sonuc, "YINELENEN") == "UYARI" and kalite.karar(sonuc) == "GECTI"


def test_mutabakat_puana_giren_hareketlerle_yapilir():
    from hat import okuma
    params = params_yukle()
    params["hazirlik"]["tahsilat_hareket_turleri"] = ["TAHSILAT"]
    tablolar = {
        "dosya": _dosya([("D-1", "TRAFIK", "R11", 1000.0, 1.0, "2025-01-01")]),
        "atama_log": pd.DataFrame([("D-1", "AV-1", "2025-02-01", None, "1", None, None)],
                                  columns=sema.alanlar("atama_log")),
        "tahsilat_hareketi": pd.DataFrame([("D-1", "2026-10-05", 100.0, "TAHSILAT", "H1"),
                                           ("D-1", "2026-10-06", 40.0, "MASRAF", "H2")],
                                          columns=sema.alanlar("tahsilat_hareketi")),
        "rapor_avukat_toplam": pd.DataFrame([("AV-1", "2026-10", 100.0, None)],
                                            columns=sema.alanlar("rapor_avukat_toplam"))}
    sonuc = pd.concat(okuma.iliskiler(tablolar, params), ignore_index=True)
    assert _durum(sonuc, "TAHSILAT:2026-10") == "GECTI"  # masraf mutabakata girmez


def test_istege_bagli_sutun_eksikse_gece_durmaz_bos_metin_bos_sayilir():
    params = params_yukle()
    log = pd.DataFrame([("D-1", "AV-1", "2026-01-01 09:00:00", "")],
                       columns=["dosya_no", "avukat_kodu", "atama_tarihi", "iptal_tarihi"])
    temiz, sonuc = kalite.denetle("atama_log", log, KESIT, params)
    assert kalite.karar(sonuc) == "GECTI" and _durum(sonuc, "EKSIK_ALAN") == "UYARI"
    assert list(temiz.columns) == sema.alanlar("atama_log") and temiz["grup"].isna().all()
    assert temiz["iptal_tarihi"].isna().all()  # API'nin "" ile gönderdiği boş tarih
    _, eksik = kalite.denetle("atama_log", log.drop(columns="avukat_kodu"), KESIT, params)
    assert _durum(eksik, "ZORUNLU_SUTUN") == "KALDI"


def test_alan_anlami_denetimleri():
    params = params_yukle()
    log = pd.DataFrame([("D-1", "AV-1", "2026-01-10", "2026-01-05", "1", None, None),
                        ("D-2", "AV-1", "2026-01-10", "2026-01-10", "2", None, None)],
                       columns=sema.alanlar("atama_log"))
    _, sonuc = kalite.denetle("atama_log", log, KESIT, params)
    satir = sonuc.set_index("kontrol").loc["TERS_TARIH"]
    assert satir["durum"] == "UYARI" and satir["deger"] == 1  # aynı gün iptal sayılmaz
    bekleme = pd.DataFrame([("D-1", "AV-1", "2026-02-10", "2026-02-01")],
                           columns=sema.alanlar("bekleme"))
    assert _durum(kalite.denetle("bekleme", bekleme, KESIT, params)[1], "TERS_TARIH") == "KALDI"
    eski = _dosya([("D-1", "TRAFIK", "R11", 1.0, 1.0, "1900-01-01")])
    _, sonuc = kalite.denetle("dosya", eski, KESIT, params)
    assert _durum(sonuc, "ESKI_TARIH:rucuya_verilis_tarihi") == "KALDI"
    yazim = _dosya([("D-1", "Trafik", "R11", 1.0, 1.0, "2025-01-01")])
    # Bilinmeyen branş geceyi durdurur (oto eşiği ve olgunluk sessizce değişirdi).
    assert _durum(kalite.denetle("dosya", yazim, KESIT, params)[1], "DEGER:brans") == "KALDI"
    surec = pd.DataFrame([("D-1", "ARABULUCULUK ", None, None, None)],
                         columns=sema.alanlar("k2_goruntu"))
    _, sonuc = kalite.denetle("k2_goruntu", surec, KESIT, params)
    assert _durum(sonuc, "DEGER:surec_turu") == "GECTI"  # boşluk kapıda temizlenir
    _, sonuc = kalite.denetle("k2_goruntu", surec.assign(surec_turu="ARABULUCU"), KESIT, params)
    assert _durum(sonuc, "DEGER:surec_turu") == "UYARI"
    puan = pd.DataFrame([("AV-1", "2026-01-01", "eksik_hatali_islem", 7.0, "IA")],
                        columns=sema.alanlar("degerlendirme"))
    assert "OLCEK:puan" not in set(kalite.denetle("degerlendirme", puan, KESIT, params)[1][
        "kontrol"])  # ölçek teyit edilmeden denetlenmez
    params["kalite_davranis"]["olcek"] = {"en_dusuk": 1, "en_yuksek": 5}
    assert _durum(kalite.denetle("degerlendirme", puan, KESIT, params)[1], "OLCEK:puan") == "KALDI"


def test_ayni_gun_sulh_ve_normal_atama_hesabi_durdurmaz():
    from avukat_perf import atama
    from yardimci import atama_tablosu
    tablo = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-01-10", None, None, "SULH"),
                           ("D-1", "AV-1", "TRAFIK", "2026-01-10")])
    donem = atama.donemler(tablo, KESIT)
    assert len(donem) == 1 and donem["bitis_tarihi"].isna().all()


def test_turkce_sayi_yalniz_kaliba_uyan_metni_cevirir():
    from hat import kaynak
    seri = pd.Series(["1.234,56", "15.000", "99,5", "1234.56", "123.5", 1234.56, None])
    sonuc = kaynak._sayi(seri, "tr")
    assert list(sonuc[:3]) == [1234.56, 15000.0, 99.5]
    assert sonuc[3] == "1234.56" and sonuc[4] == "123.5"  # kalıba uymayan metin kapıya kalır
    assert sonuc[5] == 1234.56 and pd.isna(sonuc[6])


def test_mutabakat_donem_bicimleri_ve_kirilim():
    hareket = pd.DataFrame([("D-1", "2026-10-05", 100.0, None, None)],
                           columns=sema.alanlar("tahsilat_hareketi"))
    for donem in ("2026-10", "2026-10-01", "202610", "10.2026"):
        rapor = pd.DataFrame([("AV-1", donem, 60.0, "TRAFIK"), ("AV-1", donem, 40.0, "KASKO")],
                             columns=sema.alanlar("rapor_avukat_toplam"))
        sonuc = kalite_iliski.mutabakat(hareket, rapor, params_yukle())
        assert _durum(sonuc, "TAHSILAT:2026-10") == "GECTI", donem


def test_hareket_kimligi_verilmisse_tekil_olmali():
    tablo = pd.DataFrame([("D-1", "2026-10-05", 100.0, None, "H1"),
                          ("D-1", "2026-10-05", 100.0, None, "H1"),
                          ("D-2", "2026-10-05", 50.0, None, None),
                          ("D-2", "2026-10-05", 50.0, None, None)],
                         columns=sema.alanlar("tahsilat_hareketi"))
    _, sonuc = kalite.denetle("tahsilat_hareketi", tablo, KESIT, params_yukle())
    satir = sonuc.set_index("kontrol").loc["YINELENEN:hareket_no"]
    assert satir["durum"] == "KALDI" and satir["deger"] == 2  # kimliksiz satırlar sayılmaz


def test_r11_dosyada_bos_bakiye_uyaridir():
    dosya = _dosya([("D-1", "TRAFIK", "R11", 1.0, None, "2025-01-01"),
                    ("D-2", "TRAFIK", "R06", 1.0, None, "2025-01-01")])
    satir = kalite.denetle("dosya", dosya, KESIT, params_yukle())[1].set_index(
        "kontrol").loc["BOS_BAKIYE"]
    assert satir["durum"] == "UYARI" and satir["deger"] == 1


def test_sifir_rucu_tutari_uyari_negatif_tutar_kaldi():
    dosya = _dosya([("D-1", "TRAFIK", "R11", 0.0, 0.0, "2025-01-01"),
                    ("D-3", "TRAFIK", "R11", 1.0, 0.0, "2025-01-01")])
    gecen, sonuc = kalite.denetle("dosya", dosya, KESIT, params_yukle())
    satir = sonuc.set_index("kontrol").loc["SIFIR_RUCU"]
    assert satir["durum"] == "UYARI" and satir["deger"] == 1
    assert len(gecen) == 2 and kalite.karar(sonuc) == "GECTI"  # uyarı geceyi durdurmaz
    # Negatif tutarı tahsilat hesabı reddeder: kapı veri hatası olarak durdurur (önceden uyarıyla
    # geçip gece HESAP_HATASI ile düşüyordu).
    negatif = _dosya([("D-2", "TRAFIK", "R11", -5.0, 0.0, "2025-01-01"),
                      ("D-3", "TRAFIK", "R11", 1.0, 0.0, "2025-01-01")])
    _, sonuc = kalite.denetle("dosya", negatif, KESIT, params_yukle())
    satir = sonuc.set_index("kontrol").loc["NEGATIF_RUCU"]
    assert satir["durum"] == "KALDI" and satir["deger"] == 1 and kalite.karar(sonuc) == "KALDI"
    assert sonuc.set_index("kontrol").loc["SIFIR_RUCU"]["deger"] == 0


def test_ayni_gun_saatsiz_atamalar_uyari_verir():
    """Aynı dosyada aynı gün iki atama saatsiz gelirse (kaynak yalnız gün veriyor) sıra
    bilinmez: kapı SAATSIZ_ATAMA uyarısı verir. Saatli ya da tek atamada yok."""
    params = params_yukle()

    def deger(satirlar):
        tablo = pd.DataFrame([(no, av, at, None, str(sira), None, None)
                              for sira, (no, av, at) in enumerate(satirlar)],
                             columns=sema.alanlar("atama_log"))
        _, sonuc = kalite.denetle("atama_log", tablo, "2026-11-19", params)
        satir = sonuc.set_index("kontrol").loc["SAATSIZ_ATAMA"]
        return satir["deger"], satir["durum"]
    assert deger([("D-1", "AV-07", "2026-10-01"), ("D-1", "AV-03", "2026-10-01"),
                  ("D-2", "AV-01", "2026-10-01")]) == (2, "UYARI")
    assert deger([("D-1", "AV-07", "2026-10-01 09:00:00"),
                  ("D-1", "AV-03", "2026-10-01 15:00:00")]) == (0, "GECTI")
    assert deger([("D-1", "AV-07", "2026-10-01"), ("D-1", "AV-03", "2026-10-02"),
                  ("D-2", "AV-01", "2026-10-01")]) == (0, "GECTI")
