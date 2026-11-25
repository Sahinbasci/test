"""Kaynak şeması özeti: gerçek veriden satır göstermeden alan adı, tür, doluluk ve biçim.

Dataiku'da bir Python not defterinde çalıştırın. VERI_KUMELERI'ne Excel'den yüklediğiniz veri
kümelerinin adlarını yazın. Çıktıda satır değeri yoktur: her sütun için Dataiku türü, boş oranı,
farklı değer sayısı ve en sık üç biçim maskesi yazılır (rakam 9, büyük harf A, küçük harf a:
"D-000123" → "A-999999", "05.11.2026" → "99.99.9999", "1.234,56" → "9.999,99"). DEGER_LISTESI'ne
yazdığınız sütunlarda (yalnız branş, hareket türü, durum gibi kod listeleri) farklı değerlerin
kendisi de yazılır; buraya kişi, dosya numarası ya da tutar sütunu yazmayın. Çıktıyı paylaşmadan
önce okuyun.
"""
import collections
import re

import dataiku

VERI_KUMELERI = []  # ör. ["pbi_dosya", "pbi_tahsilat", "pbi_avukat_toplam"]
DEGER_LISTESI = {}  # ör. {"pbi_dosya": ["Branş"], "pbi_tahsilat": ["Hareket Türü"]}
EN_COK_DEGER = 40


def maske(deger):
    """Değerin biçimi: rakam 9, büyük harf A, küçük harf a; diğer işaretler kalır."""
    metin = re.sub(r"\d", "9", str(deger))
    metin = re.sub(r"[^\W\d_]", lambda m: "A" if m.group(0).isupper() else "a", metin)
    return metin[:40]


def _turler(veri_kumesi):
    try:
        return {alan["name"]: alan["type"] for alan in veri_kumesi.read_schema()}
    except Exception:  # eski sürüm ya da şemasız veri kümesi
        return {}


def ozetle(ad):
    veri_kumesi = dataiku.Dataset(ad)
    try:
        tablo = veri_kumesi.get_dataframe(infer_with_pandas=False)
    except TypeError:  # eski sürüm
        tablo = veri_kumesi.get_dataframe()
    turler = _turler(veri_kumesi)
    print("== {}: {} satır, {} sütun".format(ad, len(tablo), len(tablo.columns)))
    secili = set(DEGER_LISTESI.get(ad, []))
    for sutun in tablo.columns:
        dolu = tablo[sutun].dropna()
        dolu = dolu[dolu.astype(str).str.strip() != ""]
        bos = 100.0 * (1 - len(dolu) / float(max(len(tablo), 1)))
        sik = collections.Counter(maske(deger) for deger in dolu).most_common(3)
        print("- {} | tür {} | boş %{:.1f} | {} farklı | biçim: {}".format(
            sutun, turler.get(sutun, str(tablo[sutun].dtype)), bos, dolu.nunique(),
            ", ".join(bicim for bicim, _ in sik) or "—"))
        if sutun in secili:
            degerler = sorted(set(str(deger).strip() for deger in dolu))
            print("  değerler ({}): {}".format(len(degerler), " | ".join(degerler[:EN_COK_DEGER])
                                              + (" | …" if len(degerler) > EN_COK_DEGER else "")))


for AD in VERI_KUMELERI:
    ozetle(AD)
if not VERI_KUMELERI:
    print("VERI_KUMELERI listesine veri kümesi adlarını yazıp yeniden çalıştırın.")
