"""API kimliği: yok, bearer, basic, baslik, sorgu ve oauth2 (istemci kimlik bilgileri).

Değer kimlik.gizli adındaki gizli değerden okunur (Dataiku kullanıcı gizlisi), ayar dosyasına
yazılmaz. basic için gizli değer "kullanici:sifre"; baslik için kimlik.baslik_adi; sorgu için
kimlik.parametre (anahtarı adres sorgusunda isteyen API: ?api_key=...; anahtar sorgu ayarına
yazılmaz); oauth2 için jeton_adresi, gizli değer "istemci_kimligi:istemci_sirri", isteğe bağlı
kapsam ve istemci_dogrulama basic|govde. Jeton isteği 5xx, 429, zaman aşımı ve bağlantı hatasında
üç kez denenir (veri isteğiyle aynı durumlar).
Gizli değerin başındaki ve sonundaki boşluk ve satır sonu atılır (kopyala-yapıştır); içte denetim
karakteri kalırsa değer yazılmadan durulur. Hata iletisinde değer her kimlik türünde maskelenir.
"""
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from socket import timeout as ZAMAN_ASIMI

GEREKEN = {"yok": (), "bearer": ("gizli",), "basic": ("gizli",),
           "baslik": ("gizli", "baslik_adi"), "sorgu": ("gizli", "parametre"),
           "oauth2": ("gizli", "jeton_adresi")}


def kimlik_hatalari(kimlik, yer):
    """Ayar doğrulaması: bilinen tür ve türün gerektirdiği alanlar."""
    tur = (kimlik or {}).get("tur", "yok")
    if tur not in GEREKEN:
        return ["{}: kimlik.tur {} olmalı".format(yer, " | ".join(sorted(GEREKEN)))]
    return ["{}: {} kimliği için kimlik.{} gerekir".format(yer, tur, alan)
            for alan in GEREKEN[tur] if not kimlik.get(alan)]


def kimlik_sorgusu(kimlik, gizli):
    """Anahtarı sorguda isteyen API için {parametre: anahtar}; başka türde boş."""
    if (kimlik or {}).get("tur") != "sorgu":
        return {}
    return {kimlik["parametre"]: gizli(kimlik["gizli"])}


def temiz_gizli(gizli):
    """Gizli değeri kırparak okuyan işlev; içte denetim karakteri varsa değeri yazmadan durur."""
    def oku(ad):
        deger = gizli(ad)
        if not isinstance(deger, str):
            return deger
        deger = deger.strip()
        if any(ord(harf) < 32 or ord(harf) == 127 for harf in deger):
            raise ValueError("gizli {} satır sonu ya da denetim karakteri içeriyor".format(ad))
        return deger
    return oku


def gizli_degerler(kimlik, gizli):
    """Hata iletisinde maskelenecek değerler: gizli değer, iki parçalı değerde (basic, oauth2)
    şifre ya da istemci sırrı, adreste ve başlıkta kodlanmış hâlleri."""
    kimlik = kimlik or {}
    if kimlik.get("tur", "yok") == "yok" or not kimlik.get("gizli"):
        return []
    deger = gizli(kimlik["gizli"])
    if not isinstance(deger, str) or not deger:
        return []
    parcalar = {deger, deger.partition(":")[2]} if kimlik["tur"] in ("basic", "oauth2") else {deger}
    sonuc = {base64.b64encode(deger.encode("utf-8")).decode()}
    for parca in parcalar:
        sonuc |= {parca, urllib.parse.quote(parca, safe=""), urllib.parse.quote_plus(parca)}
    return [d for d in sonuc if d]


def maskele(metin, degerler):
    for deger in sorted(degerler, key=len, reverse=True):
        metin = metin.replace(deger, "***")
    return metin


def kimlik_basligi(kimlik, gizli, baglam=None, uyku=time.sleep):
    """İstek başlıklarına eklenecek kimlik başlığı sözlüğü (sorgu türünde boş)."""
    tur = (kimlik or {}).get("tur", "yok")
    if tur in ("yok", "sorgu"):
        return {}
    deger = gizli(kimlik["gizli"])
    if tur == "bearer":
        return {"Authorization": "Bearer " + deger}
    if tur == "basic":
        return {"Authorization": "Basic " + base64.b64encode(deger.encode("utf-8")).decode()}
    if tur == "baslik":
        return {kimlik["baslik_adi"]: deger}
    if tur == "oauth2":
        return {"Authorization": "Bearer " + _oauth2_jeton(kimlik, deger, baglam, uyku)}
    raise ValueError("bilinmeyen kimlik türü: " + tur)


def _oauth2_jeton(kimlik, deger, baglam, uyku):
    """İstemci kimlik bilgileriyle (client credentials) erişim jetonu alır."""
    istemci, _, sir = deger.partition(":")
    form = {"grant_type": "client_credentials"}
    if kimlik.get("kapsam"):
        form["scope"] = kimlik["kapsam"]
    basliklar = {"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"}
    basic = kimlik.get("istemci_dogrulama", "basic") == "basic"
    form.update({} if basic else {"client_id": istemci, "client_secret": sir})
    istek = urllib.request.Request(kimlik["jeton_adresi"], method="POST", headers=basliklar,
                                   data=urllib.parse.urlencode(form).encode("utf-8"))
    if basic:  # istemci sırrı yönlendirmede başka sunucuya gitmez
        istek.add_unredirected_header("Authorization", "Basic " + base64.b64encode(
            deger.encode("utf-8")).decode())
    for sira in range(3):
        try:
            with urllib.request.urlopen(istek, timeout=kimlik.get("zaman_asimi_sn", 60),
                                        context=baglam) as yanit:
                return json.loads(yanit.read().decode("utf-8"))["access_token"]
        except urllib.error.HTTPError as hata:
            if (hata.code < 500 and hata.code != 429) or sira == 2:
                raise
        except (urllib.error.URLError, ConnectionError, ZAMAN_ASIMI):
            if sira == 2:
                raise
        uyku(2 ** sira)
    raise RuntimeError("jeton alınamadı")
