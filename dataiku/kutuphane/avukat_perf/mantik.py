"""Mantıksal değerin tek çözücüsü: veri kümesinden gelen her biçim aynı okunur.

Dataiku boş değerli mantıksal sütunu metin okur (bool_as_str: "true"/"false"); kaynak sistemler
E/H ya da 1/0 verebilir. bool("false") Python'da True olduğu için bu değerler doğrudan bool()
ile okunmaz. Doğru sayılanlar: True, sıfırdan farklı sayı, "true", "1", "e", "evet" (büyük
küçük harf ve boşluk farkı yok sayılır). Boş değer (None, NaN) ve başka her şey yanlıştır.
"""
import math

import pandas as pd

DOGRU_METINLER = ("true", "1", "e", "evet")


def dogru_mu(deger):
    if deger is None or isinstance(deger, (bool, str)):
        return bool(deger) and (deger is True or str(deger).strip().lower() in DOGRU_METINLER)
    try:
        sayi = float(deger)
    except (TypeError, ValueError):
        return False
    return not math.isnan(sayi) and sayi != 0


def dogru_seri(seri):
    """Sütunun her değeri dogru_mu ile; sonuç bool türünde seridir."""
    return pd.Series([dogru_mu(deger) for deger in seri], index=seri.index, dtype=bool)
