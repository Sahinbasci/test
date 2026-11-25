"""Süre hesabı: Kriter 1, Kriter 2, süre özeti, e-posta listesi ve süre puanı (giriş-çıkış yok).

Gölge kriter bazındadır (sure_ozet.golge_kriterleri): golge_mod parametresi iki kriteri, esasın
yedek yoldan (çekirdek sistemin takip bilgileri) gelmesi yalnız Kriter 1'i gölgeye alır
(golge_k1); Kriter 2'nin verisi yedek yola bağlı değildir. Gölgedeki kriterde e-posta
gönderilmez; bir kriter gölgedeyse süre puanı yayımlanmaz. Canlı hesapta gölge gecelerinin
kapsadığı günlerdeki düşüm puana girmez; aralıklar da kriter bazındadır
(model["golge_araliklari"] = {"K1": [...], "K2": [...]}). Süre puanı Kriter 1 ve Kriter 2'nin
ikisi de varken üretilir. Haklı bekleme kaynağı daha önce okunmuşken o gece gelmediyse Kriter 1
hesaplanmaz.
"""
import pandas as pd

from avukat_perf import hazirlik, kriter1, kriter2, olay, sure_ozet, sure_puani
from hat import gecmis

KRITERLER = ("K1", "K2")


def golge_araliklari(kayit):
    """{kriter: çalışma kaydındaki gölge gecelerinin kapsadığı gün aralıkları}."""
    return {kriter: gecmis.golge_araliklari(kayit, kriter) for kriter in KRITERLER}


def esas_kaynaklari(model):
    """{kriter: esasın kaynağı}: Kriter 1 yedek yoldan ya da dava takipten, Kriter 2 dava
    takipten. Bayrak olayına yazılır (olay.ANAHTAR)."""
    return {"K1": olay.YEDEK if model.get("golge_zorunlu") else olay.DAVA_TAKIP,
            "K2": olay.DAVA_TAKIP}


def etkin_parametreler(params, model):
    """Esas yalnız yedek yoldan geliyorsa Kriter 1 gölge modda çalışır (parametreden bağımsız)."""
    if not model.get("golge_zorunlu") or params["uyari"].get("golge_k1"):
        return params
    return dict(params, uyari=dict(params["uyari"], golge_k1=True))


def sure_girdisi(k1, k2):
    """Kriter 1 ve Kriter 2 sonuçlarını süre puanı girdisinde birleştirir."""
    parcalar = []
    if k1 is not None:
        parcalar.append(k1.assign(kriter="K1", surec="ILK_ISLEM"))
    if k2 is not None:
        parcalar.append(k2.assign(kriter="K2", surec=k2["surec_turu"]))
    return pd.concat(parcalar, ignore_index=True)


def _degerlendir(model, kesit, params):
    k1 = k2 = None
    dosya, atamalar = model["dosya"], model["atama_donemi"]
    esas = model.get("gozlem_esas_yedek" if model.get("golge_zorunlu") else "gozlem_esas")
    if esas is not None and not model.get("bekleme_eksik"):
        k1 = kriter1.degerlendir(hazirlik.k1_atamalari(atamalar, dosya),
                                 hazirlik.k1_esaslari(esas), model.get("bekleme"), kesit, params)
    if model.get("k2_goruntu") is not None:
        surec = hazirlik.k2_surecleri(model["k2_goruntu"], dosya, model.get("gozlem_dava"),
                                      model.get("gozlem_kosul"), model.get("gozlem_esas"))
        k2 = kriter2.degerlendir(atamalar, surec, kesit, params)
    return k1, k2


def kriterler(model, kesit, params, sonuc, durum):
    """Süre sonuçlarını sonuc'a yazar; süre puanı tablosunu (ya da None) döndürür."""
    params = etkin_parametreler(params, model)
    k1, k2 = _degerlendir(model, kesit, params)
    pencere, golge = params["sure_puani"]["pencere_ay"], sure_ozet.golge_kriterleri(params)
    araliklar = model.get("golge_araliklari") or {}
    haric = {kriter: [] if golge[kriter] else araliklar.get(kriter) or []
             for kriter in KRITERLER}
    kaynak = esas_kaynaklari(model)
    for kriter, ad, tablo in (("K1", "sonuc_k1", k1), ("K2", "sonuc_k2", k2)):  # Süre Takibi
        if tablo is not None:
            sonuc[ad] = tablo.assign(
                pencerede_dusum=sure_ozet.pencerede_dusum(tablo, kesit, pencere, haric[kriter]),
                dusum_durumu=sure_ozet.dusum_durumu(tablo, golge[kriter], haric[kriter]),
                esas_kaynagi=kaynak[kriter])
    if k1 is None and k2 is None:
        durum["sure"] = "KAYNAK_BEKLENIYOR"
        return None
    girdi = sure_girdisi(k1, k2)
    sonuc["sonuc_sure_ozet"] = sure_ozet.ozet(girdi, kesit, pencere, haric)
    sonuc["sonuc_eposta"] = sure_ozet.eposta_listesi(girdi, params)
    if k1 is None or k2 is None:  # süre puanı iki kriterin düşümlerinden birlikte oluşur
        durum["sure"] = "KAYNAK_BEKLENIYOR"
        return None
    kapsam = sure_puani.kapsam_hesapla(k1, kesit, pencere)
    sonuc["sonuc_sure"] = sure_puani.puanla(girdi, kapsam, kesit, params, haric)
    return sonuc["sonuc_sure"]
