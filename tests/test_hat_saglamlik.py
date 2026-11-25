"""Veri hattının sağlamlığı: gece kayıt bırakmadan çökmez, bayat girdiyle yayın yapılmaz,
kaynak biçimi farklıysa kapı durdurur, dönem değişkeni unutulsa da yeni ay yayımlanır."""
import json
import os
import shutil

import pandas as pd

from arayuz import sunum
from arayuz.temel import guncel_tablolar
from hat import akis, butunluk, calisma, donem_akisi, gecmis, hesap, kaynak, model
from yardimci import dort_sutunlu, hata_bekle, prova_ortami

GECE = "2026-11-19 02:00:00"


def _ozet(ortam):
    kayit = ortam.tablo_oku("calisma_kaydi")
    return kayit[kayit["kaynak"] == calisma.OZET]


def test_dava_takip_kalkinca_bayrak_olayi_varken_gece_cokmez():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        assert akis.gecelik(ortam, ayarlar, params, simdi=GECE)["karar"] == "GECTI"
        olaylar = len(ortam.tablo_oku("bayrak_olay"))
        for ad in ("esas_goruntu", "k2_goruntu", "takip"):
            ayarlar["kaynaklar"][ad]["yontem"] = "bekliyor"
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-20 02:00:00")
        assert sonuc["karar"] == "GECTI" and len(ortam.tablo_oku("bayrak_olay")) == olaylar
        assert "bayrak_olay" not in gecmis.son_uretilen(ortam.tablo_oku("calisma_kaydi"))
    finally:
        shutil.rmtree(kok)


def test_hesap_hatasi_kayda_kaldi_olarak_gecer():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    asil = hesap.hesapla

    def bozuk(*argumanlar):
        raise KeyError("beklenmeyen alan")
    try:
        hesap.hesapla = bozuk
        assert hata_bekle(KeyError, akis.gecelik, ortam, ayarlar, params, GECE)
        ozet = _ozet(ortam).iloc[-1]
        assert ozet["durum"] == "KALDI" and ozet["aciklama"].startswith("HESAP_HATASI · KeyError")
        assert ortam.tablo_oku("sonuc_tahsilat_avukat") is None
    finally:
        hesap.hesapla = asil
        shutil.rmtree(kok)


def test_dosya_no_bicimi_farkliysa_kapi_durdurur_kayit_birakir():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        yol = os.path.join(kok, "sentetik", "veri", "kaynak_cekirdek_atama_log.csv")
        tablo = pd.read_csv(yol, dtype=str)
        tablo["DOSYA_NO"] = tablo["DOSYA_NO"].str.replace("D-", "D", regex=False)
        tablo.to_csv(yol, index=False)
        assert akis.gecelik(ortam, ayarlar, params, simdi=GECE)["karar"] == "KALDI"
        kalite = ortam.tablo_oku("kalite_sonucu").set_index("kontrol")
        assert kalite.loc["ATAMA_DOSYA", "durum"] == "KALDI"
    finally:
        shutil.rmtree(kok)


def test_genis_degerlendirmede_satir_sapmasi_her_gece_kaldi_vermez():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        yol = os.path.join(kok, "sentetik", "veri", "kaynak_degerlendirme_puan.csv")
        uzun = pd.read_csv(yol, dtype=str)
        genis = uzun.pivot_table(index=["avukat_kodu", "degerlendirme_tarihi", "degerlendiren"],
                                 columns="alt_baslik", values="puan", aggfunc="first")
        genis.reset_index().to_csv(yol, index=False)
        ayar = ayarlar["kaynaklar"]["degerlendirme"]
        ayar["genis_degerlendirme"] = {kod: kod for kod in genis.columns}
        ayar["alan_eslemesi"] = {}
        params["kalite"]["sapma_en_az_satir"] = 0  # küçük prova tablosunda da denetlensin
        for gece in (GECE, "2026-11-20 02:00:00"):
            assert akis.gecelik(ortam, ayarlar, params, simdi=gece)["karar"] == "GECTI"
    finally:
        shutil.rmtree(kok)


def test_donem_sonu_son_gecede_uretilmeyen_girdiyi_kullanmaz():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi=GECE)
        assert ortam.tablo_oku("model_k2_goruntu") is not None
        ayarlar["kaynaklar"]["k2_goruntu"]["yontem"] = "bekliyor"
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-20 02:00:00")
        mdl = model.oku(ortam, ortam.tablo_oku("calisma_kaydi"))
        assert mdl["k2_goruntu"] is None and mdl["gozlem_dava"] is None
        assert mdl["dosya"] is not None and mdl["gozlem_esas"] is not None
    finally:
        shutil.rmtree(kok)


def test_dava_takip_kalkinca_donem_sonu_sureyi_bayat_girdiyle_hesaplamaz():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi=GECE)
        for ad in ("esas_goruntu", "k2_goruntu", "takip"):
            ayarlar["kaynaklar"][ad]["yontem"] = "bekliyor"
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-20 02:00:00")
        assert donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-20 06:00:00")[
            "karar"] == "GECTI"
        puan = ortam.tablo_oku("puan_donem")
        assert set(puan.loc[puan["sutun"] == "sure", "durum"]) == {"KAYNAK_BEKLENIYOR"}
    finally:
        shutil.rmtree(kok)


def test_bos_api_yaniti_bos_tablo_olur():
    tablo = kaynak.normalle("bekleme", pd.DataFrame(), {})
    assert list(tablo.columns) == ["dosya_no", "avukat_kodu", "baslangic", "bitis"]
    assert tablo.empty


def test_yayimlanacak_donemler_degisken_unutulsa_da_yeni_ayi_yayimlar():
    yayin = pd.DataFrame({"donem": ["2026-09", "2026-10"]})
    sec = donem_akisi.yayimlanacak_donemler
    assert sec(None, "2026-12-01 06:00", yayin) == ["2026-11"]
    assert sec("2026-09", "2026-12-01 06:00", yayin) == ["2026-09", "2026-11"]
    assert sec("2026-09", "2026-11-15 10:00", yayin) == ["2026-09"]
    assert sec(None, "2026-11-15 10:00", yayin) == ["2026-10"]
    assert sec(None, "2026-11-01 06:00", None) == ["2026-10"]


def test_donem_sonu_parametreyi_dogrular():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        bozuk = json.loads(json.dumps(params))
        bozuk["agirliklar"]["tahsilat/sure"] = 10
        assert hata_bekle(ValueError, donem_akisi.calistir, ortam, bozuk, "2026-10")
    finally:
        shutil.rmtree(kok)


def test_yazimi_yarida_kalan_gece_sonuclari_karistirmaz():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi=GECE)
        ilk = gecmis.son_kimlik(ortam.tablo_oku("calisma_kaydi"))
        gozlem_once = ortam.tablo_oku("gozlem_esas")
        asil = ortam.tablo_yaz

        def bozuk(ad, tablo):
            if ad == "sonuc_birlesik":
                raise IOError("yazma hatası")
            return asil(ad, tablo)
        ortam.tablo_yaz = bozuk
        assert hata_bekle(IOError, akis.gecelik, ortam, ayarlar, params, "2026-11-20 02:00:00")
        ortam.tablo_yaz = asil
        kayit = ortam.tablo_oku("calisma_kaydi")
        assert gecmis.son_kimlik(kayit) == ilk  # başarısız gece son başarılı sayılmaz
        tablolar = guncel_tablolar({ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR})
        gosterilen = [ad for ad, t in tablolar.items() if ad.startswith("sonuc_") and t is not None]
        assert gosterilen and all(set(tablolar[ad]["calisma_kimligi"]) == {ilk}
                                  for ad in gosterilen)
        assert tablolar["sonuc_aciklama"] is None  # bozuk gecenin yazdığı tablo gösterilmez
        mdl = model.oku(ortam, kayit)
        # Bozuk gece bütün model_ tablolarını (Kriter 2 süreç görüntüsü dahil) kendi
        # kimliğiyle yazdı; hiçbiri son başarılı gecenin tablosu sayılmaz.
        k2_diskte = ortam.tablo_oku("model_k2_goruntu")
        assert len(k2_diskte) and ilk not in set(k2_diskte["calisma_kimligi"])
        assert all(mdl[ad] is None for ad in model.TABLOLAR)
        # Gözlemler hesap ve sonuç yazımı bittikten sonra yazılır: değişmedi.
        assert ortam.tablo_oku("gozlem_esas").equals(gozlem_once)
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-21 02:00:00")
        tablolar = guncel_tablolar({ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR})
        assert tablolar["sonuc_aciklama"] is not None and tablolar["sonuc_birlesik"] is not None
        # Kimliği doğru ama yarım yazılmış (satırı eksik) model tablosu da kullanılmaz.
        kayit = ortam.tablo_oku("calisma_kaydi")
        assert all(model.oku(ortam, kayit)[ad] is not None for ad in model.TABLOLAR)
        dosya = ortam.tablo_oku("model_dosya")
        ortam.tablo_yaz("model_dosya", dosya.head(len(dosya) - 1))
        mdl = model.oku(ortam, kayit)
        assert mdl["dosya"] is None and mdl["atama_donemi"] is not None
    finally:
        shutil.rmtree(kok)


def test_k2_kaynagi_eksikken_sure_puani_ve_birlesik_yayimlanmaz():
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    params = dort_sutunlu(params)  # süre puana girdiğinde
    try:
        ayarlar["kaynaklar"]["k2_goruntu"]["yontem"] = "bekliyor"
        akis.gecelik(ortam, ayarlar, params, simdi=GECE)
        uretilen = gecmis.son_uretilen(ortam.tablo_oku("calisma_kaydi"))
        assert "sonuc_k1" in uretilen and "sonuc_sure" not in uretilen
        puan = ortam.tablo_oku("sonuc_puan_guncel")
        assert set(puan.loc[puan["sutun"] == "sure", "durum"]) == {"KAYNAK_BEKLENIYOR"}
        assert (ortam.tablo_oku("sonuc_birlesik")["durum"] != "YAYIMLANDI").all()
    finally:
        shutil.rmtree(kok)


def test_yedek_yolda_golge_mod_zorunlu():
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        assert params["uyari"]["golge_mod"] is False
        for ad in ("esas_goruntu", "k2_goruntu"):
            ayarlar["kaynaklar"][ad]["yontem"] = "bekliyor"
        akis.gecelik(ortam, ayarlar, params, simdi=GECE)
        eposta = ortam.tablo_oku("sonuc_eposta")
        assert len(eposta) and not eposta["gonderilecek"].astype(bool).any()
        kayit = ortam.tablo_oku("calisma_kaydi")
        assert gecmis.son_golge_zorunlu(kayit) and model.oku(ortam, kayit)["golge_zorunlu"]
        tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
        assert sunum.sayfa("genel", tablolar, params)["bilesenler"]["ortak.durum"][0][
            "golge_mod"] is True
    finally:
        shutil.rmtree(kok)


def test_gruplama_ayari_her_sayfayi_calistirir():
    for gruplama in (["brans"], ["tutar_bandi"]):
        ortam, ayarlar, params, kok = prova_ortami(200, 6)
        try:
            params["tahsilat"]["gruplama"] = gruplama
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECE)["karar"] == "GECTI"
            tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
            for sayfa in ("genel", "avukat", "sure", "kurallar", "veri"):
                json.dumps(sunum.sayfa(sayfa, tablolar, params), allow_nan=False)
        finally:
            shutil.rmtree(kok)


def _yazim_bozuk(ortam, hedef):
    """hedef tablonun yazımında hata veren ortam; asıl yazma işlevini döndürür."""
    asil = ortam.tablo_yaz

    def yaz(ad, tablo):
        if ad == hedef:
            raise IOError("yazma hatası")
        return asil(ad, tablo)
    ortam.tablo_yaz = yaz
    return asil


def test_ilk_gece_yarida_kalirsa_hicbir_sonuc_gosterilmez():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        asil = _yazim_bozuk(ortam, "sonuc_tahsilat_brans")
        assert hata_bekle(IOError, akis.gecelik, ortam, ayarlar, params, GECE)
        ortam.tablo_yaz = asil
        tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
        assert tablolar["sonuc_birlesik"] is not None  # yarım yazılmış tablo diskte duruyor
        genel = sunum.sayfa("genel", tablolar, params)["bilesenler"]
        assert not genel.get("genel.avukat_tablosu") and genel["ortak.durum"][0]["kesit"] is None
        mdl = model.oku(ortam, ortam.tablo_oku("calisma_kaydi"))
        assert all(mdl[ad] is None for ad in model.TABLOLAR)
        assert donem_akisi.calistir(ortam, params, "2026-10", simdi=GECE)[
            "karar"] == "KAYNAK_BEKLENIYOR"
    finally:
        shutil.rmtree(kok)


def _olay_anahtarlari(ortam):
    olay = ortam.tablo_oku("bayrak_olay")
    return sorted(map(tuple, olay[["dosya_no", "kriter", "seviye", "olay_tarihi"]].astype(
        str).values))


def test_basarisiz_gecenin_bayrak_olayi_sizmaz_ve_kalici_olmaz():
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    temiz, _, _, kok2 = prova_ortami(300, 8)
    try:
        for hedef in (ortam, temiz):
            akis.gecelik(hedef, ayarlar, params, simdi="2026-11-01 02:00:00")
        once = len(ortam.tablo_oku("bayrak_olay"))
        asil = _yazim_bozuk(ortam, "sonuc_aciklama")  # olay tabloları en son yazılır
        assert hata_bekle(IOError, akis.gecelik, ortam, ayarlar, params, GECE)
        assert len(ortam.tablo_oku("bayrak_olay")) == once
        ortam.tablo_yaz = asil
        asil = _yazim_bozuk(ortam, "olay_celiski")  # olaylar yazıldıktan sonra kesilen gece
        assert hata_bekle(IOError, akis.gecelik, ortam, ayarlar, params, GECE)
        ortam.tablo_yaz = asil
        basarili = gecmis.son_kimlik(ortam.tablo_oku("calisma_kaydi"))
        olay = ortam.tablo_oku("bayrak_olay")
        assert (olay["calisma_kimligi"] != basarili).any()  # bozuk gece olay yazmıştı
        tablolar = guncel_tablolar({ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR})
        assert set(tablolar["bayrak_olay"]["calisma_kimligi"]) == {basarili}
        assert tablolar["sonuc_k1"] is None  # bozuk gecenin sonuçları da gizli
        # Sonraki başarılı gece bozuk gecenin olaylarını kendi kimliğiyle yeniden yazar: geçmiş,
        # hiç kesilmemiş akışla aynıdır.
        for hedef in (ortam, temiz):
            akis.gecelik(hedef, ayarlar, params, simdi="2026-11-20 02:00:00")
        basarili = butunluk.basarili_satirlar(ortam.tablo_oku("bayrak_olay"),
                                             ortam.tablo_oku("calisma_kaydi"))
        assert len(basarili) == len(ortam.tablo_oku("bayrak_olay"))
        assert _olay_anahtarlari(ortam) == _olay_anahtarlari(temiz)
    finally:
        shutil.rmtree(kok)
        shutil.rmtree(kok2)


def test_negatif_rucu_tutari_gece_veri_hatasiyla_durur():
    # Önceden kapı uyarıyla geçiyor, tahsilat hesabı ValueError verip gece HESAP_HATASI ile
    # düşüyordu (alarm kod hatası gibi görünürdü). Artık kapı veri hatası olarak durdurur.
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        yol = os.path.join(kok, "sentetik", "veri", "kaynak_cekirdek_dosya.csv")
        dosya = pd.read_csv(yol, dtype=str)
        dosya.loc[0, "rucu_tutari"] = "-1500"
        dosya.to_csv(yol, index=False)
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        assert sonuc["karar"] == "KALDI"
        kayit = ortam.tablo_oku("calisma_kaydi")
        ozet = kayit[kayit["kaynak"] == calisma.OZET].iloc[-1]
        assert "HESAP_HATASI" not in str(ozet["aciklama"])
        kalite_sonucu = ortam.tablo_oku("kalite_sonucu").set_index(["kaynak", "kontrol"])
        assert kalite_sonucu.loc[("dosya", "NEGATIF_RUCU"), "durum"] == "KALDI"
    finally:
        shutil.rmtree(kok)


def test_tahsilat_hareketi_gelmezse_diger_sutunlar_ve_portfoy_uretilir():
    """Dosya bazında tahsilat hareketi isteğe bağlıdır: gelmezse yalnız
    Tahsilat sütunu kaynak bekler, toplamlardan yedek puan yoktur; Kriter 1, Kriter 2,
    kalite/davranış ve portföy üretilir, birleşik puan yayımlanmaz, sayfalar açılır, dönem
    sonu yayımlar. Önceden gece KAYNAK_BEKLENIYOR olup hiçbir sonuç üretmiyordu."""
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        ayarlar["kaynaklar"]["tahsilat_hareketi"]["yontem"] = "bekliyor"
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi=GECE)
        assert sonuc["karar"] == "GECTI" and sonuc["eksik_kaynaklar"] == []
        assert sonuc["durumlar"]["tahsilat"] == "KAYNAK_BEKLENIYOR"
        uretilen = gecmis.son_uretilen(ortam.tablo_oku("calisma_kaydi"))
        for ad in ("sonuc_portfoy", "sonuc_k1", "sonuc_k2", "sonuc_mevcut_degerlendirme",
                   "sonuc_puan_guncel", "sonuc_birlesik"):
            assert ad in uretilen, ad
        assert not [ad for ad in uretilen if ad.startswith("sonuc_tahsilat")]
        assert "model_hareket" not in uretilen
        puan = ortam.tablo_oku("sonuc_puan_guncel")
        assert set(puan.loc[puan["sutun"] == "tahsilat", "durum"]) == {"KAYNAK_BEKLENIYOR"}
        assert set(ortam.tablo_oku("sonuc_birlesik")["durum"]) == {"EKSIK_SUTUN"}
        kalite = ortam.tablo_oku("kalite_sonucu").set_index("kontrol")
        assert kalite.loc["TAHSILAT_HAREKETI_YOK", "durum"] == "UYARI"
        tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
        for sayfa in ("genel", "avukat", "sure", "kurallar", "veri"):
            json.dumps(sunum.sayfa(sayfa, tablolar, params), allow_nan=False)
        assert donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")[
            "karar"] == "GECTI"
        donem = ortam.tablo_oku("puan_donem")
        assert set(donem.loc[donem["sutun"] == "tahsilat", "durum"]) == {"KAYNAK_BEKLENIYOR"}
    finally:
        shutil.rmtree(kok)


def test_her_istege_bagli_kaynak_tek_basina_beklenirken_gece_cokmez():
    """sema'da isteğe bağlı işaretli her kaynak tek başına 'bekliyor' olunca gece hata vermez;
    bayrağı değiştiren biri, bağımlı hesap kaynağı koşulsuz kullanıyorsa bu testi düşürür."""
    from avukat_perf import sema
    for ad, tanim in sema.KAYNAKLAR.items():
        if not tanim.get("istege_bagli"):
            continue
        ortam, ayarlar, params, kok = prova_ortami(120, 5)
        try:
            ayarlar["kaynaklar"][ad]["yontem"] = "bekliyor"
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECE)["karar"] == "GECTI", ad
        finally:
            shutil.rmtree(kok)
