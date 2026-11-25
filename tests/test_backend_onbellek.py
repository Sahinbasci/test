"""Önbellek yenilemesinde tablo ve kurallar aynı tamamlanmış okumadan gelmelidir."""
import os
import sys
import threading
import time

import flask

import sahte_dataiku
from yardimci import KOK


def _arka_uc():
    onceki = sys.modules.get("dataiku")
    sys.modules["dataiku"] = sahte_dataiku.modul()
    try:
        alan = {"app": flask.Flask("onbellek_testi"), "__name__": "backend"}
        with open(os.path.join(KOK, "dataiku", "webapp", "backend.py"),
                  encoding="utf-8") as dosya:
            exec(compile(dosya.read(), "backend.py", "exec"), alan)
    finally:
        if onceki is None:
            sys.modules.pop("dataiku", None)
        else:
            sys.modules["dataiku"] = onceki
    alan["ONBELLEK"].update(zaman=time.time(), tablolar=None, params={"surum": "eski"})
    alan["_oku"] = lambda ad, okunamayan: {"surum": "yeni"}
    return alan


def test_ayar_okuma_hatasindan_sonra_tablolar_eski_kuralla_donmez():
    alan = _arka_uc()
    asil = alan["ayar"].yukle
    cagrilar = []

    def yukle(*args):
        cagrilar.append(1)
        if len(cagrilar) == 1:
            raise IOError("ayar okuma kesintisi")
        return {"surum": "yeni"}

    try:
        alan["ayar"].yukle = yukle
        try:
            alan["_veri"]()
            assert False, "ayar hatasi yutulmamali"
        except IOError:
            pass
        tablolar, params, _ = alan["_veri"]()
        assert params == {"surum": "yeni"}
        assert all(t == {"surum": "yeni"} for t in tablolar.values())
        assert len(cagrilar) == 2
    finally:
        alan["ayar"].yukle = asil


def test_eszamanli_istek_yenilenen_tabloyu_eski_kuralla_almaz():
    alan = _arka_uc()
    asil = alan["ayar"].yukle
    okuma_basladi, devam, ikinci_bitti = (threading.Event() for _ in range(3))
    sonuclar, hatalar, cagrilar = [], [], []

    def yukle(*args):
        cagrilar.append(1)
        okuma_basladi.set()
        if not devam.wait(5):
            raise RuntimeError("test bekleme suresi asildi")
        return {"surum": "yeni"}

    def oku(ikinci=False):
        try:
            sonuclar.append(alan["_veri"]())
        except Exception as hata:
            hatalar.append(hata)
        finally:
            if ikinci:
                ikinci_bitti.set()

    bir = threading.Thread(target=oku)
    iki = threading.Thread(target=oku, args=(True,))
    try:
        alan["ayar"].yukle = yukle
        bir.start()
        assert okuma_basladi.wait(5)
        iki.start()
        ikinci_bitti.wait(0.2)
    finally:
        devam.set()
        bir.join(5)
        if iki.ident is not None:
            iki.join(5)
        alan["ayar"].yukle = asil
    assert not bir.is_alive() and not iki.is_alive() and not hatalar
    assert len(sonuclar) == 2 and len(cagrilar) == 1
    assert all(params == {"surum": "yeni"} for _, params, _ in sonuclar)
