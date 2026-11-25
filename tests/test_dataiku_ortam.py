"""DataikuOrtam testleri: dataiku paketi sahte bir modülle (sahte_dataiku.py) taklit edilir."""
import os
import sys

import pandas as pd

import sahte_dataiku
from sahte_dataiku import Klasor, VeriKumesi
from yardimci import hata_bekle


def _ortam():
    sys.modules["dataiku"] = sahte_dataiku.modul()
    from hat.dataiku_ortam import DataikuOrtam
    return DataikuOrtam()


def test_tablo_gidis_donus_turleri_ve_tarih_gunu_korur():
    try:
        ortam = _ortam()
        assert ortam.tablo_oku("sonuc_k1") is None
        tablo = pd.DataFrame({"dosya_no": ["000123", None], "tutar": [1.5, None],
                              "tarih": pd.to_datetime(["2026-11-19", None]),
                              "dusum": [True, False]})
        ortam.tablo_yaz("sonuc_k1", tablo)
        geri = ortam.tablo_oku("sonuc_k1")
        assert list(geri["dosya_no"])[0] == "000123"
        assert geri["tarih"].dt.tz is None and geri["tarih"].iloc[0] == pd.Timestamp("2026-11-19")
        assert list(geri["dusum"]) == [True, False]
        VeriKumesi.eski_surum = True
        eski = ortam.tablo_oku("sonuc_k1")
        assert eski is not None and len(eski) == 2
    finally:
        sys.modules.pop("dataiku", None)


def test_kaynak_veri_kumesi_arsiv_gizli_ayar_ve_dosya():
    try:
        ortam = _ortam()
        VeriKumesi.depo["kaynak_cekirdek_dosya"] = pd.DataFrame({"dosya_no": ["007"]})
        assert list(ortam.veri_kumesi_oku("kaynak_cekirdek_dosya")["dosya_no"]) == ["007"]
        assert not ortam.arsiv_var("ham/kaynak=dosya/veri.csv.gz")
        ortam.arsiv_yaz("ham/kaynak=dosya/veri.csv.gz", b"veri")
        assert ortam.arsiv_var("ham/kaynak=dosya/veri.csv.gz")
        assert ortam.arsiv_var("/ham/kaynak=dosya/veri.csv.gz")
        assert ortam.gizli("API_ANAHTARI") == "gizli-deger"
        assert hata_bekle(KeyError, ortam.gizli, "YOK_BOYLE_GIZLI")
        Klasor("ayarlar").upload_data("params.json", '{"a": 1}'.encode("utf-8"))
        assert ortam.ayar_oku("params.json") == {"a": 1}
        Klasor("kaynak_dosyalari").upload_data("gunluk/dosya.csv", b"dosya_no\nD-1\n")
        yol = ortam.dosya_yolu("gunluk/dosya.csv")
        with open(yol, encoding="utf-8") as dosya:
            assert dosya.read() == "dosya_no\nD-1\n"
        os.remove(yol)
    finally:
        sys.modules.pop("dataiku", None)


def test_gecici_okuma_hatasi_gecmisi_silmez_bom_okunur():
    try:
        ortam = _ortam()
        ortam.tablo_yaz("calisma_kaydi", pd.DataFrame({"calisma_kimligi": ["C-1"]}))
        VeriKumesi.bozuk.add("calisma_kaydi")
        # Boş sayılsaydı gece kaydı baştan yazar, geçmiş silinirdi.
        assert hata_bekle(IOError, ortam.tablo_oku, "calisma_kaydi")
        VeriKumesi.bozuk.clear()
        assert list(ortam.tablo_oku("calisma_kaydi")["calisma_kimligi"]) == ["C-1"]
        Klasor("ayarlar").upload_data("params.json", u"\ufeff{\"a\": 1}".encode("utf-8"))
        assert ortam.ayar_oku("params.json") == {"a": 1}
    finally:
        sys.modules.pop("dataiku", None)


def test_bos_degerli_mantiksal_sutun_kimligi_bozmadan_okunur_okunamazsa_hata():
    asil = VeriKumesi.get_dataframe

    def mantiksal_bos(self, infer_with_pandas=True, **secenek):
        if not infer_with_pandas and not secenek.get("bool_as_str"):
            raise ValueError("Bool column has NA values")
        return asil(self, infer_with_pandas, **secenek)

    def hep_hata(self, infer_with_pandas=True, **secenek):
        if not infer_with_pandas:
            raise ValueError("Bool column has NA values")
        return asil(self, infer_with_pandas, **secenek)
    try:
        ortam = _ortam()
        VeriKumesi.depo["kaynak_cekirdek_dosya"] = pd.DataFrame(
            {"dosya_no": ["000123", "000124"], "aktif": [True, None]})
        VeriKumesi.get_dataframe = mantiksal_bos
        okunan = ortam.veri_kumesi_oku("kaynak_cekirdek_dosya")
        assert list(okunan["dosya_no"]) == ["000123", "000124"]
        # Üç seçenek de olmazsa pandas tahminine (baştaki sıfırlar silinir) düşülmez.
        VeriKumesi.get_dataframe = hep_hata
        assert hata_bekle(ValueError, ortam.veri_kumesi_oku, "kaynak_cekirdek_dosya")
    finally:
        VeriKumesi.get_dataframe = asil
        sys.modules.pop("dataiku", None)


def test_bos_degerli_tamsayi_sutunu_int_as_float_ile_okunur():
    """Boş değerli tamsayı sütunu şema türleriyle int_as_float ile okunur; kimlik metin kalır,
    pandas tahminine (baştaki sıfırlar silinir) düşülmez ve mantıksal sütun gereksiz yere metne
    (bool_as_str) çevrilmez."""
    try:
        ortam = _ortam()
        VeriKumesi.depo["kaynak_cekirdek_dosya"] = pd.DataFrame(
            {"dosya_no": ["000123", "000124"], "adet": [1.0, None], "aktif": [True, False]})
        VeriKumesi.tamsayi_bos.add("kaynak_cekirdek_dosya")
        okunan = ortam.veri_kumesi_oku("kaynak_cekirdek_dosya")
        assert list(okunan["dosya_no"]) == ["000123", "000124"]
        assert okunan["adet"].iloc[0] == 1.0 and pd.isna(okunan["adet"].iloc[1])
        assert list(okunan["aktif"]) == [True, False]
    finally:
        sys.modules.pop("dataiku", None)
