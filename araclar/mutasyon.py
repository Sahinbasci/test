"""Mutasyon denetimi: kitaplığa bilerek hata ekler, testlerin yakaladığını doğrular.

Yalnız yerelde çalışır; şirket ortamına taşınmaz. Her hata kodun geçici bir kopyasına
uygulanır, asıl dosyalar değişmez. Liste araclar/mutasyonlar.json dosyasındadır; her
satır [ad, modül, eski metin, yeni metin]; modül dataiku/kutuphane altındaki yoldur
(ör. avukat_perf/kriter1.py; arayüz dosyaları için ../webapp/uygulama.js). Eski metin
modülde tam bir kez geçmelidir. Satır ve modül uzunluğu testleri, aktarım özetinin ve mutasyon
listesinin güncelliği (her değişiklikte kendiliğinden düşer) bu koşuda sayılmaz; yazım
kurallarının geri kalanı (3.7 söz dizimi, adlar, bağımlılıklar) sayılır. Bir mutasyonun test koşusu
ZAMAN_SINIRI saniyeyi aşarsa (ör. sonsuz döngü) "ZAMAN AŞIMI" sorunlu sayılır.
Koşu önce mutasyonsuz kopyada testlerin geçtiğini doğrular; geçmezse durur (aksi hâlde her
mutasyon "yakalandı" görünürdü).
Kullanım: python araclar/mutasyon.py [ad parçası] [--paralel N]
"""
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOPYALANACAK = ("dataiku", "tests", "araclar", "sentetik", "grafana", "minio", "kurulum",
                "pytest.ini", "aktarim_ozeti.txt", "README.md")
SAYILMAYAN = ("tests/test_yazim.py::test_satir_en_cok_100_karakter",
              "tests/test_yazim.py::test_modul_en_cok_120_satir",
              "tests/test_ozet.py::test_aktarim_ozeti_guncel",
              "tests/test_kurulum.py::test_kurulum_paketleri_guncel",
              "tests/test_araclar.py::test_mutasyon_listesi_guncel_kodla_eslesir")
ZAMAN_SINIRI = 3600  # saniye; paralel koşuda tam test birkaç kat yavaşlar
ZAMAN_ASIMI = "ZAMAN_ASIMI"
ETIKETLER = {True: "YAKALANDI", False: "KAÇTI", None: "METİN BULUNAMADI",
             ZAMAN_ASIMI: "ZAMAN AŞIMI"}


def _kopyala(hedef):
    for ad in KOPYALANACAK:
        kaynak = os.path.join(KOK, ad)
        if os.path.isdir(kaynak):
            shutil.copytree(kaynak, os.path.join(hedef, ad),
                            ignore=shutil.ignore_patterns("__pycache__", "onizleme"))
        elif os.path.exists(kaynak):
            shutil.copy(kaynak, hedef)


def _dene(modul, eski, yeni):
    """Hata testlerce yakalanırsa True, metin bulunamazsa None, koşu ZAMAN_SINIRI'nı aşarsa
    ZAMAN_ASIMI döner. modul None ise mutasyonsuz taban koşusudur: testler geçerse False döner."""
    with tempfile.TemporaryDirectory() as gecici:
        _kopyala(gecici)
        if modul is not None:
            yol = os.path.join(gecici, "dataiku", "kutuphane", modul)
            with open(yol, encoding="utf-8") as dosya:
                metin = dosya.read()
            if metin.count(eski) != 1:
                return None
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write(metin.replace(eski, yeni))
        komut = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"]
        for test in SAYILMAYAN:
            komut += ["--deselect", test]
        try:
            sonuc = subprocess.run(komut, cwd=gecici, capture_output=True, timeout=ZAMAN_SINIRI)
        except subprocess.TimeoutExpired:
            return ZAMAN_ASIMI
        return sonuc.returncode != 0


def _is(mutasyon):
    return mutasyon[0], _dene(*mutasyon[1:])


def calistir(arguman):
    paralel = int(arguman[arguman.index("--paralel") + 1]) if "--paralel" in arguman else 1
    secim = [a for a in arguman if a != "--paralel" and not a.isdigit()]
    with open(os.path.join(KOK, "araclar", "mutasyonlar.json"), encoding="utf-8") as dosya:
        mutasyonlar = json.load(dosya)
    if secim:
        mutasyonlar = [m for m in mutasyonlar if secim[0] in m[0] or secim[0] in m[1]]
    if _dene(None, None, None) is not False:
        print("Mutasyonsuz kopyada testler geçmiyor (ya da zaman aşımı); koşu geçersiz olurdu.")
        return False
    havuz = multiprocessing.Pool(paralel) if paralel > 1 else None
    sonuclar = havuz.imap(_is, mutasyonlar) if havuz else map(_is, mutasyonlar)
    sorunlu = 0
    for ad, yakalandi in sonuclar:
        etiket = ETIKETLER[yakalandi]
        sorunlu += yakalandi is not True
        print("{:<44} {}".format(ad, etiket), flush=True)
    if havuz:
        havuz.close()
    print("{} mutasyon, {} sorunlu".format(len(mutasyonlar), sorunlu))
    return sorunlu == 0


if __name__ == "__main__":
    sys.exit(0 if calistir(sys.argv[1:]) else 1)
