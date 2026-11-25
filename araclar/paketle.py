"""Kurulum klasörünün yapıştırma paketlerini üretir (kurulum/adim_*.py).

Depo indirilmeden, GitHub'dan kopyala-yapıştırla kurulum içindir. Her kütüphane paketi
(avukat_perf, hat, arayuz) tek bir not defteri hücresine sığan bir dosyaya gömülür; çalışınca
dosyaları Dataiku proje kütüphanesine yazar ve geri okuyarak özetini doğrular. Ayar paketi
params.json ve kaynaklar.json'u (provada ek dosyaları ve sentetik veriyi de) yönetilen klasörlere
yazar. Kontrol not defterleri (dataiku/kontrol) kurulum klasörüne birebir kopyalanır.
Paketler elle değiştirilmez; kod değişince yeniden üretilir (tests/test_kurulum.py eskimeyi
yakalar).
Kullanım: python araclar/paketle.py          (kurulum/ klasörünü yazar)
"""
import os
import shutil
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUTUPHANE = os.path.join(KOK, "dataiku", "kutuphane")
HEDEF = os.path.join(KOK, "kurulum")
PAKETLER = ("avukat_perf", "hat", "arayuz")
KOPYALAR = {"adim_03_veri_kumeleri.py": ("dataiku", "kontrol", "kurulum.py"),
            "adim_05_aktarim_kontrolu.py": ("dataiku", "kontrol", "aktarim_kontrol.py")}
if KUTUPHANE not in sys.path:
    sys.path.insert(0, KUTUPHANE)
from avukat_perf.surum import metin_ozeti  # noqa: E402  (aktarım özetiyle aynı kural)

KUTUPHANE_YAZICI = '''

# ---------- kütüphaneye yazma ----------
def _ozet(metin):
    satirlar = [satir.rstrip() for satir in metin.splitlines()]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return hashlib.sha256("\\n".join(satirlar).encode("utf-8")).hexdigest()[:12]


def _cocuk(klasor, ad):
    if hasattr(klasor, "get_child"):
        return klasor.get_child(ad)
    return next((oge for oge in klasor.list() if oge.name == ad), None)


def _python_klasoru(kutuphane):
    for yol in ("/python", "python"):
        try:
            klasor = kutuphane.get_folder(yol)
        except Exception:  # sürüme göre yol biçimi değişir
            klasor = None
        if klasor is not None:
            return klasor
    raise SystemExit("Kütüphanede python klasörü bulunamadı; kurulum rehberindeki elle yapıştırma "
                     "yolunu izleyin.")


def kur():
    proje = dataiku.api_client().get_default_project()
    if not hasattr(proje, "get_library"):
        raise SystemExit("Bu Dataiku sürümünde kütüphane API'si yok; kurulum rehberindeki Git "
                         "ya da elle yapıştırma yolunu izleyin.")
    python = _python_klasoru(proje.get_library())
    klasor = _cocuk(python, PAKET) or python.add_folder(PAKET)
    hatali = []
    for ad in sorted(DOSYALAR):
        dosya = _cocuk(klasor, ad) or klasor.add_file(ad)
        dosya.write(DOSYALAR[ad])
        okunan = dosya.read()
        okunan = okunan.decode("utf-8") if isinstance(okunan, bytes) else okunan
        print("{}/{} {}".format(PAKET, ad, _ozet(okunan)))
        if _ozet(okunan) != OZET[ad]:
            hatali.append(ad)
    if hatali:
        raise SystemExit("Geri okunan içerik farklı: " + ", ".join(hatali))
    print("{}: {} dosya yazıldı ve doğrulandı. Not defterinin çekirdeğini yeniden başlatın."
          .format(PAKET, len(DOSYALAR)))


kur()
'''

AYAR_YAZICI = '''

# ---------- yükleme ----------
def _yukle(klasor_adi, yol, veri):
    dataiku.Folder(klasor_adi).upload_data(yol, veri)
    print("{}: {} ({} bayt)".format(klasor_adi, yol, len(veri)))


def ayarlari_yukle():
    dosyalar = dict(AYARLAR, **(PROVA_AYARLARI if PROVA else {}))
    for ad in sorted(dosyalar):
        json.loads(dosyalar[ad])  # bozuk yapıştırma burada durur
        _yukle("ayarlar", ad, dosyalar[ad].encode("utf-8"))


def sentetik_veriyi_yukle():
    gecici = tempfile.mkdtemp()
    try:
        for ad, sayi in sorted(uret(gecici).items()):
            with open(os.path.join(gecici, ad + ".csv"), "rb") as dosya:
                _yukle("kaynak_dosyalari", "sentetik/veri/" + ad + ".csv", dosya.read())
    finally:
        shutil.rmtree(gecici)


ayarlari_yukle()
if PROVA:
    sentetik_veriyi_yukle()
print("Ayarlar yüklendi{}. Şimdi adim_03_veri_kumeleri.py 4. hücresini yeniden çalıştırın."
      .format(" ve sentetik veri yazıldı" if PROVA else ""))
'''


def _oku(*parcalar):
    with open(os.path.join(KOK, *parcalar), encoding="utf-8") as dosya:
        return dosya.read()


def _ham(metin, ad):
    """İçerik ham üç tırnaklı metin olarak (okunur kalsın); olmazsa kaçışlı metin."""
    if "'''" in metin or metin.endswith(("\\", "'")) or "\r" in metin:
        return repr(metin)
    return "r'''" + metin + "'''"


def kutuphane_paketi(paket):
    klasor = os.path.join(KUTUPHANE, paket)
    adlar = sorted(ad for ad in os.listdir(klasor) if ad.endswith(".py"))
    metinler = {ad: _oku("dataiku", "kutuphane", paket, ad) for ad in adlar}
    bas = ('"""Kurulum adım 2: kütüphane paketi {p} ({n} dosya).\n\n'
           "araclar/paketle.py üretir; elle değiştirmeyin. Dataiku'da projenin bir Python not\n"
           "defterine bu dosyanın tamamını yapıştırıp çalıştırın: dosyalar proje kütüphanesine\n"
           "(Kod > Kütüphaneler > python/{p}) yazılır, aynı adlı dosyanın üzerine yazılır ve geri\n"
           "okunarak doğrulanır. Sonda \"{p}: {n} dosya yazıldı ve doğrulandı\" görünmelidir.\n"
           '"""\nimport hashlib\n\nimport dataiku\n\nPAKET = "{p}"\nDOSYALAR = {{}}\n\n'
           ).format(p=paket, n=len(adlar))
    govde = "".join('DOSYALAR["{}"] = {}\n\n'.format(ad, _ham(metinler[ad], ad)) for ad in adlar)
    ozet = "OZET = {\n" + "".join('    "{}": "{}",\n'.format(ad, metin_ozeti(metinler[ad]))
                                  for ad in adlar) + "}\n"
    return bas + govde + ozet + KUTUPHANE_YAZICI


def ayar_paketi():
    uretici = _oku("sentetik", "uretici.py")
    uretici = uretici[:uretici.index('\nif __name__ == "__main__":')].rstrip() + "\n"
    satirlar = ['"""Kurulum adım 4: ayar dosyaları ve sentetik prova verisi.\n\n'
                "araclar/paketle.py üretir; elle değiştirmeyin. Dataiku'da projenin bir Python\n"
                "not defterine bu dosyanın tamamını yapıştırıp çalıştırın. params.json ve\n"
                "kaynaklar.json \"ayarlar\" klasörüne yazılır. PROVA True iken prova ek dosyaları\n"
                "da yazılır, sentetik veri üretilip \"kaynak_dosyalari\" klasörüne\n"
                "(sentetik/veri/) yüklenir. Canlı projede PROVA = False yapın.\n"
                '"""\nimport json\nimport shutil\nimport tempfile\n\nimport dataiku\n\n'
                "PROVA = True  # canlı projede False\n\nAYARLAR = {}\n"]
    for ad in ("params.json", "kaynaklar.json"):
        metin = _oku("dataiku", "degiskenler", ad)
        satirlar.append('AYARLAR["{}"] = {}\n'.format(ad, _ham(metin, ad)))
    satirlar.append("\nPROVA_AYARLARI = {}\n")
    for ad in ("params_ek.json", "kaynaklar_ek.json"):
        satirlar.append('PROVA_AYARLARI["{}"] = {}\n'.format(ad, _ham(_oku("sentetik", ad), ad)))
    satirlar.append("\n\n# ---------- sentetik veri üreticisi (sentetik/uretici.py) ----------\n")
    return "".join(satirlar) + uretici + AYAR_YAZICI


def uretilecekler():
    """{dosya adı: içerik} kurulum klasöründe üretilen dosyalar."""
    sonuc = {"adim_02_kutuphane_{}.py".format(paket): kutuphane_paketi(paket)
             for paket in PAKETLER}
    sonuc["adim_04_ayarlar_ve_sentetik_veri.py"] = ayar_paketi()
    sonuc.update({ad: _oku(*kaynak) for ad, kaynak in KOPYALAR.items()})
    return sonuc


def yaz(hedef=HEDEF):
    os.makedirs(hedef, exist_ok=True)
    for ad, metin in uretilecekler().items():
        with open(os.path.join(hedef, ad), "w", encoding="utf-8", newline="\n") as dosya:
            dosya.write(metin)
        print("{:<40} {:>8} bayt".format(ad, len(metin.encode("utf-8"))))


if __name__ == "__main__":
    yaz()
    shutil.rmtree(os.path.join(KOK, "kurulum", "__pycache__"), ignore_errors=True)
