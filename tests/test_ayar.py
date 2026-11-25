"""Ayar dosyaları (hat.ayar): ek dosyayla birleştirme, sistem + kaynak ayarı ve doğrulama.

Şirkette bir sistemi bağlamak için kaynaklar_ek.json'a yalnız o sistemin bloğu yazılır
(yontem, adres kökü, kimlik); kaynakların yolu, veri kümesi ve alan eşlemesi depodan gelir.
"""
import json
import os
import shutil
import sys
import tempfile

import sahte_dataiku
from avukat_perf import sema
from hat import akis, ayar
from hat.ortam import YerelOrtam
from sahte_dataiku import Klasor
from yardimci import DEGISKENLER, KOK, params_yukle


def _json(*parcalar):
    with open(os.path.join(*parcalar), encoding="utf-8") as dosya:
        return json.load(dosya)


def _depo():
    return _json(DEGISKENLER, "kaynaklar.json")


def test_birlestir_derin_ek_kazanir_liste_degisir_taban_bozulmaz():
    taban = {"a": {"b": 1, "c": [1, 2]}, "d": "x"}
    ek = {"a": {"c": [3], "e": None}, "f": {"g": 1}}
    sonuc = ayar.birlestir(taban, ek)
    assert sonuc == {"a": {"b": 1, "c": [3], "e": None}, "d": "x", "f": {"g": 1}}
    assert taban == {"a": {"b": 1, "c": [1, 2]}, "d": "x"}
    sonuc["a"]["c"].append(9)
    assert ek["a"]["c"] == [3]
    assert ayar.birlestir(taban, None) == taban


def test_depodaki_ayar_ve_sentetik_ek_gecerli():
    assert ayar.dogrula(_depo()) == []
    prova = ayar.birlestir(_depo(), _json(KOK, "sentetik", "kaynaklar_ek.json"))
    assert ayar.dogrula(prova) == []
    # Depodaki varsayılan hiçbir kaynağı bağlamaz; prova eki hepsini dosyadan okur.
    assert {ayar.kaynak_ayari(_depo(), ad)["yontem"] for ad in sema.KAYNAKLAR} == {"bekliyor"}
    assert {ayar.kaynak_ayari(prova, ad)["yontem"] for ad in sema.KAYNAKLAR} == {"dosya"}


def test_sistem_ayari_kaynaga_gecer_adres_kokle_yoldan_kurulur():
    ek = {"sistemler": {"cekirdek": {"yontem": "api", "api": {
        "adres_koku": "https://api.example.com/v1/", "kimlik": {"tur": "basic",
                                                               "gizli": "CEKIRDEK_GIRIS"}}}}}
    ayarlar = ayar.birlestir(_depo(), ek)
    # Depodaki sayfalamada ilk sayfa numarası yok: API'nin 0 ya da 1 saydığı açıkça yazılır.
    assert set(ayar.dogrula(ayarlar)) == {"{}.api.sayfalama: sayfa türü için baslangic "
                                          "gerekir".format(ad) for ad in ("dosya", "atama_log",
                                                                           "takip")}
    sayfalama = dict(_depo()["sistemler"]["cekirdek"]["api"]["sayfalama"], baslangic=0)
    ek["sistemler"]["cekirdek"]["api"]["sayfalama"] = sayfalama
    ayarlar = ayar.birlestir(_depo(), ek)
    assert ayar.dogrula(ayarlar) == []
    cekirdek = [ad for ad, tanim in sema.KAYNAKLAR.items() if tanim["sistem"] == "cekirdek"]
    assert len(cekirdek) >= 3
    for ad in sema.KAYNAKLAR:
        etkin = ayar.kaynak_ayari(ayarlar, ad)
        if ad not in cekirdek:
            assert etkin["yontem"] == "bekliyor"
            continue
        yol = _depo()["kaynaklar"][ad]["api"]["yol"]
        assert etkin["yontem"] == "api"
        assert etkin["api"]["adres"] == "https://api.example.com/v1" + yol
        assert etkin["api"]["kimlik"] == {"tur": "basic", "gizli": "CEKIRDEK_GIRIS"}
        assert etkin["api"]["sayfalama"]["tur"] == "sayfa"  # depodaki sistem ayarı korunur
        assert etkin["dataiku"]["veri_kumesi"].startswith("kaynak_cekirdek_")


def test_kaynak_ayari_sistemi_ezer_ve_kopyadir():
    ayarlar = ayar.birlestir(_depo(), {
        "sistemler": {"cekirdek": {"yontem": "api", "api": {"adres_koku": "https://a"}}},
        "kaynaklar": {"takip": {"yontem": "dataiku"},
                      "atama_log": {"api": {"adres": "https://b/ozel?tur=1"}}}})
    assert ayar.kaynak_ayari(ayarlar, "takip")["yontem"] == "dataiku"
    assert ayar.kaynak_ayari(ayarlar, "atama_log")["api"]["adres"] == "https://b/ozel?tur=1"
    etkin = ayar.kaynak_ayari(ayarlar, "dosya")
    etkin["api"]["kimlik"]["gizli"] = "DEGISTI"
    assert ayar.kaynak_ayari(ayarlar, "dosya")["api"]["kimlik"]["gizli"] != "DEGISTI"
    assert ayar.kaynak_ayari({}, "dosya") == {"yontem": "bekliyor"}


def _hatalar(degistir):
    ayarlar = _depo()
    degistir(ayarlar)
    return ayar.dogrula(ayarlar)


def sistem(ayarlar):
    return ayarlar["sistemler"]["cekirdek"]


def kaynak(ayarlar, ad):
    return ayarlar["kaynaklar"][ad]


def test_yazim_hatasi_ve_eksik_bilgi_sessizce_beklemeye_dusmez():
    durumlar = [
        (lambda a: a.update(sistemlr={}), "bilinmeyen anahtar sistemlr"),
        (lambda a: a["sistemler"].update(cekirdk={}), "bilinmeyen sistem cekirdk"),
        (lambda a: a["kaynaklar"].update(atamalog={}), "bilinmeyen kaynak atamalog"),
        (lambda a: a["kaynaklar"].pop("takip"), "tanımsız kaynak takip"),
        (lambda a: sistem(a).update(yontm="api"), "sistemler.cekirdek: bilinmeyen anahtar yontm"),
        (lambda a: kaynak(a, "dosya").update(alan_eslemsi={}), "bilinmeyen anahtar alan_eslemsi"),
        (lambda a: sistem(a)["api"].update(sayfalma={}), "dosya.api: bilinmeyen anahtar sayfalma"),
        (lambda a: sistem(a).update(yontem="API"), "yontem bekliyor | dataiku | api | dosya"),
        (lambda a: sistem(a).update(yontem="api"), "api.adres_koku henüz girilmedi"),
        (lambda a: sistem(a)["api"].update(adres="https://x"), "adres değil adres_koku"),
        (lambda a: kaynak(a, "dosya").update(yontem="dataiku", dataiku={}),
         "dosya: dataiku yöntemi için dataiku.veri_kumesi gerekir"),
        (lambda a: kaynak(a, "bekleme").update(yontem="dosya", dosya={"yol": ""}),
         "bekleme: dosya yöntemi için dosya.yol gerekir"),
        (lambda a: sistem(a).update(yontem="api", api=dict(
            sistem(a)["api"], adres_koku="https://x", kimlik={"tur": "sorgu", "gizli": "G"})),
         "dosya.api: sorgu kimliği için kimlik.parametre gerekir"),
        (lambda a: sistem(a).update(yontem="api", api=dict(sistem(a)["api"],
                                                            adres_koku="api.example.com/v1")),
         "dosya: api adresi http:// ya da https:// ile başlamalı"),
        (lambda a: kaynak(a, "dosya").update(api={"yol": "/dosya listesi"}) or sistem(a).update(
            yontem="api", api=dict(sistem(a)["api"], adres_koku="https://x")),
         "dosya: api adresi http:// ya da https:// ile başlamalı, boşluk içermemeli"),
    ]
    for degistir, beklenen in durumlar:
        hatalar = _hatalar(degistir)
        assert any(beklenen in hata for hata in hatalar), (beklenen, hatalar)
    assert _hatalar(lambda a: a["kaynaklar"].update(_not="açıklama")) == []
    try:
        ayar.dogrula_veya_dur({"kaynaklar": {}})
        assert False, "geçersiz ayar durdurmalı"
    except ValueError as hata:
        assert "tanımsız kaynak dosya" in str(hata)


def test_yerel_ortam_ek_dosyayi_birlestirir_bom_okunur():
    kok = tempfile.mkdtemp()
    try:
        ayar_kok = os.path.join(kok, "ayarlar")
        os.makedirs(ayar_kok)
        shutil.copy(os.path.join(DEGISKENLER, "kaynaklar.json"), ayar_kok)
        ortam = YerelOrtam(kok)
        assert ortam.ayar_oku_varsa("kaynaklar_ek.json") is None
        assert ayar.yukle(ortam, "kaynaklar") == _depo()
        with open(os.path.join(ayar_kok, "kaynaklar_ek.json"), "w", encoding="utf-8-sig") as d:
            json.dump({"sistemler": {"duzeltme": {"yontem": "dataiku"}}}, d)
        birlesik = ayar.yukle(ortam, "kaynaklar")
        assert ayar.kaynak_ayari(birlesik, "bekleme")["yontem"] == "dataiku"
        assert ayar.dogrula(birlesik) == []
    finally:
        shutil.rmtree(kok)


def test_dataiku_ortaminda_ek_dosya_yoksa_yalniz_varsayilan():
    try:
        sys.modules["dataiku"] = sahte_dataiku.modul()
        from hat.dataiku_ortam import DataikuOrtam
        ortam = DataikuOrtam()
        Klasor("ayarlar").upload_data("params.json", b'{"a": {"b": 1, "c": 2}}')
        assert ortam.ayar_oku_varsa("params_ek.json") is None
        assert ayar.yukle(ortam, "params") == {"a": {"b": 1, "c": 2}}
        Klasor("ayarlar").upload_data("params_ek.json", b'{"a": {"c": 3}}')
        assert ayar.yukle(ortam, "params") == {"a": {"b": 1, "c": 3}}
    finally:
        sys.modules.pop("dataiku", None)


def test_gecersiz_kaynak_ayariyla_gece_baslamaz():
    kok = tempfile.mkdtemp()
    try:
        ortam = YerelOrtam(kok)
        ayarlar = ayar.birlestir(_depo(), {"kaynaklar": {"dosya": {"yontm": "dosya"}}})
        try:
            akis.gecelik(ortam, ayarlar, params_yukle(), simdi="2026-11-19 02:00:00")
            assert False, "geçersiz ayarla gece başlamamalı"
        except ValueError as hata:
            assert "kaynaklar.dosya: bilinmeyen anahtar yontm" in str(hata)
        assert ortam.tablo_oku("calisma_kaydi") is None
    finally:
        shutil.rmtree(kok)
