"""Ekrana bilerek konmayan sütunlar ve iç tablolar, gerekçeleriyle.

Arka uca yeni sütun eklenirse ya bir bileşene bağlanır ya buraya gerekçesiyle yazılır;
ikisi de yapılmazsa test kırılır.
"""
from hat.veri_kumeleri import CIKTI

GOSTERILMEYEN = {
    "sonuc_k1.atama_turu": "sulh ataması kapsam dışı nedeni (SULH) olarak gösterilir",
    "sonuc_k1.esas_tarihi_bilinmiyor": "kapsam dışı nedeni ESAS_TARIHI_BILINMIYOR olarak "
                                       "gösterilir",
    "sonuc_k2.baslangic_tarihi": "atamaya göre düzeltilmiş hâli (süreç başlangıcı) gösterilir",
    "sonuc_k1.esas_kaynagi": "olayların esas kaynağıyla eşlenmesi için; ekranda gösterilmez",
    "sonuc_k2.esas_kaynagi": "olayların esas kaynağıyla eşlenmesi için; ekranda gösterilmez",
    "bayrak_olay.esas_kaynagi": "Süre Takibi dönemin bugünkü esas kaynağındaki olayları gösterir",
    "olay_celiski.esas_kaynagi": "çelişki yalnız bu gecenin esas kaynağındaki olaylarla aranır",
    "sonuc_tahsilat_aylik.brans": "aylık grafikte branşlar toplanır",
    "sonuc_tahsilat_brans.beklenen": "branş tablosunda beklenen oran (beklenen ÷ rücu tutarı) "
                                     "olarak gösterilir",
    "sonuc_tahsilat_brans.r": "branş tablosunda tutar puanı gösterilir; düzeltilmiş oran avukatın "
                              "bütün dosyaları için kartta",
    "sonuc_tahsilat_yillik.hareket_sayisi": "yıllık tabloda tutar gösterilir; hareket sayısı "
                                            "aylık grafiğin ipucundadır",
    "sonuc_tahsilat_yillik.ayni_donem_tutar": "önceki yılın aynı dönemi ve değişim bundan "
                                              "hesaplanır; sonuç gösterilir",
    "sonuc_eposta.atama_tarihi": "dosya ayrıntısı Süre Takibi listesinde gösterilir",
    "sonuc_eposta.esik_sari": "dosya ayrıntısı Süre Takibi listesinde gösterilir",
    "sonuc_eposta.esik_turuncu": "dosya ayrıntısı Süre Takibi listesinde gösterilir",
    "sonuc_puan_guncel.donem": "kesit yazdırılan çıktıda gösterilir",
    "birlesik_donem.calisma_kimligi": "çalışma kimliği Veri Durumu sayfasında gösterilir",
    "calisma_kaydi.uretilen": "bayat sonuç tablosunu ayıklamak için kullanılır, gösterilmez",
    "calisma_kaydi.hazirlik_surumu": "dönem sonunun hazırlık sürümü denetimi için, gösterilmez",
}

IC_TABLOLAR = {
    "puan_donem": "dönem sütun puanları; ekran aynı sürümün birleşik dönem tablosunu okur",
    "gozlem_esas": "Kriter 1 girdisi; esasın ilk giriş günü dosya ayrıntısında gösterilir",
    "gozlem_esas_yedek": "yedek yol (gölge mod) Kriter 1 girdisi; dosya ayrıntısında gösterilir",
    "gozlem_dava": "Kriter 2 girdisi; dava esasının ilk giriş günü dosya ayrıntısında",
    "gozlem_kosul": "Kriter 2 girdisi; koşul kaybı günü dosya ayrıntısında gösterilir",
    "model_dosya": "hesap girdisi (çekirdek sistem dosyası)",
    "model_atama_donemi": "hesap girdisi (atama dönemleri); dosya ayrıntısında gösterilir",
    "model_hareket": "hesap girdisi (tahsilat hareketleri); toplamları gösterilir",
    "model_bekleme": "hesap girdisi (haklı bekleme); eşik tarihlerine yansır",
    "model_degerlendirme": "hesap girdisi (değerlendirme sistemi); alt başlık puanları gösterilir",
    "model_k2_goruntu": "hesap girdisi (dava takip süreç görüntüsü)",
}

# Gecenin yazdığı sonuc_ ve model_ tabloları çalışma kimliğiyle etiketlenir (tutarlılık denetimi).
GOSTERILMEYEN.update({ad + ".calisma_kimligi": "tablonun hangi gecelik çalışmadan geldiğini "
                      "denetler; ekran yalnız son başarılı gecenin tablosunu gösterir"
                      for ad in CIKTI if ad.startswith(("sonuc_", "model_"))})
