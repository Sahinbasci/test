"""Arayüzün sunum katmanı denetimleri: şerit durumu, okuma kesintisi,
parametre doğrulaması, eski biçimli tablo, mantıksal sütunlar, gölgenin kriter bazında olması,
bekleyen kaynak, ekran adlarının tek kaynağı, sıralama ve sınırların kararlılığı.

Her test düzeltme öncesi kodda düşer; açıklamada bulgunun kısa adı vardır.
"""
import copy
import json
import os
import shutil
import sys

import pandas as pd

import sahte_dataiku
from arayuz import sunum, sunum_dagilim, sunum_kural, sunum_sure, sunum_tahsilat
from arayuz.sozlesme import BILESENLER
from arayuz.temel import SOZLESME_SUTUNLARI, guncel_tablolar
from avukat_perf.mantik import dogru_mu
from avukat_perf.portfoy import ATANAMAYAN
from hat import akis, kaynak
from test_arayuz import _cikti
from yardimci import KOK, prova_ortami

SAYFALAR = ("genel", "avukat", "sure", "kurallar", "veri")


def _durum(tablolar, params, **ek):
    return sunum.sayfa("veri", tablolar, params, **ek)["bilesenler"]["ortak.durum"][0]


def _son_gece(kayit):
    return kayit[(kayit["kaynak"] == "*") & (kayit["tur"] == "GECELIK")].index[-1]


def _ozet_ekle(kayit, **alanlar):
    """Kayda son gecenin özet satırının değiştirilmiş bir kopyasını ekler."""
    satir = kayit.loc[_son_gece(kayit)].copy()
    for ad, deger in alanlar.items():
        satir[ad] = deger
    kayit = kayit.copy()
    kayit.loc[len(kayit) + 1000] = satir
    return kayit


def test_okuma_kesintisi_onbellekte_kalmaz_ve_seritte_soylenir():
    """1: okunamayan tablo 5 dakika önbellekte kalıp 'henüz sonuç yok' gibi görünüyordu."""
    import flask
    tablolar, params = _cikti()
    onceki = sys.modules.get("dataiku")
    sys.modules["dataiku"] = sahte_dataiku.modul()
    try:
        alan = {"app": flask.Flask("okuma_kesintisi"), "__name__": "backend"}
        with open(os.path.join(KOK, "dataiku", "webapp", "backend.py"), encoding="utf-8") as d:
            exec(compile(d.read(), "backend.py", "exec"), alan)
    finally:
        if onceki is None:
            sys.modules.pop("dataiku", None)
        else:
            sys.modules["dataiku"] = onceki
    cagri = []

    class Ortam(object):
        def tablo_oku(self, ad):
            if ad == "calisma_kaydi":
                cagri.append(ad)
                if len(cagri) == 1:
                    raise IOError("bağlantı kesildi")
            return tablolar.get(ad)

    alan["ORTAM"], asil = Ortam(), alan["ayar"].yukle
    alan["ayar"].yukle = lambda *a: params
    try:
        _, _, okunamayan = alan["_veri"]()
        assert okunamayan == ["calisma_kaydi"]
        serit = _durum({"calisma_kaydi": None}, params, okunamayan=okunamayan)
        assert serit["okunamayan"] == ["calisma_kaydi"]
        alan["ONBELLEK"]["zaman"] -= alan["YENIDEN_SN"] + 1  # kısa süre sonra yeniden denenir
        yeni, _, okunamayan = alan["_veri"]()
        assert len(cagri) == 2 and okunamayan == [] and yeni["calisma_kaydi"] is not None
        assert _durum(yeni, params)["kesit"] is not None
    finally:
        alan["ayar"].yukle = asil


def test_gecersiz_parametre_seritte_soylenir_kurallar_sayfasi_acilir():
    """2: web uygulaması parametreyi doğrulamıyordu (Kurallar 400, şerit 'ilk gecede')."""
    tablolar, params = _cikti()
    yazim = copy.deepcopy(params)
    yazim["kriter1"]["uyari_gn"] = 12
    serit = _durum(tablolar, yazim)
    assert "uyari_gn" in serit["parametre_hatasi"] and serit["kural_degisti"] is False
    assert _durum(tablolar, params)["parametre_hatasi"] is None
    tutarsiz = copy.deepcopy(params)
    tutarsiz["agirliklar"].update({"tahsilat/sure": 9.0, "sure/kalite": 0.2})
    sayfa = sunum.sayfa("kurallar", tablolar, tutarsiz)["bilesenler"]
    assert [k["hata"] for k in sayfa["kurallar.hatalar"]] and "kurallar.agirliklar" not in sayfa
    assert sunum.sayfa("kurallar", tablolar, params)["bilesenler"]["kurallar.hatalar"] == []


def _denetlenen(tablolar):
    return sorted(ad for ad in SOZLESME_SUTUNLARI if tablolar.get(ad) is not None and
                  ad.startswith(("sonuc_", "model_", "birlesik_donem")))


def test_sozlesme_sutunu_eksik_tablo_gosterilmez_sayfalar_acilir():
    """3: tek bir sütunu eksik (eski biçimli) tablo bütün sayfayı 500 yapıyordu."""
    tablolar, params = _cikti()
    kod = tablolar["sonuc_birlesik"]["avukat_kodu"].iloc[0]
    assert len(_denetlenen(tablolar)) >= 15
    for ad in _denetlenen(tablolar):
        for sutun in SOZLESME_SUTUNLARI[ad]:
            eksik = dict(tablolar, **{ad: tablolar[ad].drop(columns=sutun)})
            assert guncel_tablolar(eksik)[ad] is None, (ad, sutun)
        sutun = [s for s in sorted(SOZLESME_SUTUNLARI[ad]) if s != "avukat_kodu"][0]
        eksik = dict(tablolar, **{ad: tablolar[ad].drop(columns=sutun)})
        for sayfa in SAYFALAR:
            veri = sunum.sayfa(sayfa, eksik, params, {"kod": kod})["bilesenler"]
            assert veri["ortak.durum"] and json.dumps(veri, allow_nan=False), (ad, sayfa)


def test_gruplamada_olmayan_boyutun_sutunu_grup_tablosunu_gizlemez():
    """tahsilat.gruplama yaş bandını (ya da tutar bandını, branşı) içermezse hat
    o sütunları grup tablosuna yazmaz; eski biçim kuralı bunu eski tablo sayıp Tahsilat oranı
    göstergesini ve Dosya Grupları kartını boşaltıyordu (önceki kod gösteriyordu)."""
    tablolar, params = _cikti()
    grup = tablolar["sonuc_tahsilat_grup"]
    oran = sunum.sayfa("genel", tablolar, params)["bilesenler"]["genel.kpi"][0]["tahsilat_orani"]
    for dusen in (["yas_bandi", "yas_etiketi"], ["tutar_bandi", "bant_etiketi"],
                  ["yas_bandi", "yas_etiketi", "tutar_bandi", "bant_etiketi"]):
        degisik = dict(tablolar, sonuc_tahsilat_grup=grup.drop(columns=dusen))
        assert guncel_tablolar(degisik)["sonuc_tahsilat_grup"] is not None, dusen
        genel = sunum.sayfa("genel", degisik, params)["bilesenler"]
        assert genel["genel.kpi"][0]["tahsilat_orani"] == oran and genel["genel.gruplar"], dusen
    # Gruplamaya bağlı olmayan sütun eksikse tablo yine eski biçimdir.
    assert guncel_tablolar(dict(tablolar, sonuc_tahsilat_grup=grup.drop(
        columns="atfedilen")))["sonuc_tahsilat_grup"] is None


def test_mantiksal_cozucu():
    """e3: Dataiku boş değerli mantıksal sütunu metin okur; bool('false') True'dur."""
    dogru = (True, 1, 1.0, "true", "True", " TRUE ", "1", "E", "e", "evet")
    yanlis = (False, 0, 0.0, None, float("nan"), "false", "False", "0", "H", "", "hayir", pd.NA)
    assert all(dogru_mu(d) is True for d in dogru) and all(dogru_mu(d) is False for d in yanlis)


def test_metin_olarak_okunan_mantiksal_sutunlar_dogru_gosterilir():
    """e3: 'false' metni yeterli, gönderim, gölge ve kısmi ay okumalarında doğru sayılıyordu."""
    tablolar, params = _cikti()
    metin = {ad: t.assign(**{s: t[s].map(lambda d: "true" if dogru_mu(d) else "false")
                             for s in ("yeterli", "gonderilecek", "son_ay_kismi", "yil_ici")
                             if s in t.columns})
             for ad, t in tablolar.items() if t is not None}
    for sayfa in ("genel", "avukat", "sure"):
        assert sunum.sayfa(sayfa, metin, params) == sunum.sayfa(sayfa, tablolar, params), sayfa
    tahsilat = metin["sonuc_tahsilat_avukat"].assign(yeterli="false")
    tablo = sunum.sayfa("genel", dict(metin, sonuc_tahsilat_avukat=tahsilat), params)[
        "bilesenler"]["genel.avukat_tablosu"]
    assert {k["tahsilat_yeterli"] for k in tablo if k["avukat_kodu"] in set(
        tahsilat["avukat_kodu"])} == {False}
    kayit = metin["calisma_kaydi"].copy()
    kayit.loc[_son_gece(kayit), ["golge", "golge_zorunlu"]] = ["false", "false"]
    assert _durum(dict(metin, calisma_kaydi=kayit), params)["golge_mod"] is False


def test_golge_kriter_bazinda():
    """e1: yedek yol gecesinde yalnız Kriter 1 gölgededir; şerit tek bayrak veriyordu."""
    tablolar, params = _cikti()
    kayit = tablolar["calisma_kaydi"].copy()
    son = _son_gece(kayit)
    for golge, zorunlu, beklenen in ((False, True, (True, False)), (True, False, (True, True)),
                                     (False, False, (False, False))):
        kayit.loc[son, ["golge", "golge_zorunlu"]] = [golge, zorunlu]
        serit = _durum(dict(tablolar, calisma_kaydi=kayit), params)
        assert (serit["golge_ilk_islem"], serit["golge_dava_acma"]) == beklenen
        assert serit["golge_mod"] is any(beklenen)


def test_tahsilat_hareketi_beklenirken_kaynak_seritte_ve_sayfalar_acilir():
    """e2 (D1): tahsilat hareketi gelmeyince tahsilat bileşenleri 'kaynak bekleniyor' der."""
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        ayarlar["kaynaklar"]["tahsilat_hareketi"]["yontem"] = "bekliyor"
        assert akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")["karar"] == \
            "GECTI"
        tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
    finally:
        shutil.rmtree(kok)
    assert tablolar["sonuc_tahsilat_avukat"] is None
    for sayfa in SAYFALAR:
        veri = sunum.sayfa(sayfa, tablolar, params)["bilesenler"]
        assert veri["ortak.durum"][0]["bekleyen_kaynaklar"] == ["tahsilat_hareketi"]
        json.dumps(veri, allow_nan=False)


def test_donem_yayini_kalinca_seritte_soylenir():
    """14: aylık yayın KALDI olunca şeritte bir şey görünmüyordu."""
    tablolar, params = _cikti()
    assert _durum(tablolar, params)["son_donem_karari"] == "GECTI"
    kayit = tablolar["calisma_kaydi"]
    sonra = pd.Timestamp(kayit["baslangic"].max()) + pd.Timedelta(hours=4)
    kayit = _ozet_ekle(kayit, tur="DONEM_SONU", durum="KALDI", baslangic=sonra,
                       calisma_kimligi="C-DONEM-KALDI", uretilen=None)
    serit = _durum(dict(tablolar, calisma_kaydi=kayit), params)
    assert serit["son_donem_karari"] == "KALDI" and serit["son_karar"] == "GECTI"


def test_serit_kesiti_tablolari_secen_geceden():
    """16: şerit üretilen alanı boş GECTI satırını kesit sayıyordu; tablolar onu saymaz."""
    tablolar, params = _cikti()
    kesit = _durum(tablolar, params)["kesit"]
    kayit = tablolar["calisma_kaydi"]
    son = kayit.loc[_son_gece(kayit)]
    kayit = _ozet_ekle(kayit, calisma_kimligi="C-YARIM", uretilen=None,
                       baslangic=pd.Timestamp(son["baslangic"]) + pd.Timedelta(days=1),
                       cekim_tarihi=pd.Timestamp(son["cekim_tarihi"]) + pd.Timedelta(days=1))
    assert _durum(dict(tablolar, calisma_kaydi=kayit), params)["kesit"] == kesit


def test_kalite_karti_son_donem_sonunu_baslangic_anina_gore_secer():
    """13: aynı saniyede başlayan iki dönem sonu çalışmasında rastgele kimlik eki seçiyordu."""
    satirlar = [("C20261201020000-111111", "GECELIK", "2026-12-01 02:00:00.000"),
                ("C20261201060000-f00000", "DONEM_SONU", "2026-12-01 06:00:00.100"),
                ("C20261201060000-0aaaaa", "DONEM_SONU", "2026-12-01 06:00:00.900")]
    kayit = pd.DataFrame(satirlar, columns=["calisma_kimligi", "tur", "baslangic"]).assign(
        kaynak="*")
    kalite = pd.DataFrame({"calisma_kimligi": [s[0] for s in satirlar]})
    assert sorted(sunum_kural._son_kimlikler(kayit, kalite)) == [
        "C20261201020000-111111", "C20261201060000-0aaaaa"]
    # Çalışma kaydı yoksa en büyük kimlik.
    assert sunum_kural._son_kimlikler(None, kalite) == ["C20261201060000-f00000"]


def _celiski(adet):
    return pd.DataFrame([{"dosya_no": "D-{:03d}".format(i), "avukat_kodu": "AV-01",
                          "atama_tarihi": "2026-01-01", "kriter": "K1" if i % 2 else "K2",
                          "seviye": "SARI", "olay_tarihi": "2026-02-{:02d}".format(1 + i % 20),
                          "olay_tarihi_yeni": "2026-03-01", "calisma_kimligi": "C-1",
                          "tespit_tarihi": "2026-11-19"} for i in range(adet)])


def test_duzeltme_incelemesi_siniri_toplami_ve_kararli_secimi():
    """11: çelişkiler 200 satırda sessizce ve rastgele kesiliyordu; toplam gösterilmiyordu."""
    tablo = _celiski(sunum_kural.CELISKI_EN_COK + 1)
    sonuc = sunum_kural.veri({"olay_celiski": tablo})
    ozet = sonuc["veri.celiski_ozet"][0]
    assert (ozet["toplam"], ozet["gosterilen"]) == (201, 200) and len(sonuc["veri.celiski"]) == 200
    karisik = sunum_kural.veri({"olay_celiski": tablo.sample(frac=1, random_state=3)})
    assert karisik["veri.celiski"] == sonuc["veri.celiski"]
    # En yeni olay önce; kalan tek satır en eski olay tarihlerinden biridir.
    tarihler = [k["olay_tarihi"] for k in sonuc["veri.celiski"]]
    assert tarihler == sorted(tarihler, reverse=True)
    assert sunum_kural.veri({})["veri.celiski_ozet"] == [{"toplam": None, "gosterilen": None}]


def test_aylik_avukat_tablosu_izgaranin_son_on_iki_ayi():
    """10: aylık avukat tablosunun 'son 12 ay' kuralı hiçbir testte sabitlenmemişti."""
    aylar = [str(ay) for ay in pd.period_range("2024-12", "2026-11", freq="M")]
    satirlar = [("AV-01", "2025-01", 500.0), ("AV-01", "2026-11", 10.0),
                ("AV-02", "2026-01", 40.0), ("AV-02", "2026-03", 30.0),
                (ATANAMAYAN, "2026-05", 999.0)]
    aylik = pd.DataFrame(satirlar, columns=["avukat_kodu", "ay", "tutar"]).assign(
        ilk_ay=aylar[0], son_ay=aylar[-1], son_ay_kismi=True)
    tablo = sunum_tahsilat.aylik_tablo(aylik)
    assert sorted({k["ay"] for k in tablo}) == aylar[-12:]
    sira = []
    for k in tablo:
        if k["avukat_kodu"] not in sira:
            sira.append(k["avukat_kodu"])
    # AV-02 bu 12 ayda 70, AV-01 10 (Ocak 2025 tablo dışında): toplama göre; yazılamayan sonda.
    assert sira == ["AV-02", "AV-01", ATANAMAYAN]
    hucre = {(k["avukat_kodu"], k["ay"]): (k["tutar"], k["toplam"], k["kismi"]) for k in tablo}
    assert hucre[("AV-02", "2026-02")] == (0.0, 70.0, False)
    assert hucre[("AV-01", "2026-11")] == (10.0, 10.0, True)


def test_veri_durumu_kaynaklari_son_geceden():
    """10: Veri Durumu kaynak kartı 'son gecenin kaynakları' seçimiyle sabitlenmemişti."""
    satir = {"tur": "GECELIK", "yontem": "dosya", "satir_sayisi": 10, "kalite_sonucu": "GECTI",
             "arsiv_yolu": None, "bitis": "x", "aciklama": None}
    kayit = pd.DataFrame([
        dict(satir, calisma_kimligi="C-1", kaynak="dosya", durum="BASARILI",
             cekim_tarihi="2026-11-18", baslangic="2026-11-18 02:00:00"),
        dict(satir, calisma_kimligi="C-1", kaynak="*", durum="GECTI",
             cekim_tarihi="2026-11-18", baslangic="2026-11-18 02:00:00"),
        dict(satir, calisma_kimligi="C-2", kaynak="dosya", durum="KALDI",
             cekim_tarihi="2026-11-19", baslangic="2026-11-19 02:00:00"),
        dict(satir, calisma_kimligi="C-2", kaynak="atama_log", durum="BASARILI",
             cekim_tarihi="2026-11-19", baslangic="2026-11-19 02:00:00"),
        dict(satir, calisma_kimligi="C-2", kaynak="*", durum="KALDI",
             cekim_tarihi="2026-11-19", baslangic="2026-11-19 02:00:00")])
    sonuc = sunum_kural.veri({"calisma_kaydi": kayit})
    kaynaklar = {k["kaynak"]: (k["durum"], k["son_basarili"]) for k in sonuc["veri.kaynaklar"]}
    assert kaynaklar == {"dosya": ("KALDI", "2026-11-18"), "atama_log": ("BASARILI", "2026-11-19")}
    assert [k["calisma_kimligi"] for k in sonuc["veri.calismalar"]] == ["C-2", "C-1"]


def test_dagilim_ve_kadran_ekrandaki_yuvarlanmis_puanla():
    """15: '80,00' görünen puan 75–80 kutusunda sayılıyor, yüzdeliği farklı çıkıyordu."""
    puan = pd.DataFrame({"avukat_kodu": ["AV-1", "AV-2"], "sutun": "sure",
                         "puan": [79.996, 80.004], "durum": "GECERLI"})
    konum = {kod: sunum_dagilim.konum(puan, None, kod) for kod in ("AV-1", "AV-2")}
    for kod, tablo in konum.items():
        satir = tablo.dropna(subset=["avukat_puani"])
        assert set(satir["yuzdelik"]) == {100.0}, kod
        assert int(tablo.loc[tablo["adet"] > 0, "alt"].iloc[0]) == 80, kod
    tablolar, params = _cikti()
    guncel = tablolar["sonuc_puan_guncel"].copy()
    kod = guncel["avukat_kodu"].iloc[0]
    guncel.loc[guncel["avukat_kodu"] == kod, "puan"] = 79.996
    kadran = sunum.sayfa("avukat", dict(tablolar, sonuc_puan_guncel=guncel), params,
                         {"kod": kod})["bilesenler"]["avukat.sutunlar"]
    assert {k["puan"] for k in kadran} == {80.0}


def _olaylar(adet):
    return pd.DataFrame([{"dosya_no": "D-{:02d}".format(i), "avukat_kodu": "AV-01",
                          "atama_tarihi": "2026-01-01", "kriter": "K1", "seviye": "SARI",
                          "olay_tarihi": "2026-02-01", "calisma_kimligi": "C-1",
                          "esas_kaynagi": "dava_takip"} for i in range(adet)])


def test_son_bayrak_olaylari_arka_ucta_kararli_secilir_ve_siralanir():
    """18 ve istemci 7: aynı tarihli olaylarda seçim satır sırasına bağlıydı; sınır JS'te de
    vardı."""
    olay = _olaylar(40)
    donem = olay[["dosya_no", "avukat_kodu", "atama_tarihi", "kriter", "esas_kaynagi"]].assign(
        seviye="SARI", sure_gun=30)

    def son(olaylar, donemler):
        secilen = sunum_sure._olaylar(olaylar, donemler, donemler.head(0))
        secilen = secilen[secilen["son_sira"].notna()].sort_values("son_sira")
        return list(zip(secilen["son_sira"], secilen["dosya_no"]))
    sira = son(olay, donem)
    assert len(sira) == sunum_sure.SON_OLAY and [s for s, _ in sira] == list(
        range(1, sunum_sure.SON_OLAY + 1))
    assert son(olay.sample(frac=1, random_state=7), donem.sample(frac=1, random_state=2)) == sira
    assert [d for _, d in sira] == ["D-{:02d}".format(i) for i in range(sunum_sure.SON_OLAY)]


def test_sure_yeterli_veri_isareti_genel_tabloda_ve_kadranda():
    """e4 (D5): süre puanı da 'Yeterli veri yok' işaretini Genel Bakış ve kadranda taşır."""
    tablolar, params = _cikti()
    sure = tablolar["sonuc_sure"]
    kod = sure["avukat_kodu"].iloc[0]
    degisik = dict(tablolar, sonuc_sure=sure.assign(yeterli=sure["avukat_kodu"] != kod))
    genel = {k["avukat_kodu"]: k for k in sunum.sayfa("genel", degisik, params)["bilesenler"][
        "genel.avukat_tablosu"]}
    assert genel[kod]["sure_yeterli"] is False
    assert all(k["sure_yeterli"] is True for a, k in genel.items() if a != kod and a in set(
        sure["avukat_kodu"]))
    kadran = {k["sutun"]: k["yeterli"] for k in sunum.sayfa(
        "avukat", degisik, params, {"kod": kod})["bilesenler"]["avukat.sutunlar"]}
    assert kadran["sure"] is False


def test_brans_ve_alt_baslik_adlari_parametreden():
    """5, istemci 1: ek dosyayla eklenen branşın ekran adı ve renk sırası parametreden gelir."""
    tablolar, params = _cikti()
    yeni = copy.deepcopy(params)
    yeni["kalite"]["bilinen_branslar"].append("SAGLIK")
    yeni["gorunum"]["brans_adlari"].append(["SAGLIK", "Sağlık"])
    yeni["gorunum"]["alt_baslik_adlari"]["dosyaya_hakimiyet"] = "Dosya bilgisi"
    adlar = {(k["tur"], k["kod"]): (k["ad"], k["sira"]) for k in sunum.sayfa(
        "genel", tablolar, yeni)["bilesenler"]["ortak.adlar"]}
    assert adlar[("brans", "SAGLIK")] == ("Sağlık", len(yeni["gorunum"]["brans_adlari"]))
    assert adlar[("brans", "TRAFIK")] == ("Trafik", 1)
    assert adlar[("alt_baslik", "dosyaya_hakimiyet")] == ("Dosya bilgisi", None)
    assert adlar[("mevcut_alan", "brans_yetkinligi")] == ("Branş yetkinliği", None)
    assert adlar[("sistem", "cekirdek")][0] == params["gorunum"]["sistem_adlari"]["cekirdek"]
    sira = [k for k in adlar if k[0] == "brans"]
    assert len({adlar[k][1] for k in sira}) == len(sira)  # her branşın kendi renk sırası


def test_gorunum_adlari_dogrulanir():
    """5: ekran adları parametreye taşındı; biçimi gece başlamadan denetlenir."""
    from avukat_perf.params import dogrula
    params = _cikti()[1]
    assert dogrula(params) == []
    for alan, deger in (("brans_adlari", [["TRAFIK", "Trafik"], ["KASKO"]]),
                        ("brans_adlari", [["TRAFIK", "Trafik"], ["TRAFIK", "Oto"]]),
                        ("brans_adlari", [["TRAFIK", " "]]),
                        ("alt_baslik_adlari", {"dosyaya_hakimiyet": ""}),
                        ("mevcut_alan_adlari", {"cozum_yetenegi": None})):
        bozuk = copy.deepcopy(params)
        bozuk["gorunum"][alan] = deger
        assert [h for h in dogrula(bozuk) if alan in h], (alan, deger)


def test_bilesen_alani_kaynak_tablonun_baska_sutunuyla_ayni_adi_tasimaz():
    """8: genel.avukat_tablosu.tahsilat_orani G/B'ydi; kaynak tabloda aynı ad tahsilat ÷ rücu."""
    tablolar, _ = _cikti()
    for kimlik, bilesen in BILESENLER.items():
        okunan = {s for sutunlar in bilesen["kaynak"].values() for s in sutunlar}
        for tablo in bilesen["kaynak"]:
            if tablolar.get(tablo) is None:
                continue
            # Alan bir kaynak tablonun sütun adını taşıyorsa bileşen o sütunu okumalı.
            ayni = set(bilesen["alanlar"]) & set(tablolar[tablo].columns) - okunan
            assert not ayni, (kimlik, tablo, sorted(ayni))


def test_calisma_durumu_kaynak_degeri_eslenir():
    """Veri kanalı 16: değerlendirme sistemi E/H verirse değer eşlemesi DEVAM/AYRILDI'ya çevirir
    (arayüz değişmez; eşleme kaynak ayarındadır)."""
    ham = pd.DataFrame({"avukat_kodu": ["AV-01", "AV-02"], "unvan": ["A", "B"],
                        "calisma_durumu": ["E", "H"]})
    ayar = {"deger_eslemesi": {"calisma_durumu": {"E": "DEVAM", "H": "AYRILDI"}}}
    assert list(kaynak.normalle("avukat", ham, ayar)["calisma_durumu"]) == ["DEVAM", "AYRILDI"]


def test_sayfa_secimleri_sunumdan():
    """Araçlar 3: arka uç ve önizleme seçimleri ayrı ayrı yazıyordu (avukat süzgeci düşebilirdi).
    """
    assert sunum.SECIMLER == ("kod",) + tuple(sunum_sure.FILTRE)
    for yol in (os.path.join(KOK, "dataiku", "webapp", "backend.py"),
                os.path.join(KOK, "araclar", "onizleme.py")):
        with open(yol, encoding="utf-8") as dosya:
            metin = dosya.read()
        assert "sunum.SECIMLER" in metin and "SECIMLER = (" not in metin, yol


def test_onizleme_avukat_suzgecini_uygular():
    """Araçlar 3: önizleme sorgusundaki avukat süzgeci sunuma iletilir."""
    from araclar import onizleme
    tablolar, params = _cikti()
    k1 = tablolar["sonuc_k1"]
    kod = k1.loc[k1["seviye"] != "KAPSAM_DISI", "avukat_kodu"].iloc[0]
    durum, _, govde = onizleme.yanit("/api/sayfa?ad=sure&seviye=KAPANDI&avukat=" + kod,
                                     tablolar, params)
    liste = json.loads(govde.decode("utf-8"))["bilesenler"]["sure.liste"]
    assert durum == 200 and liste and {k["avukat_kodu"] for k in liste} == {kod}
