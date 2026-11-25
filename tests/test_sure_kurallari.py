"""Süre sütununun gözlem, kapsam ve açıklama kuralları.

Kesit 19.11.2026. Her test, düzeltme öncesi kodda yanlış sonucu veren bir senaryodur.
"""
import pandas as pd

from avukat_perf import (aciklama, agirlik, gozlem, hazirlik, kriter1, kriter2, sure_ozet,
                         sure_puani)
from avukat_perf.params import dogrula
from hat import hesap_sure
from yardimci import atama_tablosu, dort_sutunlu, params_yukle

KESIT = "2026-11-19"


def _dosya(kod, bakiye):
    return pd.DataFrame({"dosya_no": ["D-1"], "brans": ["TRAFIK"], "rucu_kodu": [kod],
                         "acik_bakiye": [bakiye]})


def test_arsiv_oncesi_kalkan_kosul_yeniden_acilsa_da_kaliciydi():
    """Arşivin ilk gecesinde dosya zaten kapalı (R06, bakiye 0): kayıp günü bilinmiyor. Dosya sonra
    R11'e ve pozitif bakiyeye döner. 'İlk kalkış kalıcıdır' kuralı tarihsiz kayba da uygulanır:
    iki avukat da KOSUL_SAGLANMIYOR, düşüm yok. Önceden kayıp hiç olmamış sayılıyor, sonraki avukat
    KIRMIZI ve düşüm alıyordu; aynı geçmiş kesit dosyanın sonraki durumuna göre değişiyordu."""
    k2 = params_yukle()["kriter2"]
    kosul = gozlem.guncelle(None, hazirlik.kosul_goruntusu(_dosya("R06", 0.0), k2), "dosya_no",
                            "kosul_kayip", "2025-01-10")
    assert kosul["tarih_bilinmiyor"].iloc[0] and pd.isna(kosul["ilk_tarih"].iloc[0])
    goruntu = pd.DataFrame({"dosya_no": ["D-1"], "surec_turu": ["ITIRAZ"],
                            "baslangic_tarihi": ["2025-05-01"]})
    atamalar = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2025-05-01", "2026-03-01",
                               "YENIDEN_ATAMA"), ("D-1", "AV-2", "TRAFIK", "2026-03-01")])
    sonuclar = {}
    for kod, bakiye in (("R06", 0.0), ("R11", 5000.0)):
        surec = hazirlik.k2_surecleri(goruntu, _dosya(kod, bakiye), None, kosul, None)
        assert surec["kosul_gorulme"].iloc[0] == pd.Timestamp("2025-01-10")
        for kesit in ("2026-02-01", KESIT):
            sonuc = kriter2.degerlendir(atamalar, surec, kesit, params_yukle())
            sonuclar[(kod, kesit)] = sonuc[["avukat_kodu", "seviye", "kapsam_disi_nedeni",
                                            "dusum"]].values.tolist()
    for kesit in ("2026-02-01", KESIT):
        assert sonuclar[("R06", kesit)] == sonuclar[("R11", kesit)], kesit
    assert all(satir[1:] == ["KAPSAM_DISI", "KOSUL_SAGLANMIYOR", False]
               for satir in sonuclar[("R11", KESIT)])


def test_dosya_tablosunda_olmayan_dosyanin_donemi_olculmez():
    """Atama logunda olup dosya tablosunda olmayan oto dosyası: branş boş. Önceden oto dışı
    eşikle (2 ay) ölçülüyor, düşümü süre özetinde ve e-posta listesinde görünüyor ama süre
    puanından sessizce düşüyordu (ekranla puan tutmuyordu)."""
    dosya = pd.DataFrame({"dosya_no": ["D-1"], "brans": ["TRAFIK"]})
    donem = atama_tablosu([("D-1", "AV-1", "TRAFIK", "2026-01-05"),
                           ("D-X", "AV-1", "TRAFIK", "2026-01-05")]).drop(columns="brans")
    esas = pd.DataFrame({"dosya_no": [], "esas_ilk_giris": []})
    k1 = kriter1.degerlendir(hazirlik.k1_atamalari(donem, dosya), esas, None, KESIT,
                             params_yukle()).set_index("dosya_no")
    assert k1.loc["D-X", "seviye"] == "KAPSAM_DISI"
    assert k1.loc["D-X", "kapsam_disi_nedeni"] == "DOSYA_YOK" and not k1.loc["D-X", "dusum"]
    assert k1.loc["D-1", "esik_kurali"] == "OTO" and k1.loc["D-1", "dusum"]
    # Değişmez kural: süre puanındaki düşüm sayısı süre özetindekiyle aynıdır.
    params = params_yukle()
    params["uyari"]["golge_mod"] = False
    k1 = k1.reset_index()
    girdi = hesap_sure.sure_girdisi(k1, None)
    kapsam = sure_puani.kapsam_hesapla(k1, KESIT, 12)
    puan = sure_puani.puanla(girdi, kapsam, KESIT, params)
    ozet = sure_ozet.ozet(girdi, KESIT, 12)
    assert int(puan["o"].sum()) == int(ozet["dusum_sayisi"].sum()) == 1
    # Ölçülmeyen dönem kapsamın paydasına girmez.
    assert kapsam.set_index("avukat_kodu")["kapsam"].to_dict() == {"AV-1": 1.0}


def test_kapsamda_dosya_yok_donemi_sayilmaz():
    k1 = pd.DataFrame({"avukat_kodu": ["AV-1"] * 5, "atama_tarihi": ["2026-01-01"] * 5,
                       "kapsam_disi_nedeni": [None, None, None, "ESAS_TARIHI_BILINMIYOR",
                                              "DOSYA_YOK"]})
    kapsam = sure_puani.kapsam_hesapla(k1, KESIT, 12)
    assert kapsam.to_dict("records") == [{"avukat_kodu": "AV-1", "kapsam": 0.75}]


def test_kaynak_tarihi_onceki_cekim_gunune_esitse_baslangic_odur():
    """Değer D günü 02:00 çekiminden sonra girilir, D+1 gecesi görülür, kaynak tarihi D'dir (en
    olağan durum). Önceden saklanan veride 'kaynak tarihi' ile 'önceki çekim günü' ayırt
    edilemiyor, başlangıç bir gün geç (ilk görülme) alınıyordu."""
    goruntu = pd.DataFrame({"dosya_no": ["D-1", "D-2"], "esas_no": ["2026/1", "2026/2"],
                            "kaynak": ["2026-01-10", None]})
    tablo = gozlem.guncelle(None, goruntu, "dosya_no", "esas_no", "2026-01-11", "2026-01-10",
                            "kaynak")
    assert list(tablo["dayanak"]) == ["KAYNAK_TARIHI", "GECELIK_GOZLEM"]
    baslangic = gozlem.baslangic_esle(tablo)
    assert baslangic["D-1"] == pd.Timestamp("2026-01-10")
    assert baslangic["D-2"] == pd.Timestamp("2026-01-11")  # kaynak yok: en geç olası gün
    assert gozlem.tarih_esle(tablo)["D-2"] == pd.Timestamp("2026-01-10")


def test_tarih_bilinmiyor_isareti_ilk_tarihten_turetilir():
    """Saklanan işaret metin ya da boş gelirse (eski Dataiku okuma yolu) astype(bool) 'false'
    metnini True yapıyordu: kesitten sonra girilmiş esasın dönemi ölçülmüyordu."""
    tablo = pd.DataFrame({"anahtar": ["D-1", "D-2", "D-3"],
                          "ilk_tarih": ["2026-01-10", None, "2026-02-01"],
                          "ilk_gorulme": ["2026-01-11", "2025-01-10", "2026-02-02"],
                          "tarih_bilinmiyor": ["false", "true", None]})
    esas = hazirlik.k1_esaslari(tablo)
    assert list(esas["tarih_bilinmiyor"]) == [False, True, False]
    assert list(gozlem.bilinmeyen_esle(tablo).index) == ["D-2"]


def test_sure_aciklamasinda_yeterli_veri_uyarisi():
    sure = pd.DataFrame([("AV-1", 30, 8, 2, 3.0, 1.0, 12 / 13, 78.85, None, "GECERLI", False)],
                        columns=["avukat_kodu", "risk_donemi", "risk_dosya", "o", "e", "kapsam",
                                 "r", "puan", "eksik_nedeni", "durum", "yeterli"])
    satirlar = aciklama.uret(params_yukle(), sure=sure)
    turler = list(satirlar["tur"])
    assert turler.count("UYARI") == 1 and "HESAP" in turler and "ISTISNA" not in turler
    uyari = satirlar[satirlar["tur"] == "UYARI"]["metin"].iloc[0]
    assert uyari.startswith("Yeterli veri yok: risk altındaki dönemlerde 8 dosya, en az 10")
    yeterli = aciklama.uret(params_yukle(), sure=sure.assign(yeterli=True))
    assert "UYARI" not in set(yeterli["tur"])


def test_sutun_agirliklari_35_30_25_10_ve_tutarli():
    """Süre dahil 35 / 30 / 25 / 10; ilk fazda (varsayılan, Süre girmez) 50 / 0 / 36 / 14."""
    params = dort_sutunlu()
    assert agirlik.sutun_agirliklari(params) == {"tahsilat": 0.35, "sure": 0.3, "kalite": 0.25,
                                                 "davranis": 0.1}
    assert agirlik.sutun_agirliklari(params_yukle()) == {"tahsilat": 0.5, "sure": 0.0,
                                                         "kalite": 0.36, "davranis": 0.14}
    assert agirlik.ham_agirliklar(params["agirliklar"])[1] < 0.01
    assert "agirliklar" in params["_teyit_bekleyen"]


def test_kapanis_kodlari_dogrulanir():
    params = params_yukle()
    assert dogrula(params) == []
    for deger in (["R06", "R11"], ["R06", ""], ["R06", 12]):
        bozuk = params_yukle()
        bozuk["kriter2"]["kapanis_kodlari"] = deger
        assert dogrula(bozuk) == ["kriter2.kapanis_kodlari boş olmayan metin listesi olmalı, "
                                  "rucu_kodu'nu içeremez"], deger
    bos = params_yukle()
    bos["kriter2"]["kapanis_kodlari"] = []
    assert dogrula(bos) == []


def _k2_tek(kod, bakiye, atamalar, kosul=None):
    goruntu = pd.DataFrame({"dosya_no": ["D-1"], "surec_turu": ["ITIRAZ"],
                            "baslangic_tarihi": ["2025-02-01"]})
    surec = hazirlik.k2_surecleri(goruntu, _dosya(kod, bakiye), None, kosul, None)
    sonuc = kriter2.degerlendir(atama_tablosu(atamalar), surec, KESIT, params_yukle())
    return sonuc[["avukat_kodu", "seviye", "kapsam_disi_nedeni", "dusum"]].values.tolist()


def test_iade_sonrasi_kapanis_disi_kod_olusmus_k2_dusumunu_silmez():
    """AV-1 düşüm aldıktan sonra (01.08.2025) dosya iade edilir (01.12.2025) ve kapanış dışı bir
    koda (R10) geçer; koşul gözlemi bunu kapanış saymaz. Sona ermiş dönem bitişine kadar ölçülür,
    oluşmuş düşüm korunur (sonlanan_atamada_dusum_korunur). Denetim öncesi kodda 'koşul bugün
    sağlanmıyor ve günü bilinmiyor' kuralıyla dönem KOSUL_SAGLANMIYOR olup düşüm siliniyordu."""
    k2, kosul, onceki = params_yukle()["kriter2"], None, None
    for gece in pd.date_range("2025-01-01", "2026-11-01", freq="MS"):
        kod = "R11" if gece < pd.Timestamp("2025-12-01") else "R10"
        kosul = gozlem.guncelle(kosul, hazirlik.kosul_goruntusu(_dosya(kod, 5000.0), k2),
                                "dosya_no", "kosul_kayip", str(gece.date()), onceki)
        onceki = str(gece.date())
    assert kosul.empty
    iade = [("D-1", "AV-1", "TRAFIK", "2025-01-15", "2025-12-01", "IADE")]
    assert _k2_tek("R10", 5000.0, iade, kosul) == [["AV-1", "SONLANDI", None, True]]
    # Sürmekte olan dönem: dosya bugün R11 değil, uyarı ve düşüm üretilmez.
    surer = [("D-1", "AV-1", "TRAFIK", "2025-01-15")]
    assert _k2_tek("R10", 5000.0, surer) == [["AV-1", "KAPSAM_DISI", "KOSUL_SAGLANMIYOR", False]]
    # Kapanış (kapanış kodu, R11'de sıfır bakiye) ve boş kod sona ermiş dönemde de kapsam dışı:
    # günü bilinmiyor (gözlem yok).
    for kod, bakiye in (("R06", 5000.0), ("R11", 0.0), (None, 5000.0)):
        assert _k2_tek(kod, bakiye, iade) == [
            ["AV-1", "KAPSAM_DISI", "KOSUL_SAGLANMIYOR", False]], kod
