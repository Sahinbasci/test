"""Arayüzün yerel önizlemesi: sentetik veriyle hattı çalıştırır ve web uygulamasını yerel bir
sunucuda açar.

Sunucunun /api/sayfa ucu dataiku/webapp/backend.py ile aynı sorgu parametrelerini alır ve
aynı sunum katmanını çağırır; filtreler dahil her sayı gerçekten hesaplanır. Arayüz dosyaları
(dataiku/webapp) değiştirilmeden okunur; yalnız Dataiku'nun verdiği getWebAppBackendUrl
işlevi burada tanımlanır.
Kullanım: python araclar/onizleme.py [--yenile] [--senaryo tam|acilis|bos] [--port 8771]
--yenile: çalışma klasörünü silip hattı baştan çalıştırır. --senaryo acilis: canlıya geçiş günü
(dava takip sistemi yok, değerlendirme ölçeği teyitsiz, gölge mod açık); ayrı klasörde
(onizleme/calisma_acilis).
"""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "dataiku", "kutuphane"))
sys.path.insert(0, os.path.join(KOK, "araclar"))

import yerel_calistir  # noqa: E402
from arayuz import sunum  # noqa: E402
from hat.ortam import YerelOrtam  # noqa: E402

CALISMA = os.path.join(KOK, "onizleme", "calisma")
WEBAPP = os.path.join(KOK, "dataiku", "webapp")
DOSYALAR = {"/stil.css": ("stil.css", "text/css"),
            "/uygulama.js": ("uygulama.js", "application/javascript")}
SAYFA = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Avukat Performans · Önizleme</title>
<link rel="stylesheet" href="stil.css"></head>
<body>
<div role="status" style="padding:10px 16px;background:#FFF6DB;color:#7A5300;
font:600 13px system-ui;text-align:center">
Sentetik test verisi — resmî performans değerlendirmesinde kullanılmaz.
</div>
{govde}
<script>window.getWebAppBackendUrl = function (yol) { return yol; };</script>
<script src="uygulama.js"></script>
</body></html>
"""


def veri_hazirla(yenile=False, senaryo="tam"):
    """Sonuç tablolarını ve senaryonun parametrelerini döndürür; gerekirse hattı çalıştırır."""
    klasor = CALISMA if senaryo == "tam" else CALISMA + "_" + senaryo
    if yenile or not os.path.isdir(os.path.join(klasor, "tablolar")):
        ortam = yerel_calistir.calistir(klasor, yazdir=False, senaryo=senaryo)
    else:
        ortam = YerelOrtam(klasor, kaynak_kok=KOK)
    tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
    return tablolar, yerel_calistir.senaryo_ayarlari(senaryo)[1]


def _oku(ad):
    with open(os.path.join(WEBAPP, ad), encoding="utf-8") as dosya:
        return dosya.read()


def yanit(yol, tablolar, params):
    """İstek yoluna karşılık (durum kodu, içerik türü, gövde baytları)."""
    adres = urlparse(yol)
    if adres.path == "/api/sayfa":
        sorgu = {ad: degerler[0] for ad, degerler in parse_qs(adres.query).items()}
        secim = {ad: sorgu[ad] for ad in sunum.SECIMLER if sorgu.get(ad)}
        try:
            durum, govde = 200, sunum.sayfa(sorgu.get("ad", "genel"), tablolar, params, secim)
        except ValueError as hata:
            durum, govde = 400, {"hata": str(hata)}
        metin = json.dumps(govde, ensure_ascii=False, allow_nan=False)
        return durum, "application/json; charset=utf-8", metin.encode("utf-8")
    if adres.path in ("/", "/index.html"):
        metin = SAYFA.replace("{govde}", _oku("index.html"))
        return 200, "text/html; charset=utf-8", metin.encode("utf-8")
    if adres.path in DOSYALAR:
        ad, tur = DOSYALAR[adres.path]
        return 200, tur + "; charset=utf-8", _oku(ad).encode("utf-8")
    return 404, "text/plain; charset=utf-8", "bulunamadı".encode("utf-8")


class _Sunucu(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def sunucu(tablolar, params, port):
    class Isleyici(BaseHTTPRequestHandler):
        def do_GET(self):
            durum, tur, govde = yanit(self.path, tablolar, params)
            self.send_response(durum)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(govde)

        def log_message(self, bicim, *degerler):
            pass

    return _Sunucu(("127.0.0.1", port), Isleyici)


if __name__ == "__main__":
    AYRAC = argparse.ArgumentParser(description="Arayüz önizlemesi")
    AYRAC.add_argument("--yenile", action="store_true")
    AYRAC.add_argument("--port", type=int, default=8771)
    AYRAC.add_argument("--senaryo", choices=("tam", "acilis", "bos"), default="tam")
    SECENEK = AYRAC.parse_args()
    TABLOLAR, PARAMS = veri_hazirla(SECENEK.yenile, SECENEK.senaryo)
    print("önizleme: http://127.0.0.1:{}  (durdurmak için Ctrl+C)".format(SECENEK.port))
    sys.stdout.flush()
    try:
        sunucu(TABLOLAR, PARAMS, SECENEK.port).serve_forever()
    except KeyboardInterrupt:
        pass
