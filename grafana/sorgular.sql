-- Grafana izleme sorguları (PostgreSQL söz dizimi).
-- Kaynak tablolar: calisma_kaydi ve kalite_sonucu (Dataiku veri kümeleri, SQL bağlantısında).
-- ${calisma_tablosu} ve ${kalite_tablosu} pano değişkenleridir; Dataiku'daki gerçek tablo
-- adıyla doldurulur (veri kümesi > Ayarlar > Bağlantı > Tablo; çoğunlukla proje anahtarı
-- önekli, ör. "AVUKAT_PERF_calisma_kaydi").
-- Özet satırı: kaynak = '*', tur = 'GECELIK'; durum = gecenin kararı
-- (GECTI | KALDI | KAYNAK_BEKLENIYOR). Kaynak satırlarında durum BASARILI | KALDI |
-- KAYNAK_BEKLENIYOR | HESAPLANMADI; KALDI gecesinde kapıdan geçmiş kaynak da KALDI yazılır,
-- kaynağın kendi kapı sonucu kalite_sonucu'ndadır (GECTI | KALDI). Tarih karşılaştırmaları gün
-- düzeyindedir (cekim_tarihi); saat dilimi farkı alarmı etkilemez.
-- Alarm sorguları (A1-A3) uyarı kuralına yapıştırılırken ${calisma_tablosu} yerine gerçek tablo
-- adı yazılır (ör. "AVUKAT_PERF_calisma_kaydi"): Grafana uyarı kuralları pano değişkenini
-- çözmez. Kural önizlemesi tek satır döndürmelidir.

-- P1 Son gecelik çalışma
SELECT cekim_tarihi, durum, baslangic, bitis, calisma_kimligi
FROM ${calisma_tablosu}
WHERE kaynak = '*' AND tur = 'GECELIK'
ORDER BY baslangic DESC
LIMIT 1;

-- P2 Kaynak tazeliği: son başarılı çekim ve üzerinden geçen gün
SELECT kaynak,
       MAX(yontem) FILTER (WHERE baslangic = son_baslangic) AS yontem,
       MAX(cekim_tarihi) FILTER (WHERE durum = 'BASARILI') AS son_basarili_cekim,
       CURRENT_DATE - (MAX(cekim_tarihi) FILTER (WHERE durum = 'BASARILI'))::date AS gecen_gun,
       MAX(durum) FILTER (WHERE baslangic = son_baslangic) AS son_durum
FROM (SELECT *, MAX(baslangic) OVER (PARTITION BY kaynak) AS son_baslangic
      FROM ${calisma_tablosu}
      WHERE tur = 'GECELIK' AND kaynak <> '*') t
GROUP BY kaynak
ORDER BY gecen_gun DESC NULLS FIRST, kaynak;

-- P3 Gece kararları (zaman çizelgesi): 0 geçti, 1 kaynak bekleniyor, 2 kaldı
SELECT cekim_tarihi AS "time",
       CASE durum WHEN 'GECTI' THEN 0 WHEN 'KAYNAK_BEKLENIYOR' THEN 1 ELSE 2 END AS karar
FROM ${calisma_tablosu}
WHERE kaynak = '*' AND tur = 'GECELIK' AND $__timeFilter(cekim_tarihi)
ORDER BY 1;

-- P4 Kaynak başına satır sayısı
SELECT cekim_tarihi AS "time", kaynak AS metric, satir_sayisi AS value
FROM ${calisma_tablosu}
WHERE tur = 'GECELIK' AND kaynak <> '*' AND satir_sayisi IS NOT NULL
  AND $__timeFilter(cekim_tarihi)
ORDER BY 1;

-- P5 Son gecenin geçmeyen kalite denetimleri (geceyi durduran KALDI satırları önce)
SELECT kaynak, kontrol, durum, deger, esik, aciklama
FROM ${kalite_tablosu}
WHERE calisma_kimligi = (SELECT calisma_kimligi FROM ${calisma_tablosu}
                         WHERE kaynak = '*' AND tur = 'GECELIK'
                         ORDER BY baslangic DESC LIMIT 1)
  AND durum <> 'GECTI'
ORDER BY CASE durum WHEN 'KALDI' THEN 0 ELSE 1 END, kaynak, kontrol;

-- A1 Alarm: son iki günde tamamlanan gece yok (sonuç 0 ise alarm). Kaynak beklenirken
--    (KAYNAK_BEKLENIYOR) gece tamamlanmış sayılır. Kalan gece A2'de, kopan kaynak A3'te.
SELECT COUNT(*) AS gecen_gece
FROM ${calisma_tablosu}
WHERE kaynak = '*' AND tur = 'GECELIK' AND durum IN ('GECTI', 'KAYNAK_BEKLENIYOR')
  AND cekim_tarihi::date >= CURRENT_DATE - 1;

-- A2 Alarm: son gece kalite kapısından geçmedi (sonuç 1 ise alarm)
SELECT CASE WHEN durum = 'KALDI' THEN 1 ELSE 0 END AS kaldi
FROM ${calisma_tablosu}
WHERE kaynak = '*' AND tur = 'GECELIK'
ORDER BY baslangic DESC
LIMIT 1;

-- A3 Alarm: daha önce okunup kendi kapısını geçmiş bir kaynak bir günden uzun süredir gelmiyor
--    (sonuç 0'dan büyükse alarm). Kaynağın kapı sonucuna bakılır: başka bir kaynak geceyi
--    durdurduğunda kapıdan geçmiş kaynaklar bayat sayılmaz.
SELECT COUNT(*) AS bayat_kaynak
FROM (SELECT kaynak, MAX(cekim_tarihi)::date AS son
      FROM ${calisma_tablosu}
      WHERE tur = 'GECELIK' AND kaynak <> '*' AND kalite_sonucu = 'GECTI'
      GROUP BY kaynak) t
WHERE CURRENT_DATE - son > 1;
