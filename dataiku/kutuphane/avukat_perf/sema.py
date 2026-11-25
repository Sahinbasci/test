"""Veri sözleşmesi: entegrasyon katmanının her mantıksal kaynak için teslim etmesi gereken
tablo şeması (alan adları eşlendikten sonra).

Her alan (ad, tür, zorunlu); tür metin, tarih, zaman (saatiyle; aynı günün kayıtlarını
sıralamak için), sayi ya da mantiksal. Zorunlu alan boş olamaz. anahtar satırı tekil kılan
alanlardır; atama logunda log kaydının referansı da anahtardadır. gozlem True olan kaynak ilk
görülme günü sabitlenen görüntüdür: boş gelmesi geceyi durdurur. istege_bagli
True olan kaynak gelmese de gecelik çalışma sürer; o kaynağa bağlı hesap "kaynak bekleniyor"
durumunda kalır. yinelenen_uyari True olan kaynakta yinelenen anahtar geceyi durdurmaz, uyarıdır:
değerlendirmede değerlendirici alanı gelmeyebilir; aynı gün birden çok değerlendirme ortalanır
(değerlendiren doluyken tekrar çift kayıttır, kalite_alan KALDI verir). Takip bilgisinde dosya
başına birden çok takip satırı (icra, dava) olabilir; gözleme tek satır girer (hat.model).
Kaynaklar sistem koduna göre: cekirdek (dosya, atama_log, takip), tahsilat_raporu
(tahsilat_hareketi, rapor_avukat_toplam), degerlendirme (degerlendirme, avukat), dava_takip
(esas_goruntu, k2_goruntu), duzeltme (bekleme). Sistemlerin ekranda görünen adları yalnız
params.json içindeki gorunum.sistem_adlari bölümünden gelir.
"""
SISTEMLER = ("cekirdek", "tahsilat_raporu", "degerlendirme", "dava_takip", "duzeltme")

KAYNAKLAR = {
    "dosya": {"sistem": "cekirdek", "anahtar": ["dosya_no"], "alanlar": [
        ("dosya_no", "metin", True), ("brans", "metin", True), ("rucu_kodu", "metin", True),
        ("rucu_tutari", "sayi", True), ("acik_bakiye", "sayi", False),
        ("rucuya_verilis_tarihi", "tarih", True)]},
    "atama_log": {"sistem": "cekirdek",
                  "anahtar": ["dosya_no", "avukat_kodu", "atama_tarihi", "atama_ref"],
                  "alanlar": [
        ("dosya_no", "metin", True), ("avukat_kodu", "metin", True),
        ("atama_tarihi", "zaman", True), ("iptal_tarihi", "zaman", False),
        ("atama_ref", "metin", False), ("grup", "metin", False), ("tipi", "metin", False)]},
    "takip": {"sistem": "cekirdek", "anahtar": ["dosya_no"], "istege_bagli": True, "gozlem": True,
              "yinelenen_uyari": True, "alanlar": [
        ("dosya_no", "metin", True), ("takip_tipi", "metin", False),
        ("esas_no", "metin", False), ("mahkeme", "metin", False),
        ("islem_tarihi", "tarih", False)]},
    "tahsilat_hareketi": {"sistem": "tahsilat_raporu", "anahtar": [], "istege_bagli": True,
                          "alanlar": [
        ("dosya_no", "metin", True), ("hareket_tarihi", "tarih", True),
        ("tutar", "sayi", True), ("hareket_turu", "metin", False),
        ("hareket_no", "metin", False)]},
    "rapor_avukat_toplam": {"sistem": "tahsilat_raporu", "anahtar": ["avukat_kodu", "donem",
                                                                     "brans"],
                         "istege_bagli": True, "alanlar": [
        ("avukat_kodu", "metin", True), ("donem", "metin", True),
        ("tahsilat_toplami", "sayi", True), ("brans", "metin", False)]},
    "degerlendirme": {"sistem": "degerlendirme", "istege_bagli": True, "yinelenen_uyari": True,
                      "anahtar": ["avukat_kodu", "degerlendirme_tarihi", "alt_baslik",
                                  "degerlendiren"], "alanlar": [
        ("avukat_kodu", "metin", True), ("degerlendirme_tarihi", "tarih", True),
        ("alt_baslik", "metin", True), ("puan", "sayi", False),
        ("degerlendiren", "metin", False)]},
    "avukat": {"sistem": "degerlendirme", "anahtar": ["avukat_kodu"], "istege_bagli": True,
               "alanlar": [("avukat_kodu", "metin", True), ("unvan", "metin", False),
                           ("calisma_durumu", "metin", False)]},
    "esas_goruntu": {"sistem": "dava_takip", "anahtar": ["dosya_no"], "istege_bagli": True,
                     "gozlem": True, "alanlar": [
                         ("dosya_no", "metin", True), ("esas_no", "metin", False),
                         ("kaynak_tarihi", "tarih", False)]},
    "k2_goruntu": {"sistem": "dava_takip", "anahtar": ["dosya_no"], "istege_bagli": True,
                   "gozlem": True, "alanlar": [
        ("dosya_no", "metin", True), ("surec_turu", "metin", False),
        ("baslangic_tarihi", "tarih", False), ("dava_esas_no", "metin", False),
        ("dava_kaynak_tarihi", "tarih", False)]},
    "bekleme": {"sistem": "duzeltme", "anahtar": [], "istege_bagli": True,
                "alanlar": [
        ("dosya_no", "metin", True), ("avukat_kodu", "metin", True),
        ("baslangic", "tarih", True), ("bitis", "tarih", False)]},
}


def alanlar(kaynak):
    """Kaynağın alan adları, şemadaki sırayla."""
    return [alan[0] for alan in KAYNAKLAR[kaynak]["alanlar"]]


def zorunlu_kaynaklar():
    """Gecelik çalışmanın başlaması için gelmesi gereken kaynaklar."""
    return [ad for ad, tanim in KAYNAKLAR.items() if not tanim.get("istege_bagli")]
