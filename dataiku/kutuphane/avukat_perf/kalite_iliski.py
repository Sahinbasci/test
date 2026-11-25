"""Kaynaklar arası denetimler: anahtar ilişkisi ve tahsilat raporuyla mutabakat."""
import re

import pandas as pd

from avukat_perf.kalite import SONUC, satir
from avukat_perf.ortak import gun, tek_gun


def iliski(kontrol, ana, alt, anahtar="dosya_no", en_cok_oran=None, agirlik=None):
    """alt tablodaki anahtarların (tek alan ya da alan demeti) ana tabloda olmayanları: UYARI.

    Hiçbiri eşleşmiyorsa (anahtar biçimleri farklı, ör. D-000001 ile D000001) ya da eşleşmeyen
    oranı en_cok_oran'ı aşıyorsa KALDI. agirlik sütunu verilirse oran o sütunun mutlak
    değeriyle de tartılır (tahsilat tutarı); büyük olan kullanılır."""
    alanlar = [anahtar] if isinstance(anahtar, str) else list(anahtar)
    eslesme = alt[alanlar].astype(object).merge(ana[alanlar].astype(object).drop_duplicates(),
                                                how="left", indicator=True)
    yetim = pd.Series((eslesme["_merge"] == "left_only").values, index=alt.index)
    sayi = int(yetim.sum())
    oran = sayi / float(len(alt)) if len(alt) else 0.0
    if agirlik is not None and len(alt):
        tutar = pd.to_numeric(alt[agirlik], errors="coerce").abs().fillna(0.0)
        oran = max(oran, float(tutar[yetim].sum()) / tutar.sum() if tutar.sum() > 0 else 0.0)
    hepsi = 0 < len(alt) == sayi
    asti = en_cok_oran is not None and oran > en_cok_oran
    durum = "GECTI" if sayi == 0 else ("KALDI" if hepsi or asti else "UYARI")
    aciklama = "ana tabloda bulunmayan {} (oran {:.4f}{})".format(
        ", ".join(alanlar), oran, "" if en_cok_oran is None else ", en çok {}".format(en_cok_oran))
    if hepsi:
        aciklama += "; hiçbiri eşleşmiyor, anahtar biçimini kontrol et"
    return pd.DataFrame([("iliski", kontrol, durum, sayi, 0, aciklama)], columns=SONUC)


def _donem(deger):
    """Rapor dönemini YYYY-AA biçimine getirir. Saatli ya da saat dilimli tarih (2026-10-31T21:00Z)
    önce yerel güne çevrilir: ay başı yerel gece yarısı UTC'de önceki aya düşerdi."""
    metin = str(deger).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d", metin):
        yerel = gun(pd.Series([metin]), zorla=True).iloc[0]
        return metin if pd.isna(yerel) else yerel.strftime("%Y-%m")
    for kalip, bicim in ((r"^(\d{4})-(\d{2})(-\d{2})?$", "{0}-{1}"),
                         (r"^(\d{4})(\d{2})$", "{0}-{1}"), (r"^(\d{2})\.(\d{4})$", "{1}-{0}")):
        uyan = re.match(kalip, metin)
        if uyan:
            return bicim.format(*uyan.groups())
    return metin


def mutabakat(hareketler, rapor_toplam, params, kesit=None):
    """Ay başına toplam tahsilat ile tahsilat raporu toplamı arasındaki göreli fark.

    Avukat bazlı karşılaştırma yapılmaz: tahsilat raporunun avukata atıf yöntemi teyit
    edilmedi. Yalnız rapor_toplam'da bulunan aylar karşılaştırılır; rapor avukat, branş ya da
    başka kırılımla gelse de ay toplamı alınır. Dönem YYYY-AA, YYYY-AA-GG, YYYYAA ya da AA.YYYY
    olabilir; başka biçim olduğu gibi kalır (eşleşmez, fark görünür). Kesitin ayı (içinde
    bulunulan, kısmi ay) yalnız uyarıdır: rapor ile hareketler farklı saatte yenilenebilir.
    Açıklama tutar içermez (kalite sonucu ve izleme panosu paylaşılabilir kalsın); göreli fark
    deger sütunundadır.
    """
    ay = gun(hareketler["hareket_tarihi"]).dt.strftime("%Y-%m")
    bizim = hareketler["tutar"].groupby(ay).sum()
    rapor = rapor_toplam["tahsilat_toplami"].groupby(
        rapor_toplam["donem"].map(_donem)).sum()
    sonuclar, kesit_ayi = [], None if kesit is None else tek_gun(kesit).strftime("%Y-%m")
    for donem, toplam in rapor.items():
        fark = abs(bizim.get(donem, 0.0) - toplam) / max(abs(toplam), 1.0)
        sonuclar.append(satir("mutabakat", "TAHSILAT:" + donem, round(fark, 6),
                               params["kalite"]["mutabakat_tolerans"],
                               "hesaplanan ile rapor toplamı arasındaki göreli fark",
                               uyari=donem == kesit_ayi))
    return pd.DataFrame(sonuclar, columns=SONUC)
