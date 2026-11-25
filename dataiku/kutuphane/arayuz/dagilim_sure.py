"""Kriter 1 ilk işlem süresi dağılımının verisi (sayım; puan hesaplanmaz).

Kapanan dönemler eşik kuralına göre ayrı sayılır (kural: OTO gün kuralı, OTO_DISI takvim ayı
kuralı; hesap anında sonuca yazılan esik_kurali'ndan; sütun yoksa TUMU). Her kural için:
- KUTU: ilk işlem süresi 5 günlük kutularda (alt, ust; ust boşsa açık uçlu son kutu), dönemin
  kapanmadan önce ulaştığı en yüksek bayrağa göre. Uzun kuyruk son kutuda toplanır (en çok 20).
- ESIK: bayrak eşikleri, hesap anında yazılan eşik günlerinden (esik_gun_sari,
  esik_gun_turuncu; süreyle aynı ölçekte, haklı bekleme hariç). Birbirine en çok ESIK_ARALIK
  gün yakın değerler tek aralıkta toplanır (takvim ayı kuralında 59–62. gün gibi): alt ve ust
  aralığın ilk ve son günüdür (adet boş: ekranda gösterilmez). Ekran eşiği parametreden
  değil bu satırlardan çizer; eşik sütunlarını taşımayan eski tabloda eşik satırı yoktur.
toplam ve ortanca, kuralın kapanan dönem sayısı ve ortanca süresidir.
"""
import pandas as pd

from avukat_perf.ortak import birlestir

SURE_KUTU = 5
SURE_EN_COK_KUTU = 20
BAYRAKSIZ = "YOK"
ESIK_ARALIK = 3
ESIKLER = (("SARI", "esik_gun_sari"), ("TURUNCU", "esik_gun_turuncu"))
KURAL_SIRASI = {"OTO": 0, "OTO_DISI": 1}
SUTUNLAR = ["tur", "kural", "alt", "ust", "bayrak", "adet", "toplam", "ortanca"]


def _kutular(kapanan, gun):
    son_kutu = min(int(gun.max() // SURE_KUTU), SURE_EN_COK_KUTU - 1)
    alt = (gun // SURE_KUTU).clip(upper=son_kutu).astype(int) * SURE_KUTU
    bayrak = kapanan.get("en_yuksek_seviye", pd.Series(None, index=kapanan.index,
                                                       dtype=object)).fillna(BAYRAKSIZ)
    sayim = pd.DataFrame({"alt": alt, "bayrak": bayrak}).groupby(
        ["alt", "bayrak"]).size().rename("adet").reset_index()
    izgara = pd.MultiIndex.from_product(
        [range(0, (son_kutu + 1) * SURE_KUTU, SURE_KUTU), sorted(set(bayrak))],
        names=["alt", "bayrak"])
    sayim = sayim.set_index(["alt", "bayrak"]).reindex(izgara, fill_value=0).reset_index()
    son = sayim["alt"] == son_kutu * SURE_KUTU
    acik_uclu = bool(gun.max() >= (son_kutu + 1) * SURE_KUTU)
    return sayim.assign(tur="KUTU", ust=(sayim["alt"] + SURE_KUTU).where(~(son & acik_uclu)))


def _esikler(kapanan):
    satirlar = []
    for bayrak, sutun in ESIKLER:
        gunler = kapanan[sutun].dropna().astype(int) if sutun in kapanan.columns else []
        araliklar = []
        for deger in sorted(set(gunler)):
            if araliklar and deger - araliklar[-1][1] <= ESIK_ARALIK:
                araliklar[-1][1] = deger
            else:
                araliklar.append([deger, deger])
        satirlar += [{"tur": "ESIK", "bayrak": bayrak, "alt": alt, "ust": ust}
                     for alt, ust in araliklar]
    return pd.DataFrame(satirlar, columns=["tur", "bayrak", "alt", "ust"])


def _kural(kapanan):
    gun = kapanan["sure_gun"].astype(float).clip(lower=0)
    tablo = birlestir([_kutular(kapanan, gun), _esikler(kapanan)],
                      ["tur", "alt", "ust", "bayrak", "adet"])
    return tablo.assign(toplam=len(kapanan), ortanca=float(gun.median()))


def k1_sure(k1):
    """Kapanan Kriter 1 dönemlerinin kural başına süre kutuları ve eşikleri (yoksa None)."""
    if k1 is None or k1.empty:
        return None
    kapanan = k1[(k1["seviye"] == "KAPANDI") & k1["sure_gun"].notna()]
    if kapanan.empty:
        return None
    kural = kapanan.get("esik_kurali", pd.Series("TUMU", index=kapanan.index)).fillna("TUMU")
    parcalar = [_kural(kapanan[kural == ad]).assign(kural=ad)
                for ad in sorted(set(kural), key=lambda ad: (KURAL_SIRASI.get(ad, 9), ad))]
    return birlestir(parcalar, SUTUNLAR)
