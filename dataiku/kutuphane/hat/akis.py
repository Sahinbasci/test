"""Gecelik akış: kaynakları oku → ham arşiv → kalite kapısı → model ve gözlem → sonuçlar.

Kaynak okuma ve kapı hat/okuma.py'dedir. Zorunlu bir kaynak bekleniyorsa (bağlantı yok) hesap
yapılmaz: KAYNAK_BEKLENIYOR. Kapı
geçmezse model ve sonuçlar güncellenmez, son geçerli veri korunur: KALDI (alarm). Aynı gün
ikinci çalışma aynı sonucu verir: arşiv yeni kimlikle ayrı yazılır, gözlem ve olay tabloları
çift satır almaz. Herhangi bir kaynakta KALDI varsa bütün gece durur (katı kapı). Okuma,
arşiv ya da biçim hatası o kaynağı KALDI yapar; hata türü ve iletisi çalışma kaydına ve
kalite sonucuna yazılır. Kapıdan sonraki hesapta hata olursa gece KALDI olarak kayda geçer
(HESAP_HATASI) ve hata senaryoya iletilir. Zaman verilmezse İstanbul saati kullanılır.
"""
import pandas as pd

from avukat_perf import kalite, olay, sema
from avukat_perf.ortak import birlestir, tek_gun
from avukat_perf.params import dogrula_veya_dur
from avukat_perf.surum import hazirlik_surumu, hesap_surumu
from hat import ayar, butunluk, calisma, gecmis, hesap, hesap_sure, model, okuma


def _olaylar(ortam, sonuc, cekim, kimlik, onceki_kayit, kaynaklar):
    """K1 ve K2 bayrak olaylarını yalnız ekleyerek birleştirir; çelişenleri ayırır.

    Başarısız gecelerden kalan olay satırları birleştirmeye girmez (yeniden yazılırlar). Çelişki
    yalnız bu gecenin esas kaynağındaki olaylarla aranır (kaynaklar: {kriter: esas kaynağı}).
    """
    ham = ortam.tablo_oku("bayrak_olay")
    butunluk.veri_kaybi(onceki_kayit, {"bayrak_olay": ham})
    mevcut = butunluk.basarili_satirlar(ham, onceki_kayit)
    mevcut = None if mevcut is None else olay.kaynakli(mevcut)
    celiski = []
    for kriter, ad in (("K1", "sonuc_k1"), ("K2", "sonuc_k2")):
        if ad not in sonuc:
            continue
        yeni = olay.olaylar(sonuc[ad], kriter).assign(calisma_kimligi=kimlik)
        onceki = None if mevcut is None else mevcut[
            (mevcut["kriter"] == kriter) & (mevcut["esas_kaynagi"] == kaynaklar[kriter])]
        celiski.append(olay.celisen_olaylar(onceki, yeni, cekim))
        mevcut = olay.olay_birlestir(mevcut, yeni)
    if mevcut is not None and celiski:
        sonuc["bayrak_olay"] = mevcut
        sonuc["olay_celiski"] = birlestir(celiski, list(celiski[0].columns)).assign(
            calisma_kimligi=kimlik, tespit_tarihi=cekim)


def _hesapla_yaz(ortam, tablolar, params, cekim, onceki, kimlik, simdi):
    """Model, puanlar ve olaylar; yazılan tablolar ve satır sayıları ("ad=sayı,...")."""
    mdl = model.kur(ortam, tablolar, params, cekim, onceki, simdi)
    sonuc, durumlar = hesap.hesapla(mdl, cekim, params)
    _olaylar(ortam, sonuc, cekim, kimlik, onceki, hesap_sure.esas_kaynaklari(mdl))
    yazilan = model.yaz(ortam, mdl, sonuc, kimlik)
    return durumlar, ",".join("{}={}".format(ad, yazilan[ad]) for ad in sorted(yazilan))


def gecelik(ortam, ayarlar, params, simdi=None):
    """Bir gecelik çalışma; özet sözlüğü döndürür (calisma_kimligi, karar, eksik, durumlar)."""
    dogrula_veya_dur(params)
    ayar.dogrula_veya_dur(ayarlar)
    simdi = calisma.simdi() if simdi is None else pd.Timestamp(simdi)
    cekim = tek_gun(simdi)  # çekim günü ve gözlem tabanı aynı andan (simdi) türetilir
    kimlik = calisma.kimlik(simdi)
    onceki = ortam.tablo_oku("calisma_kaydi")
    butunluk.kayitsiz_gecmis(ortam, onceki)
    for tur in ("GECELIK", "DONEM_SONU"):  # kesik çalışma kaydı geçmişi siler: çalışma durur
        butunluk.veri_kaybi(onceki, {"calisma_kaydi": onceki}, tur)
    tablolar, kayitlar, sonuclar = okuma.kaynaklari_oku(ortam, ayarlar, params, cekim, onceki,
                                                        kimlik, simdi)
    eksik = [ad for ad in sema.zorunlu_kaynaklar() if ad not in tablolar]
    if not eksik and all(tablolar[ad] is not None for ad in sema.zorunlu_kaynaklar()):
        sonuclar += [s.assign(calisma_kimligi=kimlik)
                     for s in okuma.iliskiler(tablolar, params, cekim)]
    karar = kalite.karar(*sonuclar)
    if eksik and karar != "KALDI":
        karar = "KAYNAK_BEKLENIYOR"
    durumlar, ozet = {}, calisma.satir(kimlik, "GECELIK", calisma.OZET, "", simdi, cekim)
    ozet["hesap_surumu"], ozet["hazirlik_surumu"] = hesap_surumu(params), hazirlik_surumu(params)
    if karar == "GECTI":
        try:
            durumlar, ozet["uretilen"] = _hesapla_yaz(ortam, tablolar, params, cekim, onceki,
                                                      kimlik, simdi)
            ozet["golge_zorunlu"] = bool(durumlar.pop("golge_zorunlu", False))
            ozet["golge"] = bool(params["uyari"]["golge_mod"])  # yedek yol ayrı: golge_zorunlu
        except Exception as hata:  # hesap ya da yazma hatası: kayda geçer, senaryo düşer
            ozet["aciklama"] = "HESAP_HATASI · " + okuma.ileti(hata)
            calisma.kaydet(ortam, onceki, kayitlar, "KALDI", ozet)
            calisma.kalite_ekle(ortam, sonuclar, cekim)
            raise
    calisma.kaydet(ortam, onceki, kayitlar, karar, ozet)
    calisma.kalite_ekle(ortam, sonuclar, cekim)
    return {"calisma_kimligi": kimlik, "karar": karar, "eksik_kaynaklar": eksik,
            "durumlar": durumlar, "hesap_surumu": ozet["hesap_surumu"]}
