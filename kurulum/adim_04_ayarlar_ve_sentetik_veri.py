"""Kurulum adım 4: ayar dosyaları ve sentetik prova verisi.

araclar/paketle.py üretir; elle değiştirmeyin. Dataiku'da projenin bir Python
not defterine bu dosyanın tamamını yapıştırıp çalıştırın. params.json ve
kaynaklar.json "ayarlar" klasörüne yazılır. PROVA True iken prova ek dosyaları
da yazılır, sentetik veri üretilip "kaynak_dosyalari" klasörüne
(sentetik/veri/) yüklenir. Canlı projede PROVA = False yapın.
"""
import json
import shutil
import tempfile

import dataiku

PROVA = True  # canlı projede False

AYARLAR = {}
AYARLAR["params.json"] = r'''{
  "_teyit_aciklama": "Hukuk ya da kaynak ekibi teyidi bekleyen parametreler (_teyit_bekleyen); Puanlama Kuralları sayfasında 'Teyit bekliyor' olarak işaretlenir. Bir karar kesinleşince yalnız buradan çıkarılır; hesap sürümünü etkilemez.",
  "_teyit_bekleyen": [
    "agirliklar",
    "birlesik_sutunlar",
    "notlar",
    "kriter1.uyari_gun",
    "kriter1.oto_branslar",
    "kriter1.sonlanan_atamada_dusum_korunur",
    "kriter2.dusum_ay",
    "kriter2.sonlanan_atamada_dusum_korunur",
    "kriter2.kapanis_kodlari",
    "tahsilat.gruplama",
    "tahsilat.tutar_bantlari",
    "tahsilat.olgunluk_ay",
    "tahsilat.yas_bantlari",
    "tahsilat.bilesen_agirliklari",
    "tahsilat.guncellik_pencere_ay",
    "tahsilat.enflasyon_duzeltme",
    "tahsilat.elde_tutma_paydasi",
    "tahsilat.yeterli_olgun_dosya",
    "kalite_davranis.olcek",
    "kalite_davranis.ters_yonlu",
    "kalite_davranis.coklu_degerlendirme",
    "kalite_davranis.pencere_ay",
    "sure_puani.pencere_ay",
    "sure_puani.yeterli_dosya",
    "uyari.golge_mod",
    "hazirlik.iptal_yorumu",
    "hazirlik.sulh_avukat_kodlari",
    "hazirlik.sulh_alani",
    "hazirlik.sulh_degerleri",
    "hazirlik.tahsilat_hareket_turleri",
    "kalite.bilinen_branslar",
    "kalite.iliski_en_cok_yetim_orani"
  ],
  "kriter1": {
    "_not": "Oto kapsamı (oto_branslar) varsayımdır; teyit bekliyor. Atama iade ya da yeniden atamayla biterse bitişten önce oluşmuş puan düşümünün korunup korunmayacağı (sonlanan_atamada_dusum_korunur) Hukuk teyidi bekliyor.",
    "uyari_gun": 10,
    "dusum_gun_oto": 20,
    "dusum_ay_diger": 2,
    "oto_branslar": [
      "TRAFIK",
      "KASKO"
    ],
    "sonlanan_atamada_dusum_korunur": true
  },
  "kriter2": {
    "_not": "Puan düşümünün ayı (dusum_ay) teyit bekliyor (4 ya da 6). Uyarı yalnız rucu_kodu kodlu dosyalarda aranır. Dosyanın kapandığını gösteren rücu kodları (kapanis_kodlari) ya da R11'de açık bakiyenin sıfırlanması koşul kaybıdır: Kriter 2 dönemi o gün kapanır, tahsilatın sıklık ve güncelliğinde dosyanın süresi o gün biter. Atama bekleyen ya da iade edilen dosyanın başka kodu kapanış sayılmaz. Kod listesi çekirdek sistem ekibinden teyit bekliyor.",
    "uyari_ay": 3,
    "dusum_ay": 6,
    "rucu_kodu": "R11",
    "kapanis_kodlari": [
      "R06",
      "R12"
    ],
    "sonlanan_atamada_dusum_korunur": true
  },
  "tahsilat": {
    "_not": "İzleme süreleri (olgunluk_ay) başlangıç tahminidir. Tutar bantları (tutar_bantlari) dosyaları tutarına göre gruplar; başlangıç sınırları 40.000 ve 150.000 TL, gerçek rücu verisi üç eşit gruba bölünerek güncellenecek. Boş liste tek bant demektir. Tahsilat puanı üç bileşenin ağırlıklı toplamıdır (bilesen_agirliklari): tutar (gerçekleşen ÷ beklenen tahsilat), sıklık (olgun dosyalarda avukatın tahsilat yaptığı dosya-ay sayısı ÷ elde tuttuğu süreden beklenen sayı) ve güncellik (aynısı, son guncellik_pencere_ay ayda bütün dosyalarla). Beklenen değerler aynı dosya grubundaki (gruplama: branş, dosya yaşı bandı, tutar bandı) diğer avukatların oranından kurulur, avukatın kendi sonucu kendi beklentisine girmez (grupta başka avukat yoksa aynı branştaki, o da yoksa bütün diğer avukatlar); yas_bantlari rücuya verilişten geçen ayın sınırlarıdır (sıklık ve güncellikte her gün o günkü yaşın bandına yazılır). Kapanan dosyanın süresi kapandığı gün biter. Sayım bileşenlerinde güven ayarı olay sayısına uygulanır (olay_guven_sabiti). Bileşen ağırlıkları, yaş sınırları ve pencere tasarım değeridir; Hukuk teyidi bekliyor. Puan en az en_az_olgun_dosya (1) olgun dosyada hesaplanır; olgun dosya yeterli_olgun_dosya'nın (10) altındaysa puan yine üretilir ve geçerli sayılır, ekranda 'Yeterli veri yok' uyarısıyla gösterilir (güven ayarı az veride puanı beklenen düzeye yaklaştırır). Branş puanında aynı kural o branşın dosyalarıyla uygulanır. Enflasyon düzeltmesi seçenektir, henüz uygulanmadı. Yıllık tahsilat tablosu son yillik_yil_sayisi takvim yılını gösterir. Elde tutma payı (elde_tutma_paydasi): ilk_atamadan (varsayılan) avukatın dosyayı tuttuğu günleri dosyanın ilk atamasından kesite kadarki güne böler; iade sonrası ve iki atama arasındaki boşluk kimseye yazılmaz, kısa süre tutulup iade edilen dosya beklentiye tam dosya olarak girmez, tek avukatın tuttuğu dosya 1 sayılır. avukat_gunleri payı yalnız avukatların tuttuğu günler arasında böler (önceki yöntem). Seçim Hukuk teyidi bekliyor.",
    "gruplama": [
      "brans",
      "yas_bandi",
      "tutar_bandi"
    ],
    "tutar_bantlari": [
      40000,
      150000
    ],
    "yas_bantlari": [
      12,
      24,
      36,
      48,
      60,
      84
    ],
    "olgunluk_ay": {
      "TRAFIK": 24,
      "KASKO": 24,
      "DIGER": 36
    },
    "en_az_olgun_dosya": 1,
    "yeterli_olgun_dosya": 10,
    "guven_sabiti": 10,
    "olay_guven_sabiti": 10,
    "taban": 75,
    "egim": 50,
    "bilesen_agirliklari": {
      "tutar": 0.6,
      "siklik": 0.2,
      "guncellik": 0.2
    },
    "elde_tutma_paydasi": "ilk_atamadan",
    "enflasyon_duzeltme": false,
    "guncellik_pencere_ay": 12,
    "aylik_pencere_ay": 24,
    "yillik_yil_sayisi": 3
  },
  "kalite_davranis": {
    "_not": "Bir sütunun puanı için alt başlıkların en az üçte ikisi puanlanmış olmalıdır (yeterlilik). Değerlendirme sisteminin puan ölçeği ve yüksek puanın olumsuz olduğu alt başlıklar (ters_yonlu) teyit bekliyor; teyit gelene kadar bu iki sütun puanlanmaz. Bir alt başlıkta birden çok değerlendirme varsa ortalaması alınır. Mevcut dört alan (mevcut_alanlar) yeni alt başlıklar eklenene kadar avukat kartında bilgi amaçlı gösterilir; puana girmez.",
    "yeterlilik": [
      2,
      3
    ],
    "alt_basliklar": {
      "kalite": [
        "eksik_hatali_islem",
        "yanlis_muhatap_eksik_taraf",
        "hatali_dava_takip_islemi",
        "hukuki_degerlendirme",
        "ic_ekip_mudahalesi",
        "sistem_kullanimi_guncellik"
      ],
      "davranis": [
        "tekrarlayan_bilgi_talebi",
        "dosyaya_hakimiyet",
        "karar_alma_inisiyatif",
        "surekli_yonlendirme_ihtiyaci",
        "yazili_iletisim_niteligi",
        "sorumluluk_alma",
        "indirim_sulh_yaklasimi"
      ]
    },
    "olcek": {
      "en_dusuk": null,
      "en_yuksek": null
    },
    "ters_yonlu": null,
    "coklu_degerlendirme": "ortalama",
    "pencere_ay": 12,
    "mevcut_alanlar": [
      "brans_yetkinligi",
      "cozum_yetenegi",
      "ulasilabilirlik",
      "durustluk_duzeyi"
    ]
  },
  "sure_puani": {
    "_not": "Ölçüm penceresi, risk altındaki dönem ve veri kapsamı tanımları önerilen varsayılandır; Hukuk teyidi bekliyor. Beklenen düşüm tabanı (en_az_beklenen) 0: puan göreli olduğu için kimse gecikmeyince beklenen düşüm 0 olur; taban 5 iken bu durumda süre puanı ve birleşik puan hiç yayımlanmıyordu. Şimdi herkes zamanındaysa herkes 75 alır. Beklenen düşüm aynı gruptaki (kriter, süreç, branş) diğer avukatların düşüm oranından kurulur, avukatın kendi dönemleri kendi beklentisine girmez (grupta başka avukat yoksa aynı kriter ve süreçteki, o da yoksa bütün diğer avukatlar). En az bir risk altındaki dönemi olan avukatın puanı hesaplanır; risk altındaki dönemlerdeki farklı dosya sayısı yeterli_dosya'nın (10) altındaysa puan yine geçerlidir, ekranda 'Yeterli veri yok' uyarısıyla gösterilir. Veri kapsamı (en_az_kapsam) tabanı değişmedi.",
    "guven_sabiti": 10,
    "taban": 75,
    "egim": 50,
    "yeterli_dosya": 10,
    "en_az_beklenen": 0,
    "en_az_kapsam": 0.8,
    "pencere_ay": 12
  },
  "uyari": {
    "_not": "Gölge mod açıkken süre bayrakları hesaplanır; e-posta gönderilmez, puan düşümü ve süre puanı uygulanmaz.",
    "golge_mod": true
  },
  "hazirlik": {
    "_not": "Çekirdek sistem alanlarının anlamı teyit bekliyor: iptal tarihinin yeniden atamayı mı hatalı girişi mi gösterdiği (iptal_yorumu), sulh amaçlı atamanın nasıl ayırt edildiği ve hangi hareket türlerinin tahsilat sayılacağı. Hareket türü verilmezse bütün hareketler tahsilat sayılır; verilirse ters kayıt (eksi tutarlı) türü de listeye yazılır, listede olmayan tür puana girmez (kalite kapısı sayısını uyarır). sulh_alani atama logunun sözleşme alanlarından biridir (atama_ref, grup, tipi); ham kaynak adı değil. Dosya aynı avukata kesintisiz yeniden atanırsa (araya başka avukat girmeden yeni atama kaydı) surer iken dönem sürer, süre ilk atamadan işler, dosyada tek düşüm olur; süre yalnız başka bir avukata atamada yeniden başlar, aynı dosyada düşüm bir defadır. yeni_donem yeni atama dönemi açar, süre yeni kayıttan başlar.",
    "iptal_yorumu": "sonraki_atamaya_gore",
    "ayni_avukata_yeniden_atama": "surer",
    "sulh_avukat_kodlari": [],
    "sulh_alani": null,
    "sulh_degerleri": [],
    "tahsilat_hareket_turleri": null
  },
  "kalite": {
    "_not": "Veri kalite kapısının eşikleri: önceki başarılı çekime göre satır sayısında izin verilen değişim (satir_sapma_orani; meşru bir sıçramada bir gece için yükseltilir), sapmanın denetlenmediği küçük tablo sınırı (sapma_en_az_satir) ve tahsilat raporuyla mutabakat toleransı. Bu tarihten eski tarih (en_eski_tarih; boş yerine yazılmış 1900-01-01 gibi) geceyi durdurur. Branş değeri bilinen_branslar listesinde yoksa gece durur (yazım farkı oto eşiğini ve olgunluk süresini sessizce değiştirirdi; kaynak kodları kaynak ayarındaki deger_eslemesi ile çevrilir); liste gerçek kodlarla teyit edilecek. Kaynaklar arası ilişkide eşleşmeyen anahtar oranı iliski_en_cok_yetim_orani'nı aşarsa gece durur (tahsilat hareketinde tutarla da tartılır); meşru eşleşmeyen kayıt olabileceği için değer ilk gerçek çekimde ölçülerek belirlenir.",
    "satir_sapma_orani": 0.5,
    "sapma_en_az_satir": 100,
    "mutabakat_tolerans": 0.005,
    "gelecek_tarih_gun": 1,
    "en_eski_tarih": "1950-01-01",
    "bilinen_branslar": [
      "TRAFIK",
      "KASKO",
      "NAKLIYAT",
      "YANGIN",
      "DAHILI_SU",
      "HIRSIZLIK",
      "DIGER"
    ],
    "iliski_en_cok_yetim_orani": 0.1
  },
  "_notlar_aciklama": "yüksekten düşüğe [not, eşik]; toplam >= eşik olan ilk not verilir. B notu teyit bekliyor",
  "notlar": [
    [
      "A",
      85
    ],
    [
      "B+",
      75
    ],
    [
      "B",
      65
    ],
    [
      "B-",
      55
    ],
    [
      "C",
      0
    ]
  ],
  "agirliklar": {
    "_not": "Sütun ağırlıkları ikili karşılaştırmalardan (Analitik Hiyerarşi Süreci) hesaplanır: \"a/b\": a sütunu b sütununun kaç katı önemli. Gerekçe: Tahsilat ve Süre nesnel sistem verisine dayanır; Hukuki Kalite ile Davranış ve İletişim aynı değerlendiricinin öznel puanıdır, bu yüzden ikisi birlikte nesnel sütunların toplamından küçük tutulur. Tahsilat Süre'den biraz (1,17 kat), Hukuki Kalite'den 1,4 kat önemli; Süre Hukuki Kalite'den 1,2 kat; hukuki doğruluk iletişim biçiminin 2,5 katı. Sonuç 35 / 30 / 25 / 10, tutarlılık oranı yaklaşık 0. Değerlendirmeler Hukuk teyidi bekliyor.",
    "tahsilat/sure": 1.17,
    "tahsilat/kalite": 1.4,
    "tahsilat/davranis": 3.5,
    "sure/kalite": 1.2,
    "sure/davranis": 3,
    "kalite/davranis": 2.5
  },
  "_birlesik_aciklama": "Birleşik puana giren sütunlar (birlesik_sutunlar). İlk fazda dava takip sistemi verisi olmadığından Süre ve Performans birleşik puana girmez; Süre Takibi sayfası ve bayraklar bilgi olarak kalır. Ağırlıklar yalnız giren sütunların ikili karşılaştırmalarından hesaplanır: Süre'nin payı diğerlerine oranında dağılır. Giren sütunların hepsi geçerli değilse birleşik puan, not ve sıra yayımlanmaz (birlesik_puan_kosulu); eksik puan sıfır sayılmaz.",
  "birlesik_sutunlar": [
    "tahsilat",
    "kalite",
    "davranis"
  ],
  "birlesik_puan_kosulu": "tum_sutunlar",
  "gorunum": {
    "_not": "Ekranda görünen adların TEK tanımlandığı yer: sistem adları, branş adları (brans_adlari: [kod, ad] listesi; sıra branşın renk paletindeki yeridir, liste ek dosyada bütünüyle değişir), kalite ve davranış alt başlıkları ile mevcut değerlendirme alanlarının adları. Gerçek adları yalnız burada yazın; arayüzdeki bütün etiketler buradan gelir. Sistem kodları (sol taraf) değişmez; branş kodları kalite.bilinen_branslar ile aynı olmalı. Listede olmayan branş ekranda kendi koduyla ve nötr renkle görünür. Bu bölüm hesaplamayı ve hesap sürümünü etkilemez.",
    "sistem_adlari": {
      "cekirdek": "Çekirdek sistem",
      "tahsilat_raporu": "Tahsilat raporu",
      "degerlendirme": "Değerlendirme sistemi",
      "dava_takip": "Dava takip sistemi",
      "duzeltme": "Düzeltme kayıtları"
    },
    "brans_adlari": [
      ["TRAFIK", "Trafik"],
      ["KASKO", "Kasko"],
      ["NAKLIYAT", "Nakliyat"],
      ["YANGIN", "Yangın"],
      ["DAHILI_SU", "Dahili Su"],
      ["HIRSIZLIK", "Hırsızlık"],
      ["DIGER", "Diğer"]
    ],
    "alt_baslik_adlari": {
      "eksik_hatali_islem": "Eksik veya hatalı işlemler",
      "yanlis_muhatap_eksik_taraf": "Yanlış muhatap veya eksik taraf",
      "hatali_dava_takip_islemi": "Hatalı dava ve takip işlemleri",
      "hukuki_degerlendirme": "Hukuki değerlendirme ve yorumlama",
      "ic_ekip_mudahalesi": "İç ekibin müdahale ihtiyacı",
      "sistem_kullanimi_guncellik": "Sistem kullanımı ve güncellik",
      "tekrarlayan_bilgi_talebi": "Tekrarlayan bilgi talepleri",
      "dosyaya_hakimiyet": "Dosyaya hakimiyet",
      "karar_alma_inisiyatif": "Karar alma ve inisiyatif",
      "surekli_yonlendirme_ihtiyaci": "Sürekli yönlendirme ihtiyacı",
      "yazili_iletisim_niteligi": "Yazılı iletişimin niteliği",
      "sorumluluk_alma": "Sorumluluk alma",
      "indirim_sulh_yaklasimi": "İndirim ve sulh süreçlerindeki yaklaşım"
    },
    "mevcut_alan_adlari": {
      "brans_yetkinligi": "Branş yetkinliği",
      "cozum_yetenegi": "Çözüm yeteneği",
      "ulasilabilirlik": "Ulaşılabilirlik",
      "durustluk_duzeyi": "Dürüstlük düzeyi"
    }
  }
}
'''
AYARLAR["kaynaklar.json"] = r'''{
  "_not": "Kaynak ayarları. sistemler: sistem başına ortak ayar (yontem: bekliyor | dataiku | api | dosya; api.adres_koku, api.kimlik, api.sayfalama, biçimler). Bir sistemi bağlamak için çoğu zaman yalnız o sistemin bloğu doldurulur: yontem, adres_koku, kimlik, sayfalama. kaynaklar: kaynağa özgü ayar (api.yol, veri kümesi, dosya yolu, alan eşlemesi); sistemdeki değeri ezer. Gizli değer dosyaya yazılmaz: kimlik.gizli Dataiku kullanıcı gizlisinin adıdır. Şirkete özgü değerler aynı klasördeki kaynaklar_ek.json'a yazılır (depoya girmez). Ayrıntı README, Veri entegrasyonu.",
  "sistemler": {
    "cekirdek": {
      "_not": "Çekirdek sistem: dosya, atama_log, takip.",
      "yontem": "bekliyor",
      "api": {
        "adres_koku": "https://CEKIRDEK-ADRESI-BEKLENIYOR",
        "http_yontemi": "GET",
        "kimlik": {
          "tur": "bearer",
          "gizli": "API_CEKIRDEK_ANAHTARI"
        },
        "sayfalama": {
          "tur": "sayfa",
          "sayfa_parametresi": "page",
          "boyut_parametresi": "size",
          "boyut": 1000
        },
        "kayit_yolu": "data",
        "basliklar": {},
        "zaman_asimi_sn": 60,
        "deneme": 3,
        "bekleme_sn": 2
      },
      "sayi_bicimi": "en",
      "tarih_bicimi": null
    },
    "tahsilat_raporu": {
      "_not": "Tahsilat raporu: tahsilat_hareketi, rapor_avukat_toplam.",
      "yontem": "bekliyor",
      "api": {
        "adres_koku": "https://RAPOR-ADRESI-BEKLENIYOR",
        "http_yontemi": "GET",
        "kimlik": {
          "tur": "bearer",
          "gizli": "API_RAPOR_ANAHTARI"
        },
        "sayfalama": {
          "tur": "sayfa",
          "sayfa_parametresi": "page",
          "boyut_parametresi": "size",
          "boyut": 1000
        },
        "kayit_yolu": "data",
        "basliklar": {},
        "zaman_asimi_sn": 60,
        "deneme": 3,
        "bekleme_sn": 2
      },
      "sayi_bicimi": "en",
      "tarih_bicimi": null
    },
    "degerlendirme": {
      "_not": "Değerlendirme sistemi: degerlendirme, avukat.",
      "yontem": "bekliyor",
      "api": {
        "adres_koku": "https://DEGERLENDIRME-ADRESI-BEKLENIYOR",
        "http_yontemi": "GET",
        "kimlik": {
          "tur": "bearer",
          "gizli": "API_DEGERLENDIRME_ANAHTARI"
        },
        "sayfalama": {
          "tur": "sayfa",
          "sayfa_parametresi": "page",
          "boyut_parametresi": "size",
          "boyut": 1000
        },
        "kayit_yolu": "data",
        "basliklar": {},
        "zaman_asimi_sn": 60,
        "deneme": 3,
        "bekleme_sn": 2
      },
      "sayi_bicimi": "en",
      "tarih_bicimi": null
    },
    "dava_takip": {
      "_not": "Dava takip sistemi: esas_goruntu, k2_goruntu.",
      "yontem": "bekliyor",
      "api": {
        "adres_koku": "https://DAVA-TAKIP-ADRESI-BEKLENIYOR",
        "http_yontemi": "GET",
        "kimlik": {
          "tur": "bearer",
          "gizli": "API_DAVA_TAKIP_ANAHTARI"
        },
        "sayfalama": {
          "tur": "sayfa",
          "sayfa_parametresi": "page",
          "boyut_parametresi": "size",
          "boyut": 1000
        },
        "kayit_yolu": "data",
        "basliklar": {},
        "zaman_asimi_sn": 60,
        "deneme": 3,
        "bekleme_sn": 2
      },
      "sayi_bicimi": "en",
      "tarih_bicimi": null
    },
    "duzeltme": {
      "_not": "Düzeltme kayıtları: bekleme.",
      "yontem": "bekliyor",
      "api": {
        "adres_koku": "https://DUZELTME-ADRESI-BEKLENIYOR",
        "http_yontemi": "GET",
        "kimlik": {
          "tur": "bearer",
          "gizli": "API_DUZELTME_ANAHTARI"
        },
        "sayfalama": {
          "tur": "sayfa",
          "sayfa_parametresi": "page",
          "boyut_parametresi": "size",
          "boyut": 1000
        },
        "kayit_yolu": "data",
        "basliklar": {},
        "zaman_asimi_sn": 60,
        "deneme": 3,
        "bekleme_sn": 2
      },
      "sayi_bicimi": "en",
      "tarih_bicimi": null
    }
  },
  "kaynaklar": {
    "dosya": {
      "api": {
        "yol": "/dosya"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_cekirdek_dosya"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_cekirdek_dosya.csv"
      },
      "alan_eslemesi": {}
    },
    "atama_log": {
      "api": {
        "yol": "/atama_log"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_cekirdek_atama_log"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_cekirdek_atama_log.csv"
      },
      "alan_eslemesi": {}
    },
    "takip": {
      "api": {
        "yol": "/takip"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_cekirdek_takip"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_cekirdek_takip.csv"
      },
      "alan_eslemesi": {}
    },
    "tahsilat_hareketi": {
      "api": {
        "yol": "/tahsilat_hareketi"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_rapor_tahsilat_hareketi"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_rapor_tahsilat_hareketi.csv"
      },
      "alan_eslemesi": {}
    },
    "rapor_avukat_toplam": {
      "api": {
        "yol": "/rapor_avukat_toplam"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_rapor_avukat_toplam"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_rapor_avukat_toplam.csv"
      },
      "alan_eslemesi": {}
    },
    "degerlendirme": {
      "api": {
        "yol": "/degerlendirme"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_degerlendirme_puan"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_degerlendirme_puan.csv"
      },
      "alan_eslemesi": {},
      "genis_degerlendirme": null
    },
    "avukat": {
      "api": {
        "yol": "/avukat"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_degerlendirme_avukat"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_degerlendirme_avukat.csv"
      },
      "alan_eslemesi": {}
    },
    "esas_goruntu": {
      "api": {
        "yol": "/esas_goruntu"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_dava_takip_esas"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_dava_takip_esas.csv"
      },
      "alan_eslemesi": {}
    },
    "k2_goruntu": {
      "api": {
        "yol": "/k2_goruntu"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_dava_takip_surec"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_dava_takip_surec.csv"
      },
      "alan_eslemesi": {}
    },
    "bekleme": {
      "api": {
        "yol": "/bekleme"
      },
      "dataiku": {
        "veri_kumesi": "kaynak_duzeltme_bekleme"
      },
      "dosya": {
        "yol": "sentetik/veri/kaynak_duzeltme_bekleme.csv"
      },
      "alan_eslemesi": {}
    }
  }
}
'''

PROVA_AYARLARI = {}
PROVA_AYARLARI["params_ek.json"] = r'''{
  "_not": "Yalnız sentetik prova ve önizleme için parametre eki. Gerçek params.json'da değerlendirme ölçeği ve yönü teyit beklediği için null; prova sentetik formun 1-5 ölçeğini ve olumlu yönünü varsayar. Gölge mod kapalı ki süre puanı da görünsün. Tahsilat ayarları (tutar bantları dahil) params.json'daki üretim varsayılanıdır.",
  "kalite_davranis": {
    "olcek": {
      "en_dusuk": 1,
      "en_yuksek": 5
    },
    "ters_yonlu": []
  },
  "uyari": {
    "golge_mod": false
  },
  "hazirlik": {
    "sulh_avukat_kodlari": [
      "SL-01",
      "SL-02"
    ]
  }
}
'''
PROVA_AYARLARI["kaynaklar_ek.json"] = r'''{
  "_not": "Sentetik prova eki: dataiku/degiskenler/kaynaklar.json üzerine birleştirilir. Bütün sistemler sentetik/veri altındaki CSV'lerden okunur (dosya yöntemi). Dataiku'daki prova projesinde bu dosya ayarlar klasörüne kaynaklar_ek.json adıyla yüklenir.",
  "sistemler": {
    "cekirdek": {
      "yontem": "dosya"
    },
    "tahsilat_raporu": {
      "yontem": "dosya"
    },
    "degerlendirme": {
      "yontem": "dosya"
    },
    "dava_takip": {
      "yontem": "dosya"
    },
    "duzeltme": {
      "yontem": "dosya"
    }
  },
  "kaynaklar": {
    "atama_log": {
      "alan_eslemesi": {
        "DOSYA_NO": "dosya_no",
        "AV_KOD": "avukat_kodu",
        "ATAMA_ZAMANI": "atama_tarihi",
        "IPTAL_ZAMANI": "iptal_tarihi",
        "ATAMA_NO": "atama_ref",
        "GRUP_KODU": "grup",
        "ATAMA_TIPI": "tipi"
      },
      "tarih_bicimi": "%d/%m/%Y %H:%M:%S"
    },
    "tahsilat_hareketi": {
      "sayi_bicimi": "tr"
    }
  }
}
'''


# ---------- sentetik veri üreticisi (sentetik/uretici.py) ----------
"""Sentetik test verisi üreticisi: bütün kaynakları sözleşmedeki biçimde CSV olarak yazar.

Gerçek veri içermez; kişi ve dosya kimlikleri AV-01, D-000001 biçimindedir. Sabit tohumla
her çalıştırmada aynı veri çıkar. Gerçeğe yakın durumlar: avukatlar arası tahsilat becerisi
(tutar ve tahsilat yapılan dosya oranı ayrı), işlem hızı ve kalite farkı; sulh amaçlı ön
atama; yeniden atama ve iade (önceki kayda iptal tarihi yazılır); itirazlı
icra, arabuluculuk ve doğrudan dava; ters kayıt; atama öncesi tahsilat; eksik değerlendirme;
kaynak alan adlarının sözleşmeden farklı gelmesi, gün/ay/yıl tarih biçimi; Türkçe sayı biçimi.
Kullanım: python sentetik/uretici.py [hedef_klasor] [dosya_sayisi] [avukat_sayisi]
"""
import csv
import datetime as dt
import os
import random
import sys

KESIT = dt.date(2026, 11, 19)
BRANSLAR = [("TRAFIK", 0.40, 0.35, 40000), ("KASKO", 0.25, 0.30, 60000),
            ("NAKLIYAT", 0.10, 0.25, 150000), ("YANGIN", 0.15, 0.20, 250000),
            ("DAHILI_SU", 0.10, 0.22, 30000)]
KALITE = ["eksik_hatali_islem", "yanlis_muhatap_eksik_taraf", "hatali_dava_takip_islemi",
          "hukuki_degerlendirme", "ic_ekip_mudahalesi", "sistem_kullanimi_guncellik"]
DAVRANIS = ["tekrarlayan_bilgi_talebi", "dosyaya_hakimiyet", "karar_alma_inisiyatif",
            "surekli_yonlendirme_ihtiyaci", "yazili_iletisim_niteligi", "sorumluluk_alma",
            "indirim_sulh_yaklasimi"]
# Bilgi amaçlı dört değerlendirme alanı (puana girmez).
ESKI_ALANLAR = ["brans_yetkinligi", "cozum_yetenegi", "ulasilabilirlik", "durustluk_duzeyi"]


def _gun(rnd, bas, son):
    return bas + dt.timedelta(days=rnd.randint(0, (son - bas).days))


def _tr(tutar):
    return "{:,.2f}".format(tutar).replace(",", "_").replace(".", ",").replace("_", ".")


def avukatlar(rnd, adet):
    """Son iki avukat ayrılmıştır, ama en az iki avukat çalışmaya devam eder (yeniden atama
    başka bir avukata yapılabilsin): 3 avukatta yalnız sonuncusu, 1 ya da 2'de hiçbiri ayrılmaz."""
    if adet < 1:
        raise ValueError("en az bir avukat gerekir")
    ayrilan = min(2, max(0, adet - 2))
    sonuc = []
    for sira in range(1, adet + 1):
        uzman = [b[0] for b in rnd.sample(BRANSLAR, 2)]
        sonuc.append({"kod": "AV-{:02d}".format(sira), "beceri": min(1.6, max(
            0.6, rnd.lognormvariate(0, 0.25))), "tahsil_hizi": min(1.6, max(
                0.6, rnd.lognormvariate(0, 0.25))), "hiz": rnd.uniform(4, 16),
            "dava_hizi": rnd.uniform(40, 200), "kalite": rnd.uniform(2.4, 4.8), "uzman": uzman,
            "durum": "AYRILDI" if sira > adet - ayrilan else "DEVAM"})
    return sonuc


def _avukat_sec(rnd, avukat_listesi, brans, haric=None):
    adaylar = [a for a in avukat_listesi if a["kod"] != haric and a["durum"] == "DEVAM"]
    if not adaylar:  # tek avukatlı üretimde yeniden atanacak başka avukat yok
        return None
    agirlik = [4 if brans in a["uzman"] else 1 for a in adaylar]
    return rnd.choices(adaylar, weights=agirlik)[0]


def _donemler(rnd, avukat_listesi, brans, verilis, log, dosya_no):
    """Dosyanın atama dönemleri: [(avukat, baslangic, bitis ya da None)]."""
    donemler = []
    atama = verilis + dt.timedelta(days=min(400, int(rnd.expovariate(1 / 40.0)) + 3))
    if rnd.random() < 0.08:
        sulh = "SL-0{}".format(rnd.randint(1, 2))
        log.append([dosya_no, sulh, verilis + dt.timedelta(days=1), atama, "SULH"])
    if atama > KESIT:
        return donemler
    avukat = _avukat_sec(rnd, avukat_listesi, brans)
    zar = rnd.random()
    if zar < 0.10:
        degisim = atama + dt.timedelta(days=rnd.randint(60, 500))
        yeni = None
        if degisim < KESIT:
            yeni = _avukat_sec(rnd, avukat_listesi, brans, avukat["kod"])
        if yeni is not None:
            donemler.append((avukat, atama, degisim))
            log.append([dosya_no, avukat["kod"], atama, degisim, "NORMAL"])
            avukat, atama = yeni, degisim
    bitis = None
    if zar > 0.97:
        bitis = atama + dt.timedelta(days=rnd.randint(20, 300))
        bitis = bitis if bitis < KESIT else None
    donemler.append((avukat, atama, bitis))
    log.append([dosya_no, avukat["kod"], atama, bitis, "NORMAL"])
    return donemler


def _hareketler(rnd, dosya_no, rucu, oran, donemler, ilk_islem, verilis):
    hareketler, toplam = [], 0.0
    if donemler and rnd.random() < 0.05:
        tarih = _gun(rnd, verilis, min(donemler[0][1], KESIT))
        hareketler.append([dosya_no, tarih, round(rucu * 0.05, 2), "TAHSILAT"])
        toplam += rucu * 0.05
    for avukat, bas, bitis in donemler:
        son = min(bitis or KESIT, KESIT)
        bas = max(bas, ilk_islem or bas)
        # Tahsilat yapılıp yapılmaması tahsil_hizi becerisine, tutarı beceriye bağlıdır.
        if bas >= son or rnd.random() > min(0.9, 0.5 * avukat["tahsil_hizi"]):
            continue
        hedef = min(rucu - toplam, rucu * oran * avukat["beceri"] * rnd.lognormvariate(0, 0.4))
        for _ in range(rnd.randint(1, 5)):
            tutar = round(max(0.0, hedef) / 3.0 * rnd.uniform(0.5, 1.5), 2)
            if tutar <= 0:
                continue
            tarih = _gun(rnd, bas, son)
            hareketler.append([dosya_no, tarih, tutar, "TAHSILAT"])
            toplam += tutar
            if rnd.random() < 0.02:
                ters = min(tarih + dt.timedelta(days=rnd.randint(1, 30)), KESIT)
                hareketler.append([dosya_no, ters, -tutar, "TERS_KAYIT"])
                toplam -= tutar
    return hareketler, toplam


def _surec(rnd, dosya_no, esas_tarihi, avukat):
    zar = rnd.random()
    if esas_tarihi is None or zar > 0.40:
        return None
    if zar < 0.25:
        tur, bas = "ITIRAZ", esas_tarihi + dt.timedelta(days=rnd.randint(20, 60))
    elif zar < 0.35:
        tur, bas = "ARABULUCULUK", esas_tarihi
    else:
        return [dosya_no, "DOGRUDAN_DAVA", "", "", ""]
    if bas > KESIT:
        return None
    dava = bas + dt.timedelta(days=int(rnd.expovariate(1 / avukat["dava_hizi"])) + 15)
    if dava > KESIT or rnd.random() < 0.2:
        return [dosya_no, tur, bas, "", ""]
    return [dosya_no, tur, bas, "{}/{}".format(dava.year, rnd.randint(1000, 99999)), dava]


def _kalite_davranis(rnd, avukat_listesi):
    satirlar = []
    seyrek = {a["kod"] for a in avukat_listesi[2:5]}
    for avukat in avukat_listesi:
        if avukat["durum"] != "DEVAM":
            continue
        for _ in range(rnd.choice([1, 2, 2, 3])):
            tarih = _gun(rnd, KESIT - dt.timedelta(days=330), KESIT)
            degerlendiren = "IA-0{}".format(rnd.randint(1, 5))
            for kod in KALITE + DAVRANIS + ESKI_ALANLAR:
                if rnd.random() < (0.6 if avukat["kod"] in seyrek else 0.12):
                    puan = ""
                else:
                    puan = min(5, max(1, int(round(rnd.gauss(avukat["kalite"], 0.6)))))
                satirlar.append([avukat["kod"], tarih, kod, puan, degerlendiren])
    return satirlar


def _rapor_toplam(hareketler, son_avukat, brans_of):
    toplam = {}
    sinir = (KESIT.replace(day=1) - dt.timedelta(days=150)).replace(day=1)
    for dosya_no, tarih, tutar, _ in hareketler:
        if tarih >= sinir and dosya_no in son_avukat:
            anahtar = (son_avukat[dosya_no], tarih.strftime("%Y-%m"), brans_of[dosya_no])
            toplam[anahtar] = toplam.get(anahtar, 0.0) + tutar
    return [[kod, donem, round(tutar, 2), brans]
            for (kod, donem, brans), tutar in sorted(toplam.items())]


def _yaz(hedef, ad, basliklar, satirlar):
    with open(os.path.join(hedef, ad + ".csv"), "w", encoding="utf-8", newline="") as dosya:
        yazici = csv.writer(dosya)
        yazici.writerow(basliklar)
        for satir in satirlar:
            yazici.writerow(["" if deger is None else deger for deger in satir])


def _log_satiri(rnd, satir):
    dosya_no, kod, atama, iptal, tur = satir
    saat = dt.time(rnd.randint(8, 19), rnd.randint(0, 59), rnd.randint(0, 59))
    bicim = "%d/%m/%Y %H:%M:%S"
    iptal_metni = "" if iptal is None or tur == "SULH" else \
        dt.datetime.combine(iptal, saat).strftime(bicim)
    return [dosya_no, kod, dt.datetime.combine(atama, saat).strftime(bicim), iptal_metni,
            "AT{:05d}".format(rnd.randint(1, 99999)), "1", "N"]


def uret(hedef, dosya_sayisi=8000, avukat_sayisi=30, tohum=2026):
    """Bütün sentetik kaynakları hedef klasöre yazar; satır sayılarını döndürür."""
    rnd = random.Random(tohum)
    liste = avukatlar(rnd, avukat_sayisi)
    dosyalar, log, hareketler, esaslar, takip, surecler, son_avukat = [], [], [], [], [], [], {}
    for sira in range(1, dosya_sayisi + 1):
        dosya_no = "D-{:06d}".format(sira)
        brans, _, oran, medyan = rnd.choices(BRANSLAR, weights=[b[1] for b in BRANSLAR])[0]
        rucu = round(medyan * rnd.lognormvariate(0, 0.8), 2)
        verilis = _gun(rnd, dt.date(2021, 1, 1), dt.date(2026, 10, 31))
        donemler = _donemler(rnd, liste, brans, verilis, log, dosya_no)
        esas_tarihi = None
        for avukat, bas, bitis in donemler:
            gecikme = rnd.expovariate(1 / avukat["hiz"]) * (4 if rnd.random() < 0.1 else 1)
            aday = bas + dt.timedelta(days=int(gecikme))
            if aday <= KESIT and (bitis is None or aday < bitis):
                esas_tarihi = aday
                break
        hareket, toplam = _hareketler(rnd, dosya_no, rucu, oran, donemler, esas_tarihi, verilis)
        hareketler += hareket
        kod, bakiye = "R11", round(max(0.0, rucu - toplam), 2)
        if toplam >= 0.95 * rucu:
            kod, bakiye = "R06", 0.0
        elif toplam <= 0 and verilis < dt.date(2022, 6, 1) and rnd.random() < 0.3:
            kod = "R12"
        dosyalar.append([dosya_no, brans, kod, rucu, bakiye, verilis])
        if donemler:
            son_avukat[dosya_no] = donemler[-1][0]["kod"]
        if esas_tarihi is None:
            continue
        esas_no = "{}/{}".format(esas_tarihi.year, rnd.randint(1000, 99999))
        esaslar.append([dosya_no, esas_no, "" if rnd.random() < 0.05 else esas_tarihi])
        dolu = rnd.random() < 0.3
        takip.append([dosya_no, "ICRA", esas_no if dolu else "", "",
                      esas_tarihi if dolu else ""])
        surec = _surec(rnd, dosya_no, esas_tarihi, donemler[-1][0])
        if surec:
            surecler.append(surec)
    acik = [(s[0], s[1], s[2]) for s in log if s[4] == "NORMAL" and s[3] is None]
    bekleme = []
    for dosya_no, kod, atama in rnd.sample(acik, min(25, len(acik))):
        bas = atama + dt.timedelta(days=rnd.randint(1, 5))
        if bas < KESIT:
            bekleme.append([dosya_no, kod, bas, bas + dt.timedelta(days=rnd.randint(3, 20))])
    os.makedirs(hedef, exist_ok=True)
    tablolar = [
        ("kaynak_cekirdek_dosya", ["dosya_no", "brans", "rucu_kodu", "rucu_tutari", "acik_bakiye",
                               "rucuya_verilis_tarihi"], dosyalar),
        ("kaynak_cekirdek_atama_log", ["DOSYA_NO", "AV_KOD", "ATAMA_ZAMANI", "IPTAL_ZAMANI",
                                   "ATAMA_NO", "GRUP_KODU", "ATAMA_TIPI"],
         [_log_satiri(rnd, s) for s in log]),
        ("kaynak_cekirdek_takip", ["dosya_no", "takip_tipi", "esas_no", "mahkeme", "islem_tarihi"],
         takip),
        ("kaynak_rapor_tahsilat_hareketi", ["dosya_no", "hareket_tarihi", "tutar", "hareket_turu",
                                            "hareket_no"],
         [[d, t, _tr(m), h, "H-{:07d}".format(i)] for i, (d, t, m, h) in
          enumerate(hareketler, 1)]),
        ("kaynak_rapor_avukat_toplam", ["avukat_kodu", "donem", "tahsilat_toplami", "brans"],
         _rapor_toplam(hareketler, son_avukat, {d[0]: d[1] for d in dosyalar})),
        ("kaynak_degerlendirme_puan", ["avukat_kodu", "degerlendirme_tarihi", "alt_baslik",
                                        "puan", "degerlendiren"], _kalite_davranis(rnd, liste)),
        ("kaynak_degerlendirme_avukat", ["avukat_kodu", "unvan", "calisma_durumu"],
         [[a["kod"], "Büro " + a["kod"], a["durum"]] for a in liste]),
        ("kaynak_dava_takip_esas", ["dosya_no", "esas_no", "kaynak_tarihi"], esaslar),
        ("kaynak_dava_takip_surec", ["dosya_no", "surec_turu", "baslangic_tarihi", "dava_esas_no",
                            "dava_kaynak_tarihi"], surecler),
        ("kaynak_duzeltme_bekleme", ["dosya_no", "avukat_kodu", "baslangic", "bitis"], bekleme)]
    for ad, basliklar, satirlar in tablolar:
        _yaz(hedef, ad, basliklar, satirlar)
    return {ad: len(satirlar) for ad, _, satirlar in tablolar}


# ---------- yükleme ----------
def _yukle(klasor_adi, yol, veri):
    dataiku.Folder(klasor_adi).upload_data(yol, veri)
    print("{}: {} ({} bayt)".format(klasor_adi, yol, len(veri)))


def ayarlari_yukle():
    dosyalar = dict(AYARLAR, **(PROVA_AYARLARI if PROVA else {}))
    for ad in sorted(dosyalar):
        json.loads(dosyalar[ad])  # bozuk yapıştırma burada durur
        _yukle("ayarlar", ad, dosyalar[ad].encode("utf-8"))


def sentetik_veriyi_yukle():
    gecici = tempfile.mkdtemp()
    try:
        for ad, sayi in sorted(uret(gecici).items()):
            with open(os.path.join(gecici, ad + ".csv"), "rb") as dosya:
                _yukle("kaynak_dosyalari", "sentetik/veri/" + ad + ".csv", dosya.read())
    finally:
        shutil.rmtree(gecici)


ayarlari_yukle()
if PROVA:
    sentetik_veriyi_yukle()
print("Ayarlar yüklendi{}. Şimdi adim_03_veri_kumeleri.py 4. hücresini yeniden çalıştırın."
      .format(" ve sentetik veri yazıldı" if PROVA else ""))
