"""Dönem sonu akışı: dönem kesitinde sütun puanları → sonuç kontrolleri → sürümlü yayın.

Gecelik akışın yazdığı model ve gözlem tablolarını okur, puanları dönemin son gününde
hesaplar. Kontroller geçmezse yayın yapılmaz (KALDI). Dönem sonunu kapsayan (kesitten
sonraki bir günde) başarılı gecelik çekim yoksa da yayın yapılmaz: bayat modelle hesaplanan
dönem, son günlerde girilmiş esas kaydını görmez. Yayımlanan dönem değiştirilmez; içerik
ya da kurallar değiştiyse yeni sürüm eklenir. Birleşik puan yalnız yeni sürümde, o sürümün
parametreleriyle hesaplanır ve birlesik_donem tablosuna sürümüyle eklenir; geçmiş dönemler
yeniden hesaplanmaz. Önce puan_donem (yayının kendisi), sonra birlesik_donem yazılır: ekran
yayımlanmamış bir sürümü göstermez. Arada kesilen çalışma tekrarlanınca eksik birleşik sürüm,
yayımlanmış sürümün kendi bilgileriyle tamamlanır.
"""
import pandas as pd

from avukat_perf import birlesik, donem, kalite
from avukat_perf.params import dogrula_veya_dur
from avukat_perf.surum import hesap_surumu
from hat import butunluk, calisma, donem_kayit, gecmis, hesap, model, okuma


def yayimlanacak_donemler(degisken, simdi, puan_donem):
    """Dönem sonu senaryosunun yayımlayacağı dönemler.

    degisken: "donem" proje değişkeni (düzeltme için elle yazılır) ya da boş. Bir önceki ay
    henüz yayımlanmadıysa her zaman listededir: değişkeni silmek unutulsa da yeni ay yayımlanır.
    """
    onceki = donem.onceki_donem(simdi)
    yayimlanan = set() if puan_donem is None or puan_donem.empty else set(puan_donem["donem"])
    donemler = [degisken] if degisken else []
    if onceki not in donemler and (not degisken or onceki not in yayimlanan):
        donemler.append(onceki)
    return donemler


def calistir(ortam, params, donem_adi, simdi=None):
    """Bir dönemi yayımlar; özet sözlüğü döndürür (karar, yayin). Model tablosu okunamazsa ya
    da hesap veya yayın hata verirse de çalışma kayda geçer (hat/donem_kayit.py)."""
    dogrula_veya_dur(params)
    simdi = calisma.simdi() if simdi is None else pd.Timestamp(simdi)
    kesit = donem.kesit(donem_adi)
    kimlik = calisma.kimlik(simdi)
    onceki = ortam.tablo_oku("calisma_kaydi")
    butunluk.kayitsiz_gecmis(ortam, onceki)
    for tur in ("GECELIK", "DONEM_SONU"):  # kesik kayıt: çalışma kayda yazmadan durur
        butunluk.veri_kaybi(onceki, {"calisma_kaydi": onceki}, tur)
    ozet = calisma.satir(kimlik, "DONEM_SONU", calisma.OZET, "", simdi, kesit)
    ozet.update(aciklama="dönem " + donem_adi, hesap_surumu=hesap_surumu(params))
    try:
        karar, yayin, kontrol = _calistir(ortam, params, donem_adi, simdi, onceki, ozet)
    except Exception as hata:  # hesap ya da yayın hatası: kayda geçer, senaryo düşer
        donem_kayit.hata(ortam, onceki, ozet, okuma.ileti(hata))
        raise
    if kontrol is not None:  # yayından sonraki kayıt hata yolunun dışında: KALDI'ya çevrilmez
        calisma.kaydet(ortam, onceki, [], karar, ozet)
        calisma.kalite_ekle(ortam, [kontrol], kesit)
    return {"calisma_kimligi": kimlik, "karar": karar, "yayin": yayin}


def _calistir(ortam, params, donem_adi, simdi, onceki, ozet):
    kesit, kimlik = donem.kesit(donem_adi), ozet["calisma_kimligi"]
    eski = {"puan_donem": ortam.tablo_oku("puan_donem"),
            "birlesik_donem": ortam.tablo_oku("birlesik_donem")}
    butunluk.veri_kaybi(onceki, eski, "DONEM_SONU")  # kesik yayın tablosu: çalışma durur
    mdl = model.oku(ortam, onceki)
    karar = donem_kayit.model_eksik(ortam, onceki, mdl, ozet)
    if karar:
        return karar, None, None
    # Dönem kendi kesitindeki gölge/canlı durumuyla hesaplanır ve sürümlenir, bugünkü parametreyle
    # değil: sonradan açılan ya da kapanan gölge mod yayımlanmış dönemi değiştirmez. Yedek yolun
    # gölgesi (golge_k1) yalnız Kriter 1'i kapsar.
    params = dict(params, uyari=dict(params["uyari"],
                                     golge_mod=gecmis.golgede_mi(onceki, kesit, "K2"),
                                     golge_k1=gecmis.golgede_mi(onceki, kesit, "K1")))
    sonuc, durumlar = hesap.hesapla(mdl, kesit, params)
    tablo = sonuc["sonuc_puan_guncel"].assign(donem=donem_adi)
    kapsam = donem.veri_kapsami(gecmis.son_basarili(onceki, "dosya", "2200-01-01")[0],
                                donem_adi)
    kontrol = pd.concat([donem.sonuc_kontrolleri(tablo), kapsam,
                         donem_kayit.hazirlik_kontrolu(onceki, params)],
                        ignore_index=True).assign(calisma_kimligi=kimlik)
    karar, yayin, uretilen = kalite.karar(kontrol), None, None
    if karar == "GECTI":
        bilgi = {"calisma_kimligi": kimlik, "hesap_surumu": hesap_surumu(params),
                 "yayin_zamani": simdi}
        puan_donem, yayin = donem.yayinla(eski["puan_donem"], tablo, donem_adi, bilgi)
        if yayin != "DEGISMEDI":
            ortam.tablo_yaz("puan_donem", puan_donem)
        uretilen = "puan_donem={},birlesik_donem={}".format(
            len(puan_donem), _birlesik_tamamla(ortam, puan_donem, donem_adi, params))
    metin = donem_kayit.METIN
    ozet["aciklama"] += " · yayın {}".format(metin.get(yayin, yayin)) + "".join(
        " · {}: {}".format(metin.get(ad, ad), metin.get(deger, deger))
        for ad, deger in sorted(durumlar.items()) if ad != "golge_zorunlu")
    ozet.update(hesap_surumu=hesap_surumu(params), uretilen=uretilen)
    return karar, yayin, kontrol


def _birlesik_tamamla(ortam, puan_donem, donem_adi, params):
    """Dönemin yayımlanmış son sürümünün birleşik puanı yoksa ya da eksik yazılmışsa yazar;
    birleşik dönem tablosunun satır sayısını döndürür.

    Sürümün satırları yayımlanan avukatların tamamını, aynı kimlik ve kural sürümüyle
    içeriyorsa dokunmaz. Birleşik puan yayımlanan satırlardan, o sürümün kimliği, kural
    sürümü ve yayın zamanıyla kurulur (DEGISMEDI'de kurallar o sürümün kurallarıdır).
    """
    son = donem.son_surum(puan_donem[puan_donem["donem"] == donem_adi])
    surum = int(son["yayin_surumu"].iloc[0])
    mevcut = ortam.tablo_oku("birlesik_donem")
    bilgi = son[["calisma_kimligi", "hesap_surumu", "yayin_zamani"]].iloc[0].to_dict()
    secili = None if mevcut is None or mevcut.empty else mevcut[
        (mevcut["donem"] == donem_adi) & (mevcut["yayin_surumu"] == surum)]
    if secili is not None and set(secili["avukat_kodu"]) == set(son["avukat_kodu"]) and set(
            zip(secili["calisma_kimligi"].astype(str), secili["hesap_surumu"].astype(str))) == {
            (str(bilgi["calisma_kimligi"]), str(bilgi["hesap_surumu"]))}:
        return len(mevcut)
    yeni = birlesik.birlestir(son, params).assign(donem=donem_adi, yayin_surumu=surum, **bilgi)
    tablo = donem.surum_ekle(mevcut, yeni, donem_adi, surum)
    ortam.tablo_yaz("birlesik_donem", tablo)
    return len(tablo)
