"""Dataiku Standard web uygulaması arka ucu (Python sekmesine yapıştırılır).

Sonuç veri kümelerini okur, arayuz.sunum ile sayfa verisini hazırlar, JSON döndürür. İş
kuralı içermez. Tablolar ve parametreler beş dakikalık önbellekte tutulur; bir tablo
okunamadıysa (bağlantı, yetki) okuma YENIDEN_SN sonra yeniden denenir ve okunamayan tablolar
üst şeritte söylenir (kesinti "henüz sonuç yok" gibi görünmez). Parametreler "ayarlar"
yönetilen klasöründeki params.json ve varsa params_ek.json dosyasından okunur (hat.ayar).
Dataiku bu sekmeye Flask uygulamasını "app" adıyla verir; ayrıca tanımlanmaz.
Uç: GET /api/sayfa?ad=genel|avukat|sure|kurallar|veri [&kod=AV-01] [&kriter=&seviye=&avukat=]
"""
import threading
import time

from flask import jsonify, request

from arayuz import sunum
from hat import ayar
from hat.dataiku_ortam import DataikuOrtam

ORTAM = DataikuOrtam()
ONBELLEK = {"zaman": 0.0, "tablolar": None, "params": None, "okunamayan": []}
ONBELLEK_KILIDI = threading.RLock()
ONBELLEK_SN = 300
YENIDEN_SN = 15  # okunamayan tablo varken önbellek süresi


@app.after_request  # noqa: F821
def hassas_yanit(yanit):
    """Performans verisi ve hata yanıtları ortak HTTP önbelleğinde tutulmaz."""
    if request.path.startswith("/api/"):
        yanit.headers["Cache-Control"] = "no-store"
    return yanit


def _oku(ad, okunamayan):
    """Bir tablonun okunamaması bütün sayfaları düşürmez; o tablo yokmuş gibi gösterilir ve
    adı okunamayan listesine eklenir."""
    try:
        return ORTAM.tablo_oku(ad)
    except Exception as hata:  # bağlantı ya da yetki: ayrıntı arka uç günlüğünde
        print("tablo okunamadı: {} ({}: {})".format(ad, type(hata).__name__, hata))
        okunamayan.append(ad)
        return None


def _veri():
    # Okuma tamamlanmadan yeni tabloyu eski kurallarla erişilebilir yapma.
    with ONBELLEK_KILIDI:
        sure = YENIDEN_SN if ONBELLEK["okunamayan"] else ONBELLEK_SN
        if ONBELLEK["tablolar"] is None or time.time() - ONBELLEK["zaman"] > sure:
            okunamayan = []
            tablolar = {ad: _oku(ad, okunamayan) for ad in sunum.TABLOLAR}
            params = ayar.yukle(ORTAM, "params")
            ONBELLEK.update(tablolar=tablolar, params=params, okunamayan=okunamayan,
                            zaman=time.time())
        return ONBELLEK["tablolar"], ONBELLEK["params"], ONBELLEK["okunamayan"]


@app.route("/api/sayfa")  # noqa: F821 (app Dataiku tarafından verilir)
def sayfa():
    ad = request.args.get("ad", "genel")
    if ad not in sunum.SAYFALAR:  # girdi yanıta yansıtılmaz
        return jsonify({"hata": "bilinmeyen sayfa"}), 400
    tablolar, params, okunamayan = _veri()
    secim = {k: request.args.get(k) for k in sunum.SECIMLER if request.args.get(k)}
    return jsonify(sunum.sayfa(ad, tablolar, params, secim, okunamayan))


@app.route("/api/yenile")  # noqa: F821
def yenile():
    """Önbelleği boşaltır (gecelik çalışmadan hemen sonra görmek için)."""
    with ONBELLEK_KILIDI:
        ONBELLEK["tablolar"] = None
    return jsonify({"durum": "yenilendi"})
