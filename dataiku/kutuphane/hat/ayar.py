"""Ayar dosyaları: yükleme, ek dosyayla birleştirme, kaynak ayarının kurulması ve doğrulama.

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
