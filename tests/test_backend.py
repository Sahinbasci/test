"""Web uygulaması arka ucu (dataiku/webapp/backend.py): Flask içinde, sahte Dataiku'yla.

Dataiku'ya yazılıp geri okunan tablolardan dönen sayfa verisi, yerelde aynı tablolardan
doğrudan hesaplananla birebir aynı olmalıdır (gidiş-dönüş ekranı değiştirmez). backend.py
dosyası Dataiku'daki gibi, "app" adlı Flask uygulaması verilerek çalıştırılır. Flask kurulu
olmayan ortamda test atlanır.
"""
import json
import os
import shutil
import sys

import sahte_dataiku
from arayuz import sunum
from hat import akis, donem_akisi
from yardimci import KOK, prova_ortami


def _arka_uc():
    """(Flask test istemcisi, yerel tablolar, parametreler); Flask yoksa None."""
    try:
        import flask
    except ImportError:
        return None
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 02:00:00")
        tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
    finally:
        shutil.rmtree(kok)
    sys.modules["dataiku"] = sahte_dataiku.modul()
    for ad, tablo in tablolar.items():
        if tablo is not None:
            sahte_dataiku.VeriKumesi(ad).write_with_schema(tablo)
    sahte_dataiku.Klasor("ayarlar").upload_data("params.json", json.dumps(params).encode("utf-8"))
    uygulama = flask.Flask("arka_uc_testi")
    with open(os.path.join(KOK, "dataiku", "webapp", "backend.py"), encoding="utf-8") as dosya:
        kod = dosya.read()
    exec(compile(kod, "backend.py", "exec"), {"app": uygulama, "__name__": "backend"})
    return uygulama.test_client(), tablolar, params


def test_arka_uc_sayfalari_yerel_hesapla_ayni():
    hazir = _arka_uc()
    if hazir is None:
        return
    istemci, tablolar, params = hazir
    try:
        kod = tablolar["sonuc_birlesik"]["avukat_kodu"].iloc[0]
        k1 = tablolar["sonuc_k1"]
        olculen = k1.loc[k1["seviye"] != "KAPSAM_DISI", "avukat_kodu"].iloc[-1]
        denemeler = [("ad=genel", "genel", None), ("ad=avukat", "avukat", None),
                     ("ad=avukat&kod=" + kod, "avukat", {"kod": kod}),
                     ("ad=sure&kriter=K2&seviye=TURUNCU", "sure",
                      {"kriter": "K2", "seviye": "TURUNCU"}),
                     # Avukat süzgeci arka uçtan sunuma iletilir (seçimler sunum.SECIMLER'de).
                     ("ad=sure&seviye=KAPANDI&avukat=" + olculen, "sure",
                      {"seviye": "KAPANDI", "avukat": olculen}),
                     ("ad=kurallar", "kurallar", None), ("ad=veri", "veri", None)]
        for sorgu, ad, secim in denemeler:
            yanit = istemci.get("/api/sayfa?" + sorgu)
            assert yanit.status_code == 200, sorgu
            beklenen = json.loads(json.dumps(sunum.sayfa(ad, tablolar, params, secim),
                                             allow_nan=False))
            assert yanit.get_json() == beklenen, sorgu
        liste = istemci.get("/api/sayfa?ad=sure&seviye=KAPANDI&avukat=" + olculen).get_json()[
            "bilesenler"]["sure.liste"]
        assert liste and {k["avukat_kodu"] for k in liste} == {olculen}
        # Bilinmeyen sayfa adı yanıta yansıtılmaz.
        yanit = istemci.get("/api/sayfa?ad=<b>yok</b>")
        assert yanit.status_code == 400 and "yok" not in json.dumps(yanit.get_json())
        assert istemci.get("/api/yenile").get_json() == {"durum": "yenilendi"}
        assert istemci.get("/api/sayfa?ad=genel").status_code == 200
    finally:
        sys.modules.pop("dataiku", None)
