"""Gecelik çalışma: Dataiku senaryosunun "Python kodu çalıştır" adımına yapıştırılır.

Senaryo: AVUKAT_PERF_GECELIK · tetikleyici: her gün 02:00 · tek adım: bu kod.
Akış (hat.akis.gecelik): kaynaklar (kaynaklar.json'daki yönteme göre) → ham arşiv
(ham_arsiv klasörü, MinIO) → kalite kapısı → geçerse ortak model, gözlemler, puanlar ve
sonuç veri kümeleri. Bu adım iş kuralı içermez; yalnız kütüphaneyi çağırır.

Karar KALDI ise hesap yapılmaz, son geçerli sonuç korunur ve adım hata vererek senaryoyu
başarısız işaretler (Dataiku bildirimi, Grafana alarmı). KAYNAK_BEKLENIYOR hata değildir:
zorunlu kaynaklar (çekirdek sistem dosya ve atama logları) bağlanana kadar beklenen durumdur;
dosya bazında tahsilat hareketi gelmezse yalnız Tahsilat sütunu kaynak bekler. Ayarlar
"ayarlar" yönetilen klasöründeki params.json ve kaynaklar.json; aynı
klasörde params_ek.json ya da kaynaklar_ek.json varsa üzerine birleştirilir (hat.ayar).
"""
from hat import akis, ayar
from hat.dataiku_ortam import DataikuOrtam

ortam = DataikuOrtam()
ozet = akis.gecelik(ortam, ayar.yukle(ortam, "kaynaklar"), ayar.yukle(ortam, "params"))
print("Gecelik çalışma:", ozet)
if ozet["karar"] == "KALDI":
    raise Exception("Kalite kapısı geçmedi; son geçerli sonuç korundu. Ayrıntı kalite_sonucu "
                    "veri kümesinde, çalışma " + ozet["calisma_kimligi"])
