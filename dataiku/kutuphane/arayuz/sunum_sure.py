"""Süre Takibi sayfası verisi: seviye sayıları, dosya listesi, bayrak olayları, e-posta özeti.

Filtresiz liste açık dönemleri (izlenen, sarı, turuncu, kırmızı) ve düşüm tarihi süre puanı
penceresine düşen dönemleri (hesapta işaretlenir: pencerede_dusum) içerir. Seviye seçilirse o
seviyedeki bütün dönemler listelenir (kapanan, sonlanan, kapsam dışı ve nedeni dahil). En ağır
seviye ve en uzun süre önce, en çok 500 satır. secim içindeki kriter, seviye ve avukat
filtreleri sınırdan önce uygulanır; hesap yapılmaz.
Filtre bileşeni sınırdan önceki toplamı ve ölçülen dönemi olan bütün avukatları verir. Olaylar
gösterilen dönemlerin olayları ve filtreye uyan bütün dönemlerin en yeni SON_OLAY olayıdır;
bunlar son_sira (1 en yeni) taşır, ekran "Son Bayrak Olayları"nı yalnız bu sırayla basar. Eşit
tarihte sıra olayın kalıcı anahtarıyla belirlenir (satır sırasından bağımsız).
"""
import pandas as pd

from avukat_perf.mantik import dogru_seri
from avukat_perf.olay import kaynakli
from avukat_perf.ortak import gun
from arayuz import dagilim_sure
from arayuz.temel import kayitlar, seviye_sirala

ACIK_DONEM = ("IZLENIYOR", "SARI", "TURUNCU", "KIRMIZI")  # listede her zaman olan seviyeler
EN_COK = 500
SON_OLAY = 30
FILTRE = {"kriter": "kriter", "seviye": "seviye", "avukat": "avukat_kodu"}


def _birlesik(tablolar):
    parcalar = [tablolar[ad].assign(kriter=kriter) for ad, kriter in
                (("sonuc_k1", "K1"), ("sonuc_k2", "K2")) if tablolar.get(ad) is not None]
    return pd.concat(parcalar, ignore_index=True) if parcalar else None


def _olaylar(olay, tum, liste):
    """Gösterilen dönemlerin olayları ile filtreye uyan dönemlerin en yeni olayları; olaylar
    dönemin bugünkü esas kaynağından (yedek yoldan geçişte eski kaynağın olayları gösterilmez)."""
    anahtar = ["dosya_no", "avukat_kodu", "atama_tarihi", "kriter", "esas_kaynagi"]
    olay = kaynakli(olay).assign(atama_tarihi=gun(olay["atama_tarihi"]))
    tum, liste = kaynakli(tum), kaynakli(liste)

    def eslesen(donemler):
        return olay.merge(donemler[anahtar].assign(atama_tarihi=gun(donemler["atama_tarihi"])),
                          on=anahtar)
    yeni = eslesen(tum).sort_values(["olay_tarihi"] + anahtar + ["seviye"], ascending=[False] + [
        True] * (len(anahtar) + 1), kind="mergesort").head(SON_OLAY)
    yeni = yeni.assign(son_sira=range(1, len(yeni) + 1))
    secilen = pd.concat([yeni, eslesen(liste)], ignore_index=True).drop_duplicates(
        anahtar + ["seviye"])
    return secilen.sort_values(anahtar + ["olay_tarihi"])


def sure(tablolar, secim=None):
    tablo = _birlesik(tablolar)
    if tablo is None:
        return {}
    sayilar = tablo.groupby(["kriter", "seviye"]).size().rename("adet").reset_index()
    sonuc = {"sure.seviyeler": kayitlar("sure.seviyeler", sayilar),
             "sure.ilk_islem_dagilim": kayitlar("sure.ilk_islem_dagilim", dagilim_sure.k1_sure(
                 tablolar.get("sonuc_k1")))}
    # Sütunu taşımayan (aktarımdan önceki gecenin) tabloda yalnız açık dönemler listelenir.
    pencere = tablo.get("pencerede_dusum", pd.Series(False, index=tablo.index))
    tum = tablo if (secim or {}).get("seviye") else tablo[
        tablo["seviye"].isin(ACIK_DONEM) | dogru_seri(pencere)]
    # Seçenek: ölçülen (kapsam dışı olmayan) dönemi bulunan bütün avukatlar; sulh avukatı yok.
    olculen = tablo.loc[tablo["seviye"] != "KAPSAM_DISI", "avukat_kodu"]
    avukatlar = sorted(olculen.dropna().unique())
    for ad, sutun in FILTRE.items():
        if (secim or {}).get(ad):
            tum = tum[tum[sutun] == secim[ad]]
    liste = seviye_sirala(tum).head(EN_COK)
    sonuc["sure.filtre"] = [{"toplam": len(tum), "gosterilen": len(liste),
                             "avukatlar": [str(kod) for kod in avukatlar]}]
    sonuc["sure.liste"] = kayitlar("sure.liste", liste)
    olay = tablolar.get("bayrak_olay")
    if olay is not None:
        sonuc["sure.olaylar"] = kayitlar("sure.olaylar", _olaylar(olay, tum, liste))
    eposta = tablolar.get("sonuc_eposta")
    if eposta is not None:
        # Gönderim kriter bazındadır (yedek yolda yalnız Kriter 1 gölgede): avukatın gönderilecek
        # ve gönderilmeyecek gecikmeleri ayrı satırda sayılır.
        gonder = dogru_seri(eposta["gonderilecek"])
        say = pd.crosstab([eposta["avukat_kodu"], gonder.rename("gonderilecek")],
                          eposta["seviye"])
        say = say.reindex(columns=["SARI", "TURUNCU", "KIRMIZI"], fill_value=0)
        say.columns = ["sari", "turuncu", "kirmizi"]
        say = say.assign(toplam=say.sum(axis=1)).reset_index()
        sonuc["sure.eposta"] = kayitlar("sure.eposta", say[
            ["avukat_kodu", "sari", "turuncu", "kirmizi", "toplam", "gonderilecek"]].sort_values(
                ["kirmizi", "toplam"], ascending=False))
    return sonuc
