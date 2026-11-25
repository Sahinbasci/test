"""Aktarım kontrolü: kod Dataiku'ya kopyalandıktan sonra bir Python not defterinde çalıştırılır.

Hücreler "# %%" satırlarıyla ayrılır; her hücreyi sırayla ayrı not defteri hücresine yapıştırıp
çalıştırın. Sonuç veri kümelerine yazılmaz; yalnız iki kontrol tablosuna ve ham_arsiv
klasörünün kontrol/ yoluna küçük bir deneme yazılır.
1. Kod özeti: kütüphane dosyaları, web uygulamasının dört sekmesi ve iki senaryo adımı;
   depo kökündeki aktarim_ozeti.txt ile satır satır aynı olmalı. Fark varsa o dosya eksik ya
   da hatalı yapıştırılmıştır; özette olmayan fazla satır, depodan kaldırılmış ve Dataiku'dan
   da silinmesi gereken dosyadır. Web uygulaması ve senaryo Dataiku API'siyle okunur; bu
   sürümde okunamazsa satır "OKUNAMADI" der, sekmeler elle karşılaştırılır. Not defterlerinin
   (kontrol/) satırı burada yazılmaz; GitHub farkından izlenir.
2. Ayarlar: ayarlar klasöründeki varsayılan params.json ve kaynaklar.json'un özeti (ek dosyalar
   hariç; aktarim_ozeti.txt'deki degiskenler/ satırlarıyla aynı olmalı); params ve kaynaklar
   (varsayılan + ek dosya) doğrulanır; etkin ek dosyalar yazılır. Hesap sürümü yerel çıktıyla
   aynı olmalı (şirket ekinde kural değeri değiştiyse farklıdır).
3. Kaynak ayarları: her kaynağın yöntemi; API gizli anahtarı tanımlı mı (değer yazılmaz).
4. Arşiv denemesi: ham_arsiv klasörüne yazma ve varlık sorgusu.
5. Tablo gidiş-dönüş: sütun türleri, tarih günü ve saati korunuyor mu (saat dilimi kayması);
   0 satırlık tablo yazılıp okunabiliyor mu.
6. Kaynak denemesi: bağlı her kaynak bir kez okunur ve kalite denetiminden geçirilir; tarih
   alanlarının türü (saat dilimi) yazılır; kaynaklar arası ilişki ve mutabakat denetlenir;
   arşive ve sonuç tablolarına yazılmaz. Hata iletisi satır verisi içermez, paylaşılabilir.
"""
# %% 1. Kod özeti (depodaki aktarim_ozeti.txt ile satır satır aynı olmalı)
import hashlib
import os

import dataiku

import avukat_perf

KUTUPHANE = os.path.dirname(os.path.dirname(os.path.abspath(avukat_perf.__file__)))
PAKETLER = ("arayuz", "avukat_perf", "hat")  # araclar/ozet.py ile aynı sıra (test denetler)
SEKMELER = (("html", "index.html"), ("css", "stil.css"), ("js", "uygulama.js"),
            ("python", "backend.py"))
SENARYOLAR = (("AVUKAT_PERF_DONEM_SONU", "donem_sonu.py"),
              ("AVUKAT_PERF_GECELIK", "gecelik_calisma.py"))


def metin_ozeti(metin):
    """araclar/ozet.py içindeki işlevle birebir aynı."""
    satirlar = [satir.rstrip() for satir in metin.splitlines()]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return hashlib.sha256("\n".join(satirlar).encode("utf-8")).hexdigest()[:12]


def _alan(oge, ad):
    return oge.get(ad) if isinstance(oge, dict) else getattr(oge, ad, None)


for paket in PAKETLER:
    klasor = os.path.join(KUTUPHANE, paket)
    if not os.path.isdir(klasor):
        print(paket, "KLASÖR YOK")
        continue
    for ad in sorted(os.listdir(klasor)):
        if ad.endswith(".py"):
            with open(os.path.join(klasor, ad), encoding="utf-8") as dosya:
                print(paket + "/" + ad, metin_ozeti(dosya.read()))

proje = dataiku.api_client().get_default_project()
try:  # web uygulamasının dört sekmesi (Dataiku API'si sürüme göre değişebilir)
    uygulamalar = list(proje.list_webapps())
    secilen = [w for w in uygulamalar if _alan(w, "name") == "avukat_performans"] or uygulamalar
    sekmeler = proje.get_webapp(_alan(secilen[0], "id")).get_settings().get_raw()["params"]
    for anahtar, ad in SEKMELER:
        print("webapp/" + ad, metin_ozeti(sekmeler.get(anahtar) or ""))
except Exception as hata:  # okunamazsa sekmeler elle karşılaştırılır
    print("webapp OKUNAMADI ({}); sekmeleri elle karşılaştırın".format(type(hata).__name__))
for senaryo, ad in SENARYOLAR:
    try:
        adimlar = proje.get_scenario(senaryo).get_settings().raw_steps
        betik = [adim["params"]["script"] for adim in adimlar
                 if adim.get("type") == "custom_python"]
        print("tarifler/" + ad, metin_ozeti(betik[0]) if betik else "PYTHON ADIMI YOK")
    except Exception as hata:
        print("tarifler/" + ad, "OKUNAMADI ({})".format(type(hata).__name__))

# %% 2. Parametreler
from avukat_perf.params import dogrula
from avukat_perf.surum import hesap_surumu, json_ozeti
from avukat_perf.sema import KAYNAKLAR
from hat import ayar as ayar_modulu
from hat.dataiku_ortam import DataikuOrtam

ortam = DataikuOrtam()
params = ayar_modulu.yukle(ortam, "params")  # params.json + varsa params_ek.json
ayarlar = ayar_modulu.yukle(ortam, "kaynaklar")  # kaynaklar.json + varsa kaynaklar_ek.json
ekler = [ad for ad in ("params_ek.json", "kaynaklar_ek.json")
         if ortam.ayar_oku_varsa(ad) is not None]
print("ek ayar dosyaları:", ", ".join(ekler) or "yok")
for ad in ("params.json", "kaynaklar.json"):  # depodaki varsayılan dosya olduğu gibi mi
    print("degiskenler/" + ad, json_ozeti(ortam.ayar_oku(ad)))
hatalar = dogrula(params)
print("params:", "geçerli" if not hatalar else hatalar)
print("kaynaklar:", ayar_modulu.dogrula(ayarlar) or "geçerli")
print("hesap_surumu", hesap_surumu(params))

# %% 3. Kaynak ayarları (sistem ayarı + kaynak ayarı)
for ad, ayar in sorted((ad, ayar_modulu.kaynak_ayari(ayarlar, ad)) for ad in KAYNAKLAR):
    yontem = ayar.get("yontem", "bekliyor")
    satir = "{:<20} {}".format(ad, yontem)
    if yontem == "dataiku":
        satir += " · veri kümesi " + ayar["dataiku"]["veri_kumesi"]
    if yontem == "api":
        gizli_adi = (ayar["api"].get("kimlik") or {}).get("gizli")
        if gizli_adi:
            try:
                ortam.gizli(gizli_adi)
                satir += " · gizli anahtar tanımlı: " + gizli_adi
            except KeyError:
                satir += " · GİZLİ ANAHTAR TANIMLI DEĞİL: " + gizli_adi
    print(satir)

# %% 4. Arşiv denemesi
import pandas as pd

from hat import calisma

deneme_yolu = "kontrol/deneme_" + calisma.simdi().strftime("%Y%m%d%H%M%S") + ".txt"
ortam.arsiv_yaz(deneme_yolu, "aktarım kontrolü".encode("utf-8"))
print("arşive yazıldı:", deneme_yolu, "· bulundu:", ortam.arsiv_var(deneme_yolu))

# %% 5. Tablo gidiş-dönüş (kontrol tabloları kurulumda oluşturulur)
# kontrol_tablo veri bağlantısında, kontrol_tablo_sql izleme tablolarının SQL bağlantısında:
# tarih ve tür davranışı bağlantıya göre değişir, ikisi de denenir.
from avukat_perf.ortak import gun
from hat import veri_kumeleri

deneme = pd.DataFrame({"metin": ["D-001", None], "sayi": [1.5, None],
                       "tarih": pd.to_datetime(["2026-11-19", None]),
                       "zaman": pd.to_datetime(["2026-11-19 02:00:00", "2026-11-19 23:30:00"]),
                       "mantiksal": [True, False]})
for tablo_adi in veri_kumeleri.KONTROL:
    # İlk gece buna dayanır: hiç yazılmamış veri kümesinin şeması boş liste dönmeli.
    sema = dataiku.Dataset(tablo_adi).read_schema(raise_if_empty=False)
    print(tablo_adi, "· hiç yazılmamışken şema boş liste:",
          sema == [] or "önceden yazılmış, ilk denemede bakın")
    ortam.tablo_yaz(tablo_adi, deneme)
    geri = ortam.tablo_oku(tablo_adi)
    print(geri.dtypes.to_dict())
    print(tablo_adi, "· sütunlar korunuyor:", list(geri.columns) == list(deneme.columns))
    print(tablo_adi, "· tarih günü korunuyor:",
          gun(geri["tarih"]).iloc[0] == pd.Timestamp("2026-11-19"))
    print(tablo_adi, "· boş tarih korunuyor:", pd.isna(geri["tarih"].iloc[1]))
    print(tablo_adi, "· mantıksal korunuyor:",
          [bool(deger) for deger in geri["mantiksal"]] == [True, False])
    print(tablo_adi, "· sayı korunuyor:",
          float(geri["sayi"].iloc[0]) == 1.5 and pd.isna(geri["sayi"].iloc[1]))
    # Atama logu ve çalışma kaydı saatlidir: saat (ör. 23:30) birebir korunmalı.
    print(tablo_adi, "· saat korunuyor:",
          list(pd.to_datetime(geri["zaman"])) == list(deneme["zaman"]))
    # Olay çelişkisi ve bekleme gibi tablolar bazı geceler 0 satır yazılır.
    ortam.tablo_yaz(tablo_adi, deneme.iloc[0:0])
    bos = ortam.tablo_oku(tablo_adi)
    print(tablo_adi, "· 0 satırlık tablo yazılıp okunuyor:",
          bos is not None and bos.empty and list(bos.columns) == list(deneme.columns))

# %% 6. Kaynak denemesi
from avukat_perf import kalite
from avukat_perf.sema import zorunlu_kaynaklar
from hat import kaynak, okuma

cekim, okunan = calisma.simdi().normalize(), {}
for ad, ayar in sorted((ad, ayar_modulu.kaynak_ayari(ayarlar, ad)) for ad in KAYNAKLAR):
    if ayar.get("yontem", "bekliyor") == "bekliyor":
        continue
    try:
        ham = kaynak.cek(ayar, ortam, okuma.baglam(cekim))
        normal = kaynak.normalle(ad, ham, ayar)
        # Tarih alanlarının ham türü (şema bilgisi): saat dilimli ("datetime64[ns, UTC]") ise
        # bilinen bir akşam kaydının günü kaynak sistemle karşılaştırılır (README, İlk kurulum).
        print(ad, "· tarih alanı türleri:", {alan: str(normal[alan].dtype) for alan, tur, _ in
                                              KAYNAKLAR[ad]["alanlar"]
                                              if tur in ("tarih", "zaman") and alan in normal})
        temiz, sonuc = kalite.denetle(ad, normal, cekim, params)
    except Exception as hata:  # bağlantı, yetki ya da biçim hatası: türü ve iletisi yazılır
        print(ad, "· OKUNAMADI ·", type(hata).__name__, str(hata)[:300])
        continue
    if temiz is not None:
        okunan[ad] = temiz
    print(ad, "·", len(ham), "satır · kalite:", kalite.karar(sonuc))
    sorunlu = sonuc[sonuc["durum"] != "GECTI"]
    if not sorunlu.empty:
        print(sorunlu[["kontrol", "durum", "deger", "esik", "aciklama"]].to_string(index=False))
# Kaynaklar arası anahtar eşleşmesi ve mutabakat (biçim farkı ilk gerçek geceden önce görülür).
if all(ad in okunan for ad in zorunlu_kaynaklar()):
    for sonuc in okuma.iliskiler(okunan, params, cekim):
        for satir in sonuc.itertuples():
            print("ilişki ·", satir.kontrol, "·", satir.durum, "·", satir.deger, satir.aciklama)
else:
    print("ilişki denetimi atlandı: zorunlu kaynaklar okunamadı")
