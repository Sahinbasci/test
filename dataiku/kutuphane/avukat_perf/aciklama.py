"""'Neden bu puanı aldı?' açıklaması.

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
