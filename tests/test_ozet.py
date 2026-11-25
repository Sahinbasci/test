"""araclar/ozet.py testleri."""
import os
import tempfile

from araclar import ozet
from araclar.ozet import dosya_ozeti


def _ozet(metin):
    with tempfile.TemporaryDirectory() as klasor:
        yol = os.path.join(klasor, "ornek.py")
        with open(yol, "w", encoding="utf-8", newline="") as dosya:
            dosya.write(metin)
        return dosya_ozeti(yol)


def test_satir_sonu_boslugu_ve_satir_sonu_bicimi_sayilmaz():
    temel = _ozet("a = 1\nb = 2\n")
    assert _ozet("a = 1   \r\nb = 2\r\n\r\n\n") == temel


def test_kod_farki_yakalanir():
    temel = _ozet("a = 1\nb = 2\n")
    assert _ozet("a = 1\nb = 3\n") != temel
    assert _ozet("a = 1\n    b = 2\n") != temel


def test_aktarim_ozeti_guncel():
    # Şirket ortamındaki aktarım kontrolü bu dosyayla karşılaştırılır; kod değişince
    # "python araclar/ozet.py --yaz" ile yenilenir.
    with open(ozet.OZET_DOSYASI, encoding="utf-8") as dosya:
        assert dosya.read().splitlines() == ozet.satirlar(), "aktarim_ozeti.txt eski"


def test_ozet_ayar_dosyalarini_ve_not_defterlerini_kapsar():
    """Varsayılan ayar dosyaları ve kontrol not defterleri de özettedir (GitHub
    farkı dışında eski bir kaynaklar.json ya da not defteri hücresi görünmüyordu)."""
    adlar = [satir.split(" ")[0] for satir in ozet.satirlar()]
    for ad in ("degiskenler/params.json", "degiskenler/kaynaklar.json",
               "kontrol/kurulum.py", "kontrol/aktarim_kontrol.py"):
        assert ad in adlar, ad
    # Ayar özeti içeriğe bakar: anahtar sırası ve girinti etkilemez, değer ve açıklama etkiler.
    from avukat_perf.surum import json_ozeti
    assert json_ozeti({"a": 1, "b": {"c": 2}}) == json_ozeti({"b": {"c": 2}, "a": 1})
    assert json_ozeti({"a": 1}) != json_ozeti({"a": 2})
    assert json_ozeti({"a": 1, "_not": "x"}) != json_ozeti({"a": 1, "_not": "y"})


def test_paket_ve_betik_listeleri_klasorden_turetilir_ve_kontrolle_ayni():
    """Yeni paket ya da senaryo betiği kendiliğinden özete ve yazım denetimine girer; not
    defterindeki sabit listeler (Dataiku'da depo yok) özetle aynı sırada tutulur."""
    import ast
    import shutil
    import test_yazim
    from yardimci import KOK, KUTUPHANE
    assert ozet.PAKETLER == ozet.paketler() and test_yazim.PAKETLER is ozet.PAKETLER
    kopya = tempfile.mkdtemp()
    try:
        for paket in ozet.PAKETLER:
            os.makedirs(os.path.join(kopya, paket))
            open(os.path.join(kopya, paket, "__init__.py"), "w").close()
        os.makedirs(os.path.join(kopya, "entegrasyon"))
        open(os.path.join(kopya, "entegrasyon", "__init__.py"), "w").close()
        os.makedirs(os.path.join(kopya, "notlar"))  # paket değil
        assert ozet.paketler(kopya) == tuple(sorted(ozet.PAKETLER + ("entegrasyon",)))
    finally:
        shutil.rmtree(kopya)
    assert set(ozet.paketler()) == {ad for ad in os.listdir(KUTUPHANE)
                                    if os.path.isdir(os.path.join(KUTUPHANE, ad))
                                    and not ad.startswith((".", "_"))}
    yol = os.path.join(KOK, "dataiku", "kontrol", "aktarim_kontrol.py")
    with open(yol, encoding="utf-8") as dosya:
        sabitler = {hedef.id: ast.literal_eval(dugum.value)
                    for dugum in ast.parse(dosya.read()).body if isinstance(dugum, ast.Assign)
                    for hedef in dugum.targets if isinstance(hedef, ast.Name)
                    and hedef.id in ("PAKETLER", "SEKMELER", "SENARYOLAR")}
    assert sabitler["PAKETLER"] == ozet.PAKETLER
    assert tuple(ad for _, ad in sabitler["SENARYOLAR"]) == ozet.TARIFLER
    assert tuple(ad for _, ad in sabitler["SEKMELER"]) == ozet.WEBAPP
