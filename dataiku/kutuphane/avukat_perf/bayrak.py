"""Bayrak, düşüm ve KIRMIZI kuralı: Kriter 1 ve Kriter 2'de ortaktır.

Eşik günü dahildir: eşik tarihi ölçüm sonuna eşit ya da ondan önceyse bayrak oluşur. TURUNCU,
atama dönemi başına bir defalık puan düşümüdür; dönem eşikten sonra kapansa da düşüm kalır.
KIRMIZI, düşüm tarihinden sonraki takvim ayının ilk günü dönem hâlâ açıksa oluşur ve yeni düşüm
doğurmaz. İade ya da yeniden atamayla sonlanan (SONLANDI) dönemde, korunur parametresi false
ise düşüm sayılmaz; bayrak geçmişi yine kalır.
"""
import pandas as pd

BAYRAKLAR = ("SARI", "TURUNCU", "KIRMIZI")


def esikler(sari, turuncu):
    """Eşik tarihleri; KIRMIZI düşümden sonraki takvim ayının ilk günüdür."""
    return {"SARI": sari, "TURUNCU": turuncu, "KIRMIZI": turuncu + pd.offsets.MonthBegin(1)}


def degerlendir(esik, son, kapanis, sonlananda_korunur):
    """(seviye, en yüksek seviye, düşüm): ölçüm sonuna (son) kadar oluşan bayraklardan.

    kapanis: KAPANDI, SONLANDI, KOSUL_DISI ya da açık dönemde None.
    """
    olusan = [bayrak for bayrak in BAYRAKLAR if esik[bayrak] <= son]
    dusum = "TURUNCU" in olusan
    if kapanis == "SONLANDI" and not sonlananda_korunur:
        dusum = False
    en_yuksek = olusan[-1] if olusan else None
    return kapanis or en_yuksek or "IZLENIYOR", en_yuksek, dusum
