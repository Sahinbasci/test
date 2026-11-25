"""Veri sözleşmesinin (avukat_perf/sema.py) kalite kapısına yansıyan kuralları ve aylık tahsilat
tablosunun penceresi (bu kurallar mutasyonla bozulunca hiçbir test düşmüyordu)."""
import pandas as pd

from arayuz import sunum_tahsilat
from avukat_perf import kalite, sema
from yardimci import params_yukle


def _kaldi(sonuc):
    return sorted(sonuc.loc[sonuc["durum"] == "KALDI", "kontrol"])


def test_ayni_zamanli_iki_atama_kaydi_referansla_ayrilir():
    """Aynı saniyede iptal edilip yeniden girilen kayıt atama referansıyla ayrılır; anahtarda
    referans olmasaydı gece her gün YINELENEN ile dururdu."""
    log = pd.DataFrame({"dosya_no": ["D-001", "D-001"], "avukat_kodu": ["AV-01", "AV-01"],
                        "atama_tarihi": ["2026-10-01 10:00:00", "2026-10-01 10:00:00"],
                        "iptal_tarihi": ["2026-10-01 10:00:00", None], "atama_ref": ["R1", "R2"],
                        "grup": [None, None], "tipi": [None, None]})
    _, sonuc = kalite.denetle("atama_log", log, "2026-11-19", params_yukle())
    assert kalite.karar(sonuc) == "GECTI", _kaldi(sonuc)


def test_ilk_gecede_bos_takip_goruntusu_geceyi_durdurur():
    """Takip bilgisi gözlem kaynağıdır: ilk gecenin boş görüntüsü de KALDI (geçseydi ertesi gece
    bütün esaslar o gün ilk görülürdü)."""
    assert sema.KAYNAKLAR["takip"].get("gozlem") is True
    bos = pd.DataFrame({ad: pd.Series([], dtype=object) for ad in sema.alanlar("takip")})
    _, sonuc = kalite.denetle("takip", bos, "2026-11-19", params_yukle(), None)
    assert "BOS_TABLO" in _kaldi(sonuc)


def test_tahsilat_girdilerinin_zorunlu_alanlari():
    """Tahsilat puanının dayandığı alanlar zorunludur; boş rücu tutarı kapıda durur (hesapta
    HESAP_HATASI yerine)."""
    zorunlu = {kaynak: {ad for ad, _, z in sema.KAYNAKLAR[kaynak]["alanlar"] if z}
               for kaynak in ("dosya", "tahsilat_hareketi", "atama_log")}
    assert zorunlu == {
        "dosya": {"dosya_no", "brans", "rucu_kodu", "rucu_tutari", "rucuya_verilis_tarihi"},
        "tahsilat_hareketi": {"dosya_no", "hareket_tarihi", "tutar"},
        "atama_log": {"dosya_no", "avukat_kodu", "atama_tarihi"}}
    dosya = pd.DataFrame({"dosya_no": ["D-001", "D-002"], "brans": ["TRAFIK", "TRAFIK"],
                          "rucu_kodu": ["R11", "R11"], "rucu_tutari": [1000.0, None],
                          "acik_bakiye": [10.0, 10.0],
                          "rucuya_verilis_tarihi": ["2024-01-05", "2024-01-05"]})
    _, sonuc = kalite.denetle("dosya", dosya, "2026-11-19", params_yukle())
    assert any(kontrol.endswith("rucu_tutari") for kontrol in _kaldi(sonuc)), _kaldi(sonuc)


def test_aylik_tahsilat_tablosu_izgaranin_son_aylarini_gosterir():
    """Hesap anındaki 24 aylık ızgaranın son 12 ayı gösterilir, kesit ayı kısmi işaretlidir
    (dilim ters olsaydı en eski 12 ay görünürdü)."""
    aylik = pd.DataFrame({"avukat_kodu": ["AV-01", "AV-01"], "ay": ["2025-01", "2026-11"],
                          "tutar": [100.0, 50.0], "ilk_ay": "2024-12", "son_ay": "2026-11",
                          "son_ay_kismi": True})
    satirlar = sunum_tahsilat.aylik_tablo(aylik)
    aylar = [satir["ay"] for satir in satirlar]
    beklenen = [str(ay) for ay in pd.period_range("2025-12", "2026-11", freq="M")]
    assert aylar == beklenen
    assert [satir["ay"] for satir in satirlar if satir["kismi"]] == ["2026-11"]
    assert sum(satir["tutar"] for satir in satirlar) == 50.0
