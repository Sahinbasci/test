"""Kurulum adım 2: kütüphane paketi hat (21 dosya).

araclar/paketle.py üretir; elle değiştirmeyin. Dataiku'da projenin bir Python not
defterine bu dosyanın tamamını yapıştırıp çalıştırın: dosyalar proje kütüphanesine
(Kod > Kütüphaneler > python/hat) yazılır, aynı adlı dosyanın üzerine yazılır ve geri
okunarak doğrulanır. Sonda "hat: 21 dosya yazıldı ve doğrulandı" görünmelidir.
"""
import hashlib

import dataiku

PAKET = "hat"
DOSYALAR = {}

DOSYALAR["__init__.py"] = r'''"""Veri hattı: entegrasyon (kaynak okuma, API), ham arşiv, çalışma kaydı ve akışlar.

Puan formülleri ve iş kuralları avukat_perf kitaplığındadır. hesap.py yalnız hangi sonucun
hangi koşulda üretileceğini (kaynak var mı, teyit edildi mi, gölge mod) ve hesap sırasını
belirler; bu koşullar da hesap sürümüne girer. Ortam (yerel ya da Dataiku) dışarıdan verilir,
böylece aynı akış iki ortamda da çalışır.
"""
'''

DOSYALAR["akis.py"] = r'''"""Gecelik akış: kaynakları oku → ham arşiv → kalite kapısı → model ve gözlem → sonuçlar.

Kaynak okuma ve kapı hat/okuma.py'dedir. Zorunlu bir kaynak bekleniyorsa (bağlantı yok) hesap
yapılmaz: KAYNAK_BEKLENIYOR. Kapı
geçmezse model ve sonuçlar güncellenmez, son geçerli veri korunur: KALDI (alarm). Aynı gün
ikinci çalışma aynı sonucu verir: arşiv yeni kimlikle ayrı yazılır, gözlem ve olay tabloları
çift satır almaz. Herhangi bir kaynakta KALDI varsa bütün gece durur (katı kapı). Okuma,
arşiv ya da biçim hatası o kaynağı KALDI yapar; hata türü ve iletisi çalışma kaydına ve
kalite sonucuna yazılır. Kapıdan sonraki hesapta hata olursa gece KALDI olarak kayda geçer
(HESAP_HATASI) ve hata senaryoya iletilir. Zaman verilmezse İstanbul saati kullanılır.
"""
import pandas as pd

from avukat_perf import kalite, olay, sema
from avukat_perf.ortak import birlestir, tek_gun
from avukat_perf.params import dogrula_veya_dur
from avukat_perf.surum import hazirlik_surumu, hesap_surumu
from hat import ayar, butunluk, calisma, gecmis, hesap, hesap_sure, model, okuma


def _olaylar(ortam, sonuc, cekim, kimlik, onceki_kayit, kaynaklar):
    """K1 ve K2 bayrak olaylarını yalnız ekleyerek birleştirir; çelişenleri ayırır.

    Başarısız gecelerden kalan olay satırları birleştirmeye girmez (yeniden yazılırlar). Çelişki
    yalnız bu gecenin esas kaynağındaki olaylarla aranır (kaynaklar: {kriter: esas kaynağı}).
    """
    ham = ortam.tablo_oku("bayrak_olay")
    butunluk.veri_kaybi(onceki_kayit, {"bayrak_olay": ham})
    mevcut = butunluk.basarili_satirlar(ham, onceki_kayit)
    mevcut = None if mevcut is None else olay.kaynakli(mevcut)
    celiski = []
    for kriter, ad in (("K1", "sonuc_k1"), ("K2", "sonuc_k2")):
        if ad not in sonuc:
            continue
        yeni = olay.olaylar(sonuc[ad], kriter).assign(calisma_kimligi=kimlik)
        onceki = None if mevcut is None else mevcut[
            (mevcut["kriter"] == kriter) & (mevcut["esas_kaynagi"] == kaynaklar[kriter])]
        celiski.append(olay.celisen_olaylar(onceki, yeni, cekim))
        mevcut = olay.olay_birlestir(mevcut, yeni)
    if mevcut is not None and celiski:
        sonuc["bayrak_olay"] = mevcut
        sonuc["olay_celiski"] = birlestir(celiski, list(celiski[0].columns)).assign(
            calisma_kimligi=kimlik, tespit_tarihi=cekim)


def _hesapla_yaz(ortam, tablolar, params, cekim, onceki, kimlik, simdi):
    """Model, puanlar ve olaylar; yazılan tablolar ve satır sayıları ("ad=sayı,...")."""
    mdl = model.kur(ortam, tablolar, params, cekim, onceki, simdi)
    sonuc, durumlar = hesap.hesapla(mdl, cekim, params)
    _olaylar(ortam, sonuc, cekim, kimlik, onceki, hesap_sure.esas_kaynaklari(mdl))
    yazilan = model.yaz(ortam, mdl, sonuc, kimlik)
    return durumlar, ",".join("{}={}".format(ad, yazilan[ad]) for ad in sorted(yazilan))


def gecelik(ortam, ayarlar, params, simdi=None):
    """Bir gecelik çalışma; özet sözlüğü döndürür (calisma_kimligi, karar, eksik, durumlar)."""
    dogrula_veya_dur(params)
    ayar.dogrula_veya_dur(ayarlar)
    simdi = calisma.simdi() if simdi is None else pd.Timestamp(simdi)
    cekim = tek_gun(simdi)  # çekim günü ve gözlem tabanı aynı andan (simdi) türetilir
    kimlik = calisma.kimlik(simdi)
    onceki = ortam.tablo_oku("calisma_kaydi")
    butunluk.kayitsiz_gecmis(ortam, onceki)
    for tur in ("GECELIK", "DONEM_SONU"):  # kesik çalışma kaydı geçmişi siler: çalışma durur
        butunluk.veri_kaybi(onceki, {"calisma_kaydi": onceki}, tur)
    tablolar, kayitlar, sonuclar = okuma.kaynaklari_oku(ortam, ayarlar, params, cekim, onceki,
                                                        kimlik, simdi)
    eksik = [ad for ad in sema.zorunlu_kaynaklar() if ad not in tablolar]
    if not eksik and all(tablolar[ad] is not None for ad in sema.zorunlu_kaynaklar()):
        sonuclar += [s.assign(calisma_kimligi=kimlik)
                     for s in okuma.iliskiler(tablolar, params, cekim)]
    karar = kalite.karar(*sonuclar)
    if eksik and karar != "KALDI":
        karar = "KAYNAK_BEKLENIYOR"
    durumlar, ozet = {}, calisma.satir(kimlik, "GECELIK", calisma.OZET, "", simdi, cekim)
    ozet["hesap_surumu"], ozet["hazirlik_surumu"] = hesap_surumu(params), hazirlik_surumu(params)
    if karar == "GECTI":
        try:
            durumlar, ozet["uretilen"] = _hesapla_yaz(ortam, tablolar, params, cekim, onceki,
                                                      kimlik, simdi)
            ozet["golge_zorunlu"] = bool(durumlar.pop("golge_zorunlu", False))
            ozet["golge"] = bool(params["uyari"]["golge_mod"])  # yedek yol ayrı: golge_zorunlu
        except Exception as hata:  # hesap ya da yazma hatası: kayda geçer, senaryo düşer
            ozet["aciklama"] = "HESAP_HATASI · " + okuma.ileti(hata)
            calisma.kaydet(ortam, onceki, kayitlar, "KALDI", ozet)
            calisma.kalite_ekle(ortam, sonuclar, cekim)
            raise
    calisma.kaydet(ortam, onceki, kayitlar, karar, ozet)
    calisma.kalite_ekle(ortam, sonuclar, cekim)
    return {"calisma_kimligi": kimlik, "karar": karar, "eksik_kaynaklar": eksik,
            "durumlar": durumlar, "hesap_surumu": ozet["hesap_surumu"]}
'''

DOSYALAR["api.py"] = r'''"""Genel REST/JSON okuyucu (yalnız standart kitaplık: urllib).

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
'''

DOSYALAR["api_kimlik.py"] = r'''"""API kimliği: yok, bearer, basic, baslik, sorgu ve oauth2 (istemci kimlik bilgileri).

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
'''

DOSYALAR["api_yanit.py"] = r'''"""API yanıtında yol izleme, kayıt listesinin çıkarılması ve sayfalama adımı.

Yol noktalı metin ("data.items") ya da parça listesidir (["sonuc.v2"]: anahtar nokta
içerirse); sayısal parça liste indeksidir ("results.0.rows"). Yanıtta olmayan yol ile değeri
null olan yol ayrılır: kayıt yolu bulunamazsa okuma sessizce boş dönmez, hata verir (yanlış
yol boş görüntü sayılırsa gözlem tabanı bozulurdu). Hata iletileri yalnız yol adını içerir.
İmleç kipinde imleç değeri sorgu parametresi olarak gönderilir; yanıtta tam adres olarak gelen
sonraki bağlantı (ör. OData nextLink) desteklenmez.
"""


def yol_izle(veri, yol):
    """(bulundu, değer): yol yanıtta var mı ve değeri."""
    parcalar = yol if isinstance(yol, list) else [p for p in str(yol or "").split(".") if p]
    for parca in parcalar:
        if isinstance(veri, dict) and parca in veri:
            veri = veri[parca]
        elif isinstance(veri, list) and str(parca).isdigit() and int(parca) < len(veri):
            veri = veri[int(parca)]
        else:
            return False, None
    return True, veri


def kayitlar(yanit, kayit_yolu):
    """Yanıttaki kayıt listesi. Yol boşsa yanıtın kendisi liste olmalı; değer null ise boş."""
    if not kayit_yolu:
        if isinstance(yanit, list):
            return yanit
        raise ValueError("yanıt liste değil; kaynak ayarında kayit_yolu verilmeli")
    bulundu, deger = yol_izle(yanit, kayit_yolu)
    if not bulundu:
        raise ValueError("kayit_yolu yanıtta yok: {}".format(kayit_yolu))
    if deger is None:
        return []
    if not isinstance(deger, list):
        raise ValueError("kayit_yolu bir liste göstermiyor: {}".format(kayit_yolu))
    return deger


def sonraki_imlec(yanit, sayfalama, sayfa_kayit):
    """Sonraki sayfanın imleci; yoksa None (son sayfa).

    Bazı API'ler son sayfada imleç alanını hiç yazmaz; bu son sayfa sayılır. Ama sayfa dolu
    geldiyse (boyut kadar kayıt) alanın olmaması ayar hatasıdır: okuma ilk sayfada bitip
    veriyi sessizce keserdi.
    """
    bulundu, imlec = yol_izle(yanit, sayfalama["sonraki_imlec_yolu"])
    if not bulundu and sayfalama.get("boyut") and len(sayfa_kayit) >= sayfalama["boyut"]:
        raise ValueError("sonraki_imlec_yolu dolu sayfada yanıtta yok: {}".format(
            sayfalama["sonraki_imlec_yolu"]))
    return imlec or None


def toplam(yanit, sayfalama):
    """sayfalama.toplam_yolu verilmişse yanıttaki toplam kayıt sayısı; değilse None."""
    if not sayfalama.get("toplam_yolu"):
        return None
    bulundu, deger = yol_izle(yanit, sayfalama["toplam_yolu"])
    if not bulundu or deger is None:
        raise ValueError("toplam_yolu yanıtta yok: {}".format(sayfalama["toplam_yolu"]))
    return int(deger)


def sayfa_sorgusu(sayfalama, sorgu, sayfa, ofset, imlec):
    tur = sayfalama["tur"]
    if tur == "sayfa":
        sorgu.update({sayfalama["sayfa_parametresi"]: sayfa,
                      sayfalama["boyut_parametresi"]: sayfalama.get("boyut", 1000)})
    elif tur == "ofset":
        sorgu.update({sayfalama["ofset_parametresi"]: ofset,
                      sayfalama["boyut_parametresi"]: sayfalama.get("boyut", 1000)})
    elif tur == "imlec" and imlec:
        sorgu[sayfalama["imlec_parametresi"]] = imlec
    return sorgu


def bitti(sayfalama, parca, imlec, okunan, toplam):
    tur, durdur = sayfalama["tur"], sayfalama.get("toplam_ile_dur") and toplam is not None
    return tur == "yok" or not parca or (tur == "imlec" and not imlec) or bool(
        durdur and okunan >= toplam)
'''

DOSYALAR["arsiv.py"] = r'''"""Ham arşiv: her kaynağın gelen verisi, değiştirilmeden, kaynak ve çekim gününe göre yazılır.

Yol: ham/kaynak=<ad>/cekim_tarihi=<YYYY-AA-GG>/calisma=<kimlik>/veri.<parquet|csv.gz>,
yanında bilgi.json (satır sayısı, sütunlar, biçim, yöntem). Var olan dosyanın üzerine
yazılmaz; aynı gece ikinci çalışma yeni kimlikle ayrı klasöre yazar. Parquet motoru
(pyarrow) yoksa ya da tablo Parquet'e çevrilemiyorsa sıkıştırılmış CSV yazılır.
"""
import gzip
import io
import json


def yol(kaynak, cekim_tarihi, calisma_kimligi, dosya_adi):
    return "ham/kaynak={}/cekim_tarihi={}/calisma={}/{}".format(
        kaynak, cekim_tarihi, calisma_kimligi, dosya_adi)


def _bayt(tablo):
    tampon = io.BytesIO()
    try:
        tablo.to_parquet(tampon, index=False)
        return "parquet", tampon.getvalue()
    except Exception:  # Parquet motoru yok ya da karışık türlü sütun: CSV'ye düş
        return "csv.gz", gzip.compress(tablo.to_csv(index=False).encode("utf-8"))


def yaz(ortam, kaynak, tablo, cekim_tarihi, calisma_kimligi, ek_bilgi):
    """Ham tabloyu arşive yazar, veri dosyasının yolunu döndürür."""
    bicim, veri = _bayt(tablo)
    veri_yolu = yol(kaynak, cekim_tarihi, calisma_kimligi, "veri." + bicim)
    if ortam.arsiv_var(veri_yolu):
        raise ValueError("arşiv dosyası zaten var, üzerine yazılmaz: " + veri_yolu)
    ortam.arsiv_yaz(veri_yolu, veri)
    bilgi = dict(ek_bilgi, satir_sayisi=len(tablo), sutunlar=[str(s) for s in tablo.columns],
                 bicim=bicim)
    metin = json.dumps(bilgi, ensure_ascii=False, default=str, indent=2)
    ortam.arsiv_yaz(yol(kaynak, cekim_tarihi, calisma_kimligi, "bilgi.json"),
                    metin.encode("utf-8"))
    return veri_yolu
'''

DOSYALAR["ayar.py"] = r'''"""Ayar dosyaları: yükleme, ek dosyayla birleştirme, kaynak ayarının kurulması ve doğrulama.

params.json ve kaynaklar.json depodaki varsayılandır. Aynı klasördeki params_ek.json ve
kaynaklar_ek.json yalnız farkları taşır ve derin birleştirilir (ekteki değer kazanır, liste ve
sayfalama bloğu bütünüyle değişir): şirkette gerçek sistem adları, iç API adresleri ve teyit
edilen değerler; prova projesinde sentetik ayarlar. Ek dosya depoya girmez; GitHub'dan gelen yeni
varsayılan onu ezmez.
kaynaklar.json iki bölümdür. sistemler: sistem başına ortak ayar (yontem, api kökü ve kimlik,
sayfalama, biçimler); bir sistemi bağlamak için çoğu zaman yalnız burası değişir. kaynaklar:
kaynağa özgü ayar (api.yol, veri kümesi, dosya yolu, alan eşlemesi). Kaynağın etkin ayarı sistem
ayarı + kaynak ayarıdır; api.adres verilmemişse adres = api.adres_koku + "/" + api.yol. Alt
blokların kuralları hat/ayar_alan.py'dedir.
"""
import copy
import re

from avukat_perf import sema
from hat.api_kimlik import kimlik_hatalari
from hat.ayar_alan import alt_blok_hatalari, bilinmeyen as _bilinmeyen

YONTEMLER = ("bekliyor", "dataiku", "api", "dosya")
KAYNAK_ANAHTARLARI = {"yontem", "api", "dataiku", "dosya", "alan_eslemesi", "deger_eslemesi",
                      "genis_degerlendirme", "sayi_bicimi", "tarih_bicimi"}
API_ANAHTARLARI = {"adres", "adres_koku", "yol", "http_yontemi", "basliklar", "sorgu",
                   "govde", "kimlik", "sayfalama", "kayit_yolu", "zaman_asimi_sn", "deneme",
                   "bekleme_sn", "en_cok_sayfa", "ca_dosyasi"}
GEREKEN = {"api": ("api", "adres"), "dataiku": ("dataiku", "veri_kumesi"),
           "dosya": ("dosya", "yol")}
YER_TUTUCU = "BEKLENIYOR"  # depodaki adres kökü yer tutucusu (ör. https://CEKIRDEK-ADRESI-...)
BUTUN_DEGISEN = ("sayfalama",)  # ekteki blok depodakini tamamen ezer (miras alan karışmaz)


def birlestir(taban, ek):
    """Sözlükleri derin birleştirir; ekteki değer kazanır (liste, metin ve sayfalama bloğu
    bütünüyle değişir: imleç kipine geçen ek depodaki sayfa boyutunu miras almaz)."""
    sonuc = copy.deepcopy(taban)
    for anahtar, deger in (ek or {}).items():
        if isinstance(deger, dict) and isinstance(sonuc.get(anahtar), dict) \
                and anahtar not in BUTUN_DEGISEN:
            sonuc[anahtar] = birlestir(sonuc[anahtar], deger)
        else:
            sonuc[anahtar] = copy.deepcopy(deger)
    return sonuc


def yukle(ortam, ad):
    """ad (params ya da kaynaklar): ad.json + varsa ad_ek.json."""
    return birlestir(ortam.ayar_oku(ad + ".json"), ortam.ayar_oku_varsa(ad + "_ek.json"))


def kaynak_ayari(ayarlar, ad):
    """Kaynağın etkin ayarı: sistem ayarı + kaynak ayarı; api adresi kökle yoldan kurulur."""
    sistem = sema.KAYNAKLAR[ad]["sistem"]
    ayar = birlestir(ayarlar.get("sistemler", {}).get(sistem, {}),
                     ayarlar.get("kaynaklar", {}).get(ad, {}))
    api = ayar.get("api")
    if api and not api.get("adres") and api.get("yol") is not None:
        yol = str(api["yol"]).lstrip("/")
        api["adres"] = str(api.get("adres_koku") or "").rstrip("/") + ("/" + yol if yol else "")
    ayar.setdefault("yontem", "bekliyor")
    return ayar


def _sistem_hatalari(sistemler):
    hatalar = []
    for sistem, blok in sorted(sistemler.items()):
        if sistem.startswith("_"):
            continue
        if sistem not in sema.SISTEMLER:
            hatalar.append("sistemler: bilinmeyen sistem " + sistem)
            continue
        hatalar += _bilinmeyen(blok, KAYNAK_ANAHTARLARI, "sistemler." + sistem)
        if (blok.get("api") or {}).get("adres"):  # bütün kaynaklar aynı adrese giderdi
            hatalar.append("sistemler.{}.api: adres değil adres_koku verilir".format(sistem))
    return hatalar


def _yontem_hatalari(ad, ayar):
    if ayar["yontem"] not in YONTEMLER:
        return ["{}: yontem {} olmalı".format(ad, " | ".join(YONTEMLER))]
    if ayar["yontem"] not in GEREKEN:
        return []
    blok, alan = GEREKEN[ayar["yontem"]]
    deger = (ayar.get(blok) or {}).get(alan)
    if not deger:
        return ["{}: {} yöntemi için {}.{} gerekir".format(ad, ayar["yontem"], blok, alan)]
    if ayar["yontem"] == "api" and YER_TUTUCU in str(deger):
        return ["{}: api.adres_koku henüz girilmedi (yer tutucu duruyor)".format(ad)]
    if ayar["yontem"] == "api" and not re.match(r"^https?://\S+$", str(deger)):
        return ["{}: api adresi http:// ya da https:// ile başlamalı, boşluk içermemeli".format(ad)]
    return []


def dogrula(ayarlar):
    """Hata iletileri listesi; boşsa geçerli. Yazım hatası sessizce 'bekliyor' sayılmaz."""
    hatalar = _bilinmeyen(ayarlar, {"sistemler", "kaynaklar"}, "kaynaklar.json")
    hatalar += _sistem_hatalari(ayarlar.get("sistemler", {}))
    kaynaklar = ayarlar.get("kaynaklar", {})
    hatalar += ["kaynaklar: bilinmeyen kaynak " + ad for ad in sorted(kaynaklar)
                if not ad.startswith("_") and ad not in sema.KAYNAKLAR]
    for ad in sema.KAYNAKLAR:
        if ad not in kaynaklar:
            hatalar.append("kaynaklar: tanımsız kaynak " + ad)
            continue
        hatalar += _bilinmeyen(kaynaklar[ad], KAYNAK_ANAHTARLARI, "kaynaklar." + ad)
        ayar = kaynak_ayari(ayarlar, ad)
        hatalar += _bilinmeyen(ayar.get("api"), API_ANAHTARLARI, ad + ".api")
        hatalar += _yontem_hatalari(ad, ayar) + alt_blok_hatalari(ad, ayar)
        if ayar["yontem"] == "api":
            hatalar += kimlik_hatalari((ayar.get("api") or {}).get("kimlik"), ad + ".api")
    return hatalar


def dogrula_veya_dur(ayarlar):
    """Geçerliyse aynen döndürür, değilse ValueError verir."""
    hatalar = dogrula(ayarlar)
    if hatalar:
        raise ValueError("Geçersiz kaynak ayarı: " + "; ".join(hatalar))
    return ayarlar
'''

DOSYALAR["ayar_alan.py"] = r'''"""Kaynak ayarının alt bloklarının doğrulanması: sayfalama, kimlik, dosya, dataiku, biçimler ve
değer eşlemesi (hat.ayar.dogrula çağırır).

Bilinmeyen anahtar (yazım hatası, ör. toplam_yol) sessizce yok sayılmaz. sayfalama.tur yok,
sayfa, ofset ya da imlec olur; türün gerektirdiği alanlar verilmelidir. sayfa türünde baslangic
açıkça yazılır: API ilk sayfayı 0 ya da 1 diye sayar ve yanlış seçim ilk sayfayı sessizce
atlardı. Gereken alanlar yalnız yöntem api iken aranır. sayi_bicimi null, tr ya da en olur.
deger_eslemesi {alan: {kaynak değeri: sözleşme kodu}}; alan sistemin kaynaklarından birinde
olmalı.
"""
from avukat_perf import sema

SAYFALAMA = {"yok": (), "sayfa": ("sayfa_parametresi", "boyut_parametresi", "baslangic"),
             "ofset": ("ofset_parametresi", "boyut_parametresi"),
             "imlec": ("imlec_parametresi", "sonraki_imlec_yolu")}
SAYFALAMA_ANAHTARLARI = {"tur", "sayfa_parametresi", "boyut_parametresi", "boyut", "baslangic",
                         "ofset_parametresi", "imlec_parametresi", "sonraki_imlec_yolu",
                         "toplam_yolu", "toplam_ile_dur"}
KIMLIK_ANAHTARLARI = {"tur", "gizli", "baslik_adi", "parametre", "jeton_adresi", "kapsam",
                      "istemci_dogrulama", "zaman_asimi_sn"}
DOSYA_ANAHTARLARI = {"yol", "ayirici", "kodlama"}
DATAIKU_ANAHTARLARI = {"veri_kumesi"}
SAYI_BICIMLERI = (None, "tr", "en")


def bilinmeyen(blok, izinli, yer):
    """'_' ile başlamayan ve izinli olmayan anahtarlar için hata iletileri."""
    return ["{}: bilinmeyen anahtar {}".format(yer, ad) for ad in sorted(blok or {})
            if not ad.startswith("_") and ad not in izinli]


def _sayfalama_hatalari(sayfalama, yer, api_mi):
    if sayfalama is None:
        return []
    if not isinstance(sayfalama, dict):
        return [yer + ".sayfalama sözlük olmalı"]
    hatalar = bilinmeyen(sayfalama, SAYFALAMA_ANAHTARLARI, yer + ".sayfalama")
    tur = sayfalama.get("tur")
    if tur not in SAYFALAMA:
        return hatalar + ["{}.sayfalama.tur {} olmalı".format(yer, " | ".join(SAYFALAMA))]
    if not api_mi:
        return hatalar
    eksik = [alan for alan in SAYFALAMA[tur] if sayfalama.get(alan) in (None, "")]
    hatalar += ["{}.sayfalama: {} türü için {} gerekir".format(yer, tur, alan) for alan in eksik]
    baslangic = sayfalama.get("baslangic")
    if tur == "sayfa" and baslangic is not None and (isinstance(baslangic, bool) or not isinstance(
            baslangic, int) or baslangic < 0):
        hatalar.append(yer + ".sayfalama.baslangic 0 ya da pozitif tam sayı olmalı")
    return hatalar


def _deger_eslemesi_hatalari(eslesme, sistem, yer):
    if eslesme is None:
        return []
    izinli = {alan for ad, tanim in sema.KAYNAKLAR.items() if tanim["sistem"] == sistem
              for alan in sema.alanlar(ad)}
    duzgun = isinstance(eslesme, dict) and all(
        isinstance(harita, dict) and all(isinstance(kod, str) for kod in harita.values())
        for alan, harita in eslesme.items() if not alan.startswith("_"))  # "_": açıklama
    if not duzgun:
        return [yer + ".deger_eslemesi {alan: {kaynak değeri: kod}} sözlüğü olmalı"]
    return ["{}.deger_eslemesi: {} alanı bu sistemin kaynaklarında yok".format(yer, alan)
            for alan in sorted(eslesme) if not alan.startswith("_") and alan not in izinli]


def alt_blok_hatalari(ad, ayar):
    """Kaynağın etkin ayarındaki alt blokların hataları."""
    api = ayar.get("api") or {}
    hatalar = _sayfalama_hatalari(api.get("sayfalama"), ad + ".api", ayar["yontem"] == "api")
    hatalar += bilinmeyen(api.get("kimlik"), KIMLIK_ANAHTARLARI, ad + ".api.kimlik")
    hatalar += bilinmeyen(ayar.get("dosya"), DOSYA_ANAHTARLARI, ad + ".dosya")
    hatalar += bilinmeyen(ayar.get("dataiku"), DATAIKU_ANAHTARLARI, ad + ".dataiku")
    if ayar.get("sayi_bicimi") not in SAYI_BICIMLERI:
        hatalar.append(ad + ": sayi_bicimi null, tr ya da en olmalı")
    hatalar += _deger_eslemesi_hatalari(ayar.get("deger_eslemesi"),
                                        sema.KAYNAKLAR[ad]["sistem"], ad)
    return hatalar
'''

DOSYALAR["butunluk.py"] = r'''"""Yalnız eklenen tabloların (gözlem, bayrak olayı, çalışma kaydı, dönem yayını) korunması.

Bu tablolar her çalışmada mevcut + yeni olarak baştan yazılır. Okunan tablo son başarılı
çalışmanın yazdığından azsa (kesik yazım ya da elle temizleme) çalışma durur: aksi hâlde geçmiş
kalıcı olarak kaybolur (ör. gözlem tablosu boş okunursa bütün esaslar yeni görülmüş sayılır).
Beklenen satır sayısı tablonun son yazıldığı başarılı çalışmadandır: araya o tabloyu yazmayan
bir gece (ör. kaynağı beklenen gözlem) girse de denetim sürer. Çalışma kaydı boş okunurken bu
tablolardan biri doluysa da çalışma durur: kayıt kaybolmuştur, hat ilk geceymiş gibi sürmez.
Bayrak olaylarından yalnız başarılı gecelerde yazılanlar kullanılır.
"""
from hat.gecmis import basarili_calismalar, sayilar
from hat.veri_kumeleri import DONEM, GOZLEM

EKLENEN = GOZLEM + ("bayrak_olay",) + DONEM


def basarili_satirlar(tablo, kayit):
    """Yalnız eklenen tablonun (bayrak olayı) başarılı gecelerde yazılmış satırları.

    Yazımı yarıda kesilen gecenin satırları ekrana ve sonraki gecenin birleştirmesine girmez;
    aynı olay sonraki başarılı gecede kendi kimliğiyle yeniden yazılır.
    """
    if tablo is None:
        return None
    gece = basarili_calismalar(kayit)
    kimlikler = set() if gece is None else set(gece["calisma_kimligi"].astype(str))
    return tablo[tablo["calisma_kimligi"].astype(str).isin(kimlikler)].reset_index(drop=True)


def veri_kaybi(kayit, tablolar, tur="GECELIK"):
    """Yalnız eklenen tablolardan, son başarılı çalışmanın yazdığından az satırla okunanlar.

    Kesik ya da elle temizlenmiş tablo baştan yazılırsa geçmiş kaybolur (ör. gözlem tablosu
    boş okunursa bütün esaslar yeni görülmüş sayılır); bu durumda çalışma durur.
    """
    beklenen = _beklenen(kayit, tur)
    eksik = []
    for ad, tablo in sorted(tablolar.items()):
        okunan = 0 if tablo is None else len(tablo)
        if beklenen.get(ad) is not None and okunan < beklenen[ad]:
            eksik.append("{} ({} satır bekleniyordu, {} okundu)".format(ad, beklenen[ad], okunan))
    if eksik:
        raise ValueError("VERI_KAYBI: " + "; ".join(eksik))


def _beklenen(kayit, tur):
    """{tablo: satır sayısı}: her tablonun son yazıldığı başarılı çalışmadaki sayısı."""
    beklenen, secili = {}, basarili_calismalar(kayit, tur)
    for _, satir in ([] if secili is None else secili.iterrows()):
        for ad, sayi in sayilar(satir).items():
            if sayi is not None or ad not in beklenen:
                beklenen[ad] = sayi
    return beklenen


def kayitsiz_gecmis(ortam, kayit):
    """Çalışma kaydı boş ya da yokken yalnız eklenen tablolardan biri dolu mu: çalışma durur
    ve kayda yazılmaz (sonraki çalışmalar da durur). İlk kurulumda bu tablolar boştur."""
    if kayit is not None and not kayit.empty:
        return
    dolu = []
    for ad in EKLENEN:
        tablo = ortam.tablo_oku(ad)
        if tablo is not None and not tablo.empty:
            dolu.append(ad)
    if dolu:
        raise ValueError("VERI_KAYBI: calisma_kaydi boş ama yalnız eklenen tablolar dolu: "
                         + ", ".join(dolu))
'''

DOSYALAR["calisma.py"] = r'''"""Çalışma kaydı (yazma tarafı): her çalışmaya kimlik verilir; kaynak başına ve özet satırı.

durum: BASARILI, KALDI (son geçerli veri korundu), KAYNAK_BEKLENIYOR, HESAPLANMADI (zorunlu
başka kaynak bekleniyor). Özet satırı: uretilen ("tablo=satır" çiftleri), hesap_surumu,
hazirlik_surumu, golge (parametreyle açılan gölge mod; iki kriter), golge_zorunlu (yedek yolun
gölgesi; yalnız Kriter 1). Kayıttan türetilen
bilgiler (son başarılı gece, gölge aralıkları) hat/gecmis.py'de, yalnız eklenen tabloların
satır kaybı denetimi hat/butunluk.py'dedir. Zaman İstanbul saatidir.
"""
import uuid

import pandas as pd

from avukat_perf.ortak import SAAT_DILIMI

SUTUNLAR = ["calisma_kimligi", "tur", "kaynak", "yontem", "baslangic", "bitis",
            "cekim_tarihi", "satir_sayisi", "kalite_sonucu", "durum", "arsiv_yolu",
            "aciklama", "uretilen", "hesap_surumu", "hazirlik_surumu", "golge", "golge_zorunlu"]
OZET = "*"


def simdi():
    """İstanbul saatiyle şimdiki an, saat dilimsiz; sunucu UTC olsa da çekim günü doğru olur."""
    return pd.Timestamp.now(tz=SAAT_DILIMI).tz_localize(None)


def kimlik(zaman):
    """Örnek: C20261119020000-a1b2c3."""
    return "C" + pd.Timestamp(zaman).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]


def satir(calisma_kimligi, tur, kaynak, yontem, baslangic, cekim_tarihi):
    kayit = dict.fromkeys(SUTUNLAR)
    kayit.update(calisma_kimligi=calisma_kimligi, tur=tur, kaynak=kaynak, yontem=yontem,
                 baslangic=pd.Timestamp(baslangic), cekim_tarihi=pd.Timestamp(cekim_tarihi))
    return kayit


def tablo(satirlar):
    return pd.DataFrame(satirlar, columns=SUTUNLAR).astype({"satir_sayisi": float})


def kaydet(ortam, onceki, kayitlar, karar, ozet_satiri):
    """Kaynak satırlarına çalışma sonucunu işler, özet satırıyla kayda ekler."""
    durum = {"GECTI": "BASARILI", "KALDI": "KALDI",
             "KAYNAK_BEKLENIYOR": "HESAPLANMADI"}.get(karar, karar)
    for kayit in kayitlar:
        kayit["durum"] = kayit["durum"] or durum
        kayit["bitis"] = simdi()
    ozet = dict(ozet_satiri, durum=karar, kalite_sonucu=karar, bitis=simdi())
    if ozet.get("uretilen"):  # kaydın kendi satır sayısı da korunur (bkz. butunluk.veri_kaybi)
        toplam = (0 if onceki is None else len(onceki)) + len(kayitlar) + 1
        ozet["uretilen"] += ",calisma_kaydi={}".format(toplam)
    yeni = tablo(kayitlar + [ozet])
    ortam.tablo_yaz("calisma_kaydi", yeni if onceki is None else
                    pd.concat([onceki, yeni], ignore_index=True))


def kalite_ekle(ortam, sonuclar, cekim):
    """Kalite sonuçlarını önceki çalışmaların sonuçlarına ekler."""
    if not sonuclar:
        return
    eski = ortam.tablo_oku("kalite_sonucu")
    yeni = pd.concat(sonuclar, ignore_index=True).assign(cekim_tarihi=pd.Timestamp(cekim))
    ortam.tablo_yaz("kalite_sonucu", yeni if eski is None else
                    pd.concat([eski, yeni], ignore_index=True))
'''

DOSYALAR["dataiku_ortam.py"] = r'''"""Dataiku ortamı: tablolar Dataiku veri kümesi, ham arşiv yönetilen klasör (MinIO'ya
bağlı S3 bağlantısı), gizli değerler Dataiku kullanıcı gizlileri (Profil > Gizliler).

Senaryo "Python kodu çalıştır" adımında, not defterinde ve web uygulaması arka ucunda
çalışır (tariflerdeki giriş/çıkış bildirimi kısıtı bu bağlamlarda yoktur). Aktarımdan sonra
dataiku/kontrol/aktarim_kontrol.py not defterinde her yöntem bir kez denenir.
Okuma veri kümesi şemasındaki türlerle yapılır (infer_with_pandas=False): pandas'ın tür
tahmini "000123" gibi kimlikleri sayıya çevirip baştaki sıfırları siler. Boş değerli tamsayı
sütununda tamsayılar ondalık (int_as_float), boş değerli mantıksal sütun metin (bool_as_str)
okunur; üçü de olmazsa okuma hata verir (pandas tahminine düşülmez). Parametreyi tanımayan eski
sürümde varsayılan okumaya düşülür ve uyarı yazılır. Şeması boş (hiç yazılmamış) veri kümesi "ilk
çalışma" sayılır; başka her okuma hatası yukarı iletilir: yalnız eklenen bir tablo (çalışma
kaydı, gözlem, bayrak olayı, dönem yayını) geçici bir hatada boş sanılıp üzerine yazılırsa
geçmiş silinirdi. Saat dilimli tarih sütunu UTC'ye çevrilip saat dilimi kaldırılır: kütüphane saat
dilimsiz yazar, Dataiku bunu UTC sayar; böylece okunan değer yazılanla aynıdır.
Kaynak dosyaları (yöntem "dosya") "kaynak_dosyalari" yönetilen klasöründen okunur.
Yöntem adları Dataiku Python API'sine dayanır; sürüm farkında yalnız bu dosya değişir.
"""
import os
import shutil
import tempfile

from hat.ortam import json_oku
from hat.veri_kumeleri import ARSIV_KLASORU, AYAR_KLASORU, DOSYA_KLASORU


def _sema_turleriyle(veri_kumesi, ad):
    for secenek in ({"infer_with_pandas": False},
                    {"infer_with_pandas": False, "int_as_float": True},
                    {"infer_with_pandas": False, "int_as_float": True, "bool_as_str": True}):
        try:
            return veri_kumesi.get_dataframe(**secenek)
        except TypeError:  # eski sürüm: parametre tanınmıyor
            print("şema türleriyle okunamadı, varsayılan okuma: " + ad)
            return veri_kumesi.get_dataframe()
        except ValueError:  # boş değerli tamsayı ya da mantıksal sütun: bir sonraki seçenek
            continue
    raise ValueError(ad + ": şema türleriyle okunamadı (boş değerli tamsayı ya da mantıksal "
                     "sütun olabilir); pandas tahminine düşülmez, kimliklerin sıfırları silinirdi")


def _utc_saf(tablo):
    for sutun in tablo.columns:
        if getattr(tablo[sutun].dtype, "tz", None) is not None:
            tablo[sutun] = tablo[sutun].dt.tz_convert("UTC").dt.tz_localize(None)
    return tablo


class DataikuOrtam(object):
    """arsiv_klasoru: ham arşiv için Dataiku yönetilen klasörünün adı."""

    def __init__(self, arsiv_klasoru=ARSIV_KLASORU):
        import dataiku
        self._dataiku = dataiku
        self._klasor = dataiku.Folder(arsiv_klasoru)

    def tablo_oku(self, ad):
        """Kütüphanenin yazdığı tablo; şeması boş (hiç yazılmamış) veri kümesi için None.

        Okuma hatası (bağlantı, yetki, olmayan veri kümesi) yukarı iletilir; gece durur.
        """
        veri_kumesi = self._dataiku.Dataset(ad)
        if not veri_kumesi.read_schema(raise_if_empty=False):
            return None
        return _utc_saf(_sema_turleriyle(veri_kumesi, ad))

    def tablo_yaz(self, ad, tablo):
        self._dataiku.Dataset(ad).write_with_schema(tablo)

    def veri_kumesi_oku(self, ad):
        """Kaynak veri kümesi (yöntem "dataiku"); tarih dönüşümü kalite kapısında yapılır."""
        return _sema_turleriyle(self._dataiku.Dataset(ad), ad)

    def dosya_yolu(self, yol):
        """Kaynak dosyasını yönetilen klasörden geçici dosyaya indirir, yolunu döndürür."""
        hedef = os.path.join(tempfile.mkdtemp(), os.path.basename(yol))
        klasor = self._dataiku.Folder(DOSYA_KLASORU)
        with klasor.get_download_stream(yol) as akis, open(hedef, "wb") as dosya:
            shutil.copyfileobj(akis, dosya)
        return hedef

    def gizli(self, ad):
        bilgi = self._dataiku.api_client().get_auth_info(with_secrets=True)
        for gizli in bilgi.get("secrets", []):
            if gizli.get("key") == ad:
                return gizli.get("value")
        if ad in os.environ:
            return os.environ[ad]
        raise KeyError("Dataiku kullanıcı gizlisi bulunamadı: " + ad)

    def arsiv_var(self, yol):
        yollar = self._klasor.list_paths_in_partition()
        return "/" + yol.lstrip("/") in set("/" + y.lstrip("/") for y in yollar)

    def arsiv_yaz(self, yol, bayt):
        self._klasor.upload_data("/" + yol.lstrip("/"), bayt)

    def ayar_oku(self, ad, klasor=AYAR_KLASORU):
        """Yönetilen klasördeki JSON ayar dosyası (ör. params.json); Windows'ta kaydedilmiş
        dosyanın baştaki BOM işareti sorun çıkarmaz."""
        with self._dataiku.Folder(klasor).get_download_stream(ad) as akis:
            return json_oku(akis.read().decode("utf-8-sig"), ad)

    def ayar_oku_varsa(self, ad, klasor=AYAR_KLASORU):
        """Ek ayar dosyası (ör. params_ek.json) klasörde varsa içeriği, yoksa None."""
        yollar = self._dataiku.Folder(klasor).list_paths_in_partition()
        if "/" + ad not in set("/" + y.lstrip("/") for y in yollar):
            return None
        return self.ayar_oku(ad, klasor)
'''

DOSYALAR["donem_akisi.py"] = r'''"""Dönem sonu akışı: dönem kesitinde sütun puanları → sonuç kontrolleri → sürümlü yayın.

Gecelik akışın yazdığı model ve gözlem tablolarını okur, puanları dönemin son gününde
hesaplar. Kontroller geçmezse yayın yapılmaz (KALDI). Dönem sonunu kapsayan (kesitten
sonraki bir günde) başarılı gecelik çekim yoksa da yayın yapılmaz: bayat modelle hesaplanan
dönem, son günlerde girilmiş esas kaydını görmez. Yayımlanan dönem değiştirilmez; içerik
ya da kurallar değiştiyse yeni sürüm eklenir. Birleşik puan yalnız yeni sürümde, o sürümün
parametreleriyle hesaplanır ve birlesik_donem tablosuna sürümüyle eklenir; geçmiş dönemler
yeniden hesaplanmaz. Önce puan_donem (yayının kendisi), sonra birlesik_donem yazılır: ekran
yayımlanmamış bir sürümü göstermez. Arada kesilen çalışma tekrarlanınca eksik birleşik sürüm,
yayımlanmış sürümün kendi bilgileriyle tamamlanır.
"""
import pandas as pd

from avukat_perf import birlesik, donem, kalite
from avukat_perf.params import dogrula_veya_dur
from avukat_perf.surum import hesap_surumu
from hat import butunluk, calisma, donem_kayit, gecmis, hesap, model, okuma


def yayimlanacak_donemler(degisken, simdi, puan_donem):
    """Dönem sonu senaryosunun yayımlayacağı dönemler.

    degisken: "donem" proje değişkeni (düzeltme için elle yazılır) ya da boş. Bir önceki ay
    henüz yayımlanmadıysa her zaman listededir: değişkeni silmek unutulsa da yeni ay yayımlanır.
    """
    onceki = donem.onceki_donem(simdi)
    yayimlanan = set() if puan_donem is None or puan_donem.empty else set(puan_donem["donem"])
    donemler = [degisken] if degisken else []
    if onceki not in donemler and (not degisken or onceki not in yayimlanan):
        donemler.append(onceki)
    return donemler


def calistir(ortam, params, donem_adi, simdi=None):
    """Bir dönemi yayımlar; özet sözlüğü döndürür (karar, yayin). Model tablosu okunamazsa ya
    da hesap veya yayın hata verirse de çalışma kayda geçer (hat/donem_kayit.py)."""
    dogrula_veya_dur(params)
    simdi = calisma.simdi() if simdi is None else pd.Timestamp(simdi)
    kesit = donem.kesit(donem_adi)
    kimlik = calisma.kimlik(simdi)
    onceki = ortam.tablo_oku("calisma_kaydi")
    butunluk.kayitsiz_gecmis(ortam, onceki)
    for tur in ("GECELIK", "DONEM_SONU"):  # kesik kayıt: çalışma kayda yazmadan durur
        butunluk.veri_kaybi(onceki, {"calisma_kaydi": onceki}, tur)
    ozet = calisma.satir(kimlik, "DONEM_SONU", calisma.OZET, "", simdi, kesit)
    ozet.update(aciklama="dönem " + donem_adi, hesap_surumu=hesap_surumu(params))
    try:
        karar, yayin, kontrol = _calistir(ortam, params, donem_adi, simdi, onceki, ozet)
    except Exception as hata:  # hesap ya da yayın hatası: kayda geçer, senaryo düşer
        donem_kayit.hata(ortam, onceki, ozet, okuma.ileti(hata))
        raise
    if kontrol is not None:  # yayından sonraki kayıt hata yolunun dışında: KALDI'ya çevrilmez
        calisma.kaydet(ortam, onceki, [], karar, ozet)
        calisma.kalite_ekle(ortam, [kontrol], kesit)
    return {"calisma_kimligi": kimlik, "karar": karar, "yayin": yayin}


def _calistir(ortam, params, donem_adi, simdi, onceki, ozet):
    kesit, kimlik = donem.kesit(donem_adi), ozet["calisma_kimligi"]
    eski = {"puan_donem": ortam.tablo_oku("puan_donem"),
            "birlesik_donem": ortam.tablo_oku("birlesik_donem")}
    butunluk.veri_kaybi(onceki, eski, "DONEM_SONU")  # kesik yayın tablosu: çalışma durur
    mdl = model.oku(ortam, onceki)
    karar = donem_kayit.model_eksik(ortam, onceki, mdl, ozet)
    if karar:
        return karar, None, None
    # Dönem kendi kesitindeki gölge/canlı durumuyla hesaplanır ve sürümlenir, bugünkü parametreyle
    # değil: sonradan açılan ya da kapanan gölge mod yayımlanmış dönemi değiştirmez. Yedek yolun
    # gölgesi (golge_k1) yalnız Kriter 1'i kapsar.
    params = dict(params, uyari=dict(params["uyari"],
                                     golge_mod=gecmis.golgede_mi(onceki, kesit, "K2"),
                                     golge_k1=gecmis.golgede_mi(onceki, kesit, "K1")))
    sonuc, durumlar = hesap.hesapla(mdl, kesit, params)
    tablo = sonuc["sonuc_puan_guncel"].assign(donem=donem_adi)
    kapsam = donem.veri_kapsami(gecmis.son_basarili(onceki, "dosya", "2200-01-01")[0],
                                donem_adi)
    kontrol = pd.concat([donem.sonuc_kontrolleri(tablo), kapsam,
                         donem_kayit.hazirlik_kontrolu(onceki, params)],
                        ignore_index=True).assign(calisma_kimligi=kimlik)
    karar, yayin, uretilen = kalite.karar(kontrol), None, None
    if karar == "GECTI":
        bilgi = {"calisma_kimligi": kimlik, "hesap_surumu": hesap_surumu(params),
                 "yayin_zamani": simdi}
        puan_donem, yayin = donem.yayinla(eski["puan_donem"], tablo, donem_adi, bilgi)
        if yayin != "DEGISMEDI":
            ortam.tablo_yaz("puan_donem", puan_donem)
        uretilen = "puan_donem={},birlesik_donem={}".format(
            len(puan_donem), _birlesik_tamamla(ortam, puan_donem, donem_adi, params))
    metin = donem_kayit.METIN
    ozet["aciklama"] += " · yayın {}".format(metin.get(yayin, yayin)) + "".join(
        " · {}: {}".format(metin.get(ad, ad), metin.get(deger, deger))
        for ad, deger in sorted(durumlar.items()) if ad != "golge_zorunlu")
    ozet.update(hesap_surumu=hesap_surumu(params), uretilen=uretilen)
    return karar, yayin, kontrol


def _birlesik_tamamla(ortam, puan_donem, donem_adi, params):
    """Dönemin yayımlanmış son sürümünün birleşik puanı yoksa ya da eksik yazılmışsa yazar;
    birleşik dönem tablosunun satır sayısını döndürür.

    Sürümün satırları yayımlanan avukatların tamamını, aynı kimlik ve kural sürümüyle
    içeriyorsa dokunmaz. Birleşik puan yayımlanan satırlardan, o sürümün kimliği, kural
    sürümü ve yayın zamanıyla kurulur (DEGISMEDI'de kurallar o sürümün kurallarıdır).
    """
    son = donem.son_surum(puan_donem[puan_donem["donem"] == donem_adi])
    surum = int(son["yayin_surumu"].iloc[0])
    mevcut = ortam.tablo_oku("birlesik_donem")
    bilgi = son[["calisma_kimligi", "hesap_surumu", "yayin_zamani"]].iloc[0].to_dict()
    secili = None if mevcut is None or mevcut.empty else mevcut[
        (mevcut["donem"] == donem_adi) & (mevcut["yayin_surumu"] == surum)]
    if secili is not None and set(secili["avukat_kodu"]) == set(son["avukat_kodu"]) and set(
            zip(secili["calisma_kimligi"].astype(str), secili["hesap_surumu"].astype(str))) == {
            (str(bilgi["calisma_kimligi"]), str(bilgi["hesap_surumu"]))}:
        return len(mevcut)
    yeni = birlesik.birlestir(son, params).assign(donem=donem_adi, yayin_surumu=surum, **bilgi)
    tablo = donem.surum_ekle(mevcut, yeni, donem_adi, surum)
    ortam.tablo_yaz("birlesik_donem", tablo)
    return len(tablo)
'''

DOSYALAR["donem_kayit.py"] = r'''"""Dönem sonu çalışmasının hazırlık kontrolü, açıklama metinleri ve yayın dışındaki
sonuçlarının kayda geçmesi.

Model tablosu okunamazsa ya da hesap veya yayın hata verirse de calisma_kaydi'na DONEM_SONU
özet satırı ve kalite_sonucu'na çalışmanın kimliğiyle denetim satırı yazılır (Veri Durumu ve
izleme bu çalışmayı görür). Son başarılı gecenin yazdığı model tablosu okunamıyor ya da başka
bir gecenin etiketini taşıyorsa kesiktir: KALDI (VERI_KAYBI). O gece hiç yazılmadıysa
(kaynağı bekleniyor) KAYNAK_BEKLENIYOR.
"""
import pandas as pd

from avukat_perf import sema
from avukat_perf.kalite import SONUC
from avukat_perf.surum import hazirlik_surumu
from hat import calisma, gecmis
from hat.model import GOZLEMLER

# Model tablosunun kaynağı; kaynağı zorunlu olan model tablosu dönem hesabı için zorunludur.
MODEL_KAYNAGI = {"dosya": "dosya", "atama_donemi": "atama_log", "hareket": "tahsilat_hareketi",
                 "bekleme": "bekleme", "degerlendirme": "degerlendirme", "avukat": "avukat",
                 "k2_goruntu": "k2_goruntu"}
ZORUNLU = tuple(ad for ad, kaynak in MODEL_KAYNAGI.items() if kaynak in sema.zorunlu_kaynaklar())


def _kontrol(kimlik, kontrol, deger, aciklama):
    return pd.DataFrame([("donem", kontrol, "KALDI", deger, 0, aciklama)],
                        columns=SONUC).assign(calisma_kimligi=kimlik)


def model_eksik(ortam, onceki, mdl, ozet):
    """Son gecenin yazdığı bir model ya da gözlem tablosu okunamıyorsa (isteğe bağlı olanlar
    dahil: kesik tahsilat hareketi Tahsilat'ı sessizce "kaynak bekleniyor" yayımlardı) ya da
    zorunlu model tablosu yoksa kayda geçirip kararı döndürür; tablolar tamsa None."""
    uretilen = gecmis.son_sayilar(onceki)
    adlar = [("model_" + ad, ad) for ad in MODEL_KAYNAGI] + [(ad, ad) for ad in GOZLEMLER]
    kesik = [tablo for tablo, ad in adlar if tablo in uretilen and mdl[ad] is None]
    eksik = [ad for ad in ZORUNLU if mdl[ad] is None]
    if not kesik and not eksik:
        return None
    kimlik, kesit = ozet["calisma_kimligi"], ozet["cekim_tarihi"]
    if kesik:
        metin = "son gecenin model tablosu okunamadı ya da kesik: " + ", ".join(kesik)
        ozet["aciklama"] = ozet["aciklama"] + " · VERI_KAYBI · " + metin
        calisma.kaydet(ortam, onceki, [], "KALDI", ozet)
        calisma.kalite_ekle(ortam, [_kontrol(kimlik, "MODEL_TABLOSU", len(kesik), metin)],
                            kesit)
        return "KALDI"
    ozet["aciklama"] = ozet["aciklama"] + " · kaynak bekleniyor: " + ", ".join(eksik)
    calisma.kaydet(ortam, onceki, [], "KAYNAK_BEKLENIYOR", ozet)
    return "KAYNAK_BEKLENIYOR"


def hata(ortam, onceki, ozet, ileti):
    """Hesap ya da yayın hatası: KALDI ve HESAP_HATASI kayda geçer (hata sonra iletilir)."""
    ozet["aciklama"] = ozet["aciklama"] + " · HESAP_HATASI · " + ileti
    calisma.kaydet(ortam, onceki, [], "KALDI", ozet)
    calisma.kalite_ekle(ortam, [_kontrol(ozet["calisma_kimligi"], "HESAP_HATASI", 1, ileti)],
                        ozet["cekim_tarihi"])


METIN = {"sure": "süre", "kalite_davranis": "kalite ve davranış", "KAYNAK_BEKLENIYOR":
         "kaynak bekleniyor", "TEYIT_BEKLIYOR": "ölçek teyidi bekleniyor", "YENI": "yeni sürüm",
         "DUZELTME": "düzeltme sürümü", "DEGISMEDI": "değişmedi", None: "yapılmadı"}


def hazirlik_kontrolu(onceki, params):
    """Son gecenin model tabloları güncel hazırlık kuralı ve koduyla mı üretildi.

    Değilse yayın yapılmaz: içerik eski kuralla hazırlanmışken yayın yeni sürümü taşırdı."""
    gece = gecmis.son_basarili_gece(onceki)
    kayitli = None if gece is None else gece.get("hazirlik_surumu")
    fark = int(isinstance(kayitli, str) and kayitli != hazirlik_surumu(params))
    return pd.DataFrame([("donem", "HAZIRLIK_SURUMU", "KALDI" if fark else "GECTI", fark, 0,
                          "hazırlık kuralı ya da kod son gecelik çalışmadan sonra değişti; "
                          "önce gecelik çalışma gerekir" if fark else "")], columns=SONUC)
'''

DOSYALAR["gecmis.py"] = r'''"""Çalışma kaydından türetilen geçmiş bilgisi (yalnız okur, hesap yapmaz).

Son başarılı çekim ve gece, o gecenin yazdığı tablolar ve satır sayıları, kimlik, gölge
durumu ve gölge gecelerinin kapsadığı günler (tablo korunması hat/butunluk.py). Özet satırının
uretilen alanı "tablo=satır" çiftleridir; eski kayıtlarda yalnız tablo adı olabilir (sayı
bilinmez). Kayıt SQL'de durabilir; satır sırası garanti olmadığı için zamana göre sıralanır.
"""
import pandas as pd

from avukat_perf.mantik import dogru_mu as _dogru  # "true", True, E, 1: tek çözücü
from hat.calisma import OZET


def son_basarili(kayit, kaynak, once):
    """'once' anından önce başlamış son başarılı çekimin (günü, satır sayısı); yoksa (None, None).

    once bu çalışmanın başlangıç anıdır: aynı gün yeniden çalıştırmada taban aynı günün önceki
    (ör. 02:00) çekimidir, gün içinde girilen değerin ilk görülme günü bugün olur. Gözlem
    kaynağının boş görüntüsü kapıda durduğu için başarılı çekim hiçbir zaman boş değildir.
    """
    if kayit is None or kayit.empty:
        return None, None
    secili = kayit[(kayit["kaynak"] == kaynak) & (kayit["durum"] == "BASARILI")]
    secili = secili.assign(_gun=pd.to_datetime(secili["cekim_tarihi"]),
                           _bas=pd.to_datetime(secili["baslangic"]))
    secili = secili[secili["_bas"] < pd.Timestamp(once)].sort_values(["_bas", "_gun"])
    if secili.empty:
        return None, None
    en_son = secili.iloc[-1]
    return pd.Timestamp(en_son["cekim_tarihi"]), int(float(en_son["satir_sayisi"]))


def basarili_calismalar(kayit, tur="GECELIK"):
    """Başarılı gecelik (ya da DONEM_SONU) çalışmaların özet satırları, başlangıç sırasıyla."""
    if kayit is None or kayit.empty or "uretilen" not in kayit.columns:
        return None
    secili = kayit[(kayit["kaynak"] == OZET) & (kayit["tur"] == tur) &
                   kayit["uretilen"].notna() & (kayit["durum"] == "GECTI")]
    return secili.assign(_bas=pd.to_datetime(secili["baslangic"])).sort_values("_bas")


def son_basarili_gece(kayit):
    """Son başarılı gecenin özet satırı; yoksa None."""
    gece = basarili_calismalar(kayit)
    return None if gece is None or gece.empty else gece.iloc[-1]


def sayilar(satir):
    """Özet satırının uretilen alanı: {tablo: satır sayısı ya da None (eski kayıt)}."""
    if satir is None or pd.isna(satir.get("uretilen")):
        return {}
    sonuc = {}
    for parca in str(satir["uretilen"]).split(","):
        ad, _, sayi = parca.partition("=")
        sonuc[ad] = int(sayi) if sayi else None
    return sonuc


def son_sayilar(kayit, tur="GECELIK"):
    """Son başarılı çalışmanın yazdığı tablolar ve satır sayıları."""
    secili = basarili_calismalar(kayit, tur)
    return {} if secili is None or secili.empty else sayilar(secili.iloc[-1])


def son_uretilen(kayit):
    """Son başarılı gecelik çalışmanın yazdığı tablo adları; hiç başarılı gece yoksa None."""
    son = son_basarili_gece(kayit)
    return None if son is None else set(sayilar(son))


def son_kimlik(kayit):
    """Son başarılı gecelik çalışmanın kimliği; yoksa None."""
    son = son_basarili_gece(kayit)
    return None if son is None else str(son["calisma_kimligi"])


def son_golge_zorunlu(kayit):
    """Son başarılı gece Kriter 1'i yedek yoldan (zorunlu gölge mod) mu hesapladı."""
    son = son_basarili_gece(kayit)
    return son is not None and _dogru(son.get("golge_zorunlu"))


def son_golge(kayit):
    """Son başarılı gece gölge modda mı hesaplandı (parametre ya da yedek yol)."""
    son = son_basarili_gece(kayit)
    return son is not None and (_dogru(son.get("golge")) or _dogru(son.get("golge_zorunlu")))


def golge_araliklari(kayit, kriter="K1"):
    """Kriterin gölge gecelerinin kapsadığı günler: [(alt, ust)], alt < gün <= ust (alt None:
    sınırsız). Her başarılı gece önceki gecenin çekim gününden sonraki günleri kendi çekim
    gününe kadar kapsar (ilk gece öncesini de). Gölge gecesinin günündeki düşüm bildirilmediği
    için puana girmez; aralıklar geçmişe dönük değişmez. Parametreyle açılan gölge (golge) iki
    kriteri, yedek yolun zorunlu gölgesi (golge_zorunlu) yalnız Kriter 1'i kapsar.
    """
    gece = basarili_calismalar(kayit)
    if gece is None or gece.empty:
        return []
    bos = pd.Series(None, index=gece.index, dtype=object)
    golge = gece.get("golge", bos).map(_dogru)
    if kriter == "K1":
        golge = golge | gece.get("golge_zorunlu", bos).map(_dogru)
    araliklar, onceki = [], None
    for cekim, golgede in zip(gece["cekim_tarihi"], golge):
        gun = pd.Timestamp(cekim).normalize()
        if golgede and araliklar and araliklar[-1][1] == onceki:
            araliklar[-1] = (araliklar[-1][0], gun)  # art arda gölge geceleri tek aralık
        elif golgede:
            araliklar.append((onceki, gun))
        onceki = gun if onceki is None else max(onceki, gun)
    return araliklar


def golgede_mi(kayit, gun, kriter="K1"):
    """Gün kriterin bir gölge gecesinin kapsadığı aralıkta mı (dönem kendi kesitinin durumuyla)."""
    gun, araliklar = pd.Timestamp(gun).normalize(), golge_araliklari(kayit, kriter)
    return any((alt is None or gun > alt) and gun <= ust for alt, ust in araliklar)
'''

DOSYALAR["hesap.py"] = r'''"""Hesap: hazırlanmış model tablolarından bütün sonuç tablolarını üretir (giriş-çıkış yok).

model sözlüğü: dosya, atama_donemi (zorunlu); hareket, bekleme, degerlendirme, avukat,
gozlem_*, k2_goruntu (yoksa None); golge_zorunlu, bekleme_eksik, golge_araliklari. Kaynağı
olmayan sonuç üretilmez; nedeni durumlar sözlüğündedir (KAYNAK_BEKLENIYOR ya da TEYIT_BEKLIYOR).
Dosya bazında tahsilat hareketi gelmediyse Tahsilat sütunu ve tahsilat tabloları üretilmez,
diğer sütunlar ve portföy hesaplanır. Kriter 1, Kriter 2 ve süre puanı hat/hesap_sure.py'dedir.
"""
import pandas as pd

from avukat_perf import (aciklama, agirlik, birlesik, donem, gozlem, kalite_davranis, portfoy,
                         tahsilat, tahsilat_evren)
from hat import hesap_sure


def _kalite_davranis(model, kesit, params, sonuc, durum):
    if model.get("degerlendirme") is None:
        durum["kalite_davranis"] = "KAYNAK_BEKLENIYOR"
        return None
    sonuc["sonuc_mevcut_degerlendirme"] = kalite_davranis.mevcut_alanlar(
        model["degerlendirme"], kesit, params)
    if not kalite_davranis.teyitli(params):
        durum["kalite_davranis"] = "TEYIT_BEKLIYOR"
        return None
    sutun, alt = kalite_davranis.puanla(model["degerlendirme"], kesit, params)
    sonuc["sonuc_kalite_davranis_sutun"], sonuc["sonuc_kalite_davranis_alt"] = sutun, alt
    return sutun


def _tahsilat(model, kesit, params, sonuc, durum):
    """Tahsilat sütunu ve tahsilat tabloları; dosya bazında hareket gelmediyse üretilmez
    (Tahsilat sütunu KAYNAK_BEKLENIYOR, toplamlardan yedek puan yok)."""
    dosya, atamalar, hareket = model["dosya"], model["atama_donemi"], model.get("hareket")
    if hareket is None:
        durum["tahsilat"] = "KAYNAK_BEKLENIYOR"
        return None
    # Kapanan dosyadan tahsilat beklenmez: sıklık ve güncellikte süresi kapandığı gün biter.
    # Koşul (rücu kodu ve açık bakiye) kaybı her gece gözlenir; geçmiş kesit aynı sonucu verir.
    kapanis = gozlem.kapanislar(model.get("gozlem_kosul"), kesit)
    avukat_t, grup_t, brans_t = tahsilat.hesapla(dosya, atamalar, hareket, kesit, params, kapanis)
    etiketler = {"tutar_bandi": ("bant_etiketi", portfoy.bant_etiketleri(params)),
                 "yas_bandi": ("yas_etiketi", tahsilat_evren.yas_etiketleri(params["tahsilat"]))}
    for sutun, (ad, etiket) in etiketler.items():  # etiket hesap anındaki sınırlardan
        if sutun in grup_t.columns:
            grup_t = grup_t.assign(**{ad: grup_t[sutun].map(etiket)})
    sonuc["sonuc_tahsilat_avukat"], sonuc["sonuc_tahsilat_grup"] = avukat_t, grup_t
    sonuc["sonuc_tahsilat_brans"] = brans_t
    for ad, islev in (("sonuc_tahsilat_aylik", portfoy.aylik_tahsilat),
                      ("sonuc_tahsilat_yillik", portfoy.yillik_tahsilat)):
        sonuc[ad] = islev(dosya, atamalar, hareket, kesit, params)
    return avukat_t


def hesapla(model, kesit, params):
    """(sonuç tabloları sözlüğü, durumlar sözlüğü)."""
    sonuc, durum = {}, {}
    avukat_t = _tahsilat(model, kesit, params, sonuc, durum)
    sonuc["sonuc_portfoy"] = portfoy.ozet(model["dosya"], model["atama_donemi"], kesit, params)
    sure = hesap_sure.kriterler(model, kesit, params, sonuc, durum)
    durum["golge_zorunlu"] = bool(model.get("golge_zorunlu"))
    kalite_davranis_t = _kalite_davranis(model, kesit, params, sonuc, durum)
    kaynaklar = [avukat_t, sonuc["sonuc_portfoy"], sure, kalite_davranis_t, model.get("avukat")]
    avukatlar = sorted({kod for tablo in kaynaklar if tablo is not None
                        for kod in tablo["avukat_kodu"].dropna()})
    sutunlar = {"tahsilat": avukat_t, "sure": sure}
    for ad in ("kalite", "davranis"):
        sutunlar[ad] = None if kalite_davranis_t is None else \
            kalite_davranis_t[kalite_davranis_t["sutun"] == ad]
    neden = {"tahsilat": durum.get("tahsilat"), "sure": durum.get("sure"),
             "kalite": durum.get("kalite_davranis"), "davranis": durum.get("kalite_davranis")}
    tablo = donem.puan_tablosu(str(pd.Timestamp(kesit).date()), sutunlar, avukatlar,
                               {sutun: deger for sutun, deger in neden.items() if deger})
    agirliklar = agirlik.sutun_agirliklari(params)  # hesap anındaki ağırlık sonuca yazılır
    sonuc["sonuc_puan_guncel"] = tablo.assign(agirlik=tablo["sutun"].map(agirliklar))
    sonuc["sonuc_birlesik"] = birlesik.birlestir(tablo, params)
    sonuc["sonuc_aciklama"] = aciklama.uret(params, avukat_t, kalite_davranis_t, sure,
                                            sonuc["sonuc_birlesik"],
                                            sonuc.get("sonuc_kalite_davranis_alt"))
    return sonuc, durum
'''

DOSYALAR["hesap_sure.py"] = r'''"""Süre hesabı: Kriter 1, Kriter 2, süre özeti, e-posta listesi ve süre puanı (giriş-çıkış yok).

Gölge kriter bazındadır (sure_ozet.golge_kriterleri): golge_mod parametresi iki kriteri, esasın
yedek yoldan (çekirdek sistemin takip bilgileri) gelmesi yalnız Kriter 1'i gölgeye alır
(golge_k1); Kriter 2'nin verisi yedek yola bağlı değildir. Gölgedeki kriterde e-posta
gönderilmez; bir kriter gölgedeyse süre puanı yayımlanmaz. Canlı hesapta gölge gecelerinin
kapsadığı günlerdeki düşüm puana girmez; aralıklar da kriter bazındadır
(model["golge_araliklari"] = {"K1": [...], "K2": [...]}). Süre puanı Kriter 1 ve Kriter 2'nin
ikisi de varken üretilir. Haklı bekleme kaynağı daha önce okunmuşken o gece gelmediyse Kriter 1
hesaplanmaz.
"""
import pandas as pd

from avukat_perf import hazirlik, kriter1, kriter2, olay, sure_ozet, sure_puani
from hat import gecmis

KRITERLER = ("K1", "K2")


def golge_araliklari(kayit):
    """{kriter: çalışma kaydındaki gölge gecelerinin kapsadığı gün aralıkları}."""
    return {kriter: gecmis.golge_araliklari(kayit, kriter) for kriter in KRITERLER}


def esas_kaynaklari(model):
    """{kriter: esasın kaynağı}: Kriter 1 yedek yoldan ya da dava takipten, Kriter 2 dava
    takipten. Bayrak olayına yazılır (olay.ANAHTAR)."""
    return {"K1": olay.YEDEK if model.get("golge_zorunlu") else olay.DAVA_TAKIP,
            "K2": olay.DAVA_TAKIP}


def etkin_parametreler(params, model):
    """Esas yalnız yedek yoldan geliyorsa Kriter 1 gölge modda çalışır (parametreden bağımsız)."""
    if not model.get("golge_zorunlu") or params["uyari"].get("golge_k1"):
        return params
    return dict(params, uyari=dict(params["uyari"], golge_k1=True))


def sure_girdisi(k1, k2):
    """Kriter 1 ve Kriter 2 sonuçlarını süre puanı girdisinde birleştirir."""
    parcalar = []
    if k1 is not None:
        parcalar.append(k1.assign(kriter="K1", surec="ILK_ISLEM"))
    if k2 is not None:
        parcalar.append(k2.assign(kriter="K2", surec=k2["surec_turu"]))
    return pd.concat(parcalar, ignore_index=True)


def _degerlendir(model, kesit, params):
    k1 = k2 = None
    dosya, atamalar = model["dosya"], model["atama_donemi"]
    esas = model.get("gozlem_esas_yedek" if model.get("golge_zorunlu") else "gozlem_esas")
    if esas is not None and not model.get("bekleme_eksik"):
        k1 = kriter1.degerlendir(hazirlik.k1_atamalari(atamalar, dosya),
                                 hazirlik.k1_esaslari(esas), model.get("bekleme"), kesit, params)
    if model.get("k2_goruntu") is not None:
        surec = hazirlik.k2_surecleri(model["k2_goruntu"], dosya, model.get("gozlem_dava"),
                                      model.get("gozlem_kosul"), model.get("gozlem_esas"))
        k2 = kriter2.degerlendir(atamalar, surec, kesit, params)
    return k1, k2


def kriterler(model, kesit, params, sonuc, durum):
    """Süre sonuçlarını sonuc'a yazar; süre puanı tablosunu (ya da None) döndürür."""
    params = etkin_parametreler(params, model)
    k1, k2 = _degerlendir(model, kesit, params)
    pencere, golge = params["sure_puani"]["pencere_ay"], sure_ozet.golge_kriterleri(params)
    araliklar = model.get("golge_araliklari") or {}
    haric = {kriter: [] if golge[kriter] else araliklar.get(kriter) or []
             for kriter in KRITERLER}
    kaynak = esas_kaynaklari(model)
    for kriter, ad, tablo in (("K1", "sonuc_k1", k1), ("K2", "sonuc_k2", k2)):  # Süre Takibi
        if tablo is not None:
            sonuc[ad] = tablo.assign(
                pencerede_dusum=sure_ozet.pencerede_dusum(tablo, kesit, pencere, haric[kriter]),
                dusum_durumu=sure_ozet.dusum_durumu(tablo, golge[kriter], haric[kriter]),
                esas_kaynagi=kaynak[kriter])
    if k1 is None and k2 is None:
        durum["sure"] = "KAYNAK_BEKLENIYOR"
        return None
    girdi = sure_girdisi(k1, k2)
    sonuc["sonuc_sure_ozet"] = sure_ozet.ozet(girdi, kesit, pencere, haric)
    sonuc["sonuc_eposta"] = sure_ozet.eposta_listesi(girdi, params)
    if k1 is None or k2 is None:  # süre puanı iki kriterin düşümlerinden birlikte oluşur
        durum["sure"] = "KAYNAK_BEKLENIYOR"
        return None
    kapsam = sure_puani.kapsam_hesapla(k1, kesit, pencere)
    sonuc["sonuc_sure"] = sure_puani.puanla(girdi, kapsam, kesit, params, haric)
    return sonuc["sonuc_sure"]
'''

DOSYALAR["kaynak.py"] = r'''"""Kaynak okuma: her mantıksal kaynak, kaynaklar.json'daki yöntemle okunur.

Yöntemler: bekliyor (bağlantı henüz yok), dataiku (Dataiku veri kümesi), api (hat.api ile
genel REST okuyucu), dosya (CSV; sentetik veri provası ve yerel çalışma). Okunan ham tablo
arşive olduğu gibi yazılır; normalle ise alan adlarını eşler (alan_eslemesi; sonra aynı adlı iki
sütun kalırsa hata), değerlendirme sisteminin geniş biçimini uzun biçime alır
(genis_degerlendirme; kaynakta olmayan eşleme sütunu puanlanmamış sayılır), kaynak değerlerini
sözleşme kodlarına çevirir (deger_eslemesi, ör. {"brans": {"Trafik": "TRAFIK"}}), metin
tarihleri verilen biçimle çevirir (tarih_bicimi, ör. "%d.%m.%Y"; biçime uymayan değer metin
kalır, kapı KALDI verir) ve metin sayıyı kaynağın biçimiyle çevirir (sayi_bicimi tr: 1.234,56;
en: 1,234.56).
API ayarında {kesit} ve {cekim_tarihi} yer tutucuları kullanılabilir (hat.okuma.baglam).
"""
import re

import pandas as pd

from avukat_perf import hazirlik, sema
from avukat_perf.kalite_tur import EN_KALIBI, TR_KALIBI
from hat import api
from hat.ayar import YONTEMLER

# Normalleştirmeyi belirleyen kaynak ayarları: arşivin bilgi.json'una yazılır (yeniden üretim).
NORMALLEME = ("alan_eslemesi", "genis_degerlendirme", "deger_eslemesi", "tarih_bicimi",
              "sayi_bicimi")


def _yer_tut(deger, baglam):
    if isinstance(deger, dict):
        return {anahtar: _yer_tut(alt, baglam) for anahtar, alt in deger.items()}
    if isinstance(deger, list):
        return [_yer_tut(alt, baglam) for alt in deger]
    if isinstance(deger, str):
        for anahtar, metin in baglam.items():
            deger = deger.replace("{" + anahtar + "}", metin)
    return deger


def cek(ayar, ortam, baglam):
    """Ham tablo; yöntem 'bekliyor' ise None."""
    yontem = ayar.get("yontem", "bekliyor")
    if yontem not in YONTEMLER:
        raise ValueError("bilinmeyen yöntem: {} ({})".format(yontem, ", ".join(YONTEMLER)))
    if yontem == "bekliyor":
        return None
    if yontem == "dataiku":
        return ortam.veri_kumesi_oku(ayar["dataiku"]["veri_kumesi"])
    if yontem == "api":
        return api.oku(_yer_tut(ayar["api"], baglam), ortam.gizli)
    dosya = ayar["dosya"]
    return pd.read_csv(ortam.dosya_yolu(dosya["yol"]), dtype=str, sep=dosya.get("ayirici", ","),
                       encoding=dosya.get("kodlama", "utf-8"), keep_default_na=False,
                       na_values=[""])


def _sayi(seri, bicim):
    """Metin sayıyı kaynağın biçimiyle çevirir (tr '1.234,56', en '1,234.56' -> 1234.56); yalnız
    kalıba uyan metin çevrilir. Sayı olarak gelen değer (API, Dataiku double) ve kalıba uymayan
    metin olduğu gibi kapıya gider; nokta silinerek 10-100 kat büyütülmez."""
    kalip, binlik, ondalik = (TR_KALIBI, ".", ",") if bicim == "tr" else (EN_KALIBI, ",", ".")

    def cevir(deger):
        if isinstance(deger, str) and re.match(kalip, deger):
            return float(deger.strip().replace(binlik, "").replace(ondalik, "."))
        return deger
    return seri.map(cevir)


def _tarih(seri, bicim):
    """Biçime uyan değer tarih olur; uymayan metin metin kalır ve kapının ISO denetimine gider
    (where datetime64'e zorlasaydı dateutil ay-gün sırasını tahmin ederdi)."""
    tarih = pd.to_datetime(seri, format=bicim, errors="coerce")
    uymayan = tarih.isna() & seri.notna()
    return tarih.astype(object).where(~uymayan, seri) if uymayan.any() else tarih


def _deger_esle(seri, harita):
    return seri.map(lambda deger: harita.get(deger.strip(), deger) if isinstance(deger, str)
                    else deger)


def normalle(ad, ham, ayar):
    """Ham tabloyu veri sözleşmesindeki alan adlarına ve biçimlere getirir.

    Kayıtsız yanıt (ör. API'den boş liste) sözleşme sütunlarıyla boş tablo olur; boşluğu kalite
    kapısı değerlendirir (zorunlu kaynakta KALDI, isteğe bağlıda UYARI).
    """
    if ham.empty and len(ham.columns) == 0:
        return pd.DataFrame(columns=sema.alanlar(ad))
    tablo = ham.rename(columns=ayar.get("alan_eslemesi") or {})
    cift = sorted(set(str(sutun) for sutun in tablo.columns[tablo.columns.duplicated()]))
    if cift:
        raise ValueError("{}: alan eşlemesinden sonra yinelenen sütun: {}".format(
            ad, ", ".join(cift)))
    genis = ayar.get("genis_degerlendirme")
    if genis:
        if not any(alan in tablo.columns for alan in genis):
            raise ValueError("{}: genis_degerlendirme sütunlarının hiçbiri yok".format(ad))
        tablo = hazirlik.degerlendirme_uzun(tablo.assign(**{
            alan: None for alan in genis if alan not in tablo.columns}), genis)
    for alan, harita in (ayar.get("deger_eslemesi") or {}).items():
        if alan in tablo.columns:
            tablo[alan] = _deger_esle(tablo[alan], harita)
    for alan, tur, _ in sema.KAYNAKLAR[ad]["alanlar"]:
        if alan not in tablo.columns:
            continue
        if tur == "sayi" and ayar.get("sayi_bicimi") in ("tr", "en"):
            tablo[alan] = _sayi(tablo[alan], ayar["sayi_bicimi"])
        if tur in ("tarih", "zaman") and ayar.get("tarih_bicimi"):
            tablo[alan] = _tarih(tablo[alan], ayar["tarih_bicimi"])
    return tablo
'''

DOSYALAR["model.py"] = r'''"""Model kurma: kalite kapısını geçmiş kaynak tablolarından hesap girdileri ve gözlemler.

Gözlemler kaynağa göre ayrı tablolardadır: dava takip esas görüntüsü (gozlem_esas), çekirdek
sistemin takip bilgileri (gozlem_esas_yedek; yedek yol), dava esası (gozlem_dava) ve Kriter 2
koşulunun kalktığı gün (gozlem_kosul). Yedek yoldan sabitlenmiş tarih dava takip sistemi
bağlanınca kullanılmaz: o sistemin gözlemi kendi ilk görüntüsünden kurulur. Esas yalnız yedek
yoldan geliyorsa golge_zorunlu True olur: Kriter 1 yalnız gölge modda çalışır. Gözlem tabanı
son başarılı çekimdir (boş görüntü kapıda durur); görüntüsü o gece gelmeyen gözlem None olur.
Haklı bekleme kaynağı daha önce okunmuşken o gece gelmezse bekleme_eksik True olur (Kriter 1
hesaplanmaz). Yazım hesaptan sonradır; sonuc_ ve model_ tabloları çalışma kimliğiyle
etiketlenir, gecenin kaydına her tablonun satır sayısı yazılır. Okuyanlar yalnız son başarılı
gecenin tablosunu, o gecenin yazdığı satır sayısıyla kullanır.
"""
from avukat_perf import gozlem, hazirlik
from hat import butunluk, gecmis, hesap_sure

TABLOLAR = ("dosya", "atama_donemi", "hareket", "bekleme", "degerlendirme", "avukat",
            "k2_goruntu")
GOZLEMLER = ("gozlem_esas", "gozlem_esas_yedek", "gozlem_dava", "gozlem_kosul")


def _gozlem_tanimlari(tablolar, params):
    takip = tablolar.get("takip")
    # Takip bilgisinde dosya başına birden çok satır olabilir (açık karar): gözleme esası dolu
    # satırlar içinde işlem tarihi en erken olan girer (gozlem.guncelle ilk dolu satırı alır).
    yedek = None if takip is None else takip.sort_values(
        "islem_tarihi", na_position="last", kind="mergesort").rename(
        columns={"islem_tarihi": "kaynak_tarihi"})
    kosul = hazirlik.kosul_goruntusu(tablolar["dosya"], params["kriter2"])
    return [("gozlem_esas", tablolar.get("esas_goruntu"), "esas_goruntu", "esas_no",
             "kaynak_tarihi"),
            ("gozlem_esas_yedek", yedek, "takip", "esas_no", "kaynak_tarihi"),
            ("gozlem_dava", tablolar.get("k2_goruntu"), "k2_goruntu", "dava_esas_no",
             "dava_kaynak_tarihi"),
            ("gozlem_kosul", kosul, "dosya", "kosul_kayip", None)]


def kur(ortam, tablolar, params, cekim, onceki_kayit, simdi):
    """Model sözlüğü; gözlem tablolarını günceller (yazmaz, bkz. yaz). simdi: bu çalışmanın
    başlangıcı; gözlem tabanı ondan önce başlamış son başarılı çekimdir (aynı gün dahil)."""
    hz = params["hazirlik"]
    model = {"dosya": tablolar["dosya"], "k2_goruntu": tablolar.get("k2_goruntu"),
             "atama_donemi": hazirlik.atama_donemleri(tablolar["atama_log"], hz),
             "hareket": None if tablolar.get("tahsilat_hareketi") is None else
             hazirlik.tahsilat_hareketleri(tablolar["tahsilat_hareketi"], hz),
             "bekleme": tablolar.get("bekleme"), "avukat": tablolar.get("avukat"),
             "degerlendirme": tablolar.get("degerlendirme"),
             "golge_zorunlu": tablolar.get("esas_goruntu") is None and
             tablolar.get("takip") is not None,
             "bekleme_eksik": tablolar.get("bekleme") is None and
             gecmis.son_basarili(onceki_kayit, "bekleme", simdi)[0] is not None,
             "golge_araliklari": hesap_sure.golge_araliklari(onceki_kayit)}
    tanimlar = _gozlem_tanimlari(tablolar, params)
    mevcut = {ad: ortam.tablo_oku(ad) for ad, goruntu, _, _, _ in tanimlar if goruntu is not None}
    butunluk.veri_kaybi(onceki_kayit, mevcut)
    for ad, goruntu, kaynak_adi, deger, kaynak_tarihi in tanimlar:
        if goruntu is None:
            model[ad] = None
            continue
        onceki_tarih, _ = gecmis.son_basarili(onceki_kayit, kaynak_adi, simdi)
        model[ad] = gozlem.guncelle(mevcut[ad], goruntu, "dosya_no", deger, cekim,
                                    onceki_tarih, kaynak_tarihi)
    return model


def yaz(ortam, model, sonuc, kimlik):
    """Sonuç, model ve gözlem tablolarını yazar; {tablo: satır sayısı} döndürür (uretilen).

    sonuc_ ve model_ tablolarına calisma_kimligi sütunu eklenir.
    """
    yazilacak = dict(sonuc)
    yazilacak.update({"model_" + ad: model[ad] for ad in TABLOLAR if model.get(ad) is not None})
    yazilacak.update({ad: model[ad] for ad in GOZLEMLER if model.get(ad) is not None})
    etiketli = sorted(ad for ad in yazilacak if ad.startswith(("sonuc_", "model_")))
    for ad in etiketli:
        ortam.tablo_yaz(ad, yazilacak[ad].assign(calisma_kimligi=kimlik))
    for ad in sorted(set(yazilacak) - set(etiketli)):  # gözlemler ve olay tabloları en son
        ortam.tablo_yaz(ad, yazilacak[ad])
    return {ad: len(tablo) for ad, tablo in yazilacak.items()}


def etiket_uygun(tablo, kimlik, sayi=None):
    """Tablo bu gecenin yazdığı tablo mu: etiketi bu kimlik ve satır sayısı kayıttakiyle aynı.

    sayi: gecenin kaydına yazılan satır sayısı (eski kayıtta None). Boş tablo yalnız o gece
    sıfır satır yazıldıysa uygundur; yarım yazılmış tablo satır sayısından ayırt edilir.
    """
    if tablo is None:
        return True
    if sayi is not None and len(tablo) != sayi:
        return False
    if "calisma_kimligi" not in tablo.columns or tablo.empty:
        return True
    return set(tablo["calisma_kimligi"].astype(str)) == {str(kimlik)}


def oku(ortam, onceki_kayit):
    """Dönem sonu için son başarılı gecenin model ve gözlem tabloları.

    O gece yazılmamış (bayat) ya da başka bir gecenin etiketini taşıyan tablo None sayılır:
    ör. dava takip bağlantısı kaldırıldıktan sonra eski süreç görüntüsüyle Kriter 2
    yayımlanmaz, yarıda kesilmiş bir gecenin yazdığı tablo kullanılmaz.
    """
    uretilen, kimlik = gecmis.son_sayilar(onceki_kayit), gecmis.son_kimlik(onceki_kayit)

    def _oku(ad):
        if ad not in uretilen:  # hiç başarılı gece yok ya da bayat
            return None
        tablo = ortam.tablo_oku(ad)
        if tablo is None or not etiket_uygun(tablo, kimlik, uretilen[ad]):
            return None
        return tablo.drop(columns="calisma_kimligi", errors="ignore")
    model = {ad: _oku("model_" + ad) for ad in TABLOLAR}
    model.update({ad: _oku(ad) for ad in GOZLEMLER})
    model["golge_zorunlu"] = gecmis.son_golge_zorunlu(onceki_kayit)
    model["bekleme_eksik"] = model["bekleme"] is None and gecmis.son_basarili(
        onceki_kayit, "bekleme", "2200-01-01")[0] is not None
    model["golge_araliklari"] = hesap_sure.golge_araliklari(onceki_kayit)
    return model
'''

DOSYALAR["okuma.py"] = r'''"""Kaynak okuma ve kalite kapısı: her kaynağı oku → ham arşiv → normalle → denetle.

Okuma, arşiv ya da biçim hatası o kaynağı KALDI yapar; hata türü ve iletisi çalışma kaydına
ve kalite sonucuna yazılır (ileti satır değeri içermez). Kaynaklar arası ilişki denetimi
gelen bütün kaynakların anahtarlarını (dosya ve avukat) ana kaynakla karşılaştırır; hiçbir
anahtar eşleşmiyorsa (biçim farkı, ör. D-000001 / D000001) ya da eşleşmeyen oranı
kalite.iliski_en_cok_yetim_orani'nı aşıyorsa (tahsilat hareketinde tutarla da tartılır) gece
durur. Haklı bekleme (dosya, avukat) çifti ve avukat listesi yalnız tümden uyuşmazlıkta durur.
"""
import pandas as pd

from avukat_perf import hazirlik, kalite, kalite_iliski, sema
from hat import arsiv, ayar as ayar_modulu, calisma, gecmis, kaynak


def kaynaklari_oku(ortam, ayarlar, params, cekim, onceki, kimlik, simdi):
    """(kapıyı geçen tablolar, kaynak başına kayıt satırları, kalite sonuçları)."""
    tablolar, kayitlar, sonuclar = {}, [], []
    for ad in sema.KAYNAKLAR:
        ayar = ayar_modulu.kaynak_ayari(ayarlar, ad)  # sistem ayarı + kaynak ayarı
        _, onceki_satir = gecmis.son_basarili(onceki, ad, simdi)
        kayit = calisma.satir(kimlik, "GECELIK", ad, ayar.get("yontem", "bekliyor"), simdi,
                              cekim)
        try:
            ham = kaynak.cek(ayar, ortam, baglam(cekim))
            if ham is None:
                kayitlar.append(dict(kayit, durum="KAYNAK_BEKLENIYOR"))
                continue
            bilgi = dict({alan: ayar.get(alan) for alan in kaynak.NORMALLEME},
                         yontem=ayar["yontem"])
            yol = arsiv.yaz(ortam, ad, ham, cekim.date(), kimlik, bilgi)
            normal = kaynak.normalle(ad, ham, ayar)
            temiz, sonuc = kalite.denetle(ad, normal, cekim, params, onceki_satir)
        except Exception as hata:  # bağlantı, yetki, arşiv ya da biçim: kayda geçer, gece durur
            metin = ileti(hata)
            kayitlar.append(dict(kayit, durum="KALDI", kalite_sonucu="KALDI", aciklama=metin))
            sonuclar.append(kalite.cekim_hatasi(ad, metin).assign(calisma_kimligi=kimlik))
            continue
        sonuclar.append(sonuc.assign(calisma_kimligi=kimlik))
        tablolar[ad] = temiz
        # Kapı normalleştirilmiş satırı sayar (geniş değerlendirme uzun biçime açılır).
        kayitlar.append(dict(kayit, satir_sayisi=len(normal), kalite_sonucu=kalite.karar(sonuc),
                             arsiv_yolu=yol))
    return tablolar, kayitlar, sonuclar


def ileti(hata):
    return "{}: {}".format(type(hata).__name__, hata)[:300]


def baglam(cekim):
    """API ayarındaki yer tutucular. Her kaynak her gece tam görüntü verir (artımlı çekim ilk
    görülme gününü bozardı); bu yüzden önceki çekimin tarihi sunulmaz."""
    return {"kesit": str(cekim.date()), "cekim_tarihi": str(cekim.date())}


# (kontrol, alt kaynak, ana kaynak, anahtar, oran sınırı uygulanır mı): alt kaynağın anahtarları
# ana kaynakta olmalı.
ILISKILER = (("ATAMA_DOSYA", "atama_log", "dosya", "dosya_no", True),
             ("HAREKET_DOSYA", "tahsilat_hareketi", "dosya", "dosya_no", True),
             ("ESAS_DOSYA", "esas_goruntu", "dosya", "dosya_no", True),
             ("TAKIP_DOSYA", "takip", "dosya", "dosya_no", True),
             ("SUREC_DOSYA", "k2_goruntu", "dosya", "dosya_no", True),
             ("BEKLEME_DOSYA", "bekleme", "dosya", "dosya_no", True),
             ("BEKLEME_AVUKAT", "bekleme", "atama_log", "avukat_kodu", True),
             ("BEKLEME_ATAMA", "bekleme", "atama_log", ("dosya_no", "avukat_kodu"), False),
             ("DEGERLENDIRME_AVUKAT", "degerlendirme", "atama_log", "avukat_kodu", True),
             ("AVUKAT_AVUKAT", "avukat", "atama_log", "avukat_kodu", False))


def iliskiler(tablolar, params, kesit=None):
    """Kaynaklar arası anahtar eşleşmesi (gelen isteğe bağlı kaynaklar dahil) ve mutabakat.

    Mutabakat puana giren hareketlerle yapılır (tahsilat sayılan hareket türleri); kesitin
    ayındaki fark uyarıdır (rapor ve hareketler farklı saatte yenilenebilir)."""
    oran = params["kalite"]["iliski_en_cok_yetim_orani"]
    sonuclar = [kalite_iliski.iliski(kontrol, tablolar[ana], tablolar[alt], anahtar,
                                     oran if oranli else None,
                                     "tutar" if alt == "tahsilat_hareketi" else None)
                for kontrol, alt, ana, anahtar, oranli in ILISKILER
                if tablolar.get(alt) is not None]
    if tablolar.get("rapor_avukat_toplam") is None:
        return sonuclar
    if tablolar.get("tahsilat_hareketi") is None:  # dosya bazında hareket yok: mutabakat yok
        return sonuclar + [pd.DataFrame([kalite.satir(
            "mutabakat", "TAHSILAT_HAREKETI_YOK", 1, uyari=True,
            aciklama="dosya bazında tahsilat hareketi gelmedi; rapor toplamıyla mutabakat "
                     "yapılmadı, Tahsilat sütunu kaynak bekliyor")], columns=kalite.SONUC)]
    hareket = hazirlik.tahsilat_hareketleri(tablolar["tahsilat_hareketi"], params["hazirlik"])
    sonuclar.append(kalite_iliski.mutabakat(hareket, tablolar["rapor_avukat_toplam"], params,
                                            kesit))
    return sonuclar
'''

DOSYALAR["ortam.py"] = r'''"""Yerel ortam: tablolar CSV, ham arşiv klasör, gizli değerler sözlük ya da ortam değişkeni.

Testler, sentetik veri provası ve arayüz önizlemesi için. Dataiku'da aynı arayüzü
hat.dataiku_ortam.DataikuOrtam sağlar: tablo_oku, tablo_yaz, veri_kumesi_oku, dosya_yolu,
gizli, arsiv_var, arsiv_yaz, ayar_oku, ayar_oku_varsa. CSV türleri kaybetmesin diye her
tablonun yanında sütun türleri (tarih, sayi, mantiksal, metin) ayrı bir dosyada tutulur. Ayar
dosyaları json_oku ile okunur (iki ortamda aynı): yinelenen anahtar hatadır.
"""
import json
import os

import pandas as pd

from hat.veri_kumeleri import AYAR_KLASORU


def json_oku(metin, ad):
    """JSON ayar metni; aynı düzeyde yinelenen anahtar hatadır. json.loads son değeri alırdı: ek
    dosyada iki kez yazılan bölümün ilk bloğu (ör. teyit edilen ölçek) sessizce kaybolurdu."""
    def tekil(ciftler):
        anahtarlar = [anahtar for anahtar, _ in ciftler]
        cift = sorted(set(a for a in anahtarlar if anahtarlar.count(a) > 1))
        if cift:
            raise ValueError("{}: yinelenen anahtar {}".format(ad, ", ".join(cift)))
        return dict(ciftler)
    return json.loads(metin, object_pairs_hook=tekil)


def _tur(seri):
    if str(seri.dtype).startswith("datetime"):
        return "tarih"
    if str(seri.dtype) == "bool":
        return "mantiksal"
    return "sayi" if pd.api.types.is_numeric_dtype(seri) else "metin"


class YerelOrtam(object):
    """kok klasörü altında tablolar/, ham/, ayarlar/ ve kaynak dosyaları."""

    def __init__(self, kok, gizliler=None, kaynak_kok=None, ayar_kok=None):
        self.kok = kok
        self._gizliler = gizliler or {}
        self._kaynak_kok = kaynak_kok or kok
        self._ayar_kok = ayar_kok or os.path.join(kok, AYAR_KLASORU)

    def _yol(self, *parcalar):
        return os.path.join(self.kok, *parcalar)

    def tablo_oku(self, ad):
        yol = self._yol("tablolar", ad + ".csv")
        if not os.path.exists(yol):
            return None
        with open(self._yol("tablolar", ad + ".turler.json"), encoding="utf-8") as dosya:
            turler = json.load(dosya)
        tablo = pd.read_csv(yol, dtype=str, keep_default_na=False, na_values=[""])
        for sutun, tur in turler.items():
            if tur == "tarih":
                tablo[sutun] = pd.to_datetime(tablo[sutun])
            elif tur == "sayi":
                tablo[sutun] = pd.to_numeric(tablo[sutun])
            elif tur == "mantiksal":
                tablo[sutun] = tablo[sutun].map({"True": True, "False": False})
        return tablo

    def tablo_yaz(self, ad, tablo):
        os.makedirs(self._yol("tablolar"), exist_ok=True)
        tablo.to_csv(self._yol("tablolar", ad + ".csv"), index=False)
        turler = {str(sutun): _tur(tablo[sutun]) for sutun in tablo.columns}
        with open(self._yol("tablolar", ad + ".turler.json"), "w", encoding="utf-8") as dosya:
            json.dump(turler, dosya, ensure_ascii=False)

    def veri_kumesi_oku(self, ad):
        return pd.read_csv(self._yol("veri_kumeleri", ad + ".csv"), dtype=str,
                           keep_default_na=False, na_values=[""])

    def dosya_yolu(self, yol):
        return yol if os.path.isabs(yol) else os.path.join(self._kaynak_kok, yol)

    def gizli(self, ad):
        if ad in self._gizliler:
            return self._gizliler[ad]
        if ad in os.environ:
            return os.environ[ad]
        raise KeyError("gizli değer bulunamadı: " + ad)

    def arsiv_var(self, yol):
        return os.path.exists(self._yol(yol))

    def arsiv_yaz(self, yol, bayt):
        hedef = self._yol(yol)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        with open(hedef, "wb") as dosya:
            dosya.write(bayt)

    def ayar_oku(self, ad):
        with open(os.path.join(self._ayar_kok, ad), encoding="utf-8-sig") as dosya:
            return json_oku(dosya.read(), ad)

    def ayar_oku_varsa(self, ad):
        yol = os.path.join(self._ayar_kok, ad)
        return self.ayar_oku(ad) if os.path.exists(yol) else None
'''

DOSYALAR["veri_kumeleri.py"] = r'''"""Dataiku'da önceden oluşturulacak veri kümeleri ve yönetilen klasörler.

Kurulum not defteri (dataiku/kontrol/kurulum.py) bu adları oluşturur. Hattın yazdığı
tabloların bu listeyle aynı olduğu testle denetlenir; ad değişirse liste de değişir.
Kaynak veri kümeleri (kaynak_*) kaynaklar.json'dan okunur, yalnız yöntemi "dataiku" olan
kaynaklar için gerekir.
"""
from avukat_perf.sema import KAYNAKLAR
from hat.ayar import kaynak_ayari

KAYIT = ("calisma_kaydi", "kalite_sonucu")
GOZLEM = ("gozlem_esas", "gozlem_esas_yedek", "gozlem_dava", "gozlem_kosul")
MODEL = ("model_dosya", "model_atama_donemi", "model_hareket", "model_bekleme",
         "model_degerlendirme", "model_avukat", "model_k2_goruntu")
SONUC = ("sonuc_tahsilat_avukat", "sonuc_tahsilat_grup", "sonuc_tahsilat_brans",
         "sonuc_portfoy",
         "sonuc_tahsilat_aylik", "sonuc_tahsilat_yillik", "sonuc_mevcut_degerlendirme",
         "sonuc_k1", "sonuc_k2", "sonuc_sure", "sonuc_sure_ozet", "sonuc_eposta",
         "sonuc_kalite_davranis_sutun", "sonuc_kalite_davranis_alt",
         "sonuc_puan_guncel", "sonuc_birlesik", "sonuc_aciklama")
OLAY = ("bayrak_olay", "olay_celiski")
DONEM = ("puan_donem", "birlesik_donem")
CIKTI = KAYIT + GOZLEM + MODEL + SONUC + OLAY + DONEM
KONTROL = ("kontrol_tablo", "kontrol_tablo_sql")  # aktarım kontrolünün gidiş-dönüş tabloları
KONTROL_SQL = "kontrol_tablo_sql"  # izleme tablolarıyla aynı (SQL) bağlantıda kurulur
AYAR_KLASORU = "ayarlar"  # params.json, kaynaklar.json ve ek dosyaları
ARSIV_KLASORU = "ham_arsiv"  # S3 (MinIO) bağlantılı ham arşiv
KLASORLER = (AYAR_KLASORU, ARSIV_KLASORU)
DOSYA_KLASORU = "kaynak_dosyalari"  # yalnız yöntemi "dosya" olan kaynak varsa gerekir
IZLEME = KAYIT  # Grafana okur; SQL bağlantısında tutulur


def kaynak_veri_kumeleri(ayarlar):
    """kaynaklar.json içinde yöntemi "dataiku" olan kaynakların veri kümesi adları."""
    secili = [kaynak_ayari(ayarlar, ad) for ad in KAYNAKLAR]
    return sorted(ayar["dataiku"]["veri_kumesi"] for ayar in secili
                  if ayar.get("yontem") == "dataiku")
'''

OZET = {
    "__init__.py": "d4fd90e280a6",
    "akis.py": "0d6a3d8fc505",
    "api.py": "5b15be3b72a1",
    "api_kimlik.py": "7cd3bceebfea",
    "api_yanit.py": "baac1979483c",
    "arsiv.py": "03865353bbda",
    "ayar.py": "48f88cacf385",
    "ayar_alan.py": "db65c0c6dca5",
    "butunluk.py": "6a59e620003d",
    "calisma.py": "811fd54f0fdd",
    "dataiku_ortam.py": "6d1b0b8e7368",
    "donem_akisi.py": "7cb17e85f5a3",
    "donem_kayit.py": "f6cf157e5f9a",
    "gecmis.py": "96c1f1a152c6",
    "hesap.py": "9f047f3e542b",
    "hesap_sure.py": "366bf1772ca1",
    "kaynak.py": "abbd61ac1af4",
    "model.py": "e05925193dc5",
    "okuma.py": "59dcf1b4ad0f",
    "ortam.py": "14517254f53d",
    "veri_kumeleri.py": "998fd2500315",
}


# ---------- kütüphaneye yazma ----------
def _ozet(metin):
    satirlar = [satir.rstrip() for satir in metin.splitlines()]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return hashlib.sha256("\n".join(satirlar).encode("utf-8")).hexdigest()[:12]


def _cocuk(klasor, ad):
    if hasattr(klasor, "get_child"):
        return klasor.get_child(ad)
    return next((oge for oge in klasor.list() if oge.name == ad), None)


def _python_klasoru(kutuphane):
    for yol in ("/python", "python"):
        try:
            klasor = kutuphane.get_folder(yol)
        except Exception:  # sürüme göre yol biçimi değişir
            klasor = None
        if klasor is not None:
            return klasor
    raise SystemExit("Kütüphanede python klasörü bulunamadı; kurulum rehberindeki elle yapıştırma "
                     "yolunu izleyin.")


def kur():
    proje = dataiku.api_client().get_default_project()
    if not hasattr(proje, "get_library"):
        raise SystemExit("Bu Dataiku sürümünde kütüphane API'si yok; kurulum rehberindeki Git "
                         "ya da elle yapıştırma yolunu izleyin.")
    python = _python_klasoru(proje.get_library())
    klasor = _cocuk(python, PAKET) or python.add_folder(PAKET)
    hatali = []
    for ad in sorted(DOSYALAR):
        dosya = _cocuk(klasor, ad) or klasor.add_file(ad)
        dosya.write(DOSYALAR[ad])
        okunan = dosya.read()
        okunan = okunan.decode("utf-8") if isinstance(okunan, bytes) else okunan
        print("{}/{} {}".format(PAKET, ad, _ozet(okunan)))
        if _ozet(okunan) != OZET[ad]:
            hatali.append(ad)
    if hatali:
        raise SystemExit("Geri okunan içerik farklı: " + ", ".join(hatali))
    print("{}: {} dosya yazıldı ve doğrulandı. Not defterinin çekirdeğini yeniden başlatın."
          .format(PAKET, len(DOSYALAR)))


kur()
