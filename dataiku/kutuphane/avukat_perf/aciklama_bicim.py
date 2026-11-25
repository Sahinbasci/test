"""Açıklama metinlerinin ortak parçaları: neden metinleri ve Türkçe sayı biçimi."""
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
