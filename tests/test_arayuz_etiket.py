"""Ekran etiketlerinin kapsaması: arka ucun üretebildiği her kodun JS sözlüğünde bir etiketi var.

Etiketler JS'te tutulur (kod ekranda Türkçe adıyla görünür). Arka uca yeni bir kod eklenip
etiketi unutulursa ekranda ham kod (ör. ESAS_TARIHI_BILINMIYOR) görünürdü; bu test kırılır.
Kodlar hem sentetik provanın sonuç tablolarından hem parametre ve kitaplık sabitlerinden alınır.
Branş, alt başlık ve mevcut alan adları parametrededir (gorunum; kodlar parametreyle değişir).
"""
import os
import re
import shutil

from avukat_perf import aciklama, bayrak, kriter2, sema
from avukat_perf.params_sema import SUTUNLAR
from hat import akis, donem_akisi
from yardimci import KOK, prova_ortami

JS = os.path.join(KOK, "dataiku", "webapp", "uygulama.js")


def _sozluk(ad):
    """uygulama.js içindeki `var AD = { ... };` sözlüğünün anahtarları."""
    with open(JS, encoding="utf-8") as dosya:
        metin = dosya.read()
    eslesme = re.search(r"var " + ad + r" = \{(.*?)\};", metin, re.S)
    assert eslesme, ad
    return set(re.findall(r'(?:^|[{,\s])"?([A-Za-z0-9_+\-]+)"?\s*:', eslesme.group(1)))


def _sozluk_degerleri(ad):
    """uygulama.js içindeki `var AD = { anahtar: "değer", ... };` sözlüğü."""
    with open(JS, encoding="utf-8") as dosya:
        metin = dosya.read()
    govde = re.search(r"var " + ad + r" = \{(.*?)\};", metin, re.S).group(1)
    return dict(re.findall(r'"?([A-Za-z0-9_+\-]+)"?\s*:\s*"([^"]*)"', govde))


def _gorunum(params, alan):
    """params.json gorunum bölümündeki ad tablosunun kodları (branşta [kod, ad] listesi)."""
    adlar = params["gorunum"][alan]
    return {kod for kod, _ in adlar} if isinstance(adlar, list) else set(adlar)


def _degerler(tablo, sutun):
    if tablo is None or sutun not in tablo.columns:
        return set()
    return {str(deger) for deger in tablo[sutun].dropna().unique()}


def test_kitaplik_sabitlerinin_etiketi_var():
    from yardimci import params_yukle
    params = params_yukle()
    assert set(bayrak.BAYRAKLAR) | {"IZLENIYOR", "KAPANDI", "SONLANDI", "KOSUL_DISI",
                                     "KAPSAM_DISI"} <= _sozluk("SEVIYE")
    assert set(kriter2.SURECLER) <= _sozluk("SUREC")
    kodlar = {kod for liste in params["kalite_davranis"]["alt_basliklar"].values() for kod in liste}
    assert kodlar <= _gorunum(params, "alt_baslik_adlari")
    mevcut = set(params["kalite_davranis"]["mevcut_alanlar"])
    assert mevcut <= _gorunum(params, "mevcut_alan_adlari")
    assert set(params["kalite"]["bilinen_branslar"]) <= _gorunum(params, "brans_adlari")
    with open(os.path.join(KOK, "dataiku", "webapp", "stil.css"), encoding="utf-8") as dosya:
        css = dosya.read()
    # Branş rengi listedeki sırayla paletten: her bilinen branşın kendi rengi var.
    with open(JS, encoding="utf-8") as dosya:
        palet = int(re.search(r"var BRANS_PALET_BOYU = (\d+);", dosya.read()).group(1))
    assert len(params["gorunum"]["brans_adlari"]) <= palet
    assert all("--brans-{}:".format(sira) in css for sira in range(1, palet + 1))
    assert all(".agirlik-seridi .sutun-" + ad + " {" in css for ad in SUTUNLAR)
    assert set(SUTUNLAR) | {"birlesik"} <= _sozluk("SUTUN") & _sozluk("SUTUN_KISA")
    # Açıklama metnindeki sütun adı ekrandaki adla aynı (kartta aynı sütun iki adla görünmez).
    ekran = _sozluk_degerleri("SUTUN")
    assert {ad: ekran[ad] for ad in SUTUNLAR} == aciklama.ETIKET
    assert set(sema.KAYNAKLAR) <= _sozluk("KAYNAK_ACIKLAMA")
    # Puan üretilmeme nedenleri (tahsilat ve süre); prova hepsini üretmeyebilir.
    assert set(aciklama.NEDEN) <= _sozluk("EKSIK_NEDEN")
    assert {not_adi for not_adi, _ in params["notlar"]} <= _sozluk("NOT_SINIFI")


DENETIM_KODU = (  # kalite_sonucu'na kontrol adı yazan biçimler
    r'(?<!calisma\.)satir\(\s*[^,()]+,\s*"([A-Z][A-Z_]+)',
    r'_kontrol\([^,]+,\s*"([A-Z][A-Z_]+)',
    r'\(\s*"(?:donem|sonuc)",\s*"([A-Z][A-Z_]+)"',
    r'\(\s*"([A-Z][A-Z_]+)(?::"|")\s*(?:\+\s*\w+\s*)?,\s*\w+\(',
    r'\(\s*"([A-Z][A-Z_]+)",\s*"[a-z_]+",\s*"[a-z_]+"')


def test_kalite_sonucu_denetim_kodlarinin_etiketi_var():
    """Kapı, ilişki, mutabakat ve dönem denetimlerinin kodu Veri Durumu'nda Türkçe adıyla
    görünür (SAATSIZ_ATAMA, TAHSILAT_HAREKETI_YOK, MODEL_TABLOSU ve dönem
    sonunun HESAP_HATASI satırı ham kodla görünüyordu)."""
    kok = os.path.join(KOK, "dataiku", "kutuphane")
    dosyalar = [os.path.join("avukat_perf", ad) for ad in os.listdir(os.path.join(
        kok, "avukat_perf")) if ad.startswith("kalite") and ad.endswith(".py")]
    dosyalar += [os.path.join("avukat_perf", "donem.py"), os.path.join("hat", "okuma.py"),
                 os.path.join("hat", "donem_kayit.py")]
    kodlar = set()
    for yol in dosyalar:
        with open(os.path.join(kok, yol), encoding="utf-8") as dosya:
            metin = dosya.read()
        for kalip in DENETIM_KODU:
            kodlar |= set(re.findall(kalip, metin))
    # Tarayıcı gerçekten kodları buluyor (boş küme testi anlamsız kılardı).
    assert {"BOS_TABLO", "ATAMA_DOSYA", "VERI_KAPSAMI", "SAATSIZ_ATAMA", "MODEL_TABLOSU",
            "TAHSILAT_HAREKETI_YOK", "HESAP_HATASI", "TERS_TARIH"} <= kodlar
    eksik = kodlar - _sozluk("DENETIM")
    assert not eksik, sorted(eksik)


def test_sentetik_sonuclardaki_kodlarin_etiketi_var():
    ortam, ayarlar, params, kok = prova_ortami(600, 12)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")
        oku = ortam.tablo_oku
        k1, k2 = oku("sonuc_k1"), oku("sonuc_k2")
        beklenen = {
            "SEVIYE": _degerler(k1, "seviye") | _degerler(k2, "seviye"),
            "KAPSAM_DISI": _degerler(k1, "kapsam_disi_nedeni") | _degerler(
                k2, "kapsam_disi_nedeni"),
            "BITIS": _degerler(k1, "bitis_nedeni") | _degerler(k2, "bitis_nedeni"),
            "DUSUM_DURUMU": _degerler(k1, "dusum_durumu") | _degerler(k2, "dusum_durumu"),
            "DURUM": _degerler(oku("sonuc_puan_guncel"), "durum"),
            "EKSIK_NEDEN": _degerler(oku("sonuc_tahsilat_avukat"), "eksik_nedeni") | _degerler(
                oku("sonuc_sure"), "eksik_nedeni"),
            "DENETIM": {str(k).split(":")[0] for k in oku("kalite_sonucu")["kontrol"].dropna()},
            "CALISMA": _degerler(oku("model_avukat"), "calisma_durumu"),
            "CALISMA_TURU": _degerler(oku("calisma_kaydi"), "tur"),
            "KURAL_ADI": _degerler(k1, "esik_kurali") | {"TUMU"},
        }
        assert _degerler(oku("sonuc_portfoy"), "brans") <= _gorunum(params, "brans_adlari")
        assert _degerler(oku("sonuc_kalite_davranis_alt"), "alt_baslik") <= _gorunum(
            params, "alt_baslik_adlari")
        for sozluk, kodlar in beklenen.items():
            # prova bu kodu gerçekten üretti (puan üretilmeme nedeni üretmeyebilir; sabitlerden
            # ayrıca denetlenir)
            assert kodlar or sozluk == "EKSIK_NEDEN", sozluk
            eksik = kodlar - _sozluk(sozluk)
            assert not eksik, (sozluk, sorted(eksik))
    finally:
        shutil.rmtree(kok)
