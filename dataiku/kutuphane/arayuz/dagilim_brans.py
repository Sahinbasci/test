"""Branş bazında gerçekleşen / beklenen tahsilat oranının dağılımı (kutu grafiği verisi).

Avukat × branş kırılımından (sonuc_tahsilat_brans) yalnız o branşta yeterli veri eşiğine
ulaşan (yeterli; kural hesap anında yazılır) ve oranı olan satırlar sayılır: az dosyalı
satırın oranı şansa çok bağlıdır. Oran 1 beklenen düzeydir. Satır türleri (tur):
- KUTU: branş başına sayılan avukat (adet), çeyrekler (ceyrek_alt, ortanca, ceyrek_ust; doğrusal
  ara değer), bıyıklar (biyik_alt, biyik_ust: çeyrekler arası açıklığın 1,5 katı içindeki en uç
  oranlar, Tukey) ve eşiğe ulaşmadığı ya da oranı olmadığı (beklenen yok) için sayılmayan
  avukat (disarida). Hiç sayılan avukatı
  olmayan branşın çeyrekleri boştur.
- AYKIRI: bıyıkların dışındaki her avukat (avukat_kodu, oran).
Branşlar sayılan avukat sayısına göre çoktan aza, eşitlikte ada göre sıralanır.
"""
import pandas as pd

from avukat_perf.mantik import dogru_seri

TUKEY = 1.5
SUTUNLAR = ["tur", "brans", "adet", "ceyrek_alt", "ortanca", "ceyrek_ust", "biyik_alt",
            "biyik_ust", "disarida", "avukat_kodu", "oran"]


def _kutu(ad, oranlar, disarida):
    if oranlar.empty:
        return {"tur": "KUTU", "brans": ad, "adet": 0, "disarida": disarida}, oranlar
    q1, ortanca, q3 = (float(oranlar.quantile(oran)) for oran in (0.25, 0.5, 0.75))
    acik = TUKEY * (q3 - q1)
    icerde = oranlar[(oranlar >= q1 - acik) & (oranlar <= q3 + acik)]
    return ({"tur": "KUTU", "brans": ad, "adet": len(oranlar), "ceyrek_alt": q1,
             "ortanca": ortanca, "ceyrek_ust": q3, "biyik_alt": float(icerde.min()),
             "biyik_ust": float(icerde.max()), "disarida": disarida}, oranlar.drop(icerde.index))


def oran_kutulari(brans):
    """Branş başına kutu ve aykırı satırları; tablo yoksa ya da eski biçimdeyse None."""
    if brans is None or brans.empty or "yeterli" not in brans.columns:
        return None
    sayilan = dogru_seri(brans["yeterli"]) & brans["oran"].notna()
    adet = sayilan.groupby(brans["brans"]).sum()
    sira = sorted(adet.index, key=lambda ad: (-adet[ad], str(ad)))
    satirlar = []
    for ad in sira:
        bu = brans["brans"] == ad
        oranlar = brans.loc[bu & sayilan, "oran"].astype(float)
        kutu, aykiri = _kutu(ad, oranlar, int((bu & ~sayilan).sum()))
        satirlar.append(kutu)
        satirlar += [{"tur": "AYKIRI", "brans": ad, "avukat_kodu": brans.at[i, "avukat_kodu"],
                      "oran": float(deger)} for i, deger in aykiri.sort_values().items()]
    return pd.DataFrame(satirlar, columns=SUTUNLAR)
