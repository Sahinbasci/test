"""Dönem sonu çalışmasının hazırlık kontrolü, açıklama metinleri ve yayın dışındaki
sonuçlarının kayda geçmesi.

Model tablosu okunamazsa ya da hesap veya yayın hata verirse de calisma_kaydi'na DONEM_SONU
özet satırı ve kalite_sonucu'na çalışmanın kimliğiyle denetim satırı yazılır (Veri Durumu ve
izleme bu çalışmayı görür). Son başarılı gecenin yazdığı model tablosu okunamıyor ya da başka
bir gecenin etiketini taşıyorsa kesiktir: KALDI (VERI_KAYBI). O gece hiç yazılmadıysa
(kaynağı bekleniyor) KAYNAK_BEKLENIYOR.
"""
import pandas as pd

from avukat_perf import sema
from avukat_perf.kalite import SONUC
from avukat_perf.surum import hazirlik_surumu
from hat import calisma, gecmis
from hat.model import GOZLEMLER

# Model tablosunun kaynağı; kaynağı zorunlu olan model tablosu dönem hesabı için zorunludur.
MODEL_KAYNAGI = {"dosya": "dosya", "atama_donemi": "atama_log", "hareket": "tahsilat_hareketi",
                 "bekleme": "bekleme", "degerlendirme": "degerlendirme", "avukat": "avukat",
                 "k2_goruntu": "k2_goruntu"}
ZORUNLU = tuple(ad for ad, kaynak in MODEL_KAYNAGI.items() if kaynak in sema.zorunlu_kaynaklar())


def _kontrol(kimlik, kontrol, deger, aciklama):
    return pd.DataFrame([("donem", kontrol, "KALDI", deger, 0, aciklama)],
                        columns=SONUC).assign(calisma_kimligi=kimlik)


def model_eksik(ortam, onceki, mdl, ozet):
    """Son gecenin yazdığı bir model ya da gözlem tablosu okunamıyorsa (isteğe bağlı olanlar
    dahil: kesik tahsilat hareketi Tahsilat'ı sessizce "kaynak bekleniyor" yayımlardı) ya da
    zorunlu model tablosu yoksa kayda geçirip kararı döndürür; tablolar tamsa None."""
    uretilen = gecmis.son_sayilar(onceki)
    adlar = [("model_" + ad, ad) for ad in MODEL_KAYNAGI] + [(ad, ad) for ad in GOZLEMLER]
    kesik = [tablo for tablo, ad in adlar if tablo in uretilen and mdl[ad] is None]
    eksik = [ad for ad in ZORUNLU if mdl[ad] is None]
    if not kesik and not eksik:
        return None
    kimlik, kesit = ozet["calisma_kimligi"], ozet["cekim_tarihi"]
    if kesik:
        metin = "son gecenin model tablosu okunamadı ya da kesik: " + ", ".join(kesik)
        ozet["aciklama"] = ozet["aciklama"] + " · VERI_KAYBI · " + metin
        calisma.kaydet(ortam, onceki, [], "KALDI", ozet)
        calisma.kalite_ekle(ortam, [_kontrol(kimlik, "MODEL_TABLOSU", len(kesik), metin)],
                            kesit)
        return "KALDI"
    ozet["aciklama"] = ozet["aciklama"] + " · kaynak bekleniyor: " + ", ".join(eksik)
    calisma.kaydet(ortam, onceki, [], "KAYNAK_BEKLENIYOR", ozet)
    return "KAYNAK_BEKLENIYOR"


def hata(ortam, onceki, ozet, ileti):
    """Hesap ya da yayın hatası: KALDI ve HESAP_HATASI kayda geçer (hata sonra iletilir)."""
    ozet["aciklama"] = ozet["aciklama"] + " · HESAP_HATASI · " + ileti
    calisma.kaydet(ortam, onceki, [], "KALDI", ozet)
    calisma.kalite_ekle(ortam, [_kontrol(ozet["calisma_kimligi"], "HESAP_HATASI", 1, ileti)],
                        ozet["cekim_tarihi"])


METIN = {"sure": "süre", "kalite_davranis": "kalite ve davranış", "KAYNAK_BEKLENIYOR":
         "kaynak bekleniyor", "TEYIT_BEKLIYOR": "ölçek teyidi bekleniyor", "YENI": "yeni sürüm",
         "DUZELTME": "düzeltme sürümü", "DEGISMEDI": "değişmedi", None: "yapılmadı"}


def hazirlik_kontrolu(onceki, params):
    """Son gecenin model tabloları güncel hazırlık kuralı ve koduyla mı üretildi.

    Değilse yayın yapılmaz: içerik eski kuralla hazırlanmışken yayın yeni sürümü taşırdı."""
    gece = gecmis.son_basarili_gece(onceki)
    kayitli = None if gece is None else gece.get("hazirlik_surumu")
    fark = int(isinstance(kayitli, str) and kayitli != hazirlik_surumu(params))
    return pd.DataFrame([("donem", "HAZIRLIK_SURUMU", "KALDI" if fark else "GECTI", fark, 0,
                          "hazırlık kuralı ya da kod son gecelik çalışmadan sonra değişti; "
                          "önce gecelik çalışma gerekir" if fark else "")], columns=SONUC)
