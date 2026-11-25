"""Testlerin ortak yardımcıları. Dosya okuma burada yapılır, çekirdekte değil."""
import json
import os
import tempfile

import pandas as pd

from araclar import yerel_calistir
from hat.ortam import YerelOrtam
from sentetik import uretici

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUTUPHANE = os.path.join(KOK, "dataiku", "kutuphane")
DEGISKENLER = os.path.join(KOK, "dataiku", "degiskenler")
ATAMA_SUTUNLARI = ["dosya_no", "avukat_kodu", "brans", "atama_tarihi", "bitis_tarihi",
                   "bitis_nedeni", "atama_turu"]


def params_yukle():
    yol = os.path.join(DEGISKENLER, "params.json")
    with open(yol, encoding="utf-8") as dosya:
        return json.load(dosya)


DORT_SUTUN = ["tahsilat", "sure", "kalite", "davranis"]


def dort_sutunlu(params=None):
    """Süre ve Performans'ın da birleşik puana girdiği ayar (ilk fazdan sonra; varsayılan
    params.json ilk fazdır: Süre girmez). Dört sütunun mekaniğini sınayan testler içindir."""
    params = json.loads(json.dumps(params_yukle() if params is None else params))
    params["birlesik_sutunlar"] = list(DORT_SUTUN)
    return params


def agirlik_karsilastirmasi(tahsilat, sure, kalite, davranis):
    """Hedef ağırlıkları (yüzde) veren tam tutarlı ikili karşılaştırmalar (params agirliklar)."""
    deger = {"tahsilat": tahsilat, "sure": sure, "kalite": kalite, "davranis": davranis}
    adlar = list(deger)
    return {"{}/{}".format(a, b): deger[a] / float(deger[b])
            for i, a in enumerate(adlar) for b in adlar[i + 1:]}


def prova_ortami(dosya=600, avukat=12):
    """Geçici klasörde küçük sentetik veri ve yerel ortam: (ortam, ayarlar, params, kök).

    Ayarlar yerel çalıştırıcıdaki gibi: depodaki varsayılan + sentetik ek dosyaları (hat.ayar).
    """
    kok = tempfile.mkdtemp()
    uretici.uret(os.path.join(kok, "sentetik", "veri"), dosya, avukat)
    ayarlar, params = yerel_calistir.senaryo_ayarlari("tam")
    return YerelOrtam(os.path.join(kok, "calisma"), kaynak_kok=kok), ayarlar, params, kok


def yayin_tabanini_dusur(params):
    """Küçük provada süre puanı gerçekten çıksın diye süre tabanları düşürülür (yalnız test):
    veri kapsamı tabanı (en_az_kapsam, %80) küçük provada aşılmaz, birleşik puan yayımlanmaz ve
    dönem testleri boş değerleri karşılaştırırdı; yeterli_dosya (30) düşürülünce "Yeterli veri
    yok" uyarısı da kalkar. Tahsilat ve beklenen düşüm tabanının varsayılanı zaten düşüktür
    (en_az_olgun_dosya 1, en_az_beklenen 0)."""
    params["sure_puani"].update(yeterli_dosya=1, en_az_kapsam=0.01)
    return params


def hata_bekle(hata_turu, fonk, *argumanlar):
    """Fonksiyon beklenen hatayı verirse True döner."""
    try:
        fonk(*argumanlar)
    except hata_turu:
        return True
    return False


def atama_tablosu(satirlar):
    """(dosya, avukat, branş, atama[, bitiş, bitiş nedeni, atama türü]) satırlarından tablo.

    Verilmeyen alanlar: bitiş boş, bitiş nedeni boş, atama türü NORMAL.
    """
    varsayilan = (None, None, "NORMAL")
    tam = [tuple(satir) + varsayilan[len(satir) - 4:] for satir in satirlar]
    return pd.DataFrame(tam, columns=ATAMA_SUTUNLARI)


def esas_tablosu(esaslar):
    """{dosya_no: esas_ilk_giris} sözlüğünden esas tablosu."""
    return pd.DataFrame(list(esaslar.items()), columns=["dosya_no", "esas_ilk_giris"])


def bekleme_tablosu(satirlar):
    """(dosya, avukat, başlangıç, bitiş) satırlarından haklı bekleme tablosu."""
    return pd.DataFrame(satirlar, columns=["dosya_no", "avukat_kodu", "baslangic", "bitis"])
