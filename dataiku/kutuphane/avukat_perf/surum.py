"""Hesap sürümü: bir sonucun hangi kod ve parametreyle üretildiğini gösterir.

hesap_surumu = kitaplık sürümü + kod özeti + parametre özeti. Kod özeti sonucu belirleyen
dosyalardan (avukat_perf paketi ve KOD_DOSYALARI'ndaki hat modülleri) çalışma anında üretilir;
hat'ın geri kalanı (HAT_GIRIS_CIKIS) yalnız okur, yazar ya da durdurur. Satır sonu ve satır
sonundaki boşluk farkı özeti değiştirmez (kopyala-yapıştır aktarımı). "_" ile başlayan
parametre anahtarları açıklamadır; gorunum bölümü yalnız ekran adlarını, kalite bölümü yalnız
kalite kapısının eşiklerini tutar (hiçbir puana girmez); üçü de sürümü etkilemez.
hazirlik_surumu, gecelik model tablolarını belirleyen kod ve parametrelerin özetidir: dönem
sonu, son geceden sonra değişen hazırlık kuralıyla yayın yapmaz.
"""
import hashlib
import json
import os

from avukat_perf import SURUM
from avukat_perf.params_sema import GORUNUM

KOD_DOSYALARI = (("avukat_perf", None), ("hat", ("akis.py", "donem_akisi.py", "gecmis.py",
                                                  "hesap.py", "hesap_sure.py", "kaynak.py",
                                                  "model.py", "okuma.py")))
HAT_GIRIS_CIKIS = ("__init__.py", "api.py", "api_kimlik.py", "api_yanit.py", "arsiv.py",
                   "ayar.py", "ayar_alan.py", "butunluk.py", "calisma.py", "dataiku_ortam.py",
                   "donem_kayit.py", "ortam.py", "veri_kumeleri.py")
SURUM_DISI = (GORUNUM, "kalite")
_ONBELLEK = {}


def metin_ozeti(metin):
    """Satır sonu ve sondaki boşluktan bağımsız kısa özet (aktarım özetiyle aynı kural)."""
    satirlar = [satir.rstrip() for satir in metin.splitlines()]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return hashlib.sha256("\n".join(satirlar).encode("utf-8")).hexdigest()[:12]


def json_ozeti(deger):
    """Ayar dosyasının (params.json, kaynaklar.json) içerik özeti: anahtar sırası, girinti ve BOM
    etkilemez; açıklamalar ve ekran adları dahil her değer etkiler (aktarım özeti)."""
    return metin_ozeti(json.dumps(deger, sort_keys=True, ensure_ascii=False))


def kod_ozeti():
    """Hesabı belirleyen kitaplık dosyalarının birleşik özeti (süreç boyunca bir kez okunur)."""
    if "kod" not in _ONBELLEK:
        kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parcalar = []
        for paket, adlar in KOD_DOSYALARI:
            klasor = os.path.join(kok, paket)
            for ad in sorted(adlar or os.listdir(klasor)):
                if ad.endswith(".py"):
                    with open(os.path.join(klasor, ad), encoding="utf-8") as dosya:
                        parcalar.append("{}/{} {}".format(paket, ad, metin_ozeti(dosya.read())))
        _ONBELLEK["kod"] = metin_ozeti("\n".join(parcalar))[:8]
    return _ONBELLEK["kod"]


def _aciklamasiz(deger):
    if isinstance(deger, dict):
        return {a: _aciklamasiz(d) for a, d in deger.items() if not a.startswith("_")}
    if isinstance(deger, list):
        return [_aciklamasiz(d) for d in deger]
    return deger


def _ozet(deger):
    metin = json.dumps(_aciklamasiz(deger), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()[:12]


def kural_surumu(params):
    """Parametre içeriğinin kısa özeti. Anahtar sırası, açıklamalar, ekran adları ve kalite
    kapısı eşikleri etkilemez."""
    return _ozet({bolum: deger for bolum, deger in params.items() if bolum not in SURUM_DISI})


def hesap_surumu(params):
    """Sonuç tablolarına yazılan sürüm: kitaplık sürümü + kod özeti + parametre özeti."""
    return "{}+{}+{}".format(SURUM, kod_ozeti(), kural_surumu(params))


def hazirlik_surumu(params):
    """Gecelik model tablolarını (atama dönemi, tahsilat hareketi, koşul gözlemi) belirleyen kod
    ve parametrelerin özeti; koşul gözlemi rücu kodu ve kapanış kodlarından kurulur."""
    k2 = params["kriter2"]
    return kod_ozeti() + "+" + _ozet({"hazirlik": params["hazirlik"], "rucu_kodu": k2["rucu_kodu"],
                                      "kapanis_kodlari": k2["kapanis_kodlari"]})
