"""Alan anlamı denetimleri (kalite kapısının parçası): ters tarih, yer tutucu tarih, bilinen
değerler, gözlem doluluğu, hareket türü ve değerlendirme.

Her denetim (kontrol, değer, uyarı mı, açıklama) döndürür; satırı kalite.denetle kurar.
- Tarih denetimleri (ESKI_TARIH, TERS_TARIH, SAATSIZ_ATAMA) kalite_tarih.py'dedir.
- DEGER: dosya branşı kalite.bilinen_branslar'da değilse KALDI (yazım farkı sessizce varsayılan
  kurala düşerdi: oto eşiği, olgunluk süresi); süreç türü Kriter 2'nin süreç kodlarında değilse
  UYARI. Hareket türü ve değerlendirme alt başlığı tanımsızsa UYARI, hiçbiri tanımlı değilse KALDI.
- DOLULUK: gözlem kaynağı doluyken değer alanı hiçbir satırda dolu değilse KALDI (alan eşlemesi
  yanlış ya da alan gelmiyor; gece geçseydi ertesi gece bütün değerler o gün "ilk görülürdü").
- DISARIDA_TERS_KAYIT: tahsilat sayılmayan türde eksi tutarlı hareket: UYARI.
- OLCEK: tanımlı alt başlık puanı teyit edilmiş ölçeğin dışındaysa KALDI (mevcut alanlar ve
  tanımsız kodlar sınanmaz; hesapla aynı kural). PENCERE_DISI: pencere dışında kalan puanlı
  değerlendirme: UYARI. YINELENEN:degerlendiren: değerlendiren doluyken aynı anahtar: KALDI.
- YINELENEN:hareket_no: hareketin kaynak kimliği verilmişse tekil olmalı: KALDI. BOS_BAKIYE:
  Kriter 2 rücu kodlu dosyada açık bakiye boş: UYARI. SIFIR_RUCU: UYARI (tahsilatı sahibinin
  gerçekleşenine girer, beklentisi yoktur; ölçüt oranına girmez; evrenden çıkarılması Hukuk
  kararı bekliyor). NEGATIF_RUCU: KALDI. İletiler satır değeri içermez; yalnız sayı verir.
"""
import pandas as pd

from avukat_perf import kalite_tarih
from avukat_perf.kalite_davranis import olcek_disi, olcek_tanimli
from avukat_perf.kriter2 import SURECLER
from avukat_perf.ortak import tek_gun
from avukat_perf.params_sema import KALITE_DAVRANIS_SUTUNLARI
from avukat_perf.pencere import icinde

DOLULUK = {"esas_goruntu": ("esas_no",), "k2_goruntu": ("surec_turu", "dava_esas_no"),
           "takip": ("esas_no",)}


def _sayi(maske):
    return int(maske.sum())


def _hareket_denetimleri(temiz, turler):
    """Tahsilat sayılan türler verilmişse listede olmayan hareketler puana girmez."""
    if turler is None:
        return []
    disarida = ~temiz["hareket_turu"].isin(turler)
    hepsi = len(temiz) > 0 and bool(disarida.all())
    return [("DEGER:hareket_turu", _sayi(disarida), not hepsi,
             "hazirlik.tahsilat_hareket_turleri'nde olmayan tür; puana girmez" +
             ("; hiçbir hareket tahsilat sayılmıyor" if hepsi else "")),
            ("DISARIDA_TERS_KAYIT", _sayi(disarida & (temiz["tutar"] < 0)), True,
             "listede olmayan türde eksi tutarlı hareket; ters kayıt puandan düşülmez")]


def _degerlendirme_denetimleri(temiz, params, kesit):
    kd = params["kalite_davranis"]
    kodlar = [kod for ad in KALITE_DAVRANIS_SUTUNLARI for kod in kd["alt_basliklar"][ad]]
    bilinmeyen = temiz["alt_baslik"].notna() & ~temiz["alt_baslik"].isin(
        kodlar + list(kd["mevcut_alanlar"]))
    hepsi = len(temiz) > 0 and bool(bilinmeyen.all())
    anahtar = ["avukat_kodu", "degerlendirme_tarihi", "alt_baslik", "degerlendiren"]
    cift = temiz["degerlendiren"].notna() & temiz.duplicated(subset=anahtar, keep=False)
    disari = temiz["puan"].notna() & ~icinde(temiz["degerlendirme_tarihi"], tek_gun(kesit),
                                             kd["pencere_ay"])
    sonuc = [("DEGER:alt_baslik", _sayi(bilinmeyen), not hepsi,
              "alt başlıklarda ve mevcut alanlarda olmayan kod; puana girmez" +
              ("; hiçbir kod tanımlı değil" if hepsi else "")),
             ("YINELENEN:degerlendiren", _sayi(cift), False,
              "aynı değerlendiricinin aynı gün ve alt başlıkta birden çok kaydı (çift kayıt)"),
             ("PENCERE_DISI", _sayi(disari), True,
              "kalite_davranis.pencere_ay dışında kalan puanlı değerlendirme; puana girmez")]
    if olcek_tanimli(params):
        sonuc.append(("OLCEK:puan", _sayi(olcek_disi(temiz, kd)), False,
                      "ölçek dışında değerlendirme puanı"))
    return sonuc


def denetimler(kaynak, temiz, params, kesit):
    """Kaynağın alan anlamı denetimleri: [(kontrol, değer, uyarı, açıklama), ...]."""
    sonuc = kalite_tarih.denetimler(kaynak, temiz,
                                    pd.Timestamp(params["kalite"]["en_eski_tarih"]))
    sonuc += [("DOLULUK:" + ad, int(len(temiz) > 0 and not temiz[ad].notna().any()), False,
               "değer alanı hiçbir satırda dolu değil (alan eşlemesi yanlış olabilir; kaynakta "
               "veri yoksa yontem bekliyor yapılır)") for ad in DOLULUK.get(kaynak, ())]
    if kaynak == "dosya":
        bilinmeyen = temiz["brans"].notna() & ~temiz["brans"].isin(
            params["kalite"]["bilinen_branslar"])
        sonuc.append(("DEGER:brans", _sayi(bilinmeyen), False,
                      "kalite.bilinen_branslar'da olmayan branş: yazım farkıysa kaynak ayarında "
                      "deger_eslemesi, yeni branşsa bilinen_branslar"))
        bos = (temiz["rucu_kodu"] == params["kriter2"]["rucu_kodu"]) & temiz["acik_bakiye"].isna()
        sonuc.append(("BOS_BAKIYE", _sayi(bos), True, "Kriter 2 rücu kodlu dosyada açık bakiye "
                      "boş; koşul son bilinen durumla sürer"))
        sonuc.append(("SIFIR_RUCU", _sayi(temiz["rucu_tutari"] == 0), True,
                      "rücu tutarı sıfır; tahsilatı avukatın gerçekleşenine girer, beklentisi "
                      "yok (diğer avukatların ölçütüne girmez)"))
        sonuc.append(("NEGATIF_RUCU", _sayi(temiz["rucu_tutari"] < 0), False,
                      "rücu tutarı negatif (veri hatası ya da düzeltme kaydı)"))
    if kaynak == "tahsilat_hareketi":
        kimlik = temiz["hareket_no"]
        cift = kimlik.notna() & kimlik.duplicated(keep=False)
        sonuc.append(("YINELENEN:hareket_no", _sayi(cift), False,
                      "aynı hareket kimliği birden çok kez geldi"))
        sonuc += _hareket_denetimleri(temiz, params["hazirlik"]["tahsilat_hareket_turleri"])
    if kaynak == "k2_goruntu":
        bilinmeyen = temiz["surec_turu"].notna() & ~temiz["surec_turu"].isin(SURECLER)
        sonuc.append(("DEGER:surec_turu", _sayi(bilinmeyen), True,
                      "tanımsız süreç türü: " + ", ".join(SURECLER) + " beklenir"))
    if kaynak == "degerlendirme":
        sonuc += _degerlendirme_denetimleri(temiz, params, kesit)
    return sonuc
