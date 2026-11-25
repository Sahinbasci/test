"""Kurulum klasörü: yapıştırma paketlerinin güncelliği ve sahte Dataiku'da çalışması."""
import os
import re
import sys
import types

from yardimci import KOK

sys.path.insert(0, os.path.join(KOK, "araclar"))
import paketle  # noqa: E402

KURULUM = os.path.join(KOK, "kurulum")


def _oku(*parcalar, ikili=False):
    with open(os.path.join(KOK, *parcalar), "rb" if ikili else "r",
              **({} if ikili else {"encoding": "utf-8"})) as dosya:
        return dosya.read()


class _Dosya(object):
    def __init__(self, ad, bozuk=False):
        self.name, self.icerik, self.bozuk = ad, None, bozuk

    def write(self, veri):
        self.icerik = veri

    def read(self):
        return self.icerik + ("# fark\n" if self.bozuk else "")


class _Klasor(object):
    def __init__(self, ad, bozuk=False):
        self.name, self.ogeler, self.bozuk = ad, {}, bozuk

    def get_child(self, ad):
        return self.ogeler.get(ad)

    def add_folder(self, ad):
        self.ogeler[ad] = _Klasor(ad, self.bozuk)
        return self.ogeler[ad]

    def add_file(self, ad):
        self.ogeler[ad] = _Dosya(ad, self.bozuk)
        return self.ogeler[ad]


def _calistir(metin, proje=None, klasorler=None):
    """Paketi sahte dataiku modülüyle çalıştırır; (çıkış iletisi ya da None)."""
    sahte = types.ModuleType("dataiku")
    sahte.api_client = lambda: types.SimpleNamespace(get_default_project=lambda: proje)

    class Folder(object):
        def __init__(self, ad):
            self.ad = ad

        def upload_data(self, yol, veri):
            klasorler.setdefault(self.ad, {})[yol] = veri

    sahte.Folder = Folder
    onceki = sys.modules.get("dataiku")
    sys.modules["dataiku"] = sahte
    try:
        exec(compile(metin, "paket", "exec"), {"__name__": "__main__", "print": lambda *a: None})
    except SystemExit as cikis:
        return str(cikis)
    finally:
        if onceki is None:
            del sys.modules["dataiku"]
        else:
            sys.modules["dataiku"] = onceki
    return None


def _proje(python):
    kutuphane = types.SimpleNamespace(get_folder=lambda yol: python if yol == "/python" else None)
    return types.SimpleNamespace(get_library=lambda: kutuphane)


def test_kurulum_paketleri_guncel():
    """Paketler ve kopyalar koddan üretilenle aynı (kod değişince: python araclar/paketle.py)."""
    for ad, metin in paketle.uretilecekler().items():
        assert _oku("kurulum", ad) == metin, ad + " eski: python araclar/paketle.py"


def test_kutuphane_paketi_dosyalari_yazar_ve_geri_okuyarak_dogrular():
    for paket in paketle.PAKETLER:
        metin = _oku("kurulum", "adim_02_kutuphane_{}.py".format(paket))
        gomulu = {}
        exec(compile(metin.split("\n# ---------- kütüphaneye yazma")[0], "paket", "exec"),
             {"__name__": "x"}, gomulu)
        python = _Klasor("python")
        assert _calistir(metin, _proje(python)) is None
        yazilan = {ad: dosya.icerik for ad, dosya in python.ogeler[paket].ogeler.items()}
        assert yazilan == gomulu["DOSYALAR"] and set(yazilan) == set(gomulu["OZET"])
        assert len(yazilan) == len([ad for ad in os.listdir(os.path.join(
            KOK, "dataiku", "kutuphane", paket)) if ad.endswith(".py")])
        # Var olan dosyanın üzerine yazılır (ikinci çalıştırma da geçer).
        assert _calistir(metin, _proje(python)) is None


def test_kutuphane_paketi_api_yoksa_ve_icerik_farkliysa_durur():
    metin = _oku("kurulum", "adim_02_kutuphane_arayuz.py")
    ileti = _calistir(metin, types.SimpleNamespace())
    assert ileti and "kütüphane API'si yok" in ileti
    ileti = _calistir(metin, _proje(_Klasor("python", bozuk=True)))
    assert ileti and ileti.startswith("Geri okunan içerik farklı")
    bos = types.SimpleNamespace(get_library=lambda: types.SimpleNamespace(
        get_folder=lambda yol: None))
    assert "python klasörü bulunamadı" in _calistir(metin, bos)


def test_ayar_paketi_ayarlari_ve_sentetik_veriyi_depodakiyle_ayni_yukler():
    metin = _oku("kurulum", "adim_04_ayarlar_ve_sentetik_veri.py")
    klasorler = {}
    assert _calistir(metin, klasorler=klasorler) is None
    beklenen = {"params.json": ("dataiku", "degiskenler", "params.json"),
                "kaynaklar.json": ("dataiku", "degiskenler", "kaynaklar.json"),
                "params_ek.json": ("sentetik", "params_ek.json"),
                "kaynaklar_ek.json": ("sentetik", "kaynaklar_ek.json")}
    assert {ad: veri for ad, veri in klasorler["ayarlar"].items()} == {
        ad: _oku(*yol, ikili=True) for ad, yol in beklenen.items()}
    csvler = sorted(ad for ad in os.listdir(os.path.join(KOK, "sentetik", "veri")))
    assert klasorler["kaynak_dosyalari"] == {
        "sentetik/veri/" + ad: _oku("sentetik", "veri", ad, ikili=True) for ad in csvler}
    assert len(csvler) == 10
    # Canlı projede yalnız iki varsayılan ayar dosyası yazılır.
    canli = {}
    assert _calistir(metin.replace("PROVA = True", "PROVA = False", 1), klasorler=canli) is None
    assert set(canli) == {"ayarlar"} and set(canli["ayarlar"]) == {"params.json", "kaynaklar.json"}


def test_rehber_her_adim_dosyasini_anar_ve_depoda_ic_ad_yok():
    rehber = _oku("kurulum", "README.md")
    adim_dosyalari = sorted(ad for ad in os.listdir(KURULUM) if ad.startswith("adim_"))
    assert len(adim_dosyalari) == 7
    for ad in adim_dosyalari:
        kok = ad[:-3]
        assert kok in rehber or ad in rehber or kok.rsplit("_", 1)[0] in rehber, ad
    # Rehberdeki adımlar sırayla numaralı ve tablodaki dosyalar mevcut.
    for yol in re.findall(r"`(kurulum/adim_[a-z0-9_]+\.py)`", rehber):
        assert os.path.exists(os.path.join(KOK, yol)), yol


def test_sema_ozeti_satir_degeri_gostermez():
    """Şema özeti satır sayısını, türü, boş oranını ve biçim maskesini yazar; satır değeri yazmaz
    (yalnız DEGER_LISTESI'ndeki kod sütununun değerleri)."""
    import pandas as pd
    tablo = pd.DataFrame({"Dosya No": ["D-000123", "D-000124", None],
                          "Branş": ["DAHİLİ SU", "Kasko", "Kasko"],
                          "Tutar": ["1.234,56", "98,70", " "],
                          "Tarih": ["05.11.2026", "01.02.2024", None]})
    sahte = types.ModuleType("dataiku")
    sahte.Dataset = lambda ad: types.SimpleNamespace(
        get_dataframe=lambda **_: tablo,
        read_schema=lambda: [{"name": "Dosya No", "type": "string"}])
    metin = _oku("kurulum", "sema_ozeti.py").replace(
        'VERI_KUMELERI = []', 'VERI_KUMELERI = ["pbi"]').replace(
        'DEGER_LISTESI = {}', 'DEGER_LISTESI = {"pbi": ["Branş"]}')
    cikti, onceki = [], sys.modules.get("dataiku")
    sys.modules["dataiku"] = sahte
    try:
        exec(compile(metin, "sema", "exec"),
             {"__name__": "__main__", "print": lambda *a: cikti.append(" ".join(map(str, a)))})
    finally:
        if onceki is None:
            del sys.modules["dataiku"]
        else:
            sys.modules["dataiku"] = onceki
    hepsi = "\n".join(cikti)
    assert cikti[0] == "== pbi: 3 satır, 4 sütun"
    assert "- Dosya No | tür string | boş %33.3 | 2 farklı | biçim: A-999999" in hepsi
    assert "biçim: 9.999,99, 99,99" in hepsi and "biçim: 99.99.9999" in hepsi
    assert "değerler (2): DAHİLİ SU | Kasko" in hepsi
    for gizli in ("D-000123", "1.234,56", "98,70", "05.11.2026", "01.02.2024"):
        assert gizli not in hepsi, gizli
