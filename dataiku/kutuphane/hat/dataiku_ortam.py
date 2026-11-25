"""Dataiku ortamı: tablolar Dataiku veri kümesi, ham arşiv yönetilen klasör (MinIO'ya
bağlı S3 bağlantısı), gizli değerler Dataiku kullanıcı gizlileri (Profil > Gizliler).

Senaryo "Python kodu çalıştır" adımında, not defterinde ve web uygulaması arka ucunda
çalışır (tariflerdeki giriş/çıkış bildirimi kısıtı bu bağlamlarda yoktur). Aktarımdan sonra
dataiku/kontrol/aktarim_kontrol.py not defterinde her yöntem bir kez denenir.
Okuma veri kümesi şemasındaki türlerle yapılır (infer_with_pandas=False): pandas'ın tür
tahmini "000123" gibi kimlikleri sayıya çevirip baştaki sıfırları siler. Boş değerli tamsayı
sütununda tamsayılar ondalık (int_as_float), boş değerli mantıksal sütun metin (bool_as_str)
okunur; üçü de olmazsa okuma hata verir (pandas tahminine düşülmez). Parametreyi tanımayan eski
sürümde varsayılan okumaya düşülür ve uyarı yazılır. Şeması boş (hiç yazılmamış) veri kümesi "ilk
çalışma" sayılır; başka her okuma hatası yukarı iletilir: yalnız eklenen bir tablo (çalışma
kaydı, gözlem, bayrak olayı, dönem yayını) geçici bir hatada boş sanılıp üzerine yazılırsa
geçmiş silinirdi. Saat dilimli tarih sütunu UTC'ye çevrilip saat dilimi kaldırılır: kütüphane saat
dilimsiz yazar, Dataiku bunu UTC sayar; böylece okunan değer yazılanla aynıdır.
Kaynak dosyaları (yöntem "dosya") "kaynak_dosyalari" yönetilen klasöründen okunur.
Yöntem adları Dataiku Python API'sine dayanır; sürüm farkında yalnız bu dosya değişir.
"""
import os
import shutil
import tempfile

from hat.ortam import json_oku
from hat.veri_kumeleri import ARSIV_KLASORU, AYAR_KLASORU, DOSYA_KLASORU


def _sema_turleriyle(veri_kumesi, ad):
    for secenek in ({"infer_with_pandas": False},
                    {"infer_with_pandas": False, "int_as_float": True},
                    {"infer_with_pandas": False, "int_as_float": True, "bool_as_str": True}):
        try:
            return veri_kumesi.get_dataframe(**secenek)
        except TypeError:  # eski sürüm: parametre tanınmıyor
            print("şema türleriyle okunamadı, varsayılan okuma: " + ad)
            return veri_kumesi.get_dataframe()
        except ValueError:  # boş değerli tamsayı ya da mantıksal sütun: bir sonraki seçenek
            continue
    raise ValueError(ad + ": şema türleriyle okunamadı (boş değerli tamsayı ya da mantıksal "
                     "sütun olabilir); pandas tahminine düşülmez, kimliklerin sıfırları silinirdi")


def _utc_saf(tablo):
    for sutun in tablo.columns:
        if getattr(tablo[sutun].dtype, "tz", None) is not None:
            tablo[sutun] = tablo[sutun].dt.tz_convert("UTC").dt.tz_localize(None)
    return tablo


class DataikuOrtam(object):
    """arsiv_klasoru: ham arşiv için Dataiku yönetilen klasörünün adı."""

    def __init__(self, arsiv_klasoru=ARSIV_KLASORU):
        import dataiku
        self._dataiku = dataiku
        self._klasor = dataiku.Folder(arsiv_klasoru)

    def tablo_oku(self, ad):
        """Kütüphanenin yazdığı tablo; şeması boş (hiç yazılmamış) veri kümesi için None.

        Okuma hatası (bağlantı, yetki, olmayan veri kümesi) yukarı iletilir; gece durur.
        """
        veri_kumesi = self._dataiku.Dataset(ad)
        if not veri_kumesi.read_schema(raise_if_empty=False):
            return None
        return _utc_saf(_sema_turleriyle(veri_kumesi, ad))

    def tablo_yaz(self, ad, tablo):
        self._dataiku.Dataset(ad).write_with_schema(tablo)

    def veri_kumesi_oku(self, ad):
        """Kaynak veri kümesi (yöntem "dataiku"); tarih dönüşümü kalite kapısında yapılır."""
        return _sema_turleriyle(self._dataiku.Dataset(ad), ad)

    def dosya_yolu(self, yol):
        """Kaynak dosyasını yönetilen klasörden geçici dosyaya indirir, yolunu döndürür."""
        hedef = os.path.join(tempfile.mkdtemp(), os.path.basename(yol))
        klasor = self._dataiku.Folder(DOSYA_KLASORU)
        with klasor.get_download_stream(yol) as akis, open(hedef, "wb") as dosya:
            shutil.copyfileobj(akis, dosya)
        return hedef

    def gizli(self, ad):
        bilgi = self._dataiku.api_client().get_auth_info(with_secrets=True)
        for gizli in bilgi.get("secrets", []):
            if gizli.get("key") == ad:
                return gizli.get("value")
        if ad in os.environ:
            return os.environ[ad]
        raise KeyError("Dataiku kullanıcı gizlisi bulunamadı: " + ad)

    def arsiv_var(self, yol):
        yollar = self._klasor.list_paths_in_partition()
        return "/" + yol.lstrip("/") in set("/" + y.lstrip("/") for y in yollar)

    def arsiv_yaz(self, yol, bayt):
        self._klasor.upload_data("/" + yol.lstrip("/"), bayt)

    def ayar_oku(self, ad, klasor=AYAR_KLASORU):
        """Yönetilen klasördeki JSON ayar dosyası (ör. params.json); Windows'ta kaydedilmiş
        dosyanın baştaki BOM işareti sorun çıkarmaz."""
        with self._dataiku.Folder(klasor).get_download_stream(ad) as akis:
            return json_oku(akis.read().decode("utf-8-sig"), ad)

    def ayar_oku_varsa(self, ad, klasor=AYAR_KLASORU):
        """Ek ayar dosyası (ör. params_ek.json) klasörde varsa içeriği, yoksa None."""
        yollar = self._dataiku.Folder(klasor).list_paths_in_partition()
        if "/" + ad not in set("/" + y.lstrip("/") for y in yollar):
            return None
        return self.ayar_oku(ad, klasor)
