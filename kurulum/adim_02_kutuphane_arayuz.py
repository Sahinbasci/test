"""Kurulum adım 2: kütüphane paketi arayuz (18 dosya).

araclar/paketle.py üretir; elle değiştirmeyin. Dataiku'da projenin bir Python not
defterine bu dosyanın tamamını yapıştırıp çalıştırın: dosyalar proje kütüphanesine
(Kod > Kütüphaneler > python/arayuz) yazılır, aynı adlı dosyanın üzerine yazılır ve geri
okunarak doğrulanır. Sonda "arayuz: 18 dosya yazıldı ve doğrulandı" görünmelidir.
"""
import hashlib

import dataiku

PAKET = "arayuz"
DOSYALAR = {}

DOSYALAR["__init__.py"] = r'''"""Arayüz sunum katmanı: ekran–veri sözleşmesi ve sayfa verisinin hazırlanması.

Arayüz hesap yapmaz. Her ekran bileşeni yalnız sözleşmede tanımlı alanları alır; arka uçta
hesaplanan her sütun ya bir bileşende gösterilir ya gerekçesiyle dışarıda bırakılır.
Testler (tests/test_arayuz.py) bunu sonuç tablolarına, HTML'e ve JavaScript'e karşı denetler.
"""
'''

DOSYALAR["dagilim_brans.py"] = r'''"""Branş bazında gerçekleşen / beklenen tahsilat oranının dağılımı (kutu grafiği verisi).

Avukat × branş kırılımından (sonuc_tahsilat_brans) yalnız o branşta yeterli veri eşiğine
ulaşan (yeterli; kural hesap anında yazılır) ve oranı olan satırlar sayılır: az dosyalı
satırın oranı şansa çok bağlıdır. Oran 1 beklenen düzeydir. Satır türleri (tur):
- KUTU: branş başına sayılan avukat (adet), çeyrekler (ceyrek_alt, ortanca, ceyrek_ust; doğrusal
  ara değer), bıyıklar (biyik_alt, biyik_ust: çeyrekler arası açıklığın 1,5 katı içindeki en uç
  oranlar, Tukey) ve eşiğe ulaşmadığı ya da oranı olmadığı (beklenen yok) için sayılmayan
  avukat (disarida). Hiç sayılan avukatı
  olmayan branşın çeyrekleri boştur.
- AYKIRI: bıyıkların dışındaki her avukat (avukat_kodu, oran).
Branşlar sayılan avukat sayısına göre çoktan aza, eşitlikte ada göre sıralanır.
"""
import pandas as pd

from avukat_perf.mantik import dogru_seri

TUKEY = 1.5
SUTUNLAR = ["tur", "brans", "adet", "ceyrek_alt", "ortanca", "ceyrek_ust", "biyik_alt",
            "biyik_ust", "disarida", "avukat_kodu", "oran"]


def _kutu(ad, oranlar, disarida):
    if oranlar.empty:
        return {"tur": "KUTU", "brans": ad, "adet": 0, "disarida": disarida}, oranlar
    q1, ortanca, q3 = (float(oranlar.quantile(oran)) for oran in (0.25, 0.5, 0.75))
    acik = TUKEY * (q3 - q1)
    icerde = oranlar[(oranlar >= q1 - acik) & (oranlar <= q3 + acik)]
    return ({"tur": "KUTU", "brans": ad, "adet": len(oranlar), "ceyrek_alt": q1,
             "ortanca": ortanca, "ceyrek_ust": q3, "biyik_alt": float(icerde.min()),
             "biyik_ust": float(icerde.max()), "disarida": disarida}, oranlar.drop(icerde.index))


def oran_kutulari(brans):
    """Branş başına kutu ve aykırı satırları; tablo yoksa ya da eski biçimdeyse None."""
    if brans is None or brans.empty or "yeterli" not in brans.columns:
        return None
    sayilan = dogru_seri(brans["yeterli"]) & brans["oran"].notna()
    adet = sayilan.groupby(brans["brans"]).sum()
    sira = sorted(adet.index, key=lambda ad: (-adet[ad], str(ad)))
    satirlar = []
    for ad in sira:
        bu = brans["brans"] == ad
        oranlar = brans.loc[bu & sayilan, "oran"].astype(float)
        kutu, aykiri = _kutu(ad, oranlar, int((bu & ~sayilan).sum()))
        satirlar.append(kutu)
        satirlar += [{"tur": "AYKIRI", "brans": ad, "avukat_kodu": brans.at[i, "avukat_kodu"],
                      "oran": float(deger)} for i, deger in aykiri.sort_values().items()]
    return pd.DataFrame(satirlar, columns=SUTUNLAR)
'''

DOSYALAR["dagilim_sure.py"] = r'''"""Kriter 1 ilk işlem süresi dağılımının verisi (sayım; puan hesaplanmaz).

Kapanan dönemler eşik kuralına göre ayrı sayılır (kural: OTO gün kuralı, OTO_DISI takvim ayı
kuralı; hesap anında sonuca yazılan esik_kurali'ndan; sütun yoksa TUMU). Her kural için:
- KUTU: ilk işlem süresi 5 günlük kutularda (alt, ust; ust boşsa açık uçlu son kutu), dönemin
  kapanmadan önce ulaştığı en yüksek bayrağa göre. Uzun kuyruk son kutuda toplanır (en çok 20).
- ESIK: bayrak eşikleri, hesap anında yazılan eşik günlerinden (esik_gun_sari,
  esik_gun_turuncu; süreyle aynı ölçekte, haklı bekleme hariç). Birbirine en çok ESIK_ARALIK
  gün yakın değerler tek aralıkta toplanır (takvim ayı kuralında 59–62. gün gibi): alt ve ust
  aralığın ilk ve son günüdür (adet boş: ekranda gösterilmez). Ekran eşiği parametreden
  değil bu satırlardan çizer; eşik sütunlarını taşımayan eski tabloda eşik satırı yoktur.
toplam ve ortanca, kuralın kapanan dönem sayısı ve ortanca süresidir.
"""
import pandas as pd

from avukat_perf.ortak import birlestir

SURE_KUTU = 5
SURE_EN_COK_KUTU = 20
BAYRAKSIZ = "YOK"
ESIK_ARALIK = 3
ESIKLER = (("SARI", "esik_gun_sari"), ("TURUNCU", "esik_gun_turuncu"))
KURAL_SIRASI = {"OTO": 0, "OTO_DISI": 1}
SUTUNLAR = ["tur", "kural", "alt", "ust", "bayrak", "adet", "toplam", "ortanca"]


def _kutular(kapanan, gun):
    son_kutu = min(int(gun.max() // SURE_KUTU), SURE_EN_COK_KUTU - 1)
    alt = (gun // SURE_KUTU).clip(upper=son_kutu).astype(int) * SURE_KUTU
    bayrak = kapanan.get("en_yuksek_seviye", pd.Series(None, index=kapanan.index,
                                                       dtype=object)).fillna(BAYRAKSIZ)
    sayim = pd.DataFrame({"alt": alt, "bayrak": bayrak}).groupby(
        ["alt", "bayrak"]).size().rename("adet").reset_index()
    izgara = pd.MultiIndex.from_product(
        [range(0, (son_kutu + 1) * SURE_KUTU, SURE_KUTU), sorted(set(bayrak))],
        names=["alt", "bayrak"])
    sayim = sayim.set_index(["alt", "bayrak"]).reindex(izgara, fill_value=0).reset_index()
    son = sayim["alt"] == son_kutu * SURE_KUTU
    acik_uclu = bool(gun.max() >= (son_kutu + 1) * SURE_KUTU)
    return sayim.assign(tur="KUTU", ust=(sayim["alt"] + SURE_KUTU).where(~(son & acik_uclu)))


def _esikler(kapanan):
    satirlar = []
    for bayrak, sutun in ESIKLER:
        gunler = kapanan[sutun].dropna().astype(int) if sutun in kapanan.columns else []
        araliklar = []
        for deger in sorted(set(gunler)):
            if araliklar and deger - araliklar[-1][1] <= ESIK_ARALIK:
                araliklar[-1][1] = deger
            else:
                araliklar.append([deger, deger])
        satirlar += [{"tur": "ESIK", "bayrak": bayrak, "alt": alt, "ust": ust}
                     for alt, ust in araliklar]
    return pd.DataFrame(satirlar, columns=["tur", "bayrak", "alt", "ust"])


def _kural(kapanan):
    gun = kapanan["sure_gun"].astype(float).clip(lower=0)
    tablo = birlestir([_kutular(kapanan, gun), _esikler(kapanan)],
                      ["tur", "alt", "ust", "bayrak", "adet"])
    return tablo.assign(toplam=len(kapanan), ortanca=float(gun.median()))


def k1_sure(k1):
    """Kapanan Kriter 1 dönemlerinin kural başına süre kutuları ve eşikleri (yoksa None)."""
    if k1 is None or k1.empty:
        return None
    kapanan = k1[(k1["seviye"] == "KAPANDI") & k1["sure_gun"].notna()]
    if kapanan.empty:
        return None
    kural = kapanan.get("esik_kurali", pd.Series("TUMU", index=kapanan.index)).fillna("TUMU")
    parcalar = [_kural(kapanan[kural == ad]).assign(kural=ad)
                for ad in sorted(set(kural), key=lambda ad: (KURAL_SIRASI.get(ad, 9), ad))]
    return birlestir(parcalar, SUTUNLAR)
'''

DOSYALAR["sozlesme.py"] = r'''"""Ekran–veri sözleşmesi: her bileşenin sayfası, beslendiği tablo sütunları ve aldığı alanlar.

kaynak: {tablo: [sütunlar]}; alanlar: bileşene gönderilen kayıt anahtarları (parametreden
beslenende kaynak boş). Ortak listeler sozlesme_alanlar.py, dışlananlar sozlesme_dislanan.py;
dağılım grafikleri sozlesme_dagilim.py, tahsilat bileşenleri sozlesme_tahsilat.py; ortak şerit,
Puanlama Kuralları ve Veri Durumu sozlesme_ortak.py. SECIMLIK_SUTUNLAR: okunan ama tabloda
bulunmayabilen (gruplamaya bağlı) sütunlar.
"""
from arayuz.sozlesme_dagilim import DAGILIM_BILESENLERI
from arayuz.sozlesme_ortak import ORTAK_BILESENLER
from arayuz.sozlesme_alanlar import (AY, BIRLESIK, K1_LISTE, K2_LISTE, MEVCUT, OLAY, SURE_OZET,
                                     SURE_PUANI, YILLIK)
from arayuz.sozlesme_tahsilat import SECIMLIK_SUTUNLAR, TAHSILAT_BILESENLERI  # noqa: F401


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


BILESENLER = {
    "genel.kpi": _b("genel", {
        "sonuc_portfoy": ["aktif_dosya", "aktif_rucu_tutari"],
        "sonuc_tahsilat_grup": ["atfedilen", "rucu_toplami", "atanamayan"],
        "sonuc_sure_ozet": ["acik_sari", "acik_turuncu", "acik_kirmizi"],
        "sonuc_birlesik": ["durum"]},
        ["aktif_dosya", "aktif_rucu_tutari", "tahsilat_orani", "atanamayan_tahsilat",
         "acik_sari", "acik_turuncu", "acik_kirmizi", "sure_verisi", "yayimlanan",
         "avukat_sayisi"]),
    "genel.sutun_durumu": _b("genel", {"sonuc_puan_guncel": ["sutun", "puan", "durum"]},
                             ["sutun", "gecerli", "ortalama", "gecersiz", "bekleme_nedeni"]),
    "genel.avukat_tablosu": _b("genel", {
        "sonuc_birlesik": ["avukat_kodu"] + BIRLESIK,
        "sonuc_tahsilat_avukat": ["oran", "yeterli"], "sonuc_portfoy": ["aktif_dosya"],
        "sonuc_sure": ["avukat_kodu", "yeterli"], "model_avukat": ["unvan"]},
        ["avukat_kodu", "unvan", "aktif_dosya", "gerceklesen_beklenen", "tahsilat_yeterli",
         "sure_yeterli"] + BIRLESIK),
    "genel.brans": _b("genel", {"sonuc_portfoy": ["brans", "aktif_dosya", "aktif_rucu_tutari"]},
                      ["brans", "aktif_dosya", "aktif_rucu_tutari"]),
    "genel.bant": _b("genel", {"sonuc_portfoy": ["tutar_bandi", "bant_etiketi", "aktif_dosya"]},
                     ["tutar_bandi", "bant_etiketi", "aktif_dosya"]),
    "genel.aylik": _b("genel", {"sonuc_tahsilat_aylik": ["avukat_kodu", "ay", "tutar"] + AY},
                      ["ay", "yazilan", "yazilamayan", "kismi"]),
    "genel.yillik": _b("genel", {"sonuc_tahsilat_yillik": YILLIK}, YILLIK),
    "genel.oncelikli": _b("genel", {"sonuc_eposta": ["avukat_kodu", "kriter", "dosya_no",
                                                     "seviye", "sure_gun"]},
                          ["kriter", "dosya_no", "avukat_kodu", "seviye", "sure_gun"]),
    "avukat.liste": _b("avukat", {"sonuc_birlesik": ["avukat_kodu", "birlesik_puan",
                                                     "performans_notu", "durum"],
                                  "model_avukat": ["avukat_kodu", "unvan"]},
                       ["avukat_kodu", "unvan", "birlesik_puan", "performans_notu", "durum"]),
    "avukat.baslik": _b("avukat", {
        "model_avukat": ["avukat_kodu", "unvan", "calisma_durumu"],
        "sonuc_birlesik": ["birlesik_puan", "performans_notu", "genel_sira", "durum",
                           "eksik_sutunlar"]},
        ["avukat_kodu", "unvan", "calisma_durumu", "birlesik_puan", "performans_notu",
         "genel_sira", "durum", "eksik_sutunlar", "yayimlanan"]),
    "avukat.sutunlar": _b("avukat", {"sonuc_puan_guncel": ["avukat_kodu", "sutun", "puan",
                                                           "durum", "agirlik"],
                                     "sonuc_tahsilat_avukat": ["avukat_kodu", "yeterli"],
                                     "sonuc_sure": ["avukat_kodu", "yeterli"]},
                          ["sutun", "puan", "durum", "agirlik", "yeterli"]),
    "avukat.aciklama": _b("avukat", {
        "sonuc_aciklama": ["avukat_kodu", "sutun", "sira", "tur", "metin", "etki"],
        "sonuc_puan_guncel": ["avukat_kodu", "sutun", "puan", "agirlik"],
        "sonuc_birlesik": ["avukat_kodu", "birlesik_puan", "performans_notu"]},
        ["sutun", "sira", "tur", "metin", "etki", "puan", "agirlik", "performans_notu"]),
    "avukat.kalite_davranis": _b("avukat", {"sonuc_kalite_davranis_sutun": [
        "avukat_kodu", "sutun", "puanlanan", "toplam", "gereken", "puan", "durum"]},
                       ["sutun", "puanlanan", "toplam", "gereken", "puan", "durum"]),
    "avukat.alt_basliklar": _b("avukat", {"sonuc_kalite_davranis_alt": [
        "avukat_kodu", "sutun", "alt_baslik", "puan", "degerlendirme_sayisi"]},
        ["sutun", "alt_baslik", "puan", "degerlendirme_sayisi"]),
    "avukat.mevcut_degerlendirme": _b("avukat", {"sonuc_mevcut_degerlendirme": [
        "avukat_kodu"] + MEVCUT}, MEVCUT),
    "avukat.portfoy": _b("avukat", {"sonuc_portfoy": ["avukat_kodu", "brans", "aktif_dosya",
                                                      "toplam_dosya", "aktif_rucu_tutari"]},
                         ["brans", "aktif_dosya", "toplam_dosya", "aktif_rucu_tutari"]),
    "avukat.sure": _b("avukat", {"sonuc_sure": ["avukat_kodu"] + SURE_PUANI}, SURE_PUANI),
    "avukat.sure_ozet": _b("avukat", {"sonuc_sure_ozet": ["avukat_kodu"] + SURE_OZET},
                           SURE_OZET),
    "avukat.aylik": _b("avukat", {"sonuc_tahsilat_aylik": ["avukat_kodu", "ay", "tutar",
                                                           "hareket_sayisi"] + AY},
                       ["ay", "tutar", "hareket_sayisi", "kismi"]),
    "avukat.gecmis": _b("avukat", {"birlesik_donem": [
        "avukat_kodu", "donem"] + BIRLESIK + ["yayin_surumu", "yayin_zamani", "hesap_surumu"]},
        ["donem"] + BIRLESIK + ["yayin_surumu", "yayin_zamani", "hesap_surumu"]),
    "sure.seviyeler": _b("sure", {"sonuc_k1": ["seviye"], "sonuc_k2": ["seviye"]},
                         ["kriter", "seviye", "adet"]),
    "sure.filtre": _b("sure", {"sonuc_k1": ["avukat_kodu", "pencerede_dusum"],
                               "sonuc_k2": ["avukat_kodu", "pencerede_dusum"]},
                      ["toplam", "gosterilen", "avukatlar"]),
    "sure.liste": _b("sure", {"sonuc_k1": K1_LISTE, "sonuc_k2": K2_LISTE},
                     ["kriter"] + K1_LISTE + [ad for ad in K2_LISTE if ad not in K1_LISTE]),
    "sure.olaylar": _b("sure", {"bayrak_olay": OLAY}, OLAY + ["son_sira"]),
    "sure.eposta": _b("sure", {"sonuc_eposta": ["avukat_kodu", "seviye", "dosya_no",
                                                "gonderilecek"]},
                      ["avukat_kodu", "sari", "turuncu", "kirmizi", "toplam", "gonderilecek"]),
}
BILESENLER.update(ORTAK_BILESENLER)
BILESENLER.update(DAGILIM_BILESENLERI)
BILESENLER.update(TAHSILAT_BILESENLERI)
'''

DOSYALAR["sozlesme_alanlar.py"] = r'''"""Sözleşmede birden çok bileşenin kullandığı sütun listeleri."""
K1_LISTE = ["dosya_no", "avukat_kodu", "brans", "atama_tarihi", "bitis_tarihi", "bitis_nedeni",
            "atama_ref", "esas_ilk_giris", "kapsam_disi_nedeni", "seviye", "en_yuksek_seviye",
            "dusum", "dusum_durumu", "sure_gun", "dusum_tarihi", "olcum_sonu", "esik_sari",
            "esik_turuncu", "esik_kirmizi"]
K2_LISTE = ["dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi", "brans", "surec_turu",
            "dava_ilk_giris", "kosul_kayip_tarihi", "rucu_kodu", "acik_bakiye",
            "kapsam_disi_nedeni", "seviye", "en_yuksek_seviye", "dusum", "dusum_durumu", "sure_gun",
            "surec_baslangici", "dusum_tarihi", "olcum_sonu", "esik_sari", "esik_turuncu",
            "esik_kirmizi"]
BIRLESIK = ["tahsilat", "sure", "kalite", "davranis", "birlesik_puan", "performans_notu",
            "genel_sira", "durum", "eksik_sutunlar"]
SURE_OZET = ["kriter", "izleniyor", "acik_sari", "acik_turuncu", "acik_kirmizi", "kapanan",
             "dusum_sayisi", "ort_sure_gun"]
OLAY = ["dosya_no", "avukat_kodu", "atama_tarihi", "kriter", "seviye", "olay_tarihi",
        "calisma_kimligi"]
YILLIK = ["avukat_kodu", "yil", "tutar", "yil_ici", "son_tarih", "onceki_ayni_donem", "degisim"]
MEVCUT = ["alt_baslik", "puan", "degerlendirme_sayisi", "son_degerlendirme"]
SURE_PUANI = ["risk_donemi", "risk_dosya", "o", "e", "kapsam", "r", "puan", "eksik_nedeni",
              "durum", "yeterli"]
AY = ["ilk_ay", "son_ay", "son_ay_kismi"]  # aylık grafiğin hesap anındaki ay ızgarası
'''

DOSYALAR["sozlesme_dagilim.py"] = r'''"""Ekran–veri sözleşmesinin dağılım grafikleri bölümü (sozlesme.BILESENLER'e eklenir).

Kutular arka uçta sayılır (arayuz/sunum_dagilim.py, arayuz/dagilim_sure.py); ekran yalnız
çizer.
"""
PUAN_KAYNAGI = {"sonuc_puan_guncel": ["avukat_kodu", "sutun", "puan", "durum"],
                "sonuc_birlesik": ["avukat_kodu", "birlesik_puan", "performans_notu", "durum"]}
KUTU = ["sutun", "alt", "ust", "adet", "not_adi", "ortanca", "toplam"]
KUTU_KONUM = [ad for ad in KUTU if ad != "not_adi"]  # konum şeridi notu göstermez


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


DAGILIM_BILESENLERI = {
    "genel.dagilim": _b("genel", PUAN_KAYNAGI, KUTU + ["taban"]),
    "genel.tahsilat_dosya": _b("genel", {"sonuc_tahsilat_avukat": ["avukat_kodu", "n", "puan",
                                                                  "durum"]},
                               ["avukat_kodu", "olgun_dosya", "puan", "durum", "taban"]),
    "genel.brans_oran": _b("genel", {"sonuc_tahsilat_brans": ["avukat_kodu", "brans", "oran",
                                                               "yeterli"]},
                           ["tur", "brans", "adet", "ceyrek_alt", "ortanca", "ceyrek_ust",
                            "biyik_alt", "biyik_ust", "disarida", "avukat_kodu", "oran"]),
    "avukat.konum": _b("avukat", PUAN_KAYNAGI, KUTU_KONUM + ["avukat_puani", "yuzdelik"]),
    "sure.ilk_islem_dagilim": _b("sure", {"sonuc_k1": ["seviye", "sure_gun", "en_yuksek_seviye",
                                                    "esik_kurali", "esik_gun_sari",
                                                    "esik_gun_turuncu"]},
                                 ["tur", "kural", "alt", "ust", "bayrak", "adet", "toplam",
                                  "ortanca"]),
}
'''

DOSYALAR["sozlesme_dislanan.py"] = r'''"""Ekrana bilerek konmayan sütunlar ve iç tablolar, gerekçeleriyle.

Arka uca yeni sütun eklenirse ya bir bileşene bağlanır ya buraya gerekçesiyle yazılır;
ikisi de yapılmazsa test kırılır.
"""
from hat.veri_kumeleri import CIKTI

GOSTERILMEYEN = {
    "sonuc_k1.atama_turu": "sulh ataması kapsam dışı nedeni (SULH) olarak gösterilir",
    "sonuc_k1.esas_tarihi_bilinmiyor": "kapsam dışı nedeni ESAS_TARIHI_BILINMIYOR olarak "
                                       "gösterilir",
    "sonuc_k2.baslangic_tarihi": "atamaya göre düzeltilmiş hâli (süreç başlangıcı) gösterilir",
    "sonuc_k1.esas_kaynagi": "olayların esas kaynağıyla eşlenmesi için; ekranda gösterilmez",
    "sonuc_k2.esas_kaynagi": "olayların esas kaynağıyla eşlenmesi için; ekranda gösterilmez",
    "bayrak_olay.esas_kaynagi": "Süre Takibi dönemin bugünkü esas kaynağındaki olayları gösterir",
    "olay_celiski.esas_kaynagi": "çelişki yalnız bu gecenin esas kaynağındaki olaylarla aranır",
    "sonuc_tahsilat_aylik.brans": "aylık grafikte branşlar toplanır",
    "sonuc_tahsilat_brans.beklenen": "branş tablosunda beklenen oran (beklenen ÷ rücu tutarı) "
                                     "olarak gösterilir",
    "sonuc_tahsilat_brans.r": "branş tablosunda tutar puanı gösterilir; düzeltilmiş oran avukatın "
                              "bütün dosyaları için kartta",
    "sonuc_tahsilat_yillik.hareket_sayisi": "yıllık tabloda tutar gösterilir; hareket sayısı "
                                            "aylık grafiğin ipucundadır",
    "sonuc_tahsilat_yillik.ayni_donem_tutar": "önceki yılın aynı dönemi ve değişim bundan "
                                              "hesaplanır; sonuç gösterilir",
    "sonuc_eposta.atama_tarihi": "dosya ayrıntısı Süre Takibi listesinde gösterilir",
    "sonuc_eposta.esik_sari": "dosya ayrıntısı Süre Takibi listesinde gösterilir",
    "sonuc_eposta.esik_turuncu": "dosya ayrıntısı Süre Takibi listesinde gösterilir",
    "sonuc_puan_guncel.donem": "kesit yazdırılan çıktıda gösterilir",
    "birlesik_donem.calisma_kimligi": "çalışma kimliği Veri Durumu sayfasında gösterilir",
    "calisma_kaydi.uretilen": "bayat sonuç tablosunu ayıklamak için kullanılır, gösterilmez",
    "calisma_kaydi.hazirlik_surumu": "dönem sonunun hazırlık sürümü denetimi için, gösterilmez",
}

IC_TABLOLAR = {
    "puan_donem": "dönem sütun puanları; ekran aynı sürümün birleşik dönem tablosunu okur",
    "gozlem_esas": "Kriter 1 girdisi; esasın ilk giriş günü dosya ayrıntısında gösterilir",
    "gozlem_esas_yedek": "yedek yol (gölge mod) Kriter 1 girdisi; dosya ayrıntısında gösterilir",
    "gozlem_dava": "Kriter 2 girdisi; dava esasının ilk giriş günü dosya ayrıntısında",
    "gozlem_kosul": "Kriter 2 girdisi; koşul kaybı günü dosya ayrıntısında gösterilir",
    "model_dosya": "hesap girdisi (çekirdek sistem dosyası)",
    "model_atama_donemi": "hesap girdisi (atama dönemleri); dosya ayrıntısında gösterilir",
    "model_hareket": "hesap girdisi (tahsilat hareketleri); toplamları gösterilir",
    "model_bekleme": "hesap girdisi (haklı bekleme); eşik tarihlerine yansır",
    "model_degerlendirme": "hesap girdisi (değerlendirme sistemi); alt başlık puanları gösterilir",
    "model_k2_goruntu": "hesap girdisi (dava takip süreç görüntüsü)",
}

# Gecenin yazdığı sonuc_ ve model_ tabloları çalışma kimliğiyle etiketlenir (tutarlılık denetimi).
GOSTERILMEYEN.update({ad + ".calisma_kimligi": "tablonun hangi gecelik çalışmadan geldiğini "
                      "denetler; ekran yalnız son başarılı gecenin tablosunu gösterir"
                      for ad in CIKTI if ad.startswith(("sonuc_", "model_"))})
'''

DOSYALAR["sozlesme_ortak.py"] = r'''"""Ekran–veri sözleşmesinin ortak şerit, Puanlama Kuralları ve Veri Durumu bölümü
(sozlesme.BILESENLER'e eklenir).

ortak.durum: üst şerit (arayuz/sunum_ortak.py); gölge kriter bazında (golge_ilk_islem,
golge_dava_acma), okunamayan tablolar, parametre hataları ve son gecede bağlantısı beklenen
kaynaklar dahil.
ortak.adlar: ekran adları (tur: sistem, brans, alt_baslik, mevcut_alan; branşta renk sırası).
kurallar.hatalar: gecenin reddedeceği parametre dosyasının hata iletileri.
"""
from arayuz.sozlesme_alanlar import OLAY


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


ORTAK_BILESENLER = {
    "ortak.durum": _b("ortak", {
        "calisma_kaydi": ["calisma_kimligi", "tur", "kaynak", "baslangic", "cekim_tarihi",
                          "bitis", "durum", "hesap_surumu", "golge", "golge_zorunlu"],
        "sonuc_sure_ozet": ["acik_kirmizi"]},
                      ["kesit", "son_guncelleme", "son_karar", "son_donem_karari",
                       "hesap_surumu", "golge_mod", "golge_ilk_islem", "golge_dava_acma",
                       "kural_degisti", "acik_kirmizi", "okunamayan", "parametre_hatasi",
                       "bekleyen_kaynaklar"]),
    "ortak.adlar": _b("ortak", {}, ["tur", "kod", "ad", "sira"]),
    "kurallar.hatalar": _b("kurallar", {}, ["hata"]),
    "kurallar.agirliklar": _b("kurallar", {}, ["sutun", "agirlik", "teyit_bekliyor", "aciklama"]),
    "kurallar.notlar": _b("kurallar", {}, ["not_adi", "esik", "teyit_bekliyor", "aciklama"]),
    "kurallar.parametreler": _b("kurallar", {}, ["bolum", "ad", "deger", "teyit_bekliyor"]),
    "kurallar.aciklamalar": _b("kurallar", {}, ["bolum", "aciklama"]),
    "veri.kaynaklar": _b("veri", {"calisma_kaydi": [
        "calisma_kimligi", "kaynak", "yontem", "cekim_tarihi", "satir_sayisi", "kalite_sonucu",
        "durum", "arsiv_yolu"]}, ["kaynak", "sistem", "yontem", "cekim_tarihi", "satir_sayisi",
                                  "kalite_sonucu", "durum", "arsiv_yolu", "son_basarili"]),
    "veri.calismalar": _b("veri", {"calisma_kaydi": [
        "calisma_kimligi", "tur", "baslangic", "bitis", "cekim_tarihi", "durum", "aciklama"]},
        ["calisma_kimligi", "tur", "baslangic", "bitis", "cekim_tarihi", "durum", "aciklama"]),
    "veri.kalite": _b("veri", {"kalite_sonucu": [
        "kaynak", "kontrol", "durum", "deger", "esik", "aciklama", "calisma_kimligi",
        "cekim_tarihi"]}, ["kaynak", "kontrol", "durum", "deger", "esik", "aciklama",
                           "calisma_kimligi", "cekim_tarihi"]),
    "veri.celiski_ozet": _b("veri", {"olay_celiski": []}, ["toplam", "gosterilen"]),
    "veri.celiski": _b("veri", {"olay_celiski": OLAY[:6] + [
        "olay_tarihi_yeni", "calisma_kimligi", "tespit_tarihi"]},
        OLAY[:6] + ["olay_tarihi_yeni", "calisma_kimligi", "tespit_tarihi"]),
}
'''

DOSYALAR["sozlesme_tahsilat.py"] = r'''"""Ekran–veri sözleşmesinin tahsilat bölümü (sozlesme.BILESENLER'e eklenir).

Avukat kartı: tahsilat puanı ve üç bileşeni (tutar, sıklık, güncellik), branş tablosu (branş
satırları ve avukatın bütün dosyaları için toplam satırı). Genel Bakış: karşılaştırma grupları
ve avukat bazında aylık tahsilat tablosu (hesap anındaki ay ızgarasının son ayları).
"""
from arayuz.sozlesme_alanlar import AY

TAHSILAT = ["n", "gerceklesen", "beklenen", "oran", "r", "puan_tutar", "siklik_o", "siklik_e",
            "puan_siklik", "guncellik_o", "guncellik_e", "puan_guncellik", "puan", "eksik_nedeni",
            "durum", "yeterli"]
BRANS = ["n", "maruziyet", "gerceklesen", "tahsilat_orani", "beklenen_oran", "dosya_basina",
         "siklik_o", "siklik_e", "guncellik_o", "guncellik_e", "puan_tutar", "puan_siklik",
         "puan_guncellik", "puan", "eksik_nedeni", "yeterli"]
GRUP = ["dosya_sayisi", "rucu_toplami", "atfedilen", "atanamayan", "oran", "siklik_hizi"]
GRUP_ANAHTARI = ["brans", "yas_bandi", "yas_etiketi", "tutar_bandi", "bant_etiketi"]
# Gruplamada (tahsilat.gruplama) olmayan boyutun sütunu grup tablosunda üretilmez (hat/hesap):
# bu sütunlar olmadan da tablo gösterilir, eski biçim sayılmaz (temel.guncel_tablolar).
SECIMLIK_SUTUNLAR = {"sonuc_tahsilat_grup": GRUP_ANAHTARI}


def _b(sayfa, kaynak, alanlar):
    return {"sayfa": sayfa, "kaynak": kaynak, "alanlar": alanlar}


TAHSILAT_BILESENLERI = {
    "avukat.tahsilat": _b("avukat", {"sonuc_tahsilat_avukat": ["avukat_kodu"] + TAHSILAT},
                          TAHSILAT),
    "avukat.brans": _b("avukat", {"sonuc_tahsilat_brans": ["avukat_kodu", "brans"] + BRANS,
                                  "sonuc_tahsilat_avukat": ["avukat_kodu"] + BRANS},
                       ["brans", "toplam"] + BRANS),
    "genel.gruplar": _b("genel", {"sonuc_tahsilat_grup": GRUP_ANAHTARI + GRUP},
                        GRUP_ANAHTARI + GRUP),
    "genel.aylik_avukat": _b("genel", {"sonuc_tahsilat_aylik": ["avukat_kodu", "ay", "tutar"] + AY},
                             ["avukat_kodu", "ay", "tutar", "kismi", "toplam"]),
}
'''

DOSYALAR["sunum.py"] = r'''"""Sayfa verisi: sayfa adına göre bileşen kayıtlarını hazırlar (Genel Bakış ve ortak şerit).

sayfa(ad, tablolar, params, secim, okunamayan) -> {"sayfa": ad, "bilesenler": {kimlik: [kayıt]}}.
tablolar: sonuç tablosu adı -> DataFrame ya da None (henüz üretilmemiş); okunamayan: arka ucun
okuyamadığı tablo adları (şeride gelir). Parametre her yanıtta doğrulanır (gecenin kuralı).
Sayfalar: genel, avukat (secim["kod"]), sure, kurallar, veri. SECIMLER: sorgudan alınan
seçimler (avukat kodu ve Süre Takibi süzgeçleri); arka uç ve önizleme bunu kullanır.
"""
from avukat_perf.mantik import dogru_seri
from avukat_perf.params import dogrula
from avukat_perf.params_sema import SUTUNLAR
from avukat_perf.portfoy import ATANAMAYAN
from arayuz import (dagilim_brans, sunum_avukat, sunum_dagilim, sunum_kural, sunum_ortak,
                    sunum_siralama, sunum_sure, sunum_tahsilat)
from arayuz.sozlesme import BILESENLER
from arayuz.temel import (ay_izgarasi, guncel_tablolar, kayitlar, oran, seviye_sirala, tek,
                          topla)

BEKLEME = ("KAYNAK_BEKLENIYOR", "TEYIT_BEKLIYOR", "GOLGE_MOD")
TABLOLAR = sorted({tablo for bilesen in BILESENLER.values() for tablo in bilesen["kaynak"]})
SAYFALAR = ("genel", "avukat", "sure", "kurallar", "veri")
SECIMLER = ("kod",) + tuple(sunum_sure.FILTRE)


def _sutun_durumu(puan):
    satirlar = []
    for sutun in SUTUNLAR:
        parca = puan[puan["sutun"] == sutun]
        gecerli = parca[parca["durum"] == "GECERLI"]
        bekleyen = parca[parca["durum"].isin(BEKLEME)]
        bekleme = bekleyen["durum"].value_counts().index[0] if len(bekleyen) and \
            gecerli.empty else None
        satirlar.append({"sutun": sutun, "gecerli": len(gecerli),
                         "ortalama": gecerli["puan"].mean() if len(gecerli) else None,
                         "gecersiz": len(parca) - len(gecerli) - len(bekleyen),
                         "bekleme_nedeni": bekleme})
    return satirlar


def _yillik_sirasi(yillik):
    """İçinde bulunulan yılın tahsilatına göre azalan; avukata yazılamayan en sonda."""
    bu_yil = yillik[dogru_seri(yillik["yil_ici"])].set_index("avukat_kodu")["tutar"]
    sira = yillik["avukat_kodu"].map(bu_yil).where(yillik["avukat_kodu"] != ATANAMAYAN,
                                                   -float("inf"))
    return yillik.assign(_s=sira).sort_values(["_s", "avukat_kodu", "yil"],
                                               ascending=[False, True, True])


def genel(tablolar, params):
    t = tablolar.get
    portfoy, grup, ozet, birlesik = (t("sonuc_portfoy"), t("sonuc_tahsilat_grup"),
                                     t("sonuc_sure_ozet"), t("sonuc_birlesik"))
    yayin = None if birlesik is None else int((birlesik["durum"] == "YAYIMLANDI").sum())
    sonuc = {"genel.kpi": tek("genel.kpi", {
        "aktif_dosya": topla(portfoy, "aktif_dosya"),
        "aktif_rucu_tutari": topla(portfoy, "aktif_rucu_tutari"),
        "tahsilat_orani": oran(topla(grup, "atfedilen"), topla(grup, "rucu_toplami")),
        "atanamayan_tahsilat": topla(grup, "atanamayan"),
        "acik_sari": topla(ozet, "acik_sari"), "acik_turuncu": topla(ozet, "acik_turuncu"),
        "acik_kirmizi": topla(ozet, "acik_kirmizi"), "sure_verisi": ozet is not None,
        "yayimlanan": yayin, "avukat_sayisi": None if birlesik is None else len(birlesik)})}
    puan = t("sonuc_puan_guncel")
    sonuc["genel.sutun_durumu"] = [] if puan is None else [
        tek("genel.sutun_durumu", satir)[0] for satir in _sutun_durumu(puan)]
    sonuc["genel.dagilim"] = kayitlar("genel.dagilim", sunum_dagilim.puan_dagilimi(
        puan, birlesik, params))
    sonuc["genel.tahsilat_dosya"] = kayitlar("genel.tahsilat_dosya", sunum_dagilim.tahsilat_dosya(
        t("sonuc_tahsilat_avukat"), params))
    sonuc["genel.brans_oran"] = kayitlar("genel.brans_oran", dagilim_brans.oran_kutulari(
        t("sonuc_tahsilat_brans")))
    sonuc["genel.avukat_tablosu"] = sunum_siralama.avukat_tablosu(tablolar)
    if portfoy is not None:  # bant etiketleri hesap anındaki sınırlardan (sonuç tablosunda)
        brans = portfoy.groupby("brans", as_index=False)[["aktif_dosya", "aktif_rucu_tutari"]]
        sonuc["genel.brans"] = kayitlar("genel.brans", brans.sum().sort_values(
            "aktif_dosya", ascending=False))
        bant = portfoy.assign(bant_etiketi=portfoy.get("bant_etiketi")).groupby(
            "tutar_bandi", as_index=False).agg(
            aktif_dosya=("aktif_dosya", "sum"), bant_etiketi=("bant_etiketi", "first"))
        sonuc["genel.bant"] = kayitlar("genel.bant", bant)
    aylik = t("sonuc_tahsilat_aylik")
    if aylik is not None:
        yazilamayan = aylik["avukat_kodu"] == ATANAMAYAN
        ay = aylik.assign(yazilan=aylik["tutar"].where(~yazilamayan, 0.0),
                          yazilamayan=aylik["tutar"].where(yazilamayan, 0.0))
        sonuc["genel.aylik"] = kayitlar("genel.aylik", ay_izgarasi(
            aylik, ay, ["yazilan", "yazilamayan"]))
    yillik = t("sonuc_tahsilat_yillik")
    if yillik is not None:
        sonuc["genel.yillik"] = kayitlar("genel.yillik", _yillik_sirasi(yillik))
    eposta = t("sonuc_eposta")
    if eposta is not None:
        sonuc["genel.oncelikli"] = kayitlar("genel.oncelikli", seviye_sirala(eposta).head(8))
    sonuc["genel.gruplar"] = kayitlar("genel.gruplar", grup)
    sonuc["genel.aylik_avukat"] = sunum_tahsilat.aylik_tablo(aylik)
    return sonuc


def sayfa(ad, tablolar, params, secim=None, okunamayan=()):
    if ad not in SAYFALAR:
        raise ValueError("bilinmeyen sayfa")  # girdi iletiye konmaz
    secim, tablolar, hatalar = secim or {}, guncel_tablolar(tablolar), dogrula(params)
    if ad == "genel":
        bilesenler = genel(tablolar, params)
    elif ad == "avukat":
        bilesenler = sunum_avukat.avukat(tablolar, params, secim.get("kod"))
    elif ad == "sure":
        bilesenler = sunum_sure.sure(tablolar, secim)
    elif ad == "kurallar":
        bilesenler = sunum_kural.kurallar(params, hatalar)
    else:
        bilesenler = sunum_kural.veri(tablolar)
    bilesenler["ortak.durum"] = sunum_ortak.ortak_durum(tablolar, params, okunamayan, hatalar)
    bilesenler["ortak.adlar"] = sunum_ortak.adlar(params)
    return {"sayfa": ad, "bilesenler": bilesenler}
'''

DOSYALAR["sunum_avukat.py"] = r'''"""Avukat sayfası verisi (Genel Bakış'taki avukat tablosu sunum_siralama.py'de).

Avukat kodu verilmezse listedeki ilk avukat (en yüksek birleşik puan) seçilir. Alt başlıklar
parametredeki sırayla, açıklama satırları sütun ve sıra numarasıyla sıralanır.
"""
import pandas as pd

from avukat_perf import donem
from avukat_perf.ortak import birlestir, yuvarla
from avukat_perf.params_sema import SUTUNLAR
from arayuz import sunum_dagilim, sunum_tahsilat
from arayuz.sunum_siralama import YETERLI, _avukatlar, _yeterli
from arayuz.temel import ay_izgarasi, kayitlar, secili

ACIKLAMA_SIRASI = {ad: sira for sira, ad in enumerate(SUTUNLAR + ("birlesik",))}


def avukat(tablolar, params, kod):
    liste = _avukatlar(tablolar)
    if liste is None or liste.empty:
        return {"avukat.liste": []}
    kod = kod if kod in set(liste["avukat_kodu"]) else liste["avukat_kodu"].iloc[0]
    t = tablolar.get
    sonuc = {"avukat.liste": kayitlar("avukat.liste", liste)}
    baslik = liste[liste["avukat_kodu"] == kod].assign(
        yayimlanan=int((liste["durum"] == "YAYIMLANDI").sum()))
    sonuc["avukat.baslik"] = kayitlar("avukat.baslik", baslik)
    puan = secili(t("sonuc_puan_guncel"), "avukat_kodu", kod)
    if puan is not None:
        # Puan ekrandaki ve birleşik puandaki gibi 2 ondalık (rengi gösterilen değerden).
        puan = puan.assign(_s=puan["sutun"].map(ACIKLAMA_SIRASI), puan=puan["puan"].map(
            yuvarla)).sort_values("_s")
        puan = puan.assign(yeterli=puan["sutun"].map(
            {sutun: _yeterli(t, kod, ad) for sutun, ad in YETERLI.items()}))
        sonuc["avukat.sutunlar"] = kayitlar("avukat.sutunlar", puan)
    aciklama = secili(t("sonuc_aciklama"), "avukat_kodu", kod)
    if aciklama is not None:
        sonuc["avukat.aciklama"] = kayitlar("avukat.aciklama", _aciklama(
            aciklama, puan, secili(t("sonuc_birlesik"), "avukat_kodu", kod)))
    sonuc["avukat.brans"] = sunum_tahsilat.brans_tablosu(tablolar, kod)
    for bilesen, tablo in (("avukat.tahsilat", "sonuc_tahsilat_avukat"),
                           ("avukat.kalite_davranis", "sonuc_kalite_davranis_sutun"),
                           ("avukat.sure", "sonuc_sure"), ("avukat.sure_ozet", "sonuc_sure_ozet")):
        sonuc[bilesen] = kayitlar(bilesen, secili(t(tablo), "avukat_kodu", kod))
    alt = secili(t("sonuc_kalite_davranis_alt"), "avukat_kodu", kod)
    if alt is not None:
        kodlar = params["kalite_davranis"]["alt_basliklar"]
        sira = {ad: no for no, ad in enumerate(kodlar["kalite"] + kodlar["davranis"])}
        sonuc["avukat.alt_basliklar"] = kayitlar("avukat.alt_basliklar", alt.assign(
            _s=alt["alt_baslik"].map(sira)).sort_values("_s"))
    mevcut = secili(t("sonuc_mevcut_degerlendirme"), "avukat_kodu", kod)
    if mevcut is not None:
        sira = {ad: no for no, ad in enumerate(params["kalite_davranis"]["mevcut_alanlar"])}
        sonuc["avukat.mevcut_degerlendirme"] = kayitlar(
            "avukat.mevcut_degerlendirme",
            mevcut.assign(_s=mevcut["alt_baslik"].map(sira)).sort_values("_s"))
    portfoy = secili(t("sonuc_portfoy"), "avukat_kodu", kod)
    if portfoy is not None:
        portfoy = portfoy.groupby("brans", as_index=False)[
            ["aktif_dosya", "toplam_dosya", "aktif_rucu_tutari"]].sum()
        sonuc["avukat.portfoy"] = kayitlar("avukat.portfoy", portfoy.sort_values(
            "toplam_dosya", ascending=False))
    aylik = t("sonuc_tahsilat_aylik")
    if aylik is not None:  # tahsilatı olmayan avukatta da ızgara sıfırla çizilir
        sonuc["avukat.aylik"] = kayitlar("avukat.aylik", ay_izgarasi(
            aylik, secili(aylik, "avukat_kodu", kod), ["tutar", "hareket_sayisi"]))
    sonuc["avukat.gecmis"] = _gecmis(t("birlesik_donem"), kod)
    sonuc["avukat.konum"] = kayitlar("avukat.konum", sunum_dagilim.konum(
        t("sonuc_puan_guncel"), t("sonuc_birlesik"), kod))
    return sonuc


def _aciklama(aciklama, puan, birlesik):
    """Açıklama satırları sütun ve sıra numarasıyla; her satırda sütunun ekrandaki puanı ve
    ağırlığı, birleşik satırlarında birleşik puan ve not (sonuç tablolarından). Açıklama satırı
    olmayan sütun için içeriksiz bir YOK satırı eklenir: ekran sütunun puanını ve ağırlığını
    (ör. bu fazda puana girmediğini) yine bilir."""
    eksik = [ad for ad in SUTUNLAR if ad not in set(aciklama["sutun"])]
    if eksik:
        aciklama = birlestir([aciklama, pd.DataFrame({
            "avukat_kodu": aciklama["avukat_kodu"].iloc[0] if len(aciklama) else None,
            "sutun": eksik, "sira": 0, "tur": "YOK", "metin": "",
            "etki": [float("nan")] * len(eksik)})], list(aciklama.columns))
    puanlar, agirliklar, notu = {}, {}, None
    if puan is not None:
        puanlar = dict(zip(puan["sutun"], puan["puan"]))
        if "agirlik" in puan.columns:
            agirliklar = dict(zip(puan["sutun"], puan["agirlik"]))
    if birlesik is not None and len(birlesik):
        puanlar["birlesik"] = yuvarla(birlesik["birlesik_puan"].iloc[0])
        notu = birlesik["performans_notu"].iloc[0]
    aciklama = aciklama.assign(
        _s=aciklama["sutun"].map(ACIKLAMA_SIRASI), puan=aciklama["sutun"].map(puanlar),
        agirlik=aciklama["sutun"].map(agirliklar),
        performans_notu=[notu if sutun == "birlesik" else None for sutun in aciklama["sutun"]])
    return aciklama.sort_values(["_s", "sira"])


def _gecmis(birlesik_donem, kod):
    """Her dönemin son yayın sürümü; puan ve not o sürümün kurallarıyla hesaplanmıştır."""
    gecmis = secili(donem.son_surum(birlesik_donem), "avukat_kodu", kod)
    if gecmis is None:
        return []
    gecmis = gecmis.sort_values("donem")
    return kayitlar("avukat.gecmis", gecmis.assign(yayin_zamani=pd.to_datetime(
        gecmis["yayin_zamani"])))
'''

DOSYALAR["sunum_dagilim.py"] = r'''"""Dağılım grafiklerinin verisi: sonuç tablolarından sayım ve seçim (puan hesaplanmaz).

- Puan dağılımı: her sütun ve birleşik puan için 5 puanlık kutularda avukat sayısı (yalnız
  geçerli ve yayımlanan puanlar; ekrandaki ve birleşik puandaki gibi 2 ondalığa yarım yukarı
  yuvarlanmış). Birleşik puan kutusunun notu sonuç tablosundaki
  performans_notu'dur; not eşikleri 5'in katı olduğundan her kutu tek nota düşer. Sütun
  puanlarında not yoktur. 100 puan son kutudadır. taban: beklenen düzeyin puanı (göreli ölçülen
  tahsilat ve süre sütunlarında; parametreden), öteki sütunlarda boş.
- Tahsilat ve portföy: her avukatın olgun dosya sayısı ve tahsilat puanı (güven ayarının
  etkisi: az dosyada puan 75'e yakın). Puanı olmayan avukat puansız gelir.
- Avukatın konumu: seçili avukatın her sütundaki yüzdeliği ve o sütunun dağılımı. Yüzdelik,
  puanı avukatınkinden düşük ya da ona eşit olan öteki avukatların oranıdır: en yüksek puan
  (eşitlerle birlikte) 100, en düşük tek puan 0; tek avukat 100.
- Kriter 1 süre dağılımı: arayuz/dagilim_sure.py.
"""
import pandas as pd

from avukat_perf.ortak import yuvarla
from avukat_perf.params_sema import SUTUNLAR

KUTU = 5
BIRLESIK = "birlesik"


def _puanlar(puan, birlesik):
    """(sutun, avukat_kodu, puan, not_adi): geçerli sütun puanları ve yayımlanan birleşik puan."""
    parcalar = []
    if puan is not None and not puan.empty:
        gecerli = puan[puan["durum"] == "GECERLI"]
        parcalar.append(gecerli[["sutun", "avukat_kodu", "puan"]].assign(not_adi=None))
    if birlesik is not None and not birlesik.empty:
        yay = birlesik[birlesik["durum"] == "YAYIMLANDI"]
        parcalar.append(pd.DataFrame({"sutun": BIRLESIK, "avukat_kodu": yay["avukat_kodu"],
                                      "puan": yay["birlesik_puan"],
                                      "not_adi": yay["performans_notu"]}))
    if not parcalar:
        return None
    tablo = pd.concat(parcalar, ignore_index=True)
    tablo = tablo[tablo["puan"].notna()]
    return tablo.assign(puan=tablo["puan"].map(yuvarla))


def _kutular(tablo):
    """Sütun başına 0-100 aralığının bütün kutuları; boş kutu 0."""
    alt = (tablo["puan"] // KUTU * KUTU).clip(lower=0, upper=100 - KUTU).astype(int)
    sayim = tablo.assign(alt=alt).groupby(["sutun", "alt"]).agg(
        adet=("puan", "size"), not_adi=("not_adi", "first")).reset_index()
    sira = [ad for ad in SUTUNLAR + (BIRLESIK,) if ad in set(tablo["sutun"])]
    izgara = pd.MultiIndex.from_product([sira, range(0, 100, KUTU)], names=["sutun", "alt"])
    sayim = sayim.set_index(["sutun", "alt"]).reindex(izgara).reset_index()
    ozet = tablo.groupby("sutun")["puan"].agg(ortanca="median", toplam="size")
    sayim = sayim.join(ozet, on="sutun").assign(ust=sayim["alt"] + KUTU)
    return sayim.assign(adet=sayim["adet"].fillna(0).astype(int))


def tabanlar(params):
    """Göreli ölçülen sütunlarda beklenen düzeyin puanı."""
    return {"tahsilat": params["tahsilat"]["taban"], "sure": params["sure_puani"]["taban"]}


def puan_dagilimi(puan, birlesik, params):
    """Genel Bakış: sütun ve birleşik puan dağılımı (kutu kayıtları)."""
    tablo = _puanlar(puan, birlesik)
    if tablo is None or tablo.empty:
        return None
    sayim = _kutular(tablo)
    return sayim.assign(taban=sayim["sutun"].map(tabanlar(params)))


def tahsilat_dosya(tahsilat_avukat, params):
    """Her avukat: olgun dosya sayısı (n, elde tutma payıyla kesirli) ve tahsilat puanı."""
    if tahsilat_avukat is None or tahsilat_avukat.empty:
        return None
    tablo = tahsilat_avukat[["avukat_kodu", "n", "puan", "durum"]]
    tablo = tablo.sort_values(["n", "avukat_kodu"]).rename(columns={"n": "olgun_dosya"})
    return tablo.assign(taban=tabanlar(params)["tahsilat"])


def konum(puan, birlesik, kod):
    """Seçili avukatın her sütundaki puanı ve yüzdeliği, sütunun dağılımıyla."""
    tablo = _puanlar(puan, birlesik)
    if tablo is None or tablo.empty:
        return None
    sayim = _kutular(tablo)
    yuzdelik = tablo.groupby("sutun")["puan"].rank(method="max", pct=False) - 1
    adet = tablo.groupby("sutun")["puan"].transform("size")
    tablo = tablo.assign(yuzdelik=(yuzdelik / (adet - 1).where(adet > 1)).fillna(1.0) * 100)
    secili = tablo[tablo["avukat_kodu"] == kod].set_index("sutun")
    return sayim.assign(avukat_puani=sayim["sutun"].map(secili["puan"]),
                        yuzdelik=sayim["sutun"].map(secili["yuzdelik"]))
'''

DOSYALAR["sunum_kural.py"] = r'''"""Puanlama Kuralları (parametrelerden) ve Veri Durumu (çalışma kaydı, kalite, çelişki).

Kurallar sayfası params.json'dan üretilir; ekranda elle yazılmış eşik yoktur. Teyit bekleyen
değerler params.json'daki _teyit_bekleyen listesinden ve null değerlerden işaretlenir.
Parametre geçersizse (gecenin reddedeceği dosya) önce hata listesi gelir; ağırlık ve not
kartları hesaplanmaz. Veri Durumu son gecelik çalışmayı, son çalışmaları, son gecelik ve son
dönem sonu çalışmasının geçmeyen kalite denetimlerini ve geriye dönük değişiklik nedeniyle
çelişen olayları (en yeni CELISKI_EN_COK; toplamıyla) gösterir. Ortak şerit sunum_ortak.py'de.
"""
import pandas as pd

from avukat_perf import agirlik
from avukat_perf.params_sema import GORUNUM, SUTUNLAR
from avukat_perf.sema import KAYNAKLAR
from arayuz.temel import kayitlar, tek
from hat import gecmis
from hat.calisma import OZET

CELISKI_EN_COK = 200
# Çelişkinin kalıcı anahtarı: aynı girdi satır sırasından bağımsız aynı satırları verir.
CELISKI_SIRASI = ["tespit_tarihi", "olay_tarihi", "kriter", "dosya_no", "avukat_kodu",
                  "atama_tarihi", "seviye", "olay_tarihi_yeni"]

def _metin(deger):
    """Parametre değerinin ekran metni: Evet/Hayır, Tanımsız, Türkçe ondalık, düz liste."""
    if deger is None:
        return "Tanımsız"
    if isinstance(deger, bool):
        return "Evet" if deger else "Hayır"
    if isinstance(deger, float):
        return repr(deger).replace(".", ",")
    if isinstance(deger, list):
        return ", ".join(_metin(oge) for oge in deger) if deger else "Boş liste"
    if isinstance(deger, dict):
        return "; ".join("{}: {}".format(ad, _metin(oge)) for ad, oge in deger.items())
    return str(deger)


def kurallar(params, hatalar=()):
    parametre, aciklama, teyit = [], [], set(params.get("_teyit_bekleyen", []))
    sonuc = {"kurallar.hatalar": [tek("kurallar.hatalar", {"hata": h})[0] for h in hatalar]}
    for bolum, alanlar in params.items():
        if bolum.startswith("_") or not isinstance(alanlar, dict) or bolum == GORUNUM:
            continue
        if alanlar.get("_not") and bolum != "agirliklar":  # ağırlık kartında gösterilir
            aciklama.append({"bolum": bolum, "aciklama": alanlar["_not"]})
        for ad, deger in alanlar.items():
            if not ad.startswith("_"):
                anahtar = bolum + "." + ad
                parametre.append({"bolum": bolum, "ad": ad, "deger": _metin(deger),
                                  "teyit_bekliyor": anahtar in teyit or bolum in teyit
                                  or deger is None})
    sonuc["kurallar.parametreler"] = [tek("kurallar.parametreler", s)[0] for s in parametre]
    sonuc["kurallar.aciklamalar"] = [tek("kurallar.aciklamalar", s)[0] for s in aciklama]
    if hatalar:  # ağırlık hesabı tutarsız karşılaştırmada hata verirdi; önce dosya düzeltilir
        return sonuc
    agirliklar = agirlik.sutun_agirliklari(params)
    sonuc["kurallar.agirliklar"] = [tek("kurallar.agirliklar", {
        "sutun": ad, "agirlik": agirliklar[ad], "teyit_bekliyor": "agirliklar" in teyit,
        "aciklama": params["agirliklar"].get("_not")})[0] for ad in SUTUNLAR]
    sonuc["kurallar.notlar"] = [tek("kurallar.notlar", {
        "not_adi": ad, "esik": esik, "teyit_bekliyor": "notlar" in teyit,
        "aciklama": params.get("_notlar_aciklama")})[0] for ad, esik in params["notlar"]]
    return sonuc


def _son_kimlikler(kayit, kalite):
    """Kalite satırı olan son gecelik ve son dönem sonu çalışması (başlangıç anına göre; kimlik
    metninin sonundaki rastgele ek sırayı belirlemez); çalışma kaydı yoksa en büyük kimlik."""
    kimlik = kalite["calisma_kimligi"].astype(str)
    ozet = None if kayit is None else kayit[(kayit["kaynak"] == OZET) & kayit[
        "calisma_kimligi"].astype(str).isin(set(kimlik))]
    if ozet is None or ozet.empty:
        return [kimlik.max()]
    ozet = ozet.assign(_bas=pd.to_datetime(ozet["baslangic"])).sort_values("_bas")
    return [str(ozet.loc[ozet["tur"] == t, "calisma_kimligi"].iloc[-1])
            for t in ("GECELIK", "DONEM_SONU") if (ozet["tur"] == t).any()]


def veri(tablolar):
    kayit, sonuc = tablolar.get("calisma_kaydi"), {}
    if kayit is not None and not kayit.empty:
        gece = kayit[kayit["tur"] == "GECELIK"]
        ozet = kayit[kayit["kaynak"] == OZET].sort_values("baslangic", ascending=False)
        if not gece.empty:
            son_kimlik = gece.sort_values("baslangic")["calisma_kimligi"].iloc[-1]
            son = gece[(gece["calisma_kimligi"] == son_kimlik) & (gece["kaynak"] != OZET)]
            son = son.assign(son_basarili=[gecmis.son_basarili(kayit, ad, "2200-01-01")[0]
                                           for ad in son["kaynak"]],
                             sistem=[KAYNAKLAR.get(ad, {}).get("sistem") for ad in son["kaynak"]])
            sonuc["veri.kaynaklar"] = kayitlar("veri.kaynaklar", son)
        sonuc["veri.calismalar"] = kayitlar("veri.calismalar", ozet.head(15))
    kalite = tablolar.get("kalite_sonucu")
    if kalite is not None and not kalite.empty:
        # Son gecelik ve son dönem sonu çalışması (kimlik başlangıç zamanıyla; çekim tarihi değil).
        son_kalite = kalite[kalite["calisma_kimligi"].isin(_son_kimlikler(kayit, kalite))]
        sonuc["veri.kalite"] = kayitlar("veri.kalite", son_kalite[son_kalite["durum"] != "GECTI"])
    celiski = tablolar.get("olay_celiski")
    sonuc["veri.celiski_ozet"] = tek("veri.celiski_ozet", {})
    if celiski is not None:
        sira = [ad for ad in CELISKI_SIRASI if ad in celiski.columns]
        secilen = celiski.sort_values(sira, ascending=[ad in CELISKI_SIRASI[2:] for ad in sira],
                                      kind="mergesort").head(CELISKI_EN_COK)
        sonuc["veri.celiski"] = kayitlar("veri.celiski", secilen)
        sonuc["veri.celiski_ozet"] = tek("veri.celiski_ozet", {"toplam": len(celiski),
                                                        "gosterilen": len(secilen)})
    return sonuc
'''

DOSYALAR["sunum_ortak.py"] = r'''"""Her sayfa yanıtındaki ortak bileşenler: üst şerit (ortak.durum) ve ekran adları (ortak.adlar).

Şerit: gösterilen verinin kesiti, hesap sürümü ve gölge durumu son BAŞARILI geceden (ekrandaki
tabloları seçen tanım: hat.gecmis.son_basarili_gece), son kararlar son gecelik ve son dönem
sonu çalışmasından. Gölge kriter bazındadır: parametreyle açılan gölge iki kriteri, yedek yolun
zorunlu gölgesi yalnız Kriter 1'i kapsar. Okunamayan tablolar, geçersiz parametre ve son gecede
bağlantısı beklenen kaynaklar da şeride gelir. Ekran adları params.json gorunum bölümündendir
(sistem, branş, alt başlık ve mevcut alan adları); branşın sırası renk paletindeki yeridir.
"""
import pandas as pd

from avukat_perf.mantik import dogru_mu
from avukat_perf.params_sema import GORUNUM
from avukat_perf.sema import SISTEMLER
from avukat_perf.surum import hesap_surumu
from arayuz.temel import tek, topla
from hat import gecmis
from hat.calisma import OZET

BEKLENIYOR = "KAYNAK_BEKLENIYOR"


def _son_karar(kayit, tur):
    """Türün (GECELIK, DONEM_SONU) son özet satırının kararı; başlangıç anına göre."""
    if kayit is None or kayit.empty:
        return None
    ozet = kayit[(kayit["kaynak"] == OZET) & (kayit["tur"] == tur)]
    if ozet.empty:
        return None
    return ozet.assign(_bas=pd.to_datetime(ozet["baslangic"])).sort_values("_bas")[
        "durum"].iloc[-1]


def ortak_durum(tablolar, params, okunamayan=(), hatalar=()):
    """okunamayan: arka ucun okuyamadığı tablolar; hatalar: parametre doğrulamasının iletileri.
    Sonuçların hesap sürümü o gecenin kaydındandır; parametre ya da kod sonra değiştiyse
    kural_degisti doğrudur (geçersiz parametrede söylenmez: önce parametre düzeltilmelidir)."""
    kayit = tablolar.get("calisma_kaydi")
    son = gecmis.son_basarili_gece(kayit)
    if son is None:  # hiç başarılı gece yok: parametredeki gölge
        k1 = k2 = dogru_mu((params.get("uyari") or {}).get("golge_mod"))
    else:
        k2 = dogru_mu(son.get("golge"))
        k1 = k2 or dogru_mu(son.get("golge_zorunlu"))
    ozet = {"golge_mod": k1 or k2, "golge_ilk_islem": k1, "golge_dava_acma": k2,
            "kural_degisti": False,
            "acik_kirmizi": topla(tablolar.get("sonuc_sure_ozet"), "acik_kirmizi"),
            "son_karar": _son_karar(kayit, "GECELIK"),
            "son_donem_karari": _son_karar(kayit, "DONEM_SONU"),
            "okunamayan": sorted(okunamayan), "parametre_hatasi": "; ".join(hatalar) or None,
            "bekleyen_kaynaklar": []}
    if son is not None:
        surum = son.get("hesap_surumu")
        gece = kayit[(kayit["calisma_kimligi"] == son["calisma_kimligi"]) &
                     (kayit["kaynak"] != OZET) & (kayit["durum"] == BEKLENIYOR)]
        ozet.update(kesit=son["cekim_tarihi"], son_guncelleme=son["bitis"], hesap_surumu=surum,
                    bekleyen_kaynaklar=sorted(gece["kaynak"].astype(str)),
                    kural_degisti=not hatalar and isinstance(surum, str)
                    and surum != hesap_surumu(params))
    return tek("ortak.durum", ozet)


def adlar(params):
    """Ekran adları: tur (sistem, brans, alt_baslik, mevcut_alan), kod, ad ve branşta sira
    (gorunum.brans_adlari listesindeki yeri, 1'den; renk paletindeki yeri)."""
    gorunum = params.get(GORUNUM) or {}
    sistem = gorunum.get("sistem_adlari") or {}
    satirlar = [("sistem", kod, sistem.get(kod) or kod, None) for kod in SISTEMLER]
    satirlar += [("brans", oge[0], oge[1], sira + 1) for sira, oge in
                 enumerate(gorunum.get("brans_adlari") or []) if len(oge) == 2]
    for tur, alan in (("alt_baslik", "alt_baslik_adlari"), ("mevcut_alan", "mevcut_alan_adlari")):
        satirlar += [(tur, kod, ad, None) for kod, ad in (gorunum.get(alan) or {}).items()]
    return [tek("ortak.adlar", dict(zip(("tur", "kod", "ad", "sira"), satir)))[0]
            for satir in satirlar]
'''

DOSYALAR["sunum_siralama.py"] = r'''"""Genel Bakış'taki avukat sıralama tablosu ve avukat listesinin sırası.

Liste birleşik puana göre (puansız en sonda), tablo genel sıraya göre (sırasız en sonda).
gerceklesen_beklenen: tahsilat sonucunun gerçekleşen ÷ beklenen oranı (tahsilat ÷ rücu tutarı
olan tahsilat_orani ile karıştırılmasın). Yeterli veri işareti tahsilat ve süre sonucundan.
"""
from avukat_perf.mantik import dogru_mu
from arayuz.temel import kayitlar, secili


def _avukatlar(tablolar):
    birlesik, avukat = tablolar.get("sonuc_birlesik"), tablolar.get("model_avukat")
    if birlesik is None:
        return None
    if avukat is not None:
        birlesik = birlesik.merge(avukat[["avukat_kodu", "unvan", "calisma_durumu"]],
                                  on="avukat_kodu", how="left")
    puan = birlesik["birlesik_puan"].fillna(-1)
    return birlesik.assign(_puan=puan).sort_values(["_puan", "avukat_kodu"],
                                                   ascending=[False, True]).drop(columns="_puan")


YETERLI = {"tahsilat": "sonuc_tahsilat_avukat", "sure": "sonuc_sure"}  # yeterli veri işareti


def _yeterli(t, kod, tablo):
    """Avukatın sütun sonucundaki yeterli veri işareti (sonuç yoksa boş)."""
    sonuc = secili(t(tablo), "avukat_kodu", kod)
    return None if sonuc is None or sonuc.empty else dogru_mu(sonuc["yeterli"].iloc[0])


def avukat_tablosu(tablolar):
    tablo = _avukatlar(tablolar)
    if tablo is None:
        return []
    tahsilat, portfoy = tablolar.get("sonuc_tahsilat_avukat"), tablolar.get("sonuc_portfoy")
    if tahsilat is not None:  # gerçekleşen ÷ beklenen (tahsilat ÷ rücu değil: tahsilat_orani)
        tablo = tablo.merge(tahsilat[["avukat_kodu", "oran", "yeterli"]].rename(columns={
            "oran": "gerceklesen_beklenen", "yeterli": "tahsilat_yeterli"}), on="avukat_kodu",
            how="left")
    sure = tablolar.get("sonuc_sure")
    if sure is not None:
        tablo = tablo.merge(sure[["avukat_kodu", "yeterli"]].rename(columns={
            "yeterli": "sure_yeterli"}), on="avukat_kodu", how="left")
    if portfoy is not None:
        aktif = portfoy.groupby("avukat_kodu", as_index=False)["aktif_dosya"].sum()
        tablo = tablo.merge(aktif, on="avukat_kodu", how="left")
    sira = tablo["genel_sira"].fillna(10 ** 6)
    tablo = tablo.assign(_sira=sira).sort_values(["_sira", "avukat_kodu"]).drop(columns="_sira")
    return kayitlar("genel.avukat_tablosu", tablo)
'''

DOSYALAR["sunum_sure.py"] = r'''"""Süre Takibi sayfası verisi: seviye sayıları, dosya listesi, bayrak olayları, e-posta özeti.

Filtresiz liste açık dönemleri (izlenen, sarı, turuncu, kırmızı) ve düşüm tarihi süre puanı
penceresine düşen dönemleri (hesapta işaretlenir: pencerede_dusum) içerir. Seviye seçilirse o
seviyedeki bütün dönemler listelenir (kapanan, sonlanan, kapsam dışı ve nedeni dahil). En ağır
seviye ve en uzun süre önce, en çok 500 satır. secim içindeki kriter, seviye ve avukat
filtreleri sınırdan önce uygulanır; hesap yapılmaz.
Filtre bileşeni sınırdan önceki toplamı ve ölçülen dönemi olan bütün avukatları verir. Olaylar
gösterilen dönemlerin olayları ve filtreye uyan bütün dönemlerin en yeni SON_OLAY olayıdır;
bunlar son_sira (1 en yeni) taşır, ekran "Son Bayrak Olayları"nı yalnız bu sırayla basar. Eşit
tarihte sıra olayın kalıcı anahtarıyla belirlenir (satır sırasından bağımsız).
"""
import pandas as pd

from avukat_perf.mantik import dogru_seri
from avukat_perf.olay import kaynakli
from avukat_perf.ortak import gun
from arayuz import dagilim_sure
from arayuz.temel import kayitlar, seviye_sirala

ACIK_DONEM = ("IZLENIYOR", "SARI", "TURUNCU", "KIRMIZI")  # listede her zaman olan seviyeler
EN_COK = 500
SON_OLAY = 30
FILTRE = {"kriter": "kriter", "seviye": "seviye", "avukat": "avukat_kodu"}


def _birlesik(tablolar):
    parcalar = [tablolar[ad].assign(kriter=kriter) for ad, kriter in
                (("sonuc_k1", "K1"), ("sonuc_k2", "K2")) if tablolar.get(ad) is not None]
    return pd.concat(parcalar, ignore_index=True) if parcalar else None


def _olaylar(olay, tum, liste):
    """Gösterilen dönemlerin olayları ile filtreye uyan dönemlerin en yeni olayları; olaylar
    dönemin bugünkü esas kaynağından (yedek yoldan geçişte eski kaynağın olayları gösterilmez)."""
    anahtar = ["dosya_no", "avukat_kodu", "atama_tarihi", "kriter", "esas_kaynagi"]
    olay = kaynakli(olay).assign(atama_tarihi=gun(olay["atama_tarihi"]))
    tum, liste = kaynakli(tum), kaynakli(liste)

    def eslesen(donemler):
        return olay.merge(donemler[anahtar].assign(atama_tarihi=gun(donemler["atama_tarihi"])),
                          on=anahtar)
    yeni = eslesen(tum).sort_values(["olay_tarihi"] + anahtar + ["seviye"], ascending=[False] + [
        True] * (len(anahtar) + 1), kind="mergesort").head(SON_OLAY)
    yeni = yeni.assign(son_sira=range(1, len(yeni) + 1))
    secilen = pd.concat([yeni, eslesen(liste)], ignore_index=True).drop_duplicates(
        anahtar + ["seviye"])
    return secilen.sort_values(anahtar + ["olay_tarihi"])


def sure(tablolar, secim=None):
    tablo = _birlesik(tablolar)
    if tablo is None:
        return {}
    sayilar = tablo.groupby(["kriter", "seviye"]).size().rename("adet").reset_index()
    sonuc = {"sure.seviyeler": kayitlar("sure.seviyeler", sayilar),
             "sure.ilk_islem_dagilim": kayitlar("sure.ilk_islem_dagilim", dagilim_sure.k1_sure(
                 tablolar.get("sonuc_k1")))}
    # Sütunu taşımayan (aktarımdan önceki gecenin) tabloda yalnız açık dönemler listelenir.
    pencere = tablo.get("pencerede_dusum", pd.Series(False, index=tablo.index))
    tum = tablo if (secim or {}).get("seviye") else tablo[
        tablo["seviye"].isin(ACIK_DONEM) | dogru_seri(pencere)]
    # Seçenek: ölçülen (kapsam dışı olmayan) dönemi bulunan bütün avukatlar; sulh avukatı yok.
    olculen = tablo.loc[tablo["seviye"] != "KAPSAM_DISI", "avukat_kodu"]
    avukatlar = sorted(olculen.dropna().unique())
    for ad, sutun in FILTRE.items():
        if (secim or {}).get(ad):
            tum = tum[tum[sutun] == secim[ad]]
    liste = seviye_sirala(tum).head(EN_COK)
    sonuc["sure.filtre"] = [{"toplam": len(tum), "gosterilen": len(liste),
                             "avukatlar": [str(kod) for kod in avukatlar]}]
    sonuc["sure.liste"] = kayitlar("sure.liste", liste)
    olay = tablolar.get("bayrak_olay")
    if olay is not None:
        sonuc["sure.olaylar"] = kayitlar("sure.olaylar", _olaylar(olay, tum, liste))
    eposta = tablolar.get("sonuc_eposta")
    if eposta is not None:
        # Gönderim kriter bazındadır (yedek yolda yalnız Kriter 1 gölgede): avukatın gönderilecek
        # ve gönderilmeyecek gecikmeleri ayrı satırda sayılır.
        gonder = dogru_seri(eposta["gonderilecek"])
        say = pd.crosstab([eposta["avukat_kodu"], gonder.rename("gonderilecek")],
                          eposta["seviye"])
        say = say.reindex(columns=["SARI", "TURUNCU", "KIRMIZI"], fill_value=0)
        say.columns = ["sari", "turuncu", "kirmizi"]
        say = say.assign(toplam=say.sum(axis=1)).reset_index()
        sonuc["sure.eposta"] = kayitlar("sure.eposta", say[
            ["avukat_kodu", "sari", "turuncu", "kirmizi", "toplam", "gonderilecek"]].sort_values(
                ["kirmizi", "toplam"], ascending=False))
    return sonuc
'''

DOSYALAR["sunum_tahsilat.py"] = r'''"""Tahsilat bileşenlerinin sunumu: avukat kartındaki branş tablosu ve aylık tahsilat tablosu."""
import pandas as pd

from avukat_perf.mantik import dogru_mu
from avukat_perf.portfoy import ATANAMAYAN
from arayuz.temel import kayitlar, secili

AYLIK_TABLO_AY = 12  # tabloda gösterilen son ay sayısı (sütun)


def brans_tablosu(tablolar, kod):
    """Avukatın branş satırları (olgun dosya sayısına göre azalan) ve bütün dosyaları için
    toplam satırı (toplam=True; avukatın tahsilat sonucundan)."""
    brans = secili(tablolar.get("sonuc_tahsilat_brans"), "avukat_kodu", kod)
    if brans is None or brans.empty:
        return []
    parcalar = [brans.sort_values(["n", "brans"], ascending=[False, True]).assign(toplam=False)]
    genel = secili(tablolar.get("sonuc_tahsilat_avukat"), "avukat_kodu", kod)
    if genel is not None and not genel.empty:
        parcalar.append(genel.assign(brans=None, toplam=True))
    return kayitlar("avukat.brans", pd.concat(parcalar, ignore_index=True, sort=False))


def aylik_tablo(aylik):
    """Avukat × ay tahsilatı: hesap anındaki ay ızgarasının son AYLIK_TABLO_AY ayı, tahsilatsız ay
    sıfır. toplam: avukatın bu aylardaki toplamı (sıralama için); avukata yazılamayan en sonda."""
    if aylik is None or aylik.empty or "ilk_ay" not in aylik.columns:
        return []
    ilk, son = aylik["ilk_ay"].iloc[0], aylik["son_ay"].iloc[0]
    aylar = [str(ay) for ay in pd.period_range(ilk, son, freq="M")][-AYLIK_TABLO_AY:]
    kismi = son if dogru_mu(aylik["son_ay_kismi"].iloc[0]) else None
    tutar = aylik[aylik["ay"].isin(aylar)].groupby(["avukat_kodu", "ay"])["tutar"].sum()
    izgara = pd.MultiIndex.from_product([sorted(aylik["avukat_kodu"].unique()), aylar],
                                        names=["avukat_kodu", "ay"])
    tablo = tutar.reindex(izgara, fill_value=0.0).reset_index()
    tablo["toplam"] = tablo.groupby("avukat_kodu")["tutar"].transform("sum")
    sira = tablo["toplam"].where(tablo["avukat_kodu"] != ATANAMAYAN, -float("inf"))
    tablo = tablo.assign(kismi=tablo["ay"] == kismi, _s=sira)
    return kayitlar("genel.aylik_avukat", tablo.sort_values(
        ["_s", "avukat_kodu", "ay"], ascending=[False, True, True]))
'''

DOSYALAR["temel.py"] = r'''"""Sunum yardımcıları: JSON'a uygun değer, sözleşmeye göre kayıt listesi, küçük toplamlar.

Bir bileşene giden her kayıt tam olarak sözleşmedeki alanları taşır: fazlası gönderilmez,
eksiği None olur. Tarih "YYYY-AA-GG" (saat varsa "YYYY-AA-GG SS:DD") metnine çevrilir.
"""
import math

import pandas as pd

from avukat_perf.mantik import dogru_mu, dogru_seri
from arayuz.sozlesme import BILESENLER, SECIMLIK_SUTUNLAR
from hat import butunluk, gecmis, model

SEVIYE_SIRASI = {"KIRMIZI": 0, "TURUNCU": 1, "SARI": 2, "IZLENIYOR": 3}
# Sonuç tablolarının mantıksal sütunları: Dataiku boş değerli mantıksal sütunu metin okur.
MANTIKSAL = ("golge", "golge_zorunlu", "gonderilecek", "esas_tarihi_bilinmiyor", "dusum",
             "pencerede_dusum", "yeterli", "son_ay_kismi", "yil_ici")
SOZLESME_SUTUNLARI = {}  # tablo -> bileşenlerin okuduğu, tabloda bulunması gereken sütunlar
for _bilesen in BILESENLER.values():
    for _tablo, _sutunlar in _bilesen["kaynak"].items():
        SOZLESME_SUTUNLARI.setdefault(_tablo, set()).update(
            set(_sutunlar) - set(SECIMLIK_SUTUNLAR.get(_tablo, ())))


def deger(ham):
    """Pandas/numpy değerini JSON'a uygun Python değerine çevirir."""
    if ham is None or (isinstance(ham, float) and math.isnan(ham)):
        return None
    if not isinstance(ham, (list, dict, str)) and pd.isna(ham):
        return None
    if isinstance(ham, pd.Timestamp):
        return ham.strftime("%Y-%m-%d" if ham == ham.normalize() else "%Y-%m-%d %H:%M")
    if hasattr(ham, "item"):
        ham = ham.item()
        return None if isinstance(ham, float) and math.isnan(ham) else ham
    return ham


def kayitlar(bilesen, tablo):
    """Tablo satırlarını bileşenin alanlarıyla kayıt listesine çevirir."""
    alanlar = BILESENLER[bilesen]["alanlar"]
    if tablo is None or tablo.empty:
        return []
    tablo = tablo.assign(**{ad: None for ad in alanlar if ad not in tablo.columns})
    return [{ad: deger(veri) for ad, veri in zip(alanlar, satir)}
            for satir in tablo[alanlar].itertuples(index=False, name=None)]


def ay_izgarasi(tablo, secilen, sutunlar):
    """Aylık değerler (secilen) hesap anındaki takvim ayı ızgarasına yayılır: tahsilatsız ay
    sıfır, kesitte bitmeyen son ay kismi. Izgara tablonun kendisindedir (ilk_ay, son_ay,
    son_ay_kismi); bu sütunları taşımayan eski tabloda yalnız kaydı olan aylar gösterilir."""
    toplam = secilen.groupby("ay")[sutunlar].sum()
    kismi_ay = None
    if len(tablo) and "ilk_ay" in tablo.columns:
        ilk, son = tablo["ilk_ay"].iloc[0], tablo["son_ay"].iloc[0]
        aylar = [str(ay) for ay in pd.period_range(ilk, son, freq="M")]
        toplam = toplam.reindex(aylar, fill_value=0)
        kismi_ay = son if dogru_mu(tablo["son_ay_kismi"].iloc[0]) else None
    sonuc = toplam.rename_axis("ay").reset_index()
    return sonuc.assign(kismi=sonuc["ay"] == kismi_ay)


def tek(bilesen, sozluk):
    """Tek kayıtlık bileşen (özet göstergeler)."""
    return [{ad: deger(sozluk.get(ad)) for ad in BILESENLER[bilesen]["alanlar"]}]


def topla(tablo, sutun):
    return None if tablo is None else float(tablo[sutun].sum())


def oran(pay, payda):
    return None if pay is None or not payda else pay / payda


def secili(tablo, sutun, deger_):
    """tablo[sutun] == deger_ satırları; tablo yoksa None."""
    return None if tablo is None else tablo[tablo[sutun] == deger_]


def seviye_sirala(tablo, ek=("sure_gun",)):
    """Seviye ağırlığına (KIRMIZI önce) ve ek sütunlara (azalan) göre sıralar."""
    sira = tablo["seviye"].map(SEVIYE_SIRASI).fillna(9)
    tablo = tablo.assign(_sira=sira)
    return tablo.sort_values(["_sira"] + list(ek), ascending=[True] + [False] * len(ek)).drop(
        columns="_sira")


def guncel_tablolar(tablolar):
    """Son başarılı gecede üretilmemiş, başka bir gecenin etiketini taşıyan ya da o gecenin
    yazdığı satır sayısını tutmayan sonuc_, model_ ve çelişki tabloları None sayılır; hiç
    başarılı gece yoksa hiçbiri gösterilmez. Sözleşmenin okuduğu bir sütunu (gruplamaya bağlı
    SECIMLIK_SUTUNLAR hariç) taşımayan sonuc_, model_ ve dönem tablosu da None'dır (tek kural).
    Bayrak olaylarından yalnız başarılı gecelerde yazılanlar kalır. Örnek: dava takip
    bağlantısı kaldırılırsa eski sonuc_k1 durur ama gösterilmez; yarıda kesilen gecenin yeni
    tahsilat tablosu eski birleşik puanla yan yana çıkmaz.
    """
    kayit = mantiksal(tablolar.get("calisma_kaydi"))
    uretilen, kimlik = gecmis.son_sayilar(kayit), gecmis.son_kimlik(kayit)

    def suz(ad, tablo):
        if ad == "bayrak_olay":
            return butunluk.basarili_satirlar(tablo, kayit)
        if tablo is not None and SOZLESME_SUTUNLARI.get(ad, set()) - set(tablo.columns) and \
                ad.startswith(("sonuc_", "model_", "birlesik_donem")):
            return None  # eski biçim (kod aktarımından önceki gece): ilk gecede yeniden yazılır
        if not ad.startswith(("sonuc_", "model_")) and ad != "olay_celiski":
            return tablo
        uygun = ad in uretilen and model.etiket_uygun(tablo, kimlik, uretilen[ad])
        return tablo if uygun else None
    return {ad: mantiksal(suz(ad, tablo)) for ad, tablo in tablolar.items()}


def mantiksal(tablo):
    """MANTIKSAL sütunları gerçek True/False yapar ("false" metni True okunmaz)."""
    if tablo is None:
        return None
    sutunlar = [ad for ad in MANTIKSAL if ad in tablo.columns]
    return tablo.assign(**{ad: dogru_seri(tablo[ad]) for ad in sutunlar}) if sutunlar else tablo
'''

OZET = {
    "__init__.py": "180884201fa7",
    "dagilim_brans.py": "6d981014966d",
    "dagilim_sure.py": "1d385c908881",
    "sozlesme.py": "788c83f38b9a",
    "sozlesme_alanlar.py": "5cf3bf36e111",
    "sozlesme_dagilim.py": "b787157a3384",
    "sozlesme_dislanan.py": "9e8c1f51c021",
    "sozlesme_ortak.py": "7a30703ce18d",
    "sozlesme_tahsilat.py": "76d022f0a369",
    "sunum.py": "ce2faada5be7",
    "sunum_avukat.py": "567b876fa527",
    "sunum_dagilim.py": "b33b8da2f3ae",
    "sunum_kural.py": "e0d031b85b9b",
    "sunum_ortak.py": "58d2277a878c",
    "sunum_siralama.py": "63e093f7bdc7",
    "sunum_sure.py": "9eb9908b970c",
    "sunum_tahsilat.py": "8d4d08cf0249",
    "temel.py": "5b55d93d7242",
}


# ---------- kütüphaneye yazma ----------
def _ozet(metin):
    satirlar = [satir.rstrip() for satir in metin.splitlines()]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    return hashlib.sha256("\n".join(satirlar).encode("utf-8")).hexdigest()[:12]


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
