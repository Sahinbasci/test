"""Sentetik test verisi üreticisi: bütün kaynakları sözleşmedeki biçimde CSV olarak yazar.

Gerçek veri içermez; kişi ve dosya kimlikleri AV-01, D-000001 biçimindedir. Sabit tohumla
her çalıştırmada aynı veri çıkar. Gerçeğe yakın durumlar: avukatlar arası tahsilat becerisi
(tutar ve tahsilat yapılan dosya oranı ayrı), işlem hızı ve kalite farkı; sulh amaçlı ön
atama; yeniden atama ve iade (önceki kayda iptal tarihi yazılır); itirazlı
icra, arabuluculuk ve doğrudan dava; ters kayıt; atama öncesi tahsilat; eksik değerlendirme;
kaynak alan adlarının sözleşmeden farklı gelmesi, gün/ay/yıl tarih biçimi; Türkçe sayı biçimi.
Kullanım: python sentetik/uretici.py [hedef_klasor] [dosya_sayisi] [avukat_sayisi]
"""
import csv
import datetime as dt
import os
import random
import sys

KESIT = dt.date(2026, 11, 19)
BRANSLAR = [("TRAFIK", 0.40, 0.35, 40000), ("KASKO", 0.25, 0.30, 60000),
            ("NAKLIYAT", 0.10, 0.25, 150000), ("YANGIN", 0.15, 0.20, 250000),
            ("DAHILI_SU", 0.10, 0.22, 30000)]
KALITE = ["eksik_hatali_islem", "yanlis_muhatap_eksik_taraf", "hatali_dava_takip_islemi",
          "hukuki_degerlendirme", "ic_ekip_mudahalesi", "sistem_kullanimi_guncellik"]
DAVRANIS = ["tekrarlayan_bilgi_talebi", "dosyaya_hakimiyet", "karar_alma_inisiyatif",
            "surekli_yonlendirme_ihtiyaci", "yazili_iletisim_niteligi", "sorumluluk_alma",
            "indirim_sulh_yaklasimi"]
# Bilgi amaçlı dört değerlendirme alanı (puana girmez).
ESKI_ALANLAR = ["brans_yetkinligi", "cozum_yetenegi", "ulasilabilirlik", "durustluk_duzeyi"]


def _gun(rnd, bas, son):
    return bas + dt.timedelta(days=rnd.randint(0, (son - bas).days))


def _tr(tutar):
    return "{:,.2f}".format(tutar).replace(",", "_").replace(".", ",").replace("_", ".")


def avukatlar(rnd, adet):
    """Son iki avukat ayrılmıştır, ama en az iki avukat çalışmaya devam eder (yeniden atama
    başka bir avukata yapılabilsin): 3 avukatta yalnız sonuncusu, 1 ya da 2'de hiçbiri ayrılmaz."""
    if adet < 1:
        raise ValueError("en az bir avukat gerekir")
    ayrilan = min(2, max(0, adet - 2))
    sonuc = []
    for sira in range(1, adet + 1):
        uzman = [b[0] for b in rnd.sample(BRANSLAR, 2)]
        sonuc.append({"kod": "AV-{:02d}".format(sira), "beceri": min(1.6, max(
            0.6, rnd.lognormvariate(0, 0.25))), "tahsil_hizi": min(1.6, max(
                0.6, rnd.lognormvariate(0, 0.25))), "hiz": rnd.uniform(4, 16),
            "dava_hizi": rnd.uniform(40, 200), "kalite": rnd.uniform(2.4, 4.8), "uzman": uzman,
            "durum": "AYRILDI" if sira > adet - ayrilan else "DEVAM"})
    return sonuc


def _avukat_sec(rnd, avukat_listesi, brans, haric=None):
    adaylar = [a for a in avukat_listesi if a["kod"] != haric and a["durum"] == "DEVAM"]
    if not adaylar:  # tek avukatlı üretimde yeniden atanacak başka avukat yok
        return None
    agirlik = [4 if brans in a["uzman"] else 1 for a in adaylar]
    return rnd.choices(adaylar, weights=agirlik)[0]


def _donemler(rnd, avukat_listesi, brans, verilis, log, dosya_no):
    """Dosyanın atama dönemleri: [(avukat, baslangic, bitis ya da None)]."""
    donemler = []
    atama = verilis + dt.timedelta(days=min(400, int(rnd.expovariate(1 / 40.0)) + 3))
    if rnd.random() < 0.08:
        sulh = "SL-0{}".format(rnd.randint(1, 2))
        log.append([dosya_no, sulh, verilis + dt.timedelta(days=1), atama, "SULH"])
    if atama > KESIT:
        return donemler
    avukat = _avukat_sec(rnd, avukat_listesi, brans)
    zar = rnd.random()
    if zar < 0.10:
        degisim = atama + dt.timedelta(days=rnd.randint(60, 500))
        yeni = None
        if degisim < KESIT:
            yeni = _avukat_sec(rnd, avukat_listesi, brans, avukat["kod"])
        if yeni is not None:
            donemler.append((avukat, atama, degisim))
            log.append([dosya_no, avukat["kod"], atama, degisim, "NORMAL"])
            avukat, atama = yeni, degisim
    bitis = None
    if zar > 0.97:
        bitis = atama + dt.timedelta(days=rnd.randint(20, 300))
        bitis = bitis if bitis < KESIT else None
    donemler.append((avukat, atama, bitis))
    log.append([dosya_no, avukat["kod"], atama, bitis, "NORMAL"])
    return donemler


def _hareketler(rnd, dosya_no, rucu, oran, donemler, ilk_islem, verilis):
    hareketler, toplam = [], 0.0
    if donemler and rnd.random() < 0.05:
        tarih = _gun(rnd, verilis, min(donemler[0][1], KESIT))
        hareketler.append([dosya_no, tarih, round(rucu * 0.05, 2), "TAHSILAT"])
        toplam += rucu * 0.05
    for avukat, bas, bitis in donemler:
        son = min(bitis or KESIT, KESIT)
        bas = max(bas, ilk_islem or bas)
        # Tahsilat yapılıp yapılmaması tahsil_hizi becerisine, tutarı beceriye bağlıdır.
        if bas >= son or rnd.random() > min(0.9, 0.5 * avukat["tahsil_hizi"]):
            continue
        hedef = min(rucu - toplam, rucu * oran * avukat["beceri"] * rnd.lognormvariate(0, 0.4))
        for _ in range(rnd.randint(1, 5)):
            tutar = round(max(0.0, hedef) / 3.0 * rnd.uniform(0.5, 1.5), 2)
            if tutar <= 0:
                continue
            tarih = _gun(rnd, bas, son)
            hareketler.append([dosya_no, tarih, tutar, "TAHSILAT"])
            toplam += tutar
            if rnd.random() < 0.02:
                ters = min(tarih + dt.timedelta(days=rnd.randint(1, 30)), KESIT)
                hareketler.append([dosya_no, ters, -tutar, "TERS_KAYIT"])
                toplam -= tutar
    return hareketler, toplam


def _surec(rnd, dosya_no, esas_tarihi, avukat):
    zar = rnd.random()
    if esas_tarihi is None or zar > 0.40:
        return None
    if zar < 0.25:
        tur, bas = "ITIRAZ", esas_tarihi + dt.timedelta(days=rnd.randint(20, 60))
    elif zar < 0.35:
        tur, bas = "ARABULUCULUK", esas_tarihi
    else:
        return [dosya_no, "DOGRUDAN_DAVA", "", "", ""]
    if bas > KESIT:
        return None
    dava = bas + dt.timedelta(days=int(rnd.expovariate(1 / avukat["dava_hizi"])) + 15)
    if dava > KESIT or rnd.random() < 0.2:
        return [dosya_no, tur, bas, "", ""]
    return [dosya_no, tur, bas, "{}/{}".format(dava.year, rnd.randint(1000, 99999)), dava]


def _kalite_davranis(rnd, avukat_listesi):
    satirlar = []
    seyrek = {a["kod"] for a in avukat_listesi[2:5]}
    for avukat in avukat_listesi:
        if avukat["durum"] != "DEVAM":
            continue
        for _ in range(rnd.choice([1, 2, 2, 3])):
            tarih = _gun(rnd, KESIT - dt.timedelta(days=330), KESIT)
            degerlendiren = "IA-0{}".format(rnd.randint(1, 5))
            for kod in KALITE + DAVRANIS + ESKI_ALANLAR:
                if rnd.random() < (0.6 if avukat["kod"] in seyrek else 0.12):
                    puan = ""
                else:
                    puan = min(5, max(1, int(round(rnd.gauss(avukat["kalite"], 0.6)))))
                satirlar.append([avukat["kod"], tarih, kod, puan, degerlendiren])
    return satirlar


def _rapor_toplam(hareketler, son_avukat, brans_of):
    toplam = {}
    sinir = (KESIT.replace(day=1) - dt.timedelta(days=150)).replace(day=1)
    for dosya_no, tarih, tutar, _ in hareketler:
        if tarih >= sinir and dosya_no in son_avukat:
            anahtar = (son_avukat[dosya_no], tarih.strftime("%Y-%m"), brans_of[dosya_no])
            toplam[anahtar] = toplam.get(anahtar, 0.0) + tutar
    return [[kod, donem, round(tutar, 2), brans]
            for (kod, donem, brans), tutar in sorted(toplam.items())]


def _yaz(hedef, ad, basliklar, satirlar):
    with open(os.path.join(hedef, ad + ".csv"), "w", encoding="utf-8", newline="") as dosya:
        yazici = csv.writer(dosya)
        yazici.writerow(basliklar)
        for satir in satirlar:
            yazici.writerow(["" if deger is None else deger for deger in satir])


def _log_satiri(rnd, satir):
    dosya_no, kod, atama, iptal, tur = satir
    saat = dt.time(rnd.randint(8, 19), rnd.randint(0, 59), rnd.randint(0, 59))
    bicim = "%d/%m/%Y %H:%M:%S"
    iptal_metni = "" if iptal is None or tur == "SULH" else \
        dt.datetime.combine(iptal, saat).strftime(bicim)
    return [dosya_no, kod, dt.datetime.combine(atama, saat).strftime(bicim), iptal_metni,
            "AT{:05d}".format(rnd.randint(1, 99999)), "1", "N"]


def uret(hedef, dosya_sayisi=8000, avukat_sayisi=30, tohum=2026):
    """Bütün sentetik kaynakları hedef klasöre yazar; satır sayılarını döndürür."""
    rnd = random.Random(tohum)
    liste = avukatlar(rnd, avukat_sayisi)
    dosyalar, log, hareketler, esaslar, takip, surecler, son_avukat = [], [], [], [], [], [], {}
    for sira in range(1, dosya_sayisi + 1):
        dosya_no = "D-{:06d}".format(sira)
        brans, _, oran, medyan = rnd.choices(BRANSLAR, weights=[b[1] for b in BRANSLAR])[0]
        rucu = round(medyan * rnd.lognormvariate(0, 0.8), 2)
        verilis = _gun(rnd, dt.date(2021, 1, 1), dt.date(2026, 10, 31))
        donemler = _donemler(rnd, liste, brans, verilis, log, dosya_no)
        esas_tarihi = None
        for avukat, bas, bitis in donemler:
            gecikme = rnd.expovariate(1 / avukat["hiz"]) * (4 if rnd.random() < 0.1 else 1)
            aday = bas + dt.timedelta(days=int(gecikme))
            if aday <= KESIT and (bitis is None or aday < bitis):
                esas_tarihi = aday
                break
        hareket, toplam = _hareketler(rnd, dosya_no, rucu, oran, donemler, esas_tarihi, verilis)
        hareketler += hareket
        kod, bakiye = "R11", round(max(0.0, rucu - toplam), 2)
        if toplam >= 0.95 * rucu:
            kod, bakiye = "R06", 0.0
        elif toplam <= 0 and verilis < dt.date(2022, 6, 1) and rnd.random() < 0.3:
            kod = "R12"
        dosyalar.append([dosya_no, brans, kod, rucu, bakiye, verilis])
        if donemler:
            son_avukat[dosya_no] = donemler[-1][0]["kod"]
        if esas_tarihi is None:
            continue
        esas_no = "{}/{}".format(esas_tarihi.year, rnd.randint(1000, 99999))
        esaslar.append([dosya_no, esas_no, "" if rnd.random() < 0.05 else esas_tarihi])
        dolu = rnd.random() < 0.3
        takip.append([dosya_no, "ICRA", esas_no if dolu else "", "",
                      esas_tarihi if dolu else ""])
        surec = _surec(rnd, dosya_no, esas_tarihi, donemler[-1][0])
        if surec:
            surecler.append(surec)
    acik = [(s[0], s[1], s[2]) for s in log if s[4] == "NORMAL" and s[3] is None]
    bekleme = []
    for dosya_no, kod, atama in rnd.sample(acik, min(25, len(acik))):
        bas = atama + dt.timedelta(days=rnd.randint(1, 5))
        if bas < KESIT:
            bekleme.append([dosya_no, kod, bas, bas + dt.timedelta(days=rnd.randint(3, 20))])
    os.makedirs(hedef, exist_ok=True)
    tablolar = [
        ("kaynak_cekirdek_dosya", ["dosya_no", "brans", "rucu_kodu", "rucu_tutari", "acik_bakiye",
                               "rucuya_verilis_tarihi"], dosyalar),
        ("kaynak_cekirdek_atama_log", ["DOSYA_NO", "AV_KOD", "ATAMA_ZAMANI", "IPTAL_ZAMANI",
                                   "ATAMA_NO", "GRUP_KODU", "ATAMA_TIPI"],
         [_log_satiri(rnd, s) for s in log]),
        ("kaynak_cekirdek_takip", ["dosya_no", "takip_tipi", "esas_no", "mahkeme", "islem_tarihi"],
         takip),
        ("kaynak_rapor_tahsilat_hareketi", ["dosya_no", "hareket_tarihi", "tutar", "hareket_turu",
                                            "hareket_no"],
         [[d, t, _tr(m), h, "H-{:07d}".format(i)] for i, (d, t, m, h) in
          enumerate(hareketler, 1)]),
        ("kaynak_rapor_avukat_toplam", ["avukat_kodu", "donem", "tahsilat_toplami", "brans"],
         _rapor_toplam(hareketler, son_avukat, {d[0]: d[1] for d in dosyalar})),
        ("kaynak_degerlendirme_puan", ["avukat_kodu", "degerlendirme_tarihi", "alt_baslik",
                                        "puan", "degerlendiren"], _kalite_davranis(rnd, liste)),
        ("kaynak_degerlendirme_avukat", ["avukat_kodu", "unvan", "calisma_durumu"],
         [[a["kod"], "Büro " + a["kod"], a["durum"]] for a in liste]),
        ("kaynak_dava_takip_esas", ["dosya_no", "esas_no", "kaynak_tarihi"], esaslar),
        ("kaynak_dava_takip_surec", ["dosya_no", "surec_turu", "baslangic_tarihi", "dava_esas_no",
                            "dava_kaynak_tarihi"], surecler),
        ("kaynak_duzeltme_bekleme", ["dosya_no", "avukat_kodu", "baslangic", "bitis"], bekleme)]
    for ad, basliklar, satirlar in tablolar:
        _yaz(hedef, ad, basliklar, satirlar)
    return {ad: len(satirlar) for ad, _, satirlar in tablolar}


if __name__ == "__main__":
    KLASOR = os.path.dirname(os.path.abspath(__file__))
    HEDEF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KLASOR, "veri")
    ADET = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    AVUKAT = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    for AD, SAYI in uret(HEDEF, ADET, AVUKAT).items():
        print("{:<30} {:>7} satır".format(AD, SAYI))
