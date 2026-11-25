"""Parametre bölümlerinin içerik kuralları (tür, kalite/davranış, not, adlar, diğer).

Tahsilat bölümünün kuralları (aylık pencere dahil) params_tahsilat.py'de, kalite kapısı, veri
hazırlığı ve branş kodlarının tutarlılığı params_veri.py'dedir.
"""
from avukat_perf.params_sema import KALITE_DAVRANIS_SUTUNLARI
from avukat_perf.params_veri import veri_hatalari
from avukat_perf.sema import SISTEMLER


def tur_uygun(deger, tur):
    """Değer şemadaki türe uyuyor mu. bool sayı sayılmaz; null yalnız *_veya_bos'ta; demet tür
    seçenek listesidir."""
    if isinstance(tur, tuple):
        return deger in tur
    if isinstance(deger, bool) or tur == "mantiksal":
        return isinstance(deger, bool) and tur == "mantiksal"
    if deger is None:
        return tur in ("liste_veya_bos", "metin_veya_bos")
    if tur == "tam":
        return isinstance(deger, int)
    if tur == "sayi":
        return isinstance(deger, (int, float))
    if tur in ("metin", "metin_veya_bos"):
        return isinstance(deger, str)
    return isinstance(deger, dict if tur == "sozluk" else list)


def _ad_mi(deger):
    return isinstance(deger, str) and bool(deger.strip())


def gorunum_hatalari(gorunum):
    """Her sistem kodu için ekranda görünecek boş olmayan bir ad, tanımsız kod yok; branş adları
    [kod, ad] çiftleri (kod tekrarsız), alt başlık ve mevcut alan adları boş olmayan metin."""
    adlar, hatalar = gorunum["sistem_adlari"], []  # açıklama anahtarı (_) zaten reddedilir
    bos = [kod for kod in SISTEMLER if not _ad_mi(adlar.get(kod))]
    if bos or set(adlar) - set(SISTEMLER):
        hatalar.append("gorunum.sistem_adlari: yalnız şu kodlar, her biri için ad: " +
                       ", ".join(SISTEMLER))
    branslar = gorunum["brans_adlari"]
    ciftler = [oge for oge in branslar if isinstance(oge, list) and len(oge) == 2
               and all(_ad_mi(parca) for parca in oge)]
    if len(ciftler) != len(branslar) or len({kod for kod, _ in ciftler}) != len(ciftler):
        hatalar.append("gorunum.brans_adlari: [kod, ad] çiftleri listesi olmalı, kod tekrarsız")
    hatalar += ["gorunum.{}: her kod için boş olmayan bir ad".format(alan)
                for alan in ("alt_baslik_adlari", "mevcut_alan_adlari")
                if not all(_ad_mi(ad) for ad in gorunum[alan].values())]
    return hatalar


def diger_hatalari(params):
    """Süre, Kriter 2, veri hazırlığı ve kalite bölümlerinin içerik kuralları. Tahsilat ve süre
    puanının ölçeği (taban, eğim) aynıdır: birleşik puan sütunları aynı anlamda toplar (taban
    her sütunda beklenen düzeydir)."""
    hatalar, k2 = veri_hatalari(params), params["kriter2"]
    tah, sure = params["tahsilat"], params["sure_puani"]
    if (tah["taban"], tah["egim"]) != (sure["taban"], sure["egim"]):
        hatalar.append("tahsilat ve sure_puani: taban ve egim aynı olmalı")
    if params["sure_puani"]["pencere_ay"] < 1:
        hatalar.append("sure_puani.pencere_ay pozitif olmalı")
    if not k2["rucu_kodu"]:
        hatalar.append("kriter2.rucu_kodu boş olamaz")
    kapanis = k2["kapanis_kodlari"]
    if not all(isinstance(kod, str) and kod.strip() for kod in kapanis) \
            or k2["rucu_kodu"] in kapanis:
        hatalar.append("kriter2.kapanis_kodlari boş olmayan metin listesi olmalı, rucu_kodu'nu "
                       "içeremez")
    return hatalar


def kalite_davranis_hatalari(kd):
    hatalar = []
    oran = kd["yeterlilik"]
    gecerli = len(oran) == 2 and all(tur_uygun(sayi, "tam") for sayi in oran)
    if not gecerli or not 0 < oran[0] <= oran[1]:
        hatalar.append("kalite_davranis.yeterlilik [pay, payda] tam sayı olmalı (ör. [2, 3]); "
                       "0 < pay <= payda")
    listeler = [kd["alt_basliklar"].get(ad) for ad in KALITE_DAVRANIS_SUTUNLARI]
    duzgun = sorted(kd["alt_basliklar"]) == sorted(KALITE_DAVRANIS_SUTUNLARI) and all(
        isinstance(liste, list) and liste and all(isinstance(kod, str) for kod in liste)
        for liste in listeler)
    kodlar = [kod for liste in listeler for kod in liste] if duzgun else []
    if not duzgun or len(set(kodlar)) < len(kodlar):
        hatalar.append("kalite_davranis.alt_basliklar: kalite ve davranis için tekrarsız "
                       "kod listesi")
    sinir = [kd["olcek"].get("en_dusuk"), kd["olcek"].get("en_yuksek")]
    sayisal = all(tur_uygun(deger, "sayi") for deger in sinir) and sinir[0] < sinir[1]
    if sorted(kd["olcek"]) != ["en_dusuk", "en_yuksek"] or not (sayisal or sinir == [None] * 2):
        hatalar.append("kalite_davranis.olcek: en_dusuk < en_yuksek sayı olmalı ya da ikisi "
                       "de null")
    ters = kd["ters_yonlu"]
    if ters is not None and not all(kod in kodlar for kod in ters):
        hatalar.append("kalite_davranis.ters_yonlu yalnız tanımlı alt başlık kodlarını "
                       "içerebilir")
    mevcut = kd["mevcut_alanlar"]
    if not all(isinstance(kod, str) for kod in mevcut) or set(mevcut) & set(kodlar):
        hatalar.append("kalite_davranis.mevcut_alanlar: alt başlıklardan ayrı kod listesi")
    if kd["pencere_ay"] < 1:
        hatalar.append("kalite_davranis.pencere_ay pozitif olmalı")
    return hatalar


def not_hatalari(notlar):
    """Not ölçeği: yüksekten düşüğe [ad, eşik] listesi; ilk eşik en çok 100, son eşik 0."""
    duzgun = bool(notlar) and all(
        isinstance(satir, list) and len(satir) == 2 and isinstance(satir[0], str)
        and tur_uygun(satir[1], "sayi") for satir in notlar)
    adlar = [satir[0] for satir in notlar] if duzgun else []
    esikler = [satir[1] for satir in notlar] if duzgun else []
    azalan = all(ust > alt for ust, alt in zip(esikler, esikler[1:]))
    if not duzgun or len(set(adlar)) < len(adlar) or not azalan or esikler[0] > 100 \
            or esikler[-1] != 0:
        return ["notlar: [ad, eşik] listesi; adlar tekrarsız, eşikler 100'den 0'a azalan"]
    return []
