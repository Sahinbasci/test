"""Kaynaklar arası ilişki ve mutabakat: kısmi anahtar uyuşmazlığı, (dosya, avukat) çifti, avukat
listesi ve kesit ayındaki mutabakat farkı."""
import re

import pandas as pd

from avukat_perf import kalite_iliski, sema
from hat import okuma
from yardimci import params_yukle


def _tablo(kaynak_adi, satirlar):
    return pd.DataFrame(satirlar, columns=sema.alanlar(kaynak_adi))


def _durum(sonuclar, kontrol):
    tablo = pd.concat(sonuclar, ignore_index=True).set_index("kontrol")
    return tuple(tablo.loc[kontrol, ["durum", "deger"]])


def _dosyalar(adet):
    return pd.DataFrame({"dosya_no": ["D-{}".format(i) for i in range(adet)]})


def test_yetim_orani_esigi_asarsa_kaldi_altinda_uyari():
    ana = _dosyalar(10)
    alt = pd.DataFrame({"dosya_no": ["D-{}".format(i) for i in range(7)] + ["X1", "X2", "X3"],
                        "tutar": [10.0] * 10})
    assert kalite_iliski.iliski("HAREKET_DOSYA", ana, alt, "dosya_no", 0.05)["durum"][0] == "KALDI"
    assert kalite_iliski.iliski("HAREKET_DOSYA", ana, alt, "dosya_no", 0.5)["durum"][0] == "UYARI"
    # Tek yetim satır ama tutarın çoğu: tutarla tartılan oran eşiği aşar.
    tek = alt.assign(dosya_no=["D-1"] * 9 + ["X1"], tutar=[1.0] * 9 + [900.0])
    sonuc = kalite_iliski.iliski("HAREKET_DOSYA", ana, tek, "dosya_no", 0.10, "tutar")
    assert tuple(sonuc[["durum", "deger"]].iloc[0]) == ("KALDI", 1)
    # Sayıca 1/10 = 0,10 eşiği aşmaz (sınır dahil): tartılmadan yalnız uyarı.
    assert kalite_iliski.iliski("HAREKET_DOSYA", ana, tek, "dosya_no", 0.10)["durum"][0] == \
        "UYARI"


def test_gecelik_iliski_parametredeki_orani_kullanir():
    params = params_yukle()
    dosya = _tablo("dosya", [("D-{}".format(i), "TRAFIK", "R06", 1.0, None, "2025-01-01")
                             for i in range(10)])
    hareket = _tablo("tahsilat_hareketi", [("D-{}".format(i), "2026-10-01", 5.0, None, None)
                                          for i in range(8)] + [
        ("D000008", "2026-10-01", 5.0, None, None), ("D000009", "2026-10-01", 5.0, None, None)])
    tablolar = {"dosya": dosya, "tahsilat_hareketi": hareket}
    assert _durum(okuma.iliskiler(tablolar, params), "HAREKET_DOSYA") == ("KALDI", 2)
    params["kalite"]["iliski_en_cok_yetim_orani"] = 0.5
    assert _durum(okuma.iliskiler(tablolar, params), "HAREKET_DOSYA") == ("UYARI", 2)
    # Sayıca 1/10 (sınırda) ama tutarın çoğu eşleşmiyor: gecede tutarla tartılır, durur.
    params["kalite"]["iliski_en_cok_yetim_orani"] = 0.1
    tablolar["tahsilat_hareketi"] = _tablo("tahsilat_hareketi", [
        ("D-{}".format(i), "2026-10-01", 1.0, None, None) for i in range(9)] + [
        ("D000009", "2026-10-01", 900.0, None, None)])
    assert _durum(okuma.iliskiler(tablolar, params), "HAREKET_DOSYA") == ("KALDI", 1)


def test_bekleme_dosya_avukat_cifti_ve_avukat_listesi_denetlenir():
    params = params_yukle()
    log = _tablo("atama_log", [("D-1", "AV-01", "2026-01-01", None, None, None, None),
                               ("D-2", "AV-02", "2026-01-01", None, None, None, None)])
    bekleme = _tablo("bekleme", [("D-1", "AV-02", "2026-02-01", "2026-02-10")])
    avukat = _tablo("avukat", [("av-01", None, None), ("av-02", None, None)])
    tablolar = {"atama_log": log, "bekleme": bekleme, "avukat": avukat,
                "dosya": pd.DataFrame({"dosya_no": ["D-1", "D-2"]})}
    sonuc = okuma.iliskiler(tablolar, params)
    assert _durum(sonuc, "BEKLEME_ATAMA") == ("KALDI", 1)  # tek satır, hiçbiri eşleşmiyor
    assert _durum(sonuc, "BEKLEME_DOSYA")[0] == "GECTI"
    assert _durum(sonuc, "AVUKAT_AVUKAT") == ("KALDI", 2)
    tablolar["bekleme"] = _tablo("bekleme", [("D-1", "AV-02", "2026-02-01", None),
                                             ("D-1", "AV-01", "2026-02-01", None)])
    tablolar["avukat"] = _tablo("avukat", [("AV-01", None, None), ("AV-99", None, None)])
    sonuc = okuma.iliskiler(tablolar, params)
    # Bekleme ve avukat listesi oranla durmaz: yanlış çift görünür olur, gece sürer.
    assert _durum(sonuc, "BEKLEME_ATAMA") == ("UYARI", 1)
    assert _durum(sonuc, "AVUKAT_AVUKAT") == ("UYARI", 1)


def test_mutabakatta_kesit_ayi_uyari_onceki_aylar_kaldi():
    params = params_yukle()
    hareket = _tablo("tahsilat_hareketi", [("D-1", "2026-10-05", 100000.0, None, None),
                                          ("D-1", "2026-11-05", 101000.0, None, None)])
    hareket["hareket_tarihi"] = pd.to_datetime(hareket["hareket_tarihi"])
    rapor = pd.DataFrame({"avukat_kodu": ["AV-1", "AV-1"], "donem": ["2026-10", "2026-11"],
                          "tahsilat_toplami": [99000.0, 100000.0], "brans": [None, None]})
    sonuc = kalite_iliski.mutabakat(hareket, rapor, params, "2026-11-19").set_index("kontrol")
    assert sonuc.loc["TAHSILAT:2026-11", "durum"] == "UYARI"
    assert sonuc.loc["TAHSILAT:2026-10", "durum"] == "KALDI"



def test_mutabakat_aciklamasi_tutar_icermez():
    """Kalite sonucu ve izleme panosu şirketten paylaşılabilir: açıklamada aylık tahsilat
    toplamı yazılmaz, göreli fark deger sütunundadır."""
    hareket = _tablo("tahsilat_hareketi", [("D-1", "2026-10-05", 101000.0, None, None)])
    hareket["hareket_tarihi"] = pd.to_datetime(hareket["hareket_tarihi"])
    rapor = pd.DataFrame({"avukat_kodu": ["AV-1"], "donem": ["2026-10"],
                          "tahsilat_toplami": [100000.0], "brans": [None]})
    sonuc = kalite_iliski.mutabakat(hareket, rapor, params_yukle(), "2026-11-19")
    assert not [metin for metin in sonuc["aciklama"] if re.search(r"\d", metin)]
    assert sonuc["deger"].iloc[0] == 0.01
