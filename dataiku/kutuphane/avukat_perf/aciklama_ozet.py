"""'Neden bu puanı aldı?' açıklamasının kısa hâli: sütun başına tek cümle (OZET) ve sütunun
birleşik puanı beklenen düzeye (taban, 75) göre ne kadar yukarı ya da aşağı çektiği (etki).

Etki = ağırlık × (sütun puanı − taban); ağırlıklar bire tamamlandığı için etkilerin toplamı
birleşik puan − tabandır. Etkiler 2 ondalığa en büyük kalanla yuvarlanır; ekrandaki eşitlik
(75 − 5,24 − 0,05 + 2,08 + 1,25 = 73,04) her zaman tutar. Cümleler gösterim içindir; hesabın
adımları KANIT ve HESAP satırlarındadır.
"""
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from avukat_perf import agirlik
from avukat_perf.aciklama_bicim import sabit, sayi
from avukat_perf.params_sema import SUTUNLAR

KURUS = Decimal("0.01")
YAKIN = Decimal("0.5")  # yalnız metin: |etki| bunun altındaysa "beklenen düzeye yakın" yazılır
KISA = {"tahsilat": "tahsilat", "sure": "süre", "kalite": "hukuki kalite",
        "davranis": "davranış"}


def _d(deger):
    return Decimal(repr(float(deger)))


def isaretli(deger):
    """Etki metni: +2,08 / −5,24 (eksi işareti U+2212)."""
    return ("+" if deger > 0 else "−" if deger < 0 else "±") + sayi(abs(float(deger)))


def tl_kisa(deger):
    mutlak = abs(float(deger))
    if mutlak >= 1e6:
        return sayi(deger / 1e6) + " Mn TL"
    if mutlak >= 1e3:
        return sayi(deger / 1e3, 1) + " bin TL"
    return sayi(deger, 0) + " TL"


def _yuzde(pay, payda):
    return None if not payda or float(payda) <= 0 else "%" + sayi(100 * pay / payda, 0)


def _liste(parcalar):
    return parcalar[0] if len(parcalar) == 1 else ", ".join(parcalar[:-1]) + " ve " + parcalar[-1]


def tahsilat(s, tah):
    """Puanı geçerli tahsilat satırı için cümle."""
    cumle = "Tahsilatı, benzer dosyalarda beklenen tutarın {} düzeyinde ({} / {}).".format(
        _yuzde(s.gerceklesen, s.beklenen), tl_kisa(s.gerceklesen), tl_kisa(s.beklenen))
    siklik = _yuzde(s.siklik_o, s.siklik_e)
    guncel = _yuzde(s.guncellik_o, s.guncellik_e)
    if siklik:
        cumle += " Dosyalarında tahsilat yapılan ay sayısı beklenenin {} düzeyinde{}.".format(
            siklik, ", son {} ayda {}".format(sabit(tah["guncellik_pencere_ay"]), guncel)
            if guncel else "")
    return cumle


def sure(s):
    if int(s.o) == 0:
        return "{} dosyada hiç puan düşümü almadı; benzer dosyalarda beklenen {}.".format(
            int(s.risk_dosya), sayi(s.e, 1))
    return "{} dosyada {} puan düşümü aldı; benzer dosyalarda beklenen {}.".format(
        int(s.risk_dosya), int(s.o), sayi(s.e, 1))


def kalite_davranis(s, alt, adlar):
    """alt: avukatın o sütundaki alt başlık satırları (alt_baslik, puan)."""
    cumle = "{} alt başlığın ortalaması.".format(int(s.puanlanan))
    puanli = [] if alt is None else [(float(p), a) for a, p in zip(
        alt["alt_baslik"], alt["puan"]) if p is not None and p == p]
    if len(puanli) < 2:
        return cumle
    en_dusuk = min(p for p, _ in puanli)
    dusukler = [adlar.get(a, a) for p, a in puanli if abs(p - en_dusuk) < 1e-9]
    puan = sayi(en_dusuk).replace(",00", "")
    if len(dusukler) == len(puanli):
        return cumle + " Bütün alt başlıklar aynı puanda ({}).".format(puan)
    if len(dusukler) > 2:  # adlarda "ve" geçtiği için ayraç nokta
        return cumle + " En düşük puan {} ({} alt başlık).".format(puan, len(dusukler))
    return cumle + " En düşük ({}): {}.".format(puan, " · ".join(dusukler))


def etkiler(s, params):
    """Yayımlanan birleşik satırı için sütun başına etki; toplamları birleşik puan − tabandır."""
    agirliklar, taban = agirlik.sutun_agirliklari(params), _d(params["tahsilat"]["taban"])
    etkin = agirlik.etkin_sutunlar(params)
    kesin = {ad: _d(agirliklar[ad]) * (_d(getattr(s, ad)) - taban) for ad in etkin}
    taban_alti = {ad: deger.quantize(KURUS, rounding=ROUND_FLOOR) for ad, deger in kesin.items()}
    artis = int(((_d(s.birlesik_puan) - taban - sum(taban_alti.values())) / KURUS)
                .to_integral_value(rounding=ROUND_HALF_UP))
    if not 0 <= artis <= len(etkin):  # olmamalı; olursa her etki kendi başına yuvarlanır
        return {ad: float(d.quantize(KURUS, rounding=ROUND_HALF_UP)) for ad, d in kesin.items()}
    sira = sorted(etkin, key=lambda ad: -(kesin[ad] - taban_alti[ad]))
    return {ad: float(taban_alti[ad] + (KURUS if ad in sira[:artis] else 0)) for ad in etkin}


def birlesik(s, etki, params):
    """(özet cümlesi, eşitlik) yayımlanan birleşik satırı için."""
    dusuren = sorted((e, ad) for ad, e in etki.items() if _d(e) <= -YAKIN)
    yukselten = sorted(((e, ad) for ad, e in etki.items() if _d(e) >= YAKIN), reverse=True)
    yakin = [KISA[ad] for ad in SUTUNLAR if ad in etki and -YAKIN < _d(etki[ad]) < YAKIN]
    adi = ["{} ({})".format(KISA[ad], isaretli(e)) for e, ad in yukselten]
    cumleler = []
    if dusuren:
        diger = ["{} ({})".format(KISA[ad], isaretli(e)) for e, ad in dusuren[1:]]
        cumleler.append("Puanı en çok {} düşürdü ({}){}.".format(
            KISA[dusuren[0][1]], isaretli(dusuren[0][0]),
            ", ardından " + _liste(diger) if diger else ""))
    if adi:
        cumleler.append(("Puanı " if not dusuren else "") + _liste(adi) + " yükseltti.")
    if yakin:
        cumleler.append(_liste(yakin) + " beklenen düzeye yakın.")
    ozet = " ".join(c[0].upper() + c[1:] for c in cumleler)
    esitlik = "Birleşik puan = {} {} = {} → {}".format(
        sabit(params["tahsilat"]["taban"]),
        " ".join(isaretli(etki[ad]).replace("+", "+ ").replace("−", "− ").replace("±", "+ ")
                 for ad in SUTUNLAR if ad in etki), sayi(s.birlesik_puan), s.performans_notu)
    return ozet, esitlik
