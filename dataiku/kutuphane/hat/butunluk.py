"""Yalnız eklenen tabloların (gözlem, bayrak olayı, çalışma kaydı, dönem yayını) korunması.

Bu tablolar her çalışmada mevcut + yeni olarak baştan yazılır. Okunan tablo son başarılı
çalışmanın yazdığından azsa (kesik yazım ya da elle temizleme) çalışma durur: aksi hâlde geçmiş
kalıcı olarak kaybolur (ör. gözlem tablosu boş okunursa bütün esaslar yeni görülmüş sayılır).
Beklenen satır sayısı tablonun son yazıldığı başarılı çalışmadandır: araya o tabloyu yazmayan
bir gece (ör. kaynağı beklenen gözlem) girse de denetim sürer. Çalışma kaydı boş okunurken bu
tablolardan biri doluysa da çalışma durur: kayıt kaybolmuştur, hat ilk geceymiş gibi sürmez.
Bayrak olaylarından yalnız başarılı gecelerde yazılanlar kullanılır.
"""
from hat.gecmis import basarili_calismalar, sayilar
from hat.veri_kumeleri import DONEM, GOZLEM

EKLENEN = GOZLEM + ("bayrak_olay",) + DONEM


def basarili_satirlar(tablo, kayit):
    """Yalnız eklenen tablonun (bayrak olayı) başarılı gecelerde yazılmış satırları.

    Yazımı yarıda kesilen gecenin satırları ekrana ve sonraki gecenin birleştirmesine girmez;
    aynı olay sonraki başarılı gecede kendi kimliğiyle yeniden yazılır.
    """
    if tablo is None:
        return None
    gece = basarili_calismalar(kayit)
    kimlikler = set() if gece is None else set(gece["calisma_kimligi"].astype(str))
    return tablo[tablo["calisma_kimligi"].astype(str).isin(kimlikler)].reset_index(drop=True)


def veri_kaybi(kayit, tablolar, tur="GECELIK"):
    """Yalnız eklenen tablolardan, son başarılı çalışmanın yazdığından az satırla okunanlar.

    Kesik ya da elle temizlenmiş tablo baştan yazılırsa geçmiş kaybolur (ör. gözlem tablosu
    boş okunursa bütün esaslar yeni görülmüş sayılır); bu durumda çalışma durur.
    """
    beklenen = _beklenen(kayit, tur)
    eksik = []
    for ad, tablo in sorted(tablolar.items()):
        okunan = 0 if tablo is None else len(tablo)
        if beklenen.get(ad) is not None and okunan < beklenen[ad]:
            eksik.append("{} ({} satır bekleniyordu, {} okundu)".format(ad, beklenen[ad], okunan))
    if eksik:
        raise ValueError("VERI_KAYBI: " + "; ".join(eksik))


def _beklenen(kayit, tur):
    """{tablo: satır sayısı}: her tablonun son yazıldığı başarılı çalışmadaki sayısı."""
    beklenen, secili = {}, basarili_calismalar(kayit, tur)
    for _, satir in ([] if secili is None else secili.iterrows()):
        for ad, sayi in sayilar(satir).items():
            if sayi is not None or ad not in beklenen:
                beklenen[ad] = sayi
    return beklenen


def kayitsiz_gecmis(ortam, kayit):
    """Çalışma kaydı boş ya da yokken yalnız eklenen tablolardan biri dolu mu: çalışma durur
    ve kayda yazılmaz (sonraki çalışmalar da durur). İlk kurulumda bu tablolar boştur."""
    if kayit is not None and not kayit.empty:
        return
    dolu = []
    for ad in EKLENEN:
        tablo = ortam.tablo_oku(ad)
        if tablo is not None and not tablo.empty:
            dolu.append(ad)
    if dolu:
        raise ValueError("VERI_KAYBI: calisma_kaydi boş ama yalnız eklenen tablolar dolu: "
                         + ", ".join(dolu))
