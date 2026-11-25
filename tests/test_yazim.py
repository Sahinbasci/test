"""Yazım kuralları denetimi.

Yalnız yerelde çalışır (Python 3.8 ve üstünü ister); şirket ortamına taşınmaz.
Kitaplık paketleri ve Dataiku'ya yapıştırılan betikler (tarifler, kontrol, web uygulaması arka
ucu) Dataiku'nun bilinmeyen Python sürümü için 3.7 uyumlu kalmalıdır. test_kos.py'nin uyarı
kuralları da burada denetlenir.
"""
import ast
import configparser
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
import tokenize
import warnings

from araclar import test_kos as kosucu  # adı test_ ile başlamaz: test sanılmasın
from araclar.ozet import PAKETLER  # kütüphane klasöründen türetilir (__init__.py taşıyanlar)
from yardimci import KOK, KUTUPHANE

SATIR_SINIRI = 100
MODUL_SINIRI = 120
ORTAK_IZIN = {"avukat_perf", "pandas", "math", "json", "hashlib", "datetime", "re", "decimal"}
IZINLI_MODULLER = {
    "avukat_perf": ORTAK_IZIN | {"os"},  # os: kod özeti için kitaplık dosyalarını okur (surum)
    "hat": ORTAK_IZIN | {"hat", "urllib", "time", "os", "io", "gzip", "random", "socket",
                         "base64", "uuid", "dataiku", "shutil", "tempfile", "http", "ssl",
                         "copy"},
    "arayuz": ORTAK_IZIN | {"arayuz", "hat"},  # hat: çalışma kaydının biçimi (calisma)
}
YENI_SURUM_ADLARI = {"removeprefix", "removesuffix"}
# feature_version yalnız yardımcıdır; Python 3.9 3.7 kipinde de şunları kabul ediyor: ":=",
# konuma bağlı parametre, finally içinde continue, parantezsiz "return 1, *x" ve
# "for i in *a, *b:", 3.9 dekoratör biçimi, "with (a as b):" ve tip açıklamasında "X | Y" ya da
# "list[int]". Hepsi ayrıca aranır.
# f-string 3.6'da vardır ama 3.8'deki "{x=}" biçimini önlemek için kitaplıkta kullanılmaz;
# betiklerde f-string serbesttir, yalnız "{x=}" biçimi yasaktır.
ESITTIRLI_FSTRING = re.compile(r"\{[^{}]*?[^{}=!<>]\s*=\s*(![rsa])?\s*(:[^{}]*)?\}")
BETIK_KLASORLERI = ("tarifler", "kontrol", "webapp")  # webapp: backend.py
YERLESIK_TURLER = {"list", "dict", "tuple", "set", "frozenset", "type"}
DONGULER = (ast.For, ast.AsyncFor, ast.While)
ISLEVLER = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
AD_KALIBI = re.compile(r"^(_*[a-z][a-z0-9_]*|_*[A-Z][A-Z0-9_]*|_)$")


def _dosyalar(klasor):
    return [os.path.join(klasor, ad) for ad in sorted(os.listdir(klasor)) if ad.endswith(".py")]


def _kitaplik():
    for paket in PAKETLER:
        for yol in _dosyalar(os.path.join(KUTUPHANE, paket)):
            yield paket, yol


def _oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def _dugumler(yol):
    return ast.walk(ast.parse(_oku(yol), filename=yol))


def _betikler():
    """Dataiku'ya yapıştırılan betikler: tarifler, kontrol, web uygulamasının arka ucu ve kurulum
    klasörünün adım dosyaları (yapıştırma paketleri dahil)."""
    return [yol for klasor in BETIK_KLASORLERI
            for yol in _dosyalar(os.path.join(KOK, "dataiku", klasor))] + _dosyalar(
                os.path.join(KOK, "kurulum"))


def _finally_continue(deneme):
    """finally gövdesinde, iç döngü ya da işleve girmeden ulaşılan continue (3.8'de geldi)."""
    bekleyen = list(deneme.finalbody)
    while bekleyen:
        dugum = bekleyen.pop()
        if isinstance(dugum, ast.Continue):
            return True
        if isinstance(dugum, DONGULER):
            bekleyen.extend(dugum.orelse)  # döngünün else'indeki continue dış döngünündür
        elif not isinstance(dugum, ISLEVLER):
            bekleyen.extend(ast.iter_child_nodes(dugum))
    return False


def _eski_dekorator(ifade):
    """3.9'dan önceki dekoratör biçimi: noktalı ad, ardından en çok bir çağrı."""
    ifade = ifade.func if isinstance(ifade, ast.Call) else ifade
    while isinstance(ifade, ast.Attribute):
        ifade = ifade.value
    return isinstance(ifade, ast.Name)


def _tip_aciklamalari(dugum):
    if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return [dugum.returns] if dugum.returns else []
    if isinstance(dugum, ast.arg):
        return [dugum.annotation] if dugum.annotation else []
    return [dugum.annotation] if isinstance(dugum, ast.AnnAssign) else []


def _yeni_tip(aciklama):
    """X | Y (3.10) ya da list[int] gibi yerleşik tür altsimgesi (3.9); 3.7'de tanımda çöker."""
    for alt in ast.walk(aciklama):
        if isinstance(alt, ast.BinOp) and isinstance(alt.op, ast.BitOr):
            return True
        if isinstance(alt, ast.Subscript) and isinstance(alt.value, ast.Name) and \
                alt.value.id in YERLESIK_TURLER:
            return True
    return False


def _parantezli_with(kaynak, dugum):
    """with (a as b, c as d): biçimi; with (a) as b: ve with (a, b): 3.7'de de geçerlidir."""
    metin = ast.get_source_segment(kaynak, dugum)
    baslik, derinlik = [], 0
    for parca in tokenize.generate_tokens(io.StringIO(metin).readline):
        derinlik += {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}.get(parca.string, 0)
        if parca.string == ":" and derinlik == 0:
            break
        if parca.type in (tokenize.NL, tokenize.COMMENT) or (
                not baslik and parca.string in ("async", "with")):
            continue
        baslik.append((parca.string, derinlik))
    # Başlığı tek bir parantez sarıyor (kapanana dek derinlik 1 ve üstü) ve içinde "as" var.
    return len(baslik) > 1 and baslik[0] == ("(", 1) and baslik[-1] == (")", 0) and all(
        d >= 1 for _, d in baslik[:-1]) and ("as", 1) in baslik


def _parantezli(metin):
    """Metin baştan sona tek bir parantez çiftinin içinde mi: "(1, *x)" evet, "(1,), *x" hayır."""
    atla = (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.ENDMARKER)
    parcalar = [parca.string for parca in tokenize.generate_tokens(io.StringIO(metin).readline)
                if parca.type not in atla]
    derinlik = 0
    for sira, parca in enumerate(parcalar):
        derinlik += {"(": 1, ")": -1}.get(parca, 0)
        if derinlik == 0:
            return parca == ")" and sira == len(parcalar) - 1
    return False


def _yildizli_demet(kaynak, dugum):
    """Yıldızlı öğeli parantezsiz demet: return ve yield (3.8), for döngüsünün yinelenen (3.9)."""
    if isinstance(dugum, (ast.Return, ast.Yield)):
        demet = dugum.value
    elif isinstance(dugum, (ast.For, ast.AsyncFor)):
        demet = dugum.iter
    else:
        return False
    return isinstance(demet, ast.Tuple) and any(
        isinstance(oge, ast.Starred) for oge in demet.elts) and not _parantezli(
        ast.get_source_segment(kaynak, demet))


def _yeni_bicim(kaynak, dugum):
    """3.8 ve sonrasında gelen, 3.9 ayrıştırıcısının 3.7 kipinde kabul ettiği biçimin adı."""
    if isinstance(dugum, ast.NamedExpr):
        return ":="
    if isinstance(dugum, ast.arguments) and dugum.posonlyargs:
        return "konuma bağlı parametre"
    if isinstance(dugum, ast.Attribute) and dugum.attr in YENI_SURUM_ADLARI:
        return dugum.attr
    if isinstance(dugum, ast.Try) and _finally_continue(dugum):
        return "finally içinde continue"
    if _yildizli_demet(kaynak, dugum):
        return "parantezsiz yıldızlı demet"
    if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not all(
            _eski_dekorator(ifade) for ifade in dugum.decorator_list):
        return "dekoratör biçimi"
    if isinstance(dugum, (ast.With, ast.AsyncWith)) and _parantezli_with(kaynak, dugum):
        return "parantezli with"
    if any(_yeni_tip(aciklama) for aciklama in _tip_aciklamalari(dugum)):
        return "tip açıklaması"
    return None


def _sozdizimi_hatalari(kaynak, ad, fstring_yasak):
    """Python 3.7'de olmayan söz dizimi (bkz. _yeni_bicim), 3.9 metin yöntemleri, f-string'in
    "{x=}" biçimi; fstring_yasak ise her f-string. ["ad:satır ..."] listesi."""
    try:
        agac = ast.parse(kaynak, filename=ad, feature_version=(3, 7))
    except SyntaxError as hata:
        return ["{}:{} {}".format(ad, hata.lineno, hata.msg)]
    hatalar = []
    for dugum in ast.walk(agac):
        yer = "{}:{}".format(ad, getattr(dugum, "lineno", "?"))
        bicim = _yeni_bicim(kaynak, dugum)
        if bicim:
            hatalar.append(yer + " " + bicim)
        elif isinstance(dugum, ast.JoinedStr):
            metin = ast.get_source_segment(kaynak, dugum) or ""
            metin = metin.replace("{{", "").replace("}}", "")
            if fstring_yasak or ESITTIRLI_FSTRING.search(metin):
                hatalar.append(yer + " f-string")
    return hatalar


def test_satir_en_cok_100_karakter():
    klasorler = [os.path.join(KOK, ad) for ad in ("tests", "araclar", "sentetik")]
    klasorler += [os.path.join(KUTUPHANE, paket) for paket in PAKETLER]
    klasorler += [os.path.join(KOK, "dataiku", ad) for ad in ("tarifler", "webapp", "kontrol")]
    for klasor in klasorler:
        for yol in _dosyalar(klasor):
            for no, satir in enumerate(_oku(yol).splitlines(), 1):
                assert len(satir) <= SATIR_SINIRI, "{}:{}".format(yol, no)


def test_modul_en_cok_120_satir():
    for _, yol in _kitaplik():
        assert len(_oku(yol).splitlines()) <= MODUL_SINIRI, yol


def test_python_37_sozdizimi():
    for _, yol in _kitaplik():
        assert _sozdizimi_hatalari(_oku(yol), yol, fstring_yasak=True) == []


def test_dataikuya_yapistirilan_betikler_python_37_sozdizimi():
    betikler = _betikler()
    assert {os.path.basename(yol) for yol in betikler} >= {
        "gecelik_calisma.py", "donem_sonu.py", "aktarim_kontrol.py", "kurulum.py", "backend.py",
        "adim_01_surum_kontrolu.py", "adim_02_kutuphane_avukat_perf.py",
        "adim_04_ayarlar_ve_sentetik_veri.py"}
    for yol in betikler:
        assert _sozdizimi_hatalari(_oku(yol), yol, fstring_yasak=False) == []


def test_sozdizimi_denetimi_yasaklari_yakalar_izinlileri_gecirir():
    yasak = ['x = (y := 1)\n', '[z for a in b if (z := a)]\n', 'def f(a, /, b):\n    pass\n',
             's.removeprefix("a")\n', 's.removesuffix("a")\n', 'f"{x=}"\n',
             'f"{x = !r:>5}"\n', 'f"{d[0]=:.2f}"\n', 'print("a", f"b {x=}")\n']
    izinli = ['x = 1\n', 'f"{x}"\n', 'f"{x!r:>5}"\n', 'f"{a == b}"\n', 'f"{a != b}"\n',
              'f"{a <= b} {a >= b}"\n', 'f"{x:=^10}"\n', 'f"{{x=}}"\n', 'f"{f(a=1)}"\n',
              '"{x=}".format(x=1)\n', 's.replace("a", "")\n', 'def f(a, *, b):\n    pass\n']
    for kaynak in yasak:
        assert _sozdizimi_hatalari(kaynak, "betik", fstring_yasak=False), kaynak
    for kaynak in izinli:
        assert _sozdizimi_hatalari(kaynak, "betik", fstring_yasak=False) == [], kaynak
    # Kitaplıkta her f-string yasaktır; f-string olmayan izinli satırlar yine geçer.
    assert _sozdizimi_hatalari('f"{x}"\n', "kitaplik", fstring_yasak=True)
    assert _sozdizimi_hatalari('"{x}".format(x=1)\n', "kitaplik", fstring_yasak=True) == []


DONGU = "for i in x:\n    try:\n        pass\n    finally:\n"
YENI_BICIMLER = {  # 3.9 ayrıştırıcısı 3.7 kipinde kabul ediyor; 3.7'de SyntaxError ya da çöküş
    "finally içinde continue": [DONGU + "        continue\n",
                                DONGU + "        if i:\n            continue\n",
                                DONGU + "        for j in y:\n            pass\n"
                                        "        else:\n            continue\n"],
    "parantezsiz yıldızlı demet": ["def f():\n    return 1, *x\n", "def f():\n    yield 1, *x\n",
                                   "def f():\n    y = yield 1, *x\n",
                                   "def f():\n    return (1,), *x\n",
                                   "for i in *a, *b:\n    pass\n", "for i in (a), *b:\n    pass\n",
                                   "async def f():\n    async for i in *a,:\n        pass\n"],
    "dekoratör biçimi": ["@a[0].b\ndef f():\n    pass\n", "@a(1)(2)\ndef f():\n    pass\n",
                         "@(lambda f: f)\nclass A:\n    pass\n"],
    "parantezli with": ["with (a as b):\n    pass\n", "with (a as b, c as d):\n    pass\n",
                        "with (\n    a as b,  # yorum\n    c,\n):\n    pass\n",
                        "async def f():\n    async with (a as b):\n        pass\n"],
    "tip açıklaması": ["def f(a: int | None):\n    pass\n", "def f() -> list[int]:\n    pass\n",
                       "x: dict[str, int] = {}\n", "def f(a: Optional[tuple[int]]):\n    pass\n"],
}
ESKI_BICIMLER = [  # yenilerin 3.7'de geçerli yakın benzerleri
    DONGU + "        for j in y:\n            continue\n",
    "for i in x:\n    try:\n        continue\n    finally:\n        pass\n",
    DONGU + "        def g():\n            for j in y:\n                continue\n",
    "def f():\n    return (1, *x)\n", "def f():\n    yield (1, *x)\n", "x = 1, *y\n",
    "def f():\n    return (\n        1, *x)\n", "for i in (*a, *b):\n    pass\n",
    "for i in a, b:\n    pass\n", "for a, *b in c:\n    pass\n",
    "def f():\n    return 1, 2\n", "@a.b.c\ndef f():\n    pass\n",
    "@a.b(1, k=2)\nclass A:\n    pass\n", "with (a) as b, (c) as d:\n    pass\n",
    "with (a, b):\n    pass\n", "with a as b, c as d:\n    pass\n", "with (a):\n    pass\n",
    "with (a, b) as c:\n    pass\n", "with f(x, y) as (b, c):\n    pass\n",
    "def f(a: int, b: 'int | None' = None) -> List[int]:\n    pass\n", "x = a | b\n",
    "y: Dict[str, int] = d[0]\n"]


def test_sozdizimi_denetimi_37_kipinde_kabul_edilen_yeni_bicimleri_yakalar():
    for bicim, kaynaklar in YENI_BICIMLER.items():
        for kaynak in kaynaklar:
            assert [hata.split(" ", 1)[1] for hata in _sozdizimi_hatalari(
                kaynak, "betik", fstring_yasak=False)] == [bicim], kaynak
    for kaynak in ESKI_BICIMLER:
        assert _sozdizimi_hatalari(kaynak, "betik", fstring_yasak=False) == [], kaynak


def test_tanimlayicilar_ascii_snake_case():
    for _, yol in _kitaplik():
        for dugum in _dugumler(yol):
            if isinstance(dugum, (ast.FunctionDef, ast.ClassDef)):
                ad = dugum.name if isinstance(dugum, ast.FunctionDef) else dugum.name.lower()
            elif isinstance(dugum, ast.arg):
                ad = dugum.arg
            elif isinstance(dugum, ast.Name) and isinstance(dugum.ctx, ast.Store):
                ad = dugum.id
            else:
                continue
            assert AD_KALIBI.match(ad), "{}: {}".format(yol, ad)


def test_yalniz_izinli_bagimliliklar():
    for paket, yol in _kitaplik():
        for dugum in _dugumler(yol):
            if isinstance(dugum, ast.Import):
                adlar = [takma.name for takma in dugum.names]
            elif isinstance(dugum, ast.ImportFrom) and dugum.level == 0:
                adlar = [dugum.module]
            else:
                continue
            for ad in adlar:
                assert ad.split(".")[0] in IZINLI_MODULLER[paket], "{}: {}".format(yol, ad)


def test_test_kos_uyari_kurallari_pytest_ini_ile_ayni():
    ayar = configparser.ConfigParser()
    ayar.read(os.path.join(KOK, "pytest.ini"), encoding="utf-8")
    satirlar = [satir.strip() for satir in ayar["pytest"]["filterwarnings"].splitlines()]
    assert tuple(satir for satir in satirlar if satir) == kosucu.UYARI_KURALLARI


def _uyar(tur, modul):
    return lambda: warnings.warn_explicit("eski kullanım", tur, "ornek.py", 1, module=modul)


def test_test_kos_uyariyi_hata_sayar_ve_suzgecleri_geri_alir():
    onceki = list(warnings.filters)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # pytest'siz ortam: uyarı kendiliğinden hata değil
        assert "FutureWarning: eski kullanım" in kosucu.calistir(_uyar(FutureWarning, "hat.akis"))
        assert "DeprecationWarning" in kosucu.calistir(_uyar(DeprecationWarning, "hat.akis"))
        assert "DeprecationWarning" in kosucu.calistir(_uyar(DeprecationWarning, "werkzeug"))
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # flask'ın kullanımdan kalkma uyarısı yok sayılır
        assert kosucu.calistir(_uyar(DeprecationWarning, "flask")) is None
        assert kosucu.calistir(_uyar(DeprecationWarning, "flask.app")) is None
        assert "FutureWarning" in kosucu.calistir(_uyar(FutureWarning, "flask"))
    assert kosucu.calistir(lambda: None) is None
    assert "AssertionError" in kosucu.calistir(lambda: _dogrula(False))
    assert warnings.filters == onceki


def _dogrula(kosul):
    assert kosul


ORNEK_TESTLER = {
    "test_ornek_kos_a.py": "import warnings\n\ntest_sabit = 5  # çağrılamaz: atlanır\n\n\n"
                           "def test_gecer():\n    pass\n\n\n"
                           "def test_uyarir():\n    warnings.warn('eski', FutureWarning)\n\n\n"
                           "def test_duser():\n    assert False\n",
    "test_ornek_kos_b.py": "import warnings\n\nwarnings.warn('eski', FutureWarning)\n"}


def _kos(dosyalar):
    """test_kos.kos'u yalnız verilen test dosyalarının bulunduğu geçici klasörde çalıştırır."""
    klasor, yol, cikti = tempfile.mkdtemp(), list(sys.path), io.StringIO()
    asil = kosucu.TESTLER
    try:
        for ad in dosyalar:
            with open(os.path.join(klasor, ad), "w", encoding="utf-8") as dosya:
                dosya.write(ORNEK_TESTLER[ad])
        kosucu.TESTLER = klasor
        with contextlib.redirect_stdout(cikti), warnings.catch_warnings():
            warnings.simplefilter("ignore")  # pytest'siz ortam: uyarı kendiliğinden hata değil
            try:
                return kosucu.kos(), cikti.getvalue()
            except Exception as hata:
                return hata, cikti.getvalue()
    finally:
        kosucu.TESTLER, sys.path[:] = asil, yol
        for ad in dosyalar:
            sys.modules.pop(ad[:-3], None)
        shutil.rmtree(klasor)


def test_test_kos_uyari_veren_testi_kaldi_sayar():
    sonuc, cikti = _kos(["test_ornek_kos_a.py"])
    assert sonuc is False and cikti.splitlines()[-1] == "1 geçti, 2 kaldı"
    kalanlar = [satir for satir in cikti.splitlines() if satir.startswith("KALDI")]
    assert kalanlar == ["KALDI test_ornek_kos_a.py::test_duser",
                        "KALDI test_ornek_kos_a.py::test_uyarir"]
    assert "FutureWarning: eski" in cikti
    # İçe aktarırken çıkan uyarı da hata sayılır (pytest'te toplama hatası).
    sonuc, _ = _kos(["test_ornek_kos_b.py"])
    assert isinstance(sonuc, FutureWarning)
