"""Kaynak ayarının alt blokları ve ayar dosyası okuma: yazım hatası sessizce kabul edilmez
(sayfalama, kimlik, dosya, biçim, değer eşlemesi, yinelenen JSON anahtarı)."""
import json
import os
import sys
import tempfile

import sahte_dataiku
from hat import api, ayar
from hat.ortam import YerelOrtam
from sahte_dataiku import Klasor
from test_hat_entegrasyon import _Sunucu
from yardimci import DEGISKENLER

SAYFA = {"tur": "sayfa", "sayfa_parametresi": "page", "boyut_parametresi": "size",
         "boyut": 1000, "baslangic": 0}


def _depo():
    with open(os.path.join(DEGISKENLER, "kaynaklar.json"), encoding="utf-8") as dosya:
        return json.load(dosya)


def _api(**sistem):
    """Çekirdek sistem API'den; depodaki ayar üzerine verilen sistem bloğu."""
    blok = {"yontem": "api", "api": {"adres_koku": "https://servis/rucu", "sayfalama": SAYFA,
                                     "kimlik": {"tur": "bearer", "gizli": "G"}}}
    for anahtar, deger in sistem.items():
        (blok["api"] if anahtar in ("sayfalama", "kimlik") else blok)[anahtar] = deger
    return ayar.birlestir(_depo(), {"sistemler": {"cekirdek": blok}})


def _hatalar(ayarlar):
    return ayar.dogrula(ayarlar)


def test_alt_bloklarda_yazim_hatasi_ve_gecersiz_deger_yakalanir():
    assert _hatalar(_api()) == []
    assert _hatalar(_api(sayfalama=dict(SAYFA, toplam_yol="meta.total")))
    assert _hatalar(_api(sayfalama=dict(SAYFA, tur="offset")))
    assert _hatalar(_api(sayfalama={"tur": "imlec", "imlec_parametresi": "cursor"}))
    assert _hatalar(_api(kimlik={"tur": "oauth2", "gizli": "G", "jeton_adresi": "https://j",
                                 "kapsm": "rucu"}))
    assert _hatalar(_api(sayi_bicimi="TR"))
    assert _hatalar(_api(sayi_bicimi="en")) == []
    ayarlar = _api()
    ayarlar["kaynaklar"]["takip"]["sistem"] = "dava_takip"
    assert _hatalar(ayarlar)
    ayarlar = _api()
    ayarlar["kaynaklar"]["dosya"]["api"]["yontem"] = "POST"  # eski ad: artık okunmaz
    assert _hatalar(ayarlar)


def test_deger_eslemesi_alani_sistemin_kaynaklarinda_olmali():
    assert _hatalar(_api(deger_eslemesi={"brans": {"Trafik": "TRAFIK"}})) == []
    assert _hatalar(_api(deger_eslemesi={"alt_baslik": {"A": "b"}}))  # değerlendirme alanı
    assert _hatalar(_api(deger_eslemesi={"brans": {"Trafik": 1}}))
    # "_" ile başlayan anahtar açıklamadır (ayar dosyalarının genel kuralı): hata değil.
    assert _hatalar(_api(deger_eslemesi={"_not": "branş kodları teyitli",
                                         "brans": {"Trafik": "TRAFIK"}})) == []


def test_adres_yolu_egik_cizgisiz_de_kurulur():
    ayarlar = _api()
    ayarlar["kaynaklar"]["dosya"]["api"]["yol"] = "dosyalar"
    assert ayar.kaynak_ayari(ayarlar, "dosya")["api"]["adres"] == "https://servis/rucu/dosyalar"
    ayarlar["kaynaklar"]["dosya"]["api"]["yol"] = "/dosyalar"
    assert ayar.kaynak_ayari(ayarlar, "dosya")["api"]["adres"] == "https://servis/rucu/dosyalar"


def test_sayfalama_bloku_ekte_butunuyle_degisir_ve_ilk_sayfa_acik_yazilir():
    imlec = {"tur": "imlec", "imlec_parametresi": "cursor", "sonraki_imlec_yolu": "next"}
    ayarlar = _api(sayfalama=imlec)
    assert ayar.kaynak_ayari(ayarlar, "dosya")["api"]["sayfalama"] == imlec  # boyut miras yok
    eksik = {k: v for k, v in SAYFA.items() if k != "baslangic"}
    assert "dosya.api.sayfalama: sayfa türü için baslangic gerekir" in _hatalar(
        _api(sayfalama=eksik))
    kayitlar = [{"dosya_no": "D-{}".format(i)} for i in range(25)]

    def yanit(yol, sorgu, basliklar):  # ilk sayfayı 0 sayan sunucu
        bas = int(sorgu["page"]) * 10
        return 200, {"data": kayitlar[bas:bas + 10]}
    sunucu = _Sunucu(yanit)
    try:
        oku = {"adres": sunucu.adres + "/d", "kayit_yolu": "data",
               "sayfalama": dict(SAYFA, boyut=10)}
        assert len(api.oku(oku, {}.get)) == 25
    finally:
        sunucu.kapat()


def test_ayar_dosyasinda_yinelenen_anahtar_hata_verir():
    klasor = tempfile.mkdtemp()
    metin = '{"kalite_davranis": {"olcek": {"en_dusuk": 1}}, "kalite_davranis": {"x": 1}}'
    with open(os.path.join(klasor, "params_ek.json"), "w", encoding="utf-8") as dosya:
        dosya.write(metin)
    ortam = YerelOrtam(tempfile.mkdtemp(), ayar_kok=klasor)
    try:
        ortam.ayar_oku("params_ek.json")
        raise AssertionError("yinelenen anahtar kabul edildi")
    except ValueError as hata:
        assert "yinelenen anahtar kalite_davranis" in str(hata)
    try:
        sys.modules["dataiku"] = sahte_dataiku.modul()
        from hat.dataiku_ortam import DataikuOrtam
        Klasor("ayarlar").upload_data("kaynaklar_ek.json", metin.encode("utf-8"))
        try:
            DataikuOrtam().ayar_oku("kaynaklar_ek.json")
            raise AssertionError("yinelenen anahtar kabul edildi")
        except ValueError as hata:
            assert "kaynaklar_ek.json: yinelenen anahtar" in str(hata)
    finally:
        sys.modules.pop("dataiku", None)

