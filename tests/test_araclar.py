"""Yerel araçlar: yerel çalıştırıcı yalnız kendi çalışma klasörünü siler."""
import os
import shutil
import tempfile

from araclar import yerel_calistir
from yardimci import hata_bekle


def test_yerel_calistirici_yabanci_klasoru_silmez():
    kok = tempfile.mkdtemp()
    try:
        yabanci = os.path.join(kok, "yabanci")
        os.makedirs(os.path.join(yabanci, "tablolar"))
        with open(os.path.join(yabanci, "onemli.txt"), "w", encoding="utf-8") as dosya:
            dosya.write("silinmemeli")
        assert hata_bekle(SystemExit, yerel_calistir._sifirla, yabanci)
        assert os.path.exists(os.path.join(yabanci, "onemli.txt"))
        calisma = os.path.join(kok, "calisma")
        for alt in ("tablolar", "ham"):
            os.makedirs(os.path.join(calisma, alt))
        open(os.path.join(calisma, ".DS_Store"), "w").close()  # macOS
        yerel_calistir._sifirla(calisma)
        assert not os.path.exists(calisma)
        yerel_calistir._sifirla(os.path.join(kok, "olmayan"))  # yoksa hata vermez
    finally:
        shutil.rmtree(kok)


def test_mutasyon_listesi_guncel_kodla_eslesir():
    # Her mutasyonun eski metni modülde tam bir kez geçer, adlar tekrarsızdır: kod taşınınca
    # eskiyen kayıt (METİN BULUNAMADI) o kuralın fiilen sınanmadığı anlamına gelirdi.
    import json
    from yardimci import KOK
    with open(os.path.join(KOK, "araclar", "mutasyonlar.json"), encoding="utf-8") as dosya:
        liste = json.load(dosya)
    adlar = [kayit[0] for kayit in liste]
    assert len(set(adlar)) == len(adlar)
    for ad, modul, eski, yeni in liste:
        with open(os.path.join(KOK, "dataiku", "kutuphane", modul), encoding="utf-8") as dosya:
            metin = dosya.read()
        assert metin.count(eski) == 1 and eski != yeni, ad


def test_yerel_calistirici_senaryo_adini_klasoru_silmeden_dogrular():
    """Yazım hatalı senaryo adı önizleme verisini silmeden hata verir."""
    kok = tempfile.mkdtemp()
    try:
        calisma = os.path.join(kok, "calisma")
        for alt in ("ham", "tablolar"):
            os.makedirs(os.path.join(calisma, alt))
        assert hata_bekle(ValueError, yerel_calistir.calistir, calisma, False, "tamm")
        assert os.path.isdir(os.path.join(calisma, "tablolar"))
    finally:
        shutil.rmtree(kok)


def test_mutasyon_araci_yazim_kurallarini_sayar_zaman_asimini_sorunlu_sayar():
    """Yalnız satır ve modül uzunluğu testleri dışarıda kalır (3.7 söz dizimi mutasyonla da
    sınanır); test koşusu zaman sınırını aşan mutasyon kilitlemez, sorunlu sayılır."""
    import subprocess
    from araclar import mutasyon
    assert all("::" in test for test in mutasyon.SAYILMAYAN)
    asil = subprocess.run

    def bekleyen(*argumanlar, **secenekler):
        """Hiç bitmeyen test koşusu: zaman sınırı verilmişse onu aşar; verilmemişse araç sonsuza
        dek beklerdi (burada "geçti" döner, test düşer)."""
        if secenekler.get("timeout") is None:
            return subprocess.CompletedProcess(argumanlar, 0)
        raise subprocess.TimeoutExpired("pytest", secenekler["timeout"])
    try:
        subprocess.run = bekleyen
        assert mutasyon._dene(None, None, None) == mutasyon.ZAMAN_ASIMI
    finally:
        subprocess.run = asil
    assert mutasyon.ETIKETLER[mutasyon.ZAMAN_ASIMI] == "ZAMAN AŞIMI"
