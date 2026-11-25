"""Aktarılan dosyaların özetini yazar; şirket ortamına kopyalanan kodun ve ayarın birebir aynı
olduğunu doğrulamak için kullanılır.

Çıktı depo kökündeki aktarim_ozeti.txt dosyasında tutulur; tests/test_ozet.py dosyanın güncel
olduğunu denetler. Kapsam: kütüphane paketleri (dataiku/kutuphane altında __init__.py taşıyan
her klasör), web uygulamasının dört sekmesi, senaryo adımları (dataiku/tarifler), kontrol not
defterleri (dataiku/kontrol), varsayılan ayar dosyaları (dataiku/degiskenler) ve hesap sürümü.
Listeler klasörlerden türetilir: yeni paket ya da betik kendiliğinden özete girer.
Özet kuralı avukat_perf.surum.metin_ozeti (kod) ve json_ozeti (ayar; anahtar sırası ve girinti
etkilemez) işlevleridir; not defterindeki bağımsız kopya (dataiku/kontrol/aktarim_kontrol.py)
testle aynı tutulur; iki çıktı satır satır eşleşmelidir (kontrol/ satırları hariç: not
defterleri Dataiku'da dosya olarak okunamaz, GitHub farkından izlenir). Satır sonu boşlukları,
satır sonu biçimi ve dosya sonundaki boş satırlar özeti etkilemez.
Kullanım: python araclar/ozet.py          (ekrana yazar)
          python araclar/ozet.py --yaz    (aktarim_ozeti.txt dosyasını günceller)
"""
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUTUPHANE = os.path.join(KOK, "dataiku", "kutuphane")
if KUTUPHANE not in sys.path:
    sys.path.insert(0, KUTUPHANE)
from avukat_perf.surum import hesap_surumu, metin_ozeti  # noqa: E402  (tek kural: surum.py)
from avukat_perf.surum import json_ozeti  # noqa: E402


def paketler(kutuphane=KUTUPHANE):
    """Kütüphane paketleri: __init__.py taşıyan klasörler, ada göre sıralı."""
    return tuple(sorted(ad for ad in os.listdir(kutuphane)
                        if os.path.isfile(os.path.join(kutuphane, ad, "__init__.py"))))


def betikler(klasor):
    """Klasördeki .py dosyaları, ada göre sıralı."""
    return tuple(sorted(ad for ad in os.listdir(klasor) if ad.endswith(".py")))


PAKETLER = paketler()
WEBAPP = ("index.html", "stil.css", "uygulama.js", "backend.py")
TARIFLER = betikler(os.path.join(KOK, "dataiku", "tarifler"))
KONTROL = betikler(os.path.join(KOK, "dataiku", "kontrol"))
AYARLAR = ("params.json", "kaynaklar.json")
OZET_DOSYASI = os.path.join(KOK, "aktarim_ozeti.txt")


def dosya_ozeti(yol):
    with open(yol, encoding="utf-8") as dosya:
        return metin_ozeti(dosya.read())


def _json(yol):
    with open(yol, encoding="utf-8-sig") as dosya:
        return json.load(dosya)


def satirlar():
    """'yol özet' satırları: kütüphane, web uygulaması, senaryo adımları, kontrol not defterleri,
    varsayılan ayarlar, hesap sürümü."""
    cikti = []
    for paket in PAKETLER:
        klasor = os.path.join(KUTUPHANE, paket)
        cikti += ["{}/{} {}".format(paket, ad, dosya_ozeti(os.path.join(klasor, ad)))
                  for ad in betikler(klasor)]
    for klasor, adlar in (("webapp", WEBAPP), ("tarifler", TARIFLER), ("kontrol", KONTROL)):
        cikti += ["{}/{} {}".format(klasor, ad, dosya_ozeti(os.path.join(KOK, "dataiku", klasor,
                                                                          ad))) for ad in adlar]
    degiskenler = os.path.join(KOK, "dataiku", "degiskenler")
    cikti += ["degiskenler/{} {}".format(ad, json_ozeti(_json(os.path.join(degiskenler, ad))))
              for ad in AYARLAR]
    cikti.append("hesap_surumu " + hesap_surumu(_json(os.path.join(degiskenler, "params.json"))))
    return cikti


if __name__ == "__main__":
    METIN = "\n".join(satirlar()) + "\n"
    if "--yaz" in sys.argv:
        with open(OZET_DOSYASI, "w", encoding="utf-8") as hedef:
            hedef.write(METIN)
    print(METIN, end="")
