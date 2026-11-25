"""Sunum yardımcıları: JSON'a uygun değer, sözleşmeye göre kayıt listesi, küçük toplamlar.

Bir bileşene giden her kayıt tam olarak sözleşmedeki alanları taşır: fazlası gönderilmez,
eksiği None olur. Tarih "YYYY-AA-GG" (saat varsa "YYYY-AA-GG SS:DD") metnine çevrilir.
"""
import math

import pandas as pd

from avukat_perf.mantik import dogru_mu, dogru_seri
from arayuz.sozlesme import BILESENLER, SECIMLIK_SUTUNLAR
from hat import butunluk, gecmis, model

SEVIYE_SIRASI = {"KIRMIZI": 0, "TURUNCU": 1, "SARI": 2, "IZLENIYOR": 3}
# Sonuç tablolarının mantıksal sütunları: Dataiku boş değerli mantıksal sütunu metin okur.
MANTIKSAL = ("golge", "golge_zorunlu", "gonderilecek", "esas_tarihi_bilinmiyor", "dusum",
             "pencerede_dusum", "yeterli", "son_ay_kismi", "yil_ici")
SOZLESME_SUTUNLARI = {}  # tablo -> bileşenlerin okuduğu, tabloda bulunması gereken sütunlar
for _bilesen in BILESENLER.values():
    for _tablo, _sutunlar in _bilesen["kaynak"].items():
        SOZLESME_SUTUNLARI.setdefault(_tablo, set()).update(
            set(_sutunlar) - set(SECIMLIK_SUTUNLAR.get(_tablo, ())))


def deger(ham):
    """Pandas/numpy değerini JSON'a uygun Python değerine çevirir."""
    if ham is None or (isinstance(ham, float) and math.isnan(ham)):
        return None
    if not isinstance(ham, (list, dict, str)) and pd.isna(ham):
        return None
    if isinstance(ham, pd.Timestamp):
        return ham.strftime("%Y-%m-%d" if ham == ham.normalize() else "%Y-%m-%d %H:%M")
    if hasattr(ham, "item"):
        ham = ham.item()
        return None if isinstance(ham, float) and math.isnan(ham) else ham
    return ham


def kayitlar(bilesen, tablo):
    """Tablo satırlarını bileşenin alanlarıyla kayıt listesine çevirir."""
    alanlar = BILESENLER[bilesen]["alanlar"]
    if tablo is None or tablo.empty:
        return []
    tablo = tablo.assign(**{ad: None for ad in alanlar if ad not in tablo.columns})
    return [{ad: deger(veri) for ad, veri in zip(alanlar, satir)}
            for satir in tablo[alanlar].itertuples(index=False, name=None)]


def ay_izgarasi(tablo, secilen, sutunlar):
    """Aylık değerler (secilen) hesap anındaki takvim ayı ızgarasına yayılır: tahsilatsız ay
    sıfır, kesitte bitmeyen son ay kismi. Izgara tablonun kendisindedir (ilk_ay, son_ay,
    son_ay_kismi); bu sütunları taşımayan eski tabloda yalnız kaydı olan aylar gösterilir."""
    toplam = secilen.groupby("ay")[sutunlar].sum()
    kismi_ay = None
    if len(tablo) and "ilk_ay" in tablo.columns:
        ilk, son = tablo["ilk_ay"].iloc[0], tablo["son_ay"].iloc[0]
        aylar = [str(ay) for ay in pd.period_range(ilk, son, freq="M")]
        toplam = toplam.reindex(aylar, fill_value=0)
        kismi_ay = son if dogru_mu(tablo["son_ay_kismi"].iloc[0]) else None
    sonuc = toplam.rename_axis("ay").reset_index()
    return sonuc.assign(kismi=sonuc["ay"] == kismi_ay)


def tek(bilesen, sozluk):
    """Tek kayıtlık bileşen (özet göstergeler)."""
    return [{ad: deger(sozluk.get(ad)) for ad in BILESENLER[bilesen]["alanlar"]}]


def topla(tablo, sutun):
    return None if tablo is None else float(tablo[sutun].sum())


def oran(pay, payda):
    return None if pay is None or not payda else pay / payda


def secili(tablo, sutun, deger_):
    """tablo[sutun] == deger_ satırları; tablo yoksa None."""
    return None if tablo is None else tablo[tablo[sutun] == deger_]


def seviye_sirala(tablo, ek=("sure_gun",)):
    """Seviye ağırlığına (KIRMIZI önce) ve ek sütunlara (azalan) göre sıralar."""
    sira = tablo["seviye"].map(SEVIYE_SIRASI).fillna(9)
    tablo = tablo.assign(_sira=sira)
    return tablo.sort_values(["_sira"] + list(ek), ascending=[True] + [False] * len(ek)).drop(
        columns="_sira")


def guncel_tablolar(tablolar):
    """Son başarılı gecede üretilmemiş, başka bir gecenin etiketini taşıyan ya da o gecenin
    yazdığı satır sayısını tutmayan sonuc_, model_ ve çelişki tabloları None sayılır; hiç
    başarılı gece yoksa hiçbiri gösterilmez. Sözleşmenin okuduğu bir sütunu (gruplamaya bağlı
    SECIMLIK_SUTUNLAR hariç) taşımayan sonuc_, model_ ve dönem tablosu da None'dır (tek kural).
    Bayrak olaylarından yalnız başarılı gecelerde yazılanlar kalır. Örnek: dava takip
    bağlantısı kaldırılırsa eski sonuc_k1 durur ama gösterilmez; yarıda kesilen gecenin yeni
    tahsilat tablosu eski birleşik puanla yan yana çıkmaz.
    """
    kayit = mantiksal(tablolar.get("calisma_kaydi"))
    uretilen, kimlik = gecmis.son_sayilar(kayit), gecmis.son_kimlik(kayit)

    def suz(ad, tablo):
        if ad == "bayrak_olay":
            return butunluk.basarili_satirlar(tablo, kayit)
        if tablo is not None and SOZLESME_SUTUNLARI.get(ad, set()) - set(tablo.columns) and \
                ad.startswith(("sonuc_", "model_", "birlesik_donem")):
            return None  # eski biçim (kod aktarımından önceki gece): ilk gecede yeniden yazılır
        if not ad.startswith(("sonuc_", "model_")) and ad != "olay_celiski":
            return tablo
        uygun = ad in uretilen and model.etiket_uygun(tablo, kimlik, uretilen[ad])
        return tablo if uygun else None
    return {ad: mantiksal(suz(ad, tablo)) for ad, tablo in tablolar.items()}


def mantiksal(tablo):
    """MANTIKSAL sütunları gerçek True/False yapar ("false" metni True okunmaz)."""
    if tablo is None:
        return None
    sutunlar = [ad for ad in MANTIKSAL if ad in tablo.columns]
    return tablo.assign(**{ad: dogru_seri(tablo[ad]) for ad in sutunlar}) if sutunlar else tablo
