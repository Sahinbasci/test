"""Hukuki Kalite (kalite) ile Davranış ve İletişim (davranis) sütun puanları; kaynak
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
