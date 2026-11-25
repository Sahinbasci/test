"""Beklentinin karşılaştırma ölçütü: aynı gruptaki DİĞER avukatların oranı (tahsilat ve süre).

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
