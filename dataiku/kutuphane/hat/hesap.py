"""Hesap: hazırlanmış model tablolarından bütün sonuç tablolarını üretir (giriş-çıkış yok).

model sözlüğü: dosya, atama_donemi (zorunlu); hareket, bekleme, degerlendirme, avukat,
gozlem_*, k2_goruntu (yoksa None); golge_zorunlu, bekleme_eksik, golge_araliklari. Kaynağı
olmayan sonuç üretilmez; nedeni durumlar sözlüğündedir (KAYNAK_BEKLENIYOR ya da TEYIT_BEKLIYOR).
Dosya bazında tahsilat hareketi gelmediyse Tahsilat sütunu ve tahsilat tabloları üretilmez,
diğer sütunlar ve portföy hesaplanır. Kriter 1, Kriter 2 ve süre puanı hat/hesap_sure.py'dedir.
"""
import pandas as pd

from avukat_perf import (aciklama, agirlik, birlesik, donem, gozlem, kalite_davranis, portfoy,
                         tahsilat, tahsilat_evren)
from hat import hesap_sure


def _kalite_davranis(model, kesit, params, sonuc, durum):
    if model.get("degerlendirme") is None:
        durum["kalite_davranis"] = "KAYNAK_BEKLENIYOR"
        return None
    sonuc["sonuc_mevcut_degerlendirme"] = kalite_davranis.mevcut_alanlar(
        model["degerlendirme"], kesit, params)
    if not kalite_davranis.teyitli(params):
        durum["kalite_davranis"] = "TEYIT_BEKLIYOR"
        return None
    sutun, alt = kalite_davranis.puanla(model["degerlendirme"], kesit, params)
    sonuc["sonuc_kalite_davranis_sutun"], sonuc["sonuc_kalite_davranis_alt"] = sutun, alt
    return sutun


def _tahsilat(model, kesit, params, sonuc, durum):
    """Tahsilat sütunu ve tahsilat tabloları; dosya bazında hareket gelmediyse üretilmez
    (Tahsilat sütunu KAYNAK_BEKLENIYOR, toplamlardan yedek puan yok)."""
    dosya, atamalar, hareket = model["dosya"], model["atama_donemi"], model.get("hareket")
    if hareket is None:
        durum["tahsilat"] = "KAYNAK_BEKLENIYOR"
        return None
    # Kapanan dosyadan tahsilat beklenmez: sıklık ve güncellikte süresi kapandığı gün biter.
    # Koşul (rücu kodu ve açık bakiye) kaybı her gece gözlenir; geçmiş kesit aynı sonucu verir.
    kapanis = gozlem.kapanislar(model.get("gozlem_kosul"), kesit)
    avukat_t, grup_t, brans_t = tahsilat.hesapla(dosya, atamalar, hareket, kesit, params, kapanis)
    etiketler = {"tutar_bandi": ("bant_etiketi", portfoy.bant_etiketleri(params)),
                 "yas_bandi": ("yas_etiketi", tahsilat_evren.yas_etiketleri(params["tahsilat"]))}
    for sutun, (ad, etiket) in etiketler.items():  # etiket hesap anındaki sınırlardan
        if sutun in grup_t.columns:
            grup_t = grup_t.assign(**{ad: grup_t[sutun].map(etiket)})
    sonuc["sonuc_tahsilat_avukat"], sonuc["sonuc_tahsilat_grup"] = avukat_t, grup_t
    sonuc["sonuc_tahsilat_brans"] = brans_t
    for ad, islev in (("sonuc_tahsilat_aylik", portfoy.aylik_tahsilat),
                      ("sonuc_tahsilat_yillik", portfoy.yillik_tahsilat)):
        sonuc[ad] = islev(dosya, atamalar, hareket, kesit, params)
    return avukat_t


def hesapla(model, kesit, params):
    """(sonuç tabloları sözlüğü, durumlar sözlüğü)."""
    sonuc, durum = {}, {}
    avukat_t = _tahsilat(model, kesit, params, sonuc, durum)
    sonuc["sonuc_portfoy"] = portfoy.ozet(model["dosya"], model["atama_donemi"], kesit, params)
    sure = hesap_sure.kriterler(model, kesit, params, sonuc, durum)
    durum["golge_zorunlu"] = bool(model.get("golge_zorunlu"))
    kalite_davranis_t = _kalite_davranis(model, kesit, params, sonuc, durum)
    kaynaklar = [avukat_t, sonuc["sonuc_portfoy"], sure, kalite_davranis_t, model.get("avukat")]
    avukatlar = sorted({kod for tablo in kaynaklar if tablo is not None
                        for kod in tablo["avukat_kodu"].dropna()})
    sutunlar = {"tahsilat": avukat_t, "sure": sure}
    for ad in ("kalite", "davranis"):
        sutunlar[ad] = None if kalite_davranis_t is None else \
            kalite_davranis_t[kalite_davranis_t["sutun"] == ad]
    neden = {"tahsilat": durum.get("tahsilat"), "sure": durum.get("sure"),
             "kalite": durum.get("kalite_davranis"), "davranis": durum.get("kalite_davranis")}
    tablo = donem.puan_tablosu(str(pd.Timestamp(kesit).date()), sutunlar, avukatlar,
                               {sutun: deger for sutun, deger in neden.items() if deger})
    agirliklar = agirlik.sutun_agirliklari(params)  # hesap anındaki ağırlık sonuca yazılır
    sonuc["sonuc_puan_guncel"] = tablo.assign(agirlik=tablo["sutun"].map(agirliklar))
    sonuc["sonuc_birlesik"] = birlesik.birlestir(tablo, params)
    sonuc["sonuc_aciklama"] = aciklama.uret(params, avukat_t, kalite_davranis_t, sure,
                                            sonuc["sonuc_birlesik"],
                                            sonuc.get("sonuc_kalite_davranis_alt"))
    return sonuc, durum
