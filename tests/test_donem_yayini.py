"""Dönem yayını: yayımlanmış dönem değişmez; kural değişikliği görünür bir düzeltme sürümüdür.

Birleşik puan yayın anında, o sürümün parametreleriyle bir kez hesaplanır. Sonradan ağırlık
ya da not eşiği değişse de geçmiş dönemlerin puanı, notu ve sırası aynı kalır.
"""
import json
import shutil

import pandas as pd

from arayuz import sunum
from avukat_perf import birlesik, donem
from hat import akis, donem_akisi
from yardimci import (agirlik_karsilastirmasi, dort_sutunlu, hata_bekle, params_yukle,
                      prova_ortami,
                      yayin_tabanini_dusur)

ANAHTAR = ["donem", "yayin_surumu", "avukat_kodu"]


def _sirali(tablo):
    return tablo.sort_values(ANAHTAR).reset_index(drop=True)


def _sira_puanla_uyumlu(tablo):
    """Her dönem ve sürümde yüksek puan küçük sıra alır; eşit puan aynı sırayı (1, 2, 2, 4)."""
    for _, grup in tablo[tablo["durum"] == "YAYIMLANDI"].groupby(["donem", "yayin_surumu"]):
        puan = grup["birlesik_puan"].astype(float)
        beklenen = puan.rank(method="min", ascending=False).astype(int)
        assert list(grup["genel_sira"].astype(int)) == list(beklenen), grup


def test_kural_degisikligi_gecmisi_degistirmez_duzeltme_surumu_ekler():
    ortam, ayarlar, params, kok = prova_ortami(600, 8)
    yayin_tabanini_dusur(params)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        for ad in ("2026-09", "2026-10"):
            assert donem_akisi.calistir(ortam, params, ad, simdi="2026-11-19 06:00:00")[
                "yayin"] == "YENI"
        once = _sirali(ortam.tablo_oku("birlesik_donem"))
        assert set(once["yayin_surumu"]) == {1}
        yayimlanan = once[once["durum"] == "YAYIMLANDI"]
        # Test boş değerleri karşılaştırmasın: her dönemde en az üç avukatın puanı yayımlanır.
        assert yayimlanan.groupby("donem").size().min() >= 3
        assert yayimlanan["birlesik_puan"].notna().all()
        _sira_puanla_uyumlu(once)
        yeni = json.loads(json.dumps(params))
        yeni["agirliklar"] = agirlik_karsilastirmasi(30, 30, 25, 15)
        sonuc = donem_akisi.calistir(ortam, yeni, "2026-10", simdi="2026-11-20 06:00:00")
        assert sonuc["yayin"] == "DUZELTME"
        sonra = _sirali(ortam.tablo_oku("birlesik_donem"))
        eski = _sirali(sonra[sonra["yayin_surumu"] == 1])
        pd.testing.assert_frame_equal(eski, once, check_dtype=False)
        ikinci = sonra[sonra["yayin_surumu"] == 2]
        assert set(ikinci["donem"]) == {"2026-10"}
        assert set(ikinci["hesap_surumu"]) != set(once["hesap_surumu"])
        _sira_puanla_uyumlu(sonra)
        # İkinci sürüm yeni ağırlıkla, aynı sütun puanlarından hesaplanır; en az bir puan değişir.
        puan = ortam.tablo_oku("puan_donem")
        puan2 = puan[(puan["donem"] == "2026-10") & (puan["yayin_surumu"] == 2)]
        beklenen = birlesik.birlestir(puan2, yeni).set_index("avukat_kodu")["birlesik_puan"]
        ikinci_puan = ikinci.set_index("avukat_kodu")["birlesik_puan"]
        pd.testing.assert_series_equal(ikinci_puan.sort_index(), beklenen.sort_index(),
                                       check_dtype=False, check_names=False)
        ilk_puan = once[once["donem"] == "2026-10"].set_index("avukat_kodu")["birlesik_puan"]
        assert (ikinci_puan.sort_index() - ilk_puan.sort_index()).abs().max() > 0.01
        # Not Geçmişi her dönemin son sürümünü gösterir: Ekim ikinci, Eylül ilk sürüm.
        kod = yayimlanan["avukat_kodu"].iloc[0]
        gecmis = {(r["donem"], r["yayin_surumu"]): r["birlesik_puan"] for r in
                  _gecmis(ortam, yeni, kod)}
        assert set(gecmis) == {("2026-09", 1), ("2026-10", 2)}
        assert abs(gecmis[("2026-10", 2)] - ikinci_puan[kod]) < 1e-9
        tekrar = donem_akisi.calistir(ortam, yeni, "2026-10", simdi="2026-11-20 07:00:00")
        assert tekrar["yayin"] == "DEGISMEDI"
        # Değişmeyen yayında birleşik tabloya dokunulmaz (yayın kimliği ve zamanı dahil).
        pd.testing.assert_frame_equal(_sirali(ortam.tablo_oku("birlesik_donem")), sonra)
    finally:
        shutil.rmtree(kok)


def _gecmis(ortam, params, kod):
    tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
    return sunum.sayfa("avukat", tablolar, params, {"kod": kod})["bilesenler"]["avukat.gecmis"]


def test_surum_ekle_yarim_kalan_denemeyi_temizler():
    eski = pd.DataFrame({"donem": ["2026-09", "2026-10", "2026-10"], "yayin_surumu": [1, 1, 2],
                         "avukat_kodu": ["AV-1", "AV-1", "AV-1"], "birlesik_puan": [1., 2., 9.]})
    yeni = pd.DataFrame({"donem": ["2026-10"], "yayin_surumu": [2], "avukat_kodu": ["AV-1"],
                         "birlesik_puan": [3.0]})
    tablo = _sirali(donem.surum_ekle(eski, yeni, "2026-10", 2))
    assert list(tablo["birlesik_puan"]) == [1.0, 2.0, 3.0]
    assert donem.surum_ekle(None, yeni, "2026-10", 2).equals(yeni)


def test_ayni_icerik_farkli_kural_duzeltme_sayilir():
    tablo = pd.DataFrame({"avukat_kodu": ["AV-1"], "donem": ["2026-10"], "sutun": ["tahsilat"],
                          "puan": [80.0], "durum": ["GECERLI"]})
    bilgi = {"calisma_kimligi": "C-1", "hesap_surumu": "h1", "yayin_zamani": "z"}
    ilk, _ = donem.yayinla(None, tablo, "2026-10", bilgi)
    _, sonuc = donem.yayinla(ilk, tablo, "2026-10", dict(bilgi, hesap_surumu="h2"))
    assert sonuc == "DUZELTME"


def _yazim_bozuk(ortam, hedef):
    asil = ortam.tablo_yaz

    def yaz(ad, tablo):
        if ad == hedef:
            raise IOError("yazma hatası")
        return asil(ad, tablo)
    ortam.tablo_yaz = yaz
    return asil


def _ekrandaki_surum(ortam, params):
    kodlar = sorted(set(ortam.tablo_oku("birlesik_donem")["avukat_kodu"]))
    return {r["yayin_surumu"] for kod in kodlar for r in _gecmis(ortam, params, kod)}


def test_yarida_kalan_yayin_ekrana_cikmaz_ve_tekrarda_tamamlanir():
    ortam, ayarlar, params, kok = prova_ortami(600, 8)
    yayin_tabanini_dusur(params)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
        yeni = json.loads(json.dumps(params))
        yeni["agirliklar"] = agirlik_karsilastirmasi(30, 30, 25, 15)
        # Yayının kendisi (puan_donem) yazılamazsa yeni ağırlıklı sürüm ekrana çıkmaz; kurallar
        # geri alınıp yeniden çalışınca da çıkmaz (önceden yayımlanmamış sürüm kalıcı görünürdü).
        asil = _yazim_bozuk(ortam, "puan_donem")
        assert hata_bekle(IOError, donem_akisi.calistir, ortam, yeni, "2026-10",
                          "2026-11-20 06:00:00")
        ortam.tablo_yaz = asil
        assert _ekrandaki_surum(ortam, params) == {1}
        assert donem_akisi.calistir(ortam, params, "2026-10", "2026-11-20 07:00:00")[
            "yayin"] == "DEGISMEDI"
        assert set(ortam.tablo_oku("birlesik_donem")["yayin_surumu"]) == {1}
        # Yayın yazılıp birleşik tablo yazılamazsa ekran son yayımlanmış birleşik sürümü
        # gösterir; tekrarda eksik sürüm yayımlanan sürümün kendi bilgileriyle tamamlanır.
        asil = _yazim_bozuk(ortam, "birlesik_donem")
        assert hata_bekle(IOError, donem_akisi.calistir, ortam, yeni, "2026-10",
                          "2026-11-21 06:00:00")
        ortam.tablo_yaz = asil
        assert _ekrandaki_surum(ortam, yeni) == {1}
        assert donem_akisi.calistir(ortam, yeni, "2026-10", "2026-11-21 07:00:00")[
            "yayin"] == "DEGISMEDI"
        assert _ekrandaki_surum(ortam, yeni) == {2}
        puan = ortam.tablo_oku("puan_donem")
        puan2 = puan[puan["yayin_surumu"] == 2]
        tablo = _sirali(ortam.tablo_oku("birlesik_donem"))
        ikinci = tablo[tablo["yayin_surumu"] == 2].set_index("avukat_kodu")
        assert ikinci["birlesik_puan"].notna().sum() >= 3
        assert set(ikinci["calisma_kimligi"]) == set(puan2["calisma_kimligi"])
        assert set(ikinci["hesap_surumu"]) == set(puan2["hesap_surumu"])
        beklenen = birlesik.birlestir(puan2, yeni).set_index("avukat_kodu")
        pd.testing.assert_series_equal(ikinci["birlesik_puan"].sort_index(),
                                       beklenen["birlesik_puan"].sort_index(), check_dtype=False)
        # Değişmeyen yayın dönem tablolarına hiç yazmaz.
        _yazim_bozuk(ortam, "birlesik_donem")
        assert donem_akisi.calistir(ortam, yeni, "2026-10", "2026-11-21 08:00:00")[
            "yayin"] == "DEGISMEDI"
        _yazim_bozuk(ortam, "puan_donem")
        assert donem_akisi.calistir(ortam, yeni, "2026-10", "2026-11-21 09:00:00")[
            "yayin"] == "DEGISMEDI"
        pd.testing.assert_frame_equal(_sirali(ortam.tablo_oku("birlesik_donem")), tablo)
    finally:
        shutil.rmtree(kok)


def test_notu_degistiren_kucuk_fark_duzeltme_sayilir():
    # 74,0549996 → 74,0550001: altı ondalıkta ikisi de 74,055 (eskiden DEGISMEDI) ama iki
    # ondalıkta 74,05 → 74,06 ve birleşik puan 84,99 (B+) → 85,00 (A).
    def tablo(tahsilat):
        return pd.DataFrame({"avukat_kodu": ["AV-1"] * 4, "donem": ["2026-10"] * 4,
                             "sutun": ["tahsilat", "sure", "kalite", "davranis"],
                             "puan": [tahsilat, 89.01, 89.84, 98.71], "durum": ["GECERLI"] * 4})
    bilgi = {"calisma_kimligi": "C-1", "hesap_surumu": "h1", "yayin_zamani": "z"}
    ilk, _ = donem.yayinla(None, tablo(74.0549996), "2026-10", bilgi)
    params = dort_sutunlu()
    params["agirliklar"] = agirlik_karsilastirmasi(35, 25, 30, 10)  # örnek bu ağırlıkla kuruldu
    notlar = [birlesik.birlestir(tablo(t), params)["performans_notu"].iloc[0]
              for t in (74.0549996, 74.0550001)]
    assert notlar == ["B+", "A"]
    assert donem.yayinla(ilk, tablo(74.0550001), "2026-10", bilgi)[1] == "DUZELTME"
    # Yayımlanan hiçbir sayıyı değiştirmeyen fark yeni sürüm açmaz.
    assert donem.yayinla(ilk, tablo(74.0549999), "2026-10", bilgi)[1] == "DEGISMEDI"


def test_yarim_yazilmis_birlesik_surum_tekrarda_tamamlanir():
    """Düzeltme sürümü yazılırken tablo yarıda kalır (eski satırlar ve yeni sürümün bir satırı
    depoya ulaşmış): tekrar çalışınca yeni sürüm bütün avukatlarla tamamlanır, eski sürüm aynı
    kalır. Sonuç kesintisiz çalışmayla aynıdır."""
    sonuclar = []
    for kesik in (False, True):
        ortam, ayarlar, params, kok = prova_ortami(300, 8)
        try:
            akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
            donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
            once = len(ortam.tablo_oku("birlesik_donem"))
            yeni = json.loads(json.dumps(params))
            yeni["agirliklar"] = agirlik_karsilastirmasi(30, 30, 25, 15)
            if kesik:
                asil = ortam.tablo_yaz

                def yaz(ad, tablo):
                    if ad == "birlesik_donem":
                        asil(ad, tablo.iloc[:once + 1])
                        raise IOError("yazım yarıda kaldı")
                    return asil(ad, tablo)
                ortam.tablo_yaz = yaz
                assert hata_bekle(IOError, donem_akisi.calistir, ortam, yeni, "2026-10",
                                  "2026-11-20 06:00:00")
                ortam.tablo_yaz = asil
                assert donem_akisi.calistir(ortam, yeni, "2026-10", "2026-11-20 07:00:00")[
                    "yayin"] == "DEGISMEDI"
            else:
                donem_akisi.calistir(ortam, yeni, "2026-10", "2026-11-20 06:00:00")
            tablo = _sirali(ortam.tablo_oku("birlesik_donem"))
            sonuclar.append(tablo.drop(columns=["calisma_kimligi", "yayin_zamani"]))
            assert sorted(set(tablo["yayin_surumu"])) == [1, 2]
        finally:
            shutil.rmtree(kok)
    pd.testing.assert_frame_equal(sonuclar[0], sonuclar[1], check_dtype=False)


def test_kesik_yayin_tablosu_calismayi_durdurur():
    """Tablo eski sürümlerin satırlarını kaybetmişse (kesik ya da elle temizlenmiş) dönem sonu
    yazmaz, durur: aksi hâlde yayımlanmış geçmiş kalıcı olarak silinirdi."""
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
        for ad in ("birlesik_donem", "puan_donem"):
            tam = ortam.tablo_oku(ad)
            ortam.tablo_yaz(ad, tam.iloc[:1])
            assert hata_bekle(ValueError, donem_akisi.calistir, ortam, params, "2026-10",
                              "2026-11-19 07:00:00")
            ortam.tablo_yaz(ad, tam)
        assert donem_akisi.calistir(ortam, params, "2026-10", "2026-11-19 08:00:00")[
            "yayin"] == "DEGISMEDI"
    finally:
        shutil.rmtree(kok)


def test_baska_kimlikli_birlesik_surum_yeniden_yazilir():
    """Birleşik tabloda yayımlanan sürümün numarasıyla ama başka bir denemenin kimliği ve kural
    sürümüyle satırlar varsa (yetim deneme) bunlar yayımlanan sürümün değerleriyle değiştirilir."""
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
        birlesik_tablo = ortam.tablo_oku("birlesik_donem")
        yetim = birlesik_tablo.assign(yayin_surumu=2, calisma_kimligi="C-YETIM",
                                      hesap_surumu="eski", birlesik_puan=1.0)
        ortam.tablo_yaz("birlesik_donem", pd.concat([birlesik_tablo, yetim], ignore_index=True))
        yeni = json.loads(json.dumps(params))
        yeni["agirliklar"] = agirlik_karsilastirmasi(30, 30, 25, 15)
        assert donem_akisi.calistir(ortam, yeni, "2026-10", "2026-11-20 06:00:00")[
            "yayin"] == "DUZELTME"
        ikinci = ortam.tablo_oku("birlesik_donem")
        ikinci = ikinci[ikinci["yayin_surumu"] == 2]
        assert "C-YETIM" not in set(ikinci["calisma_kimligi"]) and len(ikinci) == len(yetim)
    finally:
        shutil.rmtree(kok)


def _sure_durumu(ortam, donem_adi):
    puan = ortam.tablo_oku("puan_donem")
    return set(puan[(puan["donem"] == donem_adi) & (puan["sutun"] == "sure")]["durum"])


def test_golge_gecesinden_sonra_yeniden_yayin_degismez():
    """Ekim canlı geceyle yayımlandıktan sonra gölge mod açılırsa aynı veriyle yeniden yayın
    DEGISMEDI olur. Önceden dönem bugünkü gölge ayarıyla hesaplanıp
    sürümleniyordu: süre sütunu GOLGE_MOD'a düşüyor, Ekim için düzeltme sürümü açılıyordu."""
    ortam, ayarlar, params, kok = prova_ortami(600, 8)
    yayin_tabanini_dusur(params)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        assert donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")[
            "yayin"] == "YENI"
        assert "GECERLI" in _sure_durumu(ortam, "2026-10")
        once = _sirali(ortam.tablo_oku("puan_donem"))
        params["uyari"]["golge_mod"] = True
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-20 02:00:00")
        assert donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-20 06:00:00")[
            "yayin"] == "DEGISMEDI"
        pd.testing.assert_frame_equal(_sirali(ortam.tablo_oku("puan_donem")), once)
    finally:
        shutil.rmtree(kok)


def test_donem_kesitindeki_golge_durumuyla_hesaplanir():
    """Gölge gecesi önceki gecenin gününden sonrasını kendi gününe kadar kapsar: 30 Eylül canlı,
    31 Ekim gölge gecesiyse Eylül (kesit 30 Eylül) canlı, Ekim (kesit 31 Ekim) gölgede yayımlanır;
    bugünkü (canlı) ayar ikisini de değiştirmez."""
    ortam, ayarlar, params, kok = prova_ortami(600, 8)
    yayin_tabanini_dusur(params)
    try:
        for gece, golge in (("2026-09-30", False), ("2026-10-31", True), ("2026-11-19", False)):
            params["uyari"]["golge_mod"] = golge
            akis.gecelik(ortam, ayarlar, params, simdi=gece + " 02:00:00")
        for ad in ("2026-09", "2026-10"):
            assert donem_akisi.calistir(ortam, params, ad, simdi="2026-11-19 06:00:00")[
                "yayin"] == "YENI"
        eylul, ekim = _sure_durumu(ortam, "2026-09"), _sure_durumu(ortam, "2026-10")
        assert "GECERLI" in eylul and "GOLGE_MOD" not in eylul
        assert "GOLGE_MOD" in ekim and "GECERLI" not in ekim
    finally:
        shutil.rmtree(kok)


def _donem_satirlari(ortam, kimlik):
    kayit = ortam.tablo_oku("calisma_kaydi")
    kayit = kayit[(kayit["tur"] == "DONEM_SONU") & (kayit["calisma_kimligi"] == kimlik)]
    kalite = ortam.tablo_oku("kalite_sonucu")
    return kayit, kalite[kalite["calisma_kimligi"] == kimlik]


def test_donem_sonu_basarisizligi_calisma_kaydina_ve_kalite_sonucuna_gecer():
    """Kesik model tablosu KALDI (VERI_KAYBI), yayın hatası KALDI (HESAP_HATASI) olarak kayda
    geçer; önceden ikisinde de çalışmaya ait hiçbir satır yazılmıyordu."""
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        tam = ortam.tablo_oku("model_dosya")
        ortam.tablo_yaz("model_dosya", tam.iloc[1:])
        sonuc = donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
        assert sonuc["karar"] == "KALDI" and sonuc["yayin"] is None
        kayit, kalite = _donem_satirlari(ortam, sonuc["calisma_kimligi"])
        assert list(kayit["durum"]) == ["KALDI"] and "VERI_KAYBI" in kayit["aciklama"].iloc[0]
        assert list(kalite["kontrol"]) == ["MODEL_TABLOSU"] and list(kalite["durum"]) == ["KALDI"]
        ortam.tablo_yaz("model_dosya", tam)
        # İsteğe bağlı model ya da gözlem tablosu kesikse de durur: kesik tahsilat hareketiyle
        # Tahsilat sessizce "kaynak bekleniyor" yayımlanırdı.
        for ad in ("model_hareket", "gozlem_esas"):
            tablo = ortam.tablo_oku(ad)
            ortam.tablo_yaz(ad, tablo.iloc[1:])
            sonuc = donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:30:00")
            assert sonuc["karar"] == "KALDI", ad
            assert ad in _donem_satirlari(ortam, sonuc["calisma_kimligi"])[0]["aciklama"].iloc[0]
            ortam.tablo_yaz(ad, tablo)
        asil = donem.yayinla

        def bozuk(*argumanlar):
            raise IOError("yazılamadı")
        donem.yayinla = bozuk
        try:
            assert hata_bekle(IOError, donem_akisi.calistir, ortam, params, "2026-10",
                              "2026-11-19 07:00:00")
        finally:
            donem.yayinla = asil
        kayit = ortam.tablo_oku("calisma_kaydi")
        son = kayit[kayit["tur"] == "DONEM_SONU"].iloc[-1]
        assert son["durum"] == "KALDI" and "HESAP_HATASI" in son["aciklama"]
        _, kalite = _donem_satirlari(ortam, son["calisma_kimligi"])
        assert list(kalite["kontrol"]) == ["HESAP_HATASI"]
        assert ortam.tablo_oku("puan_donem") is None
    finally:
        shutil.rmtree(kok)


def test_model_tablosu_hic_yazilmadiysa_kaynak_bekleniyor_kayda_gecer():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        ayarlar["kaynaklar"]["dosya"]["yontem"] = "bekliyor"
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        sonuc = donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
        assert sonuc["karar"] == "KAYNAK_BEKLENIYOR"
        kayit, kalite = _donem_satirlari(ortam, sonuc["calisma_kimligi"])
        assert list(kayit["durum"]) == ["KAYNAK_BEKLENIYOR"] and kalite.empty
    finally:
        shutil.rmtree(kok)


def test_donem_zorunlu_model_tablolari_zorunlu_kaynaklardan_turetilir():
    from avukat_perf import sema
    from hat import donem_kayit, model
    assert set(donem_kayit.MODEL_KAYNAGI) == set(model.TABLOLAR)
    assert set(donem_kayit.MODEL_KAYNAGI.values()) <= set(sema.KAYNAKLAR)
    assert donem_kayit.ZORUNLU == tuple(ad for ad, kaynak in donem_kayit.MODEL_KAYNAGI.items()
                                        if kaynak in sema.zorunlu_kaynaklar())
    assert "dosya" in donem_kayit.ZORUNLU and "atama_donemi" in donem_kayit.ZORUNLU


def test_yayindan_sonra_kalite_kaydi_yazilamazsa_yayin_kaydi_kaldi_olmaz():
    """Yayın yapılıp çalışma kaydı yazıldıktan sonra kalite_sonucu yazılamazsa senaryo hata
    verir ama yayının DONEM_SONU kaydı GECTI kalır (hata yolu kaydı onceki +
    KALDI satırıyla yeniden yazıp yayımlanmış sürümü başarısız gösteriyordu)."""
    from hat import calisma
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    asil = calisma.kalite_ekle
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")

        def bozuk(*argumanlar):
            raise IOError("kalite_sonucu yazılamadı")
        calisma.kalite_ekle = bozuk
        assert hata_bekle(IOError, donem_akisi.calistir, ortam, params, "2026-10",
                          "2026-11-19 06:00:00")
        calisma.kalite_ekle = asil
        kayit = ortam.tablo_oku("calisma_kaydi")
        son = kayit[kayit["tur"] == "DONEM_SONU"]
        assert list(son["durum"]) == ["GECTI"], list(son["durum"])
        assert "puan_donem=" in son["uretilen"].iloc[0]
        assert "HESAP_HATASI" not in son["aciklama"].iloc[0]
        assert len(ortam.tablo_oku("puan_donem")) > 0
    finally:
        calisma.kalite_ekle = asil
        shutil.rmtree(kok)
