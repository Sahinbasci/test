"""Yerel ortam: tablolar CSV, ham arşiv klasör, gizli değerler sözlük ya da ortam değişkeni.

Testler, sentetik veri provası ve arayüz önizlemesi için. Dataiku'da aynı arayüzü
hat.dataiku_ortam.DataikuOrtam sağlar: tablo_oku, tablo_yaz, veri_kumesi_oku, dosya_yolu,
gizli, arsiv_var, arsiv_yaz, ayar_oku, ayar_oku_varsa. CSV türleri kaybetmesin diye her
tablonun yanında sütun türleri (tarih, sayi, mantiksal, metin) ayrı bir dosyada tutulur. Ayar
dosyaları json_oku ile okunur (iki ortamda aynı): yinelenen anahtar hatadır.
"""
import json
import os

import pandas as pd

from hat.veri_kumeleri import AYAR_KLASORU


def json_oku(metin, ad):
    """JSON ayar metni; aynı düzeyde yinelenen anahtar hatadır. json.loads son değeri alırdı: ek
    dosyada iki kez yazılan bölümün ilk bloğu (ör. teyit edilen ölçek) sessizce kaybolurdu."""
    def tekil(ciftler):
        anahtarlar = [anahtar for anahtar, _ in ciftler]
        cift = sorted(set(a for a in anahtarlar if anahtarlar.count(a) > 1))
        if cift:
            raise ValueError("{}: yinelenen anahtar {}".format(ad, ", ".join(cift)))
        return dict(ciftler)
    return json.loads(metin, object_pairs_hook=tekil)


def _tur(seri):
    if str(seri.dtype).startswith("datetime"):
        return "tarih"
    if str(seri.dtype) == "bool":
        return "mantiksal"
    return "sayi" if pd.api.types.is_numeric_dtype(seri) else "metin"


class YerelOrtam(object):
    """kok klasörü altında tablolar/, ham/, ayarlar/ ve kaynak dosyaları."""

    def __init__(self, kok, gizliler=None, kaynak_kok=None, ayar_kok=None):
        self.kok = kok
        self._gizliler = gizliler or {}
        self._kaynak_kok = kaynak_kok or kok
        self._ayar_kok = ayar_kok or os.path.join(kok, AYAR_KLASORU)

    def _yol(self, *parcalar):
        return os.path.join(self.kok, *parcalar)

    def tablo_oku(self, ad):
        yol = self._yol("tablolar", ad + ".csv")
        if not os.path.exists(yol):
            return None
        with open(self._yol("tablolar", ad + ".turler.json"), encoding="utf-8") as dosya:
            turler = json.load(dosya)
        tablo = pd.read_csv(yol, dtype=str, keep_default_na=False, na_values=[""])
        for sutun, tur in turler.items():
            if tur == "tarih":
                tablo[sutun] = pd.to_datetime(tablo[sutun])
            elif tur == "sayi":
                tablo[sutun] = pd.to_numeric(tablo[sutun])
            elif tur == "mantiksal":
                tablo[sutun] = tablo[sutun].map({"True": True, "False": False})
        return tablo

    def tablo_yaz(self, ad, tablo):
        os.makedirs(self._yol("tablolar"), exist_ok=True)
        tablo.to_csv(self._yol("tablolar", ad + ".csv"), index=False)
        turler = {str(sutun): _tur(tablo[sutun]) for sutun in tablo.columns}
        with open(self._yol("tablolar", ad + ".turler.json"), "w", encoding="utf-8") as dosya:
            json.dump(turler, dosya, ensure_ascii=False)

    def veri_kumesi_oku(self, ad):
        return pd.read_csv(self._yol("veri_kumeleri", ad + ".csv"), dtype=str,
                           keep_default_na=False, na_values=[""])

    def dosya_yolu(self, yol):
        return yol if os.path.isabs(yol) else os.path.join(self._kaynak_kok, yol)

    def gizli(self, ad):
        if ad in self._gizliler:
            return self._gizliler[ad]
        if ad in os.environ:
            return os.environ[ad]
        raise KeyError("gizli değer bulunamadı: " + ad)

    def arsiv_var(self, yol):
        return os.path.exists(self._yol(yol))

    def arsiv_yaz(self, yol, bayt):
        hedef = self._yol(yol)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        with open(hedef, "wb") as dosya:
            dosya.write(bayt)

    def ayar_oku(self, ad):
        with open(os.path.join(self._ayar_kok, ad), encoding="utf-8-sig") as dosya:
            return json_oku(dosya.read(), ad)

    def ayar_oku_varsa(self, ad):
        yol = os.path.join(self._ayar_kok, ad)
        return self.ayar_oku(ad) if os.path.exists(yol) else None
