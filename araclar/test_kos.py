"""pytest olmayan ortamda testleri çalıştırır.

Kullanım: python araclar/test_kos.py
Şirket ortamında test_yazim.py atlanır: kos(atla=("test_yazim.py",))
Uyarılar pytest.ini'deki gibi hata sayılır (UYARI_KURALLARI; test_yazim aynı olduğunu denetler).
"""
import builtins
import importlib
import os
import sys
import traceback
import warnings

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTLER = os.path.join(KOK, "tests")
KUTUPHANE = os.path.join(KOK, "dataiku", "kutuphane")
# pytest.ini filterwarnings satırları, aynı sırayla (eylem:ileti:tür:modül).
UYARI_KURALLARI = ("error", "ignore::DeprecationWarning:flask")


def uyari_kurallari():
    """UYARI_KURALLARI'nı etkin uyarı süzgeçlerine ekler; sonraki kural öncekini ezer."""
    for kural in UYARI_KURALLARI:
        eylem, ileti, tur, modul = (kural.split(":") + ["", "", ""])[:4]
        warnings.filterwarnings(eylem, message=ileti, category=getattr(
            builtins, tur or "Warning"), module=modul)


def calistir(fonk):
    """fonk'u uyarı kurallarıyla çalıştırır; geçerse None, kalırsa hata metni döner."""
    with warnings.catch_warnings():
        uyari_kurallari()
        try:
            fonk()
        except Exception:
            return traceback.format_exc()
    return None


def kos(atla=()):
    sys.path[:0] = [KOK, KUTUPHANE, TESTLER]
    gecen, kalanlar = 0, []
    for dosya in sorted(os.listdir(TESTLER)):
        if not (dosya.startswith("test_") and dosya.endswith(".py")) or dosya in atla:
            continue
        with warnings.catch_warnings():  # içe aktarmadaki uyarı da hata sayılır
            uyari_kurallari()
            modul = importlib.import_module(dosya[:-3])
        for ad in sorted(dir(modul)):
            if not ad.startswith("test_") or not callable(getattr(modul, ad)):
                continue
            hata = calistir(getattr(modul, ad))
            if hata is None:
                gecen += 1
            else:
                kalanlar.append("{}::{}\n{}".format(dosya, ad, hata))
    for kayit in kalanlar:
        print("KALDI", kayit)
    print("{} geçti, {} kaldı".format(gecen, len(kalanlar)))
    return not kalanlar


if __name__ == "__main__":
    sys.exit(0 if kos() else 1)
