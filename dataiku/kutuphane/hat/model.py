"""Model kurma: kalite kapısını geçmiş kaynak tablolarından hesap girdileri ve gözlemler.

Gözlemler kaynağa göre ayrı tablolardadır: dava takip esas görüntüsü (gozlem_esas), çekirdek
sistemin takip bilgileri (gozlem_esas_yedek; yedek yol), dava esası (gozlem_dava) ve Kriter 2
koşulunun kalktığı gün (gozlem_kosul). Yedek yoldan sabitlenmiş tarih dava takip sistemi
bağlanınca kullanılmaz: o sistemin gözlemi kendi ilk görüntüsünden kurulur. Esas yalnız yedek
yoldan geliyorsa golge_zorunlu True olur: Kriter 1 yalnız gölge modda çalışır. Gözlem tabanı
son başarılı çekimdir (boş görüntü kapıda durur); görüntüsü o gece gelmeyen gözlem None olur.
Haklı bekleme kaynağı daha önce okunmuşken o gece gelmezse bekleme_eksik True olur (Kriter 1
hesaplanmaz). Yazım hesaptan sonradır; sonuc_ ve model_ tabloları çalışma kimliğiyle
etiketlenir, gecenin kaydına her tablonun satır sayısı yazılır. Okuyanlar yalnız son başarılı
gecenin tablosunu, o gecenin yazdığı satır sayısıyla kullanır.
"""
from avukat_perf import gozlem, hazirlik
from hat import butunluk, gecmis, hesap_sure

TABLOLAR = ("dosya", "atama_donemi", "hareket", "bekleme", "degerlendirme", "avukat",
            "k2_goruntu")
GOZLEMLER = ("gozlem_esas", "gozlem_esas_yedek", "gozlem_dava", "gozlem_kosul")


def _gozlem_tanimlari(tablolar, params):
    takip = tablolar.get("takip")
    # Takip bilgisinde dosya başına birden çok satır olabilir (açık karar): gözleme esası dolu
    # satırlar içinde işlem tarihi en erken olan girer (gozlem.guncelle ilk dolu satırı alır).
    yedek = None if takip is None else takip.sort_values(
        "islem_tarihi", na_position="last", kind="mergesort").rename(
        columns={"islem_tarihi": "kaynak_tarihi"})
    kosul = hazirlik.kosul_goruntusu(tablolar["dosya"], params["kriter2"])
    return [("gozlem_esas", tablolar.get("esas_goruntu"), "esas_goruntu", "esas_no",
             "kaynak_tarihi"),
            ("gozlem_esas_yedek", yedek, "takip", "esas_no", "kaynak_tarihi"),
            ("gozlem_dava", tablolar.get("k2_goruntu"), "k2_goruntu", "dava_esas_no",
             "dava_kaynak_tarihi"),
            ("gozlem_kosul", kosul, "dosya", "kosul_kayip", None)]


def kur(ortam, tablolar, params, cekim, onceki_kayit, simdi):
    """Model sözlüğü; gözlem tablolarını günceller (yazmaz, bkz. yaz). simdi: bu çalışmanın
    başlangıcı; gözlem tabanı ondan önce başlamış son başarılı çekimdir (aynı gün dahil)."""
    hz = params["hazirlik"]
    model = {"dosya": tablolar["dosya"], "k2_goruntu": tablolar.get("k2_goruntu"),
             "atama_donemi": hazirlik.atama_donemleri(tablolar["atama_log"], hz),
             "hareket": None if tablolar.get("tahsilat_hareketi") is None else
             hazirlik.tahsilat_hareketleri(tablolar["tahsilat_hareketi"], hz),
             "bekleme": tablolar.get("bekleme"), "avukat": tablolar.get("avukat"),
             "degerlendirme": tablolar.get("degerlendirme"),
             "golge_zorunlu": tablolar.get("esas_goruntu") is None and
             tablolar.get("takip") is not None,
             "bekleme_eksik": tablolar.get("bekleme") is None and
             gecmis.son_basarili(onceki_kayit, "bekleme", simdi)[0] is not None,
             "golge_araliklari": hesap_sure.golge_araliklari(onceki_kayit)}
    tanimlar = _gozlem_tanimlari(tablolar, params)
    mevcut = {ad: ortam.tablo_oku(ad) for ad, goruntu, _, _, _ in tanimlar if goruntu is not None}
    butunluk.veri_kaybi(onceki_kayit, mevcut)
    for ad, goruntu, kaynak_adi, deger, kaynak_tarihi in tanimlar:
        if goruntu is None:
            model[ad] = None
            continue
        onceki_tarih, _ = gecmis.son_basarili(onceki_kayit, kaynak_adi, simdi)
        model[ad] = gozlem.guncelle(mevcut[ad], goruntu, "dosya_no", deger, cekim,
                                    onceki_tarih, kaynak_tarihi)
    return model


def yaz(ortam, model, sonuc, kimlik):
    """Sonuç, model ve gözlem tablolarını yazar; {tablo: satır sayısı} döndürür (uretilen).

    sonuc_ ve model_ tablolarına calisma_kimligi sütunu eklenir.
    """
    yazilacak = dict(sonuc)
    yazilacak.update({"model_" + ad: model[ad] for ad in TABLOLAR if model.get(ad) is not None})
    yazilacak.update({ad: model[ad] for ad in GOZLEMLER if model.get(ad) is not None})
    etiketli = sorted(ad for ad in yazilacak if ad.startswith(("sonuc_", "model_")))
    for ad in etiketli:
        ortam.tablo_yaz(ad, yazilacak[ad].assign(calisma_kimligi=kimlik))
    for ad in sorted(set(yazilacak) - set(etiketli)):  # gözlemler ve olay tabloları en son
        ortam.tablo_yaz(ad, yazilacak[ad])
    return {ad: len(tablo) for ad, tablo in yazilacak.items()}


def etiket_uygun(tablo, kimlik, sayi=None):
    """Tablo bu gecenin yazdığı tablo mu: etiketi bu kimlik ve satır sayısı kayıttakiyle aynı.

    sayi: gecenin kaydına yazılan satır sayısı (eski kayıtta None). Boş tablo yalnız o gece
    sıfır satır yazıldıysa uygundur; yarım yazılmış tablo satır sayısından ayırt edilir.
    """
    if tablo is None:
        return True
    if sayi is not None and len(tablo) != sayi:
        return False
    if "calisma_kimligi" not in tablo.columns or tablo.empty:
        return True
    return set(tablo["calisma_kimligi"].astype(str)) == {str(kimlik)}


def oku(ortam, onceki_kayit):
    """Dönem sonu için son başarılı gecenin model ve gözlem tabloları.

    O gece yazılmamış (bayat) ya da başka bir gecenin etiketini taşıyan tablo None sayılır:
    ör. dava takip bağlantısı kaldırıldıktan sonra eski süreç görüntüsüyle Kriter 2
    yayımlanmaz, yarıda kesilmiş bir gecenin yazdığı tablo kullanılmaz.
    """
    uretilen, kimlik = gecmis.son_sayilar(onceki_kayit), gecmis.son_kimlik(onceki_kayit)

    def _oku(ad):
        if ad not in uretilen:  # hiç başarılı gece yok ya da bayat
            return None
        tablo = ortam.tablo_oku(ad)
        if tablo is None or not etiket_uygun(tablo, kimlik, uretilen[ad]):
            return None
        return tablo.drop(columns="calisma_kimligi", errors="ignore")
    model = {ad: _oku("model_" + ad) for ad in TABLOLAR}
    model.update({ad: _oku(ad) for ad in GOZLEMLER})
    model["golge_zorunlu"] = gecmis.son_golge_zorunlu(onceki_kayit)
    model["bekleme_eksik"] = model["bekleme"] is None and gecmis.son_basarili(
        onceki_kayit, "bekleme", "2200-01-01")[0] is not None
    model["golge_araliklari"] = hesap_sure.golge_araliklari(onceki_kayit)
    return model
