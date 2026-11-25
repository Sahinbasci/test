"""Tek kaynak kuralı: bir değer projede tek yerde tanımlanır (README, "Tek kaynak").

- Renk yalnız stil.css :root değişkenlerindedir; kurallar, JS ve HTML değişken kullanır ve
  kullanılan her değişken tanımlıdır (yazım hatası renksiz öğe bırakırdı).
- Ekranda görünen sistem adları yalnız params.json gorunum.sistem_adlari'ndadır; kodda metin
  sabiti olarak geçmez (açıklama ve yorum serbesttir: ekrana gelmez).
- Veri kümesi ve klasör adları hat/veri_kumeleri.py'dedir: koddaki her sonuc_, model_, gozlem_,
  kontrol_ adı o listede olmalı (yazım hatası ya da listeye eklenmemiş tablo yakalanır);
  klasör adları başka modülde yazılmaz.
"""
import ast
import glob
import json
import os
import re

from hat import veri_kumeleri as vk
from yardimci import KOK

WEBAPP = os.path.join(KOK, "dataiku", "webapp")
RENK = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(")


def _oku(yol):
    with open(yol, encoding="utf-8-sig") as dosya:
        return dosya.read()


def _css():
    """(:root gövdesi, kurallar) yorumlar çıkarılmış."""
    css = re.sub(r"/\*.*?\*/", " ", _oku(os.path.join(WEBAPP, "stil.css")), flags=re.S)
    kok = re.search(r":root\s*\{(.*?)\}", css, re.S)
    return kok.group(1), css[:kok.start()] + css[kok.end():]


def test_renk_yalniz_kok_degiskenlerinde():
    kok, kurallar = _css()
    degerler = re.findall(r"[a-z-]+\s*:\s*([^;{}]+)", kurallar)
    assert not [deger for deger in degerler if RENK.search(deger)]
    for ad in ("uygulama.js", "index.html"):
        assert not RENK.search(_oku(os.path.join(WEBAPP, ad))), ad
    # Bileşene özgü değişkenler (--sv-renk) kuralda ya da JS'te atanır. JS'te ön ek + seviye ile
    # kurulan adlar (gölge modda "--golge-" + sari/turuncu/kirmizi) seviyelerin her biri için
    # tanımlı olmalı.
    js = _oku(os.path.join(WEBAPP, "uygulama.js"))
    html = _oku(os.path.join(WEBAPP, "index.html"))
    tanimli = set(re.findall(r"(--[a-z0-9-]+)\s*:", kok + kurallar + js + html))
    kullanilan = set(re.findall(r"var\((--[a-z0-9-]+)", kok + kurallar + js + html))
    on_ekler = {ad for ad in kullanilan if ad.endswith("-")}
    eksik = sorted(kullanilan - on_ekler - tanimli)
    # Branş paleti sıralıdır ("--brans-" + sıra, 1..BRANS_PALET_BOYU).
    palet = int(re.search(r"var BRANS_PALET_BOYU = (\d+);", js).group(1))
    ekler = {"--brans-": [str(sira) for sira in range(1, palet + 1)]}
    eksik += [ek + son for ek in on_ekler for son in ekler.get(ek, ("sari", "turuncu", "kirmizi"))
              if ek + son not in tanimli]
    assert not eksik, eksik


def _kod_dosyalari(uzantilar):
    for yol in glob.glob(os.path.join(KOK, "dataiku", "**", "*"), recursive=True):
        if os.path.splitext(yol)[1] in uzantilar and "__pycache__" not in yol:
            yield yol


def _metin_sabitleri(yol):
    """Python dosyasındaki metin sabitleri; modül, sınıf ve işlev açıklamaları hariç."""
    agac = ast.parse(_oku(yol))
    aciklamalar = {id(dugum.body[0].value) for dugum in ast.walk(agac)
                   if isinstance(dugum, (ast.Module, ast.ClassDef, ast.FunctionDef))
                   and dugum.body and isinstance(dugum.body[0], ast.Expr)}
    return [dugum.value for dugum in ast.walk(agac)
            if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)
            and id(dugum) not in aciklamalar]


def _json_degerleri(deger):
    """JSON içindeki metin değerleri; "_" ile başlayan açıklama anahtarları hariç."""
    if isinstance(deger, dict):
        return [m for ad, alt in deger.items() if not str(ad).startswith("_")
                for m in _json_degerleri(alt)]
    if isinstance(deger, list):
        return [m for alt in deger for m in _json_degerleri(alt)]
    return [deger] if isinstance(deger, str) else []


def test_sistem_adlari_yalniz_parametrede():
    params = json.loads(_oku(os.path.join(KOK, "dataiku", "degiskenler", "params.json")))
    adlar = [ad for kod, ad in params["gorunum"]["sistem_adlari"].items()
             if not kod.startswith("_")]
    assert adlar
    for yol in _kod_dosyalari({".py", ".js", ".html", ".json"}):
        uzanti = os.path.splitext(yol)[1]
        if uzanti == ".py":
            metinler = _metin_sabitleri(yol)
        elif uzanti == ".json":
            if os.path.basename(yol) == "params.json":
                continue
            metinler = _json_degerleri(json.loads(_oku(yol)))
        else:
            metinler = [re.sub(r"/\*.*?\*/|<!--.*?-->", " ", _oku(yol), flags=re.S)]
        assert not [ad for ad in adlar for m in metinler if ad in m], yol


def test_veri_kumesi_ve_klasor_adlari_listede():
    bilinen = set(vk.CIKTI) | set(vk.KONTROL)
    klasorler = set(vk.KLASORLER) | {vk.DOSYA_KLASORU}
    tablo_adi = re.compile(r"^(?:sonuc|model|gozlem|kontrol)_[a-z0-9_]+$")
    for yol in _kod_dosyalari({".py"}):
        sabitler = _metin_sabitleri(yol)
        bilinmeyen = {s for s in sabitler if tablo_adi.match(s)} - bilinen
        assert not bilinmeyen, (yol, sorted(bilinmeyen))
        if os.path.basename(yol) != "veri_kumeleri.py":
            assert not klasorler & set(sabitler), (yol, sorted(klasorler & set(sabitler)))


def test_yontem_listesi_ve_metin_ozeti_tek_kural():
    from araclar import ozet
    from avukat_perf import surum
    from hat import ayar, kaynak
    assert kaynak.YONTEMLER is ayar.YONTEMLER
    assert ozet.metin_ozeti is surum.metin_ozeti
    # Not defterindeki bağımsız kopya (şirkette kütüphaneden önce yapıştırılır) aynı sonucu verir.
    yol = os.path.join(KOK, "dataiku", "kontrol", "aktarim_kontrol.py")
    with open(yol, encoding="utf-8") as dosya:
        agac = ast.parse(dosya.read())
    tanim = [d for d in agac.body if isinstance(d, ast.FunctionDef) and d.name == "metin_ozeti"]
    alan = {"hashlib": __import__("hashlib")}
    exec(compile(ast.Module(body=tanim, type_ignores=[]), yol, "exec"), alan)
    # Tek başına \r (eski satır sonu) da satır ayırır: iki kopya aynı splitlines kuralını kullanır.
    for ornek in ("a\r\nb  \r\n\r\n", "a\nb\n", "", "x\t \n\n\ny", "ç\r\n", "a\rb \r"):
        assert alan["metin_ozeti"](ornek) == surum.metin_ozeti(ornek)


def test_readme_veri_sozlesmesi_tablosu_sema_ile_ayni():
    """Kaynak ekiplerine giden sözleşme tablosu sema.KAYNAKLAR'la alan alan, tür ve zorunluluk
    dahil aynıdır (atama zamanı "tarih" yazıyordu, saat istenmiyordu)."""
    from avukat_perf import sema
    tur_metni = {"metin": "", "sayi": " (sayı)", "tarih": " (tarih)",
                 "zaman": " (zaman, saatiyle)", "mantiksal": " (mantıksal)"}
    metin = _oku(os.path.join(KOK, "README.md"))
    readme = dict(re.findall(r"^\| `([a-z0-9_]+)` \| ([^|]*\\\*[^|]*) \|$", metin, re.M))
    for ad, tanim in sema.KAYNAKLAR.items():
        beklenen = ", ".join(alan + ("\\*" if zorunlu else "") + tur_metni[tur]
                             for alan, tur, zorunlu in tanim["alanlar"])
        assert readme.get(ad) == beklenen, ad
