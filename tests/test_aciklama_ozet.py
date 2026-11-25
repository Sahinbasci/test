"""'Neden bu puanı aldı?' özeti: sütun cümleleri, beklenen düzeye göre etkiler ve eşitlik."""
import random
from decimal import Decimal

import pandas as pd

from avukat_perf import aciklama, aciklama_ozet, agirlik, birlesik
from arayuz.sunum_avukat import _aciklama
from yardimci import dort_sutunlu, params_yukle

BIRLESIK = ["avukat_kodu", "tahsilat", "sure", "kalite", "davranis", "birlesik_puan",
            "performans_notu", "genel_sira", "durum", "eksik_sutunlar"]
SUTUNLAR = ("tahsilat", "sure", "kalite", "davranis")


def _satir(puanlar, toplam, notu="B", durum="YAYIMLANDI", eksik=""):
    return pd.DataFrame([("AV-1",) + tuple(puanlar) + (toplam, notu, 1.0, durum, eksik)],
                        columns=BIRLESIK)


def _ozet(tablo, sutun, tur="OZET"):
    secili = tablo[(tablo["sutun"] == sutun) & (tablo["tur"] == tur)]
    return list(zip(secili["metin"], secili["etki"]))


def test_ornek_avukatin_etkileri_ve_esitligi():
    # 0,35 × 60,03 + 0,30 × 74,83 + 0,25 × 83,33 + 0,10 × 87,50 = 73,042 → 73,04. Etkiler:
    # −5,2395, −0,051, +2,0825, +1,25; tek tek yuvarlansa toplam −1,97 olurdu, en büyük kalan
    # (süre, 0,009) bir kuruş alır ve eşitlik 73,04'ü verir.
    tablo = aciklama.uret(dort_sutunlu(), birlesik=_satir((60.03, 74.83, 83.33, 87.5), 73.04))
    assert _ozet(tablo, "birlesik")[0][0] == (
        "Puanı en çok tahsilat düşürdü (−5,24). Hukuki kalite (+2,08) ve davranış (+1,25) "
        "yükseltti. Süre beklenen düzeye yakın.")
    assert _ozet(tablo, "birlesik", "ESITLIK")[0][0] == (
        "Birleşik puan = 75 − 5,24 − 0,05 + 2,08 + 1,25 = 73,04 → B")
    etki = aciklama_ozet.etkiler(next(_satir((60.03, 74.83, 83.33, 87.5), 73.04).itertuples()),
                                 dort_sutunlu())
    assert etki == {"tahsilat": -5.24, "sure": -0.05, "kalite": 2.08, "davranis": 1.25}


def test_esitlik_her_zaman_birlesik_puani_verir():
    """Rastgele 500 avukatta etkilerin toplamı birleşik puan − 75'e kuruşu kuruşuna eşittir ve
    her etki kesin değerinden bir kuruştan az sapar. Tek tek yuvarlama bunu sağlamaz: dört sütun
    da 75,01 iken her etki 0,00'a yuvarlanır, birleşik puan ise 75,01'dir."""
    params, rnd = dort_sutunlu(), random.Random(7)
    agirliklar = agirlik.sutun_agirliklari(params)
    ornekler = [(75.01,) * 4] + [tuple(round(rnd.uniform(0, 100), 2) for _ in SUTUNLAR)
                                 for _ in range(500)]
    for puanlar in ornekler:
        toplam = birlesik.agirlikli_toplam(dict(zip(SUTUNLAR, puanlar)), agirliklar)
        etki = aciklama_ozet.etkiler(next(_satir(puanlar, toplam).itertuples()), params)
        toplam_etki = sum(Decimal(repr(e)) for e in etki.values())
        assert toplam_etki == Decimal(repr(toplam)) - 75, (puanlar, etki)
        for ad, puan in zip(SUTUNLAR, puanlar):
            kesin = Decimal(repr(agirliklar[ad])) * (Decimal(repr(puan)) - 75)
            assert abs(Decimal(repr(etki[ad])) - kesin) < Decimal("0.01"), (puanlar, ad)


def test_birlesik_cumlesinin_bicimleri():
    params = dort_sutunlu()
    tablo = aciklama.uret(params, birlesik=_satir((92.91, 86.33, 89.56, 76.8), 88.49, "A"))
    assert _ozet(tablo, "birlesik")[0][0] == (
        "Puanı tahsilat (+6,27), hukuki kalite (+3,64) ve süre (+3,40) yükseltti. Davranış "
        "beklenen düzeye yakın.")
    tablo = aciklama.uret(params, birlesik=_satir((50.0, 60.0, 75.0, 75.0), 62.75, "B-"))
    assert _ozet(tablo, "birlesik")[0][0] == (
        "Puanı en çok tahsilat düşürdü (−8,75), ardından süre (−4,50). Hukuki kalite ve "
        "davranış beklenen düzeye yakın.")
    tablo = aciklama.uret(params, birlesik=_satir((75.0, 75.0, 75.0, 75.0), 75.0))
    assert _ozet(tablo, "birlesik")[0][0] == (
        "Tahsilat, süre, hukuki kalite ve davranış beklenen düzeye yakın.")
    assert _ozet(tablo, "birlesik", "ESITLIK")[0][0] == (
        "Birleşik puan = 75 + 0,00 + 0,00 + 0,00 + 0,00 = 75,00 → B")


def test_sutun_cumleleri():
    params = params_yukle()
    tahsilat = pd.DataFrame([("AV-1", 30.0, 2385649.96, 3286540.11, 0.7259, 0.74, 61.89, 265.0,
                              388.1231, 59.54, 127.0, 218.6012, 54.96, 60.03, None, "GECERLI")],
                            columns=["avukat_kodu", "n", "gerceklesen", "beklenen", "oran", "r",
                                     "puan_tutar", "siklik_o", "siklik_e", "puan_siklik",
                                     "guncellik_o", "guncellik_e", "puan_guncellik", "puan",
                                     "eksik_nedeni", "durum"])
    tablo = aciklama.uret(params, tahsilat=tahsilat)
    assert _ozet(tablo, "tahsilat")[0][0] == (
        "Tahsilatı, benzer dosyalarda beklenen tutarın %73 düzeyinde (2,39 Mn TL / 3,29 Mn TL). "
        "Dosyalarında tahsilat yapılan ay sayısı beklenenin %68 düzeyinde, son 12 ayda %58.")
    assert aciklama_ozet.tl_kisa(1250.0) == "1,3 bin TL" and aciklama_ozet.tl_kisa(-80) == "-80 TL"
    sure = pd.DataFrame([("AV-1", 55, 51, 12, 11.9243, 0.93, 1.0, 74.83, None, "GECERLI"),
                         ("AV-2", 20, 18, 0, 1.24, 0.95, 0.9, 79.6, None, "GECERLI")],
                        columns=["avukat_kodu", "risk_donemi", "risk_dosya", "o", "e", "kapsam",
                                 "r", "puan", "eksik_nedeni", "durum"])
    tablo = aciklama.uret(params, sure=sure)
    assert [m for m, _ in _ozet(tablo, "sure")] == [
        "51 dosyada 12 puan düşümü aldı; benzer dosyalarda beklenen 11,9.",
        "18 dosyada hiç puan düşümü almadı; benzer dosyalarda beklenen 1,2."]


def test_kalite_davranis_en_dusuk_alt_baslik():
    params = params_yukle()
    sutun = pd.DataFrame([("AV-1", "kalite", 6, 6, 4, 83.33, "GECERLI"),
                          ("AV-1", "davranis", 7, 7, 5, 87.5, "GECERLI"),
                          ("AV-2", "kalite", 6, 6, 4, 87.5, "GECERLI"),
                          ("AV-3", "kalite", 6, 6, 4, 80.0, "GECERLI")],
                         columns=["avukat_kodu", "sutun", "puanlanan", "toplam", "gereken",
                                  "puan", "durum"])
    kodlar = params["kalite_davranis"]["alt_basliklar"]
    alt = [("AV-1", "kalite", k, p) for k, p in zip(kodlar["kalite"], (87.5, 87.5, 87.5, 87.5,
                                                                       75, 75))]
    alt += [("AV-1", "davranis", k, p) for k, p in zip(kodlar["davranis"],
                                                         (100, 50, 100, 100, 100, 100, None))]
    alt += [("AV-2", "kalite", k, 87.5) for k in kodlar["kalite"]]
    alt += [("AV-3", "kalite", k, p) for k, p in zip(kodlar["kalite"], (70, 70, 70, 100, 90, 80))]
    alt = pd.DataFrame(alt, columns=["avukat_kodu", "sutun", "alt_baslik", "puan"])
    tablo = aciklama.uret(params, kalite_davranis=sutun, kalite_davranis_alt=alt)
    metin = {(k, s): m for k, s, m, t in zip(tablo["avukat_kodu"], tablo["sutun"],
                                             tablo["metin"], tablo["tur"]) if t == "OZET"}
    assert metin[("AV-1", "kalite")] == ("6 alt başlığın ortalaması. En düşük (75): İç ekibin "
                                         "müdahale ihtiyacı · Sistem kullanımı ve güncellik.")
    assert metin[("AV-1", "davranis")] == ("7 alt başlığın ortalaması. En düşük (50): Dosyaya "
                                           "hakimiyet.")
    assert metin[("AV-2", "kalite")] == ("6 alt başlığın ortalaması. Bütün alt başlıklar aynı "
                                         "puanda (87,50).")
    assert metin[("AV-3", "kalite")] == ("6 alt başlığın ortalaması. En düşük puan 70 "
                                         "(3 alt başlık).")


def test_puani_gecerli_olmayan_satirda_ozet_ve_etki_yok():
    params = params_yukle()
    tablo = aciklama.uret(params, birlesik=_satir((80.0, None, None, 88.0), None, None,
                                                  "EKSIK_SUTUN", "sure,kalite"))
    assert set(tablo["tur"]) == {"ISTISNA"} and tablo["etki"].isna().all()
    kalite = pd.DataFrame([("AV-1", "kalite", 3, 6, 4, None, "EKSIK_DEGERLENDIRME")],
                          columns=["avukat_kodu", "sutun", "puanlanan", "toplam", "gereken",
                                   "puan", "durum"])
    assert "OZET" not in set(aciklama.uret(params, kalite_davranis=kalite)["tur"])


def test_etki_yalniz_sutun_ozetlerinde_ve_birlesik_yayimlandiysa():
    params = dort_sutunlu()
    sure = pd.DataFrame([("AV-1", 55, 51, 12, 11.9243, 0.93, 1.0, 74.83, None, "GECERLI")],
                        columns=["avukat_kodu", "risk_donemi", "risk_dosya", "o", "e", "kapsam",
                                 "r", "puan", "eksik_nedeni", "durum"])
    tablo = aciklama.uret(params, sure=sure,
                          birlesik=_satir((60.03, 74.83, 83.33, 87.5), 73.04))
    dolu = tablo[tablo["etki"].notna()]
    assert list(zip(dolu["sutun"], dolu["tur"], dolu["etki"])) == [("sure", "OZET", -0.05)]
    tek = aciklama.uret(params, sure=sure)  # birleşik yoksa etki de yok
    assert tek["etki"].isna().all() and "OZET" in set(tek["tur"])


def test_sunum_satirlara_puan_agirlik_ve_not_ekler():
    """Sunum satırlara sütunun puanını ve ağırlığını, birleşik satırına notu ekler; açıklaması
    olmayan sütun için içeriksiz YOK satırı gelir (bu fazda puana girmeyen Süre'nin ağırlığı 0)."""
    aciklama_t = pd.DataFrame([("AV-1", "birlesik", 2, "OZET", "x", None),
                               ("AV-1", "tahsilat", 1, "KANIT", "a", None),
                               ("AV-1", "birlesik", 1, "HESAP", "y", None),
                               ("AV-1", "tahsilat", 12, "OZET", "b", -5.24)],
                              columns=["avukat_kodu", "sutun", "sira", "tur", "metin", "etki"])
    puan = pd.DataFrame([("AV-1", "tahsilat", 60.03, 0.5), ("AV-1", "sure", None, 0.0)],
                        columns=["avukat_kodu", "sutun", "puan", "agirlik"])
    birlesik_t = _satir((60.03, 74.83, 83.33, 87.5), 73.04)
    sonuc = _aciklama(aciklama_t, puan, birlesik_t)
    assert list(zip(sonuc["sutun"], sonuc["sira"], sonuc["tur"])) == [
        ("tahsilat", 1, "KANIT"), ("tahsilat", 12, "OZET"), ("sure", 0, "YOK"),
        ("kalite", 0, "YOK"), ("davranis", 0, "YOK"), ("birlesik", 1, "HESAP"),
        ("birlesik", 2, "OZET")]
    satir = sonuc.set_index(["sutun", "sira"])
    assert satir.loc[("tahsilat", 12), "puan"] == 60.03
    assert satir.loc[("tahsilat", 1), "agirlik"] == 0.5
    assert satir.loc[("sure", 0), "agirlik"] == 0.0 and satir.loc[("sure", 0), "metin"] == ""
    assert satir.loc[("birlesik", 1), "puan"] == 73.04
    assert list(sonuc["performans_notu"]) == [None] * 5 + ["B", "B"]
    eski = _aciklama(aciklama_t, puan.drop(columns="agirlik"), None)  # eski tablo: ağırlık yok
    assert eski["agirlik"].isna().all() and eski["performans_notu"].isna().all()

def test_ilk_fazda_sure_etkisiz_ve_esitlikte_yok():
    """Varsayılan (ilk faz): 0,5 × 60,03 + 0,36 × 83,33 + 0,14 × 87,5 = 72,2638 → 72,26. Kesin
    etkiler −7,485 / +2,9988 / +1,75; aşağı yuvarlanınca −7,49 / +2,99 / +1,75 = −2,75, hedef
    −2,74: eksik kuruş en büyük kalana (kalite, 0,0088) gider. Süre eşitlikte ve cümlede yok."""
    params = params_yukle()
    satir = _satir((60.03, 74.83, 83.33, 87.5), 72.26)
    etki = aciklama_ozet.etkiler(next(satir.itertuples()), params)
    assert etki == {"tahsilat": -7.49, "kalite": 3.0, "davranis": 1.75}
    tablo = aciklama.uret(params, birlesik=satir)
    assert _ozet(tablo, "birlesik", "ESITLIK")[0][0] == (
        "Birleşik puan = 75 − 7,49 + 3,00 + 1,75 = 72,26 → B")
    cumle = _ozet(tablo, "birlesik")[0][0]
    assert "süre" not in cumle.lower(), cumle
    assert _ozet(tablo, "birlesik", "HESAP")[0][0] == (
        "Birleşik puan = 0,50 × 60,03 + 0,36 × 83,33 + 0,14 × 87,50 = 72,26 → B")
