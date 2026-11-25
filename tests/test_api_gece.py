"""Sahte API ile uçtan uca gece: bütün kaynaklar sayfalı bir JSON servisinden okunur.

Aynı sentetik veri bir kez dosya yöntemiyle, bir kez API'yle okunur; hattın yazdığı model,
gözlem ve sonuç tabloları birebir aynı olmalı. Ayar, depodaki kaynaklar.json yapısıyla kurulur
(sistem başına yontem ve adres kökü, kimlik bearer, sayfa sayfalaması, kayıt yolu "data");
şirkette API bağlanınca değişecek olan yalnız bu bloktur.
"""
import copy
import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pandas as pd

from hat import akis, ayar
from hat import veri_kumeleri as vk
from hat.ortam import YerelOrtam
from yardimci import prova_ortami

ANAHTAR = "sahte-anahtar"
SIMDI = "2026-11-19 02:00:00"


def _sunucu(kok, ayarlar, istekler):
    """Kaynağın dosya yöntemindeki CSV'sini /<kaynak> yolunda sayfa sayfa veren sunucu."""
    yollar = {ayar.kaynak_ayari(ayarlar, ad)["api"]["yol"]: ad for ad in ayarlar["kaynaklar"]}

    class Isleyici(BaseHTTPRequestHandler):
        def do_GET(self):
            adres = urlparse(self.path)
            sorgu = {k: v[0] for k, v in parse_qs(adres.query).items()}
            istekler.append(adres.path)
            if self.headers.get("Authorization") != "Bearer " + ANAHTAR:
                kod, govde = 401, {"hata": "kimlik"}
            else:
                dosya = ayar.kaynak_ayari(ayarlar, yollar[adres.path])["dosya"]["yol"]
                tablo = pd.read_csv(os.path.join(kok, dosya), dtype=str, keep_default_na=False)
                kayitlar = [{ad: (deger if deger != "" else None) for ad, deger in satir.items()}
                            for satir in tablo.to_dict("records")]
                boyut, sayfa = int(sorgu["size"]), int(sorgu["page"])
                kod, govde = 200, {"data": kayitlar[(sayfa - 1) * boyut:sayfa * boyut]}
            self.send_response(kod)
            self.end_headers()
            self.wfile.write(json.dumps(govde).encode("utf-8"))

        def log_message(self, *argumanlar):
            pass

    sunucu = HTTPServer(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return sunucu


def _api_ayari(ayarlar, adres):
    """Bütün sistemler API'den: depodaki kimlik ve sayfalama ayarı, küçük sayfa boyutu; sunucu
    ilk sayfayı 1 sayar (baslangic depoda yok, entegrasyonda açıkça yazılır)."""
    yeni = copy.deepcopy(ayarlar)
    for sistem in yeni["sistemler"].values():
        if isinstance(sistem, dict):
            sistem["yontem"] = "api"
            sistem["api"].update(adres_koku=adres, deneme=1)
            sistem["api"]["sayfalama"].update(boyut=97, baslangic=1)
    return yeni


def _gizliler(ayarlar):
    return {s["api"]["kimlik"]["gizli"]: ANAHTAR for s in ayarlar["sistemler"].values()
            if isinstance(s, dict)}


def test_api_ile_gece_dosya_yontemiyle_ayni_sonucu_verir():
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    istekler = []
    sunucu = _sunucu(kok, ayarlar, istekler)
    try:
        adres = "http://127.0.0.1:{}".format(sunucu.server_port)
        api_ayari = _api_ayari(ayarlar, adres)
        api_ortam = YerelOrtam(os.path.join(kok, "calisma_api"), gizliler=_gizliler(api_ayari))
        dosya_sonuc = akis.gecelik(ortam, ayarlar, params, simdi=SIMDI)
        api_sonuc = akis.gecelik(api_ortam, api_ayari, params, simdi=SIMDI)
        assert dosya_sonuc["karar"] == api_sonuc["karar"] == "GECTI"
        # Her kaynak istendi; her biri en az iki istekle (veri sayfası + sondaki boş sayfa), en
        # büyük kaynaklar birden çok veri sayfasıyla okundu.
        yollar = {ayar.kaynak_ayari(api_ayari, ad)["api"]["yol"] for ad in api_ayari["kaynaklar"]}
        assert set(istekler) == yollar
        assert all(istekler.count(yol) >= 2 for yol in yollar)
        assert max(istekler.count(yol) for yol in yollar) > 3
        for ad in vk.GOZLEM + vk.MODEL + vk.SONUC:
            beklenen, gelen = ortam.tablo_oku(ad), api_ortam.tablo_oku(ad)
            assert (beklenen is None) == (gelen is None), ad
            if beklenen is not None:
                pd.testing.assert_frame_equal(beklenen.drop(columns="calisma_kimligi",
                                                            errors="ignore"),
                                              gelen.drop(columns="calisma_kimligi",
                                                         errors="ignore"), obj=ad)
        kayit = api_ortam.tablo_oku("calisma_kaydi")
        kaynaklar = kayit[kayit["kaynak"].isin(list(api_ayari["kaynaklar"]))]
        assert set(kaynaklar["yontem"]) == {"api"} and set(kaynaklar["durum"]) == {"BASARILI"}
        # Yanlış anahtar: kaynaklar okunamaz, gece KALDI ve hata kayda geçer (çökmez).
        yanlis = YerelOrtam(os.path.join(kok, "calisma_yanlis"),
                            gizliler={ad: "yanlis" for ad in _gizliler(api_ayari)})
        assert akis.gecelik(yanlis, api_ayari, params, simdi=SIMDI)["karar"] == "KALDI"
        hata = yanlis.tablo_oku("calisma_kaydi")
        assert hata[hata["kaynak"] == "dosya"]["aciklama"].iloc[0].startswith("HTTPError")
    finally:
        sunucu.shutdown()
        sunucu.server_close()
        shutil.rmtree(kok)
