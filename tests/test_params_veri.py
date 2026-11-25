"""Parametre doğrulaması: branş kodlarının üç listede tutarlılığı, kod listesi öğeleri, sulh
alanı, hareket türü listesi ve gece hesapta düşecek değerler gece başlamadan yakalanır."""
from avukat_perf import params as pr
from yardimci import params_yukle


def _degistir(bolum, alan, deger):
    params = params_yukle()
    params[bolum][alan] = deger
    return params


def test_brans_kodlari_bilinen_branslarla_tutarli_olmali():
    assert pr.dogrula(_degistir("kriter1", "oto_branslar", ["TRAFİK", "KASKO"]))
    assert pr.dogrula(_degistir("kriter1", "oto_branslar", ["TRAFIK", "KAKSO"]))
    olgunluk = {"TRAFIK": 24, "KAKSO": 24, "DIGER": 36}
    assert pr.dogrula(_degistir("tahsilat", "olgunluk_ay", olgunluk))
    assert pr.dogrula(_degistir("tahsilat", "olgunluk_ay", {"KASKO": 24, "DIGER": 36})) == []


def test_kod_listesi_ogeleri_metin_ve_hareket_turu_listesi_bos_olamaz():
    assert pr.dogrula(_degistir("hazirlik", "sulh_degerleri", [3]))
    assert pr.dogrula(_degistir("hazirlik", "sulh_avukat_kodlari", [""]))
    assert pr.dogrula(_degistir("hazirlik", "tahsilat_hareket_turleri", []))
    assert pr.dogrula(_degistir("hazirlik", "tahsilat_hareket_turleri", ["TAHSILAT"])) == []
    bilinen = params_yukle()["kalite"]["bilinen_branslar"]
    assert pr.dogrula(_degistir("kalite", "bilinen_branslar", bilinen + [7])) == [
        "kalite: en_eski_tarih geçerli bir YYYY-AA-GG günü, bilinen_branslar boş olmayan metin "
        "listesi olmalı"]


def test_sulh_alani_atama_logunun_sozlesme_alani_olmali():
    hatalar = pr.dogrula(_degistir("hazirlik", "sulh_alani", "ATAMA_TIPI"))
    assert hatalar and "atama_ref, grup, tipi" in hatalar[0]
    assert pr.dogrula(_degistir("hazirlik", "sulh_alani", "avukat_kodu"))
    assert pr.dogrula(_degistir("hazirlik", "sulh_alani", "grup")) == []


def test_gecede_dusecek_parametreler_dogrulamada_yakalanir():
    assert pr.dogrula(_degistir("kalite", "en_eski_tarih", "1950-13-45"))
    assert pr.dogrula(_degistir("tahsilat", "enflasyon_duzeltme", True))
    params = params_yukle()
    params["_teyit_bekleyen"] = "kriter1"
    assert pr.dogrula(params) == ["_teyit_bekleyen liste olmalı"]


def test_iliski_yetim_orani_sinirlari():
    assert pr.dogrula(_degistir("kalite", "iliski_en_cok_yetim_orani", 1.0))
    assert pr.dogrula(_degistir("kalite", "iliski_en_cok_yetim_orani", -0.1))
    assert pr.dogrula(_degistir("kalite", "iliski_en_cok_yetim_orani", 0.0)) == []
