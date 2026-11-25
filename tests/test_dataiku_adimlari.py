"""Dataiku'ya yapıştırılan adımların duman testi: senaryo adımları (gecelik, dönem sonu) ve
aktarım kontrol not defteri sahte Dataiku modülüyle baştan sona çalıştırılır.

Bu dosyalar yerelde başka hiçbir yerde çalışmaz; bir yazım ya da çağrı hatası ancak şirkette
görülürdü. Gerçek Dataiku davranışı aktarım kontrolüyle ayrıca denenir.
"""
import contextlib
import io
import json
import os
import runpy
import sys

import pandas as pd

import sahte_dataiku
from araclar import ozet
from avukat_perf import sema
from hat.ayar import kaynak_ayari
from sahte_dataiku import Klasor, VeriKumesi
from yardimci import KOK, hata_bekle

DATAIKU = os.path.join(KOK, "dataiku")


def _hazirla():
    """Sahte Dataiku: ayarlar klasöründe depodaki params.json ve kaynaklar.json ile prova ekleri
    (params_ek.json, kaynaklar_ek.json; şirketteki gibi ayrı dosya), kaynak_dosyalari klasöründe
    sentetik CSV'ler."""
    sys.modules["dataiku"] = sahte_dataiku.modul()
    from araclar import yerel_calistir
    for kaynak_klasor, ad in (("dataiku/degiskenler", "params.json"),
                              ("dataiku/degiskenler", "kaynaklar.json"),
                              ("sentetik", "params_ek.json"), ("sentetik", "kaynaklar_ek.json")):
        with open(os.path.join(KOK, kaynak_klasor, ad), "rb") as dosya:
            Klasor("ayarlar").upload_data(ad, dosya.read())
    ayarlar = yerel_calistir.senaryo_ayarlari("tam")[0]
    for ad in sema.KAYNAKLAR:
        ayar = kaynak_ayari(ayarlar, ad)
        if ayar.get("yontem") == "dosya":
            with open(os.path.join(KOK, ayar["dosya"]["yol"]), "rb") as dosya:
                Klasor("kaynak_dosyalari").upload_data(ayar["dosya"]["yol"], dosya.read())


def _calistir(*parcalar):
    cikti = io.StringIO()
    with contextlib.redirect_stdout(cikti):
        runpy.run_path(os.path.join(DATAIKU, *parcalar), run_name="__main__")
    return cikti.getvalue()


def test_senaryo_adimlari_ve_aktarim_kontrolu_calisir():
    try:
        _hazirla()
        gece = _calistir("tarifler", "gecelik_calisma.py")
        assert "'karar': 'GECTI'" in gece, gece[-300:]
        # Senaryo günlüğündeki hesap sürümü aktarım kontrolündekiyle karşılaştırılır (README).
        assert "'hesap_surumu': '" in gece
        assert VeriKumesi.depo["sonuc_birlesik"] is not None
        donem = _calistir("tarifler", "donem_sonu.py")
        assert "'karar': 'GECTI'" in donem and "birlesik_donem" in VeriKumesi.depo, donem[-300:]
        kontrol = _calistir("kontrol", "aktarim_kontrol.py")
        # Not defterindeki özet işlevi araclar/ozet.py ile aynı sonucu verir; ayarlar klasöründeki
        # varsayılan params.json ve kaynaklar.json'un özeti de aynıdır (ek dosyalar hariç).
        beklenen = [satir for satir in ozet.satirlar()
                    if satir.split("/")[0] in ozet.PAKETLER + ("degiskenler",)]
        assert len([s for s in beklenen if s.startswith("degiskenler/")]) == len(ozet.AYARLAR)
        assert beklenen and all(satir in kontrol.splitlines() for satir in beklenen)
        assert "params: geçerli" in kontrol and "kaynaklar: geçerli" in kontrol, kontrol[-500:]
        assert "ek ayar dosyaları: params_ek.json, kaynaklar_ek.json" in kontrol
        assert "OKUNAMADI ·" not in kontrol
        for tablo_adi in ("kontrol_tablo", "kontrol_tablo_sql"):
            assert tablo_adi + " · tarih günü korunuyor: True" in kontrol
    finally:
        sys.modules.pop("dataiku", None)


def test_kalite_kalirsa_gecelik_adim_hata_verir():
    try:
        _hazirla()
        Klasor.dosyalar.pop(("kaynak_dosyalari", "/sentetik/veri/kaynak_cekirdek_dosya.csv"))
        assert hata_bekle(Exception, _calistir, "tarifler", "gecelik_calisma.py")
    finally:
        sys.modules.pop("dataiku", None)


def test_aktarim_kontrolu_dataiku_kaynaginin_tarih_turunu_yazar():
    """Saat dilimli kaynak tarihi akşam kaydını ertesi güne kaydırabilir; kurulumda görülsün."""
    try:
        _hazirla()
        ek = json.loads(Klasor.dosyalar[("ayarlar", "/kaynaklar_ek.json")].decode("utf-8"))
        ek["kaynaklar"]["esas_goruntu"] = {"yontem": "dataiku"}
        Klasor("ayarlar").upload_data("kaynaklar_ek.json", json.dumps(ek).encode("utf-8"))
        with open(os.path.join(DATAIKU, "degiskenler", "kaynaklar.json"), encoding="utf-8") as d:
            veri_kumesi = json.load(d)["kaynaklar"]["esas_goruntu"]["dataiku"]["veri_kumesi"]
        tarih = pd.Series(pd.to_datetime(["2026-10-20 22:00"])).dt.tz_localize("UTC")
        VeriKumesi.depo[veri_kumesi] = pd.DataFrame({"dosya_no": ["D-000001"],
                                                     "esas_no": ["2026/1"],
                                                     "kaynak_tarihi": tarih})
        kontrol = _calistir("kontrol", "aktarim_kontrol.py")
        assert ("esas_goruntu · tarih alanı türleri: {'kaynak_tarihi': 'datetime64[ns, UTC]'}"
                in kontrol), kontrol[-800:]
    finally:
        sys.modules.pop("dataiku", None)


def test_aktarim_kontrolu_saat_kaymasini_bos_tabloyu_ve_iliskiyi_dener():
    """5. hücre saati birebir (02:00, 23:30) ve 0 satırlık tabloyu dener; saati üç saat kaydıran
    bağlantıda "saat korunuyor: False" yazar (gün aynı kalsa da). 6. hücre okunan kaynaklarla
    ilişki denetimini çalıştırır."""
    asil = VeriKumesi.get_dataframe

    def kaydiran(self, infer_with_pandas=True, **secenek):
        tablo = asil(self, infer_with_pandas, **secenek)
        if self.ad.startswith("kontrol_tablo"):
            for sutun in tablo.columns:
                if str(tablo[sutun].dtype).startswith("datetime64"):
                    tablo[sutun] = tablo[sutun] + pd.Timedelta(hours=3)
        return tablo
    try:
        _hazirla()
        kontrol = _calistir("kontrol", "aktarim_kontrol.py")
        for tablo_adi in ("kontrol_tablo", "kontrol_tablo_sql"):
            assert tablo_adi + " · saat korunuyor: True" in kontrol, kontrol[-800:]
            assert tablo_adi + " · 0 satırlık tablo yazılıp okunuyor: True" in kontrol
        assert "ilişki · ATAMA_DOSYA · GECTI" in kontrol
        VeriKumesi.get_dataframe = kaydiran
        kontrol = _calistir("kontrol", "aktarim_kontrol.py")
        assert "kontrol_tablo · saat korunuyor: False" in kontrol
        assert "kontrol_tablo · tarih günü korunuyor: True" in kontrol
    finally:
        VeriKumesi.get_dataframe = asil
        sys.modules.pop("dataiku", None)


def test_kurulum_ayar_dosyasi_yokken_de_bastan_sona_calisir():
    """Kurulum not defteri sırayla çalıştırılınca ayarlar henüz yüklenmemişken 4. hücrede
    düşmez; ayarlar yüklenince kaynak veri kümelerini denetler."""
    try:
        sys.modules["dataiku"] = sahte_dataiku.modul()
        cikti = _calistir("kontrol", "kurulum.py")
        assert "kaynaklar.json yok" in cikti and "Sonraki adım" in cikti
        assert "calisma_kaydi" in sahte_dataiku.Proje.olusturulan
        _hazirla()
        cikti = _calistir("kontrol", "kurulum.py")
        assert "kaynaklar.json yok" not in cikti
    finally:
        sys.modules.pop("dataiku", None)
