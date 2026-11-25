"""Grafana panosu sorgu dosyasıyla aynı kalır; panelin okuduğu sütunlar çalışma kaydında ve kalite
sonucunda var; alarm ve panel sorguları küçük bir kayıtla sqlite'ta çalıştırılır (PostgreSQL'e
özgü tarih ifadeleri çevrilerek)."""
import json
import os
import re
import sqlite3

from avukat_perf.kalite import SONUC
from hat.calisma import SUTUNLAR
from yardimci import KOK

GRAFANA = os.path.join(KOK, "grafana")


def _sorgular():
    with open(os.path.join(GRAFANA, "sorgular.sql"), encoding="utf-8") as dosya:
        metin = dosya.read()
    bloklar = {}
    for parca in re.split(r"\n(?=-- [PA]\d )", metin):
        eslesme = re.match(r"-- ([PA]\d) [^\n]*\n((?:--[^\n]*\n)*)(.*)", parca, re.S)
        if eslesme:
            bloklar[eslesme.group(1)] = eslesme.group(3).strip().rstrip(";")
    return bloklar


def test_pano_sorgulari_dosyayla_ayni():
    with open(os.path.join(GRAFANA, "pano.json"), encoding="utf-8") as dosya:
        pano = json.load(dosya)
    panodaki = [hedef["rawSql"] for panel in pano["panels"] for hedef in panel["targets"]]
    sorgular = _sorgular()
    assert panodaki == [sorgular["P{}".format(sira)] for sira in range(1, 6)]
    assert {"A1", "A2", "A3"} <= set(sorgular)


def test_sorgulardaki_calisma_sutunlari_tabloda_var():
    sozcukler = set(re.findall(r"\b[a-z_]+\b", " ".join(_sorgular().values())))
    beklenen = {"calisma_kimligi", "tur", "kaynak", "yontem", "baslangic", "bitis",
                "cekim_tarihi", "satir_sayisi", "durum"}
    assert beklenen <= sozcukler and beklenen <= set(SUTUNLAR)


def _sqlite(ad):
    """Sorguyu sqlite'a çevirir: pano değişkenleri tablo adı, ::date date(), CURRENT_DATE :bugun."""
    metin = _sorgular()[ad]
    metin = metin.replace("${calisma_tablosu}", "calisma").replace("${kalite_tablosu}", "kalite")
    metin = re.sub(r"(MAX\(cekim_tarihi\)|\w+)::date", r"date(\1)", metin)
    metin = metin.replace("CURRENT_DATE - 1", "date(:bugun, '-1 day')")
    return metin.replace("CURRENT_DATE - son > 1", "julianday(:bugun) - julianday(son) > 1")


def _calistir(ad, calisma, kalite=(), bugun="2026-11-19"):
    vt = sqlite3.connect(":memory:")
    vt.execute("CREATE TABLE calisma (calisma_kimligi, tur, kaynak, baslangic, cekim_tarihi, "
               "durum, kalite_sonucu)")
    vt.executemany("INSERT INTO calisma VALUES (?, 'GECELIK', ?, ?, ?, ?, ?)", calisma)
    vt.execute("CREATE TABLE kalite (calisma_kimligi, kaynak, kontrol, durum, deger, esik, "
               "aciklama)")
    vt.executemany("INSERT INTO kalite VALUES (?, ?, ?, ?, 0, 0, '')", kalite)
    return vt.execute(_sqlite(ad), {"bugun": bugun}).fetchall()


def _gece(kimlik, gun, karar, kaynaklar):
    """Bir gecenin özet ve kaynak satırları: kaynaklar {ad: (durum, kalite_sonucu)}."""
    zaman = gun + " 02:00:00"
    return [(kimlik, "*", zaman, gun, karar, karar)] + [
        (kimlik, ad, zaman, gun, durum, sonuc) for ad, (durum, sonuc) in kaynaklar.items()]


def test_kaynak_beklenirken_gecen_gece_alarmi_calmaz():
    """Kurulumdan entegrasyona kadar her gece KAYNAK_BEKLENIYOR: A1 her gün çalmamalı
    (README "alarm üretilmez" diyordu)."""
    bekleyen = {"dosya": ("KAYNAK_BEKLENIYOR", None)}
    gece = _gece("C1", "2026-11-18", "KAYNAK_BEKLENIYOR", bekleyen)
    gece += _gece("C2", "2026-11-19", "KAYNAK_BEKLENIYOR", bekleyen)
    assert _calistir("A1", gece) == [(2,)]
    kalan = _gece("C3", "2026-11-18", "KALDI", {"dosya": ("KALDI", "KALDI")})
    assert _calistir("A1", kalan) == [(0,)] and _calistir("A2", kalan) == [(1,)]


def test_tek_kaynak_kalinca_yalniz_o_kaynak_bayat_kaldi_satirlari_once():
    """Bir kaynak iki gece kalınca A3 yalnız onu sayar (kapıdan geçen kaynaklar gece KALDI diye
    bayat görünmez); P5'te geceyi durduran KALDI satırı uyarıların üstündedir."""
    gece = _gece("C1", "2026-11-16", "GECTI", {ad: ("BASARILI", "GECTI")
                                                for ad in ("dosya", "atama_log", "takip")})
    for kimlik, gun in (("C2", "2026-11-17"), ("C3", "2026-11-18")):
        gece += _gece(kimlik, gun, "KALDI", {"dosya": ("KALDI", "GECTI"),
                                             "atama_log": ("KALDI", "KALDI"),
                                             "takip": ("KALDI", "GECTI")})
    assert _calistir("A3", gece) == [(1,)]
    kalite = [("C3", "atama_log", "TUR:atama_tarihi", "KALDI"),
              ("C3", "dosya", "DEGER:brans", "UYARI"), ("C3", "avukat", "EKSIK_ALAN", "UYARI")]
    assert [satir[2] for satir in _calistir("P5", gece, kalite)] == ["KALDI", "UYARI", "UYARI"]


def test_p5_sutunlari_kalite_sonucunda_alarm_metni_tablo_adini_soyler():
    sutunlar = re.match(r"SELECT (.*?)\s+FROM", _sorgular()["P5"], re.S).group(1)
    assert {ad.strip() for ad in sutunlar.split(",")} <= set(SONUC)
    with open(os.path.join(GRAFANA, "README.md"), encoding="utf-8") as dosya:
        alarm = dosya.read().split("## Alarmlar", 1)[1]
    assert "${calisma_tablosu}" in alarm and "gerçek tablo adı" in alarm
