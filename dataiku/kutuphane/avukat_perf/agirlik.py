"""Birleşik puanın sütun ağırlıkları: ikili karşılaştırmalardan (Analitik Hiyerarşi Süreci).

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
