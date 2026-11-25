"""Geçişler ve veri bütünlüğü: prod öncesi incelemenin P1 bulgularına karşı gerileme testleri.

Gölgeden canlıya ve yedek yoldan dava takip sistemine geçişte haksız düşüm oluşmaz; boş ya da
eşleşmeyen gözlem görüntüsü, boşalan haklı bekleme kaynağı ve kesik gözlem tablosu geceyi
durdurur; dönem sonu son geceden sonra değişen hazırlık kuralıyla yayın yapmaz; aynı gün
yeniden atamada dosya sonraki avukattadır; kısa süre tutulup iade edilen dosya tahsilat
beklentisine tam dosya olarak girmez.
"""
import os
import shutil

import pandas as pd

from arayuz import sunum
from avukat_perf import hazirlik, kalite, sema, tahsilat
from hat import akis, donem_akisi, gecmis, kaynak
from yardimci import atama_tablosu, hata_bekle, params_yukle, prova_ortami

GECELER = ("2026-11-17 02:00:00", "2026-11-18 02:00:00", "2026-11-19 02:00:00")
K1_SUTUNLARI = ["dosya_no", "avukat_kodu", "atama_tarihi", "seviye", "dusum", "sure_gun"]


def _k1(ortam):
    return ortam.tablo_oku("sonuc_k1")[K1_SUTUNLARI].sort_values(K1_SUTUNLARI[:3]).reset_index(
        drop=True)


def _kaynak_degistir(degistir):
    """kaynak.normalle'yi sarar: degistir(ad, ham) değiştirilmiş ham tabloyu döndürür.

    Değişiklik arşivden sonra, normalleştirmeden önce uygulanır (kapı bunu görür)."""
    asil = kaynak.normalle

    def normalle(ad, ham, ayar):
        return asil(ad, degistir(ad, ham), ayar)
    kaynak.normalle = normalle
    return asil


def _kur(dosya=600, avukat=12):
    return prova_ortami(dosya, avukat)


def test_golge_donemindeki_dusum_canliya_geciste_puana_girmez():
    sayilar = {}
    for golge_gecmisi in (True, False):
        ortam, ayarlar, params, kok = _kur()
        try:
            params["uyari"]["golge_mod"] = golge_gecmisi
            akis.gecelik(ortam, ayarlar, params, simdi=GECELER[1])
            params["uyari"]["golge_mod"] = False
            akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])
            kayit = ortam.tablo_oku("calisma_kaydi")
            beklenen = [(None, pd.Timestamp("2026-11-18"))] if golge_gecmisi else []
            assert gecmis.golge_araliklari(kayit) == beklenen
            k1 = ortam.tablo_oku("sonuc_k1")
            dusum = k1[k1["dusum"].astype(bool)]
            once = pd.to_datetime(dusum["dusum_tarihi"]) < pd.Timestamp("2026-11-19")
            durum = set(dusum.loc[once, "dusum_durumu"])
            assert durum == ({"GOLGE_DONEMI"} if golge_gecmisi else {"UYGULANDI"})
            sayilar[golge_gecmisi] = int(ortam.tablo_oku("sonuc_sure_ozet")["dusum_sayisi"].sum())
        finally:
            shutil.rmtree(kok)
    # Gölge geçmişi varken canlıya geçişten önceki düşümler sayılmaz.
    assert sayilar[False] > 0 and sayilar[True] < sayilar[False]


def _dusumler(ortam):
    tablolar = [ortam.tablo_oku(ad).assign(kriter_k2=ad == "sonuc_k2")
                for ad in ("sonuc_k1", "sonuc_k2")]
    dusum = pd.concat([t[t["dusum"].astype(bool)] for t in tablolar], ignore_index=True)
    return dusum.assign(dusum_tarihi=pd.to_datetime(dusum["dusum_tarihi"]))


def _uc_gece(geceler, golgeler):
    """Üç gecelik çalışma: (gölge aralıkları, düşümler, özet düşüm sayısı, süre puanı O)."""
    ortam, ayarlar, params, kok = _kur()
    try:
        for gun, golge in zip(geceler, golgeler):
            params["uyari"]["golge_mod"] = golge
            akis.gecelik(ortam, ayarlar, params, simdi=str(gun.date()) + " 02:00:00")
        return (gecmis.golge_araliklari(ortam.tablo_oku("calisma_kaydi")), _dusumler(ortam),
                int(ortam.tablo_oku("sonuc_sure_ozet")["dusum_sayisi"].sum()),
                int(ortam.tablo_oku("sonuc_sure")["o"].astype(int).sum()))
    finally:
        shutil.rmtree(kok)


def test_araya_giren_golge_gecesi_onceki_canli_dusumleri_silmez():
    """Canlı, gölge, canlı: yalnız gölge gecesinin kapsadığı günlerdeki (önceki gecenin günü
    hariç, kendi günü dahil) düşüm puan dışında kalır; önceki ve sonraki düşümler sayılır. Önceden
    gölge gecesi canlı başlangıcı ileri taşıyıp önceki bütün
    düşümleri siliyordu. Gölge gecesi, sentetik veride düşümü olan bir Kasım gününe konur."""
    kasim = pd.Timestamp("2026-11-19")
    on = _uc_gece([pd.Timestamp("2026-10-20"), pd.Timestamp("2026-10-25"), kasim], (False,) * 3)
    gunler = sorted(set(on[1]["dusum_tarihi"]))
    golge = [gun for gun in gunler if pd.Timestamp("2026-11-03") <= gun < kasim][0]
    geceler = [golge - pd.Timedelta(days=2), golge, kasim]
    canli = _uc_gece(geceler, (False, False, False))
    arada = _uc_gece(geceler, (False, True, False))
    assert canli[0] == [] and arada[0] == [(geceler[0], golge)]
    tarih = arada[1]["dusum_tarihi"]
    golgede = (tarih > geceler[0]) & (tarih <= golge)
    assert golgede.sum() >= 1 and (~golgede).sum() >= 10
    assert set(arada[1].loc[golgede, "dusum_durumu"]) == {"GOLGE_DONEMI"}
    assert set(arada[1].loc[~golgede, "dusum_durumu"]) == {"UYGULANDI"}
    assert set(canli[1]["dusum_durumu"]) == {"UYGULANDI"}
    assert canli[2] - arada[2] == golgede.sum()
    # Süre puanının gerçekleşen düşümü (O) de yalnız gölge günlerindeki düşüm kadar azalır.
    assert canli[3] > 0 and canli[3] - arada[3] == golgede.sum()


def test_yedek_yoldan_dava_takibe_geciste_haksiz_dusum_olusmaz():
    sonuclar, olay_sayilari = [], []
    for yedek_gecmisi in (True, False):
        ortam, ayarlar, params, kok = _kur()
        try:
            if yedek_gecmisi:
                kaynaklar = ayarlar["kaynaklar"]
                for ad in ("esas_goruntu", "k2_goruntu"):
                    kaynaklar[ad]["yontem"] = "bekliyor"
                for gece in GECELER[:2]:
                    assert akis.gecelik(ortam, ayarlar, params, simdi=gece)["karar"] == "GECTI"
                assert gecmis.son_golge_zorunlu(ortam.tablo_oku("calisma_kaydi"))
                for ad in ("esas_goruntu", "k2_goruntu"):
                    del kaynaklar[ad]["yontem"]  # yeniden sistem ayarı (dosya)
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])["karar"] == "GECTI"
            assert set(ortam.tablo_oku("gozlem_esas")["dayanak"]) == {"ARSIV_ONCESI"}
            sonuclar.append(_k1(ortam))
            # Yedek yolun olayları kayıtta kalır ama dava takip hesabıyla çelişki sayılmaz;
            # dava takip kaynağındaki K1 olayları kesintisiz akışla aynıdır.
            olaylar = ortam.tablo_oku("bayrak_olay")
            k1 = olaylar[(olaylar["kriter"] == "K1") & (olaylar["esas_kaynagi"] == "dava_takip")]
            olay_sayilari.append(len(k1))
            assert ortam.tablo_oku("olay_celiski").empty
            if yedek_gecmisi:
                assert set(olaylar.loc[olaylar["kriter"] == "K1", "esas_kaynagi"]) == {
                    "yedek", "dava_takip"}
                # Süre Takibi yalnız bugünkü kaynağın (dava takip) olaylarını gösterir.
                tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
                secim = {"kriter": "K1", "seviye": "KAPANDI"}
                gosterilen = sunum.sayfa("sure", tablolar, params, secim)["bilesenler"][
                    "sure.olaylar"]
                anahtar = ["dosya_no", "avukat_kodu", "atama_tarihi", "seviye", "olay_tarihi"]
                gecerli = {tuple(str(pd.Timestamp(d))[:10] if "tarih" in a else str(d)
                                 for a, d in zip(anahtar, satir))
                           for satir in k1[anahtar].itertuples(index=False, name=None)}
                assert gosterilen and all(tuple(str(o[a])[:10] if "tarih" in a else str(o[a])
                                                for a in anahtar) in gecerli for o in gosterilen)
        finally:
            shutil.rmtree(kok)
    pd.testing.assert_frame_equal(sonuclar[0], sonuclar[1], check_dtype=False)
    assert olay_sayilari[0] == olay_sayilari[1] > 0


def test_yedek_yolun_zorunlu_golgesi_yalniz_kriter_1i_kapsar():
    """Esas yalnız yedek yoldan gelirken Kriter 2 canlıdır: düşümü uygulanır, e-postası
    gönderilir, sonraki canlı gecede de puana girer; Kriter 1 gölgededir (yedek yoldan Kriter 1
    yalnız gölge modda). Önceden 80 K2 düşümü GOLGE, ertesi canlı gecede GOLGE_DONEMI kalıyordu."""
    ortam, ayarlar, params, kok = _kur()
    try:
        params["uyari"]["golge_mod"] = False
        ayarlar["kaynaklar"]["esas_goruntu"]["yontem"] = "bekliyor"
        assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[1])["karar"] == "GECTI"
        k1, k2 = ortam.tablo_oku("sonuc_k1"), ortam.tablo_oku("sonuc_k2")
        assert set(k1["dusum_durumu"].dropna()) == {"GOLGE"}
        assert set(k2["dusum_durumu"].dropna()) == {"UYGULANDI"} and k2["dusum"].sum() > 0
        eposta = ortam.tablo_oku("sonuc_eposta")
        assert set(eposta.loc[eposta["kriter"] == "K2", "gonderilecek"].astype(str)) == {"True"}
        assert set(eposta.loc[eposta["kriter"] == "K1", "gonderilecek"].astype(str)) == {"False"}
        assert set(ortam.tablo_oku("sonuc_sure")["durum"]) == {"GOLGE_MOD"}
        kayit = ortam.tablo_oku("calisma_kaydi")
        assert gecmis.golge_araliklari(kayit, "K2") == []
        assert gecmis.golge_araliklari(kayit, "K1") == [(None, pd.Timestamp("2026-11-18"))]
        del ayarlar["kaynaklar"]["esas_goruntu"]["yontem"]
        assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])["karar"] == "GECTI"
        dusum = _dusumler(ortam)
        once = dusum["dusum_tarihi"] <= pd.Timestamp("2026-11-18")
        assert (once & dusum["kriter_k2"]).sum() > 0 and (once & ~dusum["kriter_k2"]).sum() > 0
        assert set(dusum.loc[once & dusum["kriter_k2"], "dusum_durumu"]) == {"UYGULANDI"}
        assert set(dusum.loc[once & ~dusum["kriter_k2"], "dusum_durumu"]) == {"GOLGE_DONEMI"}
        # Süre özetinin düşüm sayısı her kriterde kendi aralığıyla sayılır.
        ozet = ortam.tablo_oku("sonuc_sure_ozet")
        for kriter, ad in (("K1", "sonuc_k1"), ("K2", "sonuc_k2")):
            beklenen = ortam.tablo_oku(ad)["pencerede_dusum"].astype(str).eq("True").sum()
            assert ozet.loc[ozet["kriter"] == kriter, "dusum_sayisi"].astype(int).sum() == \
                beklenen, kriter
            assert beklenen > 0 or kriter == "K1"
    finally:
        shutil.rmtree(kok)


def test_donem_kesitindeki_yedek_yol_golgesi_kriter_1i_golgede_tutar():
    """31 Ekim gecesi esas yedek yoldan geldiyse Ekim, bugün dava takip bağlı olsa da süre
    puanı yayımlanmadan (GOLGE_MOD) hesaplanır; 30 Eylül canlıysa Eylül canlıdır."""
    ortam, ayarlar, params, kok = _kur()
    try:
        params["uyari"]["golge_mod"] = False
        params["sure_puani"].update(yeterli_dosya=1, en_az_beklenen=0, en_az_kapsam=0.01)
        for gece, yedek in (("2026-09-30", False), ("2026-10-31", True), ("2026-11-19", False)):
            if yedek:
                ayarlar["kaynaklar"]["esas_goruntu"]["yontem"] = "bekliyor"
            elif "yontem" in ayarlar["kaynaklar"]["esas_goruntu"]:
                del ayarlar["kaynaklar"]["esas_goruntu"]["yontem"]
            assert akis.gecelik(ortam, ayarlar, params, simdi=gece + " 02:00:00")[
                "karar"] == "GECTI"
        durum = {}
        for ad in ("2026-09", "2026-10"):
            assert donem_akisi.calistir(ortam, params, ad, simdi="2026-11-19 06:00:00")[
                "karar"] == "GECTI"
            puan = ortam.tablo_oku("puan_donem")
            durum[ad] = set(puan[(puan["donem"] == ad) & (puan["sutun"] == "sure")]["durum"])
        assert "GOLGE_MOD" not in durum["2026-09"] and "GECERLI" in durum["2026-09"]
        assert "GOLGE_MOD" in durum["2026-10"] and "GECERLI" not in durum["2026-10"]
    finally:
        shutil.rmtree(kok)


def test_bos_gozlem_goruntusu_geceyi_durdurur_ve_tabani_bozmaz():
    sonuclar = []
    for bos_gece in (True, False):
        ortam, ayarlar, params, kok = _kur()
        try:
            if bos_gece:
                asil = _kaynak_degistir(lambda ad, ham: ham.iloc[0:0] if ad == "esas_goruntu"
                                        else ham)
                try:
                    assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[1])[
                        "karar"] == "KALDI"
                finally:
                    kaynak.normalle = asil
                sonuc = ortam.tablo_oku("kalite_sonucu")
                satir = sonuc[(sonuc["kaynak"] == "esas_goruntu") &
                              (sonuc["kontrol"] == "BOS_TABLO")]
                assert list(satir["durum"]) == ["KALDI"]
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])["karar"] == "GECTI"
            assert set(ortam.tablo_oku("gozlem_esas")["dayanak"]) == {"ARSIV_ONCESI"}
            sonuclar.append(_k1(ortam))
        finally:
            shutil.rmtree(kok)
    pd.testing.assert_frame_equal(sonuclar[0], sonuclar[1], check_dtype=False)


def test_bekleme_kaynagi_bosalirsa_gece_durur_kalkarsa_k1_hesaplanmaz():
    ortam, ayarlar, params, kok = _kur()
    try:
        assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[1])["karar"] == "GECTI"
        asil = _kaynak_degistir(lambda ad, ham: ham.iloc[0:0] if ad == "bekleme" else ham)
        try:
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])["karar"] == "KALDI"
        finally:
            kaynak.normalle = asil
        ayarlar["kaynaklar"]["bekleme"]["yontem"] = "bekliyor"
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 03:00:00")
        assert sonuc["karar"] == "GECTI" and sonuc["durumlar"]["sure"] == "KAYNAK_BEKLENIYOR"
        assert "sonuc_k1" not in gecmis.son_uretilen(ortam.tablo_oku("calisma_kaydi"))
    finally:
        shutil.rmtree(kok)


def test_esas_anahtari_eslesmezse_gece_durur():
    ortam, ayarlar, params, kok = _kur(300, 8)
    try:
        def bicim(ad, ham):
            if ad != "esas_goruntu":
                return ham
            sutun = ayarlar["kaynaklar"][ad].get("alan_eslemesi", {})
            ham_ad = next((k for k, v in sutun.items() if v == "dosya_no"), "dosya_no")
            return ham.assign(**{ham_ad: ham[ham_ad].astype(str).str.replace("-", "")})
        asil = _kaynak_degistir(bicim)
        try:
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])["karar"] == "KALDI"
        finally:
            kaynak.normalle = asil
        sonuc = ortam.tablo_oku("kalite_sonucu").set_index("kontrol")
        assert sonuc.loc["ESAS_DOSYA", "durum"] == "KALDI"
    finally:
        shutil.rmtree(kok)


def test_kesik_yalniz_eklenen_tablo_geceyi_durdurur_ve_uzerine_yazmaz():
    for ad in ("gozlem_esas", "bayrak_olay", "calisma_kaydi"):
        ortam, ayarlar, params, kok = _kur(300, 8)
        try:
            akis.gecelik(ortam, ayarlar, params, simdi=GECELER[1])
            tam = ortam.tablo_oku(ad)
            # Geçmişin kaybı (baştan satır silinmesi). Çalışma kaydında yalnız son gecenin
            # satırları kaybolursa o gece çalışmamış görünür; bu sayıyla yakalanmaz.
            ortam.tablo_yaz(ad, tam.iloc[1:])
            assert hata_bekle(ValueError, akis.gecelik, ortam, ayarlar, params, GECELER[2]), ad
            assert len(ortam.tablo_oku(ad)) == len(tam) - 1, ad  # kesik tablo ezilmedi
            if ad != "calisma_kaydi":  # kaydı kesikken gece kayıt yazmadan durur
                kayit = ortam.tablo_oku("calisma_kaydi")
                ozet = kayit[(kayit["kaynak"] == "*") & (kayit["tur"] == "GECELIK")].iloc[-1]
                assert ozet["durum"] == "KALDI" and "VERI_KAYBI" in ozet["aciklama"], ad
        finally:
            shutil.rmtree(kok)


def test_araya_tabloyu_yazmayan_gece_girse_de_kesik_tablo_yakalanir():
    """Kesik gözlem ya da olay tablosu, o tabloyu yazmayan bir gece araya girse de VERI_KAYBI
    verir: beklenen satır sayısı tablonun son yazıldığı başarılı gecedendir.
    Önceden denetim yalnız son geceye bakıyordu; kaybolan esaslar yeni görülmüş sayılıp
    düşüm sayısı 47'den 292'ye çıkıyordu."""
    bekleyenler = {"gozlem_esas": ("esas_goruntu",),
                   "bayrak_olay": ("esas_goruntu", "takip", "k2_goruntu")}
    for ad, kaynaklar in bekleyenler.items():
        ortam, ayarlar, params, kok = _kur(300, 8)
        try:
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[0])["karar"] == "GECTI"
            tam = ortam.tablo_oku(ad)
            for kaynak_adi in kaynaklar:
                ayarlar["kaynaklar"][kaynak_adi]["yontem"] = "bekliyor"
            assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[1])["karar"] == "GECTI"
            assert ad not in gecmis.son_uretilen(ortam.tablo_oku("calisma_kaydi")), ad
            for kaynak_adi in kaynaklar:
                del ayarlar["kaynaklar"][kaynak_adi]["yontem"]
            ortam.tablo_yaz(ad, tam.iloc[:20])
            assert hata_bekle(ValueError, akis.gecelik, ortam, ayarlar, params, GECELER[2]), ad
            assert len(ortam.tablo_oku(ad)) == 20, ad  # kesik tablo ezilmedi
        finally:
            shutil.rmtree(kok)


def test_calisma_kaydi_bosalirsa_eklenen_tablolar_doluyken_calisma_durur():
    """Çalışma kaydı boş okunur ama gözlem, olay ya da dönem yayını doluysa hat ilk geceymiş
    gibi sürmez (gölge düşümleri canlı sayılır, kesik yayın denetlenmezdi): VERI_KAYBI, kayda
    yazılmaz. İlk kurulumda (bütün tablolar boş) çalışma sürer."""
    ortam, ayarlar, params, kok = _kur(300, 8)
    try:
        params["uyari"]["golge_mod"] = False
        assert akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])["karar"] == "GECTI"
        assert donem_akisi.calistir(ortam, params, "2026-10", simdi=GECELER[2].replace(
            "02:", "06:"))["karar"] == "GECTI"
        kayit = ortam.tablo_oku("calisma_kaydi")
        for bos in (kayit.iloc[0:0], None):
            if bos is None:
                os.remove(ortam._yol("tablolar", "calisma_kaydi.csv"))
            else:
                ortam.tablo_yaz("calisma_kaydi", bos)
            assert hata_bekle(ValueError, akis.gecelik, ortam, ayarlar, params,
                              "2026-11-20 02:00:00")
            assert hata_bekle(ValueError, donem_akisi.calistir, ortam, params, "2026-10",
                              "2026-11-20 06:00:00")
            okunan = ortam.tablo_oku("calisma_kaydi")
            assert okunan is None or okunan.empty  # kayda yazılmadı: sonraki geceler de durur
    finally:
        shutil.rmtree(kok)


def test_donem_sonu_degisen_hazirlik_kuraliyla_yayin_yapmaz():
    ortam, ayarlar, params, kok = _kur(300, 8)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi=GECELER[2])
        params["hazirlik"]["sulh_avukat_kodlari"] = []
        sonuc = donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
        assert sonuc["karar"] == "KALDI" and sonuc["yayin"] is None
        kontrol = ortam.tablo_oku("kalite_sonucu").set_index("kontrol")
        assert kontrol.loc["HAZIRLIK_SURUMU", "durum"] == "KALDI"
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 07:00:00")
        sonuc = donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 08:00:00")
        assert sonuc["karar"] == "GECTI" and sonuc["yayin"] == "YENI"
        aciklama = ortam.tablo_oku("calisma_kaydi")["aciklama"].dropna().iloc[-1]
        assert "{" not in aciklama and "yeni sürüm" in aciklama
    finally:
        shutil.rmtree(kok)


def _donemler(satirlar):
    """(dosya, avukat, atama zamanı, iptal zamanı) satırlarından kapıdan geçmiş atama dönemleri."""
    tablo = pd.DataFrame([(no, av, at, ip, str(sira), None, None)
                          for sira, (no, av, at, ip) in enumerate(satirlar)],
                         columns=sema.alanlar("atama_log"))
    temiz, sonuc = kalite.denetle("atama_log", tablo, "2026-11-19", params_yukle())
    assert kalite.karar(sonuc) == "GECTI"
    return hazirlik.atama_donemleri(temiz, params_yukle()["hazirlik"])


def test_ayni_gun_yeniden_atamada_sira_saatle_belirlenir():
    for ilk, sonra in (("AV-07", "AV-03"), ("AV-03", "AV-07")):
        donem = _donemler([("D-1", ilk, "2026-10-01 09:00:00", None),
                           ("D-1", sonra, "2026-10-01 15:00:00", None)])
        assert list(donem["avukat_kodu"]) == [sonra] and donem["bitis_tarihi"].isna().all()
        assert list(donem["atama_tarihi"]) == [pd.Timestamp("2026-10-01")]
    donem = _donemler([("D-1", "AV-02", "2026-10-01 09:00:00", "2026-10-01 09:05:00"),
                       ("D-1", "AV-01", "2026-10-01 09:10:00", None)])
    assert list(donem["avukat_kodu"]) == ["AV-01"]


def test_kisa_sure_tutulup_iade_edilen_dosya_beklentiye_tam_girmez():
    """AV-1 ve AV-2 kendi 30'ar dosyalarında %30 tahsil eder; AV-1 ayrıca 30 dosyayı 10 gün
    tutup iade eder, Şirket bu dosyalarda %30 tahsil eder. İki avukat da ortalama avukattır."""
    dosya, atama, hareket = [], [], []
    for sira in range(90):
        no = "D-{:03d}".format(sira)
        dosya.append((no, "YANGIN", 10000.0, "2021-01-01"))
        avukat = "AV-1" if sira < 60 else "AV-2"
        if 30 <= sira < 60:  # 10 gün tutulup iade edilen dosyalar
            atama.append((no, avukat, "YANGIN", "2021-02-01", "2021-02-11", "IADE"))
            hareket.append((no, "2022-06-01", 3000.0))  # Şirket tahsil etti, kimseye yazılmaz
        else:
            atama.append((no, avukat, "YANGIN", "2021-02-01"))
            hareket.append((no, "2022-06-01", 3000.0))
    girdi = (pd.DataFrame(dosya, columns=["dosya_no", "brans", "rucu_tutari",
                                          "rucuya_verilis_tarihi"]), atama_tablosu(atama),
             pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]))
    puan = {}
    for payda in ("ilk_atamadan", "avukat_gunleri"):
        params = params_yukle()
        params["tahsilat"]["elde_tutma_paydasi"] = payda
        avukat, _ = tahsilat.puanla(*girdi, kesit="2026-11-19", params=params)
        puan[payda] = avukat.set_index("avukat_kodu")["puan_tutar"].to_dict()
    assert all(abs(deger - 75.0) < 0.5 for deger in puan["ilk_atamadan"].values())
    assert puan["avukat_gunleri"]["AV-1"] < 70 < 90 < puan["avukat_gunleri"]["AV-2"]
