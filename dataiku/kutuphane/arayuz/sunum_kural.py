"""Puanlama Kuralları (parametrelerden) ve Veri Durumu (çalışma kaydı, kalite, çelişki).

Kurallar sayfası params.json'dan üretilir; ekranda elle yazılmış eşik yoktur. Teyit bekleyen
değerler params.json'daki _teyit_bekleyen listesinden ve null değerlerden işaretlenir.
Parametre geçersizse (gecenin reddedeceği dosya) önce hata listesi gelir; ağırlık ve not
kartları hesaplanmaz. Veri Durumu son gecelik çalışmayı, son çalışmaları, son gecelik ve son
dönem sonu çalışmasının geçmeyen kalite denetimlerini ve geriye dönük değişiklik nedeniyle
çelişen olayları (en yeni CELISKI_EN_COK; toplamıyla) gösterir. Ortak şerit sunum_ortak.py'de.
"""
import pandas as pd

from avukat_perf import agirlik
from avukat_perf.params_sema import GORUNUM, SUTUNLAR
from avukat_perf.sema import KAYNAKLAR
from arayuz.temel import kayitlar, tek
from hat import gecmis
from hat.calisma import OZET

CELISKI_EN_COK = 200
# Çelişkinin kalıcı anahtarı: aynı girdi satır sırasından bağımsız aynı satırları verir.
CELISKI_SIRASI = ["tespit_tarihi", "olay_tarihi", "kriter", "dosya_no", "avukat_kodu",
                  "atama_tarihi", "seviye", "olay_tarihi_yeni"]

def _metin(deger):
    """Parametre değerinin ekran metni: Evet/Hayır, Tanımsız, Türkçe ondalık, düz liste."""
    if deger is None:
        return "Tanımsız"
    if isinstance(deger, bool):
        return "Evet" if deger else "Hayır"
    if isinstance(deger, float):
        return repr(deger).replace(".", ",")
    if isinstance(deger, list):
        return ", ".join(_metin(oge) for oge in deger) if deger else "Boş liste"
    if isinstance(deger, dict):
        return "; ".join("{}: {}".format(ad, _metin(oge)) for ad, oge in deger.items())
    return str(deger)


def kurallar(params, hatalar=()):
    parametre, aciklama, teyit = [], [], set(params.get("_teyit_bekleyen", []))
    sonuc = {"kurallar.hatalar": [tek("kurallar.hatalar", {"hata": h})[0] for h in hatalar]}
    for bolum, alanlar in params.items():
        if bolum.startswith("_") or not isinstance(alanlar, dict) or bolum == GORUNUM:
            continue
        if alanlar.get("_not") and bolum != "agirliklar":  # ağırlık kartında gösterilir
            aciklama.append({"bolum": bolum, "aciklama": alanlar["_not"]})
        for ad, deger in alanlar.items():
            if not ad.startswith("_"):
                anahtar = bolum + "." + ad
                parametre.append({"bolum": bolum, "ad": ad, "deger": _metin(deger),
                                  "teyit_bekliyor": anahtar in teyit or bolum in teyit
                                  or deger is None})
    sonuc["kurallar.parametreler"] = [tek("kurallar.parametreler", s)[0] for s in parametre]
    sonuc["kurallar.aciklamalar"] = [tek("kurallar.aciklamalar", s)[0] for s in aciklama]
    if hatalar:  # ağırlık hesabı tutarsız karşılaştırmada hata verirdi; önce dosya düzeltilir
        return sonuc
    agirliklar = agirlik.sutun_agirliklari(params)
    sonuc["kurallar.agirliklar"] = [tek("kurallar.agirliklar", {
        "sutun": ad, "agirlik": agirliklar[ad], "teyit_bekliyor": "agirliklar" in teyit,
        "aciklama": params["agirliklar"].get("_not")})[0] for ad in SUTUNLAR]
    sonuc["kurallar.notlar"] = [tek("kurallar.notlar", {
        "not_adi": ad, "esik": esik, "teyit_bekliyor": "notlar" in teyit,
        "aciklama": params.get("_notlar_aciklama")})[0] for ad, esik in params["notlar"]]
    return sonuc


def _son_kimlikler(kayit, kalite):
    """Kalite satırı olan son gecelik ve son dönem sonu çalışması (başlangıç anına göre; kimlik
    metninin sonundaki rastgele ek sırayı belirlemez); çalışma kaydı yoksa en büyük kimlik."""
    kimlik = kalite["calisma_kimligi"].astype(str)
    ozet = None if kayit is None else kayit[(kayit["kaynak"] == OZET) & kayit[
        "calisma_kimligi"].astype(str).isin(set(kimlik))]
    if ozet is None or ozet.empty:
        return [kimlik.max()]
    ozet = ozet.assign(_bas=pd.to_datetime(ozet["baslangic"])).sort_values("_bas")
    return [str(ozet.loc[ozet["tur"] == t, "calisma_kimligi"].iloc[-1])
            for t in ("GECELIK", "DONEM_SONU") if (ozet["tur"] == t).any()]


def veri(tablolar):
    kayit, sonuc = tablolar.get("calisma_kaydi"), {}
    if kayit is not None and not kayit.empty:
        gece = kayit[kayit["tur"] == "GECELIK"]
        ozet = kayit[kayit["kaynak"] == OZET].sort_values("baslangic", ascending=False)
        if not gece.empty:
            son_kimlik = gece.sort_values("baslangic")["calisma_kimligi"].iloc[-1]
            son = gece[(gece["calisma_kimligi"] == son_kimlik) & (gece["kaynak"] != OZET)]
            son = son.assign(son_basarili=[gecmis.son_basarili(kayit, ad, "2200-01-01")[0]
                                           for ad in son["kaynak"]],
                             sistem=[KAYNAKLAR.get(ad, {}).get("sistem") for ad in son["kaynak"]])
            sonuc["veri.kaynaklar"] = kayitlar("veri.kaynaklar", son)
        sonuc["veri.calismalar"] = kayitlar("veri.calismalar", ozet.head(15))
    kalite = tablolar.get("kalite_sonucu")
    if kalite is not None and not kalite.empty:
        # Son gecelik ve son dönem sonu çalışması (kimlik başlangıç zamanıyla; çekim tarihi değil).
        son_kalite = kalite[kalite["calisma_kimligi"].isin(_son_kimlikler(kayit, kalite))]
        sonuc["veri.kalite"] = kayitlar("veri.kalite", son_kalite[son_kalite["durum"] != "GECTI"])
    celiski = tablolar.get("olay_celiski")
    sonuc["veri.celiski_ozet"] = tek("veri.celiski_ozet", {})
    if celiski is not None:
        sira = [ad for ad in CELISKI_SIRASI if ad in celiski.columns]
        secilen = celiski.sort_values(sira, ascending=[ad in CELISKI_SIRASI[2:] for ad in sira],
                                      kind="mergesort").head(CELISKI_EN_COK)
        sonuc["veri.celiski"] = kayitlar("veri.celiski", secilen)
        sonuc["veri.celiski_ozet"] = tek("veri.celiski_ozet", {"toplam": len(celiski),
                                                        "gosterilen": len(secilen)})
    return sonuc
