"""Depoda gerçek sistem ve kurum adları geçmez; ekranda görünen sistem adları tek yerden gelir.

Yasaklı adlar depoya girmeyen yerel bir dosyadan okunur: kök klasördeki .yasakli_adlar (her
satır büyük-küçük harf duyarsız bir düzenli ifade; # ile başlayan satır açıklama). Dosya yoksa
(ör. şirket bilgisayarında) tarama atlanır. Tek yer testleri her ortamda çalışır.
Taranan dosyalar depoya girecek olanlardır (git ls-files: izlenen ve yok sayılmayan yeni
dosyalar; git yoksa klasör yürüyüşü ve .gitignore'daki adlar). Metin, yol ve kalıp NFC'ye
normalleştirilir: ayrışık (NFD) yazılmış Türkçe harf (ör. PDF'ten kopyalanan metin) kalıptan
kaçmaz. Sentetik veri dosyaları da baştan sona taranır.
"""
import json
import os
import re
import subprocess
import unicodedata

from arayuz import sunum
from avukat_perf.params import dogrula
from avukat_perf.params_sema import GORUNUM
from avukat_perf.sema import KAYNAKLAR, SISTEMLER
from avukat_perf.surum import hesap_surumu
from yardimci import KOK, params_yukle


def _nfc(metin):
    return unicodedata.normalize("NFC", metin)


def _yok_sayilanlar():
    """Git yokken: .gitignore satırları (ad olarak) ve .git."""
    adlar = {".git"}
    yol = os.path.join(KOK, ".gitignore")
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as dosya:
            adlar |= {satir.strip().rstrip("/") for satir in dosya
                      if satir.strip() and not satir.startswith(("#", "*"))}
    return adlar


def kalip(satir):
    return re.compile(_nfc(satir), re.I)


def _kaliplar():
    yol = os.path.join(KOK, ".yasakli_adlar")
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8") as dosya:
        satirlar = [satir.strip() for satir in dosya]
    return [kalip(satir) for satir in satirlar if satir and not satir.startswith("#")]


def _git_dosyalari():
    """Depoya girecek dosyalar (izlenen + yok sayılmayan yeni); git yoksa None."""
    try:
        cikti = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=KOK,
                               capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if cikti.returncode != 0:
        return None
    yollar = [os.path.join(KOK, yol) for yol in cikti.stdout.decode("utf-8").split("\0") if yol]
    return [yol for yol in yollar if os.path.isfile(yol)]  # silinmiş izlenen dosya atlanır


def _dosyalar():
    git = _git_dosyalari()
    if git is not None:
        return [yol for yol in git if not yol.endswith(".pyc")]
    atlanan, bulunan = _yok_sayilanlar(), []
    for kok, klasorler, dosyalar in os.walk(KOK):
        klasorler[:] = [ad for ad in klasorler if ad not in atlanan]
        bulunan += [os.path.join(kok, ad) for ad in dosyalar
                    if ad not in atlanan and not ad.endswith(".pyc")]
    return bulunan


def eslesir(goreli, metin, kaliplar):
    """Dosya yolunda ya da metninin herhangi bir yerinde yasaklı kalıp geçiyor mu (NFC)."""
    goreli, metin = _nfc(goreli), _nfc(metin)
    return any(k.search(metin) or k.search(goreli) for k in kaliplar)


def test_depoda_yasakli_ad_yok():
    kaliplar, bulgular = _kaliplar(), []
    for yol in _dosyalar() if kaliplar else []:
        goreli = os.path.relpath(yol, KOK)
        try:
            with open(yol, encoding="utf-8") as dosya:
                metin = dosya.read()
        except (UnicodeDecodeError, OSError):
            metin = ""
        if eslesir(goreli, metin, kaliplar):
            bulgular.append(goreli)
    assert not bulgular, sorted(set(bulgular))


def test_tarama_ayrisik_harfi_ve_veri_satirlarini_yakalar():
    """NFD yazılmış Türkçe metin ve sentetik verinin ilk satırdan sonraki satırları da taranır;
    yerel ek ayar dosyası ve docs/ taranmaz."""
    ornek = [kalip("çalışma")]
    assert eslesir("notlar.md", unicodedata.normalize("NFD", "bu çalışma"), ornek)
    assert eslesir("sentetik/veri/x.csv", "a,b\n1,çalışma\n", ornek)
    assert not eslesir("notlar.md", "calisma", ornek)
    goreli = {os.path.relpath(yol, KOK).replace(os.sep, "/") for yol in _dosyalar()}
    assert "tests/test_gizlilik.py" in goreli and "README.md" in goreli
    assert not [yol for yol in goreli if yol.startswith("docs/") or yol.endswith("_ek.json")
                and yol.startswith("dataiku/degiskenler/") or yol == ".yasakli_adlar"]


def test_sistem_adlari_yalniz_parametrede_tanimli():
    params = params_yukle()
    adlar = {kod: ad for kod, ad in params[GORUNUM]["sistem_adlari"].items()
             if not kod.startswith("_")}
    assert sorted(adlar) == sorted(SISTEMLER)
    assert {kaynak["sistem"] for kaynak in KAYNAKLAR.values()} <= set(SISTEMLER)
    for ad in ("uygulama.js", "index.html"):
        with open(os.path.join(KOK, "dataiku", "webapp", ad), encoding="utf-8") as dosya:
            metin = dosya.read()
        assert not [gorunen for gorunen in adlar.values() if gorunen in metin], ad


def test_ad_degisikligi_yalniz_ekrani_degistirir():
    params = params_yukle()
    yeni = json.loads(json.dumps(params))
    yeni[GORUNUM]["sistem_adlari"]["dava_takip"] = "Yeni Ad"
    assert hesap_surumu(yeni) == hesap_surumu(params) and dogrula(yeni) == []
    tablolar = {ad: None for ad in sunum.TABLOLAR}
    for sayfa in ("genel", "veri"):
        adlar = sunum.sayfa(sayfa, tablolar, yeni)["bilesenler"]["ortak.adlar"]
        sistem = {kayit.get("kod", kayit.get("sistem")): kayit["ad"] for kayit in adlar
                  if kayit.get("tur", "sistem") == "sistem"}
        assert sistem["dava_takip"] == "Yeni Ad"
    eksik = json.loads(json.dumps(params))
    del eksik[GORUNUM]["sistem_adlari"]["cekirdek"]
    assert dogrula(eksik)
    bos = json.loads(json.dumps(params))
    bos[GORUNUM]["sistem_adlari"]["cekirdek"] = " "
    assert dogrula(bos)
