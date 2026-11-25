"""Kaynak ayarının alt bloklarının doğrulanması: sayfalama, kimlik, dosya, dataiku, biçimler ve
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
