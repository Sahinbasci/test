"""surum modülünün testleri."""
import os
import shutil
import subprocess
import sys
import tempfile

from avukat_perf import SURUM
from avukat_perf import surum
from yardimci import KUTUPHANE, params_yukle


def _degistir(bolum, alan, deger):
    params = params_yukle()
    params[bolum][alan] = deger
    return params


def test_kural_surumu_icerige_baglidir():
    temel = surum.kural_surumu(params_yukle())
    assert surum.kural_surumu(params_yukle()) == temel
    assert surum.kural_surumu(_degistir("kriter2", "dusum_ay", 4)) != temel
    degisik = _degistir("kriter1", "sonlanan_atamada_dusum_korunur", False)
    assert surum.kural_surumu(degisik) != temel
    assert surum.kural_surumu(_degistir("tahsilat", "tutar_bantlari", [10000])) != temel


def test_kural_surumu_aciklama_ve_siradan_etkilenmez():
    temel = surum.kural_surumu(params_yukle())
    assert surum.kural_surumu(_degistir("kriter2", "_not", "başka bir açıklama")) == temel
    ters = dict(reversed(list(params_yukle().items())))
    assert surum.kural_surumu(ters) == temel


def test_hesap_surumu_kitaplik_kod_ve_parametreyi_tasir():
    params = params_yukle()
    kod = surum.kod_ozeti()
    assert surum.hesap_surumu(params) == "{}+{}+{}".format(SURUM, kod, surum.kural_surumu(params))
    assert len(kod) == 8 and kod == surum.kod_ozeti()


def test_kod_ozeti_satir_sonu_ve_sondaki_bosluktan_etkilenmez():
    # Kopyala-yapıştır aktarımında CRLF ve satır sonu boşluğu sürümü değiştirmez.
    assert surum.metin_ozeti("a = 1\nb = 2\n") == surum.metin_ozeti("a = 1  \r\nb = 2\r\n\n")
    assert surum.metin_ozeti("a = 1\n") != surum.metin_ozeti("a = 2\n")


def test_hazirlik_surumu_yalniz_hazirlik_kurallarina_bagli():
    temel = surum.hazirlik_surumu(params_yukle())
    assert surum.hazirlik_surumu(_degistir("kriter2", "dusum_ay", 4)) == temel
    assert surum.hazirlik_surumu(_degistir("hazirlik", "sulh_avukat_kodlari", ["AV-9"])) != temel
    assert surum.hazirlik_surumu(_degistir("kriter2", "rucu_kodu", "R12")) != temel
    # Koşul gözlemi kapanış kodlarından da kurulur (model tablosu gozlem_kosul).
    assert surum.hazirlik_surumu(_degistir("kriter2", "kapanis_kodlari", ["R06"])) != temel


def test_hat_modullerinin_her_biri_kod_ozetinde_ya_da_giris_cikis_listesinde():
    """Sonucu belirleyen hat modülü (gölge aralıkları, normalleştirme, dönem yayını) kod
    özetine girer; geri kalanı açıkça yalnız giriş-çıkış listesindedir."""
    hat = dict(surum.KOD_DOSYALARI)["hat"]
    adlar = {ad for ad in os.listdir(os.path.join(KUTUPHANE, "hat")) if ad.endswith(".py")}
    assert not set(hat) & set(surum.HAT_GIRIS_CIKIS)
    assert set(hat) | set(surum.HAT_GIRIS_CIKIS) == adlar
    for ad in ("gecmis.py", "kaynak.py", "donem_akisi.py", "hesap.py", "model.py", "okuma.py"):
        assert ad in hat


def _kopyada_kod_ozeti(degisecek):
    """Kütüphane kopyasında bir dosyanın sonuna satır eklenince yeni süreçteki kod özeti."""
    kok = tempfile.mkdtemp()
    try:
        hedef = os.path.join(kok, "kutuphane")
        shutil.copytree(KUTUPHANE, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        if degisecek:
            with open(os.path.join(hedef, degisecek), "a", encoding="utf-8") as dosya:
                dosya.write("DENEME = 1\n")
        komut = "from avukat_perf import surum; print(surum.kod_ozeti())"
        return subprocess.check_output([sys.executable, "-B", "-c", komut], cwd=hedef).strip()
    finally:
        shutil.rmtree(kok)


def test_sonucu_belirleyen_hat_dosyasi_degisince_kod_ozeti_degisir():
    taban = _kopyada_kod_ozeti(None)
    for ad in ("hat/gecmis.py", "hat/donem_akisi.py", "hat/kaynak.py", "hat/model.py"):
        assert _kopyada_kod_ozeti(ad) != taban, ad
    assert _kopyada_kod_ozeti("hat/arsiv.py") == taban  # yalnız giriş-çıkış


def test_kalite_kapisi_esigi_hesap_surumunu_degistirmez():
    """kalite.* hiçbir puana girmez; meşru sıçramada bir gece için satir_sapma_orani
    yükseltilince "Kurallar değişti" görünmez, dönem tekrarı düzeltme sürümü açmaz."""
    temel = surum.kural_surumu(params_yukle())
    assert surum.kural_surumu(_degistir("kalite", "satir_sapma_orani", 3.0)) == temel
    assert surum.kural_surumu(_degistir("kalite", "iliski_en_cok_yetim_orani", 0.5)) == temel
    assert surum.kural_surumu(_degistir("kriter1", "uyari_gun", 9)) != temel
