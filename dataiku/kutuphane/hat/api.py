"""Genel REST/JSON okuyucu (yalnız standart kitaplık: urllib).

Ayar alanları README'de (Veri entegrasyonu, API); kimlik türleri hat.api_kimlik'te. sayfalama.tur:
yok, sayfa, ofset, imlec. Okuma boş sayfada ya da imleç bitince biter (kısa sayfa son sayılmaz);
toplam_yolu (toplam KAYIT sayısı) okuma sonunda doğrulanır, toplam_ile_dur true ise toplama
ulaşınca durur. Aynı sayfa ya da imleç tekrar gelirse okuma durur. 5xx, 429 (Retry-After'a
uyarak) ve bağlantı hatası artan beklemeyle yeniden denenir; OAuth2 jetonu süresi dolarsa (401)
bir kez yenilenir; kimlik başlığı yönlendirmede taşınmaz.
"""
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPException
from socket import timeout as ZAMAN_ASIMI

import pandas as pd

from hat import api_yanit
from hat.api_kimlik import gizli_degerler, kimlik_basligi, kimlik_sorgusu, maskele, temiz_gizli

YENIDEN_DENENEN = (urllib.error.URLError, ZAMAN_ASIMI, ConnectionError, HTTPException)
EN_UZUN_BEKLEME_SN = 300


def _bekleme(hata, ayar, sira):
    deger = hata.headers.get("Retry-After") if isinstance(hata, urllib.error.HTTPError) else None
    if deger and str(deger).strip().isdigit():
        return min(int(deger), EN_UZUN_BEKLEME_SN)
    return ayar.get("bekleme_sn", 2) * (2 ** sira)


def _istek(ayar, sorgu, basliklar, kimlik, uyku, baglam):
    ayirac = "&" if "?" in ayar["adres"] else "?"
    adres = ayar["adres"] + (ayirac + urllib.parse.urlencode(sorgu) if sorgu else "")
    govde = ayar.get("govde")
    veri = None if govde is None else json.dumps(govde).encode("utf-8")
    deneme = ayar.get("deneme", 3)
    for sira in range(deneme):
        try:
            istek = urllib.request.Request(adres, data=veri, headers=basliklar,
                                           method=ayar.get("http_yontemi", "GET"))
            for ad, deger in kimlik.items():  # yönlendirmede başka adrese gönderilmez
                istek.add_unredirected_header(ad, deger)
            with urllib.request.urlopen(istek, timeout=ayar.get("zaman_asimi_sn", 60),
                                        context=baglam) as yanit:
                return json.loads(yanit.read().decode(yanit.headers.get_content_charset() or
                                                      "utf-8"))
        except urllib.error.HTTPError as hata:
            if (hata.code < 500 and hata.code != 429) or sira == deneme - 1:
                raise
            uyku(_bekleme(hata, ayar, sira))
        except YENIDEN_DENENEN as hata:
            if sira == deneme - 1:
                raise
            uyku(_bekleme(hata, ayar, sira))
    raise RuntimeError("istek tamamlanamadı")


def oku(ayar, gizli, uyku=time.sleep):
    """Bütün sayfaları okuyup tek tablo döndürür; iç içe alanlar noktayla düzleştirilir.

    Gizli değer kırpılarak okunur; hata iletisinde her kimlik türünde maskelenir: ileti çalışma
    kaydına, kalite sonucuna, izleme panosuna ve Veri Durumu sayfasına yazılır.
    """
    gizli = temiz_gizli(gizli)
    gizliler = gizli_degerler(ayar.get("kimlik"), gizli)
    try:
        return _oku(ayar, gizli, uyku)
    except Exception as hata:
        metin = str(hata)
        if not any(deger in metin for deger in gizliler):
            raise
        raise RuntimeError("{}: {}".format(type(hata).__name__, maskele(metin, gizliler))) from None


def _oku(ayar, gizli, uyku):
    baglam = ssl.create_default_context(cafile=ayar["ca_dosyasi"]) if ayar.get(
        "ca_dosyasi") else None
    basliklar = dict({"Accept": "application/json"}, **ayar.get("basliklar", {}))
    if ayar.get("govde") is not None:
        basliklar.setdefault("Content-Type", "application/json")
    kimlik, yenilendi = kimlik_basligi(ayar.get("kimlik"), gizli, baglam, uyku), False
    sayfalama = ayar.get("sayfalama") or {"tur": "yok"}
    sorgu = dict(ayar.get("sorgu", {}), **kimlik_sorgusu(ayar.get("kimlik"), gizli))
    kayitlar, onceki, toplam = [], None, None
    sayfa, ofset, imlec = sayfalama.get("baslangic", 1), 0, None
    for _ in range(ayar.get("en_cok_sayfa", 10000)):
        sorgu = api_yanit.sayfa_sorgusu(sayfalama, sorgu, sayfa, ofset, imlec)
        try:
            yanit = _istek(ayar, sorgu, basliklar, kimlik, uyku, baglam)
        except urllib.error.HTTPError as hata:  # süresi dolan OAuth2 jetonu bir kez yenilenir
            if hata.code != 401 or yenilendi or (ayar.get("kimlik") or {}).get("tur") != "oauth2":
                raise
            kimlik, yenilendi = kimlik_basligi(ayar.get("kimlik"), gizli, baglam, uyku), True
            yanit = _istek(ayar, sorgu, basliklar, kimlik, uyku, baglam)
        parca = api_yanit.kayitlar(yanit, ayar.get("kayit_yolu"))
        if parca and parca == onceki:
            raise RuntimeError("aynı sayfa yeniden geldi; sayfalama ayarını kontrol et")
        kayitlar.extend(parca)
        onceki, toplam = parca, api_yanit.toplam(yanit, sayfalama) if toplam is None else toplam
        if sayfalama["tur"] == "imlec":
            yeni = api_yanit.sonraki_imlec(yanit, sayfalama, parca)
            if yeni and yeni == imlec:
                raise RuntimeError("imleç ilerlemiyor; sayfalama ayarını kontrol et")
            imlec = yeni
        if api_yanit.bitti(sayfalama, parca, imlec, len(kayitlar), toplam):
            if toplam is not None and len(kayitlar) != toplam:
                raise ValueError("toplam_yolu {} kayıt diyor, {} kayıt okundu".format(
                    toplam, len(kayitlar)))
            return pd.json_normalize(kayitlar) if kayitlar else pd.DataFrame()
        sayfa, ofset = sayfa + 1, ofset + len(parca)
    raise RuntimeError("en_cok_sayfa sınırı aşıldı; sayfalama ayarını kontrol et")
