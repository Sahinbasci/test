"""Kaynak okuma ve kalite kapısı: her kaynağı oku → ham arşiv → normalle → denetle.

Okuma, arşiv ya da biçim hatası o kaynağı KALDI yapar; hata türü ve iletisi çalışma kaydına
ve kalite sonucuna yazılır (ileti satır değeri içermez). Kaynaklar arası ilişki denetimi
gelen bütün kaynakların anahtarlarını (dosya ve avukat) ana kaynakla karşılaştırır; hiçbir
anahtar eşleşmiyorsa (biçim farkı, ör. D-000001 / D000001) ya da eşleşmeyen oranı
kalite.iliski_en_cok_yetim_orani'nı aşıyorsa (tahsilat hareketinde tutarla da tartılır) gece
durur. Haklı bekleme (dosya, avukat) çifti ve avukat listesi yalnız tümden uyuşmazlıkta durur.
"""
import pandas as pd

from avukat_perf import hazirlik, kalite, kalite_iliski, sema
from hat import arsiv, ayar as ayar_modulu, calisma, gecmis, kaynak


def kaynaklari_oku(ortam, ayarlar, params, cekim, onceki, kimlik, simdi):
    """(kapıyı geçen tablolar, kaynak başına kayıt satırları, kalite sonuçları)."""
    tablolar, kayitlar, sonuclar = {}, [], []
    for ad in sema.KAYNAKLAR:
        ayar = ayar_modulu.kaynak_ayari(ayarlar, ad)  # sistem ayarı + kaynak ayarı
        _, onceki_satir = gecmis.son_basarili(onceki, ad, simdi)
        kayit = calisma.satir(kimlik, "GECELIK", ad, ayar.get("yontem", "bekliyor"), simdi,
                              cekim)
        try:
            ham = kaynak.cek(ayar, ortam, baglam(cekim))
            if ham is None:
                kayitlar.append(dict(kayit, durum="KAYNAK_BEKLENIYOR"))
                continue
            bilgi = dict({alan: ayar.get(alan) for alan in kaynak.NORMALLEME},
                         yontem=ayar["yontem"])
            yol = arsiv.yaz(ortam, ad, ham, cekim.date(), kimlik, bilgi)
            normal = kaynak.normalle(ad, ham, ayar)
            temiz, sonuc = kalite.denetle(ad, normal, cekim, params, onceki_satir)
        except Exception as hata:  # bağlantı, yetki, arşiv ya da biçim: kayda geçer, gece durur
            metin = ileti(hata)
            kayitlar.append(dict(kayit, durum="KALDI", kalite_sonucu="KALDI", aciklama=metin))
            sonuclar.append(kalite.cekim_hatasi(ad, metin).assign(calisma_kimligi=kimlik))
            continue
        sonuclar.append(sonuc.assign(calisma_kimligi=kimlik))
        tablolar[ad] = temiz
        # Kapı normalleştirilmiş satırı sayar (geniş değerlendirme uzun biçime açılır).
        kayitlar.append(dict(kayit, satir_sayisi=len(normal), kalite_sonucu=kalite.karar(sonuc),
                             arsiv_yolu=yol))
    return tablolar, kayitlar, sonuclar


def ileti(hata):
    return "{}: {}".format(type(hata).__name__, hata)[:300]


def baglam(cekim):
    """API ayarındaki yer tutucular. Her kaynak her gece tam görüntü verir (artımlı çekim ilk
    görülme gününü bozardı); bu yüzden önceki çekimin tarihi sunulmaz."""
    return {"kesit": str(cekim.date()), "cekim_tarihi": str(cekim.date())}


# (kontrol, alt kaynak, ana kaynak, anahtar, oran sınırı uygulanır mı): alt kaynağın anahtarları
# ana kaynakta olmalı.
ILISKILER = (("ATAMA_DOSYA", "atama_log", "dosya", "dosya_no", True),
             ("HAREKET_DOSYA", "tahsilat_hareketi", "dosya", "dosya_no", True),
             ("ESAS_DOSYA", "esas_goruntu", "dosya", "dosya_no", True),
             ("TAKIP_DOSYA", "takip", "dosya", "dosya_no", True),
             ("SUREC_DOSYA", "k2_goruntu", "dosya", "dosya_no", True),
             ("BEKLEME_DOSYA", "bekleme", "dosya", "dosya_no", True),
             ("BEKLEME_AVUKAT", "bekleme", "atama_log", "avukat_kodu", True),
             ("BEKLEME_ATAMA", "bekleme", "atama_log", ("dosya_no", "avukat_kodu"), False),
             ("DEGERLENDIRME_AVUKAT", "degerlendirme", "atama_log", "avukat_kodu", True),
             ("AVUKAT_AVUKAT", "avukat", "atama_log", "avukat_kodu", False))


def iliskiler(tablolar, params, kesit=None):
    """Kaynaklar arası anahtar eşleşmesi (gelen isteğe bağlı kaynaklar dahil) ve mutabakat.

    Mutabakat puana giren hareketlerle yapılır (tahsilat sayılan hareket türleri); kesitin
    ayındaki fark uyarıdır (rapor ve hareketler farklı saatte yenilenebilir)."""
    oran = params["kalite"]["iliski_en_cok_yetim_orani"]
    sonuclar = [kalite_iliski.iliski(kontrol, tablolar[ana], tablolar[alt], anahtar,
                                     oran if oranli else None,
                                     "tutar" if alt == "tahsilat_hareketi" else None)
                for kontrol, alt, ana, anahtar, oranli in ILISKILER
                if tablolar.get(alt) is not None]
    if tablolar.get("rapor_avukat_toplam") is None:
        return sonuclar
    if tablolar.get("tahsilat_hareketi") is None:  # dosya bazında hareket yok: mutabakat yok
        return sonuclar + [pd.DataFrame([kalite.satir(
            "mutabakat", "TAHSILAT_HAREKETI_YOK", 1, uyari=True,
            aciklama="dosya bazında tahsilat hareketi gelmedi; rapor toplamıyla mutabakat "
                     "yapılmadı, Tahsilat sütunu kaynak bekliyor")], columns=kalite.SONUC)]
    hareket = hazirlik.tahsilat_hareketleri(tablolar["tahsilat_hareketi"], params["hazirlik"])
    sonuclar.append(kalite_iliski.mutabakat(hareket, tablolar["rapor_avukat_toplam"], params,
                                            kesit))
    return sonuclar
