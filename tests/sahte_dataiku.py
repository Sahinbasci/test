"""Dataiku'nun sahte karşılığı: testlerde dataiku paketi yerine geçer.

Dataiku'nun davranışlarını canlandırır: saat dilimsiz tarih UTC sayılıp saat dilimli geri
gelir; infer_with_pandas=True okumada kimlikteki baştaki sıfırlar silinir (pandas tahmini);
infer_with_pandas=False okumada boş değerli tamsayı sütunu (tamsayi_bos kümesindeki veri
kümeleri) int_as_float verilmeden ValueError verir; bool_as_str mantıksal değerleri metne
çevirir; gizliler yalnız with_secrets=True ile döner.
Gerçek davranış aktarımdan sonra dataiku/kontrol/aktarim_kontrol.py ile ayrıca denenir.
"""
import io
import types

import pandas as pd


class VeriKumesi(object):
    depo = {}
    eski_surum = False
    bozuk = set()  # okunurken geçici hata veren veri kümeleri
    tamsayi_bos = set()  # boş değerli tamsayı sütunu olan veri kümeleri

    def __init__(self, ad, project_key=None, ignore_flow=False):
        self.ad = ad

    def read_schema(self, raise_if_empty=True):
        if self.ad in self.bozuk:
            raise IOError("bağlantı kesildi")
        if self.ad not in self.depo:
            if raise_if_empty:
                raise Exception("dataset has no schema")
            return []
        return [{"name": ad} for ad in self.depo[self.ad].columns]

    def get_dataframe(self, infer_with_pandas=True, **secenek):
        if not infer_with_pandas and self.eski_surum:
            raise TypeError("get_dataframe() got an unexpected keyword argument")
        if (not infer_with_pandas and self.ad in self.tamsayi_bos
                and not secenek.get("int_as_float")):
            raise ValueError("Integer column has NA values")
        tablo = self.depo[self.ad].copy()
        if infer_with_pandas:
            tablo = pd.read_csv(io.StringIO(tablo.to_csv(index=False)))
        if secenek.get("bool_as_str"):  # mantıksal sütun metin gelir ("true" / "false")
            for sutun in tablo.columns:
                if tablo[sutun].map(lambda deger: isinstance(deger, bool)).any():
                    tablo[sutun] = tablo[sutun].map(
                        lambda deger: str(deger).lower() if isinstance(deger, bool) else deger)
        return tablo

    def write_with_schema(self, tablo):
        kopya = tablo.copy()
        for sutun in kopya.columns:
            if str(kopya[sutun].dtype).startswith("datetime64[ns]") and kopya[sutun].dt.tz is None:
                kopya[sutun] = kopya[sutun].dt.tz_localize("UTC")
        self.depo[self.ad] = kopya


class Klasor(object):
    dosyalar = {}

    def __init__(self, ad, project_key=None, ignore_flow=False):
        self.ad = ad

    def list_paths_in_partition(self, partition=""):
        return sorted(yol for (klasor, yol) in self.dosyalar if klasor == self.ad)

    def upload_data(self, yol, veri):
        self.dosyalar[(self.ad, "/" + yol.lstrip("/"))] = veri

    def get_download_stream(self, yol):
        return io.BytesIO(self.dosyalar[(self.ad, "/" + yol.lstrip("/"))])


class _KumeYardimcisi(object):
    def __init__(self, ad):
        self.ad = ad

    def with_store_into(self, baglanti):
        return self

    def create(self):
        Proje.olusturulan.append(self.ad)


class Proje(object):
    """Web uygulaması ve senaryo ayarı yoktur: aktarım kontrolü bunları "okunamadı" yazar.
    Kurulum not defteri için veri kümesi ve klasör listesi ve oluşturma vardır."""
    olusturulan = []

    def list_webapps(self):
        return []

    def list_datasets(self):
        return [{"name": ad} for ad in VeriKumesi.depo]

    def list_managed_folders(self):
        return [{"name": ad} for ad in sorted({klasor for klasor, _ in Klasor.dosyalar})]

    def new_managed_dataset(self, ad):
        return _KumeYardimcisi(ad)

    def create_managed_folder(self, ad, folder_type=None, connection_name=None):
        Proje.olusturulan.append(ad)

    def get_scenario(self, kimlik):
        raise KeyError(kimlik)


class Istemci(object):
    def get_auth_info(self, with_secrets=False):
        bilgi = {"authIdentifier": "deneme"}
        if with_secrets:  # gerçek API gizlileri yalnız bu bayrakla verir
            bilgi["secrets"] = [{"key": "API_ANAHTARI", "value": "gizli-deger"}]
        return bilgi

    def get_default_project(self):
        return Proje()


DEGISKENLER = {}


def modul():
    modul = types.ModuleType("dataiku")
    modul.Dataset, modul.Folder = VeriKumesi, Klasor
    modul.api_client = Istemci
    modul.get_custom_variables = lambda: dict(DEGISKENLER)
    VeriKumesi.depo, VeriKumesi.eski_surum, Klasor.dosyalar = {}, False, {}
    Proje.olusturulan = []
    VeriKumesi.bozuk, VeriKumesi.tamsayi_bos = set(), set()
    return modul
