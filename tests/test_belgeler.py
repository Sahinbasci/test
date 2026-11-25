"""README'nin adım adım izlenen bölümleri dosyalarla tutarlı kalır (prova adımları
kurulum not defterindeki ayarı söylemiyor, prova ekinde olmayan tutar bantlarını sayıyordu)."""
import json
import os

from araclar import mutasyon
from hat.ayar_alan import DOSYA_ANAHTARLARI
from yardimci import KOK


def _readme():
    with open(os.path.join(KOK, "README.md"), encoding="utf-8") as dosya:
        return dosya.read()


def _bolum(metin, baslik):
    return metin.split(baslik, 1)[1].split("\n#", 1)[0]


def test_prova_bolumu_kurulum_ayarini_ve_prova_ekini_dogru_anlatir():
    prova = _bolum(_readme(), "### Sentetik veriyle Dataiku provası")
    with open(os.path.join(KOK, "dataiku", "kontrol", "kurulum.py"), encoding="utf-8") as dosya:
        assert "DOSYA_KAYNAGI_VAR = False" in dosya.read()  # varsayılan kapalı: prova açmalı
    assert "DOSYA_KAYNAGI_VAR = True" in prova
    with open(os.path.join(KOK, "sentetik", "params_ek.json"), encoding="utf-8") as dosya:
        ek = json.load(dosya)
    if "tahsilat" not in ek:
        assert "tutar bant" not in prova


def test_dosya_yontemi_anahtarlari_ve_mutasyon_zaman_siniri_belgede():
    metin = _readme()
    for anahtar in sorted(DOSYA_ANAHTARLARI):
        assert "`dosya.{}`".format(anahtar) in metin, anahtar
    assert "{} saniye".format(mutasyon.ZAMAN_SINIRI) in metin


def test_bilerek_yapilmayanlar_kaynagi_olmayan_avukat_bilgilerini_sayar():
    bolum = _bolum(_readme(), "## Bilerek yapılmayanlar")
    for ad in ("sözleşme başlangıcı", "bölge", "yetkili avukat"):
        assert ad in bolum, ad
