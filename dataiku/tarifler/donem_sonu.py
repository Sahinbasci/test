"""Dönem sonu: Dataiku senaryosunun "Python kodu çalıştır" adımına yapıştırılır.

Senaryo: AVUKAT_PERF_DONEM_SONU · tetikleyici: her ayın 1'i 06:00 (gecelik çalışmadan sonra).
Bir önceki takvim ayını yayımlar (hat.donem_akisi.calistir): dönem kesitinde sütun puanları
→ sonuç kontrolleri → sürümlü yayın (puan_donem, birlesik_donem). Yayımlanmış dönem
değiştirilmez; içerik ya da kurallar değiştiyse yeni sürüm eklenir.

Belirli bir dönemi yeniden hesaplatmak (düzeltme) için senaryo elle çalıştırılmadan önce proje
değişkenine "donem" yazılır, ör. {"donem": "2026-10"}; iş bitince değişken silinir. Silinmesi
unutulursa yeni ay yine yayımlanır (hat.donem_akisi.yayimlanacak_donemler).
Ay sonunu kapsayan başarılı bir gecelik çalışma yoksa yayın yapılmaz ve adım hata verir.
Yayımlanmayan her dönem (kontrol geçmedi, model tablosu kesik, kaynak bekleniyor ya da hesap
hatası) calisma_kaydi'nda DONEM_SONU satırıyla görülür; kaynak bekleniyor dışındakilerin nedeni
kalite_sonucu'nda da aynı kimlikle yazılır.
"""
import dataiku

from hat import ayar, calisma, donem_akisi
from hat.dataiku_ortam import DataikuOrtam

ortam = DataikuOrtam()
params = ayar.yukle(ortam, "params")
degisken = dataiku.get_custom_variables().get("donem")
donemler = donem_akisi.yayimlanacak_donemler(degisken, calisma.simdi(),
                                             ortam.tablo_oku("puan_donem"))
hatalar = []
for donem_adi in donemler:
    ozet = donem_akisi.calistir(ortam, params, donem_adi)
    print("Dönem sonu:", donem_adi, ozet)
    if ozet["karar"] != "GECTI":
        hatalar.append("{} {} (çalışma {})".format(donem_adi, ozet["karar"],
                                                    ozet["calisma_kimligi"]))
if degisken:
    print("Not: 'donem' proje değişkeni tanımlı ({}); düzeltme bittiyse silin.".format(degisken))
if hatalar:
    raise Exception("Yayımlanmayan dönem: " + "; ".join(hatalar)
                    + ". Ayrıntı calisma_kaydi (DONEM_SONU) ve kalite_sonucu veri kümelerinde, "
                    "aynı çalışma kimliğiyle.")
