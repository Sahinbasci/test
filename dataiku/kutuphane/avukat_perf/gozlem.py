"""Gözlem: gecelik anlık görüntülerden bir alanın ilk dolu görüldüğü günü sabitler.

Kaynak sistem bir alanın ilk giriş tarihini tutmuyorsa (ör. dava takip esas numarası) her gece
alınan görüntü bu tarihi bizim tarafta sabitler. Bir anahtarın değeri ilk kez dolu
görüldüğünde satır eklenir; değer sonra değişse de satır değişmez (yalnız ekleme).
Tarih avukat lehine en erken olası gündür: önceki başarılı çekimin günü. Çekim gece (02:00)
yapıldığı için önceki çekimde görülmeyen değer o günün geri kalanında girilmiş olabilir.
Kaynak tarihi (ör. dava takip sisteminin takip tarihi) [önceki çekim günü, bu çekim günü]
aralığına düşüyorsa o kullanılır (dayanak KAYNAK_TARIHI). Kaçan gece bu yüzden avukatın
aleyhine işlemez. İlk çekimde zaten dolu olan değer arşiv öncesidir: çekimden önceki bir kaynak
tarihi varsa o, yoksa tarih bilinmiyor; ilk_gorulme o zaman değerin en geç hangi gün var
olduğunu gösterir.
"""
import pandas as pd

from avukat_perf.ortak import birlestir, gun, tek_gun

SUTUNLAR = ["anahtar", "ilk_deger", "ilk_gorulme", "onceki_basarili_cekim", "ilk_tarih",
            "dayanak", "tarih_bilinmiyor"]


def bos():
    """Boş gözlem tablosu."""
    return pd.DataFrame(columns=SUTUNLAR)


def guncelle(mevcut, goruntu, anahtar, deger, cekim_tarihi, onceki_basarili=None,
             kaynak_tarihi=None):
    """Görüntüde değeri ilk kez dolu görülen anahtarlar için satır ekler.

    onceki_basarili: bir önceki başarılı çekimin günü; None ise bu ilk çekimdir.
    kaynak_tarihi: görüntüde kaynak sistemin verdiği tarih sütununun adı (isteğe bağlı).
    """
    mevcut = bos() if mevcut is None else mevcut
    cekim = tek_gun(cekim_tarihi)
    metin = goruntu[deger].astype(str).str.strip()
    dolu = goruntu[goruntu[deger].notna() & (metin != "")].drop_duplicates(anahtar)
    yeni = dolu[~dolu[anahtar].isin(set(mevcut["anahtar"]))]
    if yeni.empty:
        return mevcut
    kaynak = (gun(yeni[kaynak_tarihi], zorla=True) if kaynak_tarihi
              else pd.Series(pd.NaT, index=yeni.index))
    if onceki_basarili is None or pd.isna(onceki_basarili):
        onceki, dayanak = pd.NaT, "ARSIV_ONCESI"
        ilk = kaynak.where(kaynak <= cekim)
    else:
        onceki = tek_gun(onceki_basarili)
        aralikta = (kaynak >= onceki) & (kaynak <= cekim)
        ilk = kaynak.where(aralikta, onceki)
        dayanak = aralikta.map({True: "KAYNAK_TARIHI", False: "GECELIK_GOZLEM"}).values
    satirlar = pd.DataFrame({
        "anahtar": yeni[anahtar].values, "ilk_deger": yeni[deger].astype(str).values,
        "ilk_gorulme": cekim, "onceki_basarili_cekim": onceki,
        "ilk_tarih": pd.to_datetime(ilk.values), "dayanak": dayanak})
    satirlar["tarih_bilinmiyor"] = tarih_bilinmiyor(satirlar)
    return birlestir([mevcut, satirlar], SUTUNLAR)


def tarih_bilinmiyor(gozlem_tablosu):
    """İlk giriş günü bilinmeyen (arşiv öncesi) satırlar (bool Series): işaretin tek tanımı.
    Saklanan tarih_bilinmiyor sütunu bilgi içindir; okunurken türü yorumlanmaz."""
    return pd.to_datetime(gozlem_tablosu["ilk_tarih"]).isna()


def tarih_esle(gozlem_tablosu):
    """anahtar -> ilk_tarih eşlemesi (Series); tablo yoksa boş."""
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    return pd.to_datetime(gozlem_tablosu.set_index("anahtar")["ilk_tarih"])


def baslangic_esle(gozlem_tablosu):
    """anahtar -> başlangıç olarak kullanılacak en geç olası ilk giriş günü.

    ilk_tarih bitiş için avukat lehine en erken gündür; başlangıçta en erken gün avukatın
    aleyhinedir (eşikler öne çekilir). Kaynak tarihi aralıktaysa o, değilse değerin görüldüğü
    çekim günü kullanılır.
    """
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    tablo = gozlem_tablosu
    ilk = pd.to_datetime(tablo["ilk_tarih"])
    kaynak = ilk.notna() & tablo["dayanak"].isin(["ARSIV_ONCESI", "KAYNAK_TARIHI"])
    deger = ilk.where(kaynak, pd.to_datetime(tablo["ilk_gorulme"]))
    return pd.Series(deger.values, index=tablo["anahtar"].values)


def bilinmeyen_esle(gozlem_tablosu):
    """Değeri var ama ilk giriş günü bilinmeyen (arşiv öncesi) anahtarlar -> ilk görüldüğü
    çekim günü; değer en geç o gün vardı. Tablo yoksa boş."""
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    secili = gozlem_tablosu[tarih_bilinmiyor(gozlem_tablosu).values]
    return pd.to_datetime(secili.set_index("anahtar")["ilk_gorulme"])


def kapanislar(gozlem_tablosu, kesit):
    """Koşul gözleminden kesitte tahsile kapalı dosyaların kapanış günü (Series, indeks dosya_no;
    arşiv öncesi kapanmış, günü bilinmeyen dosyada NaT). Kesitten sonra kapanan açık sayılır.

    Tahsilatta avukat lehine gün en geç olası gündür (kapanışın görüldüğü çekim günü): araya
    kaçan gece girse de dosyayı kapatan tahsilat sıklık ve güncellikte sayılır. Kriter 2 bitişi
    en erken günü kullanır (tarih_esle).
    """
    if gozlem_tablosu is None or gozlem_tablosu.empty:
        return pd.Series(dtype="datetime64[ns]")
    tablo = gozlem_tablosu
    ilk = pd.to_datetime(tablo["ilk_tarih"])
    gun = ilk.where(tablo["dayanak"] != "GECELIK_GOZLEM", pd.to_datetime(tablo["ilk_gorulme"]))
    secili = ilk.isna() | (ilk <= tek_gun(kesit))
    return pd.Series(gun[secili].values, index=tablo.loc[secili, "anahtar"].values)
