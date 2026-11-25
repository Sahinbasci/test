"""Kurulum adım 2: kütüphane paketi avukat_perf (42 dosya).

araclar/paketle.py üretir; elle değiştirmeyin. Dataiku'da projenin bir Python not
defterine bu dosyanın tamamını yapıştırıp çalıştırın: dosyalar proje kütüphanesine
(Kod > Kütüphaneler > python/avukat_perf) yazılır, aynı adlı dosyanın üzerine yazılır ve geri
okunarak doğrulanır. Sonda "avukat_perf: 42 dosya yazıldı ve doğrulandı" görünmelidir.
"""
import hashlib

import dataiku

PAKET = "avukat_perf"
DOSYALAR = {}

DOSYALAR["__init__.py"] = r'''"""Sözleşmeli Avukat Performans Sistemi: kural ve puan motoru."""

SURUM = "0.3.0"
'''

DOSYALAR["aciklama.py"] = r'''"""'Neden bu puanı aldı?' açıklaması.

Her avukat ve sütun için sıralı satırlar üretir: KANIT (dayanılan veri), HESAP (formül,
gerçek değerlerle), UYARI, ISTISNA (puan üretilmediyse nedeni), OZET (puanı geçerli sütunun
tek cümlelik nedeni; birleşikte puanı neyin düşürüp yükselttiği) ve ESITLIK (birleşik puanın
beklenen düzeyden etkilerle kurulması). OZET satırının etki sütunu, sütunun birleşik puanı
beklenen düzeye göre ne kadar çektiğidir (aciklama_ozet). Yeni satırlar sona eklenir; hesap
adımlarının sırası değişmez. Metinler sonuç tablolarından ve parametrelerden gelir; arayüz hesap
yapmaz. Sayılar Türkçe biçimdedir. Eksik girdi tablosu None verilebilir.
"""
import pandas as pd

from avukat_perf import agirlik, aciklama_ozet
from avukat_perf.aciklama_bicim import (  # noqa: F401
    ETIKET, NEDEN, kesin, kirpma, sabit, sayi, sayim)
from avukat_perf.aciklama_tahsilat import tahsilat as _tahsilat
from avukat_perf.sure_puani import ham_puan


def _kalite_davranis(s):
    """Yeterlilik kararı ve gereken sayı sonuç satırından gelir (kural yalnız çekirdekte)."""
    satirlar = [("KANIT", "Puanlanan alt başlık: {} / {}".format(s.puanlanan, s.toplam)),
                ("HESAP", "Yeterlilik: puanlanan {}, gereken en az {} → {}".format(
                    sabit(s.puanlanan), sabit(s.gereken),
                    "sağlanıyor" if s.durum == "GECERLI" else "sağlanmıyor"))]
    if s.durum != "GECERLI":
        return satirlar + [("ISTISNA", "Eksik değerlendirme: puan üretilmedi.")]
    return satirlar + [("HESAP", "Puan = puanlanan alt başlıkların ortalaması = "
                        + sayi(s.puan))]


def _sure(s, sp):
    satirlar = [("KANIT", "Risk altındaki dönem: {} ({} dosya) · düşüm (O): {} · beklenen "
                 "düşüm (E): {}".format(s.risk_donemi, s.risk_dosya, s.o, sayim(s.e, 4))),
                ("KANIT", "Veri kapsamı: " + ("—" if pd.isna(s.kapsam)
                                               else "%" + sayim(s.kapsam, 1, 100))),
                ("HESAP", "R = ({} + {}) ÷ ({} + {}) = {}".format(
                    s.o, sabit(sp["guven_sabiti"]), kesin(s.e), sabit(sp["guven_sabiti"]),
                    sayi(s.r, 6)))]
    if isinstance(s.eksik_nedeni, str):
        esik = {"AZ_BEKLENEN": sayi(sp["en_az_beklenen"], 1).replace(",0", ""),
                "KAPSAM_DUSUK": "%" + sayi(100 * sp["en_az_kapsam"], 0)}.get(s.eksik_nedeni, "")
        return satirlar + [("ISTISNA", NEDEN[s.eksik_nedeni].format("en az " + esik))]
    if not bool(getattr(s, "yeterli", True)):  # eski tabloda sütun yok: uyarı yazılmaz
        satirlar.insert(2, ("UYARI", "Yeterli veri yok: risk altındaki dönemlerde {} dosya, en az "
                            "{} olmalı. Puan az veriyle hesaplandı; güven ayarı onu beklenen "
                            "düzeye yaklaştırır.".format(s.risk_dosya,
                                                         sayi(sp["yeterli_dosya"], 0))))
    return satirlar + [("HESAP", "Puan = {} + {} × (1 − R) = {}{}".format(
        sabit(sp["taban"]), sabit(sp["egim"]), sayi(s.puan), kirpma(ham_puan(s.r, sp))))]


def _birlesik(s, params, etkiler):
    if s.durum != "YAYIMLANDI":
        eksik = ", ".join(ETIKET[ad] for ad in s.eksik_sutunlar.split(","))
        return [("ISTISNA", "Birleşik puan hesaplanmadı; eksik sütun: " + eksik + ".")]
    agirliklar = agirlik.sutun_agirliklari(params)
    parcalar = " + ".join("{} × {}".format(sayi(agirliklar[ad]), sayi(getattr(s, ad)))
                          for ad in agirlik.etkin_sutunlar(params))
    etkiler[s.avukat_kodu] = etki = aciklama_ozet.etkiler(s, params)
    ozet, esitlik = aciklama_ozet.birlesik(s, etki, params)
    return [("HESAP", "Birleşik puan = {} = {} → {}".format(
        parcalar, sayi(s.birlesik_puan), s.performans_notu)), ("OZET", ozet),
        ("ESITLIK", esitlik)]


def _ozetli(satirlar, s, cumle):
    """Puanı geçerli satıra tek cümlelik özet eklenir."""
    return satirlar + [("OZET", cumle())] if s.durum == "GECERLI" else satirlar


def uret(params, tahsilat=None, kalite_davranis=None, sure=None, birlesik=None,
         kalite_davranis_alt=None):
    """Avukat, sütun ve sıra başına açıklama satırları ve OZET satırlarının etkisi."""
    tah, etkiler = params["tahsilat"], {}
    altlar = {} if kalite_davranis_alt is None else dict(
        list(kalite_davranis_alt.groupby(["avukat_kodu", "sutun"])))
    adlar = params.get("gorunum", {}).get("alt_baslik_adlari", {})
    kaynaklar = [
        (tahsilat, lambda s: "tahsilat", lambda s: _ozetli(
            _tahsilat(s, tah), s, lambda: aciklama_ozet.tahsilat(s, tah))),
        (kalite_davranis, lambda s: s.sutun, lambda s: _ozetli(
            _kalite_davranis(s), s, lambda: aciklama_ozet.kalite_davranis(
                s, altlar.get((s.avukat_kodu, s.sutun)), adlar))),
        (sure, lambda s: "sure", lambda s: _ozetli(
            _sure(s, params["sure_puani"]), s, lambda: aciklama_ozet.sure(s))),
        (birlesik, lambda s: "birlesik", lambda s: _birlesik(s, params, etkiler))]
    satirlar = []
    for tablo, sutun, uretici in kaynaklar:
        for s in ([] if tablo is None else tablo.itertuples()):
            for sira, (tur, metin) in enumerate(uretici(s), 1):
                satirlar.append((s.avukat_kodu, sutun(s), sira, tur, metin))
    tablo = pd.DataFrame(satirlar, columns=["avukat_kodu", "sutun", "sira", "tur", "metin"])
    etki = [etkiler.get(kod, {}).get(sutun) if tur == "OZET" else None
            for kod, sutun, tur in zip(tablo["avukat_kodu"], tablo["sutun"], tablo["tur"])]
    return tablo.assign(etki=pd.Series(etki, index=tablo.index, dtype=float))
'''

DOSYALAR["aciklama_bicim.py"] = r'''"""Açıklama metinlerinin ortak parçaları: neden metinleri ve Türkçe sayı biçimi."""
import math
from decimal import ROUND_FLOOR, Decimal

from avukat_perf.ortak import yuvarla

NEDEN = {
    "AZ_DOSYA": "Puan üretilmedi: dosya sayısı yayın tabanının altında ({}).",
    "BEKLENEN_SIFIR": "Puan üretilmedi: beklenen tahsilat sıfır.",
    "AZ_BEKLENEN": "Puan üretilmedi: beklenen düşüm sayısı yayın tabanının altında ({}).",
    "KAPSAM_DUSUK": "Puan üretilmedi: veri kapsamı yayın tabanının altında ({}).",
    "GOLGE_MOD": "Gölge mod: bayraklar hesaplanıyor, puan yayımlanmıyor.",
}
ETIKET = {"tahsilat": "Tahsilat", "sure": "Süre ve Performans", "kalite": "Hukuki Kalite",
          "davranis": "Davranış ve İletişim"}  # ekrandaki adlarla aynı (uygulama.js SUTUN)


def sayi(deger, ondalik=2):
    """Türkçe sayı metni, yarım yukarı yuvarlanmış; boş değer için uzun çizgi."""
    if deger is None or (isinstance(deger, float) and math.isnan(deger)):
        return "—"
    yuvarlanan = yuvarla(deger, ondalik)
    yuvarlanan = 0.0 if yuvarlanan == 0 else yuvarlanan  # yuvarlanınca sıfır olan eksi: "0,00"
    metin = "{:,.{}f}".format(yuvarlanan, ondalik)
    return metin.replace(",", "_").replace(".", ",").replace("_", ".")


def sabit(deger):
    """Parametre ya da tam sayı sayım: tam sayıysa ondalıksız, değilse gereken kadar ondalık
    (en çok 4); güven sabiti 7,5 verilirse '8' görünmez."""
    if float(deger) == int(deger):
        return sayi(deger, 0)
    return sayi(deger, 4).rstrip("0")


def kesin(deger):
    """Hesaba giren kesirli sayı (ör. elde tutma payıyla olgun dosya): tam sayıysa ondalıksız,
    değilse 6 ondalık; formüldeki sayılarla elle hesap tutsun diye kesilmez."""
    if round(float(deger), 9) == int(round(float(deger), 9)):
        return sayi(deger, 0)
    return sayi(deger, 6)


def sayim(deger, ondalik=2, carpan=1):
    """Eşikle karşılaştırılan sayım (olgun dosya, beklenen düşüm, kapsam × 100) aşağı kesilir:
    tabanın hemen altındaki 19,996 dosya '20,00' görünüp 'en az 20' ile çelişmez. Hesap gibi
    önce 9 ondalığa yuvarlanır (19,999999999999996 dosya tabanı geçer)."""
    if deger is None or (isinstance(deger, float) and math.isnan(deger)):
        return "—"
    kesin = Decimal(repr(round(float(deger), 9))) * carpan
    return sayi(float(kesin.quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_FLOOR)), ondalik)


def kirpma(ham):
    """Kırpılmamış puan 0–100 dışındaysa açıklamaya eklenecek not."""
    return "" if 0 <= ham <= 100 else " (0–100 aralığına kırpıldı)"
'''

DOSYALAR["aciklama_ozet.py"] = r'''"""'Neden bu puanı aldı?' açıklamasının kısa hâli: sütun başına tek cümle (OZET) ve sütunun
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
'''

DOSYALAR["aciklama_tahsilat.py"] = r'''"""'Neden bu puanı aldı?' açıklamasının tahsilat satırları: üç bileşen ve birleşimi."""
from avukat_perf.aciklama_bicim import NEDEN, kesin, kirpma, sabit, sayi, sayim
from avukat_perf.tahsilat_puan import ham_puan, olay_puani, yeterli_mi

# Elle hesap ekrandaki sayılarla tutsun: beklenen 4, R 6 ondalık (R'deki 0,00005'lik yuvarlama
# puanda 0,0025 eder, ikinci ondalığı değiştirebilir); formüldeki n kesilmez, ağırlıklar
# yuvarlanmaz.
BILESEN = (("siklik", "Sıklık", "Olgun dosyalarda tahsilat yapılan dosya-ay"),
           ("guncellik", "Güncellik", "Son {} ayda tahsilat yapılan dosya-ay"))


def _olay(s, ad, baslik, kanit, tah):
    gerceklesen, beklenen = getattr(s, ad + "_o"), getattr(s, ad + "_e")
    r = olay_puani(gerceklesen, beklenen, tah)[0]
    k = sabit(tah["olay_guven_sabiti"])
    return [("KANIT", "{}: {} · beklenen: {} (elde tutulan süre × gruptaki diğer "
                     "avukatların tahsilat hızı)".format(
                kanit.format(tah["guncellik_pencere_ay"]), sabit(gerceklesen),
                sayi(beklenen, 4))),
            ("HESAP", "{} puanı: R = ({} + {}) ÷ ({} + {}) = {} → {}{}".format(
                baslik, sabit(gerceklesen), k, sayi(beklenen, 4), k, sayi(r, 6),
                sayi(getattr(s, "puan_" + ad)), kirpma(ham_puan(r, tah))))]


def tahsilat(s, tah):
    """Tahsilat sonuç satırından (sonuc_tahsilat_avukat) açıklama satırları."""
    k, taban, egim = sabit(tah["guven_sabiti"]), tah["taban"], tah["egim"]
    satirlar = [("KANIT", "Olgun dosya (elde tutma payıyla): " + sayim(s.n)),
                ("KANIT", "Gerçekleşen tahsilat: " + sayi(s.gerceklesen) + " TL"),
                ("KANIT", "Beklenen tahsilat: " + sayi(s.beklenen) + " TL")]
    if isinstance(s.eksik_nedeni, str):
        esik = "en az " + sayi(tah["en_az_olgun_dosya"], 0)
        return satirlar + [("ISTISNA", NEDEN[s.eksik_nedeni].format(esik))]
    if not yeterli_mi(s.n, tah):
        satirlar.append(("UYARI", "Yeterli veri yok: olgun dosya {}, en az {} olmalı. Puan az "
                         "veriyle hesaplandı; güven ayarı onu beklenen düzeye yaklaştırır.".format(
                             sayim(s.n), sayi(tah["yeterli_olgun_dosya"], 0))))
    satirlar += [
        ("HESAP", "Gerçekleşen ÷ beklenen = " + sayi(s.oran, 6)),
        ("HESAP", "R = ({n} × {o} + {k}) ÷ ({n} + {k}) = {r}".format(
            n=kesin(s.n), o=sayi(s.oran, 6), k=k, r=sayi(s.r, 6))),
        ("HESAP", "Tutar puanı = {} + {} × (R − 1) = {}{}".format(
            sabit(taban), sabit(egim), sayi(s.puan_tutar), kirpma(ham_puan(s.r, tah))))]
    for ad, baslik, kanit in BILESEN:
        satirlar += _olay(s, ad, baslik, kanit, tah)
    agirlik = tah["bilesen_agirliklari"]
    return satirlar + [("HESAP", "Tahsilat puanı = {} × {} + {} × {} + {} × {} = {}".format(
        sabit(agirlik["tutar"]), sayi(s.puan_tutar), sabit(agirlik["siklik"]),
        sayi(s.puan_siklik), sabit(agirlik["guncellik"]), sayi(s.puan_guncellik), sayi(s.puan)))]
'''

DOSYALAR["agirlik.py"] = r'''"""Birleşik puanın sütun ağırlıkları: ikili karşılaştırmalardan (Analitik Hiyerarşi Süreci).

params agirliklar: {"a/b": oran}; a sütununun b sütununa göre kaç kat önemli olduğu (1 eşit,
2 iki kat; 0,5 yarısı kadar). Her sütun çifti bir kez yazılır, yönü serbesttir. Ağırlık,
karşılaştırma matrisinin satır geometrik ortalamalarının toplamı 1'e ölçeklenmiş hâlidir.
params birlesik_sutunlar birleşik puana giren sütunlardır (ilk fazda Süre ve Performans girmez);
ağırlıklar yalnız bu sütunların karşılaştırmalarından hesaplanır, girmeyen sütunun ağırlığı 0'dır.
Karşılaştırmalar tutarlıyken bu, çıkarılan sütunun payını diğerlerine oranında dağıtmaktır.
Tutarlılık oranı (CR) = (λmax − n) ÷ (n − 1) ÷ RI (Saaty; üç sütunda 0,58, dörtte 0,90); 0,10'u
aşan karşılaştırmalar kendi içinde çelişkili sayılır (ör. A > B, B > C ama C > A). Ağırlıklar tam
yüzdeye en büyük kalan yöntemiyle yuvarlanır (toplam 100); birleşik puan elle hesaplanabilir.
"""
import math

from avukat_perf.params_sema import SUTUNLAR

RASTGELE_TUTARLILIK = {3: 0.58, 4: 0.90}  # n ölçüt için rastgele matrislerin ortalama tutarsızlığı
EN_COK_TUTARSIZLIK = 0.10
ORAN_SINIRI = 9.0


def etkin_sutunlar(params):
    """Birleşik puana giren sütunlar, SUTUNLAR sırasında."""
    secilen = params.get("birlesik_sutunlar", SUTUNLAR)
    return tuple(ad for ad in SUTUNLAR if ad in secilen)


def _ciftler(karsilastirma, sutunlar=SUTUNLAR):
    """{(i, j): oran} sözlüğü (indeksler sutunlar sırasında) ve hata iletileri. Puana girmeyen
    sütunun çiftleri denetlenir ama hesaba girmez."""
    ciftler, hatalar = {}, []
    for anahtar, oran in karsilastirma.items():
        if str(anahtar).startswith("_"):
            continue
        a, _, b = str(anahtar).partition("/")
        if a not in SUTUNLAR or b not in SUTUNLAR or a == b:
            hatalar.append("agirliklar: bilinmeyen çift " + str(anahtar))
            continue
        gecerli = isinstance(oran, (int, float)) and not isinstance(oran, bool) and \
            1 / ORAN_SINIRI <= oran <= ORAN_SINIRI
        if not gecerli:
            hatalar.append("agirliklar: {} oranı 1/9 ile 9 arasında sayı olmalı".format(anahtar))
            continue
        if a not in sutunlar or b not in sutunlar:
            continue
        i, j = sutunlar.index(a), sutunlar.index(b)
        if (min(i, j), max(i, j)) in ciftler:
            hatalar.append("agirliklar: {} çifti iki kez yazılmış".format(anahtar))
        else:
            ciftler[(min(i, j), max(i, j))] = oran if i < j else 1.0 / oran
    eksik = [sutunlar[i] + "/" + sutunlar[j] for i in range(len(sutunlar))
             for j in range(i + 1, len(sutunlar)) if (i, j) not in ciftler]
    if eksik and not hatalar:
        hatalar.append("agirliklar: eksik çift " + ", ".join(eksik))
    return ciftler, hatalar


def _matris(ciftler, n):
    return [[1.0 if i == j else (ciftler[(i, j)] if i < j else 1.0 / ciftler[(j, i)])
             for j in range(n)] for i in range(n)]


def ham_agirliklar(karsilastirma, sutunlar=SUTUNLAR):
    """Yuvarlanmamış ağırlıklar ve tutarlılık oranı: ({sütun: ağırlık}, CR)."""
    n = len(sutunlar)
    matris = _matris(_ciftler(karsilastirma, sutunlar)[0], n)
    ortalama = [math.exp(sum(math.log(x) for x in satir) / n) for satir in matris]
    agirlik = [deger / sum(ortalama) for deger in ortalama]
    if n < 3:  # bir ya da iki sütunda karşılaştırma her zaman tutarlıdır
        return dict(zip(sutunlar, agirlik)), 0.0
    lam = sum(sum(satir[j] * agirlik[j] for j in range(n)) / agirlik[i]
              for i, satir in enumerate(matris)) / n
    return dict(zip(sutunlar, agirlik)), max(0.0, (lam - n) / (n - 1) / RASTGELE_TUTARLILIK[n])


def hatalar(karsilastirma, sutunlar=SUTUNLAR):
    """Parametre doğrulaması: çiftler eksiksiz ve tekrarsız, oranlar sınırda, CR en çok 0,10."""
    _, iletiler = _ciftler(karsilastirma, sutunlar)
    if iletiler:
        return iletiler
    oran = ham_agirliklar(karsilastirma, sutunlar)[1]
    if oran > EN_COK_TUTARSIZLIK:
        return ["agirliklar: karşılaştırmalar tutarsız (tutarlılık oranı {:.3f} > {:.2f})".format(
            oran, EN_COK_TUTARSIZLIK)]
    return []


def sutun_agirliklari(params):
    """{sütun: ağırlık} bütün sütunlar için; puana girmeyen sütun 0. Tam yüzdeye yuvarlanmış (en
    büyük kalan; eşitlikte SUTUNLAR sırası). Karşılaştırmalar geçersizse ValueError."""
    etkin = etkin_sutunlar(params)
    iletiler = hatalar(params["agirliklar"], etkin)
    if iletiler:
        raise ValueError("; ".join(iletiler))
    ham = ham_agirliklar(params["agirliklar"], etkin)[0]
    yuzde = {ad: ham[ad] * 100 for ad in etkin}
    tam = {ad: int(math.floor(deger + 1e-9)) for ad, deger in yuzde.items()}
    # Kalan 9 ondalığa yuvarlanır: matematiksel olarak eşit iki kalanı kayan nokta artığı ayırmaz.
    kalan = sorted(etkin, key=lambda ad: (-round(yuzde[ad] - tam[ad], 9), SUTUNLAR.index(ad)))
    for ad in kalan[:100 - sum(tam.values())]:
        tam[ad] += 1
    return {ad: tam.get(ad, 0) / 100.0 for ad in SUTUNLAR}

def birlesik_hatalari(params):
    """Birleşik puana giren sütunlar ve ağırlık karşılaştırmaları (bütün sütunlarla ve yalnız
    puana girenlerle; ikisi de tutarlı olmalı)."""
    iletiler = list(hatalar(params["agirliklar"]))
    sutunlar = params.get("birlesik_sutunlar")
    if not isinstance(sutunlar, list) or not sutunlar or len(set(map(str, sutunlar))) != \
            len(sutunlar) or not set(sutunlar) <= set(SUTUNLAR):
        iletiler.append("birlesik_sutunlar: tekrarsız ve boş olmayan sütun listesi olmalı ("
                        + ", ".join(SUTUNLAR) + ")")
    elif not iletiler:
        iletiler += hatalar(params["agirliklar"], etkin_sutunlar(params))
    if params.get("birlesik_puan_kosulu") != "tum_sutunlar":
        iletiler.append("birlesik_puan_kosulu yalnız tum_sutunlar olabilir")
    return iletiler
'''

DOSYALAR["atama.py"] = r'''"""Atama geçmişi: kapsam, kesitte bilinen atama dönemleri, elde tutma payı ve atıf.

Atama dönemi [atama_tarihi, bitis_tarihi) aralığıdır; bitiş günü dosya artık o avukatta
değildir. Sulh amaçlı ve hatalı girilip iptal edilen atamalar kapsam dışıdır. Kapsamdaki
dönemler aynı dosyada çakışamaz; yeniden atamada önceki dönemin bitişi veri hazırlığında
yazılır.
"""
import math

import pandas as pd

from avukat_perf.ortak import (BIR_GUN, anahtar_kontrol, bos_kontrol, gun, sutun_kontrol,
                               tek_gun)

SUTUNLAR = ("dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi", "bitis_nedeni",
            "atama_turu")
ANAHTAR = ("dosya_no", "avukat_kodu", "atama_tarihi")


def kapsam_belirle(atamalar):
    """Sulh amaçlı ve hatalı girilip iptal edilen atamalara neden yazar; satır silmez."""
    tablo = atamalar.copy()
    neden = pd.Series(None, index=tablo.index, dtype=object)
    neden.loc[tablo["bitis_nedeni"] == "IPTAL"] = "IPTAL"
    neden.loc[tablo["atama_turu"] == "SULH"] = "SULH"
    tablo["kapsam_disi_nedeni"] = neden
    return tablo


def donemler(atamalar, kesit):
    """Kesitte bilinen, kapsamdaki atama dönemleri; kesitten sonraki bitiş boş sayılır."""
    sutun_kontrol(atamalar, SUTUNLAR, "atamalar")
    bos_kontrol(atamalar, ANAHTAR, "atamalar")
    kesit = tek_gun(kesit)
    tablo = kapsam_belirle(atamalar).assign(atama_tarihi=gun(atamalar["atama_tarihi"]),
                                            bitis_tarihi=gun(atamalar["bitis_tarihi"]))
    anahtar_kontrol(tablo[tablo["kapsam_disi_nedeni"].isna()], ANAHTAR, "atamalar")
    secili = tablo["kapsam_disi_nedeni"].isna() & (tablo["atama_tarihi"] <= kesit)
    tablo = tablo.loc[secili, list(SUTUNLAR[:4])]
    tablo = tablo.assign(bitis_tarihi=tablo["bitis_tarihi"].where(tablo["bitis_tarihi"] <= kesit))
    tablo = tablo[~(tablo["bitis_tarihi"] <= tablo["atama_tarihi"])]  # boş dönem: tutulan gün yok
    tablo = tablo.sort_values(["dosya_no", "atama_tarihi"]).reset_index(drop=True)
    onceki_bitis = tablo.groupby("dosya_no")["bitis_tarihi"].shift()
    onceki_acik = tablo.duplicated("dosya_no") & onceki_bitis.isna()
    cakisma = onceki_acik | (tablo["atama_tarihi"] < onceki_bitis)
    if cakisma.any():
        raise ValueError("atamalar: kapsamdaki {} dönem öncekiyle çakışıyor".format(
            int(cakisma.sum())))
    return tablo


def tutulan_gunler(donem, baslangiclar, kesit):
    """(dosya, avukat) başına [baslangic, kesit] içinde dosyanın elde tutulduğu gün sayısı ve
    dosyanın aralıkta ilk tutulduğu gün (ilk). Aralıkta dosyayı hiç tutmamış avukat sonuca girmez.

    baslangiclar: dosya_no, baslangic.
    """
    sinir = tek_gun(kesit) + BIR_GUN
    tablo = donem.merge(baslangiclar, on="dosya_no")
    bas = tablo["atama_tarihi"].where(tablo["atama_tarihi"] >= tablo["baslangic"],
                                      tablo["baslangic"])
    son = tablo["bitis_tarihi"].fillna(sinir)
    son = son.where(son <= sinir, sinir)
    tablo = tablo.assign(gun=(son - bas).dt.days.clip(lower=0), ilk=bas)
    tablo = tablo[tablo["gun"] > 0]
    tablo = tablo.assign(ilk=tablo.groupby("dosya_no")["ilk"].transform("min"))
    return tablo.groupby(["dosya_no", "avukat_kodu", "ilk"], as_index=False)["gun"].sum()


def elde_tutma_paylari(donem, baslangiclar, kesit, payda):
    """Dosya başına avukatların elde tutma payı; gün sayısı [baslangic, kesit] içinde sayılır.

    payda ilk_atamadan: avukatın günü ÷ dosyanın aralıktaki ilk atamasından kesite kadarki gün;
    iade sonrası ve iki atama arasındaki boşluk hiçbir avukata yazılmaz (kısa süre tutulup iade
    edilen dosya beklentiye tam dosya girmez), tek avukatın tuttuğu dosya 1 sayılır. payda
    avukat_gunleri: avukatın günü ÷ avukatların günleri toplamı; paylar toplamı 1'dir.
    """
    tablo = tutulan_gunler(donem, baslangiclar, kesit)
    bolen = ((tek_gun(kesit) + BIR_GUN - tablo["ilk"]).dt.days if payda == "ilk_atamadan"
             else tablo.groupby("dosya_no")["gun"].transform("sum"))
    tablo = tablo.assign(pay=tablo["gun"] / bolen)
    return tablo[["dosya_no", "avukat_kodu", "pay"]].reset_index(drop=True)


def hareket_atfet(hareketler, donem, kesit):
    """Her hareketi, hareket tarihinde dosyayı elinde tutan avukata yazar.

    Kesitten sonraki hareket alınmaz. Kapsamdaki bir döneme düşmeyen hareketin
    avukat_kodu boş kalır: bu tutar avukata yazılamayan tahsilattır.
    """
    zorunlu = ("dosya_no", "hareket_tarihi", "tutar")
    sutun_kontrol(hareketler, zorunlu, "hareketler")
    bos_kontrol(hareketler, zorunlu, "hareketler")
    tablo = hareketler[list(zorunlu)].assign(hareket_tarihi=gun(hareketler["hareket_tarihi"]),
                                             tutar=hareketler["tutar"].astype(float))
    try:
        toplam = math.fsum(tablo["tutar"].abs())
    except OverflowError:
        toplam = float("inf")
    if not math.isfinite(toplam):
        raise ValueError("hareketler: tutar sonlu değil ya da toplam sayısal aralığı aşıyor")
    tablo = tablo[tablo["hareket_tarihi"] <= tek_gun(kesit)].reset_index(drop=True)
    eslesme = tablo[["dosya_no", "hareket_tarihi"]].reset_index().merge(
        donem[["dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi"]], on="dosya_no")
    tarih = eslesme["hareket_tarihi"]
    icinde = (tarih >= eslesme["atama_tarihi"]) & (
        eslesme["bitis_tarihi"].isna() | (tarih < eslesme["bitis_tarihi"]))
    avukat = eslesme.loc[icinde].set_index("index")["avukat_kodu"]
    # Hiçbir hareket eşleşmese de sütun metin türünde kalır (birleştirmeler tür uyuşmazlığına
    # düşmez).
    return tablo.assign(avukat_kodu=pd.Series(tablo.index.map(avukat), index=tablo.index,
                                              dtype=object))
'''

DOSYALAR["bayrak.py"] = r'''"""Bayrak, düşüm ve KIRMIZI kuralı: Kriter 1 ve Kriter 2'de ortaktır.

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
'''

DOSYALAR["bekleme.py"] = r'''"""Haklı bekleme: avukattan kaynaklanmayan, Şirket'in uygun gördüğü bekleme süreleri.

Kayıtlar düzeltme tablosundan gelir. Başlangıç ve bitiş günü dahildir. Bitişi boş ya da
kesitten sonra olan bekleme kesitte kesilir; kesitten sonra başlayan bekleme sayılmaz.
Aralıklar [başlangıç, bitiş + 1 gün) biçiminde tutulur.
"""
from avukat_perf.ortak import BIR_GUN, bos_kontrol, gun, sutun_kontrol

SUTUNLAR = ("dosya_no", "avukat_kodu", "baslangic", "bitis")


def araliklar(beklemeler, kesit):
    """(dosya_no, avukat_kodu) başına çakışmaları birleştirilmiş, sıralı aralıklar."""
    sonuc = {}
    if beklemeler is None or beklemeler.empty:
        return sonuc
    sutun_kontrol(beklemeler, SUTUNLAR, "beklemeler")
    bos_kontrol(beklemeler, ("dosya_no", "avukat_kodu", "baslangic"), "beklemeler")
    tablo = beklemeler.assign(baslangic=gun(beklemeler["baslangic"]),
                              bitis=gun(beklemeler["bitis"]))
    tablo = tablo[tablo["baslangic"] <= kesit]
    if (tablo["bitis"] < tablo["baslangic"]).any():
        raise ValueError("beklemeler: bitişi başlangıcından önce olan satır var")
    tablo = tablo.assign(bitis=tablo["bitis"].fillna(kesit)).sort_values("baslangic")
    for anahtar, grup in tablo.groupby(["dosya_no", "avukat_kodu"]):
        birlesik = []
        for bas, son in zip(grup["baslangic"], grup["bitis"]):
            son = min(son, kesit) + BIR_GUN
            if birlesik and bas <= birlesik[-1][1]:
                birlesik[-1][1] = max(birlesik[-1][1], son)
            else:
                birlesik.append([bas, son])
        sonuc[anahtar] = birlesik
    return sonuc


def kaydir(esik, atama, aralik_listesi):
    """Atamadan sonra ve eşikten önce başlayan bekleme günleri kadar eşiği ileri atar.

    Kaydırma yeni eşiğin önüne düşen sonraki beklemeyi de sayar; liste sıralı olmalıdır.
    """
    for bas, son in aralik_listesi:
        bas = max(bas, atama)
        if bas < esik and son > bas:
            esik = esik + (son - bas)
    return esik


def gun_sayisi(atama, olcum_sonu, aralik_listesi):
    """[atama, olcum_sonu) içine düşen bekleme günü sayısı."""
    toplam = 0
    for bas, son in aralik_listesi:
        toplam += max((min(son, olcum_sonu) - max(bas, atama)).days, 0)
    return toplam
'''

DOSYALAR["birlesik.py"] = r'''"""Birleşik puan, performans notu ve genel sıralama.

Girdi uzun biçimdedir: avukat_kodu, sutun, puan, durum (puan_donem tablosundaki gibi).
Birleşik puana giren sütunlar params birlesik_sutunlar'dır (ilk fazda Süre ve Performans
girmez; ağırlıklar agirlik.py). Giren sütunların hepsi GECERLI olan avukat için birleşik puan
hesaplanır. Biri eksikse birleşik puan, not ve sıra yayımlanmaz; ağırlık diğer sütunlara
dağıtılmaz, eksik puan sıfır sayılmaz. Girmeyen sütunun puanı tabloda bilgi olarak durur.
Sütun puanları 2 ondalığa yuvarlanır; ağırlıklı toplam ondalık aritmetikle hesaplanıp yine 2
ondalığa yuvarlanır. Yuvarlama elle hesaptaki gibi yarım
yukarıdır; not yuvarlanmış puana göre verilir, böylece ekrandaki sayı ile not tutarlıdır.
Eşit puan aynı sırayı alır (1, 2, 2, 4); sıralama yalnız yayımlananlar arasındadır.
"""
from decimal import Decimal

import pandas as pd

from avukat_perf.ortak import (anahtar_kontrol, bos_kontrol, ondalik_yuvarla, sutun_kontrol,
                               yuvarla)
from avukat_perf import agirlik
from avukat_perf.params_sema import SUTUNLAR

GIRDI = ("avukat_kodu", "sutun", "puan", "durum")


def not_ver(puan, notlar):
    """Puanın eşiğine ulaştığı ilk not; notlar yüksekten düşüğe [ad, eşik] listesidir.

    Puan boşsa (NaN) hiçbir eşiğe ulaşmaz, sonuç None olur.
    """
    for ad, esik in notlar:
        if puan >= esik:
            return ad
    return None


def _gecerli_puanlar(sutun_puanlari):
    """GECERLI satırlar, puanı 2 ondalığa yuvarlanmış olarak."""
    sutun_kontrol(sutun_puanlari, GIRDI, "sutun_puanlari")
    bos_kontrol(sutun_puanlari, ("avukat_kodu", "sutun", "durum"), "sutun_puanlari")
    anahtar_kontrol(sutun_puanlari, ("avukat_kodu", "sutun"), "sutun_puanlari")
    if not sutun_puanlari["sutun"].isin(SUTUNLAR).all():
        raise ValueError("sutun_puanlari: tanımsız sütun adı var")
    gecerli = sutun_puanlari[sutun_puanlari["durum"] == "GECERLI"]
    puan = gecerli["puan"].astype(float)
    if (puan.isna() | (puan < 0) | (puan > 100)).any():
        raise ValueError("sutun_puanlari: GECERLI satırda puan boş ya da 0-100 dışında")
    return gecerli.assign(puan=puan.map(yuvarla))


def agirlikli_toplam(puanlar, agirliklar):
    """Σ ağırlık × puan, ondalık aritmetikle ve 2 ondalığa yarım yukarı: elle hesapla aynı.

    Kayan noktayla 0,35 × 85 + 0,25 × 85,58 + 0,30 × 84,5 + 0,10 × 85 = 84,9949… çıkar ve
    84,99 olurdu; doğru sonuç 84,995 → 85,00'tır.
    """
    toplam = sum(Decimal(repr(float(agirliklar[ad]))) * Decimal(repr(float(puan)))
                 for ad, puan in puanlar.items())
    return ondalik_yuvarla(toplam)


def birlestir(sutun_puanlari, params):
    """Avukat başına sütun puanları, birleşik puan, not, genel sıra ve yayın durumu."""
    gecerli = _gecerli_puanlar(sutun_puanlari)
    avukatlar = sorted(sutun_puanlari["avukat_kodu"].unique())
    genis = gecerli.pivot(index="avukat_kodu", columns="sutun", values="puan")
    genis = genis.reindex(index=avukatlar, columns=list(SUTUNLAR))
    etkin = list(agirlik.etkin_sutunlar(params))
    eksik = genis[etkin].isna()
    tam = ~eksik.any(axis=1)
    agirliklar = agirlik.sutun_agirliklari(params)
    birlesik = pd.Series([agirlikli_toplam(satir[etkin], agirliklar) if tamam else None
                          for (_, satir), tamam in zip(genis.iterrows(), tam)],
                         index=genis.index, dtype=float)
    sonuc = genis.assign(
        birlesik_puan=birlesik,
        performans_notu=[not_ver(puan, params["notlar"]) for puan in birlesik],
        genel_sira=birlesik.rank(method="min", ascending=False),
        durum=tam.map({True: "YAYIMLANDI", False: "EKSIK_SUTUN"}),
        eksik_sutunlar=[",".join(ad for ad in etkin if satir[ad])
                        for _, satir in eksik.iterrows()])
    return sonuc.rename_axis(columns=None).reset_index()
'''

DOSYALAR["donem.py"] = r'''"""Dönem sonu: kesit, dönem puan tablosu, sonuç kontrolleri ve sürümlü yayın.

Dönem YYYY-AA biçimindedir; kesit dönemin son günüdür. Dönem puan tablosu uzun biçimdedir
(avukat, dönem, sütun, puan, durum). Kaynağı henüz gelmeyen sütun KAYNAK_BEKLENIYOR,
kaynağı gelip o avukatı içermeyen sütun VERI_YOK durumundadır.
Yayımlanan dönem değiştirilmez: aynı dönem yeniden yayımlanırken içerik ve hesap sürümü
(kurallar) aynıysa tablo değişmez (DEGISMEDI), biri farklıysa yeni yayın sürümü eklenir
(DUZELTME). Birleşik puan da yayın anında, o sürümün kurallarıyla bir kez hesaplanır ve
sürümüyle saklanır (surum_ekle). Arayüz son sürümü okur.
"""
import re

import pandas as pd

from avukat_perf.kalite import SONUC
from avukat_perf.ortak import birlestir, yuvarla
from avukat_perf.params_sema import SUTUNLAR

ICERIK = ["avukat_kodu", "sutun", "puan", "durum"]
SIRA = ["avukat_kodu", "donem", "sutun", "puan", "durum"]


def kesit(donem):
    """'2026-10' -> 2026-10-31."""
    if not re.match(r"^\d{4}-\d{2}$", str(donem)):
        raise ValueError("dönem YYYY-AA biçiminde olmalı")
    return (pd.Timestamp(donem + "-01") + pd.offsets.MonthEnd(1)).normalize()


def onceki_donem(tarih):
    """Tarihten bir önceki takvim ayı: 2026-11-01 -> '2026-10'."""
    return (pd.Timestamp(tarih).normalize().replace(day=1) - pd.Timedelta(days=1)).strftime(
        "%Y-%m")


def veri_kapsami(son_cekim, donem):
    """Dönem sonunu kapsayan başarılı gecelik çekim var mı (kesitten sonraki bir günde)."""
    eski = son_cekim is None or pd.Timestamp(son_cekim).normalize() <= kesit(donem)
    aciklama = "son başarılı gecelik çekim: {}".format(
        "yok" if son_cekim is None else pd.Timestamp(son_cekim).date())
    return pd.DataFrame([("donem", "VERI_KAPSAMI", "KALDI" if eski else "GECTI", int(eski), 0,
                          aciklama)], columns=SONUC)


def puan_tablosu(donem, sutun_tablolari, avukatlar, bekleme_nedeni=None):
    """sutun_tablolari: {sütun: (avukat_kodu, puan, durum) tablosu ya da None}.

    bekleme_nedeni: tablosu None olan sütunun durumu (varsayılan KAYNAK_BEKLENIYOR;
    ör. değerlendirme ölçeği teyit beklerken TEYIT_BEKLIYOR).
    """
    parcalar = []
    for sutun in SUTUNLAR:
        tablo = sutun_tablolari.get(sutun)
        durum = (bekleme_nedeni or {}).get(sutun, "KAYNAK_BEKLENIYOR") if tablo is None \
            else "VERI_YOK"
        parca = pd.DataFrame(columns=["avukat_kodu", "puan", "durum"]) if tablo is None \
            else tablo[["avukat_kodu", "puan", "durum"]]
        eksik = sorted(set(avukatlar) - set(parca["avukat_kodu"]))
        ek = pd.DataFrame({"avukat_kodu": eksik, "puan": float("nan"), "durum": durum})
        parca = birlestir([parca, ek], ["avukat_kodu", "puan", "durum"])
        parcalar.append(parca.assign(sutun=sutun))
    tablo = pd.concat(parcalar, ignore_index=True).assign(donem=donem)
    tablo["puan"] = tablo["puan"].astype(float)
    return tablo[SIRA].sort_values(["avukat_kodu", "sutun"]).reset_index(drop=True)


def sonuc_kontrolleri(tablo):
    """Yayından önce: puan aralığı, sütun tamlığı ve anahtar tekilliği (KALDI ise yayın yok)."""
    gecerli = tablo[tablo["durum"] == "GECERLI"]["puan"]
    aralik_disi = int((gecerli.isna() | (gecerli < 0) | (gecerli > 100)).sum())
    # Her avukatın sütunları tam olarak dört sütun adıdır (sayı değil ad karşılaştırılır).
    kume = tablo.groupby("avukat_kodu")["sutun"].agg(lambda s: frozenset(s))
    eksik_sutun = int((kume != frozenset(SUTUNLAR)).sum())
    yinelenen = int(tablo.duplicated(["avukat_kodu", "donem", "sutun"]).sum())
    satirlar = [("sonuc", "PUAN_ARALIGI", aralik_disi), ("sonuc", "SUTUN_TAMLIGI", eksik_sutun),
                ("sonuc", "YINELENEN", yinelenen)]
    return pd.DataFrame([(k, ad, "GECTI" if deger == 0 else "KALDI", deger, 0, "")
                         for k, ad, deger in satirlar], columns=SONUC)


def _icerik(tablo):
    """Puan, birleşik puanın ve notun kullandığı değerle (2 ondalık, yarım yukarı)."""
    secili = tablo[ICERIK].sort_values(["avukat_kodu", "sutun"]).reset_index(drop=True)
    return secili.assign(puan=secili["puan"].astype(float).map(yuvarla))


def yayinla(mevcut, yeni, donem, ek_bilgi):
    """(tablo, sonuç). ek_bilgi: calisma_kimligi, hesap_surumu, yayin_zamani sözlüğü."""
    yeni = yeni.assign(**ek_bilgi)
    if mevcut is None or mevcut.empty:
        return yeni.assign(yayin_surumu=1), "YENI"
    onceki = mevcut[mevcut["donem"] == donem]
    if onceki.empty:
        return pd.concat([mevcut, yeni.assign(yayin_surumu=1)], ignore_index=True), "YENI"
    son = onceki[onceki["yayin_surumu"] == onceki["yayin_surumu"].max()]
    ayni_kural = set(son["hesap_surumu"]) == {ek_bilgi["hesap_surumu"]}
    if ayni_kural and _icerik(son).equals(_icerik(yeni)):
        return mevcut, "DEGISMEDI"
    surum = int(onceki["yayin_surumu"].max()) + 1
    return pd.concat([mevcut, yeni.assign(yayin_surumu=surum)], ignore_index=True), "DUZELTME"


def surum_ekle(mevcut, yeni, donem, surum):
    """Bir dönemin yeni yayın sürümünün satırlarını ekler; önceki sürümlere dokunmaz.

    Aynı dönem ve sürümde, yarıda kesilmiş bir denemeden kalan satırlar önce çıkarılır.
    """
    if mevcut is None or mevcut.empty:
        return yeni.reset_index(drop=True)
    kalan = mevcut[~((mevcut["donem"] == donem) & (mevcut["yayin_surumu"] == surum))]
    return pd.concat([kalan, yeni], ignore_index=True)


def son_surum(tablo):
    """Her dönemin son yayın sürümü."""
    if tablo is None or tablo.empty:
        return tablo
    en_son = tablo.groupby("donem")["yayin_surumu"].transform("max")
    return tablo[tablo["yayin_surumu"] == en_son].reset_index(drop=True)
'''

DOSYALAR["gozlem.py"] = r'''"""Gözlem: gecelik anlık görüntülerden bir alanın ilk dolu görüldüğü günü sabitler.

Kaynak sistem bir alanın ilk giriş tarihini tutmuyorsa (ör. dava takip esas numarası) her gece
alınan görüntü bu tarihi bizim tarafta sabitler. Bir anahtarın değeri ilk kez dolu
görüldüğünde satır eklenir; değer sonra değişse de satır değişmez (yalnız ekleme).
Tarih avukat lehine en erken olası gündür: önceki başarılı çekimin günü. Çekim gece (02:00)
yapıldığı için önceki çekimde görülmeyen değer o günün geri kalanında girilmiş olabilir.
Kaynak tarihi (ör. dava takip sisteminin takip tarihi) [önceki çekim günü, bu çekim günü]
aralığına düşüyorsa o kullanılır (dayanak KAYNAK_TARIHI). Kaçan gece bu yüzden avukatın
aleyhine işlemez. İlk çekimde zaten dolu olan değer arşiv öncesidir: çekimden önceki bir kaynak
tarihi varsa o, yoksa tarih bilinmiyor; ilk_gorulme o zaman değerin en geç hangi gün var
olduğunu gösterir.
"""
import pandas as pd

from avukat_perf.ortak import birlestir, gun, tek_gun

SUTUNLAR = ["anahtar", "ilk_deger", "ilk_gorulme", "onceki_basarili_cekim", "ilk_tarih",
            "dayanak", "tarih_bilinmiyor"]


def bos():
    """Boş gözlem tablosu."""
    return pd.DataFrame(columns=SUTUNLAR)


def guncelle(mevcut, goruntu, anahtar, deger, cekim_tarihi, onceki_basarili=None,
             kaynak_tarihi=None):
    """Görüntüde değeri ilk kez dolu görülen anahtarlar için satır ekler.

    onceki_basarili: bir önceki başarılı çekimin günü; None ise bu ilk çekimdir.
    kaynak_tarihi: görüntüde kaynak sistemin verdiği tarih sütununun adı (isteğe bağlı).
    """
    mevcut = bos() if mevcut is None else mevcut
    cekim = tek_gun(cekim_tarihi)
    metin = goruntu[deger].astype(str).str.strip()
    dolu = goruntu[goruntu[deger].notna() & (metin != "")].drop_duplicates(anahtar)
    yeni = dolu[~dolu[anahtar].isin(set(mevcut["anahtar"]))]
    if yeni.empty:
        return mevcut
    kaynak = (gun(yeni[kaynak_tarihi], zorla=True) if kaynak_tarihi
              else pd.Series(pd.NaT, index=yeni.index))
    if onceki_basarili is None or pd.isna(onceki_basarili):
        onceki, dayanak = pd.NaT, "ARSIV_ONCESI"
        ilk = kaynak.where(kaynak <= cekim)
    else:
        onceki = tek_gun(onceki_basarili)
        aralikta = (kaynak >= onceki) & (kaynak <= cekim)
        ilk = kaynak.where(aralikta, onceki)
        dayanak = aralikta.map({True: "KAYNAK_TARIHI", False: "GECELIK_GOZLEM"}).values
    satirlar = pd.DataFrame({
        "anahtar": yeni[anahtar].values, "ilk_deger": yeni[deger].astype(str).values,
        "ilk_gorulme": cekim, "onceki_basarili_cekim": onceki,
        "ilk_tarih": pd.to_datetime(ilk.values), "dayanak": dayanak})
    satirlar["tarih_bilinmiyor"] = tarih_bilinmiyor(satirlar)
    return birlestir([mevcut, satirlar], SUTUNLAR)


def tarih_bilinmiyor(gozlem_tablosu):
    """İlk giriş günü bilinmeyen (arşiv öncesi) satırlar (bool Series): işaretin tek tanımı.
    Saklanan tarih_bilinmiyor sütunu bilgi içindir; okunurken türü yorumlanmaz."""
    return pd.to_datetime(gozlem_tablosu["ilk_tarih"]).isna()


def tarih_esle(gozlem_tablosu):
    """anahtar -> ilk_tarih eşlemesi (Series); tablo yoksa boş."""
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    return pd.to_datetime(gozlem_tablosu.set_index("anahtar")["ilk_tarih"])


def baslangic_esle(gozlem_tablosu):
    """anahtar -> başlangıç olarak kullanılacak en geç olası ilk giriş günü.

    ilk_tarih bitiş için avukat lehine en erken gündür; başlangıçta en erken gün avukatın
    aleyhinedir (eşikler öne çekilir). Kaynak tarihi aralıktaysa o, değilse değerin görüldüğü
    çekim günü kullanılır.
    """
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    tablo = gozlem_tablosu
    ilk = pd.to_datetime(tablo["ilk_tarih"])
    kaynak = ilk.notna() & tablo["dayanak"].isin(["ARSIV_ONCESI", "KAYNAK_TARIHI"])
    deger = ilk.where(kaynak, pd.to_datetime(tablo["ilk_gorulme"]))
    return pd.Series(deger.values, index=tablo["anahtar"].values)


def bilinmeyen_esle(gozlem_tablosu):
    """Değeri var ama ilk giriş günü bilinmeyen (arşiv öncesi) anahtarlar -> ilk görüldüğü
    çekim günü; değer en geç o gün vardı. Tablo yoksa boş."""
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    secili = gozlem_tablosu[tarih_bilinmiyor(gozlem_tablosu).values]
    return pd.to_datetime(secili.set_index("anahtar")["ilk_gorulme"])


def kapanislar(gozlem_tablosu, kesit):
    """Koşul gözleminden kesitte tahsile kapalı dosyaların kapanış günü (Series, indeks dosya_no;
    arşiv öncesi kapanmış, günü bilinmeyen dosyada NaT). Kesitten sonra kapanan açık sayılır.

    Tahsilatta avukat lehine gün en geç olası gündür (kapanışın görüldüğü çekim günü): araya
    kaçan gece girse de dosyayı kapatan tahsilat sıklık ve güncellikte sayılır. Kriter 2 bitişi
    en erken günü kullanır (tarih_esle).
    """
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    tablo = gozlem_tablosu
    ilk = pd.to_datetime(tablo["ilk_tarih"])
    gun = ilk.where(tablo["dayanak"] != "GECELIK_GOZLEM", pd.to_datetime(tablo["ilk_gorulme"]))
    secili = ilk.isna() | (ilk <= tek_gun(kesit))
    return pd.Series(gun[secili].values, index=tablo.loc[secili, "anahtar"].values)
'''

DOSYALAR["hazirlik.py"] = r'''"""Veri hazırlığı: kaynak tablolarından hesap girdilerinin kurulması (hazirlik parametreleri).

atama_donemleri: çekirdek sistemin avukat logundan atama dönemleri. Sulh amaçlı atama avukat
kodu listesinden ya da alan-değer eşleşmesinden tanınır. Bitiş, iptal tarihi ile dosyadaki
sonraki sulh dışı atamanın erkenidir. iptal_yorumu sonraki_atamaya_gore: sonraki atama varsa
YENIDEN_ATAMA, yoksa IADE; hatali_iptal: iptal tarihli her atama IPTAL (kapsam dışı). Kayıtlar
saatiyle sıralanır (aynı gün yeniden atamada dosya sonraki avukattadır), tarihler güne indirilir;
bitişi atama gününde ya da önce olan boş dönem çıkarılır. Aynı avukata kesintisiz yeniden
atamada (ayni_avukata_yeniden_atama) surer: dönem sürer; yeni_donem: yeni dönem açılır.
Geniş biçimli değerlendirme uzun biçime çevrilir. Kriter 2 süreçlerinde boş arabuluculuk
başlangıcı esasın en geç olası ilk giriş günüdür (bkz. gozlem.baslangic_esle).
"""
import pandas as pd

from avukat_perf import gozlem
from avukat_perf.kriter2 import ARABULUCULUK, SUREC_SUTUNLARI

DONEM_SUTUNLARI = ["dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi",
                   "bitis_nedeni", "atama_turu", "atama_ref"]


def atama_donemleri(atama_log, hz):
    """Çekirdek sistemin avukat logundan atama dönemi tablosu."""
    tablo = atama_log.sort_values(["dosya_no", "atama_tarihi", "avukat_kodu", "iptal_tarihi",
                                   "atama_ref"], na_position="last", kind="mergesort")
    tablo = tablo.reset_index(drop=True)
    sulh = tablo["avukat_kodu"].isin(hz["sulh_avukat_kodlari"])
    if hz["sulh_alani"]:
        sulh = sulh | tablo[hz["sulh_alani"]].isin(hz["sulh_degerleri"])
    iptal = tablo["iptal_tarihi"]
    hatali = hz["iptal_yorumu"] == "hatali_iptal"
    # Hatalı girilip iptal edilen atama önceki atamanın dönemini kesmez.
    sayilan = ~sulh & ~(iptal.notna() & hatali)
    sonraki = tablo[sayilan].groupby("dosya_no")["atama_tarihi"].shift(-1).reindex(tablo.index)
    bitis = iptal.where(sonraki.isna() | (iptal.notna() & (iptal <= sonraki)), sonraki)
    if hatali:
        neden = iptal.notna().map({True: "IPTAL", False: "YENIDEN_ATAMA"})
    else:
        neden = sonraki.notna().map({True: "YENIDEN_ATAMA", False: "IADE"})
    tablo = tablo.assign(atama_tarihi=pd.to_datetime(tablo["atama_tarihi"]).dt.normalize(),
                         bitis_tarihi=pd.to_datetime(bitis).dt.normalize(),
                         bitis_nedeni=neden.where(bitis.notna()),
                         atama_turu=sulh.map({True: "SULH", False: "NORMAL"}))
    bos = tablo["bitis_tarihi"].notna() & (tablo["bitis_tarihi"] <= tablo["atama_tarihi"])
    tablo = tablo.loc[~bos, DONEM_SUTUNLARI].reset_index(drop=True)
    return _surdur(tablo) if hz["ayni_avukata_yeniden_atama"] == "surer" else tablo


def _surdur(tablo):
    """Aynı avukata kesintisiz yeniden atamada dönemleri birleştirir; bitiş son kayıttan gelir.
    Sulh dönemi ve hatalı girilip iptal edilen kayıt (IPTAL) araya girmez, dönemi kesmez."""
    normal = tablo[(tablo["atama_turu"] == "NORMAL") & (tablo["bitis_nedeni"] != "IPTAL")]
    # Önceki dönem bu kaydın atamasıyla bitiyorsa (bitiş nedeni o zaman YENIDEN_ATAMA) kesinti yok.
    onceki = normal.groupby("dosya_no")[["avukat_kodu", "bitis_tarihi"]].shift(1)
    surer = ((normal["avukat_kodu"] == onceki["avukat_kodu"])
             & (onceki["bitis_tarihi"] == normal["atama_tarihi"]))
    son = normal.index.to_series().groupby((~surer).cumsum().values).transform("max")[~surer]
    tablo = tablo.copy()
    for sutun in ("bitis_tarihi", "bitis_nedeni"):
        tablo.loc[son.index, sutun] = tablo.loc[son.values, sutun].values
    return tablo.drop(surer[surer].index).reset_index(drop=True)


def degerlendirme_uzun(tablo, alan_kod):
    """Değerlendirme sisteminin geniş tablosunu (alan adı -> alt başlık kodu) uzun biçime alır."""
    if "degerlendiren" not in tablo.columns:
        tablo = tablo.assign(degerlendiren=None)
    kimlik = ["avukat_kodu", "degerlendirme_tarihi", "degerlendiren"]
    uzun = tablo.melt(id_vars=kimlik, value_vars=list(alan_kod), var_name="alt_baslik",
                      value_name="puan")
    return uzun.assign(alt_baslik=uzun["alt_baslik"].map(alan_kod))


def tahsilat_hareketleri(tablo, hz):
    """Yalnız tahsilat sayılan hareket türleri; parametre null ise hepsi."""
    turler = hz["tahsilat_hareket_turleri"]
    return tablo if turler is None else tablo[tablo["hareket_turu"].isin(turler)]


def k1_atamalari(donemler, dosya):
    """Kriter 1 girdisi: atama dönemleri ve dosyanın branşı."""
    return donemler.merge(dosya[["dosya_no", "brans"]], on="dosya_no", how="left")


def k1_esaslari(esas_gozlem):
    """Kriter 1 girdisi: dosya başına esasın ilk giriş günü, tarih bilinmiyor işareti ve
    esasın ilk görüldüğü çekim günü (tarihi bilinmeyen esas en geç o gün vardı)."""
    tablo = gozlem.bos() if esas_gozlem is None else esas_gozlem
    return pd.DataFrame({"dosya_no": tablo["anahtar"].values,
                         "esas_ilk_giris": pd.to_datetime(tablo["ilk_tarih"]).values,
                         "tarih_bilinmiyor": gozlem.tarih_bilinmiyor(tablo).values,
                         "ilk_gorulme": pd.to_datetime(tablo["ilk_gorulme"]).values})


def kosul_goruntusu(dosya, k2):
    """Kapanmış dosyaların koşul gözlemi girdisi (Kriter 2 koşul kaybı, tahsilat kapanışı): kod
    kapanis_kodlari'nda ya da rücu kodunda açık bakiye <= 0. Atama bekleyen ya da iade edilen
    dosyanın başka kodu kapanış değildir."""
    kod = dosya["rucu_kodu"]
    kayip = kod.isin(k2["kapanis_kodlari"]) | ((kod == k2["rucu_kodu"]) &
                                                (dosya["acik_bakiye"] <= 0))
    return pd.DataFrame({"dosya_no": dosya["dosya_no"],
                         "kosul_kayip": kayip.map({True: "EVET", False: None})})


def k2_surecleri(k2_goruntu, dosya, dava_gozlem, kosul_gozlem, esas_gozlem):
    """Kriter 2 girdisi: dosya başına süreç, başlangıç, dava ve koşul kaybı tarihleri.
    dava_gorulme, kosul_gorulme: günü bilinmeyen (arşiv öncesi) kaydın ilk görüldüğü çekim günü."""
    tablo = k2_goruntu[["dosya_no", "surec_turu", "baslangic_tarihi"]].merge(
        dosya[["dosya_no", "brans", "rucu_kodu", "acik_bakiye"]], on="dosya_no", how="left")
    tablo["dava_ilk_giris"] = tablo["dosya_no"].map(gozlem.tarih_esle(dava_gozlem))
    tablo["dava_gorulme"] = tablo["dosya_no"].map(gozlem.bilinmeyen_esle(dava_gozlem))
    tablo["kosul_kayip_tarihi"] = tablo["dosya_no"].map(gozlem.tarih_esle(kosul_gozlem))
    tablo["kosul_gorulme"] = tablo["dosya_no"].map(gozlem.bilinmeyen_esle(kosul_gozlem))
    bos_baslangic = (tablo["surec_turu"] == ARABULUCULUK) & tablo["baslangic_tarihi"].isna()
    esas = tablo["dosya_no"].map(gozlem.baslangic_esle(esas_gozlem))
    tablo["baslangic_tarihi"] = pd.to_datetime(tablo["baslangic_tarihi"]).where(
        ~bos_baslangic, esas)
    return tablo[list(SUREC_SUTUNLARI) + ["dava_gorulme", "kosul_gorulme"]]
'''

DOSYALAR["kalite.py"] = r'''"""Veri kalite kapısı: şema, tür, boşluk, anahtar, satır sayısı ve tarih (ilişki ve mutabakat
kalite_iliski.py'de). Hukuki Kalite sütun puanı bu modülde değil, kalite_davranis.py'dedir.

Her denetim bir satır üretir: kaynak, kontrol, durum (GECTI, UYARI, KALDI), deger, esik,
aciklama. Bir KALDI varsa o gecenin hesabı yapılmaz, son geçerli veri korunur (karar).
denetle tabloyu şemadaki türlere çevirir (kalite_tur.py) ve yalnız şema alanlarını bırakır;
çevrilemeyen değer KALDI sayılır. Türkçe ya da belirsiz biçimli metin sayı (15.000, 83,763)
kaynak ayarında sayi_bicimi (tr ya da en) verilmemişse KALDI: tutar bin kat yanlış okunurdu.
Boş tablo zorunlu kaynakta, gözlem kaynağında (esas, süreç, takip görüntüsü) ve önceki
başarılı çekimi dolu olan isteğe bağlı kaynakta KALDI, ilk kez boş gelen isteğe bağlıda UYARI.
Satır sapması önceki çekimi sapma_en_az_satir'dan küçük tabloda denetlenmez; meşru sıçramada
oran bir gece yükseltilir.
"""
import re

import pandas as pd

from avukat_perf import kalite_alan
from avukat_perf.kalite_tur import TARIH_TUR, TR_SAYI, bos_metin, cevir
from avukat_perf.ortak import tek_gun
from avukat_perf.sema import KAYNAKLAR

SONUC = ["kaynak", "kontrol", "durum", "deger", "esik", "aciklama"]


def satir(kaynak, kontrol, deger, esik=0, aciklama="", uyari=False):
    """Bir denetim satırı: değer eşiği aşmıyorsa GECTI, aşıyorsa UYARI ya da KALDI."""
    durum = "GECTI" if deger <= esik else ("UYARI" if uyari else "KALDI")
    return (kaynak, kontrol, durum, deger, esik, aciklama)


def denetle(kaynak, tablo, kesit, params, onceki_satir=None):
    """(temiz tablo ya da None, sonuç tablosu). Zorunlu sütun eksikse temiz tablo None.

    İsteğe bağlı alan sütun olarak gelmezse boş sütun eklenir, EKSIK_ALAN uyarısı verilir."""
    tanim, sonuclar = KAYNAKLAR[kaynak], []
    eksik = [ad for ad, _, zorunlu in tanim["alanlar"] if zorunlu and ad not in tablo.columns]
    sonuclar.append(satir(kaynak, "ZORUNLU_SUTUN", len(eksik), aciklama=", ".join(eksik)))
    if eksik:
        return None, pd.DataFrame(sonuclar, columns=SONUC)
    istege = [ad for ad, _, _ in tanim["alanlar"] if ad not in tablo.columns]
    sonuclar.append(satir(kaynak, "EKSIK_ALAN", len(istege), aciklama=", ".join(istege),
                          uyari=True))
    temiz = tablo.assign(**{ad: None for ad in istege})[[ad for ad, _, _ in tanim["alanlar"]]]
    temiz = temiz.apply(bos_metin)
    sinir = tek_gun(kesit) + pd.Timedelta(days=params["kalite"]["gelecek_tarih_gun"])
    for ad, tur, zorunlu in tanim["alanlar"]:
        dolu = temiz[ad].notna()
        if tur == "sayi":
            yerel = temiz[ad].map(lambda d: isinstance(d, str) and bool(re.match(TR_SAYI,
                                                                                 d.strip())))
            sonuclar.append(satir(kaynak, "SAYI_BICIMI:" + ad, int(yerel.sum()),
                                   aciklama="Türkçe ya da belirsiz biçimli metin sayı (1.234 ya "
                                            "da 1,234: binlik mi ondalık mı); kaynağın biçimini "
                                            "teyit edip kaynak ayarında sayi_bicimi tr ya da en "
                                            "verin"))
        temiz[ad] = cevir(temiz[ad], tur)
        if tur == "sayi":
            sonsuz = temiz[ad].isin([float("inf"), float("-inf")])
            sonuclar.append(satir(kaynak, "SONSUZ:" + ad, int(sonsuz.sum()),
                                   aciklama="sonlu olmayan sayısal değer"))
        if tur != "metin":
            bozuk = int((dolu & temiz[ad].isna()).sum())
            sonuclar.append(satir(kaynak, "TUR:" + ad, bozuk, aciklama=TARIH_TUR if tur in (
                "tarih", "zaman") else "çevrilemeyen değer"))
        if zorunlu:
            sonuclar.append(satir(kaynak, "BOS:" + ad, int(temiz[ad].isna().sum())))
        if tur in ("tarih", "zaman"):
            ileri = int((temiz[ad].dt.normalize() > sinir).sum())
            sonuclar.append(satir(kaynak, "GELECEK_TARIH:" + ad, ileri, uyari=True))
    anahtar = tanim["anahtar"] or list(temiz.columns)
    yinelenen = int(temiz.duplicated(subset=anahtar, keep=False).sum())
    sonuclar.append(satir(kaynak, "YINELENEN", yinelenen,
                           uyari=not tanim["anahtar"] or tanim.get("yinelenen_uyari", False)))
    sonuclar += [satir(kaynak, kontrol, deger, aciklama=aciklama, uyari=uyari) for
                 kontrol, deger, uyari, aciklama in kalite_alan.denetimler(kaynak, temiz, params,
                                                                        kesit)]
    bos_uyari = tanim.get("istege_bagli") and not tanim.get("gozlem") and not onceki_satir
    sonuclar.append(satir(kaynak, "BOS_TABLO", int(temiz.empty), uyari=bool(bos_uyari)))
    if onceki_satir and onceki_satir >= params["kalite"]["sapma_en_az_satir"]:
        sapma = abs(len(temiz) - onceki_satir) / float(onceki_satir)
        sonuclar.append(satir(kaynak, "SATIR_SAPMASI", round(sapma, 4),
                               params["kalite"]["satir_sapma_orani"],
                               "önceki başarılı çekim: {} satır".format(onceki_satir)))
    return temiz, pd.DataFrame(sonuclar, columns=SONUC)


def cekim_hatasi(kaynak, ileti):
    """Kaynak okunamadı (bağlantı, yetki, biçim): KALDI satırı."""
    return pd.DataFrame([satir(kaynak, "CEKIM_HATASI", 1, aciklama=ileti)], columns=SONUC)


def karar(*sonuclar):
    """Sonuç tablolarından biri KALDI içeriyorsa KALDI, yoksa GECTI."""
    kaldi = any((tablo["durum"] == "KALDI").any() for tablo in sonuclar if tablo is not None)
    return "KALDI" if kaldi else "GECTI"
'''

DOSYALAR["kalite_alan.py"] = r'''"""Alan anlamı denetimleri (kalite kapısının parçası): ters tarih, yer tutucu tarih, bilinen
değerler, gözlem doluluğu, hareket türü ve değerlendirme.

Her denetim (kontrol, değer, uyarı mı, açıklama) döndürür; satırı kalite.denetle kurar.
- Tarih denetimleri (ESKI_TARIH, TERS_TARIH, SAATSIZ_ATAMA) kalite_tarih.py'dedir.
- DEGER: dosya branşı kalite.bilinen_branslar'da değilse KALDI (yazım farkı sessizce varsayılan
  kurala düşerdi: oto eşiği, olgunluk süresi); süreç türü Kriter 2'nin süreç kodlarında değilse
  UYARI. Hareket türü ve değerlendirme alt başlığı tanımsızsa UYARI, hiçbiri tanımlı değilse KALDI.
- DOLULUK: gözlem kaynağı doluyken değer alanı hiçbir satırda dolu değilse KALDI (alan eşlemesi
  yanlış ya da alan gelmiyor; gece geçseydi ertesi gece bütün değerler o gün "ilk görülürdü").
- DISARIDA_TERS_KAYIT: tahsilat sayılmayan türde eksi tutarlı hareket: UYARI.
- OLCEK: tanımlı alt başlık puanı teyit edilmiş ölçeğin dışındaysa KALDI (mevcut alanlar ve
  tanımsız kodlar sınanmaz; hesapla aynı kural). PENCERE_DISI: pencere dışında kalan puanlı
  değerlendirme: UYARI. YINELENEN:degerlendiren: değerlendiren doluyken aynı anahtar: KALDI.
- YINELENEN:hareket_no: hareketin kaynak kimliği verilmişse tekil olmalı: KALDI. BOS_BAKIYE:
  Kriter 2 rücu kodlu dosyada açık bakiye boş: UYARI. SIFIR_RUCU: UYARI (tahsilatı sahibinin
  gerçekleşenine girer, beklentisi yoktur; ölçüt oranına girmez; evrenden çıkarılması Hukuk
  kararı bekliyor). NEGATIF_RUCU: KALDI. İletiler satır değeri içermez; yalnız sayı verir.
"""
import pandas as pd

from avukat_perf import kalite_tarih
from avukat_perf.kalite_davranis import olcek_disi, olcek_tanimli
from avukat_perf.kriter2 import SURECLER
from avukat_perf.ortak import tek_gun
from avukat_perf.params_sema import KALITE_DAVRANIS_SUTUNLARI
from avukat_perf.pencere import icinde

DOLULUK = {"esas_goruntu": ("esas_no",), "k2_goruntu": ("surec_turu", "dava_esas_no"),
           "takip": ("esas_no",)}


def _sayi(maske):
    return int(maske.sum())


def _hareket_denetimleri(temiz, turler):
    """Tahsilat sayılan türler verilmişse listede olmayan hareketler puana girmez."""
    if turler is None:
        return []
    disarida = ~temiz["hareket_turu"].isin(turler)
    hepsi = len(temiz) > 0 and bool(disarida.all())
    return [("DEGER:hareket_turu", _sayi(disarida), not hepsi,
             "hazirlik.tahsilat_hareket_turleri'nde olmayan tür; puana girmez" +
             ("; hiçbir hareket tahsilat sayılmıyor" if hepsi else "")),
            ("DISARIDA_TERS_KAYIT", _sayi(disarida & (temiz["tutar"] < 0)), True,
             "listede olmayan türde eksi tutarlı hareket; ters kayıt puandan düşülmez")]


def _degerlendirme_denetimleri(temiz, params, kesit):
    kd = params["kalite_davranis"]
    kodlar = [kod for ad in KALITE_DAVRANIS_SUTUNLARI for kod in kd["alt_basliklar"][ad]]
    bilinmeyen = temiz["alt_baslik"].notna() & ~temiz["alt_baslik"].isin(
        kodlar + list(kd["mevcut_alanlar"]))
    hepsi = len(temiz) > 0 and bool(bilinmeyen.all())
    anahtar = ["avukat_kodu", "degerlendirme_tarihi", "alt_baslik", "degerlendiren"]
    cift = temiz["degerlendiren"].notna() & temiz.duplicated(subset=anahtar, keep=False)
    disari = temiz["puan"].notna() & ~icinde(temiz["degerlendirme_tarihi"], tek_gun(kesit),
                                             kd["pencere_ay"])
    sonuc = [("DEGER:alt_baslik", _sayi(bilinmeyen), not hepsi,
              "alt başlıklarda ve mevcut alanlarda olmayan kod; puana girmez" +
              ("; hiçbir kod tanımlı değil" if hepsi else "")),
             ("YINELENEN:degerlendiren", _sayi(cift), False,
              "aynı değerlendiricinin aynı gün ve alt başlıkta birden çok kaydı (çift kayıt)"),
             ("PENCERE_DISI", _sayi(disari), True,
              "kalite_davranis.pencere_ay dışında kalan puanlı değerlendirme; puana girmez")]
    if olcek_tanimli(params):
        sonuc.append(("OLCEK:puan", _sayi(olcek_disi(temiz, kd)), False,
                      "ölçek dışında değerlendirme puanı"))
    return sonuc


def denetimler(kaynak, temiz, params, kesit):
    """Kaynağın alan anlamı denetimleri: [(kontrol, değer, uyarı, açıklama), ...]."""
    sonuc = kalite_tarih.denetimler(kaynak, temiz,
                                    pd.Timestamp(params["kalite"]["en_eski_tarih"]))
    sonuc += [("DOLULUK:" + ad, int(len(temiz) > 0 and not temiz[ad].notna().any()), False,
               "değer alanı hiçbir satırda dolu değil (alan eşlemesi yanlış olabilir; kaynakta "
               "veri yoksa yontem bekliyor yapılır)") for ad in DOLULUK.get(kaynak, ())]
    if kaynak == "dosya":
        bilinmeyen = temiz["brans"].notna() & ~temiz["brans"].isin(
            params["kalite"]["bilinen_branslar"])
        sonuc.append(("DEGER:brans", _sayi(bilinmeyen), False,
                      "kalite.bilinen_branslar'da olmayan branş: yazım farkıysa kaynak ayarında "
                      "deger_eslemesi, yeni branşsa bilinen_branslar"))
        bos = (temiz["rucu_kodu"] == params["kriter2"]["rucu_kodu"]) & temiz["acik_bakiye"].isna()
        sonuc.append(("BOS_BAKIYE", _sayi(bos), True, "Kriter 2 rücu kodlu dosyada açık bakiye "
                      "boş; koşul son bilinen durumla sürer"))
        sonuc.append(("SIFIR_RUCU", _sayi(temiz["rucu_tutari"] == 0), True,
                      "rücu tutarı sıfır; tahsilatı avukatın gerçekleşenine girer, beklentisi "
                      "yok (diğer avukatların ölçütüne girmez)"))
        sonuc.append(("NEGATIF_RUCU", _sayi(temiz["rucu_tutari"] < 0), False,
                      "rücu tutarı negatif (veri hatası ya da düzeltme kaydı)"))
    if kaynak == "tahsilat_hareketi":
        kimlik = temiz["hareket_no"]
        cift = kimlik.notna() & kimlik.duplicated(keep=False)
        sonuc.append(("YINELENEN:hareket_no", _sayi(cift), False,
                      "aynı hareket kimliği birden çok kez geldi"))
        sonuc += _hareket_denetimleri(temiz, params["hazirlik"]["tahsilat_hareket_turleri"])
    if kaynak == "k2_goruntu":
        bilinmeyen = temiz["surec_turu"].notna() & ~temiz["surec_turu"].isin(SURECLER)
        sonuc.append(("DEGER:surec_turu", _sayi(bilinmeyen), True,
                      "tanımsız süreç türü: " + ", ".join(SURECLER) + " beklenir"))
    if kaynak == "degerlendirme":
        sonuc += _degerlendirme_denetimleri(temiz, params, kesit)
    return sonuc
'''

DOSYALAR["kalite_davranis.py"] = r'''"""Hukuki Kalite (kalite) ile Davranış ve İletişim (davranis) sütun puanları; kaynak
değerlendirme sistemi.

Pencere: (kesit - pencere_ay ay, kesit] içindeki değerlendirmeler. Yalnız
kalite_davranis.alt_basliklar listelerindeki kodlar kullanılır; mevcut eski alanlar gibi
diğer kodlar yok sayılır. Puan 0-100 ölçeğine çevrilir; yüksek puan olumludur, ters
yönlü alt başlıkta 100'den çıkarılır. Boş puan "puanlanmamış" demektir.
Bir alt başlığın birden çok değerlendirmesi coklu_degerlendirme kuralıyla birleşir:
ortalama, ya da son: en son tarihteki değerlendirmelerin ortalaması.
Sütun puanı puanlanan alt başlıkların ortalamasıdır. Yeterlilik tam sayıyla sınanır:
puanlanan * payda >= toplam * pay; sağlanmazsa puan yok, durum EKSIK_DEGERLENDIRME.
gereken bu koşulu sağlayan en küçük puanlanan sayısıdır (ekran parametreyi okumaz).
mevcut_alanlar: yeni alt başlıklar eklenene kadar bilgi amaçlı gösterilen mevcut alanlar
(puana girmez, alt başlıklara eşlenmez, ölçek teyidi gerekmez).
"""
import pandas as pd

from avukat_perf.ortak import bos_kontrol, gun, sutun_kontrol, tek_gun
from avukat_perf.params_sema import KALITE_DAVRANIS_SUTUNLARI
from avukat_perf.pencere import icinde

SUTUNLAR = ("avukat_kodu", "degerlendirme_tarihi", "alt_baslik", "puan")
ANAHTAR = ["avukat_kodu", "sutun", "alt_baslik"]


def olcek_tanimli(params):
    """Değerlendirme ölçeği (en düşük, en yüksek) verilmiş mi."""
    olcek = params["kalite_davranis"]["olcek"]
    return None not in (olcek["en_dusuk"], olcek["en_yuksek"])


def teyitli(params):
    """Ölçek ve yön teyit edildi mi (null yok): değilse sütun puanı üretilmez."""
    return olcek_tanimli(params) and params["kalite_davranis"]["ters_yonlu"] is not None


def olcek_disi(tablo, kd):
    """Tanımlı alt başlıkta ölçek dışı puan (kapı ve hesap aynı kural; mevcut alan sınanmaz)."""
    kodlar = [kod for ad in KALITE_DAVRANIS_SUTUNLARI for kod in kd["alt_basliklar"][ad]]
    puan, olcek = pd.to_numeric(tablo["puan"], errors="coerce"), kd["olcek"]
    return tablo["alt_baslik"].isin(kodlar) & ((puan < olcek["en_dusuk"]) |
                                               (puan > olcek["en_yuksek"]))


def _pencere(degerlendirmeler, kesit, kd):
    """Penceredeki, tanımlı alt başlıklara ait değerlendirmeler; puan 0-100 ölçeğinde."""
    olcek = kd["olcek"]
    if not teyitli({"kalite_davranis": kd}):
        raise ValueError("kalite_davranis: ölçek ve yön değerlendirme sistemi ekibinden teyit "
                         "bekliyor (kalite_davranis.olcek, kalite_davranis.ters_yonlu)")
    sutun_kontrol(degerlendirmeler, SUTUNLAR, "degerlendirmeler")
    bos_kontrol(degerlendirmeler, SUTUNLAR[:3], "degerlendirmeler")
    kesit = tek_gun(kesit)
    sutun = {kod: ad for ad in KALITE_DAVRANIS_SUTUNLARI for kod in kd["alt_basliklar"][ad]}
    tablo = degerlendirmeler.assign(
        degerlendirme_tarihi=gun(degerlendirmeler["degerlendirme_tarihi"]),
        puan=degerlendirmeler["puan"].astype(float),
        sutun=degerlendirmeler["alt_baslik"].map(sutun))
    tarih = tablo["degerlendirme_tarihi"]
    tablo = tablo[tablo["sutun"].notna() & icinde(tarih, kesit, kd["pencere_ay"])]
    if olcek_disi(tablo, kd).any():
        raise ValueError("degerlendirmeler: ölçek dışında puan var")
    en_dusuk, en_yuksek = olcek["en_dusuk"], olcek["en_yuksek"]
    olcekli = (tablo["puan"] - en_dusuk) / (en_yuksek - en_dusuk) * 100.0
    ters = tablo["alt_baslik"].isin(kd["ters_yonlu"])
    return tablo.assign(puan=olcekli.where(~ters, 100.0 - olcekli))


def _alt_baslik_puanlari(pencere, kd):
    """Avukat ve alt başlık başına birleştirilmiş puan ve penceredeki değerlendirme sayısı."""
    puanli = pencere.dropna(subset=["puan"])
    sayi = puanli.groupby(ANAHTAR).size().rename("degerlendirme_sayisi")
    if kd["coklu_degerlendirme"] == "son":
        son = puanli.groupby(ANAHTAR)["degerlendirme_tarihi"].transform("max")
        puanli = puanli[puanli["degerlendirme_tarihi"] == son]
    ortalama = puanli.groupby(ANAHTAR)["puan"].mean()
    return pd.concat([ortalama, sayi], axis=1).reset_index()


def puanla(degerlendirmeler, kesit, params):
    """Avukat başına kalite ve davranış sütun puanı.

    Dönüş: (sütun tablosu, alt başlık tablosu). Penceresinde tanımlı bir alt başlıkta
    değerlendirmesi olan her avukat için iki sütun da yer alır.
    """
    kd = params["kalite_davranis"]
    pencere = _pencere(degerlendirmeler, kesit, kd)
    alt = _alt_baslik_puanlari(pencere, kd)
    dizin = pd.MultiIndex.from_product(
        [sorted(pencere["avukat_kodu"].unique()), list(KALITE_DAVRANIS_SUTUNLARI)],
        names=["avukat_kodu", "sutun"])
    tablo = alt.groupby(["avukat_kodu", "sutun"])["puan"].agg(["size", "mean"])
    tablo = tablo.reindex(dizin)
    puanlanan = tablo["size"].fillna(0).astype(int)
    toplam = pd.Series([len(kd["alt_basliklar"][ad]) for ad in dizin.get_level_values(1)],
                       index=dizin, dtype="int64")
    pay, payda = kd["yeterlilik"]
    yeterli = puanlanan * payda >= toplam * pay
    durum = yeterli.map({True: "GECERLI", False: "EKSIK_DEGERLENDIRME"})
    sonuc = pd.DataFrame({"puanlanan": puanlanan, "toplam": toplam,
                          "gereken": -(-toplam * pay // payda),
                          "puan": tablo["mean"].where(yeterli), "durum": durum})
    return sonuc.reset_index(), alt


def mevcut_alanlar(degerlendirmeler, kesit, params):
    """Mevcut alanların pencere içi ortalaması (değerlendirme sisteminin kendi ölçeğinde),
    değerlendirme sayısı ve son değerlendirme tarihi; avukat ve alan başına."""
    kd = params["kalite_davranis"]
    sutun_kontrol(degerlendirmeler, SUTUNLAR, "degerlendirmeler")
    kesit = tek_gun(kesit)
    tablo = degerlendirmeler.assign(
        degerlendirme_tarihi=gun(degerlendirmeler["degerlendirme_tarihi"]),
        puan=degerlendirmeler["puan"].astype(float))
    tarih = tablo["degerlendirme_tarihi"]
    secili = tablo["alt_baslik"].isin(kd["mevcut_alanlar"]) & tablo["puan"].notna() & \
        icinde(tarih, kesit, kd["pencere_ay"])
    return tablo[secili].groupby(["avukat_kodu", "alt_baslik"], as_index=False).agg(
        puan=("puan", "mean"), degerlendirme_sayisi=("puan", "size"),
        son_degerlendirme=("degerlendirme_tarihi", "max"))
'''

DOSYALAR["kalite_iliski.py"] = r'''"""Kaynaklar arası denetimler: anahtar ilişkisi ve tahsilat raporuyla mutabakat."""
import re

import pandas as pd

from avukat_perf.kalite import SONUC, satir
from avukat_perf.ortak import gun, tek_gun


def iliski(kontrol, ana, alt, anahtar="dosya_no", en_cok_oran=None, agirlik=None):
    """alt tablodaki anahtarların (tek alan ya da alan demeti) ana tabloda olmayanları: UYARI.

    Hiçbiri eşleşmiyorsa (anahtar biçimleri farklı, ör. D-000001 ile D000001) ya da eşleşmeyen
    oranı en_cok_oran'ı aşıyorsa KALDI. agirlik sütunu verilirse oran o sütunun mutlak
    değeriyle de tartılır (tahsilat tutarı); büyük olan kullanılır."""
    alanlar = [anahtar] if isinstance(anahtar, str) else list(anahtar)
    eslesme = alt[alanlar].astype(object).merge(ana[alanlar].astype(object).drop_duplicates(),
                                                how="left", indicator=True)
    yetim = pd.Series((eslesme["_merge"] == "left_only").values, index=alt.index)
    sayi = int(yetim.sum())
    oran = sayi / float(len(alt)) if len(alt) else 0.0
    if agirlik is not None and len(alt):
        tutar = pd.to_numeric(alt[agirlik], errors="coerce").abs().fillna(0.0)
        oran = max(oran, float(tutar[yetim].sum()) / tutar.sum() if tutar.sum() > 0 else 0.0)
    hepsi = 0 < len(alt) == sayi
    asti = en_cok_oran is not None and oran > en_cok_oran
    durum = "GECTI" if sayi == 0 else ("KALDI" if hepsi or asti else "UYARI")
    aciklama = "ana tabloda bulunmayan {} (oran {:.4f}{})".format(
        ", ".join(alanlar), oran, "" if en_cok_oran is None else ", en çok {}".format(en_cok_oran))
    if hepsi:
        aciklama += "; hiçbiri eşleşmiyor, anahtar biçimini kontrol et"
    return pd.DataFrame([("iliski", kontrol, durum, sayi, 0, aciklama)], columns=SONUC)


def _donem(deger):
    """Rapor dönemini YYYY-AA biçimine getirir. Saatli ya da saat dilimli tarih (2026-10-31T21:00Z)
    önce yerel güne çevrilir: ay başı yerel gece yarısı UTC'de önceki aya düşerdi."""
    metin = str(deger).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d", metin):
        yerel = gun(pd.Series([metin]), zorla=True).iloc[0]
        return metin if pd.isna(yerel) else yerel.strftime("%Y-%m")
    for kalip, bicim in ((r"^(\d{4})-(\d{2})(-\d{2})?$", "{0}-{1}"),
                         (r"^(\d{4})(\d{2})$", "{0}-{1}"), (r"^(\d{2})\.(\d{4})$", "{1}-{0}")):
        uyan = re.match(kalip, metin)
        if uyan:
            return bicim.format(*uyan.groups())
    return metin


def mutabakat(hareketler, rapor_toplam, params, kesit=None):
    """Ay başına toplam tahsilat ile tahsilat raporu toplamı arasındaki göreli fark.

    Avukat bazlı karşılaştırma yapılmaz: tahsilat raporunun avukata atıf yöntemi teyit
    edilmedi. Yalnız rapor_toplam'da bulunan aylar karşılaştırılır; rapor avukat, branş ya da
    başka kırılımla gelse de ay toplamı alınır. Dönem YYYY-AA, YYYY-AA-GG, YYYYAA ya da AA.YYYY
    olabilir; başka biçim olduğu gibi kalır (eşleşmez, fark görünür). Kesitin ayı (içinde
    bulunulan, kısmi ay) yalnız uyarıdır: rapor ile hareketler farklı saatte yenilenebilir.
    Açıklama tutar içermez (kalite sonucu ve izleme panosu paylaşılabilir kalsın); göreli fark
    deger sütunundadır.
    """
    ay = gun(hareketler["hareket_tarihi"]).dt.strftime("%Y-%m")
    bizim = hareketler["tutar"].groupby(ay).sum()
    rapor = rapor_toplam["tahsilat_toplami"].groupby(
        rapor_toplam["donem"].map(_donem)).sum()
    sonuclar, kesit_ayi = [], None if kesit is None else tek_gun(kesit).strftime("%Y-%m")
    for donem, toplam in rapor.items():
        fark = abs(bizim.get(donem, 0.0) - toplam) / max(abs(toplam), 1.0)
        sonuclar.append(satir("mutabakat", "TAHSILAT:" + donem, round(fark, 6),
                               params["kalite"]["mutabakat_tolerans"],
                               "hesaplanan ile rapor toplamı arasındaki göreli fark",
                               uyari=donem == kesit_ayi))
    return pd.DataFrame(sonuclar, columns=SONUC)
'''

DOSYALAR["kalite_tarih.py"] = r'''"""Tarih anlamı denetimleri (kalite_alan'ın parçası): yer tutucu tarih, ters tarih ve saatsiz
aynı gün ataması.

- ESKI_TARIH: kalite.en_eski_tarih'ten eski tarih (ör. boş yerine 1900-01-01): KALDI.
- TERS_TARIH: atama logunda iptal günü atama gününden önce (aynı gün değil): dönem boş sayılıp
  çıkar, UYARI. Haklı beklemede bitiş başlangıçtan önce: KALDI (bekleme hesaplanamaz).
- SAATSIZ_ATAMA: atama logunda aynı dosyada aynı gün birden çok atama var ve o günün bütün
  atama zamanları 00:00: UYARI. Aynı gün yeniden atamada sıra saatle belirlenir; kaynak yalnız
  gün veriyorsa dosya avukat koduna göre sıralanıp yanlış avukata yazılabilir. Veri sözleşmesi
  atama ve iptal zamanını saatiyle ister.
"""
import pandas as pd


def _sayi(maske):
    return int(maske.sum())


def _saatsiz_ayni_gun(temiz):
    """Aynı dosyada aynı gün birden çok ataması olan ve o günün saatleri hepsi 00:00 satırlar."""
    secili = temiz[temiz["atama_tarihi"].notna()]
    gun = secili["atama_tarihi"].dt.normalize()
    grup = pd.DataFrame({"dosya": secili["dosya_no"], "gun": gun,
                         "saatsiz": secili["atama_tarihi"] == gun}).groupby(["dosya", "gun"])
    sayi = grup["saatsiz"].transform("size")
    return _sayi((sayi > 1) & grup["saatsiz"].transform("all").astype(bool))


def denetimler(kaynak, temiz, en_eski):
    """[(kontrol, değer, uyarı mı, açıklama), ...]."""
    sonuc = []
    for ad in temiz.columns:
        if pd.api.types.is_datetime64_any_dtype(temiz[ad]):
            sonuc.append(("ESKI_TARIH:" + ad, _sayi(temiz[ad] < en_eski), False,
                          "kalite.en_eski_tarih'ten eski tarih (yer tutucu olabilir)"))
    if kaynak == "atama_log":
        ters = temiz["iptal_tarihi"].dt.normalize() < temiz["atama_tarihi"].dt.normalize()
        sonuc.append(("TERS_TARIH", _sayi(ters), True,
                      "iptal günü atama gününden önce; dönem boş sayılıp çıkarılır"))
        sonuc.append(("SAATSIZ_ATAMA", _saatsiz_ayni_gun(temiz), True,
                      "aynı dosyada aynı gün birden çok atama saatsiz (00:00); sıra bilinmez, "
                      "kaynak atama zamanını saatiyle vermeli"))
    if kaynak == "bekleme":
        sonuc.append(("TERS_TARIH", _sayi(temiz["bitis"] < temiz["baslangic"]), False,
                      "bekleme bitişi başlangıcından önce"))
    return sonuc
'''

DOSYALAR["kalite_tur.py"] = r'''"""Kalite kapısının tür çevirisi: metin, sayı ve tarih alanlarının şemadaki türe getirilmesi.

Metin alanında tam sayı değerli ondalık (ör. 123.0) "123" olur; tarih türünde gelen metin alanı
(rapor dönemi) yerel güne çevrilir. Boş ya da yalnız boşluk olan metin boştur. Sayı kalıpları
burada tek yerdedir: TR_SAYI kapıda Türkçe ya da belirsiz biçimi yakalar, TR_KALIBI ve EN_KALIBI
kaynak ayarındaki sayi_bicimi ile çevrilen biçimlerdir (hat.kaynak).
"""
import pandas as pd

from avukat_perf.ortak import gun

TR_SAYI = r"^-?\d{1,3}(\.\d{3})+(,\d+)?$|^-?\d+,\d+$"  # Türkçe ya da belirsiz (1.234, 1,234)
TR_KALIBI = r"^\s*-?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?\s*$"  # sayi_bicimi tr: 1.234,56
EN_KALIBI = r"^\s*-?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?\s*$"  # sayi_bicimi en: 1,234.56
TARIH_TUR = ("çevrilemeyen değer: YYYY-AA-GG değil ya da tarih sınırı dışında (ör. 9999-12-31 "
             "açık uç yer tutucusu; veri hazırlığında boşa eşlenir)")


def _metin(deger):
    if isinstance(deger, float) and deger.is_integer():
        return str(int(deger))
    return str(deger).strip()


def cevir(seri, tur):
    if tur in ("tarih", "zaman"):
        return gun(seri, zorla=True, saat=tur == "zaman")
    if tur == "sayi":
        return pd.to_numeric(seri, errors="coerce")
    if pd.api.types.is_datetime64_any_dtype(seri):  # metin alanı tarih türünde (rapor dönemi)
        seri = gun(seri).dt.strftime("%Y-%m-%d").where(seri.notna())
    metin = seri.map(_metin, na_action="ignore")
    return metin.where(metin != "")


def bos_metin(seri):
    """Boş ya da yalnız boşluk olan metin boş değerdir (API "" ile gönderebilir). Tarih ve sayı
    dışındaki her tür (string, category) object'e çevrilir: ortak._tarih_disi_ayikla ile aynı."""
    if pd.api.types.is_datetime64_any_dtype(seri) or pd.api.types.is_numeric_dtype(seri):
        return seri
    seri = seri.astype(object).where(seri.notna(), None)
    return seri.where(~seri.map(lambda deger: isinstance(deger, str) and not deger.strip()))
'''

DOSYALAR["kriter1.py"] = r'''"""Kriter 1: İlk İşlem Süresi. Atama dönemi başına seviye, düşüm ve süre.

Başlangıç atama tarihi, bitiş dosyanın esas numarasının ilk giriş tarihidir. Eşik günü
dahildir: süre >= eşik ise bayrak oluşur. Haklı bekleme eşik tarihini ileri kaydırır.
KIRMIZI: düşüm ayından sonraki ayın ilk günü dosya hâlâ açıksa; yeni düşüm doğurmaz.
Kesitten sonraki tarihler henüz bilinmiyor sayılır; aynı veri ve kesitle sonuç aynıdır.
esik_kurali (OTO: gün kuralı, OTO_DISI: takvim ayı kuralı), esik_gun_sari ve esik_gun_turuncu
eşiğin atamadan kaçıncı gün olduğudur (bekleme hariç; süreyle aynı ölçek): kural bilgisi hesap
anında sonuca yazılır, ekran eşiği buradan çizer. Branşı boş dönem (dosya tablosunda olmayan
dosya) ölçülmez: DOSYA_YOK; oto dışı eşikle ölçülmesi düşümü yanlış güne kaydırırdı.
"""
import pandas as pd

from avukat_perf import atama as atama_gecmisi
from avukat_perf import bayrak, bekleme
from avukat_perf.ortak import anahtar_kontrol, bos_kontrol, gun, sutun_kontrol, tek_gun

ATAMA_SUTUNLARI = atama_gecmisi.SUTUNLAR + ("brans",)
ANAHTAR = atama_gecmisi.ANAHTAR
TARIH_SONUCLARI = ("dusum_tarihi", "olcum_sonu", "esik_sari", "esik_turuncu", "esik_kirmizi")
SONUC_SUTUNLARI = ("kapsam_disi_nedeni", "seviye", "en_yuksek_seviye", "dusum",
                   "sure_gun", "esik_kurali", "esik_gun_sari", "esik_gun_turuncu") + TARIH_SONUCLARI


def esikler(atama, oto, aralik_listesi, k1):
    """Bekleme kaydırması uygulanmış SARI, TURUNCU ve KIRMIZI eşik tarihleri."""
    sari = atama + pd.Timedelta(days=k1["uyari_gun"])
    if oto:
        turuncu = atama + pd.Timedelta(days=k1["dusum_gun_oto"])
    else:
        turuncu = atama + pd.DateOffset(months=k1["dusum_ay_diger"])
    sari = bekleme.kaydir(sari, atama, aralik_listesi)
    turuncu = bekleme.kaydir(turuncu, atama, aralik_listesi)
    return bayrak.esikler(sari, turuncu)


def _donem_sonucu(kayit, kesit, k1, araliklar):
    """Tek atama dönemi için SONUC_SUTUNLARI değerleri."""
    sonuc = dict.fromkeys(SONUC_SUTUNLARI)
    atama = kayit["atama_tarihi"]
    bitis = kayit["bitis_tarihi"] if kayit["bitis_tarihi"] <= kesit else None
    esas = kayit["esas_ilk_giris"] if kayit["esas_ilk_giris"] <= kesit else None
    neden = kayit["kapsam_disi_nedeni"]
    if pd.isna(neden) and pd.isna(kayit["brans"]):  # dosya tablosunda yok: eşik kuralı bilinmez
        neden = "DOSYA_YOK"
    if pd.isna(neden) and esas is not None and esas < atama:
        neden = "ESAS_ONCEDEN_VAR"
    if pd.isna(neden) and esas is None and kayit["esas_tarihi_bilinmiyor"]:
        gorulme = kayit["esas_gorulme"]
        onceden = not pd.isna(gorulme) and gorulme < atama
        neden = "ESAS_ONCEDEN_VAR" if onceden else "ESAS_TARIHI_BILINMIYOR"
    if not pd.isna(neden):
        sonuc.update(kapsam_disi_nedeni=neden, seviye="KAPSAM_DISI", dusum=False)
        return sonuc
    if esas is not None and (bitis is None or esas <= bitis):
        son, kapanis = esas, "KAPANDI"
    elif bitis is not None:
        son, kapanis = bitis, "SONLANDI"
    else:
        son, kapanis = kesit, None
    aralik_listesi = araliklar.get((kayit["dosya_no"], kayit["avukat_kodu"]), [])
    oto = kayit["brans"] in k1["oto_branslar"]
    esik, olagan = esikler(atama, oto, aralik_listesi, k1), esikler(atama, oto, [], k1)
    seviye, en_yuksek, dusum = bayrak.degerlendir(esik, son, kapanis,
                                                  k1["sonlanan_atamada_dusum_korunur"])
    gecen = (son - atama).days - bekleme.gun_sayisi(atama, son, aralik_listesi)
    sonuc.update(seviye=seviye, en_yuksek_seviye=en_yuksek,
                 dusum=dusum, dusum_tarihi=esik["TURUNCU"] if dusum else None,
                 sure_gun=gecen, olcum_sonu=son, esik_sari=esik["SARI"],
                 esik_kurali="OTO" if oto else "OTO_DISI",
                 esik_gun_sari=(olagan["SARI"] - atama).days,
                 esik_gun_turuncu=(olagan["TURUNCU"] - atama).days,
                 esik_turuncu=esik["TURUNCU"], esik_kirmizi=esik["KIRMIZI"])
    return sonuc


def degerlendir(atamalar, esaslar, beklemeler, kesit, params):
    """Kesit tarihinde her atama dönemi için seviye, düşüm ve süre.

    atamalar: ATAMA_SUTUNLARI; bitis_nedeni IADE, YENIDEN_ATAMA, IPTAL ya da boş;
    atama_turu NORMAL ya da SULH. esaslar: dosya_no, esas_ilk_giris; dosya başına en
    erken tarih alınır. İsteğe bağlı tarih_bilinmiyor sütunu True ise esas arşivden önce
    girilmiş, tarihi bilinmiyordur: dönem ölçülmez (ESAS_TARIHI_BILINMIYOR). İsteğe bağlı
    ilk_gorulme o esasın ilk görüldüğü çekim günüdür; atama bu günden sonraysa esas atamadan
    önce vardı (ESAS_ONCEDEN_VAR).
    beklemeler: bekleme.SUTUNLAR ya da None. Kesitten sonra başlayan atama sonuca girmez.
    """
    sutun_kontrol(atamalar, ATAMA_SUTUNLARI, "atamalar")
    sutun_kontrol(esaslar, ("dosya_no", "esas_ilk_giris"), "esaslar")
    bos_kontrol(atamalar, ANAHTAR, "atamalar")
    kesit = tek_gun(kesit)
    tablo = atama_gecmisi.kapsam_belirle(atamalar)
    tablo["atama_tarihi"] = gun(tablo["atama_tarihi"])
    tablo["bitis_tarihi"] = gun(tablo["bitis_tarihi"])
    anahtar_kontrol(tablo[tablo["kapsam_disi_nedeni"].isna()], ANAHTAR, "atamalar")
    tablo = tablo[tablo["atama_tarihi"] <= kesit].reset_index(drop=True)
    ilk_esas = gun(esaslar["esas_ilk_giris"]).groupby(esaslar["dosya_no"]).min()
    tablo["esas_ilk_giris"] = pd.to_datetime(tablo["dosya_no"].map(ilk_esas))
    isaret = pd.Series(False, index=esaslar.index)
    if "tarih_bilinmiyor" in esaslar.columns:
        isaret = esaslar["tarih_bilinmiyor"].astype(object).eq(True)
    gorulme = (gun(esaslar["ilk_gorulme"]) if "ilk_gorulme" in esaslar.columns
               else pd.Series(pd.NaT, index=esaslar.index, dtype="datetime64[ns]"))
    gorulme = gorulme[isaret].groupby(esaslar.loc[isaret, "dosya_no"]).min()
    tablo["esas_tarihi_bilinmiyor"] = tablo["dosya_no"].isin(set(gorulme.index))
    tablo["esas_gorulme"] = pd.to_datetime(tablo["dosya_no"].map(gorulme))
    araliklar = bekleme.araliklar(beklemeler, kesit)
    satirlar = [_donem_sonucu(kayit, kesit, params["kriter1"], araliklar)
                for kayit in tablo.to_dict("records")]
    sonuc = pd.DataFrame(satirlar, columns=list(SONUC_SUTUNLARI))
    for sutun in TARIH_SONUCLARI:
        sonuc[sutun] = pd.to_datetime(sonuc[sutun])
    sonuc["dusum"] = sonuc["dusum"].astype(bool)
    return pd.concat([tablo.drop(columns=["kapsam_disi_nedeni", "esas_gorulme"]), sonuc], axis=1)
'''

DOSYALAR["kriter2.py"] = r'''"""Kriter 2: Dava Açma Süresi (dava takip sistemine bağlı). Atama dönemi başına seviye, düşüm
ve süre. Süreç tablosu dosya başınadır. surec_turu ITIRAZ (itiraz nedeniyle durdurma) ya da
ARABULUCULUK ise kriter uygulanır; DOGRUDAN_DAVA, KESINLESTI ve boş kapsam dışıdır.
Başlangıç, süreç başlangıcı ile atama tarihinin büyüğüdür: yeniden atamada süre yeni
atamadan başlar. Bitiş sırasıyla: dava esas kaydının ilk girişi (KAPANDI), atamanın bitişi
(SONLANDI), koşulun kalktığı gün (KOSUL_DISI: dosya kapandı; bkz. hazirlik.kosul_goruntusu),
kesit. Koşul bugün sağlanmıyor ve kalktığı gün bilinmiyorsa ya da arşiv öncesinde kalkmışsa
(isteğe bağlı kosul_gorulme; ilk kalkış kalıcıdır) dönem kapsam dışıdır. Bugünkü kod kapanış
dışı başka bir kodsa (iade, atama bekleyen) bu yalnız sürmekte olan dönemi kapsam dışı yapar:
sona ermiş dönem bitişine kadar ölçülür, oluşmuş düşüm korunur. Kalktığı gün kesitten sonraysa
koşul kesitte sağlanıyordu (geçmiş kesit aynı sonucu verir).
Dava kaydı var ama ilk giriş günü bilinmiyorsa (arşiv öncesi; isteğe bağlı dava_gorulme) dönem
ölçülmez: DAVA_TARIHI_BILINMIYOR, kayıt atamadan önce de görülmüşse DAVA_ONCEDEN_VAR. Eşikler
takvim ayıdır; bayrak, düşüm ve KIRMIZI kuralı Kriter 1 ile ortaktır (avukat_perf/bayrak.py).
"""
import pandas as pd

from avukat_perf import atama as atama_gecmisi
from avukat_perf import bayrak
from avukat_perf.ortak import anahtar_kontrol, gun, sutun_kontrol, tek_gun

SUREC_SUTUNLARI = ("dosya_no", "brans", "surec_turu", "baslangic_tarihi", "dava_ilk_giris",
                   "kosul_kayip_tarihi", "rucu_kodu", "acik_bakiye")
ARABULUCULUK = "ARABULUCULUK"
UYGULANAN = ("ITIRAZ", ARABULUCULUK)
SURECLER = UYGULANAN + ("DOGRUDAN_DAVA", "KESINLESTI")  # bilinen süreç türleri (kalite kapısı)
TARIHLER = ("baslangic_tarihi", "dava_ilk_giris", "kosul_kayip_tarihi")
GORULME = ("dava_gorulme", "kosul_gorulme")  # isteğe bağlı: günü bilinmeyen kaydın görülmesi
SONUC_TARIHLERI = ("surec_baslangici", "dusum_tarihi", "olcum_sonu", "esik_sari",
                   "esik_turuncu", "esik_kirmizi")
SONUC_SUTUNLARI = ("kapsam_disi_nedeni", "seviye", "en_yuksek_seviye", "dusum",
                   "sure_gun") + SONUC_TARIHLERI
ONCE_BITERSE = {"KAPANDI": "DAVA_ONCEDEN_VAR", "SONLANDI": "SUREC_ATAMA_DISI",
                "KOSUL_DISI": "KOSUL_SAGLANMIYOR"}


def kosul_kalkti(rucu_kodu, acik_bakiye, kod):
    """Kriter 2 koşulu bugün sağlanmıyor mu: rücu kodu başka ya da açık bakiye sıfır ya da eksi.
    Boş bakiye bilinmez; koşul kalkmış sayılmaz (son bilinen durum sürer)."""
    return rucu_kodu != kod or bool(pd.notna(acik_bakiye) and acik_bakiye <= 0)


def _sonlanan_baska_kod(kayit, k2):
    """Dönem sona ermiş, dosyanın bugünkü kodu kapanış dışı başka kod (iade, atama bekleyen)."""
    kod = kayit["rucu_kodu"]
    return pd.notna(kayit["bitis_tarihi"]) and isinstance(kod, str) and \
        kod != k2["rucu_kodu"] and kod not in k2["kapanis_kodlari"]


def _baslangic_nedeni(kayit, tarih, k2):
    """Süreç ve koşul bakımından kapsam dışı nedeni; kapsamdaysa None."""
    if kayit["surec_turu"] not in UYGULANAN:
        return "SUREC_" + (kayit["surec_turu"] if isinstance(kayit["surec_turu"], str)
                           else "YOK")
    if tarih["baslangic_tarihi"] is None:
        return "BASLANGIC_YOK"
    kosul_simdi = not kosul_kalkti(kayit["rucu_kodu"], kayit["acik_bakiye"], k2["rucu_kodu"]) \
        or _sonlanan_baska_kod(kayit, k2)
    if (pd.isna(kayit["kosul_kayip_tarihi"]) and not kosul_simdi) or \
            pd.notna(kayit["kosul_gorulme"]):
        return "KOSUL_SAGLANMIYOR"
    return None


def _dava_nedeni(kayit, tarih):
    """Dava kaydı var ama ilk giriş günü bilinmiyorsa kapsam dışı nedeni; yoksa None."""
    gorulme = kayit["dava_gorulme"]
    if tarih["dava_ilk_giris"] is not None or pd.isna(gorulme):
        return None
    return "DAVA_ONCEDEN_VAR" if gorulme < kayit["atama_tarihi"] else "DAVA_TARIHI_BILINMIYOR"


def _donem_sonucu(kayit, kesit, k2):
    """Tek atama dönemi için SONUC_SUTUNLARI değerleri."""
    sonuc = dict.fromkeys(SONUC_SUTUNLARI)
    tarih = {ad: kayit[ad] if kayit[ad] <= kesit else None
             for ad in TARIHLER + ("bitis_tarihi",)}
    neden = _baslangic_nedeni(kayit, tarih, k2) or _dava_nedeni(kayit, tarih)
    bas = None if neden else max(tarih["baslangic_tarihi"], kayit["atama_tarihi"])
    adaylar = [(tarih["dava_ilk_giris"], "KAPANDI"), (tarih["bitis_tarihi"], "SONLANDI"),
               (tarih["kosul_kayip_tarihi"], "KOSUL_DISI")]
    adaylar = [aday for aday in adaylar if aday[0] is not None]
    son, kapanis = min(adaylar, key=lambda aday: aday[0]) if adaylar else (kesit, None)
    if neden is None and son < bas:
        neden = ONCE_BITERSE[kapanis]
    if neden is not None:
        sonuc.update(kapsam_disi_nedeni=neden, seviye="KAPSAM_DISI", dusum=False)
        return sonuc
    turuncu = bas + pd.DateOffset(months=k2["dusum_ay"])
    esik = bayrak.esikler(bas + pd.DateOffset(months=k2["uyari_ay"]), turuncu)
    seviye, en_yuksek, dusum = bayrak.degerlendir(esik, son, kapanis,
                                                  k2["sonlanan_atamada_dusum_korunur"])
    sonuc.update(seviye=seviye, en_yuksek_seviye=en_yuksek,
                 dusum=dusum, dusum_tarihi=turuncu if dusum else None,
                 sure_gun=(son - bas).days, surec_baslangici=bas, olcum_sonu=son,
                 esik_sari=esik["SARI"], esik_turuncu=turuncu, esik_kirmizi=esik["KIRMIZI"])
    return sonuc


def degerlendir(atamalar, surecler, kesit, params):
    """Kesit tarihinde, süreci olan dosyaların her kapsamdaki atama dönemi için sonuç.

    atamalar: atama.SUTUNLAR; surecler: SUREC_SUTUNLARI, dosya başına bir satır.
    """
    sutun_kontrol(surecler, SUREC_SUTUNLARI, "surecler")
    anahtar_kontrol(surecler, ("dosya_no",), "surecler")
    kesit = tek_gun(kesit)
    donem = atama_gecmisi.donemler(atamalar, kesit)
    bos = pd.Series(pd.NaT, index=surecler.index, dtype="datetime64[ns]")
    hazir = surecler.assign(acik_bakiye=surecler["acik_bakiye"].astype(float),
                            **{ad: gun(surecler[ad]) if ad in surecler.columns else bos
                               for ad in GORULME + TARIHLER})
    tablo = donem.merge(hazir, on="dosya_no").reset_index(drop=True)
    satirlar = [_donem_sonucu(kayit, kesit, params["kriter2"])
                for kayit in tablo.to_dict("records")]
    sonuc = pd.DataFrame(satirlar, columns=list(SONUC_SUTUNLARI))
    for sutun in SONUC_TARIHLERI:
        sonuc[sutun] = pd.to_datetime(sonuc[sutun])
    sonuc["dusum"] = sonuc["dusum"].astype(bool)
    return pd.concat([tablo.drop(columns=list(GORULME)), sonuc], axis=1)
'''

DOSYALAR["mantik.py"] = r'''"""Mantıksal değerin tek çözücüsü: veri kümesinden gelen her biçim aynı okunur.

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
'''

DOSYALAR["olay.py"] = r'''"""Bayrak olay kaydı: türetme, yalnız ekleyerek birleştirme ve çelişki tespiti.

Olay tarihi eşik tarihidir, çalışma tarihi değil. Aynı veri ve kesitle iki kez çalışmak
aynı satırları üretir; birleştirme anahtarı bu yüzden çift kaydı önler. Kayıtlı olay
silinmez ve değiştirilmez; yeni hesapla çelişen olay düzeltme incelemesine gider.
Anahtar esasın kaynağını da taşır (esas_kaynagi: dava_takip ya da yedek; değerlendirmede
sütun yoksa dava_takip): yedek yoldan dava takibe geçişte yedek yolun olayları kalır ama yeni
kaynağın hesabıyla karşılaştırılmaz (çelişki sayılmaz). Sütunu taşımayan eski kayıt dava_takip
sayılır.
"""
import pandas as pd

from avukat_perf.bayrak import BAYRAKLAR
from avukat_perf.ortak import gun, tek_gun

DONEM_ANAHTARI = ["dosya_no", "avukat_kodu", "atama_tarihi"]
ANAHTAR = DONEM_ANAHTARI + ["kriter", "seviye", "esas_kaynagi"]
DAVA_TAKIP, YEDEK = "dava_takip", "yedek"


def kaynakli(tablo):
    """esas_kaynagi sütunu olmayan ya da boş olan (eski) satırlar dava_takip sayılır."""
    kaynak = tablo["esas_kaynagi"] if "esas_kaynagi" in tablo.columns else None
    return tablo.assign(esas_kaynagi=DAVA_TAKIP if kaynak is None else kaynak.fillna(DAVA_TAKIP))


def olaylar(degerlendirme, kriter):
    """Değerlendirme tablosundaki oluşmuş bayrakları olay satırlarına çevirir.

    Gereken sütunlar: dönem anahtarı, olcum_sonu, esik_sari, esik_turuncu, esik_kirmizi.
    """
    parcalar, degerlendirme = [], kaynakli(degerlendirme)
    for bayrak in BAYRAKLAR:
        esik = degerlendirme["esik_" + bayrak.lower()]
        secili = degerlendirme[esik <= degerlendirme["olcum_sonu"]]
        parcalar.append(secili[DONEM_ANAHTARI + ["esas_kaynagi"]].assign(
            kriter=kriter, seviye=bayrak, olay_tarihi=esik[secili.index]))
    tablo = pd.concat(parcalar, ignore_index=True)[
        DONEM_ANAHTARI + ["kriter", "seviye", "olay_tarihi", "esas_kaynagi"]]
    return tablo.sort_values(DONEM_ANAHTARI + ["olay_tarihi"]).reset_index(drop=True)


def _hizala(tablo):
    return kaynakli(tablo).assign(atama_tarihi=gun(tablo["atama_tarihi"]),
                                  olay_tarihi=gun(tablo["olay_tarihi"]))


def olay_birlestir(mevcut, yeni):
    """Yalnız ekler: anahtarı kayıtlı olan olay yeniden yazılmaz, kayıtlı olay silinmez."""
    yeni = _hizala(yeni)
    if mevcut is None or mevcut.empty:
        return yeni.reset_index(drop=True)
    mevcut = _hizala(mevcut)
    birlesim = yeni.merge(mevcut[ANAHTAR].drop_duplicates(), on=ANAHTAR, how="left",
                          indicator=True)
    eklenecek = birlesim[birlesim["_merge"] == "left_only"].drop(columns="_merge")
    return pd.concat([mevcut, eklenecek], ignore_index=True)


def celisen_olaylar(mevcut, yeni, kesit):
    """Kesite kadar kayda geçmiş olup yeni hesapta çıkmayan ya da tarihi değişen olaylar.

    Boş olmayan sonuç, kaynak veride geriye dönük değişiklik olduğunu gösterir.
    """
    sutunlar = ANAHTAR + ["olay_tarihi", "olay_tarihi_yeni"]
    if mevcut is None or mevcut.empty:
        return pd.DataFrame(columns=sutunlar)
    mevcut, yeni = _hizala(mevcut), _hizala(yeni)
    eski = mevcut[mevcut["olay_tarihi"] <= tek_gun(kesit)]
    karsilastirma = eski.merge(yeni[ANAHTAR + ["olay_tarihi"]], on=ANAHTAR, how="left",
                               suffixes=("", "_yeni"))
    farkli = karsilastirma["olay_tarihi_yeni"] != karsilastirma["olay_tarihi"]
    return karsilastirma[farkli].reset_index(drop=True)
'''

DOSYALAR["ortak.py"] = r'''"""Modüllerin ortak yardımcıları: girdi denetimi ve tarih biçimi.

Hata iletileri satır değeri içermez; yalnız sütun adı ve satır sayısı verir.
Metin olarak gelen tarih (object, string ya da category türü) YYYY-AA-GG biçiminde olmalıdır
(saatli ya da saatsiz, karışık olabilir); başka biçim (ör. 05.11.2026) ve sayı (ör. epoch) tahmin
edilmez, hata sayılır. pandas 2.x biçimi ilk satırdan tahmin ettiği için karışık biçim bildirilir.
Yuvarlama elle hesaptaki gibi yarım yukarıdır (bkz. yuvarla).
"""
import re
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

SAAT_DILIMI = "Europe/Istanbul"
BIR_GUN = pd.Timedelta(days=1)
KARISIK_BICIM = {"format": "mixed"} if int(pd.__version__.split(".")[0]) >= 2 else {}
ISO_TARIH = r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$"


def sutun_kontrol(tablo, sutunlar, ad):
    """Eksik sütun varsa ValueError verir."""
    eksik = [sutun for sutun in sutunlar if sutun not in tablo.columns]
    if eksik:
        raise ValueError("{}: eksik sütun: {}".format(ad, ", ".join(eksik)))


def bos_kontrol(tablo, sutunlar, ad):
    """Zorunlu sütunlarda boş değer varsa ValueError verir."""
    for sutun in sutunlar:
        sayi = int(tablo[sutun].isna().sum())
        if sayi:
            raise ValueError("{}: {} sütununda {} boş satır var".format(ad, sutun, sayi))


def anahtar_kontrol(tablo, anahtar, ad):
    """Anahtar sütunlarında yinelenen satır varsa ValueError verir."""
    sayi = int(tablo.duplicated(subset=list(anahtar), keep=False).sum())
    if sayi:
        raise ValueError("{}: anahtarı yinelenen {} satır var".format(ad, sayi))


def _tarih_disi_ayikla(seri, zorla):
    """YYYY-AA-GG olmayan metni ve sayıyı boşaltır (zorla) ya da hata verir; boş metin boştur."""
    if pd.api.types.is_numeric_dtype(seri) and not pd.api.types.is_bool_dtype(seri):
        bozuk = seri.notna()
    elif not pd.api.types.is_datetime64_any_dtype(seri):
        seri = seri.astype(object).where(seri.notna(), None)  # string türü de denetlenir
        metin = seri.map(lambda deger: isinstance(deger, str))
        seri = seri.where(~metin, seri.where(metin, "").astype(str).str.strip())
        seri = seri.where(seri != "")
        metin = seri.map(lambda deger: isinstance(deger, str))
        sayi = seri.map(lambda deger: isinstance(deger, (int, float)) and not pd.isna(deger))
        bozuk = sayi | (metin & ~seri.where(metin, "").astype(str).str.match(ISO_TARIH))
    else:
        return seri
    if bozuk.any() and not zorla:
        raise ValueError("tarih: {} değer YYYY-AA-GG biçiminde değil".format(int(bozuk.sum())))
    return seri.where(~bozuk) if bozuk.any() else seri


def _dilimli_metin(deger):
    return isinstance(deger, str) and re.search(r"(Z|[+-]\d{2}:?\d{2})$", deger) is not None


def _yerel_an(deger, zorla):
    """Tek değer: saat dilimliyse yerel saate çevrilip dilimi kaldırılır."""
    try:
        an = pd.Timestamp(deger)
    except ValueError:
        if zorla:
            return pd.NaT
        raise
    return an.tz_convert(SAAT_DILIMI).tz_localize(None) if an.tzinfo is not None else an


def gun(seri, zorla=False, saat=False):
    """Tarih sütununu saatsiz yerel güne çevirir (saat True ise yerel anı korur); boş NaT olur.

    Saat dilimli değer önce yerel saate çevrilir: UTC saklanmış yerel gece yarısı (ör.
    2026-10-11T21:00Z) bir önceki güne kaymaz. zorla True ise çevrilemeyen değer NaT olur.
    """
    seri, kip = _tarih_disi_ayikla(seri, zorla), "coerce" if zorla else "raise"
    if seri.dtype == object and seri.map(_dilimli_metin).any():
        # Saat dilimli metin (karışık dilim olabilir) tek tek yerel saate çevrilir.
        tarih = pd.to_datetime(seri.map(lambda deger: _yerel_an(deger, zorla),
                                        na_action="ignore"), errors=kip)
    else:
        tarih = pd.to_datetime(seri, errors=kip, **(KARISIK_BICIM if seri.dtype == object else {}))
    if tarih.dt.tz is not None:
        tarih = tarih.dt.tz_convert(SAAT_DILIMI).dt.tz_localize(None)
    return tarih if saat else tarih.dt.normalize()


def birlestir(tablolar, sutunlar):
    """Boş tabloları dışarıda bırakarak alt alta ekler; hepsi boşsa sütunlu boş tablo."""
    dolu = [tablo for tablo in tablolar if tablo is not None and not tablo.empty]
    if not dolu:
        return pd.DataFrame(columns=sutunlar)
    return pd.concat(dolu, ignore_index=True)[sutunlar]


def tek_gun(deger):
    """Tek bir tarih değerini gun() kuralıyla çevirir."""
    return gun(pd.Series([deger])).iloc[0]


def ondalik_yuvarla(deger, ondalik=2):
    """Decimal değeri yarım yukarı yuvarlar ve float döndürür."""
    return float(deger.quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_HALF_UP))


def yuvarla(deger, ondalik=2):
    """Elle hesaptaki gibi yarım yukarı yuvarlar (74,065 → 74,07); boş değer NaN olur.

    round() ikili gösterimdeki değeri yuvarlar (74,065 → 74,06); not eşiğinde bu, elle
    yapılan hesaptan farklı not verebilir.
    """
    if deger is None or pd.isna(deger):
        return float("nan")
    return ondalik_yuvarla(Decimal(repr(float(deger))), ondalik)
'''

DOSYALAR["params.py"] = r'''"""Parametre sözlüğünün doğrulanması.

Bu modül dosya okumaz. Sözlüğü çağıran taraf verir (hat.ayar: params.json + params_ek.json).
"_" ile başlayan anahtarlar açıklamadır, yok sayılır. Şemada olmayan anahtar hatadır: ek
dosyadaki bir yazım hatası (ör. uyari_gn) sessizce hiçbir şeyi değiştirmezdi.
"""
import math

import pandas as pd

from avukat_perf import agirlik
from avukat_perf.params_kural import (diger_hatalari, gorunum_hatalari, kalite_davranis_hatalari,
                                      not_hatalari, tur_uygun)
from avukat_perf.params_tahsilat import tahsilat_hatalari
from avukat_perf.params_sema import ALANLAR, TUR_ADI

UST_ALANLAR = set(ALANLAR) | {"notlar", "birlesik_puan_kosulu", "birlesik_sutunlar", "agirliklar"}


def _bilinmeyenler(blok, izinli, yer):
    return ["bilinmeyen anahtar: " + yer + str(ad) for ad in sorted(blok, key=str)
            if not str(ad).startswith("_") and ad not in izinli]


def _yapi_hatalari(params):
    hatalar = _bilinmeyenler(params, UST_ALANLAR, "")
    for bolum in sorted(ALANLAR):
        if not isinstance(params.get(bolum), dict):
            hatalar.append("eksik bölüm: " + bolum)
            continue
        hatalar += _bilinmeyenler(params[bolum], ALANLAR[bolum], bolum + ".")
        for alan, tur in sorted(ALANLAR[bolum].items()):
            if alan not in params[bolum]:
                hatalar.append("eksik alan: {}.{}".format(bolum, alan))
            elif not tur_uygun(params[bolum][alan], tur):
                ad = " ya da ".join(tur) if isinstance(tur, tuple) else TUR_ADI[tur]
                hatalar.append("{} olmalı: {}.{}".format(ad, bolum, alan))
            elif tur == "sozluk" and any(str(ad).startswith("_") for ad in params[bolum][alan]):
                hatalar.append("açıklama anahtarı (_) yalnız bölüm düzeyinde yazılır: {}.{}".format(
                    bolum, alan))
    if not isinstance(params.get("notlar"), list):
        hatalar.append("liste olmalı: notlar")
    if not isinstance(params.get("agirliklar"), dict):
        hatalar.append("sözlük olmalı: agirliklar")
    return hatalar


def en_kisa_ay_suresi(ay):
    """ay takvim ayının en kısa gün karşılığı (1 ay 28, 2 ay 59 gün): atama hangi gün olursa
    olsun oto dışı düşüm bu süreden önce gelmez. Artık yıl dahil dört yılın her günü denenir."""
    gunler = pd.date_range("2001-01-01", "2004-12-31", freq="D")
    return int(((gunler + pd.DateOffset(months=int(ay))) - gunler).days.min())


def _sonlu_olmayanlar(deger, yol=""):
    """NaN ve sonsuz hiçbir alanda kabul edilmez. JSON okuyucu NaN yazımını kabul eder ve NaN ile
    her karşılaştırma yanlış döndüğü için diğer kurallardan sessizce geçerdi (ör. ağırlık)."""
    if isinstance(deger, float) and not math.isfinite(deger):
        return ["sonlu bir sayı olmalı (NaN ya da sonsuz olamaz): " + yol]
    if isinstance(deger, dict):
        return [hata for ad, alt in sorted(deger.items()) if not str(ad).startswith("_")
                for hata in _sonlu_olmayanlar(alt, (yol + "." if yol else "") + str(ad))]
    if isinstance(deger, list):
        return [hata for sira, alt in enumerate(deger)
                for hata in _sonlu_olmayanlar(alt, "{}[{}]".format(yol, sira))]
    return []


def _teyit_hatalari(params):
    """_teyit_bekleyen listesindeki her anahtar (bölüm ya da bölüm.alan) parametrede olmalı."""
    hatalar, liste = [], params.get("_teyit_bekleyen", [])
    if not isinstance(liste, list):
        return ["_teyit_bekleyen liste olmalı"]
    for anahtar in liste:
        bolum, _, alan = str(anahtar).partition(".")
        if bolum not in params or (alan and alan not in params[bolum]):
            hatalar.append("_teyit_bekleyen: tanımsız anahtar " + str(anahtar))
    return hatalar


def _kural_hatalari(params):
    k1, k2, sure = params["kriter1"], params["kriter2"], params["sure_puani"]
    hatalar = (tahsilat_hatalari(params["tahsilat"])
               + kalite_davranis_hatalari(params["kalite_davranis"])
               + gorunum_hatalari(params["gorunum"])
               + not_hatalari(params["notlar"]) + diger_hatalari(params))
    if not 0 < k1["uyari_gun"] < k1["dusum_gun_oto"]:
        hatalar.append("kriter1: 0 < uyari_gun < dusum_gun_oto olmalı")
    if k1["dusum_ay_diger"] <= 0:
        hatalar.append("kriter1: dusum_ay_diger sıfırdan büyük olmalı")
    elif k1["uyari_gun"] >= en_kisa_ay_suresi(k1["dusum_ay_diger"]):
        hatalar.append("kriter1: uyari_gun oto dışı düşümden önce olmalı (dusum_ay_diger ayın "
                       "en kısa gün karşılığından küçük)")
    if not 0 < k2["uyari_ay"] < k2["dusum_ay"]:
        hatalar.append("kriter2: 0 < uyari_ay < dusum_ay olmalı")
    if not 0 < sure["en_az_kapsam"] <= 1:
        hatalar.append("sure_puani: en_az_kapsam 0 ile 1 arasında olmalı")
    if sure["guven_sabiti"] <= 0 or sure["egim"] <= 0 or sure["yeterli_dosya"] < 1 \
            or sure["en_az_beklenen"] < 0:
        hatalar.append("sure_puani: guven_sabiti ve egim > 0, yeterli_dosya >= 1, "
                       "en_az_beklenen >= 0 olmalı")
    return hatalar + agirlik.birlesik_hatalari(params)


def dogrula(params):
    """Hata iletilerinin listesini döndürür; liste boşsa sözlük geçerlidir."""
    hatalar = _yapi_hatalari(params) + _sonlu_olmayanlar(params)
    return hatalar if hatalar else _teyit_hatalari(params) + _kural_hatalari(params)


def dogrula_veya_dur(params):
    """Geçerliyse sözlüğü aynen döndürür, değilse ValueError verir."""
    hatalar = dogrula(params)
    if hatalar:
        raise ValueError("Geçersiz parametre: " + "; ".join(hatalar))
    return params
'''

DOSYALAR["params_kural.py"] = r'''"""Parametre bölümlerinin içerik kuralları (tür, kalite/davranış, not, adlar, diğer).

Tahsilat bölümünün kuralları (aylık pencere dahil) params_tahsilat.py'de, kalite kapısı, veri
hazırlığı ve branş kodlarının tutarlılığı params_veri.py'dedir.
"""
from avukat_perf.params_sema import KALITE_DAVRANIS_SUTUNLARI
from avukat_perf.params_veri import veri_hatalari
from avukat_perf.sema import SISTEMLER


def tur_uygun(deger, tur):
    """Değer şemadaki türe uyuyor mu. bool sayı sayılmaz; null yalnız *_veya_bos'ta; demet tür
    seçenek listesidir."""
    if isinstance(tur, tuple):
        return deger in tur
    if isinstance(deger, bool) or tur == "mantiksal":
        return isinstance(deger, bool) and tur == "mantiksal"
    if deger is None:
        return tur in ("liste_veya_bos", "metin_veya_bos")
    if tur == "tam":
        return isinstance(deger, int)
    if tur == "sayi":
        return isinstance(deger, (int, float))
    if tur in ("metin", "metin_veya_bos"):
        return isinstance(deger, str)
    return isinstance(deger, dict if tur == "sozluk" else list)


def _ad_mi(deger):
    return isinstance(deger, str) and bool(deger.strip())


def gorunum_hatalari(gorunum):
    """Her sistem kodu için ekranda görünecek boş olmayan bir ad, tanımsız kod yok; branş adları
    [kod, ad] çiftleri (kod tekrarsız), alt başlık ve mevcut alan adları boş olmayan metin."""
    adlar, hatalar = gorunum["sistem_adlari"], []  # açıklama anahtarı (_) zaten reddedilir
    bos = [kod for kod in SISTEMLER if not _ad_mi(adlar.get(kod))]
    if bos or set(adlar) - set(SISTEMLER):
        hatalar.append("gorunum.sistem_adlari: yalnız şu kodlar, her biri için ad: " +
                       ", ".join(SISTEMLER))
    branslar = gorunum["brans_adlari"]
    ciftler = [oge for oge in branslar if isinstance(oge, list) and len(oge) == 2
               and all(_ad_mi(parca) for parca in oge)]
    if len(ciftler) != len(branslar) or len({kod for kod, _ in ciftler}) != len(ciftler):
        hatalar.append("gorunum.brans_adlari: [kod, ad] çiftleri listesi olmalı, kod tekrarsız")
    hatalar += ["gorunum.{}: her kod için boş olmayan bir ad".format(alan)
                for alan in ("alt_baslik_adlari", "mevcut_alan_adlari")
                if not all(_ad_mi(ad) for ad in gorunum[alan].values())]
    return hatalar


def diger_hatalari(params):
    """Süre, Kriter 2, veri hazırlığı ve kalite bölümlerinin içerik kuralları. Tahsilat ve süre
    puanının ölçeği (taban, eğim) aynıdır: birleşik puan sütunları aynı anlamda toplar (taban
    her sütunda beklenen düzeydir)."""
    hatalar, k2 = veri_hatalari(params), params["kriter2"]
    tah, sure = params["tahsilat"], params["sure_puani"]
    if (tah["taban"], tah["egim"]) != (sure["taban"], sure["egim"]):
        hatalar.append("tahsilat ve sure_puani: taban ve egim aynı olmalı")
    if params["sure_puani"]["pencere_ay"] < 1:
        hatalar.append("sure_puani.pencere_ay pozitif olmalı")
    if not k2["rucu_kodu"]:
        hatalar.append("kriter2.rucu_kodu boş olamaz")
    kapanis = k2["kapanis_kodlari"]
    if not all(isinstance(kod, str) and kod.strip() for kod in kapanis) \
            or k2["rucu_kodu"] in kapanis:
        hatalar.append("kriter2.kapanis_kodlari boş olmayan metin listesi olmalı, rucu_kodu'nu "
                       "içeremez")
    return hatalar


def kalite_davranis_hatalari(kd):
    hatalar = []
    oran = kd["yeterlilik"]
    gecerli = len(oran) == 2 and all(tur_uygun(sayi, "tam") for sayi in oran)
    if not gecerli or not 0 < oran[0] <= oran[1]:
        hatalar.append("kalite_davranis.yeterlilik [pay, payda] tam sayı olmalı (ör. [2, 3]); "
                       "0 < pay <= payda")
    listeler = [kd["alt_basliklar"].get(ad) for ad in KALITE_DAVRANIS_SUTUNLARI]
    duzgun = sorted(kd["alt_basliklar"]) == sorted(KALITE_DAVRANIS_SUTUNLARI) and all(
        isinstance(liste, list) and liste and all(isinstance(kod, str) for kod in liste)
        for liste in listeler)
    kodlar = [kod for liste in listeler for kod in liste] if duzgun else []
    if not duzgun or len(set(kodlar)) < len(kodlar):
        hatalar.append("kalite_davranis.alt_basliklar: kalite ve davranis için tekrarsız "
                       "kod listesi")
    sinir = [kd["olcek"].get("en_dusuk"), kd["olcek"].get("en_yuksek")]
    sayisal = all(tur_uygun(deger, "sayi") for deger in sinir) and sinir[0] < sinir[1]
    if sorted(kd["olcek"]) != ["en_dusuk", "en_yuksek"] or not (sayisal or sinir == [None] * 2):
        hatalar.append("kalite_davranis.olcek: en_dusuk < en_yuksek sayı olmalı ya da ikisi "
                       "de null")
    ters = kd["ters_yonlu"]
    if ters is not None and not all(kod in kodlar for kod in ters):
        hatalar.append("kalite_davranis.ters_yonlu yalnız tanımlı alt başlık kodlarını "
                       "içerebilir")
    mevcut = kd["mevcut_alanlar"]
    if not all(isinstance(kod, str) for kod in mevcut) or set(mevcut) & set(kodlar):
        hatalar.append("kalite_davranis.mevcut_alanlar: alt başlıklardan ayrı kod listesi")
    if kd["pencere_ay"] < 1:
        hatalar.append("kalite_davranis.pencere_ay pozitif olmalı")
    return hatalar


def not_hatalari(notlar):
    """Not ölçeği: yüksekten düşüğe [ad, eşik] listesi; ilk eşik en çok 100, son eşik 0."""
    duzgun = bool(notlar) and all(
        isinstance(satir, list) and len(satir) == 2 and isinstance(satir[0], str)
        and tur_uygun(satir[1], "sayi") for satir in notlar)
    adlar = [satir[0] for satir in notlar] if duzgun else []
    esikler = [satir[1] for satir in notlar] if duzgun else []
    azalan = all(ust > alt for ust, alt in zip(esikler, esikler[1:]))
    if not duzgun or len(set(adlar)) < len(adlar) or not azalan or esikler[0] > 100 \
            or esikler[-1] != 0:
        return ["notlar: [ad, eşik] listesi; adlar tekrarsız, eşikler 100'den 0'a azalan"]
    return []
'''

DOSYALAR["params_sema.py"] = r'''"""Parametre sözlüğünün şeması: bölümler, alanlar ve alan türleri.

Tür adları: sayi, tam, mantiksal, metin, liste, sozluk; liste_veya_bos ve metin_veya_bos
teyit bekleyen değer için null da kabul eder. Tür bir demetse alan yalnız o değerlerden birini
alır (seçenek). notlar bölüm değil listedir; params.py
ayrıca denetler.
"""
SUTUNLAR = ("tahsilat", "sure", "kalite", "davranis")
GORUNUM = "gorunum"  # yalnız ekranda görünen adlar; hesap sürümüne girmez
KALITE_DAVRANIS_SUTUNLARI = ("kalite", "davranis")
TAHSILAT_GRUPLARI = ("brans", "yas_bandi", "tutar_bandi")
TAHSILAT_BILESENLERI = ("tutar", "siklik", "guncellik")
COKLU_KURALLARI = ("ortalama", "son")
IPTAL_YORUMLARI = ("sonraki_atamaya_gore", "hatali_iptal")
ELDE_TUTMA_PAYDALARI = ("ilk_atamadan", "avukat_gunleri")
YENIDEN_ATAMA_KURALLARI = ("yeni_donem", "surer")
ALANLAR = {
    "kriter1": {"uyari_gun": "tam", "dusum_gun_oto": "tam", "dusum_ay_diger": "tam",
                "oto_branslar": "liste", "sonlanan_atamada_dusum_korunur": "mantiksal"},
    "kriter2": {"uyari_ay": "tam", "dusum_ay": "tam", "rucu_kodu": "metin",
                "kapanis_kodlari": "liste", "sonlanan_atamada_dusum_korunur": "mantiksal"},
    "tahsilat": {"gruplama": "liste", "tutar_bantlari": "liste", "yas_bantlari": "liste",
                 "olgunluk_ay": "sozluk", "en_az_olgun_dosya": "tam",
                 "yeterli_olgun_dosya": "tam", "guven_sabiti": "sayi",
                 "olay_guven_sabiti": "sayi", "taban": "sayi", "egim": "sayi",
                 "bilesen_agirliklari": "sozluk", "elde_tutma_paydasi": ELDE_TUTMA_PAYDALARI,
                 "enflasyon_duzeltme": "mantiksal", "guncellik_pencere_ay": "tam",
                 "aylik_pencere_ay": "tam", "yillik_yil_sayisi": "tam"},
    "kalite_davranis": {"yeterlilik": "liste", "alt_basliklar": "sozluk", "olcek": "sozluk",
              "ters_yonlu": "liste_veya_bos", "coklu_degerlendirme": COKLU_KURALLARI,
              "pencere_ay": "tam", "mevcut_alanlar": "liste"},
    "sure_puani": {"guven_sabiti": "sayi", "taban": "sayi", "egim": "sayi",
                   "yeterli_dosya": "tam", "en_az_beklenen": "sayi", "en_az_kapsam": "sayi",
                   "pencere_ay": "tam"},
    "uyari": {"golge_mod": "mantiksal"},
    "hazirlik": {"iptal_yorumu": IPTAL_YORUMLARI,
                 "ayni_avukata_yeniden_atama": YENIDEN_ATAMA_KURALLARI,
                 "sulh_avukat_kodlari": "liste",
                 "sulh_alani": "metin_veya_bos", "sulh_degerleri": "liste",
                 "tahsilat_hareket_turleri": "liste_veya_bos"},
    "kalite": {"satir_sapma_orani": "sayi", "sapma_en_az_satir": "tam",
               "mutabakat_tolerans": "sayi", "gelecek_tarih_gun": "tam",
               "en_eski_tarih": "metin", "bilinen_branslar": "liste",
               "iliski_en_cok_yetim_orani": "sayi"},
    GORUNUM: {"sistem_adlari": "sozluk", "brans_adlari": "liste", "alt_baslik_adlari": "sozluk",
              "mevcut_alan_adlari": "sozluk"},
}
TUR_ADI = {"sayi": "sayı", "tam": "tam sayı", "mantiksal": "true ya da false",
           "metin": "metin", "liste": "liste", "sozluk": "sözlük",
           "liste_veya_bos": "liste ya da null", "metin_veya_bos": "metin ya da null"}
'''

DOSYALAR["params_tahsilat.py"] = r'''"""Tahsilat bölümünün içerik kuralları: olgunluk, gruplama, bantlar, pencereler ve bileşen
ağırlıkları."""
from avukat_perf.params_kural import tur_uygun
from avukat_perf.params_sema import TAHSILAT_BILESENLERI, TAHSILAT_GRUPLARI


def _artan_pozitif(liste, tur):
    return all(tur_uygun(sinir, tur) and sinir > 0 for sinir in liste) and all(
        alt < ust for alt, ust in zip(liste, liste[1:]))


def tahsilat_hatalari(tah):
    hatalar = []
    olgunluk = tah["olgunluk_ay"]
    gecerli_ay = all(tur_uygun(ay, "tam") and ay > 0 for ay in olgunluk.values())
    if "DIGER" not in olgunluk or not gecerli_ay:
        hatalar.append("tahsilat.olgunluk_ay: DIGER bulunmalı, aylar pozitif tam sayı olmalı")
    if tah["en_az_olgun_dosya"] < 1 or tah["guven_sabiti"] < 0 or tah["egim"] <= 0:
        hatalar.append("tahsilat: en_az_olgun_dosya, guven_sabiti ya da egim geçersiz")
    if tah["yeterli_olgun_dosya"] < tah["en_az_olgun_dosya"]:
        hatalar.append("tahsilat.yeterli_olgun_dosya en_az_olgun_dosya'dan küçük olamaz")
    if tah["olay_guven_sabiti"] <= 0:
        hatalar.append("tahsilat.olay_guven_sabiti pozitif olmalı")
    if tah["guncellik_pencere_ay"] < 1 or tah["yillik_yil_sayisi"] < 1 \
            or tah["aylik_pencere_ay"] < 1:
        hatalar.append("tahsilat.guncellik_pencere_ay, aylik_pencere_ay ve yillik_yil_sayisi "
                       "pozitif olmalı")
    grup = tah["gruplama"]
    if not grup or not all(ad in TAHSILAT_GRUPLARI for ad in grup) or len(set(grup)) < len(grup):
        hatalar.append("tahsilat.gruplama yalnız brans, yas_bandi ve tutar_bandi içerebilir, "
                       "tekrarsız")
    if not _artan_pozitif(tah["tutar_bantlari"], "sayi"):
        hatalar.append("tahsilat.tutar_bantlari artan pozitif sayılar olmalı")
    if not _artan_pozitif(tah["yas_bantlari"], "tam"):
        hatalar.append("tahsilat.yas_bantlari artan pozitif tam sayılar (ay) olmalı")
    if tah["enflasyon_duzeltme"]:
        hatalar.append("tahsilat.enflasyon_duzeltme henüz uygulanmadı; false olmalı")
    agirlik = tah["bilesen_agirliklari"]
    gecerli = sorted(agirlik) == sorted(TAHSILAT_BILESENLERI) and all(
        tur_uygun(deger, "sayi") and deger >= 0 for deger in agirlik.values())
    if not gecerli or abs(sum(agirlik.values()) - 1.0) > 1e-9:
        hatalar.append("tahsilat.bilesen_agirliklari: tutar, siklik ve guncellik için negatif "
                       "olmayan sayı; toplamı 1")
    return hatalar
'''

DOSYALAR["params_veri.py"] = r'''"""Kalite kapısı ve veri hazırlığı parametrelerinin içerik kuralları; branş kodlarının üç yerde
(kalite.bilinen_branslar, kriter1.oto_branslar, tahsilat.olgunluk_ay) tutarlılığı.

Kod listelerinin öğeleri boş olmayan metindir: kapı kod alanlarını metne çevirdiği için listeye
sayı olarak yazılmış öğe hiçbir satırla eşleşmezdi. Branş kodu bilinen_branslar dışında olamaz:
yazım farkı oto eşiğini ve olgunluk süresini sessizce varsayılana düşürürdü. sulh_alani atama
logunun sözleşme alanlarından biridir (kapı şema dışı sütunu atar; ham kaynak adı her gece hesap
hatası verirdi); ayrım başka bir alandaysa atama_log şemasına isteğe bağlı alan eklenir.
"""
from datetime import datetime

from avukat_perf import sema

SULH_ALANLARI = [alan for alan in sema.alanlar("atama_log")
                 if alan not in ("dosya_no", "avukat_kodu", "atama_tarihi", "iptal_tarihi")]


def _metin_listesi(liste):
    return all(isinstance(oge, str) and oge.strip() for oge in liste)


def _gun_mu(metin):
    try:
        datetime.strptime(metin, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def kalite_hatalari(kal):
    hatalar = []
    if kal["satir_sapma_orani"] <= 0 or not 0 <= kal["mutabakat_tolerans"] < 1 \
            or kal["gelecek_tarih_gun"] < 0 or kal["sapma_en_az_satir"] < 0:
        hatalar.append("kalite: satir_sapma_orani > 0, 0 <= mutabakat_tolerans < 1, "
                       "gelecek_tarih_gun >= 0, sapma_en_az_satir >= 0 olmalı")
    if not _gun_mu(kal["en_eski_tarih"]) or not kal["bilinen_branslar"] \
            or not _metin_listesi(kal["bilinen_branslar"]):
        hatalar.append("kalite: en_eski_tarih geçerli bir YYYY-AA-GG günü, bilinen_branslar boş "
                       "olmayan metin listesi olmalı")
    if not 0 <= kal["iliski_en_cok_yetim_orani"] < 1:
        hatalar.append("kalite.iliski_en_cok_yetim_orani 0 ile 1 arasında olmalı (1 hariç)")
    return hatalar


def brans_hatalari(params):
    bilinen, hatalar = set(params["kalite"]["bilinen_branslar"]), []
    oto = params["kriter1"]["oto_branslar"]
    if not _metin_listesi(oto) or not set(oto) <= bilinen:
        hatalar.append("kriter1.oto_branslar yalnız kalite.bilinen_branslar kodlarını içerebilir")
    if set(params["tahsilat"]["olgunluk_ay"]) - bilinen - {"DIGER"}:
        hatalar.append("tahsilat.olgunluk_ay anahtarları kalite.bilinen_branslar kodları ya da "
                       "DIGER olmalı")
    return hatalar


def hazirlik_hatalari(hz):
    hatalar, turler = [], hz["tahsilat_hareket_turleri"]
    listeler = [hz["sulh_avukat_kodlari"], hz["sulh_degerleri"], turler or []]
    if not all(_metin_listesi(liste) for liste in listeler):
        hatalar.append("hazirlik: sulh_avukat_kodlari, sulh_degerleri ve tahsilat_hareket_turleri "
                       "öğeleri boş olmayan metin olmalı")
    if turler == []:
        hatalar.append("hazirlik.tahsilat_hareket_turleri boş liste olamaz (bütün hareketler "
                       "için null)")
    if hz["sulh_alani"] is not None and hz["sulh_alani"] not in SULH_ALANLARI:
        hatalar.append("hazirlik.sulh_alani null ya da atama logunun şu alanlarından biri olmalı: "
                       + ", ".join(SULH_ALANLARI))
    return hatalar


def veri_hatalari(params):
    """Kalite, branş tutarlılığı ve veri hazırlığı kuralları."""
    return (kalite_hatalari(params["kalite"]) + brans_hatalari(params)
            + hazirlik_hatalari(params["hazirlik"]))
'''

DOSYALAR["pencere.py"] = r'''"""Ölçüm penceresi: (kesit − n ay, kesit] aralığı.

Pencereyi kullanan bütün hesaplar (süre puanı ve özeti, kalite ve davranış, tahsilat güncelliği)
aralığı buradan alır; sınır kuralı tek yerde tanımlıdır. haric verilirse o gün aralıklarına
düşen tarih pencerede sayılmaz: gölge gecelerinin kapsadığı günlerdeki düşüm puana girmez.
Aylık grafik takvim aylarıyla çalışır (takvim_aylari): kesitin ayıyla biten n ay; ilk ay ayın
1'inden başlar, son ay kesite kadardır.
"""
import pandas as pd

from avukat_perf.ortak import tek_gun


def sinirlar(kesit, ay):
    """(bas, son): pencerede olan tarih bas < tarih <= son."""
    son = tek_gun(kesit)
    return son - pd.DateOffset(months=ay), son


def aralik_disinda(tarih, haric, kriter=None):
    """Tarih serisinden hiçbir hariç aralığa (alt < gün <= ust; alt None: sınırsız) düşmeyenler.

    haric {kriter: aralıklar} ise her satır kendi kriterinin aralıklarıyla sınanır (kriter
    serisi gerekir): yedek yolun zorunlu gölgesi yalnız Kriter 1'in günlerini kapsar."""
    if isinstance(haric, dict):
        if kriter is None:
            raise ValueError("kriter bazında hariç aralık için kriter sütunu gerekir")
        sonuc = pd.Series(True, index=tarih.index)
        for ad, araliklar in haric.items():
            sonuc = sonuc & (aralik_disinda(tarih, araliklar) | (kriter != ad))
        return sonuc
    sonuc = pd.Series(True, index=tarih.index)
    for alt, ust in haric or []:
        icinde = tarih <= ust
        if alt is not None:
            icinde = icinde & (tarih > alt)
        sonuc = sonuc & ~icinde
    return sonuc


def takvim_aylari(kesit, ay):
    """(ilk gün, ["YYYY-AA", ...]): kesitin ayıyla biten ay adet takvim ayı."""
    son = tek_gun(kesit)
    ilk = (son - pd.DateOffset(months=ay - 1)).replace(day=1)
    return ilk, [str(donem) for donem in pd.period_range(ilk, son, freq="M")]


def ay_sonu_mu(kesit):
    """Kesit ayın son günü mü (son ay tam mı)."""
    gun = tek_gun(kesit)
    return gun + pd.offsets.MonthEnd(0) == gun


def icinde(tarih, kesit, ay, haric=None, kriter=None):
    """Tarih serisinden pencerede olanlar (bool); boş tarih ve hariç aralıktaki tarih değildir."""
    bas, son = sinirlar(kesit, ay)
    return (tarih > bas) & (tarih <= son) & aralik_disinda(tarih, haric, kriter)
'''

DOSYALAR["portfoy.py"] = r'''"""Portföy ve aylık tahsilat (arayüz için).

Portföy: avukat, branş ve tutar bandı başına aktif dosya, toplam dosya ve aktif dosyaların
rücu tutarı; bant etiketi hesap anındaki sınırlardandır. Aktif: kesitte kapsamdaki açık atama
dönemi. Toplam: kesite kadar kapsamdaki bir atamayla avukatta bulunmuş tüm dosyalar.
Aylık tahsilat: avukat, branş ve ay başına, hareket tarihindeki avukata yazılan tahsilat.
Avukata yazılamayan tutar avukat_kodu ATANAMAYAN ile ayrı satırdadır. Pencere kesitin ayıyla
biten aylik_pencere_ay takvim ayıdır; ay ızgarası (ilk_ay, son_ay, son_ay_kismi) her satırda
hesap anındaki değerle durur, ekran tahsilatsız ayı sıfırla bu ızgaradan çizer.
Yıllık tahsilat: avukat ve takvim yılı başına, içinde bulunulan yıl önceki yılın aynı
dönemiyle karşılaştırılır (gereksinim: aylık ve yıllık tahsilatların karşılaştırılması).
"""
import pandas as pd

from avukat_perf import atama, tahsilat
from avukat_perf.aciklama import sayi
from avukat_perf.ortak import tek_gun
from avukat_perf.pencere import ay_sonu_mu, takvim_aylari
from avukat_perf.tahsilat_evren import dosyalari_hazirla, tutar_bandi_ekle

ATANAMAYAN = "ATANAMAYAN"
ANAHTAR = ["avukat_kodu", "brans", "tutar_bandi"]


def bant_etiketleri(params):
    """Tutar bandı numarası -> etiket (ör. 0: '40.000 altı')."""
    sinirlar = params["tahsilat"]["tutar_bantlari"]
    if not sinirlar:
        return {0: "Tek bant"}
    etiket = {0: sayi(sinirlar[0], 0) + " altı",
              len(sinirlar): sayi(sinirlar[-1], 0) + " ve üzeri"}
    for sira in range(1, len(sinirlar)):
        etiket[sira] = "{} – {}".format(sayi(sinirlar[sira - 1], 0), sayi(sinirlar[sira], 0))
    return etiket


def ozet(dosyalar, atamalar, kesit, params):
    """Avukat, branş ve tutar bandı başına portföy."""
    dosya = tutar_bandi_ekle(dosyalari_hazirla(dosyalar), params["tahsilat"])
    donem = atama.donemler(atamalar, kesit)
    tablo = donem.merge(dosya[["dosya_no", "brans", "tutar_bandi", "rucu_tutari"]],
                        on="dosya_no")
    toplam = tablo.groupby(ANAHTAR)["dosya_no"].nunique().rename("toplam_dosya")
    aktif = tablo[tablo["bitis_tarihi"].isna()].drop_duplicates(["avukat_kodu", "dosya_no"])
    aktif = aktif.groupby(ANAHTAR).agg(aktif_dosya=("dosya_no", "nunique"),
                                       aktif_rucu_tutari=("rucu_tutari", "sum"))
    sonuc = pd.concat([toplam, aktif], axis=1)
    sonuc = sonuc.fillna({"aktif_dosya": 0, "aktif_rucu_tutari": 0.0})
    sonuc = sonuc.astype({"aktif_dosya": int, "toplam_dosya": int}).reset_index()
    return sonuc.assign(bant_etiketi=sonuc["tutar_bandi"].map(bant_etiketleri(params)))


def aylik_tahsilat(dosyalar, atamalar, hareketler, kesit, params):
    """Avukat, branş ve ay (YYYY-AA) başına tahsilat tutarı ve hareket sayısı."""
    kesit = tek_gun(kesit)
    dosya = dosyalari_hazirla(dosyalar)
    donem = atama.donemler(atamalar, kesit)
    hareket = atama.hareket_atfet(hareketler, donem, kesit).merge(
        dosya[["dosya_no", "brans"]], on="dosya_no")
    ilk, aylar = takvim_aylari(kesit, params["tahsilat"]["aylik_pencere_ay"])
    hareket = hareket[hareket["hareket_tarihi"] >= ilk]
    hareket = hareket.assign(ay=hareket["hareket_tarihi"].dt.strftime("%Y-%m"),
                             avukat_kodu=hareket["avukat_kodu"].fillna(ATANAMAYAN))
    sonuc = hareket.groupby(["avukat_kodu", "brans", "ay"]).agg(
        tutar=("tutar", "sum"), hareket_sayisi=("tutar", "size"))
    return sonuc.reset_index().assign(ilk_ay=aylar[0], son_ay=aylar[-1],
                                      son_ay_kismi=not ay_sonu_mu(kesit))


def yillik_tahsilat(dosyalar, atamalar, hareketler, kesit, params):
    """Avukat ve takvim yılı başına tahsilat: son yillik_yil_sayisi yıl, içinde bulunulan yıl
    kesite kadar (yil_ici). Hareket tarihindeki avukata yazılır; yazılamayan ATANAMAYAN.

    ayni_donem_tutar her yılın 1 Ocak'tan kesitin ay ve gününe kadarki tahsilatıdır; kesit ay
    sonuysa ayın tamamı (28 Şubat 2029 kesitinde 29 Şubat 2028 dahil). İçinde
    bulunulan yılın satırında önceki yılın aynı dönemi (onceki_ayni_donem) ve değişim oranı
    (degisim) verilir; önceki dönem sıfır ya da negatifse değişim boştur. Tahsilatı olmayan
    yıl sıfırdır. Önceki yıl, gösterilmese de (yillik_yil_sayisi 1) karşılaştırma için hesaplanır.
    """
    kesit = tek_gun(kesit)
    dosya = dosyalari_hazirla(dosyalar)
    hareket = atama.hareket_atfet(hareketler, atama.donemler(atamalar, kesit), kesit)
    gosterilen = params["tahsilat"]["yillik_yil_sayisi"]
    yillar = list(range(kesit.year - max(gosterilen, 2) + 1, kesit.year + 1))
    hareket = hareket[hareket["dosya_no"].isin(dosya["dosya_no"]) &
                      hareket["hareket_tarihi"].dt.year.isin(yillar)]
    tarih = hareket["hareket_tarihi"]
    son_gun = 31 if ay_sonu_mu(kesit) else kesit.day
    ayni = (tarih.dt.month < kesit.month) | ((tarih.dt.month == kesit.month) &
                                              (tarih.dt.day <= son_gun))
    hareket = hareket.assign(yil=tarih.dt.year, ayni=hareket["tutar"].where(ayni, 0.0),
                             avukat_kodu=hareket["avukat_kodu"].fillna(ATANAMAYAN))
    tablo = hareket.groupby(["avukat_kodu", "yil"]).agg(
        tutar=("tutar", "sum"), hareket_sayisi=("tutar", "size"),
        ayni_donem_tutar=("ayni", "sum"))
    dizin = pd.MultiIndex.from_product([sorted(hareket["avukat_kodu"].unique()), yillar],
                                       names=["avukat_kodu", "yil"])
    tablo = tablo.reindex(dizin, fill_value=0).reset_index()
    onceki = tablo[tablo["yil"] == kesit.year - 1].set_index("avukat_kodu")["ayni_donem_tutar"]
    bu_yil = tablo["yil"] == kesit.year
    tablo["onceki_ayni_donem"] = tablo["avukat_kodu"].map(onceki).where(bu_yil)
    oran = tablo["tutar"] / tablo["onceki_ayni_donem"] - 1
    tablo["degisim"] = oran.where(tablo["onceki_ayni_donem"] >= tahsilat.YARIM_KURUS)
    tablo = tablo[tablo["yil"] > kesit.year - gosterilen].reset_index(drop=True)
    son = [kesit if yil == kesit.year else pd.Timestamp(year=yil, month=12, day=31)
           for yil in tablo["yil"]]
    return tablo.assign(yil_ici=tablo["yil"] == kesit.year, son_tarih=pd.to_datetime(son),
                        tutar=tablo["tutar"].astype(float),
                        hareket_sayisi=tablo["hareket_sayisi"].astype(int))
'''

DOSYALAR["referans.py"] = r'''"""Beklentinin karşılaştırma ölçütü: aynı gruptaki DİĞER avukatların oranı (tahsilat ve süre).

Avukatın kendi sonucu kendi beklentisine girmez. Böylece fazla başarı puanı hiçbir zaman
düşürmez ve grupta payı büyük olan avukatın sapması bastırılmaz; herkes aynı başarıdaysa yine
herkes 75 alır. Grupta başka avukat yoksa sıradaki katman (daha geniş grup), en son bütün diğer
avukatlar kullanılır. Katman seçimi tek yerdedir:
- Tahsilat: dosya grubu, branş, bütün diğerleri. Tutar bileşeninde diğerlerinin oranı 0 ya da
  eksiyse (kimse tahsil etmedi, ters kayıt) ölçüt yok sayılır, üst katmana geçilir; hepsinde
  yoksa oran 0 (beklenen sıfır, puan yok). Sıklık ve güncellikte 0 geçerli bir ölçüttür (o yaş
  bandında kimseden tahsilat beklenmez; beklenen 0 puanı gizlemez).
- Süre: kriter × süreç × branş, kriter × süreç, bütün diğerleri. Diğerlerinin düşüm oranı 0
  geçerli bir ölçüttür (kimse gecikmedi).
"""
import pandas as pd

AVUKAT = "avukat_kodu"


def _oran(tablo, anahtar, pay, payda, sifir_olcut_degil):
    toplam = tablo.groupby(anahtar)[[pay, payda]].transform("sum")
    kendi = tablo.groupby([AVUKAT] + anahtar)[[pay, payda]].transform("sum")
    diger_payda = toplam[payda] - kendi[payda]
    oran = ((toplam[pay] - kendi[pay]) / diger_payda).where(diger_payda > 0)
    return oran.where(oran > 0) if sifir_olcut_degil else oran


def digerlerinin_orani(tablo, katmanlar, pay, payda, sifir_olcut_degil):
    """Satır başına diğer avukatların pay ÷ payda oranı; ilk ölçütü olan katmandan.

    tablo: avukat_kodu, katman sütunları, pay ve payda. katmanlar: daralandan genişleyene
    anahtar listeleri; sonuncusundan sonra bütün diğer avukatlar denenir. Ölçüt yoksa 0.
    """
    tablo = tablo.assign(_tum=0)
    oran = pd.Series(float("nan"), index=tablo.index)
    for anahtar in [list(katman) for katman in katmanlar] + [["_tum"]]:
        oran = oran.fillna(_oran(tablo, anahtar, pay, payda, sifir_olcut_degil))
    return oran.fillna(0.0)


def tahsilat_orani(tablo, grup, pay, payda, sifir_olcut_degil):
    """Tahsilat katmanları: dosya grubu, branş, bütün diğerleri."""
    return digerlerinin_orani(tablo, [grup, ["brans"]], pay, payda, sifir_olcut_degil)
'''

DOSYALAR["sema.py"] = r'''"""Veri sözleşmesi: entegrasyon katmanının her mantıksal kaynak için teslim etmesi gereken
tablo şeması (alan adları eşlendikten sonra).

Her alan (ad, tür, zorunlu); tür metin, tarih, zaman (saatiyle; aynı günün kayıtlarını
sıralamak için), sayi ya da mantiksal. Zorunlu alan boş olamaz. anahtar satırı tekil kılan
alanlardır; atama logunda log kaydının referansı da anahtardadır. gozlem True olan kaynak ilk
görülme günü sabitlenen görüntüdür: boş gelmesi geceyi durdurur. istege_bagli
True olan kaynak gelmese de gecelik çalışma sürer; o kaynağa bağlı hesap "kaynak bekleniyor"
durumunda kalır. yinelenen_uyari True olan kaynakta yinelenen anahtar geceyi durdurmaz, uyarıdır:
değerlendirmede değerlendirici alanı gelmeyebilir; aynı gün birden çok değerlendirme ortalanır
(değerlendiren doluyken tekrar çift kayıttır, kalite_alan KALDI verir). Takip bilgisinde dosya
başına birden çok takip satırı (icra, dava) olabilir; gözleme tek satır girer (hat.model).
Kaynaklar sistem koduna göre: cekirdek (dosya, atama_log, takip), tahsilat_raporu
(tahsilat_hareketi, rapor_avukat_toplam), degerlendirme (degerlendirme, avukat), dava_takip
(esas_goruntu, k2_goruntu), duzeltme (bekleme). Sistemlerin ekranda görünen adları yalnız
params.json içindeki gorunum.sistem_adlari bölümünden gelir.
"""
SISTEMLER = ("cekirdek", "tahsilat_raporu", "degerlendirme", "dava_takip", "duzeltme")

KAYNAKLAR = {
    "dosya": {"sistem": "cekirdek", "anahtar": ["dosya_no"], "alanlar": [
        ("dosya_no", "metin", True), ("brans", "metin", True), ("rucu_kodu", "metin", True),
        ("rucu_tutari", "sayi", True), ("acik_bakiye", "sayi", False),
        ("rucuya_verilis_tarihi", "tarih", True)]},
    "atama_log": {"sistem": "cekirdek",
                  "anahtar": ["dosya_no", "avukat_kodu", "atama_tarihi", "atama_ref"],
                  "alanlar": [
        ("dosya_no", "metin", True), ("avukat_kodu", "metin", True),
        ("atama_tarihi", "zaman", True), ("iptal_tarihi", "zaman", False),
        ("atama_ref", "metin", False), ("grup", "metin", False), ("tipi", "metin", False)]},
    "takip": {"sistem": "cekirdek", "anahtar": ["dosya_no"], "istege_bagli": True, "gozlem": True,
              "yinelenen_uyari": True, "alanlar": [
        ("dosya_no", "metin", True), ("takip_tipi", "metin", False),
        ("esas_no", "metin", False), ("mahkeme", "metin", False),
        ("islem_tarihi", "tarih", False)]},
    "tahsilat_hareketi": {"sistem": "tahsilat_raporu", "anahtar": [], "istege_bagli": True,
                          "alanlar": [
        ("dosya_no", "metin", True), ("hareket_tarihi", "tarih", True),
        ("tutar", "sayi", True), ("hareket_turu", "metin", False),
        ("hareket_no", "metin", False)]},
    "rapor_avukat_toplam": {"sistem": "tahsilat_raporu", "anahtar": ["avukat_kodu", "donem",
                                                                     "brans"],
                         "istege_bagli": True, "alanlar": [
        ("avukat_kodu", "metin", True), ("donem", "metin", True),
        ("tahsilat_toplami", "sayi", True), ("brans", "metin", False)]},
    "degerlendirme": {"sistem": "degerlendirme", "istege_bagli": True, "yinelenen_uyari": True,
                      "anahtar": ["avukat_kodu", "degerlendirme_tarihi", "alt_baslik",
                                  "degerlendiren"], "alanlar": [
        ("avukat_kodu", "metin", True), ("degerlendirme_tarihi", "tarih", True),
        ("alt_baslik", "metin", True), ("puan", "sayi", False),
        ("degerlendiren", "metin", False)]},
    "avukat": {"sistem": "degerlendirme", "anahtar": ["avukat_kodu"], "istege_bagli": True,
               "alanlar": [("avukat_kodu", "metin", True), ("unvan", "metin", False),
                           ("calisma_durumu", "metin", False)]},
    "esas_goruntu": {"sistem": "dava_takip", "anahtar": ["dosya_no"], "istege_bagli": True,
                     "gozlem": True, "alanlar": [
                         ("dosya_no", "metin", True), ("esas_no", "metin", False),
                         ("kaynak_tarihi", "tarih", False)]},
    "k2_goruntu": {"sistem": "dava_takip", "anahtar": ["dosya_no"], "istege_bagli": True,
                   "gozlem": True, "alanlar": [
        ("dosya_no", "metin", True), ("surec_turu", "metin", False),
        ("baslangic_tarihi", "tarih", False), ("dava_esas_no", "metin", False),
        ("dava_kaynak_tarihi", "tarih", False)]},
    "bekleme": {"sistem": "duzeltme", "anahtar": [], "istege_bagli": True,
                "alanlar": [
        ("dosya_no", "metin", True), ("avukat_kodu", "metin", True),
        ("baslangic", "tarih", True), ("bitis", "tarih", False)]},
}


def alanlar(kaynak):
    """Kaynağın alan adları, şemadaki sırayla."""
    return [alan[0] for alan in KAYNAKLAR[kaynak]["alanlar"]]


def zorunlu_kaynaklar():
    """Gecelik çalışmanın başlaması için gelmesi gereken kaynaklar."""
    return [ad for ad, tanim in KAYNAKLAR.items() if not tanim.get("istege_bagli")]
'''

DOSYALAR["sure_ozet.py"] = r'''"""Süre takibi özeti ve gecikme e-posta listesi (arayüz ve uyarı için).

Girdi Kriter 1 ve Kriter 2 değerlendirmelerinin birleşimidir; kriter sütunu K1 ya da K2.
Özet, avukat ve kriter başına: izlenen ve açık bayraklı dönem sayıları, pencerede kapanan
dönemler ve ortalama süreleri, penceredeki düşüm sayısı. Pencere (kesit − ay, kesit];
düşüm sayısında gölge gecelerinin kapsadığı günler sayılmaz (haric). Düşüm durumu: UYGULANDI,
GOLGE (bu hesap gölge modda: uygulanmadı) ya da GOLGE_DONEMI (gölge gecesinin kapsadığı günde
oluştu, bildirilmedi, puana girmez).
E-posta listesi açık dönemlerden SARI, TURUNCU ve KIRMIZI olanlardır. Gönderim bu modülün
işi değildir; gölgedeki kriterin satırları listede kalır ama gonderilecek False olur.
"""
import pandas as pd

from avukat_perf.ortak import gun, sutun_kontrol
from avukat_perf.pencere import aralik_disinda, icinde

GIRDI = ("avukat_kodu", "kriter", "dosya_no", "atama_tarihi", "seviye", "dusum",
         "dusum_tarihi", "sure_gun", "olcum_sonu", "esik_sari", "esik_turuncu")
ACIK = {"KIRMIZI": 0, "TURUNCU": 1, "SARI": 2}


def golge_kriterleri(params):
    """Kriter başına gölge: golge_mod iki kriteri, golge_k1 (yedek yol; parametre dosyasında
    yok, hesap anında verilir) yalnız Kriter 1'i kapsar."""
    uyari = params["uyari"]
    return {"K1": bool(uyari["golge_mod"] or uyari.get("golge_k1")),
            "K2": bool(uyari["golge_mod"])}


def pencerede_dusum(degerlendirmeler, kesit, pencere_ay, haric=None):
    """Düşüm tarihi pencerede (ve gölge gününde değil) olan dönemler (bool)."""
    tarih = gun(degerlendirmeler["dusum_tarihi"])
    return degerlendirmeler["dusum"].astype(bool) & icinde(
        tarih, kesit, pencere_ay, haric, degerlendirmeler.get("kriter"))


def dusum_durumu(degerlendirmeler, golge, haric=None):
    """Düşümü olan dönemde düşümün puana girip girmediği; düşümsüz dönemde boş."""
    tarih = gun(degerlendirmeler["dusum_tarihi"])
    golgede = ~aralik_disinda(tarih, haric, degerlendirmeler.get("kriter")) & tarih.notna()
    durum = pd.Series("UYGULANDI", index=degerlendirmeler.index).where(~golgede, "GOLGE_DONEMI")
    if golge:
        durum = pd.Series("GOLGE", index=degerlendirmeler.index)
    return durum.where(degerlendirmeler["dusum"].astype(bool))


def ozet(degerlendirmeler, kesit, pencere_ay, haric=None):
    """Avukat ve kriter başına süre özeti."""
    sutun_kontrol(degerlendirmeler, GIRDI, "degerlendirmeler")
    tablo = degerlendirmeler
    seviye = tablo["seviye"]
    kapanan = (seviye == "KAPANDI") & icinde(gun(tablo["olcum_sonu"]), kesit, pencere_ay)
    yardimci = pd.DataFrame({
        "avukat_kodu": tablo["avukat_kodu"], "kriter": tablo["kriter"],
        "izleniyor": seviye == "IZLENIYOR", "acik_sari": seviye == "SARI",
        "acik_turuncu": seviye == "TURUNCU", "acik_kirmizi": seviye == "KIRMIZI",
        "kapanan": kapanan,
        "kapanan_sure": tablo["sure_gun"].astype(float).where(kapanan),
        "dusum_sayisi": pencerede_dusum(tablo, kesit, pencere_ay, haric)})
    anahtar = ["avukat_kodu", "kriter"]
    sayilar = yardimci.drop(columns="kapanan_sure").groupby(anahtar).sum().astype(int)
    ortalama = yardimci.groupby(anahtar)["kapanan_sure"].mean().rename("ort_sure_gun")
    return pd.concat([sayilar, ortalama], axis=1).reset_index()


def eposta_listesi(degerlendirmeler, params):
    """Avukat başına açık gecikmeler; en ağır seviye ve en uzun süre önce."""
    sutun_kontrol(degerlendirmeler, GIRDI, "degerlendirmeler")
    tablo = degerlendirmeler[degerlendirmeler["seviye"].isin(list(ACIK))]
    sutunlar = ["avukat_kodu", "kriter", "dosya_no", "atama_tarihi", "seviye", "sure_gun",
                "esik_sari", "esik_turuncu"]
    golge = golge_kriterleri(params)
    tablo = tablo[sutunlar].assign(sira=tablo["seviye"].map(ACIK),
                                   gonderilecek=~tablo["kriter"].map(golge).astype(bool))
    tablo = tablo.sort_values(["avukat_kodu", "sira", "sure_gun"],
                              ascending=[True, True, False])
    return tablo.drop(columns="sira").reset_index(drop=True)
'''

DOSYALAR["sure_puani.py"] = r'''"""Süre ve Performans sütun puanı (dava takip sistemine bağlı).

Girdi Kriter 1 ve Kriter 2 değerlendirmelerinin birleşimidir (GIRDI sütunları).
Pencere (kesit − pencere_ay ay, kesit]; gölge gecelerinin kapsadığı günler sayılmaz (haric).
Risk altındaki dönem: düşüm eşiği (esik_turuncu) pencereye düşen ve ya düşüm almış ya da
süresinde kapanmış (KAPANDI) dönem; süresinden önce iade ya da koşul kaybıyla biten sayılmaz.
O: avukatın düşüm sayısı. E: avukatın her risk altındaki dönemi için aynı kriter, süreç ve
branştaki DİĞER avukatların düşüm oranının toplamı (grupta başka avukat yoksa aynı kriter ve
süreçteki, o da yoksa bütün diğerleri; bkz. referans). R = (O + k) ÷ (E + k); puan =
kırp(taban + eğim × (1 − R)). Yayın tabanı: E >= en_az_beklenen, kapsam >= en_az_kapsam.
yeterli: risk dönemlerinde en az yeterli_dosya farklı dosya (risk_dosya); altında puan
geçerlidir, ekranda 'Yeterli veri yok' uyarısıyla gösterilir.
Kapsam: avukatın penceredeki Kriter 1 dönemlerinden esas tarihi bilinenlerin oranı. Pencerede
ölçülen Kriter 1 dönemi olmayan avukatta tarihi bilinmeyen esas da yoktur: kapsam 1.
Gölge modda O, E ve R hesaplanır, puan yayımlanmaz (durum GOLGE_MOD).
"""
import pandas as pd

from avukat_perf.ortak import gun, sutun_kontrol
from avukat_perf.pencere import icinde
from avukat_perf.referans import digerlerinin_orani
from avukat_perf.sure_ozet import golge_kriterleri

GIRDI = ("avukat_kodu", "dosya_no", "kriter", "surec", "brans", "seviye", "dusum",
         "esik_turuncu")
GRUP = ["kriter", "surec", "brans"]
OLCULMEYEN = ("SULH", "IPTAL", "ESAS_ONCEDEN_VAR", "DOSYA_YOK")


def ham_puan(r, sp):
    """Kırpılmamış puan: taban + eğim × (1 − R) (açıklama metni de bunu kullanır)."""
    return sp["taban"] + sp["egim"] * (1.0 - r)


def puan_hesapla(o, e, sp):
    """(R, puan): R = (O + k) ÷ (E + k), puan 0-100 aralığına kırpılır."""
    r = (o + sp["guven_sabiti"]) / (e + sp["guven_sabiti"])
    return r, min(max(ham_puan(r, sp), 0.0), 100.0)


def risk_altindaki(degerlendirmeler, kesit, pencere_ay, haric=None):
    """Düşüm eşiği pencerede olan ve düşüm almış ya da süresinde kapanmış dönemler."""
    sutun_kontrol(degerlendirmeler, GIRDI, "degerlendirmeler")
    esik = gun(degerlendirmeler["esik_turuncu"])
    tablo = degerlendirmeler.assign(esik_turuncu=esik,
                                    dusum=degerlendirmeler["dusum"].astype(bool))
    secili = icinde(esik, kesit, pencere_ay, haric, degerlendirmeler["kriter"]) & (
        tablo["dusum"] | (tablo["seviye"] == "KAPANDI"))
    return tablo[secili].reset_index(drop=True)


def kapsam_hesapla(k1_degerlendirme, kesit, pencere_ay):
    """Avukat başına, penceredeki Kriter 1 dönemlerinden esas tarihi bilinenlerin oranı."""
    atama = gun(k1_degerlendirme["atama_tarihi"])
    neden = k1_degerlendirme["kapsam_disi_nedeni"]
    tablo = k1_degerlendirme[icinde(atama, kesit, pencere_ay) & ~neden.isin(OLCULMEYEN)]
    bilinen = tablo["kapsam_disi_nedeni"] != "ESAS_TARIHI_BILINMIYOR"
    oran = bilinen.groupby(tablo["avukat_kodu"]).mean().rename("kapsam")
    return oran.reset_index()


def _eksik_nedeni(satir, sp, golge):
    if golge:
        return "GOLGE_MOD"
    if round(satir.e, 9) < sp["en_az_beklenen"]:  # E kesirli oranların toplamı
        return "AZ_BEKLENEN"
    if satir.kapsam < sp["en_az_kapsam"]:
        return "KAPSAM_DUSUK"
    return None


def puanla(degerlendirmeler, kapsam, kesit, params, haric=None):
    """Avukat başına O, E, R, kapsam, puan, durum ve yeterli. kapsam: avukat_kodu, kapsam.

    haric: gölge gecelerinin kapsadığı gün aralıkları; o günlerdeki eşikler risk dönemine girmez.
    """
    sp = params["sure_puani"]
    risk = risk_altindaki(degerlendirmeler, kesit, sp["pencere_ay"], haric)
    risk = risk.assign(_bir=1.0, _dusum=risk["dusum"].astype(float))
    risk = risk.assign(diger_orani=digerlerinin_orani(risk, [GRUP, GRUP[:2]], "_dusum", "_bir",
                                                      False))
    tablo = risk.groupby("avukat_kodu").agg(
        risk_donemi=("dusum", "size"), risk_dosya=("dosya_no", "nunique"), o=("dusum", "sum"),
        e=("diger_orani", "sum"))
    tablo = tablo.reset_index().merge(kapsam[["avukat_kodu", "kapsam"]], on="avukat_kodu",
                                      how="left")
    tablo["kapsam"] = tablo["kapsam"].fillna(1.0)  # pencerede ölçülen Kriter 1 dönemi yok
    tablo["o"] = tablo["o"].astype(int)
    golge = any(golge_kriterleri(params).values())  # bir kriter gölgedeyse puan yayımlanmaz
    satirlar = []
    for satir in tablo.itertuples():
        r, puan = puan_hesapla(satir.o, satir.e, sp)
        neden = _eksik_nedeni(satir, sp, golge)
        satirlar.append((r, None if neden else puan, neden))
    ek = pd.DataFrame(satirlar, columns=["r", "puan", "eksik_nedeni"], index=tablo.index)
    tablo = pd.concat([tablo, ek.astype({"r": float, "puan": float})], axis=1)
    durum = tablo["eksik_nedeni"].map({"GOLGE_MOD": "GOLGE_MOD"}).fillna("VERI_YETERSIZ")
    return tablo.assign(durum=durum.where(tablo["eksik_nedeni"].notna(), "GECERLI"),
                        yeterli=tablo["risk_dosya"] >= sp["yeterli_dosya"])
'''

DOSYALAR["surum.py"] = r'''"""Hesap sürümü: bir sonucun hangi kod ve parametreyle üretildiğini gösterir.

hesap_surumu = kitaplık sürümü + kod özeti + parametre özeti. Kod özeti sonucu belirleyen
dosyalardan (avukat_perf paketi ve KOD_DOSYALARI'ndaki hat modülleri) çalışma anında üretilir;
hat'ın geri kalanı (HAT_GIRIS_CIKIS) yalnız okur, yazar ya da durdurur. Satır sonu ve satır
sonundaki boşluk farkı özeti değiştirmez (kopyala-yapıştır aktarımı). "_" ile başlayan
parametre anahtarları açıklamadır; gorunum bölümü yalnız ekran adlarını, kalite bölümü yalnız
kalite kapısının eşiklerini tutar (hiçbir puana girmez); üçü de sürümü etkilemez.
hazirlik_surumu, gecelik model tablolarını belirleyen kod ve parametrelerin özetidir: dönem
sonu, son geceden sonra değişen hazırlık kuralıyla yayın yapmaz.
"""
import hashlib
import json
import os

from avukat_perf import SURUM
from avukat_perf.params_sema import GORUNUM

KOD_DOSYALARI = (("avukat_perf", None), ("hat", ("akis.py", "donem_akisi.py", "gecmis.py",
                                                  "hesap.py", "hesap_sure.py", "kaynak.py",
                                                  "model.py", "okuma.py")))
HAT_GIRIS_CIKIS = ("__init__.py", "api.py", "api_kimlik.py", "api_yanit.py", "arsiv.py",
                   "ayar.py", "ayar_alan.py", "butunluk.py", "calisma.py", "dataiku_ortam.py",
                   "donem_kayit.py", "ortam.py", "veri_kumeleri.py")
SURUM_DISI = (GORUNUM, "kalite")
_ONBELLEK = {}


def metin_ozeti(metin):
    """Satır sonu ve sondaki boşluktan bağımsız kısa özet (aktarım özetiyle aynı kural)."""
    satirlar = [satir.rstrip() for satir in metin.splitlines()]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return hashlib.sha256("\n".join(satirlar).encode("utf-8")).hexdigest()[:12]


def json_ozeti(deger):
    """Ayar dosyasının (params.json, kaynaklar.json) içerik özeti: anahtar sırası, girinti ve BOM
    etkilemez; açıklamalar ve ekran adları dahil her değer etkiler (aktarım özeti)."""
    return metin_ozeti(json.dumps(deger, sort_keys=True, ensure_ascii=False))


def kod_ozeti():
    """Hesabı belirleyen kitaplık dosyalarının birleşik özeti (süreç boyunca bir kez okunur)."""
    if "kod" not in _ONBELLEK:
        kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parcalar = []
        for paket, adlar in KOD_DOSYALARI:
            klasor = os.path.join(kok, paket)
            for ad in sorted(adlar or os.listdir(klasor)):
                if ad.endswith(".py"):
                    with open(os.path.join(klasor, ad), encoding="utf-8") as dosya:
                        parcalar.append("{}/{} {}".format(paket, ad, metin_ozeti(dosya.read())))
        _ONBELLEK["kod"] = metin_ozeti("\n".join(parcalar))[:8]
    return _ONBELLEK["kod"]


def _aciklamasiz(deger):
    if isinstance(deger, dict):
        return {a: _aciklamasiz(d) for a, d in deger.items() if not a.startswith("_")}
    if isinstance(deger, list):
        return [_aciklamasiz(d) for d in deger]
    return deger


def _ozet(deger):
    metin = json.dumps(_aciklamasiz(deger), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()[:12]


def kural_surumu(params):
    """Parametre içeriğinin kısa özeti. Anahtar sırası, açıklamalar, ekran adları ve kalite
    kapısı eşikleri etkilemez."""
    return _ozet({bolum: deger for bolum, deger in params.items() if bolum not in SURUM_DISI})


def hesap_surumu(params):
    """Sonuç tablolarına yazılan sürüm: kitaplık sürümü + kod özeti + parametre özeti."""
    return "{}+{}+{}".format(SURUM, kod_ozeti(), kural_surumu(params))


def hazirlik_surumu(params):
    """Gecelik model tablolarını (atama dönemi, tahsilat hareketi, koşul gözlemi) belirleyen kod
    ve parametrelerin özeti; koşul gözlemi rücu kodu ve kapanış kodlarından kurulur."""
    k2 = params["kriter2"]
    return kod_ozeti() + "+" + _ozet({"hazirlik": params["hazirlik"], "rucu_kodu": k2["rucu_kodu"],
                                      "kapanis_kodlari": k2["kapanis_kodlari"]})
'''

DOSYALAR["tahsilat.py"] = r'''"""Tahsilat sütun puanı: tutar, sıklık ve güncellik bileşenlerinin ağırlıklı toplamı.

Üç bileşen de avukatın gerçekleşenini aynı dosya grubundan (gruplama: branş, dosya yaşı bandı,
tutar bandı) beklenene oranlar (bkz. tahsilat_tutar, tahsilat_olay, tahsilat_puan):
- Tutar: olgun dosyalarda avukata yazılan tahsilat ÷ beklenen tahsilat.
- Sıklık: olgun dosyalarda tahsilat yapılan dosya-ay sayısı ÷ elde tutulan süreden (dosya-yıl)
  beklenen sayı.
- Güncellik: aynısı, son dönemde (guncellik_pencere_ay) bütün dosyalarla.
Olgun dosya: kesitte branşının izleme süresini doldurmuş ve bu sürede kapsamdaki bir avukatta
bulunmuş dosya; avukatlar arasında elde tutma payıyla bölünür. Hareketler yalnız tahsilat
hareketlerini içermelidir; ters kayıt eksi tutarla gelir.
"""
from avukat_perf import atama, tahsilat_olay
from avukat_perf.ortak import tek_gun
from avukat_perf.tahsilat_evren import bantli_dosyalar, olgunlar
from avukat_perf.tahsilat_puan import YARIM_KURUS, puan_hesapla, puanla as _puanla  # noqa: F401
from avukat_perf.tahsilat_puan import yeterli_mi
from avukat_perf.tahsilat_tutar import tutar

ANAHTAR = ["avukat_kodu", "brans"]
TOPLANAN = ["n", "maruziyet", "gerceklesen", "beklenen", "siklik_o", "siklik_e", "guncellik_o",
            "guncellik_e"]


def puanla(dosyalar, atamalar, hareketler, kesit, params, kapanis=None):
    """Avukat başına tahsilat puanı ve grup başına oranlar: (avukat tablosu, grup tablosu).

    n kesirlidir: elde tutma paylarının toplamı. Avukata yazılamayan tahsilat (atamadan önce,
    sulh döneminde, boşlukta) puana girmez, grup tablosunda ayrı görünür.
    """
    avukat, gruplar, _ = hesapla(dosyalar, atamalar, hareketler, kesit, params, kapanis)
    return avukat, gruplar


def hesapla(dosyalar, atamalar, hareketler, kesit, params, kapanis=None):
    """(avukat, grup, avukat × branş) tabloları.

    kapanis: dosya_no -> kesitte tahsile kapalı dosyanın kapanış günü (bilinmiyorsa NaT); sıklık
    ve güncellikte dosyanın süresi o gün biter. Verilmezse bütün dosyalar açık sayılır.
    Branş tablosu aynı bileşenleri avukatın o branştaki dosyalarıyla verir. Puan en az
    en_az_olgun_dosya olgun dosyada üretilir; yeterli: olgun dosya en az yeterli_olgun_dosya
    (altında puan geçerlidir, ekranda 'Yeterli veri yok' uyarısıyla gösterilir). Avukatın
    puanı branş puanlarının ortalaması değildir; bütün dosyalarından hesaplanır.
    """
    tah = params["tahsilat"]
    if tah["enflasyon_duzeltme"]:
        raise ValueError("tahsilat: enflasyon_duzeltme henüz uygulanmadı")
    kesit = tek_gun(kesit)
    grup = list(tah["gruplama"])
    kirilim = grup + [ad for ad in ("brans",) if ad not in grup]
    dosya = bantli_dosyalar(dosyalar, kesit, tah)
    olgun = olgunlar(dosya, kesit, tah)
    donem = atama.donemler(atamalar, kesit)
    baslangic = olgun[["dosya_no", "rucuya_verilis_tarihi"]].rename(
        columns={"rucuya_verilis_tarihi": "baslangic"})
    pay = atama.elde_tutma_paylari(donem, baslangic, kesit, tah["elde_tutma_paydasi"]).merge(
        olgun, on="dosya_no")
    pay = pay.assign(maruziyet=pay["pay"] * pay["rucu_tutari"])
    hareket = atama.hareket_atfet(hareketler, donem, kesit)
    # Tutar da sıklık ve güncellik gibi [rücuya veriliş, kesit] aralığındaki tahsilatı sayar.
    olgun_hareket = hareket.merge(olgun[["dosya_no", "rucu_tutari", "rucuya_verilis_tarihi"]
                                        + kirilim], on="dosya_no")
    verilisten = olgun_hareket["hareket_tarihi"] >= olgun_hareket["rucuya_verilis_tarihi"]
    olgun_hareket = olgun_hareket[olgun_hareket["dosya_no"].isin(pay["dosya_no"]) & verilisten]
    gruplar, brans = tutar(pay, olgun_hareket, grup, kirilim)
    siklik, guncellik, siklik_hizi = tahsilat_olay.sayimlar(olgun, dosya, donem, hareket, kesit,
                                                             tah, kapanis)
    brans = brans.merge(siklik, on=ANAHTAR, how="left").merge(guncellik, on=ANAHTAR, how="outer")
    brans = brans.fillna({ad: 0.0 for ad in TOPLANAN})
    brans = brans.sort_values(ANAHTAR).reset_index(drop=True)
    avukat = _puanla(brans.groupby("avukat_kodu", as_index=False)[TOPLANAN].sum(), tah)
    durum = avukat["eksik_nedeni"].isna().map({True: "GECERLI", False: "VERI_YETERSIZ"})
    brans = _puanla(brans, tah)
    brans = brans.assign(yeterli=yeterli_mi(brans["n"], tah))
    # Grup tablosu kesitteki olgun dosya gruplarıdır; sıklık hızı dosyaların o banttaki süresinden.
    gruplar = gruplar.merge(siklik_hizi[grup + ["siklik_hizi"]], on=grup, how="left")
    avukat = avukat.assign(durum=durum, yeterli=yeterli_mi(avukat["n"], tah))
    return avukat, gruplar, brans
'''

DOSYALAR["tahsilat_evren.py"] = r'''"""Tahsilat evreni: dosya tablosunun denetimi, olgun dosyalar, rücu tutarı ve dosya yaşı bandı.

Olgun dosya: kesitte rücuya verilişten bu yana branşının izleme süresini (olgunluk_ay)
doldurmuş dosya; olgunluk günü dahildir. Bant sınırına eşit tutar üst banda girer. Yaş bandı,
dosyanın kesitte tamamladığı yaş sınırı (yas_bantlari, ay) sayısıdır: 0 ilk sınırdan genç dosya;
sınır günü dahildir. Tahsilat dosyanın ömrüne yayıldığı için beklenen değerler aynı yaştaki
dosyalardan kurulur; yoksa portföyü yeni olan avukat eski olana göre düşük görünür.
"""
import math

import pandas as pd

from avukat_perf.ortak import anahtar_kontrol, bos_kontrol, gun, sutun_kontrol, tek_gun

DOSYA_SUTUNLARI = ("dosya_no", "brans", "rucu_tutari", "rucuya_verilis_tarihi")
SONSUZ = float("inf")


def dosyalari_hazirla(dosyalar):
    """Dosya tablosunu denetler; tarihi güne, rücu tutarını sayıya çevirir."""
    sutun_kontrol(dosyalar, DOSYA_SUTUNLARI, "dosyalar")
    bos_kontrol(dosyalar, DOSYA_SUTUNLARI, "dosyalar")
    anahtar_kontrol(dosyalar, ("dosya_no",), "dosyalar")
    tablo = dosyalar[list(DOSYA_SUTUNLARI)].assign(
        rucuya_verilis_tarihi=gun(dosyalar["rucuya_verilis_tarihi"]),
        rucu_tutari=dosyalar["rucu_tutari"].astype(float))
    try:
        toplam = math.fsum(tablo["rucu_tutari"].abs())
    except OverflowError:
        toplam = float("inf")
    if not math.isfinite(toplam):
        raise ValueError("dosyalar: rücu tutarı sonlu değil ya da toplam sayısal aralığı aşıyor")
    if (tablo["rucu_tutari"] < 0).any():
        raise ValueError("dosyalar: rücu tutarı negatif olan satır var")
    return tablo


def bantli_dosyalar(dosyalar, kesit, tah):
    """Denetlenmiş dosyalar, tutar_bandi ve yas_bandi sütunlarıyla."""
    return yas_bandi_ekle(tutar_bandi_ekle(dosyalari_hazirla(dosyalar), tah), kesit, tah)


def olgun_dosyalar(dosyalar, kesit, tah):
    """Kesitte olgunlaşmış dosyalar, tutar_bandi ve yas_bandi sütunlarıyla.

    Olgunluk günü dahildir. Bant sınırına eşit tutar üst banda girer; sınır yoksa tek bant.
    """
    return olgunlar(bantli_dosyalar(dosyalar, kesit, tah), kesit, tah)


def olgunlar(tablo, kesit, tah):
    """Bantlı dosya tablosundan kesitte olgunlaşmış olanlar."""
    aylar = tablo["brans"].map(tah["olgunluk_ay"]).fillna(tah["olgunluk_ay"]["DIGER"])
    sinir = [tarih + pd.DateOffset(months=int(ay))
             for tarih, ay in zip(tablo["rucuya_verilis_tarihi"], aylar)]
    olgun = pd.Series(sinir, index=tablo.index, dtype="datetime64[ns]") <= tek_gun(kesit)
    return tablo[olgun].reset_index(drop=True)


def tutar_bandi_ekle(tablo, tah):
    """Rücu tutarına göre bant numarası (0'dan); sınıra eşit tutar üst banda girer."""
    bantlar = [-SONSUZ] + list(tah["tutar_bantlari"]) + [SONSUZ]
    bant = pd.cut(tablo["rucu_tutari"], bantlar, right=False, labels=False)
    return tablo.assign(tutar_bandi=bant.astype("int64"))


def yas_sinirlari(verilis, tah):
    """Her yaş sınırı için dosya başına sınır günü (Series listesi): rücuya veriliş + n ay."""
    tekil = list(verilis.drop_duplicates())
    return [pd.to_datetime(verilis.map({v: v + pd.DateOffset(months=int(ay)) for v in tekil}))
            for ay in tah["yas_bantlari"]]


def yas_bandi(tarih, sinirlar):
    """Tarihte dosyanın tamamladığı yaş sınırı sayısı; sınır günü dahildir. Tutar grubundaki
    (kesitte) ve sıklık ile güncellikteki (her gün, olay günü) yaş bandının tek tanımı."""
    bant = pd.Series(0, index=tarih.index, dtype="int64")
    for sinir in sinirlar:
        bant = bant + (sinir <= tarih).astype("int64")
    return bant


def yas_bandi_ekle(tablo, kesit, tah):
    """Kesitte dosya yaşı bandı: rücuya verilişten bu yana tamamlanan sınır (ay) sayısı."""
    kesit = pd.Series(tek_gun(kesit), index=tablo.index)
    sinirlar = yas_sinirlari(tablo["rucuya_verilis_tarihi"], tah)
    return tablo.assign(yas_bandi=yas_bandi(kesit, sinirlar))


def yas_etiketleri(tah):
    """Yaş bandı numarası -> etiket ("0–12 ay", ..., "84+ ay"); sınır yoksa tek etiket."""
    sinirlar = [0] + [int(ay) for ay in tah["yas_bantlari"]]
    etiket = {sira: "{}–{} ay".format(alt, ust)
              for sira, (alt, ust) in enumerate(zip(sinirlar, sinirlar[1:]))}
    etiket[len(sinirlar) - 1] = "{}+ ay".format(sinirlar[-1]) if len(sinirlar) > 1 else "Tüm yaşlar"
    return etiket
'''

DOSYALAR["tahsilat_maruz.py"] = r'''"""Sayım bileşenlerinin kişi-zamanı: maruziyet (dosya-yıl) ve olay (tahsilat yapılan dosya-ay).

Maruziyet: avukatın dosyayı elinde tuttuğu günler ÷ 365, dosyanın aralık başından (dahil)
bitişine (hariç) kadar; her gün o günkü dosya yaşının bandına yazılır (yas_bantlari, rücuya
verilişten geçen ay). Olay: avukata yazılan net tahsilatı (ters kayıt düşülmüş) yarım kuruştan
büyük olan takvim ayı (avukat, dosya, ay); bandı o aydaki ilk pozitif tahsilatın günündeki yaştır.
Yalnız dosyanın aralığındaki hareketler sayılır; böylece her olay avukatın maruziyeti içindedir.
"""
import pandas as pd

from avukat_perf.ortak import BIR_GUN
from avukat_perf.tahsilat_evren import yas_bandi, yas_sinirlari
from avukat_perf.tahsilat_puan import YARIM_KURUS

YIL = 365.0
CIFT = ["avukat_kodu", "dosya_no"]


def maruziyet(donem, dosya, tah):
    """(avukat, dosya, yas_bandi) başına dosya-yıl.

    dosya: dosya_no, rucuya_verilis_tarihi, alt (aralık başı, dahil), ust (bitiş, hariç).
    """
    tablo = donem.merge(dosya[["dosya_no", "rucuya_verilis_tarihi", "alt", "ust"]], on="dosya_no")
    bas = tablo["atama_tarihi"].where(tablo["atama_tarihi"] >= tablo["alt"], tablo["alt"])
    son = tablo["bitis_tarihi"].where(tablo["bitis_tarihi"] < tablo["ust"], tablo["ust"])
    son = son.fillna(tablo["ust"])
    sinirlar = yas_sinirlari(tablo["rucuya_verilis_tarihi"], tah)
    parcalar = []
    for bant in range(len(sinirlar) + 1):
        alt = bas if bant == 0 else bas.where(bas >= sinirlar[bant - 1], sinirlar[bant - 1])
        ust = son if bant == len(sinirlar) else son.where(son <= sinirlar[bant], sinirlar[bant])
        gun = (ust - alt).dt.days.clip(lower=0)
        parcalar.append(tablo[CIFT].assign(yas_bandi=bant, maruz=gun / YIL))
    sonuc = pd.concat(parcalar, ignore_index=True)
    sonuc = sonuc[sonuc["maruz"] > 0]
    return sonuc.groupby(CIFT + ["yas_bandi"], as_index=False)["maruz"].sum()


def olaylar(hareket, dosya, tah):
    """(avukat, dosya, yas_bandi) başına olay sayısı. hareket: avukata yazılmış hareketler."""
    tablo = hareket[hareket["avukat_kodu"].notna()].merge(
        dosya[["dosya_no", "rucuya_verilis_tarihi", "alt", "ust"]], on="dosya_no")
    tarih = tablo["hareket_tarihi"]
    tablo = tablo[(tarih >= tablo["alt"]) & (tarih < tablo["ust"])]
    # Bant ayın ilk pozitif tahsilatından: 0 TL ya da ters kayıt olayı başka yaş bandına taşımaz.
    tablo = tablo.assign(ay=tablo["hareket_tarihi"].dt.strftime("%Y-%m"),
                         pozitif=tablo["hareket_tarihi"].where(tablo["tutar"] > YARIM_KURUS))
    ay = tablo.groupby(CIFT + ["ay"], as_index=False).agg(
        tutar=("tutar", "sum"), tarih=("pozitif", "min"),
        rucuya_verilis_tarihi=("rucuya_verilis_tarihi", "first"))
    ay = ay[ay["tutar"] > YARIM_KURUS]
    sinirlar = yas_sinirlari(ay["rucuya_verilis_tarihi"], tah)
    ay = ay.assign(yas_bandi=yas_bandi(ay["tarih"], sinirlar))
    return ay.groupby(CIFT + ["yas_bandi"]).size().rename("olay").reset_index()


def kapanis_ustu(dosya, hareket, kapanis, kesit):
    """Dosya başına aralık bitişi (hariç): açık dosyada kesitin ertesi günü; kapanış günü
    biliniyorsa onun ertesi günü (kapanış günü dahil: dosyayı kapatan tahsilat o gün gelir);
    bilinmiyorsa (arşiv öncesi kapanmış) son pozitif tahsilatın ertesi günü, hiç tahsilatı
    yoksa NaT (dosya sayılmaz).

    kapanis: dosya_no -> kesitte tahsile kapalı dosyanın kapanış günü (bilinmiyorsa NaT).
    """
    sinir = kesit + BIR_GUN
    kapanis = (kapanis if kapanis is not None else pd.Series(dtype="datetime64[ns]"))
    kapali = dosya["dosya_no"].isin(kapanis.index)
    gun = pd.to_datetime(dosya["dosya_no"].map(kapanis)) + BIR_GUN
    son = hareket[hareket["tutar"] > YARIM_KURUS].groupby("dosya_no")["hareket_tarihi"].max()
    tahmin = pd.to_datetime(dosya["dosya_no"].map(son)) + BIR_GUN
    ust = gun.where(gun.notna(), tahmin).where(kapali, sinir)
    return ust.where(ust.isna() | (ust <= sinir), sinir)
'''

DOSYALAR["tahsilat_olay.py"] = r'''"""Tahsilat puanının sayım bileşenleri: sıklık ve güncellik (avukat × branş başına O ve E).

Kişi-zaman yöntemi (dolaylı standardizasyon): gerçekleşen O, avukatın tahsilat yaptığı dosya-ay
sayısıdır; beklenen E = Σ avukatın maruziyeti (dosya-yıl) × aynı dosya grubundaki hız. Grup
(tahsilat.gruplama) branş, o günkü dosya yaşı bandı ve tutar bandıdır; hız aynı gruptaki diğer
avukatların olay ÷ maruziyetidir (referans), avukatın kendi olayı beklentisine girmez.
Dosyanın el değiştirmesi olay üretmez, kısa ya da uzun tutmak tek başına avantaj değildir (bkz.
tahsilat_maruz). Kapanan dosyanın süresi kapandığı gün biter.
- Sıklık: olgun dosyalar, rücuya verilişten kesite.
- Güncellik: bütün dosyalar, (kesit − guncellik_pencere_ay ay, kesit] penceresinde.
"""
import pandas as pd

from avukat_perf.ortak import BIR_GUN
from avukat_perf.pencere import sinirlar
from avukat_perf.tahsilat_maruz import kapanis_ustu, maruziyet, olaylar
from avukat_perf.referans import tahsilat_orani

ANAHTAR = ["avukat_kodu", "brans"]


def _say(dosya, donem, hareket, tah, ad):
    """dosya: dosya_no, brans, tutar_bandi, rucuya_verilis_tarihi, alt, ust."""
    dosya = dosya[dosya["ust"].notna() & (dosya["ust"] > dosya["alt"])]
    grup = list(tah["gruplama"])
    ek = dosya[["dosya_no", "brans", "tutar_bandi"]]
    maruz = maruziyet(donem, dosya, tah).merge(ek, on="dosya_no")
    olay = olaylar(hareket, dosya, tah).merge(ek, on="dosya_no")
    hiz = maruz.groupby(grup)["maruz"].sum().to_frame().join(
        olay.groupby(grup)["olay"].sum(), how="left").fillna(0.0)
    hiz[ad + "_hizi"] = hiz["olay"] / hiz["maruz"]  # grup tablosunda gösterilen genel hız
    anahtar = ["avukat_kodu"] + grup + [ad for ad in ("brans",) if ad not in grup]
    hucre = maruz.groupby(anahtar)["maruz"].sum().to_frame().join(
        olay.groupby(anahtar)["olay"].sum(), how="left").fillna(0.0).reset_index()
    hucre["e"] = hucre["maruz"] * tahsilat_orani(hucre, grup, "olay", "maruz", False)
    sonuc = hucre.groupby(ANAHTAR)[["e", "olay"]].sum()
    sonuc = sonuc.rename(columns={"olay": ad + "_o", "e": ad + "_e"}).reset_index()
    return sonuc[ANAHTAR + [ad + "_o", ad + "_e"]], hiz.reset_index()


def sayimlar(olgun, dosya, donem, hareket, kesit, tah, kapanis):
    """(sıklık tablosu, güncellik tablosu, sıklık grup hızları)."""
    ust = kapanis_ustu(olgun, hareket, kapanis, kesit).values
    s, hiz = _say(olgun.assign(alt=olgun["rucuya_verilis_tarihi"], ust=ust), donem, hareket,
                  tah, "siklik")
    pencere_bas, _ = sinirlar(kesit, tah["guncellik_pencere_ay"])
    ilk = pencere_bas + BIR_GUN
    verilis = dosya["rucuya_verilis_tarihi"]
    pencere = dosya.assign(alt=verilis.where(verilis > ilk, ilk),
                           ust=kapanis_ustu(dosya, hareket, kapanis, kesit).values)
    g, _ = _say(pencere, donem, hareket, tah, "guncellik")
    return s, g, hiz
'''

DOSYALAR["tahsilat_puan.py"] = r'''"""Tahsilat puanının bileşen puanları ve birleşimi (avukat ve avukat × branş tablosu için).

Tutar: R = (n × G/B + k) ÷ (n + k); n elde tutma paylarının toplamı. Sıklık ve güncellik olay
sayımıdır, güven ayarı sayıya uygulanır: R = (O + k_olay) ÷ (E + k_olay); az veride puan tabana
(beklenen düzey) yaklaşır. Her bileşen kırp(taban + eğim × (R − 1), 0, 100) ve iki ondalığa yarım
yukarı yuvarlanır; tahsilat puanı yuvarlanmış bileşenlerin ağırlıklı toplamıdır (ekrandaki
sayılarla elle hesap tutar). Yayın tabanının altındaki (AZ_DOSYA) ya da beklenen tahsilatı
olmayan (BEKLENEN_SIFIR) satırda bileşen puanları ve tahsilat puanı üretilmez.
"""
import pandas as pd

from avukat_perf.birlesik import agirlikli_toplam
from avukat_perf.ortak import yuvarla

YARIM_KURUS = 0.005  # tutar karşılaştırmalarında sıfır sayılan en büyük artık
PUANLAR = ["r", "puan_tutar", "puan_siklik", "puan_guncellik", "puan"]


def ham_puan(r, tah):
    """Kırpılmamış bileşen puanı: taban + eğim × (R − 1) (açıklama metni de bunu kullanır)."""
    return tah["taban"] + tah["egim"] * (r - 1)


def _kirp(r, tah):
    # 9 ondalık: tam yarım değer (75,375) kayan nokta artığıyla (75,37499…) aşağı yuvarlanmasın.
    return round(min(max(ham_puan(r, tah), 0.0), 100.0), 9)


def puan_hesapla(n, gerceklesen, beklenen, tah):
    """Tutar bileşeni: (R, puan, eksik nedeni). Puan üretilemezse R ve puan None olur.

    n kesirli payların toplamıdır; eşik karşılaştırması kayan nokta artığını (60 × 1/3 =
    19,999…) yok saymak için yuvarlanmış n ile yapılır.
    """
    if round(n, 9) < tah["en_az_olgun_dosya"]:
        return None, None, "AZ_DOSYA"
    if beklenen < YARIM_KURUS:  # toplamdaki kayan nokta artığı (1e-12) beklenen sayılmaz
        return None, None, "BEKLENEN_SIFIR"
    sabit = tah["guven_sabiti"]
    r = (n * gerceklesen / beklenen + sabit) / (n + sabit)
    return r, _kirp(r, tah), None


def yeterli_mi(n, tah):
    """Olgun dosya (sayı ya da sütun) yeterli veri eşiğinde mi. Altında puan yine geçerlidir,
    ekranda 'Yeterli veri yok' uyarısıyla gösterilir."""
    return round(n, 9) >= tah["yeterli_olgun_dosya"]


def olay_puani(gerceklesen, beklenen, tah):
    """Sayım bileşeni (sıklık, güncellik): (R, puan); güven ayarı olay sayısına uygulanır."""
    sabit = tah["olay_guven_sabiti"]
    r = (gerceklesen + sabit) / (beklenen + sabit)
    return r, _kirp(r, tah)


def puanla(tablo, tah):
    """Tabloya oranları, bileşen puanlarını, tahsilat puanını ve eksik nedenini ekler.

    tablo: n, maruziyet (payla tartılmış rücu tutarı), gerceklesen, beklenen, siklik_o,
    siklik_e, guncellik_o, guncellik_e. oran: gerçekleşen ÷ beklenen (beklenen yarım kuruştan
    küçükse boş); tahsilat_orani ve beklenen_oran rücu tutarına oranlardır; dosya_basina
    gerçekleşen ÷ n.
    """
    maruz = tablo["maruziyet"].where(tablo["maruziyet"] > 0)
    tablo = tablo.assign(
        oran=(tablo["gerceklesen"] / tablo["beklenen"]).where(tablo["beklenen"] >= YARIM_KURUS),
        tahsilat_orani=tablo["gerceklesen"] / maruz, beklenen_oran=tablo["beklenen"] / maruz,
        dosya_basina=(tablo["gerceklesen"] / tablo["n"]).where(tablo["n"] > 0))
    satirlar = []
    for s in tablo.itertuples():
        r, tutar, neden = puan_hesapla(s.n, s.gerceklesen, s.beklenen, tah)
        if neden:
            satirlar.append((None,) * len(PUANLAR) + (neden,))
            continue
        bilesen = {"tutar": yuvarla(tutar),
                   "siklik": yuvarla(olay_puani(s.siklik_o, s.siklik_e, tah)[1]),
                   "guncellik": yuvarla(olay_puani(s.guncellik_o, s.guncellik_e, tah)[1])}
        puan = agirlikli_toplam(bilesen, tah["bilesen_agirliklari"])
        satirlar.append((r, bilesen["tutar"], bilesen["siklik"], bilesen["guncellik"], puan, None))
    ek = pd.DataFrame(satirlar, columns=PUANLAR + ["eksik_nedeni"], index=tablo.index)
    return pd.concat([tablo, ek.astype({ad: float for ad in PUANLAR})], axis=1)
'''

DOSYALAR["tahsilat_tutar.py"] = r'''"""Tahsilat puanının tutar bileşeni: grup tahsilat oranı ve avukatın beklenen tahsilatı.

Oranlar yalnız avukata yazılan tahsilattan hesaplanır (Σ yazılan tahsilat ÷ Σ payla tartılmış
rücu tutarı). Grup tablosu grubun bütün oranını gösterir; avukatın beklentisi aynı gruptaki
diğer avukatların oranından kurulur (referans). Rücu tutarı sıfır olan dosyanın tahsilatı
sahibinin gerçekleşenine girer, ölçüt oranının payına girmez (paydada karşılığı yoktur; girseydi
diğer avukatların beklentisini yükseltirdi). Bu dosyaların evrenden çıkarılması Hukuk kararıdır.
"""
import pandas as pd

from avukat_perf.referans import tahsilat_orani


def grup_tablosu(pay, hareket, grup):
    """Grup başına dosya sayısı, rücu toplamı, avukata yazılan ve yazılamayan tahsilat."""
    tablo = pay.groupby(grup).agg(dosya_sayisi=("pay", "sum"),
                                  rucu_toplami=("maruziyet", "sum"))
    yazilan = hareket["avukat_kodu"].notna()
    tablo["atfedilen"] = hareket[yazilan].groupby(grup)["tutar"].sum()
    tablo["atanamayan"] = hareket[~yazilan].groupby(grup)["tutar"].sum()
    tablo = tablo.fillna(0.0)
    # Ekranda gösterilen grup oranı; beklenti diğer avukatların oranından gelir
    # (referans). Net tahsilatı eksi olan grupta (ör. ters kayıt) oran 0 gösterilir.
    oran = (tablo["atfedilen"] / tablo["rucu_toplami"]).where(
        (tablo["rucu_toplami"] > 0) & (tablo["atfedilen"] > 0), 0.0)
    return tablo.assign(oran=oran).reset_index()


def tutar(pay, hareket, grup, kirilim):
    """(grup tablosu, avukat × branş başına n, maruziyet, gerceklesen, beklenen).

    kirilim: grup sütunları ve brans. Beklenen = Σ diğer avukatların grup oranı × payla
    tartılmış rücu tutarı. hareket: kirilim ve rucu_tutari sütunlarıyla.
    """
    gruplar = grup_tablosu(pay, hareket, grup)
    anahtar = ["avukat_kodu"] + kirilim
    tablo = pd.concat([
        pay.groupby(anahtar).agg(n=("pay", "sum"), maruziyet=("maruziyet", "sum")),
        hareket.groupby(anahtar)["tutar"].sum().rename("gerceklesen"),
        hareket[hareket["rucu_tutari"] > 0].groupby(anahtar)["tutar"].sum().rename("referans")],
        axis=1).fillna(0.0)
    tablo = tablo.reset_index()
    oran = tahsilat_orani(tablo, grup, "referans", "maruziyet", True)  # 0 ya da eksi: ölçüt yok
    tablo["beklenen"] = tablo["maruziyet"] * oran
    return gruplar, tablo.groupby(["avukat_kodu", "brans"], as_index=False)[
        ["n", "maruziyet", "gerceklesen", "beklenen"]].sum()
'''

OZET = {
    "__init__.py": "dc82727b8e4d",
    "aciklama.py": "fe27ba7d3194",
    "aciklama_bicim.py": "95915dada551",
    "aciklama_ozet.py": "cbde10092d22",
    "aciklama_tahsilat.py": "7ee3346fc7a0",
    "agirlik.py": "ea925f6a0f1d",
    "atama.py": "17650ef6aa8c",
    "bayrak.py": "a4ff07cad74a",
    "bekleme.py": "8ebdeefa0038",
    "birlesik.py": "6f55c4693f7e",
    "donem.py": "350b4bad78f3",
    "gozlem.py": "aa57e2ab042d",
    "hazirlik.py": "03977aff2219",
    "kalite.py": "857daea97455",
    "kalite_alan.py": "692ac49cd667",
    "kalite_davranis.py": "38037fbacc67",
    "kalite_iliski.py": "29ffd32aeec5",
    "kalite_tarih.py": "f20faa89e1aa",
    "kalite_tur.py": "bce2c0ec98d8",
    "kriter1.py": "a6a481af7e7b",
    "kriter2.py": "481083acf3c9",
    "mantik.py": "cf0c768457a1",
    "olay.py": "cf7676096016",
    "ortak.py": "035e4dec73e2",
    "params.py": "4ec692fb7dab",
    "params_kural.py": "a36fab50d90c",
    "params_sema.py": "0560297ecde1",
    "params_tahsilat.py": "cd383f6cbebf",
    "params_veri.py": "5583b5fb97b8",
    "pencere.py": "ebff227eaa79",
    "portfoy.py": "ff971861785f",
    "referans.py": "e82c47e0a8f6",
    "sema.py": "f1fa10c75893",
    "sure_ozet.py": "84c368b1390d",
    "sure_puani.py": "c173762db5b8",
    "surum.py": "8cfbb2297311",
    "tahsilat.py": "7aa16c3304af",
    "tahsilat_evren.py": "2190397aaef9",
    "tahsilat_maruz.py": "79c210b5e620",
    "tahsilat_olay.py": "8d8dc656c159",
    "tahsilat_puan.py": "ee1d8c534ea4",
    "tahsilat_tutar.py": "865c761113ad",
}


# ---------- kütüphaneye yazma ----------
def _ozet(metin):
    satirlar = [satir.rstrip() for satir in metin.splitlines()]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return hashlib.sha256("\n".join(satirlar).encode("utf-8")).hexdigest()[:12]


def _cocuk(klasor, ad):
    if hasattr(klasor, "get_child"):
        return klasor.get_child(ad)
    return next((oge for oge in klasor.list() if oge.name == ad), None)


def _python_klasoru(kutuphane):
    for yol in ("/python", "python"):
        try:
            klasor = kutuphane.get_folder(yol)
        except Exception:  # sürüme göre yol biçimi değişir
            klasor = None
        if klasor is not None:
            return klasor
    raise SystemExit("Kütüphanede python klasörü bulunamadı; kurulum rehberindeki elle yapıştırma "
                     "yolunu izleyin.")


def kur():
    proje = dataiku.api_client().get_default_project()
    if not hasattr(proje, "get_library"):
        raise SystemExit("Bu Dataiku sürümünde kütüphane API'si yok; kurulum rehberindeki Git "
                         "ya da elle yapıştırma yolunu izleyin.")
    python = _python_klasoru(proje.get_library())
    klasor = _cocuk(python, PAKET) or python.add_folder(PAKET)
    hatali = []
    for ad in sorted(DOSYALAR):
        dosya = _cocuk(klasor, ad) or klasor.add_file(ad)
        dosya.write(DOSYALAR[ad])
        okunan = dosya.read()
        okunan = okunan.decode("utf-8") if isinstance(okunan, bytes) else okunan
        print("{}/{} {}".format(PAKET, ad, _ozet(okunan)))
        if _ozet(okunan) != OZET[ad]:
            hatali.append(ad)
    if hatali:
        raise SystemExit("Geri okunan içerik farklı: " + ", ".join(hatali))
    print("{}: {} dosya yazıldı ve doğrulandı. Not defterinin çekirdeğini yeniden başlatın."
          .format(PAKET, len(DOSYALAR)))


kur()
