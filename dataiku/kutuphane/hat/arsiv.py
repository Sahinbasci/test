"""Ham arşiv: her kaynağın gelen verisi, değiştirilmeden, kaynak ve çekim gününe göre yazılır.

Yol: ham/kaynak=<ad>/cekim_tarihi=<YYYY-AA-GG>/calisma=<kimlik>/veri.<parquet|csv.gz>,
yanında bilgi.json (satır sayısı, sütunlar, biçim, yöntem). Var olan dosyanın üzerine
yazılmaz; aynı gece ikinci çalışma yeni kimlikle ayrı klasöre yazar. Parquet motoru
(pyarrow) yoksa ya da tablo Parquet'e çevrilemiyorsa sıkıştırılmış CSV yazılır.
"""
import gzip
import io
import json


def yol(kaynak, cekim_tarihi, calisma_kimligi, dosya_adi):
    return "ham/kaynak={}/cekim_tarihi={}/calisma={}/{}".format(
        kaynak, cekim_tarihi, calisma_kimligi, dosya_adi)


def _bayt(tablo):
    tampon = io.BytesIO()
    try:
        tablo.to_parquet(tampon, index=False)
        return "parquet", tampon.getvalue()
    except Exception:  # Parquet motoru yok ya da karışık türlü sütun: CSV'ye düş
        return "csv.gz", gzip.compress(tablo.to_csv(index=False).encode("utf-8"))


def yaz(ortam, kaynak, tablo, cekim_tarihi, calisma_kimligi, ek_bilgi):
    """Ham tabloyu arşive yazar, veri dosyasının yolunu döndürür."""
    bicim, veri = _bayt(tablo)
    veri_yolu = yol(kaynak, cekim_tarihi, calisma_kimligi, "veri." + bicim)
    if ortam.arsiv_var(veri_yolu):
        raise ValueError("arşiv dosyası zaten var, üzerine yazılmaz: " + veri_yolu)
    ortam.arsiv_yaz(veri_yolu, veri)
    bilgi = dict(ek_bilgi, satir_sayisi=len(tablo), sutunlar=[str(s) for s in tablo.columns],
                 bicim=bicim)
    metin = json.dumps(bilgi, ensure_ascii=False, default=str, indent=2)
    ortam.arsiv_yaz(yol(kaynak, cekim_tarihi, calisma_kimligi, "bilgi.json"),
                    metin.encode("utf-8"))
    return veri_yolu
