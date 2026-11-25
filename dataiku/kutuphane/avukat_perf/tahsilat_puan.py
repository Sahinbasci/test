"""Tahsilat puanının bileşen puanları ve birleşimi (avukat ve avukat × branş tablosu için).

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
