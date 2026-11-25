"""params modülünün testleri. Düz assert kullanır; pytest olmadan da çalışır."""
from avukat_perf import params as pr
from yardimci import agirlik_karsilastirmasi, hata_bekle, params_yukle


def _degistir(bolum, alan, deger):
    params = params_yukle()
    params[bolum][alan] = deger
    return params


def test_varsayilan_parametreler_gecerli():
    assert pr.dogrula(params_yukle()) == []


def test_eksik_bolum_yakalanir():
    params = params_yukle()
    del params["tahsilat"]
    assert pr.dogrula(params) == ["eksik bölüm: tahsilat"]


def test_eksik_alan_yakalanir():
    params = params_yukle()
    del params["kriter1"]["uyari_gun"]
    del params["kriter1"]["sonlanan_atamada_dusum_korunur"]
    assert pr.dogrula(params) == ["eksik alan: kriter1.sonlanan_atamada_dusum_korunur",
                                  "eksik alan: kriter1.uyari_gun"]


def test_tirnak_icinde_sayi_yakalanir():
    hatalar = pr.dogrula(_degistir("kriter1", "uyari_gun", "10"))
    assert hatalar == ["tam sayı olmalı: kriter1.uyari_gun"]


def test_gun_ve_ay_sayisi_tam_sayi_olmali():
    assert pr.dogrula(_degistir("kriter1", "dusum_ay_diger", 2.0)) == [
        "tam sayı olmalı: kriter1.dusum_ay_diger"]
    assert pr.dogrula(_degistir("kriter2", "dusum_ay", 4.5)) == [
        "tam sayı olmalı: kriter2.dusum_ay"]


def test_mantiksal_alan_yalniz_true_false_olabilir():
    for deger in ("true", 1, None):
        hatalar = pr.dogrula(_degistir("kriter1", "sonlanan_atamada_dusum_korunur", deger))
        assert hatalar == ["true ya da false olmalı: kriter1.sonlanan_atamada_dusum_korunur"]
    assert pr.dogrula(_degistir("tahsilat", "enflasyon_duzeltme", False)) == []


def test_sayi_yerine_mantiksal_deger_yakalanir():
    hatalar = pr.dogrula(_degistir("tahsilat", "egim", True))
    assert hatalar == ["sayı olmalı: tahsilat.egim"]


def test_olgunluk_ayi_pozitif_tam_sayi_olmali():
    for olgunluk in ({"TRAFIK": 24}, {"DIGER": 36.5}, {"DIGER": 0}):
        assert len(pr.dogrula(_degistir("tahsilat", "olgunluk_ay", olgunluk))) == 1


def test_agirlik_karsilastirmasi_tutarsizsa_hata():
    assert len(pr.dogrula(_degistir("agirliklar", "tahsilat/kalite", 9))) == 1


def test_nan_ve_sonsuz_hicbir_alanda_gecmez():
    # NaN ağırlık eskiden geçiyordu: 26 avukatın birleşik puanı boşken durumu YAYIMLANDI oluyordu.
    nan, sonsuz = float("nan"), float("inf")
    assert pr.dogrula(_degistir("agirliklar", "sure/kalite", nan)) == [
        "sonlu bir sayı olmalı (NaN ya da sonsuz olamaz): agirliklar.sure/kalite"]
    assert hata_bekle(ValueError, pr.dogrula_veya_dur, _degistir("agirliklar", "sure/kalite", nan))
    assert pr.dogrula(_degistir("sure_puani", "egim", sonsuz))
    params = params_yukle()
    params["tahsilat"]["tutar_bantlari"] = [50000.0, nan]
    params["notlar"][1][1] = -sonsuz
    assert pr.dogrula(params) == [
        "sonlu bir sayı olmalı (NaN ya da sonsuz olamaz): notlar[1][1]",
        "sonlu bir sayı olmalı (NaN ya da sonsuz olamaz): tahsilat.tutar_bantlari[1]"]


def test_iki_agirlik_adayi_da_gecerli():
    params = params_yukle()
    params["agirliklar"] = agirlik_karsilastirmasi(35, 30, 25, 10)
    assert pr.dogrula(params) == []


def _notlar(notlar):
    params = params_yukle()
    params["notlar"] = notlar
    return pr.dogrula(params)


def test_not_olcegi_bicimi_ve_esikleri():
    assert _notlar([["A", 85], ["B+", 75], ["B-", 55], ["C", 0]]) == []
    assert _notlar([["GECTI", 50], ["KALDI", 0]]) == []
    hata = ["notlar: [ad, eşik] listesi; adlar tekrarsız, eşikler 100'den 0'a azalan"]
    for notlar in ([], [["A", 85], ["B", 85], ["C", 0]], [["A", 85], ["B", 90], ["C", 0]],
                   [["A", 85], ["C", 10]], [["A", 101], ["C", 0]], [["A", 85], ["A", 0]],
                   [["A", "85"], ["C", 0]], [["A", 85, 1], ["C", 0]], [[85, "A"], ["C", 0]],
                   [{"A": 85}, ["C", 0]], [["A", True], ["C", 0]]):
        assert _notlar(notlar) == hata, notlar
    assert _notlar({"A": 85}) == ["liste olmalı: notlar"]


def test_uyari_esigi_dusumden_once_olmali():
    assert len(pr.dogrula(_degistir("kriter1", "uyari_gun", 20))) == 1
    assert len(pr.dogrula(_degistir("kriter2", "uyari_ay", 6))) == 1


def test_yeterlilik_orani_bicimi():
    assert len(pr.dogrula(_degistir("kalite_davranis", "yeterlilik", [3, 2]))) == 1
    assert len(pr.dogrula(_degistir("kalite_davranis", "yeterlilik", [2]))) == 1
    assert pr.dogrula(_degistir("kalite_davranis", "yeterlilik", "2/3")) == [
        "liste olmalı: kalite_davranis.yeterlilik"]


def test_tutar_bantlari_artan_pozitif_olmali():
    for bant in ([50000, 10000], [0, 10000], [10000, 10000], ["10000"], [True]):
        hatalar = pr.dogrula(_degistir("tahsilat", "tutar_bantlari", bant))
        assert hatalar == ["tahsilat.tutar_bantlari artan pozitif sayılar olmalı"], bant
    for bant in ([], [10000], [10000, 50000.5, 250000]):
        assert pr.dogrula(_degistir("tahsilat", "tutar_bantlari", bant)) == [], bant


def test_guncellik_penceresi_pozitif_tam_sayi_olmali():
    assert pr.dogrula(_degistir("tahsilat", "guncellik_pencere_ay", 0)) == [
        "tahsilat.guncellik_pencere_ay, aylik_pencere_ay ve yillik_yil_sayisi pozitif olmalı"]
    assert pr.dogrula(_degistir("tahsilat", "yillik_yil_sayisi", 0))
    assert pr.dogrula(_degistir("tahsilat", "aylik_pencere_ay", 0)) == [
        "tahsilat.guncellik_pencere_ay, aylik_pencere_ay ve yillik_yil_sayisi pozitif olmalı"]
    assert pr.dogrula(_degistir("sure_puani", "pencere_ay", 0)) == [
        "sure_puani.pencere_ay pozitif olmalı"]
    assert pr.dogrula(_degistir("kalite_davranis", "mevcut_alanlar", ["dosyaya_hakimiyet"]))
    assert pr.dogrula(_degistir("tahsilat", "guncellik_pencere_ay", 12.0)) == [
        "tam sayı olmalı: tahsilat.guncellik_pencere_ay"]


def test_gruplama_yalniz_bilinen_sutunlar():
    for grup in ([], ["brans", "yas"], ["brans", "brans"], [{"brans": 1}]):
        assert len(pr.dogrula(_degistir("tahsilat", "gruplama", grup))) == 1, grup
    for grup in (["brans"], ["brans", "yas_bandi"], ["yas_bandi", "tutar_bandi", "brans"]):
        assert pr.dogrula(_degistir("tahsilat", "gruplama", grup)) == [], grup
    assert params_yukle()["tahsilat"]["gruplama"] == ["brans", "yas_bandi", "tutar_bandi"]


def test_yas_bantlari_artan_pozitif_tam_sayi():
    hata = ["tahsilat.yas_bantlari artan pozitif tam sayılar (ay) olmalı"]
    for bant in ([0, 12], [24, 12], [12, 12], [-12], [12.5, 24], ["12"]):
        assert pr.dogrula(_degistir("tahsilat", "yas_bantlari", bant)) == hata, bant
    for bant in ([], [12], [12, 24, 36, 48, 60, 84]):
        assert pr.dogrula(_degistir("tahsilat", "yas_bantlari", bant)) == [], bant


def test_bilesen_agirliklari_uc_bilesen_negatif_degil_toplam_bir():
    hata = ["tahsilat.bilesen_agirliklari: tutar, siklik ve guncellik için negatif olmayan sayı; "
            "toplamı 1"]
    yanlislar = ({"tutar": 0.6, "siklik": 0.2}, {"tutar": 0.7, "siklik": 0.2, "guncellik": 0.2},
                 {"tutar": 1.2, "siklik": -0.2, "guncellik": 0.0},
                 {"tutar": 0.6, "siklik": 0.2, "guncellik": 0.1, "hiz": 0.1},
                 {"tutar": "0.6", "siklik": 0.2, "guncellik": 0.2})
    for agirlik in yanlislar:
        assert pr.dogrula(_degistir("tahsilat", "bilesen_agirliklari", agirlik)) == hata, agirlik
    for agirlik in ({"tutar": 1, "siklik": 0, "guncellik": 0},
                    {"tutar": 0.5, "siklik": 0.25, "guncellik": 0.25}):
        assert pr.dogrula(_degistir("tahsilat", "bilesen_agirliklari", agirlik)) == [], agirlik
    assert params_yukle()["tahsilat"]["bilesen_agirliklari"] == {
        "tutar": 0.6, "siklik": 0.2, "guncellik": 0.2}


def test_olay_guven_sabiti_pozitif_olmali():
    for deger in (0, -1):
        assert pr.dogrula(_degistir("tahsilat", "olay_guven_sabiti", deger)) == [
            "tahsilat.olay_guven_sabiti pozitif olmalı"]
    assert pr.dogrula(_degistir("tahsilat", "olay_guven_sabiti", 2.5)) == []


def test_kalite_davranis_teyit_bekleyen_null_degerler_gecerli():
    kd = params_yukle()["kalite_davranis"]
    assert kd["olcek"] == {"en_dusuk": None, "en_yuksek": None} and kd["ters_yonlu"] is None
    assert [len(kd["alt_basliklar"][ad]) for ad in ("kalite", "davranis")] == [6, 7]


def test_kalite_davranis_olcek_ve_yon_kurallari():
    gecerli = ({"en_dusuk": 1, "en_yuksek": 5}, {"en_dusuk": 0, "en_yuksek": 100.0})
    for olcek in gecerli:
        assert pr.dogrula(_degistir("kalite_davranis", "olcek", olcek)) == [], olcek
    gecersiz = ({"en_dusuk": 5, "en_yuksek": 1}, {"en_dusuk": 1, "en_yuksek": None},
                {"en_dusuk": "1", "en_yuksek": 5}, {"en_dusuk": 1}, {"en_dusuk": True,
                                                                    "en_yuksek": 5})
    for olcek in gecersiz:
        assert len(pr.dogrula(_degistir("kalite_davranis", "olcek", olcek))) == 1, olcek
    assert pr.dogrula(_degistir("kalite_davranis", "ters_yonlu", ["dosyaya_hakimiyet"])) == []
    assert pr.dogrula(_degistir("kalite_davranis", "ters_yonlu", [])) == []
    assert len(pr.dogrula(_degistir("kalite_davranis", "ters_yonlu", ["yok_boyle_kod"]))) == 1
    assert pr.dogrula(_degistir("kalite_davranis", "ters_yonlu", "hepsi")) == [
        "liste ya da null olmalı: kalite_davranis.ters_yonlu"]


def test_kalite_davranis_alt_baslik_ve_coklu_kurali():
    for basliklar in ({"kalite": ["a"]}, {"kalite": ["a"], "davranis": ["a"]},
                      {"kalite": [], "davranis": ["b"]}, {"kalite": ["a"], "davranis": "b"}):
        hatalar = pr.dogrula(_degistir("kalite_davranis", "alt_basliklar", basliklar))
        assert len(hatalar) == 1, basliklar
    assert len(pr.dogrula(_degistir("kalite_davranis", "coklu_degerlendirme", "en_yuksek"))) == 1
    assert pr.dogrula(_degistir("kalite_davranis", "coklu_degerlendirme", "son")) == []
    assert len(pr.dogrula(_degistir("kalite_davranis", "pencere_ay", 0))) == 1


def test_yeni_bolumlerin_kurallari():
    assert pr.dogrula(_degistir("hazirlik", "iptal_yorumu", "hatali_iptal")) == []
    assert len(pr.dogrula(_degistir("hazirlik", "iptal_yorumu", "bilinmiyor"))) == 1
    # Seçenekli alan: yalnız izinli değerler; hata iletisi seçenekleri sayar.
    assert pr.dogrula(_degistir("hazirlik", "ayni_avukata_yeniden_atama", "yeni_donem")) == []
    for yanlis in ("sur", True, None, ["surer"]):
        assert pr.dogrula(_degistir("hazirlik", "ayni_avukata_yeniden_atama", yanlis)) == [
            "yeni_donem ya da surer olmalı: hazirlik.ayni_avukata_yeniden_atama"], yanlis
    assert pr.dogrula(_degistir("tahsilat", "elde_tutma_paydasi", "dosya_omru")) == [
        "ilk_atamadan ya da avukat_gunleri olmalı: tahsilat.elde_tutma_paydasi"]
    assert pr.dogrula(_degistir("hazirlik", "sulh_alani", "grup")) == []
    assert pr.dogrula(_degistir("hazirlik", "sulh_alani", 3)) == [
        "metin ya da null olmalı: hazirlik.sulh_alani"]
    assert len(pr.dogrula(_degistir("kalite", "mutabakat_tolerans", 1.0))) == 1
    assert len(pr.dogrula(_degistir("kalite", "satir_sapma_orani", 0))) == 1
    assert len(pr.dogrula(_degistir("kriter2", "rucu_kodu", ""))) == 1
    assert len(pr.dogrula(_degistir("sure_puani", "pencere_ay", 0))) == 1
    assert pr.dogrula(_degistir("uyari", "golge_mod", "evet")) == [
        "true ya da false olmalı: uyari.golge_mod"]


def test_gecersiz_parametre_hesabi_durdurur():
    assert hata_bekle(ValueError, pr.dogrula_veya_dur, _degistir("tahsilat", "egim", 0))
    gecerli = params_yukle()
    assert pr.dogrula_veya_dur(gecerli) is gecerli


def test_sure_puani_sifira_bolme_ve_ters_egim_yakalanir():
    # guven_sabiti 0 iken O = E = 0 olan avukatta R = 0 / 0 olurdu.
    for alan, deger in (("guven_sabiti", 0), ("egim", -50), ("yeterli_dosya", 0)):
        assert pr.dogrula(_degistir("sure_puani", alan, deger)), alan


def test_yeterlilik_ondalik_oranla_verilemez():
    # [0.6667, 1] ile 4/6 = 0.6666... yetersiz sayılırdı; tam sayı oran zorunlu.
    assert pr.dogrula(_degistir("kalite_davranis", "yeterlilik", [0.6667, 1]))


def test_kalite_sapma_en_az_satir():
    assert pr.dogrula(_degistir("kalite", "sapma_en_az_satir", -1))
    params = params_yukle()
    del params["kalite"]["sapma_en_az_satir"]
    assert pr.dogrula(params) == ["eksik alan: kalite.sapma_en_az_satir"]


def test_teyit_listesindeki_anahtar_tanimli_olmali():
    params = params_yukle()
    params["_teyit_bekleyen"] = params["_teyit_bekleyen"] + ["tahsilat.yok_boyle", "olmayan"]
    assert pr.dogrula(params) == ["_teyit_bekleyen: tanımsız anahtar tahsilat.yok_boyle",
                                  "_teyit_bekleyen: tanımsız anahtar olmayan"]


def test_bilinmeyen_anahtar_yazim_hatasi_sayilir():
    # Ek dosyadaki yazım hatası sessizce hiçbir şeyi değiştirmezdi.
    for degistir, beklenen in (
            (lambda p: p["kriter1"].update(uyari_gn=5), "bilinmeyen anahtar: kriter1.uyari_gn"),
            (lambda p: p.update(kritr1={}), "bilinmeyen anahtar: kritr1"),
            (lambda p: p["agirliklar"].update({"sur/kalite": 1}),
             "agirliklar: bilinmeyen çift sur/kalite")):
        params = params_yukle()
        degistir(params)
        assert beklenen in pr.dogrula(params), beklenen
    params = params_yukle()
    params["_ek_not"] = "açıklama"
    params["kriter1"]["_not"] = "açıklama"
    assert pr.dogrula(params) == []


def test_uyari_oto_disi_dusumden_once_olmali():
    # 30 günlük uyarı 1 aylık oto dışı düşümle: Şubat'ta atanan dosya TURUNCU'ya SARI'dan önce
    # ulaşırdı (önceden yalnız oto düşüm günüyle karşılaştırılıyordu).
    hata = ("kriter1: uyari_gun oto dışı düşümden önce olmalı (dusum_ay_diger ayın en kısa gün "
            "karşılığından küçük)")
    params = params_yukle()
    params["kriter1"].update(uyari_gun=28, dusum_gun_oto=40, dusum_ay_diger=1)  # Şubat: 28 gün
    assert hata in pr.dogrula(params)
    params["kriter1"].update(uyari_gun=27)
    assert pr.dogrula(params) == []
    # İki ayın en kısa karşılığı 59 gün (Aralık sonu → Şubat sonu); sınır gereğinden sıkı değil.
    params["kriter1"].update(uyari_gun=58, dusum_gun_oto=70, dusum_ay_diger=2)
    assert pr.dogrula(params) == []
    params["kriter1"].update(uyari_gun=59)
    assert hata in pr.dogrula(params)
    assert [pr.en_kisa_ay_suresi(ay) for ay in (1, 2, 3, 12)] == [28, 59, 89, 365]


def test_ic_sozlukte_aciklama_anahtari_acik_hata_verir():
    # Önceden "_not" iç sözlükte anlaşılmaz bir hatayla (ör. "aylar pozitif tam sayı olmalı")
    # reddediliyordu; ek dosyada yazılırsa ne yapılacağı açık olmalı.
    params = params_yukle()
    params["tahsilat"]["olgunluk_ay"]["_not"] = "açıklama"
    assert "açıklama anahtarı (_) yalnız bölüm düzeyinde yazılır: tahsilat.olgunluk_ay" in \
        pr.dogrula(params)


def test_tahsilat_ve_sure_puani_olcegi_ayni_olmali():
    """Birleşik puan sütunları aynı anlamda toplar: taban (75) ve eğim (50) tahsilatta ve süre
    puanında aynıdır; biri değişip öteki kalırsa gece başlamaz."""
    for bolum, alan, deger in (("tahsilat", "taban", 70), ("sure_puani", "egim", 40)):
        params = params_yukle()
        params[bolum][alan] = deger
        assert [h for h in pr.dogrula(params) if "taban ve egim" in h], (bolum, alan)
    params = params_yukle()
    for bolum in ("tahsilat", "sure_puani"):
        params[bolum].update(taban=70, egim=40)
    assert pr.dogrula(params) == []
