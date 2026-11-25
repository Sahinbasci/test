"""Her sayfa yanıtındaki ortak bileşenler: üst şerit (ortak.durum) ve ekran adları (ortak.adlar).

Şerit: gösterilen verinin kesiti, hesap sürümü ve gölge durumu son BAŞARILI geceden (ekrandaki
tabloları seçen tanım: hat.gecmis.son_basarili_gece), son kararlar son gecelik ve son dönem
sonu çalışmasından. Gölge kriter bazındadır: parametreyle açılan gölge iki kriteri, yedek yolun
zorunlu gölgesi yalnız Kriter 1'i kapsar. Okunamayan tablolar, geçersiz parametre ve son gecede
bağlantısı beklenen kaynaklar da şeride gelir. Ekran adları params.json gorunum bölümündendir
(sistem, branş, alt başlık ve mevcut alan adları); branşın sırası renk paletindeki yeridir.
"""
import pandas as pd

from avukat_perf.mantik import dogru_mu
from avukat_perf.params_sema import GORUNUM
from avukat_perf.sema import SISTEMLER
from avukat_perf.surum import hesap_surumu
from arayuz.temel import tek, topla
from hat import gecmis
from hat.calisma import OZET

BEKLENIYOR = "KAYNAK_BEKLENIYOR"


def _son_karar(kayit, tur):
    """Türün (GECELIK, DONEM_SONU) son özet satırının kararı; başlangıç anına göre."""
    if kayit is None or kayit.empty:
        return None
    ozet = kayit[(kayit["kaynak"] == OZET) & (kayit["tur"] == tur)]
    if ozet.empty:
        return None
    return ozet.assign(_bas=pd.to_datetime(ozet["baslangic"])).sort_values("_bas")[
        "durum"].iloc[-1]


def ortak_durum(tablolar, params, okunamayan=(), hatalar=()):
    """okunamayan: arka ucun okuyamadığı tablolar; hatalar: parametre doğrulamasının iletileri.
    Sonuçların hesap sürümü o gecenin kaydındandır; parametre ya da kod sonra değiştiyse
    kural_degisti doğrudur (geçersiz parametrede söylenmez: önce parametre düzeltilmelidir)."""
    kayit = tablolar.get("calisma_kaydi")
    son = gecmis.son_basarili_gece(kayit)
    if son is None:  # hiç başarılı gece yok: parametredeki gölge
        k1 = k2 = dogru_mu((params.get("uyari") or {}).get("golge_mod"))
    else:
        k2 = dogru_mu(son.get("golge"))
        k1 = k2 or dogru_mu(son.get("golge_zorunlu"))
    ozet = {"golge_mod": k1 or k2, "golge_ilk_islem": k1, "golge_dava_acma": k2,
            "kural_degisti": False,
            "acik_kirmizi": topla(tablolar.get("sonuc_sure_ozet"), "acik_kirmizi"),
            "son_karar": _son_karar(kayit, "GECELIK"),
            "son_donem_karari": _son_karar(kayit, "DONEM_SONU"),
            "okunamayan": sorted(okunamayan), "parametre_hatasi": "; ".join(hatalar) or None,
            "bekleyen_kaynaklar": []}
    if son is not None:
        surum = son.get("hesap_surumu")
        gece = kayit[(kayit["calisma_kimligi"] == son["calisma_kimligi"]) &
                     (kayit["kaynak"] != OZET) & (kayit["durum"] == BEKLENIYOR)]
        ozet.update(kesit=son["cekim_tarihi"], son_guncelleme=son["bitis"], hesap_surumu=surum,
                    bekleyen_kaynaklar=sorted(gece["kaynak"].astype(str)),
                    kural_degisti=not hatalar and isinstance(surum, str)
                    and surum != hesap_surumu(params))
    return tek("ortak.durum", ozet)


def adlar(params):
    """Ekran adları: tur (sistem, brans, alt_baslik, mevcut_alan), kod, ad ve branşta sira
    (gorunum.brans_adlari listesindeki yeri, 1'den; renk paletindeki yeri)."""
    gorunum = params.get(GORUNUM) or {}
    sistem = gorunum.get("sistem_adlari") or {}
    satirlar = [("sistem", kod, sistem.get(kod) or kod, None) for kod in SISTEMLER]
    satirlar += [("brans", oge[0], oge[1], sira + 1) for sira, oge in
                 enumerate(gorunum.get("brans_adlari") or []) if len(oge) == 2]
    for tur, alan in (("alt_baslik", "alt_baslik_adlari"), ("mevcut_alan", "mevcut_alan_adlari")):
        satirlar += [(tur, kod, ad, None) for kod, ad in (gorunum.get(alan) or {}).items()]
    return [tek("ortak.adlar", dict(zip(("tur", "kod", "ad", "sira"), satir)))[0]
            for satir in satirlar]
