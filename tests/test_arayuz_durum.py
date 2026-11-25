"""Arayüzün durum doğruluğu: üst şerit son başarılı geceyi gösterir, kural değişikliği söylenir,
süre listesinin sınırı sayacı ve seçenekleri bozmaz; JS veriye yalnız sözleşmeyle erişir."""
import json
import re

import pandas as pd

from arayuz import sunum, sunum_kural, sunum_sure
from avukat_perf import agirlik
from test_arayuz import _cikti, _cizici_bloklari, _oku
from yardimci import agirlik_karsilastirmasi


def _serit(tablolar, params):
    return sunum.sayfa("veri", tablolar, params)["bilesenler"]["ortak.durum"][0]


def test_serit_son_basarili_gecenin_kesitini_ve_son_karari_gosterir():
    tablolar, params = _cikti()
    kayit = tablolar["calisma_kaydi"]
    ozet = kayit[(kayit["kaynak"] == "*") & (kayit["tur"] == "GECELIK")].iloc[-1]
    kaldi = ozet.copy()
    kaldi["calisma_kimligi"], kaldi["durum"] = "C-SONRA", "KALDI"
    kaldi["baslangic"] = pd.Timestamp(ozet["baslangic"]) + pd.Timedelta(days=1)
    kaldi["cekim_tarihi"] = pd.Timestamp(ozet["cekim_tarihi"]) + pd.Timedelta(days=1)
    kaldi["uretilen"], kaldi["hesap_surumu"] = None, None
    kayit = kayit.copy()
    kayit.loc[len(kayit)] = kaldi
    serit = _serit(dict(tablolar, calisma_kaydi=kayit), params)
    assert serit["son_karar"] == "KALDI"
    assert serit["kesit"] == str(pd.Timestamp(ozet["cekim_tarihi"]).date())
    assert serit["kural_degisti"] is False and serit["hesap_surumu"]


def test_parametre_degisince_kural_degisti_soylenir():
    tablolar, params = _cikti()
    yeni = json.loads(json.dumps(params))
    yeni["agirliklar"] = agirlik_karsilastirmasi(35, 30, 25, 10)
    serit = _serit(tablolar, yeni)
    assert serit["kural_degisti"] is True
    # Sürüm, ekrandaki sonuçların hesaplandığı sürümdür (gece kaydı), yeni parametreninki değil.
    assert serit["hesap_surumu"] == _serit(tablolar, params)["hesap_surumu"]


def test_hic_basarili_gece_yokken_kesit_bos():
    tablolar, params = _cikti()
    kayit = tablolar["calisma_kaydi"].assign(durum="KALDI", uretilen=None)
    serit = _serit(dict(tablolar, calisma_kaydi=kayit), params)
    assert serit["kesit"] is None and serit["son_karar"] == "KALDI"


def test_sure_listesi_siniri_sayaci_secenekleri_ve_son_olaylari_bozmaz():
    tablolar, params = _cikti()
    eski, sunum_sure.EN_COK = sunum_sure.EN_COK, 5
    try:
        veri = sunum.sayfa("sure", tablolar, params)["bilesenler"]
        secili = sunum.sayfa("sure", tablolar, params, {"kriter": "K1"})["bilesenler"]
    finally:
        sunum_sure.EN_COK = eski
    tam = sunum.sayfa("sure", tablolar, params)["bilesenler"]
    filtre = veri["sure.filtre"][0]
    assert len(veri["sure.liste"]) == filtre["gosterilen"] == 5
    assert filtre["toplam"] == len(tam["sure.liste"]) > 5
    olculen = set()
    for ad in ("sonuc_k1", "sonuc_k2"):
        tablo = tablolar[ad]
        olculen |= set(tablo.loc[tablo["seviye"] != "KAPSAM_DISI", "avukat_kodu"])
    assert filtre["avukatlar"] == sorted(olculen)
    assert {k["avukat_kodu"] for k in tam["sure.liste"]} <= olculen
    assert secili["sure.filtre"][0]["avukatlar"] == filtre["avukatlar"]
    en_yeni = max(k["olay_tarihi"] for k in tam["sure.olaylar"])
    assert max(k["olay_tarihi"] for k in veri["sure.olaylar"]) == en_yeni


def _kod(js):
    """Yorumları ve metin sabitlerini çıkarılmış JS."""
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return re.sub(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', '""', js)


def test_cizici_kayda_dogrudan_erismez_sayi_sabitiyle_bicimlendirmez():
    bloklar, _ = _cizici_bloklari(_oku("uygulama.js"))
    for kimlik, blok in bloklar.items():
        kod = _kod(blok)
        # Veri alanları snake_case'tir; r.alan_adi ya da r["alan_adi"] sözleşmeyi atlatır.
        assert not re.findall(r"\.\s*[a-z0-9]+_[a-z0-9_]+\b", kod), kimlik
        assert not re.findall(r'\[\s*"[a-z0-9]+_[a-z0-9_]+"\s*\]', blok), kimlik
        # Ekrandaki sayı arka uçtan gelir: biçimlendiriciye elle yazılmış sayı verilmez.
        assert not re.findall(r"\b(?:sayi|yuzde|tl|kisa|kisaTl|puanMetni|skorHucre)\(\s*-?\d",
                              kod), kimlik


def test_kural_degisince_etiket_ve_agirlik_hesaptaki_kurallardan():
    # Yeniden hesap yapılmadan bant sınırı ve ağırlık değişirse eski sayılar yeni adlarla
    # gösterilmez: etiket ve ağırlık sonuç tablosundan gelir.
    tablolar, params = _cikti()
    yeni = json.loads(json.dumps(params))
    yeni["agirliklar"] = agirlik_karsilastirmasi(35, 30, 25, 10)
    yeni["tahsilat"]["tutar_bantlari"] = [1.0, 2.0]
    eski_sayfa, yeni_sayfa = (sunum.sayfa("genel", tablolar, p)["bilesenler"]
                              for p in (params, yeni))
    for bilesen in ("genel.bant", "genel.gruplar"):
        assert eski_sayfa[bilesen] == yeni_sayfa[bilesen], bilesen
    assert {k["bant_etiketi"] for k in yeni_sayfa["genel.bant"]} >= {"40.000 altı"}
    kod = tablolar["sonuc_birlesik"]["avukat_kodu"].iloc[0]
    sutunlar = sunum.sayfa("avukat", tablolar, yeni, {"kod": kod})["bilesenler"]["avukat.sutunlar"]
    assert {k["sutun"]: k["agirlik"] for k in sutunlar} == agirlik.sutun_agirliklari(params)


def test_sure_listesi_penceresi_hesaptaki_kesitten():
    # Liste yalnız açık dönemleri ve hesapta pencerede işaretlenen düşümleri gösterir. Eskiden
    # pencere ölçüm bitişlerinin en büyüğünden kuruluyordu: kapanmış dönemlerden oluşan listede
    # Ocak 2025 düşümü (kesit 19.11.2026, pencere 12 ay) görünüyordu.
    tablolar, params = _cikti()
    k1 = tablolar["sonuc_k1"]
    kapanan = k1[k1["seviye"] == "KAPANDI"].head(3).copy()
    kapanan["olcum_sonu"] = pd.Timestamp("2025-03-01")
    kapanan["dusum"], kapanan["pencerede_dusum"] = True, False
    kapanan["dusum_tarihi"] = pd.Timestamp("2025-01-15")
    liste = sunum_sure.sure({"sonuc_k1": kapanan})["sure.liste"]
    assert liste == []
    tum = sunum.sayfa("sure", tablolar, params)["bilesenler"]["sure.liste"]
    pencerede = k1[k1["pencerede_dusum"] & ~k1["seviye"].isin(sunum_sure.ACIK_DONEM)]
    assert set(pencerede["dosya_no"]) <= {k["dosya_no"] for k in tum}


def test_kirmizi_sayaci_her_sayfa_yanitinda():
    tablolar, params = _cikti()
    beklenen = float(tablolar["sonuc_sure_ozet"]["acik_kirmizi"].sum())
    for ad in ("genel", "avukat", "sure", "kurallar", "veri"):
        assert _serit(tablolar, params) == sunum.sayfa(ad, tablolar, params)["bilesenler"][
            "ortak.durum"][0]
        assert sunum.sayfa(ad, tablolar, params)["bilesenler"]["ortak.durum"][0][
            "acik_kirmizi"] == beklenen


def test_yeni_sutunlari_tasimayan_onceki_gece_tablolariyla_sayfalar_acilir():
    # Kod aktarıldıktan sonraki ilk geceye kadar sonuç tabloları eski biçimdedir.
    tablolar, params = _cikti()
    eski = {ad: (tablo.drop(columns=["pencerede_dusum", "bant_etiketi", "agirlik", "gereken"],
                            errors="ignore") if tablo is not None else None)
            for ad, tablo in tablolar.items()}
    kod = tablolar["sonuc_birlesik"]["avukat_kodu"].iloc[0]
    for ad, secim in (("genel", None), ("avukat", {"kod": kod}), ("sure", None)):
        assert sunum.sayfa(ad, eski, params, secim)["bilesenler"], ad


def test_yarim_yazilmis_sonuc_tablosu_gosterilmez():
    """Etiketi doğru ama satır sayısı gecenin kaydındakinden farklı tablo gösterilmez."""
    from arayuz.temel import guncel_tablolar
    tablolar, params = _cikti()
    assert guncel_tablolar(tablolar)["sonuc_k1"] is not None
    for kesik in (tablolar["sonuc_k1"].iloc[:1], tablolar["sonuc_k1"].iloc[0:0]):
        assert guncel_tablolar(dict(tablolar, sonuc_k1=kesik))["sonuc_k1"] is None


def test_veri_durumu_kalite_karti_son_calismayi_gosterir_donem_sonu_dahil():
    """Dönem sonu çalışmasının çekim tarihi kesittir (ay sonu), onu kapsayan gecelik çekimden
    küçüktür. Kart çekim tarihine göre seçseydi dönem sonunda kalan denetim hiç görünmezdi."""
    kalite = pd.DataFrame([
        ("C20261201020000-aaaaaa", "2026-12-01", "dosya", "EKSIK_ALAN", "UYARI"),
        ("C20261201090000-bbbbbb", "2026-11-30", "donem", "HAZIRLIK_SURUMU", "KALDI")],
        columns=["calisma_kimligi", "cekim_tarihi", "kaynak", "kontrol", "durum"]).assign(
            deger=None, esik=None, aciklama="")
    kart = sunum_kural.veri({"kalite_sonucu": kalite})["veri.kalite"]
    assert [k["kontrol"] for k in kart] == ["HAZIRLIK_SURUMU"]
    # Çalışma kaydı varsa son gecelik ve son dönem sonu birlikte gösterilir.
    kayit = pd.DataFrame([("C20261201020000-aaaaaa", "GECELIK", "2026-12-01 02:00:00"),
                          ("C20261201090000-bbbbbb", "DONEM_SONU", "2026-12-01 09:00:00")],
                         columns=["calisma_kimligi", "tur", "baslangic"]).assign(kaynak="*")
    assert sorted(sunum_kural._son_kimlikler(kayit, kalite)) == [
        "C20261201020000-aaaaaa", "C20261201090000-bbbbbb"]
