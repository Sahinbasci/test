/* Sözleşmeli Avukat Performans Sistemi: Dataiku web uygulaması JS sekmesi.
   Kurallar: (1) her bileşen yalnız CIZICILER["kimlik"] bloğunda çizilir; (2) veri alanına
   yalnız al(satir, "alan") ile erişilir; (3) arayüz hesap yapmaz, yalnız biçimlendirir.
   tests/test_arayuz.py bu kuralları sözleşmeye (arayuz/sozlesme.py) karşı denetler. */
(function () {
  "use strict";

  var SUTUN = { tahsilat: "Tahsilat", sure: "Süre ve Performans", kalite: "Hukuki Kalite",
    davranis: "Davranış ve İletişim", birlesik: "Birleşik puan" };
  var SUTUN_KISA = { tahsilat: "Tahsilat", sure: "Süre", kalite: "Kalite", davranis: "Davranış",
    birlesik: "Birleşik" };
  /* Skor rengi: her on puan bir ton. Doksan ve üstü koyu yeşil; puan düştükçe
     sarıya, turuncuya ve kırkın altında kırmızıya geçer. Not ölçeğinden bağımsız görsel bir
     ölçektir; not rozetleri notun rengini taşır. */
  var SKOR_RENK = ["var(--skor-doksan)", "var(--skor-seksen)", "var(--skor-yetmis)", "var(--skor-altmis)",
    "var(--skor-elli)", "var(--skor-kirk)", "var(--skor-alt)"];
  function puanRengi(puan) {
    if (bos(puan) || isNaN(Number(puan))) { return "var(--ana)"; }
    var sira = Math.ceil((100 - Number(puan)) / 10) - 1;  /* doksan–yüz → ilk ton, seksen–doksan → ikinci */
    return SKOR_RENK[Math.max(0, Math.min(SKOR_RENK.length - 1, sira))];
  }
  /* Renk açıklaması: on puanlık basamaklar, yüksekten düşüğe. */
  function skorLejanti() {
    return lejantKutulari(SKOR_RENK.map(function (renk, i) {
      var ust = 100 - 10 * i, alt = ust - 10;
      return [i === 0 ? sayi(alt, 0) + " ve üstü" : i === SKOR_RENK.length - 1 ? sayi(ust, 0) + " altı" :
        sayi(alt, 0) + "–" + sayi(ust, 0), renk];
    }));
  }
  var DURUM = { GECERLI: "Geçerli", VERI_YETERSIZ: "Veri yetersiz", VERI_YOK: "Veri yok",
    EKSIK_DEGERLENDIRME: "Eksik değerlendirme", KAYNAK_BEKLENIYOR: "Kaynak bekleniyor",
    TEYIT_BEKLIYOR: "Teyit bekliyor", GOLGE_MOD: "Gölge mod", YAYIMLANDI: "Hesaplandı",
    EKSIK_SUTUN: "Eksik sütun", BASARILI: "Başarılı", KALDI: "Kaldı", GECTI: "Geçti",
    UYARI: "Uyarı", HESAPLANMADI: "Hesaplanmadı" };
  /* Gecelik birleşik puanın YAYIMLANDI durumu "puana giren sütunlar tam, puan hesaplandı" demektir; her gece
     yeniden hesaplanır. "Yayımlandı" yalnız değişmeyen aylık dönem yayınıdır (Not Geçmişi). */
  var DONEM_DURUM = { YAYIMLANDI: "Yayımlandı" };
  var SEVIYE = { IZLENIYOR: "İzleniyor", SARI: "Sarı", TURUNCU: "Turuncu", KIRMIZI: "Kırmızı",
    KAPANDI: "Kapandı", SONLANDI: "Sonlandı", KOSUL_DISI: "Koşul kalktı",
    KAPSAM_DISI: "Kapsam dışı" };
  var KRITER = { K1: "Kriter 1 · İlk işlem", K2: "Kriter 2 · Dava açma" };
  var DUSUM_DURUMU = { UYGULANDI: "Evet", GOLGE: "Uygulanmadı (gölge mod)",
    GOLGE_DONEMI: "Gölge döneminde, puana girmez" };
  var EKSIK_NEDEN = { AZ_DOSYA: "Dosya sayısı yayın tabanının altında",
    BEKLENEN_SIFIR: "Beklenen tahsilat sıfır", AZ_BEKLENEN: "Beklenen düşüm tabanın altında",
    KAPSAM_DUSUK: "Veri kapsamı düşük", GOLGE_MOD: "Gölge mod" };
  var KAPSAM_DISI = { SULH: "Sulh amaçlı atama", IPTAL: "Hatalı giriş, iptal edildi",
    ESAS_ONCEDEN_VAR: "Esas atamadan önce girilmiş", DOSYA_YOK: "Dosya kaydı yok",
    ESAS_TARIHI_BILINMIYOR: "Esas tarihi bilinmiyor (arşiv öncesi)",
    SUREC_DOGRUDAN_DAVA: "Doğrudan dava", SUREC_KESINLESTI: "Kesinleşen icra",
    SUREC_YOK: "Süreç yok", BASLANGIC_YOK: "Başlangıç tarihi yok",
    KOSUL_SAGLANMIYOR: "Rücu kodu ya da açık bakiye koşulu yok",
    DAVA_ONCEDEN_VAR: "Dava atamadan önce açılmış", SUREC_ATAMA_DISI: "Süreç atama dışında",
    DAVA_TARIHI_BILINMIYOR: "Dava kaydı var, tarihi bilinmiyor (arşiv öncesi)" };
  var BITIS = { IADE: "İade", YENIDEN_ATAMA: "Yeniden atama", IPTAL: "İptal" };
  var SUREC = { ITIRAZ: "İtiraz nedeniyle durdurma", ARABULUCULUK: "Arabuluculuk",
    DOGRUDAN_DAVA: "Doğrudan dava", KESINLESTI: "Kesinleşen icra" };
  var CALISMA = { DEVAM: "Çalışıyor", AYRILDI: "Ayrıldı" };
  var YONTEM = { bekliyor: "Bağlantı bekleniyor", dataiku: "Dataiku veri kümesi", api: "API",
    dosya: "Dosya" };
  var CALISMA_TURU = { GECELIK: "Gecelik", DONEM_SONU: "Dönem sonu" };
  var DENETIM = { ZORUNLU_SUTUN: "Zorunlu sütun", TUR: "Çevrilemeyen değer", BOS: "Boş zorunlu alan",
    SONSUZ: "Sonlu olmayan sayı",
    YINELENEN: "Yinelenen kayıt", BOS_TABLO: "Boş tablo", SATIR_SAPMASI: "Satır sayısı sapması",
    GELECEK_TARIH: "Gelecek tarih", SAYI_BICIMI: "Sayı biçimi", CEKIM_HATASI: "Okuma hatası",
    ATAMA_DOSYA: "Atama logu · dosya ilişkisi", HAREKET_DOSYA: "Tahsilat hareketi · dosya ilişkisi",
    TAHSILAT: "Tahsilat mutabakatı", PUAN_ARALIGI: "Puan aralığı", SUTUN_TAMLIGI: "Sütun tamlığı",
    VERI_KAPSAMI: "Dönem sonunu kapsayan gece", EKSIK_ALAN: "Gelmeyen isteğe bağlı alan",
    TERS_TARIH: "Ters tarih", ESKI_TARIH: "Geçersiz eski tarih", DEGER: "Tanımsız değer",
    OLCEK: "Ölçek dışı puan", BOS_BAKIYE: "Boş açık bakiye", SIFIR_RUCU: "Sıfır rücu tutarı",
    NEGATIF_RUCU: "Negatif rücu tutarı", ESAS_DOSYA: "Esas · dosya ilişkisi",
    TAKIP_DOSYA: "Takip bilgisi · dosya ilişkisi", SUREC_DOSYA: "Süreç · dosya ilişkisi",
    BEKLEME_DOSYA: "Haklı bekleme · dosya ilişkisi", BEKLEME_AVUKAT: "Haklı bekleme · avukat ilişkisi",
    DEGERLENDIRME_AVUKAT: "Değerlendirme · avukat ilişkisi", HAZIRLIK_SURUMU: "Hazırlık sürümü",
    BEKLEME_ATAMA: "Haklı bekleme · atama ilişkisi", AVUKAT_AVUKAT: "Avukat listesi · atama ilişkisi",
    DOLULUK: "Boş değer alanı", PENCERE_DISI: "Pencere dışı değerlendirme",
    DISARIDA_TERS_KAYIT: "Puana girmeyen ters kayıt", SAATSIZ_ATAMA: "Saatsiz aynı gün ataması",
    TAHSILAT_HAREKETI_YOK: "Dosya bazında tahsilat hareketi yok",
    MODEL_TABLOSU: "Kesik ya da okunamayan model tablosu", HESAP_HATASI: "Hesap hatası" };
  var DENETIM_KAYNAGI = { iliski: "Kaynaklar arası", mutabakat: "Mutabakat", donem: "Dönem yayını",
    sonuc: "Sonuç kontrolleri" };
  var SEVIYE_SIRASI = ["KIRMIZI", "TURUNCU", "SARI", "IZLENIYOR", "KAPANDI", "SONLANDI", "KOSUL_DISI",
    "KAPSAM_DISI"];
  /* Branş, alt başlık ve mevcut değerlendirme alanı adları burada yazılmaz: params.json gorunum
     bölümünden ortak.adlar bileşeniyle gelir (kodlar parametreyle değişebilir; tek yer orası). */
  var BRANS = {}, ALT_BASLIK = {}, MEVCUT_ALAN = {};
  /* Kaynakların açıklaması. Sistem adları burada yazılmaz: params.json gorunum.sistem_adlari
     bölümünden ortak.adlar bileşeniyle gelir (SISTEM_ADI). */
  var KAYNAK_ACIKLAMA = { dosya: "Rücu dosyası", atama_log: "Avukat atama logları",
    takip: "Takip bilgileri", tahsilat_hareketi: "Tahsilat hareketleri",
    rapor_avukat_toplam: "Avukat toplamları", degerlendirme: "Değerlendirmeler",
    avukat: "Avukat listesi", esas_goruntu: "Esas görüntüsü", k2_goruntu: "Süreç görüntüsü",
    bekleme: "Haklı bekleme" };
  var SISTEM_ADI = {};
  var NOT_SINIFI = { "A": "not-A", "B+": "not-Bp", "B": "not-B", "B-": "not-Bm", "C": "not-C" };
  /* Branş rengi branşın gorunum.brans_adlari listesindeki sırasıyla sıralı paletten (stil.css
     --brans-1 … ; komşu renkler doğrulandı) gelir; halkada dilimler bu sırayla dizilir. Listede
     olmayan ya da paletin dışında kalan branş nötr renktedir (--brans-bilinmeyen). */
  var BRANS_SIRA = {};
  var BRANS_PALET_BOYU = 7;
  function bransRengi(kod) {
    var sira = Number(BRANS_SIRA[kod]);
    return sira >= 1 && sira <= BRANS_PALET_BOYU ? "var(--brans-" + sira + ")" : "var(--brans-bilinmeyen)";
  }
  function bransSirasi(kod) { return BRANS_SIRA[kod] === undefined ? Infinity : Number(BRANS_SIRA[kod]); }

  var durum = { sayfa: null, kod: null, filtre: { kriter: "", seviye: "", avukat: "" },
    olaylar: {}, eksikAlanlar: {}, notFiltresi: "", avukatArama: "", golge: { K1: false, K2: false }, bekleyen: [],
    okunamayan: [], parametreHatasi: null, sekme: "ozet", bolum: { genel: "ozet", sure: "ozet" } };
  var SAYFALAR = ["genel", "avukat", "sure", "kurallar", "veri"];
  var CIZICILER = {};

  /* ---------- yardımcılar (veriye al() ile erişmez, yalnız değer alır) ---------- */
  function al(satir, alan) {
    if (!satir || !Object.prototype.hasOwnProperty.call(satir, alan)) {
      durum.eksikAlanlar[alan] = true;
      if (window.console) { console.error("Sözleşme dışı alan: " + alan); }
      return undefined;
    }
    return satir[alan];
  }
  function bos(v) { return v === null || v === undefined || v === ""; }
  function kac(v) {
    return String(bos(v) ? "—" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  /* Gösterilen hassasiyete yuvarlanınca sıfır olan değer işaretsiz yazılır (kayan nokta artığı
     eksi sıfır ya da eksi yüzde sıfır görünmez). */
  function yuvarlanmis(v, d) { var x = Number(Number(v).toFixed(d)); return x === 0 ? 0 : x; }
  function sayi(v, ondalik) {
    if (bos(v) || isNaN(Number(v))) { return "—"; }
    var d = ondalik === undefined ? 0 : ondalik;
    return yuvarlanmis(v, d).toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  /* Eşikle karşılaştırılan sayım (olgun dosya, beklenen düşüm, kapsam) aşağı kesilir: yayın
     tabanının hemen altındaki değer yuvarlanıp tabanın kendisi gibi görünmez. */
  function sayim(v, ondalik) {
    if (bos(v) || isNaN(Number(v))) { return "—"; }
    var k = Math.pow(10, ondalik || 0);
    return sayi(Math.floor(Number(v) * k + 1e-9) / k, ondalik);
  }
  function yuzde(v, ondalik, kesik) {
    if (bos(v) || isNaN(Number(v))) { return "—"; }
    var mutlak = (kesik ? sayim : sayi)(Math.abs(Number(v)) * 100, ondalik);
    return (Number(v) < 0 && /[1-9]/.test(mutlak) ? "-%" : "%") + mutlak;
  }
  /* Yüzde olarak gösterilen hassasiyette eksi mi (kırmızı yazı ve işaret aynı kararla). */
  function eksiMi(v, ondalik) { return yuvarlanmis(Number(v) * 100, ondalik || 0) < 0; }
  function tl(v) { return bos(v) ? "—" : sayi(v, 0) + " TL"; }
  /* Kısa tutar (Bin, Mn, Mr). adim verilirse (eksen ızgarası) ondalık adımdan gelir: iki buçukluk
     adımdaki çizgi bir ondalığa yuvarlanıp değerinden sapmaz. */
  function kisa(v, adim) {
    var n = Number(v), birimler = [[1e9, " Mr"], [1e6, " Mn"], [1e3, " Bin"]];
    for (var i = 0; i < birimler.length; i++) {
      /* Bir ondalığa yuvarlanınca birime ulaşan değer üst birimle yazılır (bin değil milyon gibi). */
      if (Math.abs(n) >= birimler[i][0] * (1 - 5e-5)) {
        var b = n / birimler[i][0], ince = adim && Math.abs(adim / birimler[i][0] * 10 -
          Math.round(adim / birimler[i][0] * 10)) > 1e-9;
        return sayi(b, Math.abs(b - Math.round(b)) < 1e-9 ? 0 : ince ? 2 : 1) + birimler[i][1];
      }
    }
    return sayi(n, 0);
  }
  function kisaTl(v) {
    if (bos(v)) { return "—"; }
    var p = kisa(v).split(" ");
    return p[0] + " <small>" + (p[1] ? p[1] + " " : "") + "TL</small>";
  }
  function tarih(v) {
    if (bos(v)) { return "—"; }
    var p = String(v).split(" "), g = p[0].split("-");
    return kac(g.length === 3 ? g[2] + "." + g[1] + "." + g[0] + (p[1] ? " " + p[1] : "") : v);
  }
  var AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
  var AYLAR_UZUN = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
    "Ekim", "Kasım", "Aralık"];
  /* Ham metin döner; çağıran kaçışlar (kac). */
  function ayEtiketi(v, ilk) {
    var g = String(v).split("-");
    if (g.length !== 2) { return { etiket: String(v), alt: "", uzun: String(v) }; }
    var sira = Number(g[1]) - 1;
    return { etiket: AYLAR[sira], alt: ilk || sira === 0 ? g[0] : "", uzun: AYLAR_UZUN[sira] + " " + g[0] };
  }
  /* Aylık grafik noktası: kesitte bitmeyen son ay (kismi) ipucunda ve kartın görünür özetinde
     (kartUstOzet) belirtilir. */
  function kismiNotu(veri) {
    var son = veri[veri.length - 1];
    return son && son.kismi ? "Son ay (" + kac(son.etiket) + ") kesite kadar" : null;
  }
  function ayNoktasi(ay, kismi) {
    var e = ayEtiketi(ay, true);
    return { etiket: e.etiket, yil: e.alt, kismi: kismi, uzun: e.uzun + (kismi ? " (kesite kadar)" : "") };
  }
  function donemEtiketi(v) {  /* ham metin; çağıran kaçışlar */
    var g = String(v).split("-");
    return g.length === 2 ? AYLAR[Number(g[1]) - 1] + " " + g[0] : String(v);
  }
  function rozet(kod, metin) {
    return bos(kod) ? "—" : "<span class='rozet " + kac(kod) + "'>" + kac(metin || kod) + "</span>";
  }
  function durumRozeti(kod) { return rozet(kod, DURUM[kod] || SEVIYE[kod] || kod); }
  /* Dosyası yeterli veri eşiğinin altındaki tahsilat ya da süre puanı (tahsilatta olgun dosya, sürede
     risk altındaki dosya): puan geçerlidir, kırmızı uyarıyla gösterilir (eşik Puanlama Kuralları
     sayfasında). */
  function azVeriRozeti(yeterli, puan) {
    return yeterli === false && !bos(puan) ? "<span class='rozet AZ_VERI' title='Dosya sayısı " +
      "yeterli veri eşiğinin altında; puan az veriyle hesaplandı, güven ayarı onu beklenen düzeye " +
      "yaklaştırır'>Yeterli veri yok</span>" : "";
  }
  function azVeriSatiri(yeterli, puan) {
    var r = azVeriRozeti(yeterli, puan);
    return r ? "<div class='az-veri'>" + r + "</div>" : "";
  }
  /* Gölge kriter bazındadır: parametreyle açılan gölge iki kriteri, yedek yolun zorunlu gölgesi
     yalnız Kriter 1'i kapsar (ortak.durum golge_ilk_islem, golge_dava_acma). */
  function golgeSeviye(kod, kriter) {
    return !!durum.golge[kriter] && (kod === "SARI" || kod === "TURUNCU" || kod === "KIRMIZI");
  }
  function golgeHepsi() { return durum.golge.K1 && durum.golge.K2; }
  function golgeKriterleri() {
    return ["K1", "K2"].filter(function (k) { return durum.golge[k]; }).map(function (k) {
      return KRITER[k]; }).join(" ve ");
  }
  function seviyeRozeti(kod, kriter) {
    if (!golgeSeviye(kod, kriter)) { return rozet(kod, SEVIYE[kod] || kod); }
    return "<span class='rozet golge' title='Gölge mod: bilgi amaçlı'>" + kac(SEVIYE[kod] || kod) + "</span>";
  }
  /* Sayım denetimlerinin değeri tam sayı olarak yazılır (ondalıksız); oranlar iki ondalık. */
  function denetimSayisi(v) { return bos(v) ? "—" : sayi(v, Math.round(Number(v)) === Number(v) ? 0 : 2); }
  function denetimAdi(kod) {
    if (bos(kod)) { return "—"; }
    var p = String(kod).split(":");
    return kac((DENETIM[p[0]] || p[0]) + (p.length > 1 ? " · " + p.slice(1).join(":") : ""));
  }
  function notRozeti(not) {
    return bos(not) ? "—" : "<span class='rozet not " + (NOT_SINIFI[not] || "") + "'>" + kac(not) + "</span>";
  }
  function brans(kod) { return kac(BRANS[kod] || kod); }
  /* Odaklanan rozetin açıklaması ekran okuyucuya da ulaşır (ad = ipucu metni). */
  function ipucuRozeti(sinif, metin, ipucu) {
    return "<span class='rozet " + sinif + "' tabindex='0' role='img' aria-label=\"" + kac(metin + ": " + ipucu) +
      "\" data-ipucu=\"" + kac(kac(ipucu)) + "\">" + kac(metin) + "</span>";
  }
  function unvanMetni(v) { return "<div class='ikincil unvan' title='" + kac(v) + "'>" + kac(v) + "</div>"; }
  function eksikSutunlar(metin) {
    return String(metin).split(",").map(function (e) { return kac(SUTUN[e] || e); }).join(", ");
  }
  function sistemAdi(kod) { return kac(SISTEM_ADI[kod] || kod); }
  function bilgi(metin) {
    return "<i class='bilgi' tabindex='0' role='img' aria-label=\"" + kac(metin) + "\" data-ipucu=\"" +
      kac(kac(metin)) + "\">i</i>";
  }
  /* Kart başlığı: açıklama ekranı kalabalıklaştırmaz, başlığın yanındaki bilgi simgesinde durur
     (başlıkta zaten bilgi simgesi varsa tekrarlanmaz). Veriyle değişen kısa özet (ör. avukat sayısı)
     ve durum uyarısı görünür kalır: kartUstOzet. */
  function kartUst(baslik, aciklama, sag) {
    var ipucu = aciklama && baslik.indexOf("class='bilgi'") < 0 ? bilgi(aciklama.replace(/<[^>]*>/g, "")) : "";
    return kartUstOzet(baslik + ipucu, null, sag);
  }
  function kartUstOzet(baslik, ozet, sag) {
    return "<div class='kart-ust'><div><h2>" + baslik + "</h2>" +
      (ozet ? "<div class='aciklama'>" + ozet + "</div>" : "") + "</div>" +
      (sag ? "<div>" + sag + "</div>" : "") + "</div>";
  }
  function bosDurum(metin, kesik) {
    return "<div class='bos-durum" + (kesik ? " kesik" : "") + "'>" + metin + "</div>";
  }
  function yukleniyor() { return "<div class='yukleniyor'><span></span><span></span><span></span></div>"; }
  function tablo(basliklar, satirlar, sinif) {
    if (!satirlar.length) { return bosDurum("Gösterilecek kayıt yok."); }
    var sirali = (sinif || "").indexOf("siralanabilir") >= 0;
    return "<div class='kaydirma'><table class='tablo " + (sinif || "") + "'><thead><tr>" +
      basliklar.map(function (b) {
        var sayisal = b.charAt(0) === "#", siniflar = (sayisal ? "sayi " : "") + (sirali && b ? "siralanir" : "");
        /* Başlıkta bilgi simgesi varsa sıralama ipucu (title) eklenmez: iki ipucu üst üste açılırdı. */
        var ipucu = b.indexOf("class='bilgi'") < 0 ? " title='Sıralamak için tıklayın ya da Enter tuşuna basın'" : "";
        return "<th" + (siniflar ? " class='" + siniflar + "'" : "") + (sirali && b ? ipucu +
          " tabindex='0' aria-sort='none'" : "") + ">" + (sayisal ? b.slice(1) : b) +
          "</th>";
      }).join("") + "</tr></thead><tbody>" + satirlar.join("") + "</tbody></table></div>";
  }
  function hucre(icerik, sayisal, deger) {
    return "<td" + (sayisal ? " class='sayi'" : "") + (bos(deger) || isNaN(Number(deger)) ? "" :
      " data-deger='" + Number(deger) + "'") + ">" + icerik + "</td>";
  }
  function tabloSirala(th) {
    var tablo = th.closest("table"), govde = tablo.tBodies[0], sira = th.cellIndex;
    var onceki = th.getAttribute("data-yon");
    var artan = onceki ? onceki === "azalan" : !th.classList.contains("sayi");
    Array.prototype.forEach.call(tablo.querySelectorAll("th[data-yon]"), function (b) {
      b.removeAttribute("data-yon");
      b.setAttribute("aria-sort", "none");
    });
    th.setAttribute("data-yon", artan ? "artan" : "azalan");
    th.setAttribute("aria-sort", artan ? "ascending" : "descending");
    function anahtar(tr) {
      var td = tr.cells[sira];
      if (!td) { return null; }
      if (td.hasAttribute("data-deger")) { return Number(td.getAttribute("data-deger")); }
      var metin = td.textContent.trim();
      if (metin === "" || metin === "—") { return null; }
      var gun = /^(\d\d)\.(\d\d)\.(\d{4})/.exec(metin);
      if (gun) { return Number(gun[3] + gun[2] + gun[1]); }
      var sayisal = /^%?(-?\d[\d.]*(,\d+)?)(\s|$)/.exec(metin);
      return sayisal ? Number(sayisal[1].replace(/\./g, "").replace(",", ".")) : metin;
    }
    var satirlar = Array.prototype.slice.call(govde.rows);
    satirlar.sort(function (a, b) {
      var x = anahtar(a), y = anahtar(b);
      if (x === null || y === null) { return x === y ? 0 : x === null ? 1 : -1; }
      var fark = typeof x === "number" && typeof y === "number" ? x - y :
        String(x).localeCompare(String(y), "tr", { numeric: true });
      return artan ? fark : -fark;
    });
    satirlar.forEach(function (tr) { govde.appendChild(tr); });
    durakYenile(govde);
  }
  function bilgiNotu(metin) { return "<div class='bilgi-notu'>" + metin + "</div>"; }
  /* Dosya bazında tahsilat hareketi isteğe bağlı kaynaktır; son gecede bağlantısı beklenirken
     tahsilat bileşenleri boş durumu bununla anlatır (ortak.durum bekleyen_kaynaklar). */
  var TAHSILAT_KAYNAGI = "tahsilat_hareketi";
  var TAHSILAT_BILESENLERI = ["genel.aylik", "genel.yillik", "genel.aylik_avukat", "genel.gruplar",
    "genel.tahsilat_dosya", "genel.brans_oran", "avukat.tahsilat", "avukat.brans", "avukat.aylik"];
  function tahsilatBekleniyor() { return durum.bekleyen.indexOf(TAHSILAT_KAYNAGI) >= 0; }
  /* Kartın kendi başlığı (boş veriyle çizilir) korunur, gövdesi "kaynak bekleniyor" olur. */
  function bekleniyorCiz(kok, kimlik) {
    try { CIZICILER[kimlik](kok, []); } catch (hata) { kok.innerHTML = ""; }
    var ust = kok.querySelector(".kart-ust");
    kok.innerHTML = (ust ? ust.outerHTML : "") + bosDurum(tahsilatBekleniyorMetni(), true);
  }
  function tahsilatBekleniyorMetni() {
    return rozet("KAYNAK_BEKLENIYOR", DURUM.KAYNAK_BEKLENIYOR) + " " + sistemAdi("tahsilat_raporu") +
      " tahsilat hareketleri henüz bağlanmadı; tahsilat sonuçları kaynak gelince üretilir.";
  }
  function sinirla(oran) { return bos(oran) || isNaN(Number(oran)) ? 0 : Math.max(0, Math.min(1, Number(oran))); }
  function cubuk(oran, renk) {
    return "<div class='cubuk'><span style='width:" + (sinirla(oran) * 100).toFixed(1) + "%;" +
      (renk ? "--cubuk-renk:" + renk : "") + "'></span></div>";
  }
  function satirCubuk(ad, deger, oran, renk, alt) {
    return "<div class='satir-cubuk'><span class='ad'>" + ad + "</span><span class='deger'>" + deger +
      "</span>" + cubuk(oran, renk) + (alt ? "<div class='ikincil'>" + alt + "</div>" : "") + "</div>";
  }
  /* Puanlar iki ondalıkla gösterilir: birleşik puan ve not bu hassasiyette hesaplanır; tek ondalıkta
     eşiğin hemen altındaki puan eşiğe yuvarlanmış görünür ve notla çelişirdi. */
  function puanMetni(v) { return bos(v) ? "—" : sayi(v, 2); }
  function skorHucre(v) {
    return bos(v) ? "<span class='ikincil'>—</span>" : "<span class='skor-hucre'><b>" + puanMetni(v) + "</b>" +
      cubuk(Number(v) / 100, puanRengi(v)) + "</span>";
  }
  function kadran(puan, altMetin, renk) {
    var gecerli = !bos(puan), o = gecerli ? sinirla(Number(puan) / 100) : 0;
    var aci = Math.PI * (1 - o), x = 70 + 54 * Math.cos(aci), y = 70 - 54 * Math.sin(aci);
    var yay = gecerli && o > 0 ? "<path d='M16 70 A54 54 0 0 1 " + x.toFixed(2) + " " + y.toFixed(2) +
      "' fill='none' stroke='" + (renk || "var(--ana)") + "' stroke-width='11' stroke-linecap='round'/>" : "";
    return "<svg viewBox='0 0 140 80' role='img' aria-label='" + (gecerli ? puanMetni(puan) : kac(altMetin)) +
      "'><path d='M16 70 A54 54 0 0 1 124 70' fill='none' stroke='var(--gri-zemin)' stroke-width='11' " +
      "stroke-linecap='round'/>" + yay + "<text x='70' y='66' text-anchor='middle' font-size='21' " +
      "font-weight='700' fill='" + (gecerli ? "var(--metin)" : "var(--soluk)") + "' font-family='inherit'>" +
      puanMetni(puan) + "</text></svg>";
  }
  function eksenAdimi(en) {
    var secenek = [4, 5].map(function (adet) {
      var ham = en / adet, us = Math.pow(10, Math.floor(Math.log(ham) / Math.LN10));
      var adim = [1, 2, 2.5, 5, 10].map(function (k) { return k * us; }).filter(function (a) {
        return a >= ham - 1e-9; })[0];
      return { adet: adet, adim: adim, tavan: adim * adet };
    });
    return secenek[1].tavan < secenek[0].tavan ? secenek[1] : secenek[0];
  }
  /* Eksen: pozitif veride sıfırdan başlar; eksi değer (ters kayıt) varsa sıfırın altına uzar ve
     sıfır çizgisi koyu çizilir. Değerler kırpılmaz. */
  function grafikOlcegi(degerler) {
    var ust = Math.max(1, Math.max.apply(null, degerler)), alt = Math.min(0, Math.min.apply(null, degerler));
    if (alt === 0) { var o = eksenAdimi(ust); return { taban: 0, tavan: o.tavan, adim: o.adim, adet: o.adet }; }
    var adim = eksenAdimi(ust - alt).adim, taban = Math.floor(alt / adim) * adim;
    var tavan = Math.max(adim, Math.ceil(ust / adim) * adim);
    return { taban: taban, tavan: tavan, adim: adim, adet: Math.round((tavan - taban) / adim) };
  }
  var grafikSayaci = 0;
  function cizgiGrafik(veriler, seriler, bosMetin) {
    if (!veriler.length) { return bosDurum(bosMetin || "Bu dönemde kayıt yok."); }
    var degerler = [];
    veriler.forEach(function (v) {
      seriler.forEach(function (s) { degerler.push(Number(v[s.anahtar]) || 0); });
    });
    /* Ay ızgarası tahsilatsız ayları sıfırla doldurur; hepsi sıfırsa boş durum gösterilir. */
    if (!degerler.some(function (d) { return d !== 0; })) { return bosDurum(bosMetin || "Bu dönemde kayıt yok."); }
    var olcek = grafikOlcegi(degerler), n = veriler.length, izgara = "", aralik = olcek.tavan - olcek.taban;
    function yukseklik(deger) { return (deger - olcek.taban) / aralik; }
    for (var i = 0; i <= olcek.adet; i++) {
      var deger = olcek.taban + olcek.adim * i;
      izgara += "<div class='cg-izgara" + (olcek.taban < 0 && Math.abs(deger) < 1e-9 ? " sifir" : "") +
        "' style='bottom:" + (yukseklik(deger) * 100) + "%'><span>" + kisa(deger, olcek.adim) + "</span></div>";
    }
    function nokta(v, j, s) {
      return ((j + 0.5) / n * 1000).toFixed(1) + "," +
        (1000 - yukseklik(Number(v[s.anahtar]) || 0) * 1000).toFixed(1);
    }
    var sifirY = (1000 - yukseklik(0) * 1000).toFixed(1), tekNokta = "";
    var cizimler = seriler.map(function (s) {
      var noktalar = veriler.map(function (v, j) { return nokta(v, j, s); });
      if (n === 1) {  /* tek ayda çizgi oluşmaz: değer nokta olarak gösterilir */
        var p = noktalar[0].split(",");
        tekNokta += "<i class='cg-nokta' style='left:" + p[0] / 10 + "%;top:" + p[1] / 10 + "%;" +
          "border-color:" + s.renk + "'></i>";
        return "";
      }
      var ilkX = noktalar[0].split(",")[0], sonX = noktalar[n - 1].split(",")[0];
      /* Alan dolgusu üstte belirgin, tabana doğru solar (dikey geçiş, seri rengi). */
      var kimlik = "cg-dolgu-" + (++grafikSayaci);
      var alan = s.alan ? "<defs><linearGradient id='" + kimlik + "' x1='0' y1='0' x2='0' y2='1'>" +
        "<stop offset='0' stop-color='" + s.renk + "' stop-opacity='0.22'/><stop offset='1' stop-color='" +
        s.renk + "' stop-opacity='0'/></linearGradient></defs><path d='M" + ilkX + "," + sifirY + " L" +
        noktalar.join(" L") + " L" + sonX + "," + sifirY + " Z' fill='url(#" + kimlik + ")'/>" : "";
      return alan + "<polyline points='" + noktalar.join(" ") + "' fill='none' stroke='" + s.renk +
        "' stroke-width='" + (s.kesik ? 1.5 : 2.5) + "' vector-effect='non-scaling-stroke' " +
        "stroke-linejoin='round' stroke-linecap='round'" + (s.kesik ? " stroke-dasharray='5 4'" : "") + "/>";
    }).join("");
    var hedefler = veriler.map(function (v, sira) {
      var ipucu = "<b>" + kac(v.uzun) + "</b><table>" + seriler.map(function (s) {
        return "<tr><td>" + kac(s.ad) + "</td><td>" + tl(v[s.anahtar]) + "</td></tr>";
      }).join("") + (v.ek ? "<tr><td>" + kac(v.ek[0]) + "</td><td>" + kac(v.ek[1]) + "</td></tr>" : "") +
        "</table>";
      var ad = v.uzun + ": " + seriler.map(function (s) { return s.ad + " " + tl(v[s.anahtar]); })
        .join(", ") + (v.ek ? ", " + v.ek[0] + " " + v.ek[1] : "");
      /* Aylar tek sekme durağıdır (öteki grafikler gibi); ok tuşlarıyla gezilir. */
      return "<div class='cg-hedef' data-gezinme tabindex='" + (sira ? -1 : 0) + "' role='img' aria-label=\"" +
        kac(ad) + "\" data-ipucu=\"" +
        kac(ipucu) + "\"></div>";
    }).join("");
    /* Uzun seride etiketler son noktadan geriye eşit aralıkla seçilir (en çok ~12); yıl yalnız
       değiştiği etikette yazılır. Kesitte bitmeyen son ay ipucunda ve kartın görünür özetinde
       (kismiNotu) belirtilir. */
    var seyrek = Math.ceil(n / 12), oncekiYil = null;
    var eksen = veriler.map(function (v, j) {
      if ((n - 1 - j) % seyrek !== 0) { return "<span></span>"; }
      var alt = v.yil && v.yil !== oncekiYil ? v.yil : "";
      oncekiYil = v.yil || oncekiYil;
      return "<span>" + kac(v.etiket) + (alt ? "<small>" + kac(alt) + "</small>" : "") + "</span>";
    }).join("");
    var lejant = seriler.length > 1 ? "<div class='lejant'>" + seriler.map(function (s) {
      return "<span><i class='" + (s.kesik ? "kesik" : "") + "' style='border-color:" + s.renk + "'></i>" +
        kac(s.ad) + "</span>";
    }).join("") + "</div>" : "";
    return "<div class='cizgi-grafik'><div class='cg-alan'>" + izgara + "<svg viewBox='0 0 1000 1000' " +
      "preserveAspectRatio='none'>" + cizimler + "</svg>" + tekNokta + "<div class='cg-hedefler'>" + hedefler +
      "</div></div><div class='cg-eksen'>" + eksen + "</div>" + lejant + "</div>";
  }
  function pasta(kalemler, merkez, merkezAlt, basliklar) {
    var toplam = kalemler.reduce(function (t, k) { return t + (Number(k.deger) || 0); }, 0) || 1;
    var r = 58, cevre = 2 * Math.PI * r, birikim = 0;
    var dilimler = kalemler.map(function (k) {
      var pay = (Number(k.deger) || 0) / toplam, uzunluk = Math.max(0, pay * cevre - 2);
      var dilim = "<circle cx='75' cy='75' r='" + r + "' fill='none' stroke='" + k.renk +
        "' stroke-width='22' stroke-dasharray='" + uzunluk.toFixed(2) + " " + cevre.toFixed(2) +
        "' stroke-dashoffset='" + (-birikim).toFixed(2) + "' transform='rotate(-90 75 75)'/>";
      birikim += pay * cevre;
      return dilim;
    }).join("");
    var lejant = kalemler.map(function (k, i) {
      return "<div><i style='background:" + k.renk + "'></i><span>" + k.ad + "</span>" +
        "<span class='sayi'>" + sayi(k.deger, 0) + "</span><span class='ikincil'>" +
        yuzde((Number(k.deger) || 0) / toplam, 1) + "</span><span class='ek'>" + (k.ek || "") + "</span></div>";
    }).join("");
    if (basliklar) {
      lejant = "<div class='baslik-satiri'><span></span>" + basliklar.map(function (b, i) {
        return "<span" + (i ? " style='text-align:right'" : "") + ">" + b + "</span>";
      }).join("") + "</div>" + lejant;
    }
    /* Halka süstür; verinin metin hâli yanındaki lejanttır (ekran okuyucu onu okur). */
    return "<div class='pasta'><svg viewBox='0 0 150 150' aria-hidden='true'>" + dilimler + "<text x='75' y='76' " +
      "text-anchor='middle' font-size='22' font-weight='700' fill='var(--metin)' font-family='inherit'>" +
      merkez + "</text><text x='75' y='94' text-anchor='middle' font-size='11' fill='var(--soluk)' " +
      "font-family='inherit'>" + kac(merkezAlt) + "</text></svg><div class='pasta-lejant'>" + lejant +
      "</div></div>";
  }
  function istatistik(ad, deger, alt) {
    return "<div class='istatistik'><div class='kpi-ad'>" + ad + "</div><div class='deger'>" + deger +
      "</div>" + (alt ? "<div class='kpi-alt'>" + alt + "</div>" : "") + "</div>";
  }
  /* Gösterge kartı simgeleri (ton: mavi, yesil, turuncu, lacivert; stil.css --ton-*). */
  var KPI_IKON = {
    dosya: "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.9' stroke-linecap='round' " +
      "stroke-linejoin='round'><path d='M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z'/></svg>",
    tahsilat: "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.9' stroke-linecap='round' " +
      "stroke-linejoin='round'><path d='M4 17l5-5 4 4 7-8'/><path d='M15 8h5v5'/></svg>",
    gecikme: "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.9' stroke-linecap='round' " +
      "stroke-linejoin='round'><circle cx='12' cy='13' r='8'/><path d='M12 9v4l2.5 2.5M9 2h6'/></svg>",
    puan: "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.9' stroke-linecap='round' " +
      "stroke-linejoin='round'><path d='M12 3l2.6 5.5 6 .8-4.4 4.2 1.1 6-5.3-2.9-5.3 2.9 1.1-6L3.4 9.3l6-.8z'/></svg>"
  };
  function kpi(ad, deger, alt, secenek) {
    var o = secenek || {};
    var ikon = o.ikon ? "<span class='kpi-ikon " + (o.ton || "mavi") + "'>" + KPI_IKON[o.ikon] + "</span>" : "";
    return "<div class='kpi " + (o.sinif || "") + "'><div class='kpi-ust'>" + ikon + "<div class='kpi-ad'>" + ad +
      (o.bilgi ? bilgi(o.bilgi) : "") + "</div></div><div class='kpi-deger'>" + deger + "</div><div class='kpi-alt'>" +
      (alt || "&nbsp;") + "</div>" + (o.ek || "") + "</div>";
  }
  /* Ayrıntı penceresi: açılınca odak Kapat düğmesine gelir, Tab pencerenin içinde döner, kapanınca
     odak pencereyi açan öğeye döner. Pencerenin adı içindeki #cekmece-baslik öğesidir. */
  var cekmeceDonus = null;
  function cekmeceAc(html) {
    var c = document.getElementById("cekmece"), a = document.getElementById("cekmece-arka");
    cekmeceDonus = document.activeElement;
    c.innerHTML = html; c.hidden = false; a.hidden = false;
    var k = c.querySelector("[data-kapat]");
    if (k) { k.onclick = cekmeceKapat; k.focus(); } else { c.focus(); }
  }
  function cekmeceKapat() {
    var c = document.getElementById("cekmece");
    if (c.hidden) { return; }
    c.hidden = true;
    document.getElementById("cekmece-arka").hidden = true;
    if (cekmeceDonus && document.body.contains(cekmeceDonus)) { cekmeceDonus.focus(); }
    cekmeceDonus = null;
  }
  function cekmeceOdak(e) {
    var c = document.getElementById("cekmece");
    if (e.key !== "Tab" || c.hidden) { return; }
    var odaklar = c.querySelectorAll("button, select, input, a[href]");
    var ilk = odaklar[0], son = odaklar[odaklar.length - 1], etkin = document.activeElement;
    if (!ilk) { e.preventDefault(); c.focus(); return; }
    if (e.shiftKey && (etkin === ilk || !c.contains(etkin))) { e.preventDefault(); son.focus(); }
    if (!e.shiftKey && (etkin === son || !c.contains(etkin))) { e.preventDefault(); ilk.focus(); }
  }
  /* Gezinme grubu: aynı kaptaki satırlar ya da noktalar tek sekme durağıdır (uzun listede
     yüzlerce durak olmasın). Komşu, tuşa basıldığı andaki görünür sıradan bulunur; süzme ve
     sıralamadan sonra durak ilk görünür öğeye taşınır (durakYenile). */
  var GEZINME = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };
  function gorunenler(el) {
    return Array.prototype.filter.call(el.parentNode.children, function (o) {
      return o.hasAttribute("data-gezinme") && o.offsetParent !== null;
    });
  }
  function durakYenile(kap) {
    var gruplar = [];
    Array.prototype.forEach.call(kap.querySelectorAll("[data-gezinme]"), function (o) {
      o.tabIndex = -1;
      if (gruplar.indexOf(o.parentNode) < 0) { gruplar.push(o.parentNode); }
    });
    gruplar.forEach(function (g) {
      var ilk = Array.prototype.filter.call(g.children, function (o) {
        return o.hasAttribute("data-gezinme") && o.style.display !== "none";
      })[0];
      if (ilk) { ilk.tabIndex = 0; }
    });
  }
  function gez(e, el) {
    var liste = gorunenler(el), sira = liste.indexOf(el);
    var hedef = e.key === "Home" ? 0 : e.key === "End" ? liste.length - 1 :
      GEZINME[e.key] ? sira + GEZINME[e.key] : null;
    if (hedef === null || sira < 0 || !liste[hedef]) { return; }
    e.preventDefault();
    liste.forEach(function (o) { o.tabIndex = -1; });
    liste[hedef].tabIndex = 0;
    liste[hedef].focus();
  }
  /* Tıklanan satır ve öğeler klavyeyle de açılır (Enter ya da boşluk). */
  function tiklamaBagla(kok, secici, isleyici) {
    var ogeler = Array.prototype.slice.call(kok.querySelectorAll(secici));
    ogeler.forEach(function (el) {
      el.addEventListener("click", function () { isleyici(el); });
      if (/^(BUTTON|A|SELECT|INPUT)$/.test(el.tagName)) { return; }
      var grup = el.tagName === "TR" || el.classList.contains("dg-nokta");
      if (grup) { el.setAttribute("data-gezinme", ""); } else { el.tabIndex = 0; }
      if (el.tagName !== "TR") { el.setAttribute("role", "button"); }
      el.addEventListener("keydown", function (e) {
        if (e.target !== el) { return; }
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); isleyici(el); return; }
        if (grup) { gez(e, el); }
      });
    });
    durakYenile(kok);
  }
  function ipucuBagla() {
    var kutu = document.getElementById("ipucu");
    function goster(el, x, y) {
      kutu.innerHTML = el.getAttribute("data-ipucu");
      kutu.classList.add("acik");
      var g = kutu.offsetWidth, h = kutu.offsetHeight;
      kutu.style.left = Math.max(8, Math.min(window.innerWidth - g - 8, x + 14)) + "px";
      kutu.style.top = Math.max(8, Math.min(window.innerHeight - h - 8, y - h - 10)) + "px";
    }
    function gizle() { kutu.classList.remove("acik"); }
    document.addEventListener("mousemove", function (e) {
      var el = e.target.closest ? e.target.closest("[data-ipucu]") : null;
      if (el) { goster(el, e.clientX, e.clientY); } else { gizle(); }
    });
    document.addEventListener("focusin", function (e) {
      var el = e.target.closest ? e.target.closest("[data-ipucu]") : null;
      if (el) { var r = el.getBoundingClientRect(); goster(el, r.left + r.width / 2, r.top); } else { gizle(); }
    });
    window.addEventListener("scroll", gizle, { passive: true });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { gizle(); }
      var sinif = e.target.classList;
      if (sinif && (sinif.contains("dg-sutun") || sinif.contains("kutu-satir") || sinif.contains("cg-hedef"))) {
        gez(e, e.target);
      }
    });
  }

  /* ---------- dağılım grafikleri (veri arka uçta sayılır; burada yalnız çizilir) ---------- */
  /* Puan taşıyan öğeler on puanlık skor ölçeğiyle (puanRengi) renklenir; tek seri tek renktir. */
  var PUAN_UST = 100;  /* puan ölçeğinin üst sınırı (bütün sütunlar 0-100) */
  var REF_ADIM = 16;  /* üst üste gelen referans etiketleri arasındaki dikey aralık (piksel) */
  var BEKLENEN_ORAN = 1;  /* gerçekleşen / beklenen = 1: beklenen düzey (tanım gereği) */
  var BAYRAK_RENK = { YOK: "var(--seri)", SARI: "var(--sari)", TURUNCU: "var(--turuncu)",
    KIRMIZI: "var(--kirmizi)" };
  var BAYRAK_ADI = { YOK: "Bayrak oluşmadan", SARI: "Sarıdan sonra", TURUNCU: "Turuncudan sonra",
    KIRMIZI: "Kırmızıdan sonra" };
  /* Sayım ekseni (avukat, dönem, dosya sayısı): adım en az 1 ve tam sayıdır. */
  function sayimEkseni(en) {
    var o = eksenAdimi(Math.max(en, 1));
    if (o.adim >= 1 && o.adim % 1 === 0) { return o; }
    var adim = Math.max(1, Math.ceil(o.adim));
    return { adim: adim, tavan: Math.max(adim, Math.ceil(en / adim) * adim) };
  }
  function olcekCizgileri(tavan, adim) {
    var izgara = "";
    for (var d = 0; d <= tavan + 1e-9; d += adim) {
      izgara += "<div class='cg-izgara' style='bottom:" + (d / tavan * 100) + "%'><span>" + sayi(d, 0) +
        "</span></div>";
    }
    return izgara;
  }
  /* kutular: [{alt, ust, parcalar: [{adet, renk, ad}], ipucu, ad}]; xEtiketleri: [[konum %, metin]] */
  /* Dikey referanslar: { sol, genislik (yüzde; 0 ise çizgi), ad, renk }. Birden çok etiket üst
     üste binmesin diye basamaklanır; etiket yazısı metin rengindedir, çizgi kendi rengindedir. */
  function referanslar(cizgiler) {
    return (cizgiler || []).map(function (c, i) {
      return "<div class='dg-referans" + (c.genislik ? " bant" : "") + "' style='left:" + c.sol + "%;width:" +
        (c.genislik || 0) + "%;border-color:" + (c.renk || "var(--etiket)") + "'><span style='top:" +
        (-REF_ADIM * (i + 1)) + "px'>" + kac(c.ad) + "</span></div>";
    }).join("");
  }
  /* Arka plan bölgeleri: { sol, genislik (yüzde), sinif (sari | turuncu | golge), ad }. */
  function bolgeCiz(bolgeler) {
    return (bolgeler || []).map(function (b) {
      return "<div class='bolge " + b.sinif + "' style='left:" + b.sol + "%;width:" + b.genislik + "%'><span>" +
        kac(b.ad) + "</span></div>";
    }).join("");
  }
  function histogram(kutular, xEtiketleri, cizgiler, yukseklik, bolgeler) {
    var en = Math.max.apply(null, kutular.map(function (k) {
      return k.parcalar.reduce(function (t, p) { return t + p.adet; }, 0);
    }).concat([1]));
    var o = sayimEkseni(en);
    /* Çubuklar tek sekme durağıdır; ok tuşlarıyla gezilir (gez, belge düzeyinde bağlı). */
    var cubuklar = kutular.map(function (k, i) {
      var parca = k.parcalar.filter(function (p) { return p.adet > 0; }).map(function (p) {
        return "<i style='height:" + (p.adet / o.tavan * 100) + "%;background:" + p.renk + "'></i>";
      }).join("");
      return "<div class='dg-sutun' data-gezinme tabindex='" + (i ? -1 : 0) + "' role='img' aria-label=\"" +
        kac(k.ad) + "\" data-ipucu=\"" + kac(k.ipucu) + "\">" + parca + "</div>";
    }).join("");
    var eksen = xEtiketleri.map(function (e) {
      return "<span style='left:" + e[0] + "%'>" + kac(e[1]) + "</span>";
    }).join("");
    /* Her referans etiketi çizim alanının üstünde bir satır kaplar; dolgu etiket sayısına göre. */
    var etiketSayisi = (cizgiler || []).length;
    return "<div class='dagilim'" + (etiketSayisi ? " style='padding-top:" + REF_ADIM * (etiketSayisi + 1) +
      "px'" : "") + "><div class='dg-alan' style='height:" +
      (yukseklik || 200) + "px'>" + bolgeCiz(bolgeler) + olcekCizgileri(o.tavan, o.adim) +
      "<div class='dg-cubuklar'>" + cubuklar +
      "</div>" + referanslar(cizgiler) +
      "</div><div class='dg-eksen'>" + eksen + "</div></div>";
  }
  function lejantKutulari(kalemler) {
    return "<div class='lejant'>" + kalemler.map(function (k) {
      return "<span><i class='kutu' style='background:" + k[1] + "'></i>" + kac(k[0]) + "</span>";
    }).join("") + "</div>";
  }
  /* Eksen etiketleri veriden: onun (uzun eksende yirmi beşin) katı olan kutu sınırları ve son kutunun üst sınırı. */
  function kutuEtiketleri(kutular) {
    var n = kutular.length, etiket = [], adim = n > 12 ? 25 : 10;
    kutular.forEach(function (k, i) {
      if (Number(k.alt) % adim === 0) { etiket.push([i / n * 100, sayi(k.alt, 0)]); }
    });
    if (n) { etiket.push([100, sayi(kutular[n - 1].ust, 0)]); }
    return etiket;
  }

  /* ---------- ortak ---------- */
  CIZICILER["ortak.adlar"] = function (kok, s) {
    var hedef = { sistem: SISTEM_ADI, brans: BRANS, alt_baslik: ALT_BASLIK, mevcut_alan: MEVCUT_ALAN };
    s.forEach(function (r) {
      var tur = al(r, "tur"), kod = al(r, "kod");
      if (hedef[tur]) { hedef[tur][kod] = al(r, "ad"); }
      if (tur === "brans") { BRANS_SIRA[kod] = al(r, "sira"); }
    });
  };

  CIZICILER["ortak.durum"] = function (kok, s) {
    var d = s[0] || {}, kirmizi = al(d, "acik_kirmizi");
    durum.golge = { K1: al(d, "golge_ilk_islem") === true, K2: al(d, "golge_dava_acma") === true };
    durum.bekleyen = al(d, "bekleyen_kaynaklar") || [];
    durum.okunamayan = al(d, "okunamayan") || [];
    durum.parametreHatasi = al(d, "parametre_hatasi");
    var golge = al(d, "golge_mod") === true, hepsi = golgeHepsi();
    /* Menü ve zil sayacı her sayfa yanıtıyla güncellenir; yeni gecenin sayısı hangi sayfa
       açıksa orada görünür. Sayaç iki kriterin kırmızısını sayar; ikisi de gölgedeyse nötrdür. */
    Array.prototype.forEach.call(document.querySelectorAll(".rozet-sayi"), function (r) {
      r.classList.toggle("notr", hepsi);
      r.textContent = kirmizi ? sayi(kirmizi, 0) : "";
    });
    /* Üst şerit ekranda yalnız dikkat isteyen durumu gösterir (veri okunamadı, parametre geçersiz,
       gölge mod, kurallar değişti, gecelik çalışma ya da dönem yayını kaldı). Kesit, son güncelleme,
       son çalışma ve hesap sürümü yazdırılan çıktıda yer alır: basılı raporda verinin hangi tarihe
       ait olduğu görünür (stil.css, yalniz-baski). */
    var karar = al(d, "son_karar"), donem = al(d, "son_donem_karari"), hata = durum.parametreHatasi;
    kok.innerHTML = "<span class='yalniz-baski'>Kesit <b>" + tarih(al(d, "kesit")) + "</b></span>" +
      "<span class='yalniz-baski'>Son güncelleme <b>" + tarih(al(d, "son_guncelleme")) + "</b></span>" +
      "<span class='" + (bos(karar) || karar === "GECTI" ? "yalniz-baski" : "uyari-hap") + "'>Son gecelik " +
      "çalışma " + durumRozeti(karar) + "</span>" + (donem === "KALDI" ? "<span class='uyari-hap'>Dönem " +
      "yayını " + durumRozeti(donem) + "</span>" : "") +
      (durum.okunamayan.length ? ipucuRozeti("KALDI", "Veri okunamadı", "Okunamayan tablolar: " +
        durum.okunamayan.join(", ") + ". Bu tablolar ekranda yokmuş gibi gösterilir; birkaç saniye sonra " +
        "sayfayı yeniden açın. Sorun sürerse veri bağlantısını ya da yetkiyi denetleyin.") : "") +
      (hata ? ipucuRozeti("KALDI", "Parametre dosyası geçersiz", "Gecelik çalışma bu dosyayla başlamaz; " +
        "hatalar Puanlama Kuralları sayfasında: " + hata) : "") +
      (golge ? ipucuRozeti("GOLGE_MOD", "Gölge mod", (hepsi ? "Süre" : golgeKriterleri()) + " bayrakları " +
        "hesaplanır ama kesinleşmemiştir: e-posta gönderilmez, puan düşümü uygulanmaz" + (hepsi ? " ve süre " +
        "puanı üretilmez. Sayılar bilgi amaçlıdır." : ". Öteki kriter canlıdır.")) : "") +
      (al(d, "kural_degisti") === true ? ipucuRozeti("UYARI", "Kurallar değişti", "Parametreler ya da " +
        "hesap kodu son başarılı gecelik çalışmadan sonra değişti. Ekrandaki sonuçlar önceki kurallarla " +
        "hesaplandı; ilk gecelik çalışmada güncellenir.") : "") +
      "<span class='yalniz-baski'>Sürüm <span class='mono'>" + kac(al(d, "hesap_surumu")) + "</span></span>";
  };

  /* ---------- Genel Bakış ---------- */
  CIZICILER["genel.kpi"] = function (kok, s) {
    var d = s[0];
    var sari = al(d, "acik_sari"), turuncu = al(d, "acik_turuncu"), kirmizi = al(d, "acik_kirmizi");
    var gecikme, hepsi = golgeHepsi(), biri = durum.golge.K1 || durum.golge.K2;
    if (al(d, "sure_verisi")) {
      var toplam = (sari || 0) + (turuncu || 0) + (kirmizi || 0), payda = toplam || 1;
      /* Sayılar iki kriterin toplamıdır: ikisi de gölgedeyse nötr, biri gölgedeyse not düşülür. */
      gecikme = kpi("Aktif gecikme", "<span" + (kirmizi && !hepsi ? " style='color:var(--kirmizi)'" : "") +
        ">" + sayi(toplam, 0) + "</span>", hepsi ? "Gölge mod · bilgi amaçlı" : sayi(kirmizi, 0) +
        " kırmızı · " + sayi(turuncu, 0) + " turuncu · " + sayi(sari, 0) + " sarı" +
        (biri ? "<br>" + kac(golgeKriterleri()) + " gölge modda" : ""),
        { bilgi: "Henüz işlem yapılmamış, bayrağı süren dosyalar (Kriter 1 ve Kriter 2). Sarı: uyarı, " +
          "turuncu: puan düşümü, kırmızı: kritik gecikme. İşlem girilince gecikme kapanır, geçmişi saklanır" +
          (biri ? ". Gölge moddaki kriterde (" + golgeKriterleri() + ") kesinleşmemiştir; e-posta ve puan " +
          "düşümü uygulanmaz" : ""), ikon: "gecikme", ton: "turuncu",
        ek: "<div class='bayrak-seridi'><span style='flex:" + (kirmizi || 0) / payda +
        ";background:" + bayrakRengi("KIRMIZI", hepsi) + "'></span><span style='flex:" + (turuncu || 0) / payda +
        ";background:" + bayrakRengi("TURUNCU", hepsi) + "'></span><span style='flex:" + (sari || 0) / payda +
        ";background:" + bayrakRengi("SARI", hepsi) + "'></span></div>" });
    } else {
      gecikme = kpi("Aktif gecikme", "—", sistemAdi("dava_takip") + " verisi bekleniyor",
        { sinif: "bekliyor", ikon: "gecikme", ton: "turuncu" });
    }
    var yazilmayan = al(d, "atanamayan_tahsilat"), oran = al(d, "tahsilat_orani");
    var tahsilatAlt = bos(oran) && tahsilatBekleniyor() ? sistemAdi("tahsilat_raporu") + " tahsilat hareketleri " +
      "bekleniyor" : "Olgun dosyalarda, avukata yazılan" + (bos(yazilmayan) ? "" : "<br>Avukata yazılmayan: " +
      kisaTl(yazilmayan));
    kok.innerHTML = [
      kpi("Aktif dosya", sayi(al(d, "aktif_dosya"), 0), "Rücu tutarı " + kisaTl(al(d, "aktif_rucu_tutari")),
        { bilgi: "Kesitte sözleşmeli avukatta açık olan atama dönemleri (sulh ve iptal hariç) ve bu dosyaların " +
          "rücu tutarı toplamı (kaynak: " + SISTEM_ADI.cekirdek + ")", ikon: "dosya", ton: "mavi" }),
      kpi("Tahsilat oranı", yuzde(oran, 1), tahsilatAlt,
        { bilgi: "Olgun dosyalarda avukata yazılan tahsilat ÷ bu dosyaların rücu tutarı (yeniden atanan dosyada " +
          "avukatların elde tutma payıyla). Her tahsilat, o gün " +
          "dosyayı elinde tutan avukata yazılır. Avukata yazılmayan: olgun dosyalarda hiçbir avukata yazılmayan " +
          "tahsilat (dosya atanmadan önce, sulh döneminde ya da iki atama arasında); puana girmez.",
          ikon: "tahsilat", ton: "yesil", sinif: bos(oran) && tahsilatBekleniyor() ? "bekliyor" : "" }),
      gecikme,
      kpi("Puanı hesaplanan", sayi(al(d, "yayimlanan"), 0) + " <small>/ " +
        sayi(al(d, "avukat_sayisi"), 0) + "</small>", "Puana giren sütunları tam olan avukat",
        { bilgi: "Birleşik puan, not ve sıra yalnız puana giren sütunların hepsi geçerliyse hesaplanır; her gece " +
          "yeniden hesaplanır, aylık dönem yayını Not Geçmişi'ndedir", ikon: "puan", ton: "lacivert" })
    ].join("");
  };


  CIZICILER["genel.sutun_durumu"] = function (kok, s) {
    var bekleyenler = [];
    var satirlar = s.map(function (r) {
      var bekleme = al(r, "bekleme_nedeni"), ort = al(r, "ortalama");
      if (bekleme) {
        bekleyenler.push(kac(SUTUN[al(r, "sutun")] || al(r, "sutun")) + " (" + kac(DURUM[bekleme] || bekleme)
          .toLocaleLowerCase("tr-TR") + ")");
      }
      return "<tr>" + hucre("<b>" + kac(SUTUN[al(r, "sutun")] || al(r, "sutun")) + "</b>") +
        hucre(bekleme ? rozet(bekleme, DURUM[bekleme]) : sayi(al(r, "gecerli"), 0) + " avukat", true) +
        hucre(bekleme ? "—" : sayi(al(r, "gecersiz"), 0), true) +
        hucre(bekleme || bos(ort) ? "<span class='ikincil'>—</span>" : skorHucre(ort), true) + "</tr>";
    });
    kok.innerHTML = kartUst("Sütun Durumu " + bilgi("Her sütunda puanı üretilen avukat sayısı ve " +
      "puanların ortalaması; puan üretilemeyenler veri yetersiz ya da eksik değerlendirmedir"),
      "Dört performans sütununda puan üretimi ve ortalama puan") + (bekleyenler.length ?
      bilgiNotu("<b>Birleşik puan ve genel sıra henüz hesaplanmıyor.</b> Bekleyen sütunlar: " +
        bekleyenler.join(", ") + ". Hazır sütunlar aşağıda ayrı gösterilir.") : "") +
      "<div class='kart-govde dolu'>" + tablo(["Sütun", "#Puanlanan", "#Puan yok", "#Ortalama puan"],
        satirlar) + "</div>";
  };

  CIZICILER["genel.aylik"] = function (kok, s) {
    var veri = s.map(function (r) {
      var v = ayNoktasi(al(r, "ay"), al(r, "kismi") === true);
      v.yazilan = al(r, "yazilan");
      v.yazilamayan = al(r, "yazilamayan");
      return v;
    });
    kok.innerHTML = kartUstOzet("Aylık Tahsilat" + bilgi("Hareket tarihindeki avukata yazılan ve hiçbir avukata " +
      "yazılmayan tutar"), kismiNotu(veri)) +
      cizgiGrafik(veri, [{ anahtar: "yazilan", ad: "Avukata yazılan", renk: "var(--ana)", alan: true },
        { anahtar: "yazilamayan", ad: "Avukata yazılmayan", renk: "var(--soluk)", kesik: true }],
        "Bu dönemde tahsilat yok.");
  };

  CIZICILER["genel.dagilim"] = function (kok, s) {
    var sutunlar = {}, sira = [];
    s.forEach(function (r) {
      var ad = al(r, "sutun");
      if (!sutunlar[ad]) {
        sutunlar[ad] = { kutular: [], ortanca: al(r, "ortanca"), toplam: al(r, "toplam"), taban: al(r, "taban") };
        sira.push(ad);
      }
      sutunlar[ad].kutular.push({ alt: al(r, "alt"), ust: al(r, "ust"), adet: al(r, "adet"),
        not: al(r, "not_adi") });
    });
    if (!sira.length) {
      kok.innerHTML = kartUst("Puan Dağılımı", "Avukatların sütun ve birleşik puanlarının dağılımı") +
        bosDurum("Henüz geçerli puan yok.");
      return;
    }
    var secili = sutunlar[durum.dagilimSutun] ? durum.dagilimSutun : (sutunlar.birlesik ? "birlesik" : sira[0]);
    var veri = sutunlar[secili], birlesik = secili === "birlesik";
    /* Eksen ilk dolu kutunun bir öncesinden başlar: puanlar dar aralıkta toplanınca çubuklar
       sıkışmaz. Beklenen düzey çizgisi görünen aralığa göre konumlanır. */
    var bas = 0;
    while (bas < veri.kutular.length - 1 && !(Number(veri.kutular[bas].adet) > 0)) { bas += 1; }
    var gorunen = veri.kutular.slice(Math.max(0, bas - 1));
    var eksenAlt = Number(gorunen[0].alt), eksenUst = Number(gorunen[gorunen.length - 1].ust);
    var kutular = gorunen.map(function (k) {
      /* Kutunun rengi kutunun puan aralığından (on puanlık skor ölçeği; not ölçeğinden bağımsız). */
      var renk = puanRengi(k.alt);
      var metin = sayi(k.alt, 0) + "–" + sayi(k.ust, 0) + " puan: " + sayi(k.adet, 0) + " avukat" +
        (birlesik && k.not ? " · not " + k.not : "");
      return { parcalar: [{ adet: k.adet, renk: renk }], ad: metin, ipucu: kac(metin) };
    });
    var secenekler = sira.map(function (ad) {
      return "<button class='" + (ad === secili ? "etkin" : "") + "' data-dagilim='" + kac(ad) + "'" +
        " aria-pressed='" + (ad === secili) + "' title='" + kac(SUTUN[ad] || ad) + "'>" +
        kac(SUTUN_KISA[ad] || ad) + "</button>";
    }).join("");
    var lejant = skorLejanti();
    var taban = bos(veri.taban) ? null : Number(veri.taban);
    kok.innerHTML = kartUstOzet("Puan Dağılımı", sayi(veri.toplam, 0) + " avukat · ortanca " + puanMetni(veri.ortanca) +
      (taban === null ? "" : " · " + sayi(taban, 0) + " beklenen düzeydir (ortalama avukat)")) +
      "<div class='dg-secim'><div class='segment' role='group' aria-label='Gösterilen puan'>" + secenekler +
      "</div></div>" +
      histogram(kutular, kutuEtiketleri(gorunen), taban === null || taban < eksenAlt ? [] :
        [{ sol: (taban - eksenAlt) / (eksenUst - eksenAlt) * 100, ad: "Beklenen düzey" }]) + lejant;
    tiklamaBagla(kok, "[data-dagilim]", function (el) {
      durum.dagilimSutun = el.getAttribute("data-dagilim");
      CIZICILER["genel.dagilim"](kok, s);
      var yeni = kok.querySelector("[data-dagilim='" + durum.dagilimSutun + "']");
      if (yeni) { yeni.focus(); }  /* yeniden çizimden sonra odak seçilen düğmede kalır */
    });
  };

  CIZICILER["genel.tahsilat_dosya"] = function (kok, s) {
    var puanli = [], puansiz = 0, taban = null;
    s.forEach(function (r) {
      var puan = al(r, "puan");
      taban = bos(al(r, "taban")) ? taban : Number(al(r, "taban"));
      if (bos(puan) || al(r, "durum") !== "GECERLI") { puansiz += 1; return; }
      puanli.push({ kod: al(r, "avukat_kodu"), n: Number(al(r, "olgun_dosya")) || 0, puan: Number(puan) });
    });
    var baslik = kartUst("Tahsilat Puanı ve Portföy", "Her nokta bir avukat. Az dosyalı avukatın puanı " +
      "şansa daha açıktır; güven ayarı bunu yalnız kısmen yumuşatır. Sıralamayı dosya sayısıyla birlikte okuyun");
    if (!puanli.length) { kok.innerHTML = baslik + bosDurum("Henüz geçerli tahsilat puanı yok."); return; }
    var o = sayimEkseni(Math.max.apply(null, puanli.map(function (p) { return p.n; }).concat([1])));
    var y = eksenAdimi(PUAN_UST), izgara = olcekCizgileri(y.tavan, y.adim) + (taban === null ? "" :
      "<div class='cg-izgara referans' style='bottom:" + (taban / y.tavan * 100) + "%'><b>Beklenen düzey " +
      sayi(taban, 0) + "</b></div>");
    var noktalar = puanli.map(function (p) {
      var ad = p.kod + ": " + sayim(p.n, 0) + " olgun dosya, puan " + puanMetni(p.puan);
      return "<i class='dg-nokta' data-kod='" + kac(p.kod) + "' aria-label=\"" + kac(ad) +
        "\" style='left:" + (p.n / o.tavan * 100) + "%;bottom:" + Math.max(0, Math.min(y.tavan, p.puan)) / y.tavan * 100 +
        "%;background:" + puanRengi(p.puan) + "' data-ipucu=\"" + kac("<b>" + kac(p.kod) + "</b><table><tr><td>Olgun dosya</td><td>" + sayim(p.n, 1) +
        "</td></tr><tr><td>Tahsilat puanı</td><td>" + puanMetni(p.puan) + "</td></tr></table>") + "\"></i>";
    }).join("");
    var eksen = [];
    for (var d = 0; d <= o.tavan + 1e-9; d += o.adim) { eksen.push([d / o.tavan * 100, sayi(d, 0)]); }
    kok.innerHTML = baslik + "<div class='dagilim'><div class='dg-alan sacilim' style='height:220px'>" + izgara +
      noktalar + "</div><div class='dg-eksen sacilim'>" + eksen.map(function (e) {
        return "<span style='left:" + e[0] + "%'>" + kac(e[1]) + "</span>";
      }).join("") + "</div><div class='dg-eksen-adi'>Olgun dosya sayısı</div></div>" +
      (puansiz ? bilgiNotu(sayi(puansiz, 0) + " avukatın puanı yok (veri yetersiz); grafikte gösterilmez. " +
        "Olgun dosyası olmayan avukatlar da grafikte yer almaz.") : "");
    tiklamaBagla(kok, "[data-kod]", function (el) { sayfaAc("avukat", { kod: el.getAttribute("data-kod") }); });
  };

  /* Yatay eksen: alt sınırdan (eksi oran varsa sıfırın altından) üst sınıra, yüzde etiketli. */
  function oranEkseni(alt, ust, adim) {
    var etiket = [];
    for (var d = alt; d <= ust + 1e-9; d += adim) {
      etiket.push("<span style='left:" + ((d - alt) / (ust - alt) * 100) + "%'>" + yuzde(d, 0) + "</span>");
    }
    return etiket.join("");
  }
  CIZICILER["genel.brans_oran"] = function (kok, s) {
    var kutular = [], aykiri = {};
    s.forEach(function (r) {
      var b = al(r, "brans");
      if (al(r, "tur") === "AYKIRI") {
        (aykiri[b] = aykiri[b] || []).push({ kod: al(r, "avukat_kodu"), oran: Number(al(r, "oran")) });
        return;
      }
      kutular.push({ brans: b, adet: Number(al(r, "adet")) || 0, q1: Number(al(r, "ceyrek_alt")),
        ortanca: Number(al(r, "ortanca")), q3: Number(al(r, "ceyrek_ust")), alt: Number(al(r, "biyik_alt")),
        ust: Number(al(r, "biyik_ust")), disarida: Number(al(r, "disarida")) || 0 });
    });
    var baslik = kartUst("Branş Bazında Gerçekleşen / Beklenen" + bilgi("Her avukatın o branştaki " +
      "tahsilatının, aynı dosya grubundaki (Puanlama Kuralları'ndaki gruplama) oranlara göre beklenene " +
      "oranı. Yalnız o branşta yeterli veri eşiğine (Puanlama Kuralları) ulaşan avukatlar sayılır; puana " +
      "girmez. Kutu ortadaki yarı avukatı, çizgi ortancayı, bıyıklar " +
      "olağan aralığı gösterir; noktalar aykırı avukatlardır"));
    var sayilan = kutular.filter(function (k) { return k.adet > 0; });
    if (!sayilan.length) {
      kok.innerHTML = baslik + bosDurum("Henüz bir branşta yeterli veri eşiğine ulaşan avukat yok.");
      return;
    }
    /* Eksen sıfırdan başlar; eksi oran (ters kayıt) varsa sıfırın altına uzar. Üstte bıyıkların
       ötesindeki aykırılar kenarda sayıyla gösterilir. */
    var enAz = 0, enCok = BEKLENEN_ORAN;
    sayilan.forEach(function (k) { enAz = Math.min(enAz, k.alt); enCok = Math.max(enCok, k.ust); });
    Object.keys(aykiri).forEach(function (b) {
      aykiri[b].forEach(function (p) { enAz = Math.min(enAz, p.oran); });
    });
    var adim = eksenAdimi((enCok - enAz) * 1.1).adim;
    var eksenAlt = enAz < 0 ? Math.floor(enAz / adim) * adim : 0;
    var eksenUst = eksenAlt + Math.ceil((enCok * 1.1 - eksenAlt) / adim) * adim;
    var x = { tavan: eksenUst };
    function konum(v) { return (Math.max(eksenAlt, Math.min(v, eksenUst)) - eksenAlt) / (eksenUst - eksenAlt) * 100; }
    var disarida = 0;
    var satirlar = kutular.map(function (k, i) {
      disarida += k.disarida;
      var renk = bransRengi(k.brans), ad = BRANS[k.brans] || k.brans;
      var noktalar = aykiri[k.brans] || [], kesik = noktalar.filter(function (p) { return p.oran > x.tavan; });
      var ozet = ad + ": " + sayi(k.adet, 0) + " avukat" + (k.adet ? ", ortanca " + yuzde(k.ortanca, 0) +
        ", çeyrekler " + yuzde(k.q1, 0) + "–" + yuzde(k.q3, 0) + ", aykırı " + sayi(noktalar.length, 0) : "");
      var ipucu = "<b>" + kac(ad) + "</b><table><tr><td>Sayılan avukat</td><td>" + sayi(k.adet, 0) +
        "</td></tr>" + (k.adet ? "<tr><td>Ortanca</td><td>" + yuzde(k.ortanca, 1) + "</td></tr><tr><td>Çeyrekler" +
        "</td><td>" + yuzde(k.q1, 1) + " – " + yuzde(k.q3, 1) + "</td></tr><tr><td>Bıyıklar</td><td>" +
        yuzde(k.alt, 1) + " – " + yuzde(k.ust, 1) + "</td></tr><tr><td>Aykırı</td><td>" +
        sayi(noktalar.length, 0) + "</td></tr>" : "") + "<tr><td>Kutuya girmeyen</td><td>" +
        sayi(k.disarida, 0) + "</td></tr></table>";
      var cizim = !k.adet ? "<span class='kutu-yok'>Yeterli veri eşiğine ulaşan avukat yok</span>" :
        "<i class='kutu-biyik' style='left:" + konum(k.alt) + "%;width:" + (konum(k.ust) - konum(k.alt)) + "%'></i>" +
        "<i class='kutu-govde' style='left:" + konum(k.q1) + "%;width:" + (konum(k.q3) - konum(k.q1)) +
        "%;border-color:" + renk + "'><b style='background:" + renk + "'></b></i>" +
        "<i class='kutu-ortanca' style='left:" + konum(k.ortanca) + "%'></i>" +
        noktalar.filter(function (p) { return p.oran <= x.tavan; }).map(function (p) {
          return "<i class='kutu-aykiri' style='left:" + konum(p.oran) + "%;border-color:" + renk + "' data-ipucu=\"" +
            kac("<b>" + kac(p.kod) + "</b> · gerçekleşen / beklenen " + yuzde(p.oran, 1)) + "\"></i>";
        }).join("") + (kesik.length ? "<span class='kutu-kesik'>+" + sayi(kesik.length, 0) + " ›</span>" : "");
      return "<div class='kutu-satir' data-gezinme tabindex='" + (i ? -1 : 0) + "' role='img' aria-label=\"" +
        kac(ozet) + "\" data-ipucu=\"" + kac(ipucu) + "\"><div class='kutu-ad'><i class='kutu' style='background:" +
        renk + "'></i>" + kac(ad) + "<small>" + sayi(k.adet, 0) + " avukat</small></div><div class='kutu-alan'>" +
        "<i class='kutu-referans' style='left:" + konum(BEKLENEN_ORAN) + "%'></i>" + cizim + "</div></div>";
    }).join("");
    kok.innerHTML = baslik + "<div class='kutu-grafik'><div class='kutu-ust'><span style='left:" +
      konum(BEKLENEN_ORAN) + "%'>Beklenen düzey</span></div>" + satirlar + "<div class='dg-eksen kutu-eksen'>" +
      oranEkseni(eksenAlt, eksenUst, adim) + "</div><div class='dg-eksen-adi kutu-eksen-adi'>Gerçekleşen / beklenen" +
      "</div></div>" + (disarida ? bilgiNotu(sayi(disarida, 0) + " avukat-branş eşleşmesi yeterli veri " +
      "eşiğinin altında kaldığı ya da beklenen tahsilatı olmadığı için kutulara girmedi.") : "");
  };

  CIZICILER["genel.avukat_tablosu"] = function (kok, s) {
    var notlar = [], siraVar = false;
    var satirlar = s.map(function (r) {
      var durumKod = al(r, "durum"), eksik = al(r, "eksik_sutunlar"), not = al(r, "performans_notu");
      var oran = al(r, "gerceklesen_beklenen"), anahtar = bos(not) ? "YOK" : not;
      if (notlar.indexOf(anahtar) < 0) { notlar.push(anahtar); }
      var sira = al(r, "genel_sira");
      if (!bos(sira)) { siraVar = true; }
      return "<tr class='tiklanir' data-kod='" + kac(al(r, "avukat_kodu")) + "' data-not='" + kac(anahtar) + "'>" +
        hucre(bos(sira) ? "<span class='ikincil'>—</span>" : sayi(sira, 0), false, sira) +
        hucre("<b>" + kac(al(r, "avukat_kodu")) + "</b>" + unvanMetni(al(r, "unvan"))) +
        hucre(sayi(al(r, "aktif_dosya"), 0), true, al(r, "aktif_dosya")) +
        /* Yazı aşağı kesilir: beklenenin hemen altındaki oran kırmızı yazıyla yüzde yüz görünmez. */
        hucre("<span class='" + (!bos(oran) && oran < BEKLENEN_ORAN ? "kotu-metin" : "") + "'>" +
          yuzde(oran, 0, true) + "</span>", true, oran) +
        hucre(puanMetni(al(r, "tahsilat")) + azVeriSatiri(al(r, "tahsilat_yeterli"), al(r, "tahsilat")),
          true, al(r, "tahsilat")) +
        hucre(puanMetni(al(r, "sure")) + azVeriSatiri(al(r, "sure_yeterli"), al(r, "sure")), true, al(r, "sure")) +
        hucre(puanMetni(al(r, "kalite")), true, al(r, "kalite")) +
        hucre(puanMetni(al(r, "davranis")), true, al(r, "davranis")) +
        hucre(skorHucre(al(r, "birlesik_puan")), true, al(r, "birlesik_puan")) +
        hucre(notRozeti(not), false, bos(al(r, "birlesik_puan")) ? null : -al(r, "birlesik_puan")) +
        hucre(durumRozeti(durumKod) + (eksik ? "<div class='ikincil'>Eksik: " + eksikSutunlar(eksik) +
          "</div>" : "")) + "</tr>";
    });
    /* Not düğmeleri veriden: notlar en yüksek puanlarına göre sıralanır (ölçek parametrededir). */
    var enYuksek = {};
    s.forEach(function (r) {
      var n = al(r, "performans_notu"), p = Number(al(r, "birlesik_puan"));
      if (!bos(n) && !(enYuksek[n] >= p)) { enYuksek[n] = p; }
    });
    var sira = Object.keys(enYuksek).sort(function (a, b) { return enYuksek[b] - enYuksek[a]; }).concat(["YOK"]);
    if (durum.notFiltresi && notlar.indexOf(durum.notFiltresi) < 0) { durum.notFiltresi = ""; }
    var segment = "<div class='segment' role='group' aria-label='Not süzgeci'><button data-not-filtre='' class='" + (durum.notFiltresi ? "" : "etkin") +
      "' aria-pressed='" + !durum.notFiltresi + "'>Tümü</button>" + sira.filter(function (n) {
        return notlar.indexOf(n) >= 0; }).map(function (n) {
        return "<button data-not-filtre='" + kac(n) + "' class='" + (durum.notFiltresi === n ? "etkin" : "") +
          "' aria-pressed='" + (durum.notFiltresi === n) + "'>" +
          (n === "YOK" ? "Hesaplanmadı" : kac(n)) + "</button>";
      }).join("") + "</div>";
    kok.innerHTML = kartUstOzet("Avukat Performans Sıralaması", sayi(s.length, 0) + " avukat · " + (siraVar ?
      "birleşik puana göre sıralı" : "birleşik puan henüz hesaplanmıyor") + " · sütun başlığına tıklayınca " +
      "sıralanır, satıra tıklayınca avukat kartı açılır", segment) + "<div class='kart-govde dolu'>" +
      tablo(["Sıra", "Avukat", "#Aktif dosya", "#Gerç./Bekl." + bilgi("Olgun dosyalarda gerçekleşen tahsilatın " +
        "beklenen tahsilata oranı"), "#Tahsilat", "#Süre", "#Kalite", "#Davranış", "#Birleşik puan", "Not",
        "Durum"], satirlar, "siralanabilir") + "</div><div class='kart-alt'><span>Puan " +
      "tek başına yaptırım gerekçesi değildir; dönem yayınları değişmez, düzeltme yeni sürüm olarak eklenir." +
      "</span></div>";
    function uygula() {
      Array.prototype.forEach.call(kok.querySelectorAll("tr[data-not]"), function (el) {
        el.style.display = !durum.notFiltresi || el.getAttribute("data-not") === durum.notFiltresi ? "" : "none";
      });
      Array.prototype.forEach.call(kok.querySelectorAll("[data-not-filtre]"), function (el) {
        var secili = el.getAttribute("data-not-filtre") === durum.notFiltresi;
        el.classList.toggle("etkin", secili);
        el.setAttribute("aria-pressed", secili ? "true" : "false");
      });
      durakYenile(kok);
    }
    tiklamaBagla(kok, "[data-not-filtre]", function (el) { durum.notFiltresi = el.getAttribute("data-not-filtre"); uygula(); });
    tiklamaBagla(kok, "tr[data-kod]", function (el) { sayfaAc("avukat", { kod: el.getAttribute("data-kod") }); });
    uygula();
  };

  CIZICILER["genel.yillik"] = function (kok, s) {
    var yillar = [], avukatlar = {}, sira = [], bitis = "";
    s.forEach(function (r) {
      var kod = al(r, "avukat_kodu"), yil = al(r, "yil");
      if (yillar.indexOf(yil) < 0) { yillar.push(yil); }
      if (!avukatlar[kod]) { avukatlar[kod] = { tutar: {} }; sira.push(kod); }
      avukatlar[kod].tutar[yil] = al(r, "tutar");
      if (al(r, "yil_ici") === true) {
        avukatlar[kod].onceki = al(r, "onceki_ayni_donem");
        avukatlar[kod].degisim = al(r, "degisim");
        bitis = al(r, "son_tarih");
      }
    });
    yillar.sort();
    var satirlar = sira.map(function (kod) {
      var x = avukatlar[kod], d = x.degisim;
      return "<tr>" + hucre(kod === "ATANAMAYAN" ? "<span class='ikincil'>Avukata yazılmayan</span>" :
        "<b>" + kac(kod) + "</b>") + yillar.map(function (yil) {
          return hucre(tl(x.tutar[yil]), true, x.tutar[yil]);
        }).join("") + hucre(tl(x.onceki), true, x.onceki) +
        hucre(bos(d) ? "—" : "<span class='" + (eksiMi(d, 1) ? "kotu-metin" : "") + "'>" + yuzde(d, 1) + "</span>",
          true, d) + "</tr>";
    });
    var son = yillar.length ? yillar[yillar.length - 1] : "";
    kok.innerHTML = kartUst("Yıllık Tahsilat", "Hareket tarihindeki avukata yazılan tahsilat · " + kac(son) +
      " yılı " + tarih(bitis) + " tarihine kadar · değişim önceki yılın aynı dönemine göre") +
      "<div class='kart-govde dolu'>" + tablo(["Avukat"].concat(yillar.map(function (yil) {
        return "#" + kac(yil) + (yil === son ? " (yıl içi)" : "");
      })).concat(["#Önceki yıl aynı dönem", "#Değişim"]), satirlar, "siralanabilir") + "</div>";
  };


  CIZICILER["genel.oncelikli"] = function (kok, s) {
    var ogeler = s.map(function (r) {
      var seviye = al(r, "seviye"), sinif = golgeSeviye(seviye, al(r, "kriter")) ? "golge" : kac(seviye);
      return "<div class='liste-oge " + sinif + "' data-avukat='" + kac(al(r, "avukat_kodu")) +
        "' data-kriter='" + kac(al(r, "kriter")) + "'><div><div class='baslik'>" + kac(al(r, "dosya_no")) +
        "</div><div class='ikincil'>" + kac(KRITER[al(r, "kriter")]) + " · " + kac(al(r, "avukat_kodu")) +
        "</div></div><div class='sag " + sinif + "'>" + kac(SEVIYE[seviye] || seviye) + "<div class='ikincil'>" +
        sayi(al(r, "sure_gun"), 0) + " gün</div></div></div>";
    }).join("");
    kok.innerHTML = kartUstOzet("Öncelikli Dosyalar" + bilgi("Aktif gecikmeler, en ağır bayrak önce; " +
      "tıklayınca Süre Takibi'nde avukatın o kriterdeki dönemleri açılır"), durum.golge.K1 || durum.golge.K2 ?
      "Gölge mod (" + kac(golgeKriterleri()) + "): bilgi amaçlı" : null) + (ogeler ? "<div class='liste'>" + ogeler + "</div>" : bosDurum("Aktif gecikme yok."));
    tiklamaBagla(kok, "[data-avukat]", function (el) {
      durum.filtre = { kriter: el.getAttribute("data-kriter"), seviye: "", avukat: el.getAttribute("data-avukat") };
      durum.bolum.sure = "donemler";
      sayfaAc("sure");
    });
  };

  CIZICILER["genel.brans"] = function (kok, s) {
    var toplam = 0;
    var kalemler = s.map(function (r) {
      var adet = al(r, "aktif_dosya"), kod = al(r, "brans");
      toplam += Number(adet) || 0;
      return { kod: kod, ad: "<b>" + brans(kod) + "</b>", deger: adet, ek: kisaTl(al(r, "aktif_rucu_tutari")),
        renk: bransRengi(kod) };
    }).sort(function (a, b) {  /* sabit branş sırası: renk komşulukları her zaman aynı */
      var x = bransSirasi(a.kod), y = bransSirasi(b.kod);
      return x === y ? String(a.kod).localeCompare(String(b.kod), "tr") : x < y ? -1 : 1;
    });
    kok.innerHTML = kartUst("Portföy · Branşa Göre", "Aktif dosyaların branşa göre dağılımı ve rücu tutarı") +
      "<div class='kart-govde'>" + (kalemler.length ? pasta(kalemler, sayi(toplam, 0), "aktif dosya",
        ["Branş", "Dosya", "Pay", "Rücu tutarı"]) : bosDurum("Kayıt yok.")) + "</div>";
  };

  CIZICILER["genel.bant"] = function (kok, s) {
    var toplam = 0, en = 0;
    var kalemler = s.map(function (r) {
      var adet = Number(al(r, "aktif_dosya")) || 0;
      toplam += adet; en = Math.max(en, adet);
      return { ad: "Bant " + kac(al(r, "tutar_bandi") + 1) + " · " + kac(al(r, "bant_etiketi")), deger: adet };
    });
    kok.innerHTML = kartUst("Portföy · Tutar Bandına Göre", "Aktif dosya sayısı; bant sınırları parametre " +
      "dosyasından") + "<div class='kart-govde'>" + (kalemler.length ? kalemler.map(function (k) {
        return satirCubuk(k.ad, "<b>" + sayi(k.deger, 0) + "</b><span class='ikincil'>" +
          yuzde(k.deger / (toplam || 1), 1) + "</span>", k.deger / (en || 1), "var(--seri)");
      }).join("") : bosDurum("Kayıt yok.")) + "</div>";
  };

  /* Gruplamada olmayan boyutun (yaş ya da tutar bandı) sütunu gösterilmez. Satırlar kesitteki
     olgun dosya gruplarıdır; sıklık hızı dosyaların o banttaki süresinden gelir. */
  CIZICILER["genel.gruplar"] = function (kok, s) {
    var yasVar = s.some(function (r) { return !bos(al(r, "yas_bandi")); });
    var tutarVar = s.some(function (r) { return !bos(al(r, "tutar_bandi")); });
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre("<b class='tek-satir'>" + brans(al(r, "brans")) + "</b>") +
        (yasVar ? hucre("<span class='tek-satir'>" + kac(al(r, "yas_etiketi") || "—") + "</span>", false,
          al(r, "yas_bandi")) : "") +
        (tutarVar ? hucre("<span class='tek-satir'>" + kac(al(r, "bant_etiketi") || "—") + "</span>", false,
          al(r, "tutar_bandi")) : "") +
        hucre(sayi(al(r, "dosya_sayisi"), 1), true, al(r, "dosya_sayisi")) +
        hucre(tl(al(r, "rucu_toplami")), true, al(r, "rucu_toplami")) +
        hucre(tl(al(r, "atfedilen")), true, al(r, "atfedilen")) +
        hucre(tl(al(r, "atanamayan")), true, al(r, "atanamayan")) +
        hucre("<b>" + yuzde(al(r, "oran"), 1) + "</b>", true, al(r, "oran")) +
        hucre(sayi(al(r, "siklik_hizi"), 2), true, al(r, "siklik_hizi")) + "</tr>";
    });
    var basliklar = ["Branş"].concat(yasVar ? ["Dosya yaşı" + bilgi("Dosyanın rücuya verilişinden kesite " +
      "kadar geçen süre; bant sınırları Puanlama Kuralları sayfasında")] : [], tutarVar ? ["Tutar bandı" +
      bilgi("Dosyanın rücu tutarına göre grubu; sınırlar Puanlama Kuralları sayfasında")] : [],
      ["#Olgun dosya" + bilgi("Olgun dosyaların avukatlara yazılan payı. Yeniden atanan dosya avukatlar " +
        "arasında elde tutulan gün oranında bölünür; iade sonrası ya da iki atama arasındaki süre kimseye " +
        "yazılmaz. Bu yüzden sayı kesirli olabilir"), "#Rücu toplamı", "#Avukata yazılan",
        "#Avukata yazılmayan" + bilgi("Hiçbir avukata yazılmayan tahsilat: atamadan önce, sulh amaçlı ya " +
          "da iptal edilen atama döneminde veya iki atama arasında gelen tahsilat. Puana girmez; eksi " +
          "değer bu dönemlerdeki ters kayıttır"), "#Tahsilat oranı",
        "#Tahsilat ayı / dosya-yıl" + bilgi("Sıklık hızı: dosyaların avukatlarda geçirdiği her yıl " +
          "başına tahsilat yapılan ay sayısı")]);
    kok.innerHTML = kartUst("Tahsilat Karşılaştırma Grupları " + bilgi("Avukatın beklenen tahsilatı, olgun " +
      "dosyalarının rücu tutarına bu gruptaki diğer avukatların tahsilat oranı uygulanarak bulunur. Sıklık " +
      "ve güncellikte beklenen tahsilat ayı sayısı, dosyanın avukatta geçirdiği süreye (dosya-yıl) " +
      "gruptaki diğer avukatların tahsilat ayı hızı uygulanarak bulunur. Tablodaki oranlar grubun " +
      "bütününündür; hız dosyaların o yaş bandında geçirdiği süreden hesaplanır. Olgun dosya ve " +
      "rücu toplamı yeniden atanan dosyada elde tutma payıyla sayılır. Gruplama Puanlama Kuralları " +
      "sayfasında")) + "<div class='kart-govde dolu'>" +
      tablo(basliklar, satirlar, "siralanabilir") + "</div>";
  };

  /* Avukat bazında aylık tahsilat (son aylar); avukata yazılmayan tutar en altta. */
  CIZICILER["genel.aylik_avukat"] = function (kok, s) {
    var aylar = [], avukatlar = {}, sira = [], kismi = {};
    s.forEach(function (r) {
      var kod = al(r, "avukat_kodu"), ay = al(r, "ay");
      if (aylar.indexOf(ay) < 0) { aylar.push(ay); }
      if (!avukatlar[kod]) { avukatlar[kod] = { tutar: {}, toplam: al(r, "toplam") }; sira.push(kod); }
      avukatlar[kod].tutar[ay] = al(r, "tutar");
      if (al(r, "kismi") === true) { kismi[ay] = true; }
    });
    aylar.sort();
    var satirlar = sira.map(function (kod) {
      var x = avukatlar[kod];
      return "<tr>" + hucre(kod === "ATANAMAYAN" ? "<span class='ikincil'>Avukata yazılmayan</span>" :
        "<b>" + kac(kod) + "</b>") + hucre("<b>" + kisaTl(x.toplam) + "</b>", true, x.toplam) +
        aylar.map(function (ay) { return hucre(kisaTl(x.tutar[ay]), true, x.tutar[ay]); }).join("") + "</tr>";
    });
    kok.innerHTML = kartUstOzet("Aylık Tahsilat (Avukat Bazında)" + bilgi("Hareket tarihindeki avukata " +
      "yazılan tahsilat"), aylar.length && kismi[aylar[aylar.length - 1]] ? "Son ay kesite kadar" : null) +
      "<div class='kart-govde dolu'>" + tablo(["Avukat", "#Toplam"].concat(aylar.map(function (ay, i) {
        var e = ayEtiketi(ay, i === 0);
        return "#" + kac(e.etiket) + (e.alt ? " " + kac(e.alt) : "");
      })), satirlar, "siralanabilir") + "</div>";
  };

  /* ---------- Avukat Kartı ---------- */
  /* Arama anahtarı: büyük harf, boşluk ve ayraçsız (AV-08, av08 ve 08 aynı avukatı bulur). */
  function aramaAnahtari(metin) { return String(metin).toLocaleUpperCase("tr-TR").replace(/[\s\-_.·]/g, ""); }
  CIZICILER["avukat.liste"] = function (kok, s) {
    var ogeler = s.map(function (r) {
      var kod = al(r, "avukat_kodu"), puan = al(r, "birlesik_puan"), d = al(r, "durum");
      return "<tr class='tiklanir" + (kod === durum.kod ? " secili" : "") + "' data-kod='" + kac(kod) +
        "' data-ara='" + kac(aramaAnahtari(kod + " " + (al(r, "unvan") || ""))) + "'>" +
        hucre("<b>" + kac(kod) + "</b>" + unvanMetni(al(r, "unvan"))) +
        hucre(bos(puan) ? "<span class='ikincil tek-satir'>" + kac(DURUM[d] || d) + "</span>" : "<b>" +
          puanMetni(puan) + "</b>", true, puan) + hucre(bos(al(r, "performans_notu")) ? "" :
          notRozeti(al(r, "performans_notu"))) + "</tr>";
    });
    kok.innerHTML = kartUst("Avukatlar", null, "<span class='ikincil' id='avukat-sayac'></span>") +
      "<div class='liste-arama'><input type='search' id='avukat-arama' class='arama' autocomplete='off' " +
      "spellcheck='false' placeholder='Avukat kodu ara' aria-label='Avukat kodu ile ara' aria-controls='avukat-tablo'>" +
      "</div><div class='kart-govde dolu' id='avukat-tablo'>" +
      tablo(["Avukat", "#Puan", "Not"], ogeler) + "<div class='bos-satir ikincil' id='avukat-yok' hidden>" +
      "Bu aramayla eşleşen avukat yok.</div></div>";
    var giris = document.getElementById("avukat-arama");
    giris.value = durum.avukatArama || "";  /* kac() boş değeri "—" yazar; kutu boş başlamalı */
    function gorunenler() {
      return Array.prototype.filter.call(kok.querySelectorAll("tr[data-kod]"), function (el) {
        return el.style.display !== "none";
      });
    }
    function uygula() {
      var aranan = aramaAnahtari(durum.avukatArama || "");
      Array.prototype.forEach.call(kok.querySelectorAll("tr[data-kod]"), function (el) {
        el.style.display = !aranan || el.getAttribute("data-ara").indexOf(aranan) >= 0 ? "" : "none";
      });
      var sayisi = gorunenler().length;
      document.getElementById("avukat-sayac").textContent = (aranan ? sayi(sayisi, 0) + " / " : "") +
        sayi(s.length, 0) + " avukat · birleşik puana göre";
      document.getElementById("avukat-yok").hidden = sayisi > 0;
      durakYenile(kok);
    }
    giris.oninput = function () { durum.avukatArama = giris.value; uygula(); };
    giris.onkeydown = function (e) {
      if (e.key === "Enter") {
        var ilk = gorunenler()[0];
        if (ilk) { sayfaAc("avukat", { kod: ilk.getAttribute("data-kod") }); }
      } else if (e.key === "Escape" && giris.value) {
        e.stopPropagation();
        giris.value = "";
        durum.avukatArama = "";
        uygula();
      }
    };
    tiklamaBagla(kok, "tr[data-kod]", function (el) { sayfaAc("avukat", { kod: el.getAttribute("data-kod") }); });
    uygula();
  };

  CIZICILER["avukat.baslik"] = function (kok, s) {
    var d = s[0];
    if (!d) { kok.innerHTML = bosDurum("Avukat bulunamadı."); return; }
    var kod = al(d, "avukat_kodu"), eksik = al(d, "eksik_sutunlar"), sira = al(d, "genel_sira");
    var panel = document.getElementById("neden-paneli");
    durum.kod = kod;
    /* Adresteki kod bulunamadıysa sunucu ilk avukatı döndürür; adres gösterilen avukata düzeltilir. */
    if (durum.sayfa === "avukat" && location.hash !== adresKur("avukat")) {
      uygulananAdres = adresKur("avukat");
      history.replaceState(null, "", uygulananAdres);
    }
    Array.prototype.forEach.call(document.querySelectorAll(".avukat-liste tr[data-kod]"), function (el) {
      el.classList.toggle("secili", el.getAttribute("data-kod") === kod);
    });
    kok.innerHTML = "<div class='profil-ust'><div class='avukat-kimlik'><div class='avatar'>" +
      kac(String(kod).slice(-2)) + "</div><div><div class='avukat-ad'>" + kac(kod) + " " +
      (bos(al(d, "performans_notu")) ? "" : notRozeti(al(d, "performans_notu"))) + "</div><div class='ikincil'>" +
      kac(al(d, "unvan")) + " · " + kac(CALISMA[al(d, "calisma_durumu")] || al(d, "calisma_durumu")) +
      "</div></div></div><button class='dugme' id='neden-dugmesi' aria-controls='neden-paneli' " +
      "aria-expanded='" + !panel.hidden + "'>" +
      (panel.hidden ? "Neden bu puanı aldı?" : "Açıklamayı gizle") + "</button></div><div class='istatistikler'>" +
      istatistik("Birleşik puan" + bilgi("Puana giren sütunların ağırlıklı toplamı"), puanMetni(al(d, "birlesik_puan")),
        "Yüz üzerinden") +
      istatistik("Genel sıra", bos(sira) ? "—" : sayi(sira, 0) + ".", "Puanı hesaplanan " +
        sayi(al(d, "yayimlanan"), 0) + " avukat içinde") +
      istatistik("Durum", durumRozeti(al(d, "durum")), eksik ? "Eksik: " + eksikSutunlar(eksik) :
        "Puana giren sütunların hepsi geçerli") + "</div>";
    var dugme = document.getElementById("neden-dugmesi");
    dugme.onclick = function () {
      panel.hidden = !panel.hidden;
      dugme.textContent = panel.hidden ? "Neden bu puanı aldı?" : "Açıklamayı gizle";
      dugme.setAttribute("aria-expanded", panel.hidden ? "false" : "true");
    };
  };

  /* Neden bu puanı aldı?: birleşik puanın özeti, sütun başına puan, beklenen düzeye göre etki ve
     tek cümlelik neden; hesap adımları (VERİ, HESAP) düğmenin arkasında. Cümleler, etkiler ve
     eşitlik kütüphaneden gelir (aciklama_ozet); arayüz yalnız çizer. Çubuk boyu satırlar arası
     karşılaştırma içindir: en büyük etki ETKI_YARI piksel. */
  var ACIKLAMA_SUTUNLARI = ["tahsilat", "sure", "kalite", "davranis"];
  /* Ağırlığı sıfır olan sütun bu fazda birleşik puana girmez (params birlesik_sutunlar). */
  function puanaGirmez(agirlik) { return !bos(agirlik) && Number(agirlik) === 0; }
  function agirlikMetni(agirlik) { return puanaGirmez(agirlik) ? "Bu fazda puana girmez" : "Ağırlık " + yuzde(agirlik, 0); }
  var ETKI_YARI = 54;
  var ADIM_TURU = { KANIT: "VERİ", HESAP: "HESAP" };
  function etkiMetni(v) { return (v > 0 ? "+" : v < 0 ? "−" : "±") + sayi(Math.abs(v), 2); }
  function etkiCubugu(etki, olcek) {
    if (bos(etki)) { return "<div class='etki'><span class='ikincil'>—</span></div>"; }
    var v = Number(etki), yon = v < 0 ? "eksi" : "arti";
    var genislik = Math.max(2, Math.round(Math.abs(v) / olcek * ETKI_YARI));
    return "<div class='etki'><span class='etki-ray'><span class='etki-cubuk " + yon + "' style='width:" +
      genislik + "px'></span></span><b class='" + yon + "'>" + etkiMetni(v) + "</b></div>";
  }
  function puanCipi(puan) {
    if (bos(puan)) { return "<span class='ikincil'>—</span>"; }
    return "<span class='puan-cip' style='--renk:" + puanRengi(puan) + "'>" + puanMetni(puan) + "</span>";
  }
  CIZICILER["avukat.aciklama"] = function (kok, s) {
    var gruplar = {};
    s.forEach(function (r) {
      var ad = al(r, "sutun");
      (gruplar[ad] = gruplar[ad] || []).push({ sira: al(r, "sira"), tur: al(r, "tur"), metin: al(r, "metin"),
        etki: al(r, "etki"), puan: al(r, "puan"), agirlik: al(r, "agirlik"), not: al(r, "performans_notu") });
    });
    function satirlari(ad, turler) {
      return (gruplar[ad] || []).filter(function (x) { return turler.indexOf(x.tur) >= 0; })
        .sort(function (a, b) { return a.sira - b.sira; });
    }
    var ozetler = ACIKLAMA_SUTUNLARI.map(function (ad) { return satirlari(ad, ["OZET"])[0]; });
    var olcek = Math.max.apply(null, [1].concat(ozetler.map(function (o) {
      return o && !bos(o.etki) ? Math.abs(Number(o.etki)) : 0;
    })));
    var birlesik = (gruplar.birlesik || [])[0] || {};
    var bOzet = satirlari("birlesik", ["OZET", "ISTISNA"])[0], esitlik = satirlari("birlesik", ["ESITLIK"])[0];
    var ozetBandi = "<div class='neden-ozet'>" + (bos(birlesik.puan) ? "" : "<div class='neden-puan'>" +
      puanMetni(birlesik.puan) + " " + notRozeti(birlesik.not) + "</div>") + "<div class='neden-cumle'>" +
      (bOzet ? kac(bOzet.metin) : "Birleşik puan hesaplanmadı.") + "</div></div>";
    var satirlar = ACIKLAMA_SUTUNLARI.map(function (ad, i) {
      var ilk = (gruplar[ad] || [])[0] || {}, gorunen = satirlari(ad, ["OZET", "UYARI", "ISTISNA"]);
      var girmez = puanaGirmez(ilk.agirlik);
      return "<div class='neden-sira" + (girmez ? " girmez" : "") + "'><div class='neden-ad'><b>" + kac(SUTUN[ad]) +
        "</b><span>" + agirlikMetni(ilk.agirlik) + "</span></div><div class='neden-skor'>" + puanCipi(ilk.puan) +
        "</div>" + etkiCubugu(ozetler[i] ? ozetler[i].etki : null, olcek) + "<div class='neden-metin'>" +
        (girmez ? "<div class='ikincil'>Bu fazda birleşik puana girmez; bilgi olarak gösterilir.</div>" : "") +
        (gorunen.length ? gorunen.map(function (x) {
          return "<div class='" + kac(x.tur) + "'>" + kac(x.metin) + "</div>";
        }).join("") : girmez ? "" : "<span class='ikincil'>Bu sütunda avukatın sonucu yok; durumu Sütun " +
          "Puanları kartında.</span>") + "</div></div>";
    }).join("");
    var adimlar = ACIKLAMA_SUTUNLARI.concat(["birlesik"]).map(function (ad) {
      var x = satirlari(ad, ["KANIT", "HESAP"]);
      return x.length ? "<section><h3>" + kac(SUTUN[ad]) + "</h3>" + x.map(function (y) {
        return "<div class='neden-satir " + kac(y.tur) + "'><span class='tur'>" + ADIM_TURU[y.tur] + "</span>" +
          kac(y.metin) + "</div>";
      }).join("") + "</section>" : "";
    }).join("");
    kok.innerHTML = kartUst("Neden bu puanı aldı?", "Her sütunda beklenen düzey aynıdır. Çubuk, sütunun " +
      "birleşik puanı beklenen düzeye göre ne kadar yukarı ya da aşağı çektiğini gösterir; sayılar sonuç " +
      "tablolarından gelir") + ozetBandi + "<div class='neden-tablo'><div class='neden-sira neden-baslik' " +
      "aria-hidden='true'><div>Sütun</div><div>Puan</div><div>Etkisi</div><div>Neden</div></div>" + satirlar +
      "</div><div class='neden-alt'><div class='ikincil'>" + (esitlik ? kac(esitlik.metin) : "") + "</div>" +
      "<button class='dugme' id='adim-dugmesi' aria-expanded='false' aria-controls='neden-adimlar'>" +
      "Hesap adımlarını göster</button></div><div id='neden-adimlar' class='neden-adimlar' hidden>" + adimlar +
      "</div>";
    var dugme = document.getElementById("adim-dugmesi"), alan = document.getElementById("neden-adimlar");
    dugme.onclick = function () {
      alan.hidden = !alan.hidden;
      dugme.textContent = alan.hidden ? "Hesap adımlarını göster" : "Hesap adımlarını gizle";
      dugme.setAttribute("aria-expanded", alan.hidden ? "false" : "true");
    };
  };

  CIZICILER["avukat.sutunlar"] = function (kok, s) {
    var kadranlar = s.map(function (r) {
      var puan = al(r, "puan"), d = al(r, "durum");
      return "<div class='kadran'>" + kadran(puan, DURUM[d] || d, puanRengi(puan)) +
        "<div class='kadran-ad'>" +
        kac(SUTUN[al(r, "sutun")] || al(r, "sutun")) + "</div><div class='kadran-alt'>" +
        agirlikMetni(al(r, "agirlik")) + "</div>" + (d === "GECERLI" ? "" : durumRozeti(d)) +
        azVeriSatiri(al(r, "yeterli"), puan) + "</div>";
    }).join("");
    kok.innerHTML = kartUst("Sütun Puanları", "Her sütun sıfır ile yüz arasında puanlanır; birleşik puan yalnız puana " +
      "giren sütunların hepsi geçerliyse hesaplanır") + "<div class='kadranlar'>" + kadranlar + "</div>";
  };

  /* Tahsilat puanının bileşenleri (tutar, sıklık, güncellik): ad, açıklama, gerçekleşen ve beklenen metni. */
  function bilesenSatiri(ad, aciklama, puan, ayrinti) {
    return "<tr>" + hucre("<b>" + ad + "</b>" + bilgi(aciklama) + "<div class='ikincil'>" + ayrinti + "</div>") +
      hucre(skorHucre(puan), true, puan) + "</tr>";
  }
  function sayimMetni(o, e) { return sayi(o, 0) + " / " + sayi(e, 1); }
  CIZICILER["avukat.tahsilat"] = function (kok, s) {
    var d = s[0];
    if (!d) { kok.innerHTML = kartUst("Tahsilat Performansı") + bosDurum("Olgun dosyası yok.", true); return; }
    var neden = al(d, "eksik_nedeni");
    var satirlar = [
      bilesenSatiri("Tutar", "Olgun dosyalarda tahsil edilen tutarın, aynı dosya grubundaki tahsilat " +
        "oranlarına göre beklenen tutara oranı. Düzeltilmiş oran: " + sayi(al(d, "r"), 3),
        al(d, "puan_tutar"), tl(al(d, "gerceklesen")) + " / " + tl(al(d, "beklenen")) + " · " + yuzde(al(d, "oran"), 1)),
      bilesenSatiri("Sıklık", "Olgun dosyalarında tahsilat yapılan ay sayısının (dosya-ay), dosyaları elinde " +
        "tuttuğu süre ve aynı dosya grubunun tahsilat hızından beklenen sayıya oranı. Kapanan dosyanın " +
        "süresi kapandığı gün biter", al(d, "puan_siklik"),
        sayimMetni(al(d, "siklik_o"), al(d, "siklik_e")) + " dosya-ay"),
      bilesenSatiri("Güncellik", "Sıklığın aynısı, yalnız son dönemde (pencere Puanlama Kuralları " +
        "sayfasında) ve olgunluk şartı olmadan elinde tuttuğu bütün dosyalarla", al(d, "puan_guncellik"),
        sayimMetni(al(d, "guncellik_o"), al(d, "guncellik_e")) + " dosya-ay")];
    kok.innerHTML = kartUstOzet("Tahsilat Performansı " + bilgi("Tahsilat puanı üç bileşenin ağırlıklı toplamıdır; " +
      "ağırlıklar Puanlama Kuralları sayfasında, hesabın adımları Neden bu puanı aldı? bölümünde. " +
      "Gerçekleşen / beklenen her bileşenin dayanağıdır"),
      "Olgun dosya " + sayim(al(d, "n"), 1) + " (elde tutma payıyla)", durumRozeti(al(d, "durum"))) +
      "<div class='istatistikler'>" + istatistik("Tahsilat puanı", "<b>" + puanMetni(al(d, "puan")) + "</b>",
        neden ? kac(EKSIK_NEDEN[neden] || neden) : azVeriRozeti(al(d, "yeterli"), al(d, "puan"))) + "</div>" +
      "<div class='kart-govde dolu'>" + tablo(["Bileşen", "#Puan"], satirlar) + "</div>";
  };

  /* Avukatın branş tablosu: branş satırları ve bütün dosyaları için toplam satırı. Puanlar başta;
     tutar sütunları altlarında dayanağıyla (rücu tutarı, beklenen oran). */
  CIZICILER["avukat.brans"] = function (kok, s) {
    function alt(metin) { return "<div class='ikincil'>" + metin + "</div>"; }
    var satirlar = s.map(function (r) {
      var toplam = al(r, "toplam") === true;
      return "<tr" + (toplam ? " class='toplam-satiri'" : "") + ">" +
        hucre(toplam ? "<b>Tüm dosyalar</b>" : "<b>" + brans(al(r, "brans")) + "</b>") +
        hucre(skorHucre(al(r, "puan")) + (al(r, "eksik_nedeni") ?
          alt(kac(EKSIK_NEDEN[al(r, "eksik_nedeni")] || al(r, "eksik_nedeni"))) : "") +
          azVeriSatiri(al(r, "yeterli"), al(r, "puan")), true, al(r, "puan")) +
        hucre(skorHucre(al(r, "puan_tutar")), true, al(r, "puan_tutar")) +
        hucre(skorHucre(al(r, "puan_siklik")) + alt(sayimMetni(al(r, "siklik_o"), al(r, "siklik_e"))),
          true, al(r, "puan_siklik")) +
        hucre(skorHucre(al(r, "puan_guncellik")) + alt(sayimMetni(al(r, "guncellik_o"), al(r, "guncellik_e"))),
          true, al(r, "puan_guncellik")) +
        hucre(sayim(al(r, "n"), 1), true, al(r, "n")) +
        hucre(kisaTl(al(r, "gerceklesen")) + alt(kisaTl(al(r, "maruziyet"))), true, al(r, "gerceklesen")) +
        hucre(yuzde(al(r, "tahsilat_orani"), 1) + alt(yuzde(al(r, "beklenen_oran"), 1)), true,
          al(r, "tahsilat_orani")) +
        hucre(kisaTl(al(r, "dosya_basina")), true, al(r, "dosya_basina")) + "</tr>";
    });
    kok.innerHTML = kartUst("Branş Bazında Tahsilat " + bilgi("Branş puanı aynı formülle o branşın dosyalarıyla, " +
      "o branşta yayın tabanına ulaşan satırda üretilir; üretilmediyse nedeni puanın altında. Sıklık ve " +
      "güncellik altında gerçekleşen / beklenen tahsilat ayı (dosya-ay). Tahsilat altında rücu tutarı (elde " +
      "tutma payıyla); tahsilat oranı altında aynı dosya grubundan beklenen oran. Son satır avukatın bütün " +
      "dosyaları")) +
      "<div class='kart-govde dolu'>" + tablo(["Branş", "#Puan", "#Tutar", "#Sıklık", "#Güncellik",
        "#Olgun dosya", "#Tahsilat / rücu", "#Oran / beklenen", "#Dosya başına"], satirlar) + "</div>";
  };

  CIZICILER["avukat.sure"] = function (kok, s) {
    var d = s[0];
    if (!d) {
      kok.innerHTML = kartUst("Süre ve Performans") + bosDurum(sistemAdi("dava_takip") + " verisi bekleniyor ya da dönem yok.", true);
      return;
    }
    var neden = al(d, "eksik_nedeni");
    kok.innerHTML = kartUst("Süre ve Performans " + bilgi("Kriter 1 ve Kriter 2 düşümlerinin sayısının, aynı " +
      "branş ve süreçteki diğer avukatların düşüm oranından beklenen düşüm sayısına oranı"), null,
      durumRozeti(al(d, "durum"))) +
      "<div class='istatistikler'>" +
      istatistik("Risk altındaki dönem" + bilgi("Pencerede düşüm eşiğine ulaşabilecek kadar süren atama " +
        "dönemleri; yeterli veri eşiği bu dönemlerdeki farklı dosya sayısıyla sınanır"),
        sayi(al(d, "risk_donemi"), 0), sayi(al(d, "risk_dosya"), 0) + " dosya") +
      istatistik("Gerçekleşen düşüm", sayi(al(d, "o"), 0)) +
      istatistik("Beklenen düşüm" + bilgi("Aynı branş ve süreçteki diğer avukatların düşüm oranına göre " +
        "bu avukattan beklenen düşüm sayısı"), sayim(al(d, "e"), 2)) +
      istatistik("Veri kapsamı", yuzde(al(d, "kapsam"), 1, true)) +
      istatistik("Düzeltilmiş oran" + bilgi("Gerçekleşen düşümün beklenene güven ayarlı oranı; birden " +
        "küçükse beklenenden iyi"), sayi(al(d, "r"), 3)) +
      istatistik("Süre puanı", puanMetni(al(d, "puan")), neden ? kac(EKSIK_NEDEN[neden] || neden) :
        azVeriRozeti(al(d, "yeterli"), al(d, "puan"))) + "</div>";
  };

  CIZICILER["avukat.kalite_davranis"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre("<b>" + kac(SUTUN[al(r, "sutun")] || al(r, "sutun")) + "</b>") +
        hucre(sayi(al(r, "puanlanan"), 0) + " / " + sayi(al(r, "toplam"), 0) + "<div class='ikincil'>en az " +
          sayi(al(r, "gereken"), 0) + "</div>", true) +
        hucre(skorHucre(al(r, "puan")), true) + hucre(durumRozeti(al(r, "durum"))) + "</tr>";
    });
    kok.innerHTML = kartUst("Kalite ve Davranış Değerlendirmesi", "Puanlanan alt başlıkların ortalaması; puan " +
      "için gereken en az alt başlık sayısı satırda") + (satirlar.length ? "<div class='kart-govde dolu'>" + tablo(["Sütun", "#Puanlanan",
      "#Puan", "Durum"], satirlar) + "</div>" : bosDurum("Değerlendirme ölçeğinin teyidi ya da değerlendirme bekleniyor.", true));
  };

  CIZICILER["avukat.alt_basliklar"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre(kac(ALT_BASLIK[al(r, "alt_baslik")] || al(r, "alt_baslik")) + "<div class='ikincil'>" +
        kac(SUTUN[al(r, "sutun")]) + "</div>") + hucre(skorHucre(al(r, "puan")), true) +
        hucre(sayi(al(r, "degerlendirme_sayisi"), 0), true) + "</tr>";
    });
    kok.innerHTML = kartUst("Alt Başlık Puanları", "Sıfır ile yüz arası; yüksek puan olumlu değerlendirmedir") +
      (satirlar.length ? "<div class='kart-govde dolu'>" + tablo(["Alt başlık", "#Puan", "#Değerlendirme"],
        satirlar, "siralanabilir") + "</div>" : bosDurum("Değerlendirme yok.", true));
  };

  CIZICILER["avukat.mevcut_degerlendirme"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      var kod = al(r, "alt_baslik");
      return "<tr>" + hucre("<b>" + kac(MEVCUT_ALAN[kod] || kod) + "</b>") +
        hucre(sayi(al(r, "puan"), 2), true, al(r, "puan")) +
        hucre(sayi(al(r, "degerlendirme_sayisi"), 0), true, al(r, "degerlendirme_sayisi")) +
        hucre(tarih(al(r, "son_degerlendirme"))) + "</tr>";
    });
    kok.innerHTML = kartUstOzet("Mevcut Değerlendirme Alanları " + bilgi("Yeni alt başlıklar " +
      (SISTEM_ADI.degerlendirme || "") + " tarafına eklenene kadar bilgi amaçlıdır; puana girmez ve alt " +
      "başlıklara eşlenmez"), sistemAdi("degerlendirme") + " ölçeğinde ortalama") + (satirlar.length ?
      "<div class='kart-govde dolu'>" + tablo(["Alan", "#Ortalama", "#Değerlendirme", "Son"], satirlar) +
      "</div>" : bosDurum("Bu avukat için mevcut alanlarda değerlendirme yok.", true));
  };

  CIZICILER["avukat.portfoy"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre("<b>" + brans(al(r, "brans")) + "</b>") + hucre(sayi(al(r, "aktif_dosya"), 0), true) +
        hucre(sayi(al(r, "toplam_dosya"), 0), true) + hucre(tl(al(r, "aktif_rucu_tutari")), true) + "</tr>";
    });
    kok.innerHTML = kartUst("Portföy", "Aktif: açık atama · Toplam: avukatta bulunmuş tüm dosyalar") +
      "<div class='kart-govde dolu'>" + tablo(["Branş", "#Aktif", "#Toplam", "#Aktif rücu tutarı"], satirlar) +
      "</div>";
  };

  CIZICILER["avukat.sure_ozet"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre("<b>" + kac(KRITER[al(r, "kriter")]) + "</b>") + hucre(sayi(al(r, "izleniyor"), 0), true) +
        hucre(sayi(al(r, "acik_sari"), 0), true) + hucre(sayi(al(r, "acik_turuncu"), 0), true) +
        hucre(sayi(al(r, "acik_kirmizi"), 0), true) + hucre(sayi(al(r, "kapanan"), 0), true) +
        hucre(sayi(al(r, "ort_sure_gun"), 1), true) + hucre(sayi(al(r, "dusum_sayisi"), 0), true) + "</tr>";
    });
    kok.innerHTML = kartUstOzet("Süre Takibi Özeti" + bilgi("Aktif gecikmeler; pencerede kapanan dönemler ve " +
      "düşümler"), durum.golge.K1 || durum.golge.K2 ? "Gölge mod (" + kac(golgeKriterleri()) + "): düşüm " +
      "uygulanmaz, sayılar bilgi amaçlı" : null,
      satirlar.length ? "<button class='dugme' data-donemler>Dönemleri listele</button>" : "") +
      (satirlar.length ? "<div class='kart-govde dolu'>" + tablo(["Kriter", "#İzlenen", "#Sarı", "#Turuncu",
        "#Kırmızı", "#Kapanan", "#Ort. gün", "#Düşüm"], satirlar) + "</div>" : bosDurum(sistemAdi("dava_takip") +
        " verisi bekleniyor ya da dönem yok.", true));
    tiklamaBagla(kok, "[data-donemler]", function () {
      durum.filtre = { kriter: "", seviye: "", avukat: durum.kod };
      durum.bolum.sure = "donemler";
      sayfaAc("sure");
    });
  };

  CIZICILER["avukat.aylik"] = function (kok, s) {
    var veri = s.map(function (r) {
      var v = ayNoktasi(al(r, "ay"), al(r, "kismi") === true);
      v.tutar = al(r, "tutar");
      v.ek = ["Hareket", sayi(al(r, "hareket_sayisi"), 0)];
      return v;
    });
    kok.innerHTML = kartUstOzet("Aylık Tahsilat" + bilgi("Hareket tarihinde bu avukata yazılan tahsilat"),
      kismiNotu(veri)) +
      cizgiGrafik(veri, [{ anahtar: "tutar", ad: "Tahsilat", renk: "var(--ana)", alan: true }],
        "Bu dönemde tahsilat yok.");
  };

  CIZICILER["avukat.konum"] = function (kok, s) {
    var sutunlar = {}, sira = [];
    s.forEach(function (r) {
      var ad = al(r, "sutun");
      if (!sutunlar[ad]) {
        sutunlar[ad] = { kutular: [], puan: al(r, "avukat_puani"), yuzdelik: al(r, "yuzdelik"),
          toplam: al(r, "toplam"), ortanca: al(r, "ortanca") };
        sira.push(ad);
      }
      sutunlar[ad].kutular.push({ alt: al(r, "alt"), ust: al(r, "ust"), adet: al(r, "adet") });
    });
    var baslik = kartUst("Avukatların Arasındaki Yeri", "Her sütunda bütün avukatların puan dağılımı; çizgi bu " +
      "avukatın puanıdır");
    if (!sira.length) { kok.innerHTML = baslik + bosDurum("Henüz geçerli puan yok."); return; }
    var satirlar = sira.map(function (ad) {
      var v = sutunlar[ad], en = Math.max.apply(null, v.kutular.map(function (k) { return k.adet; }).concat([1]));
      var cubuklar = v.kutular.map(function (k) {
        return "<i style='height:" + (k.adet / en * 100) + "%'></i>";
      }).join("");
      var isaret = bos(v.puan) ? "" : "<b class='konum-isaret' style='left:" +
        Math.max(0, Math.min(PUAN_UST, Number(v.puan))) / PUAN_UST * 100 + "%'></b>";
      var metin = bos(v.puan) ? "<span class='ikincil'>Puan yok</span>" : "<b>" + puanMetni(v.puan) +
        "</b><span class='ikincil'>" + sayi(v.toplam, 0) + " avukat içinde yüzdelik " + sayi(v.yuzdelik, 0) +
        "</span>";
      var ad2 = (SUTUN[ad] || ad) + ": " + (bos(v.puan) ? "puan yok" : "puan " + puanMetni(v.puan) + ", yüzdelik " +
        sayi(v.yuzdelik, 0) + ", ortanca " + puanMetni(v.ortanca));
      return "<div class='konum-satir' role='img' aria-label=\"" + kac(ad2) + "\"><div class='konum-ad'>" +
        kac(SUTUN[ad] || ad) + "</div><div class='konum-serit'>" + cubuklar + isaret + "</div><div class='konum-deger'>" +
        metin + "</div></div>";
    }).join("");
    var ilk = sutunlar[sira[0]].kutular, eksen = ilk.length ? [ilk[0].alt, ilk[Math.floor(ilk.length / 2)].alt,
      ilk[ilk.length - 1].ust] : [];
    /* Eksen satırlarla aynı ızgarada durur: sütunlar daralınca da şeridin altında hizalı kalır. */
    kok.innerHTML = baslik + "<div class='kart-govde'>" + satirlar + "<div class='konum-eksen-satir'><span></span>" +
      "<div class='konum-eksen'>" + eksen.map(function (d) { return "<span>" + sayi(d, 0) + "</span>"; }).join("") +
      "</div><span></span></div></div>";
  };

  CIZICILER["avukat.gecmis"] = function (kok, s) {
    var kutular = s.map(function (r) {
      return "<div class='donem-kutu'>" + kac(donemEtiketi(al(r, "donem"))) + notRozeti(al(r, "performans_notu")) +
        "</div>";
    }).join("");
    var satirlar = s.map(function (r) {
      var eksik = al(r, "eksik_sutunlar");
      return "<tr>" + hucre("<b class='tek-satir'>" + kac(donemEtiketi(al(r, "donem"))) + "</b><div>" +
          rozet(al(r, "durum"), DONEM_DURUM[al(r, "durum")] || DURUM[al(r, "durum")]) + "</div>" +
          (eksik ? "<div class='ikincil'>Eksik: " +
          eksikSutunlar(eksik) + "</div>" : "")) +
        hucre(puanMetni(al(r, "tahsilat")), true) + hucre(puanMetni(al(r, "sure")), true) +
        hucre(puanMetni(al(r, "kalite")), true) + hucre(puanMetni(al(r, "davranis")), true) +
        hucre("<b>" + puanMetni(al(r, "birlesik_puan")) + "</b>", true) +
        hucre(bos(al(r, "genel_sira")) ? "—" : sayi(al(r, "genel_sira"), 0), true) +
        hucre("<div class='yayin-hucre'><span class='ikincil'>Sürüm " + kac(al(r, "yayin_surumu")) + " · " +
          tarih(al(r, "yayin_zamani")) + "</span><div class='mono'>" + kac(al(r, "hesap_surumu")) +
          "</div></div>") + "</tr>";
    });
    kok.innerHTML = kartUst("Not Geçmişi", "Yayımlanan dönemler değişmez; düzeltme yeni sürüm olur") +
      (kutular ? "<div class='not-gecmisi'>" + kutular + "</div>" : "") + "<div class='kart-govde dolu' " +
      "style='margin-top:8px'>" + tablo(["Dönem", "#Tahsilat", "#Süre", "#Kalite", "#Davranış", "#Birleşik",
        "#Sıra", "Yayın"], satirlar) + "</div>";
  };

  /* ---------- Süre Takibi ---------- */
  CIZICILER["sure.seviyeler"] = function (kok, s) {
    var gruplar = {};
    s.forEach(function (r) {
      var k = al(r, "kriter");
      (gruplar[k] = gruplar[k] || []).push({ seviye: al(r, "seviye"), adet: al(r, "adet") });
    });
    var sira = SEVIYE_SIRASI;
    kok.innerHTML = kartUst("Seviyelere Göre Dönemler", "Kesitteki bütün atama dönemleri") +
      (durum.golge.K1 || durum.golge.K2 ? bilgiNotu("<b>Gölge mod açık (" + kac(golgeKriterleri()) + ").</b> " +
        "Bayraklar hesaplanır ama kesinleşmemiştir: e-posta gönderilmez, puan düşümü uygulanmaz. Sayılar veri " +
        "doluluğunu ve kuralı sınamak içindir.") : "") + Object.keys(gruplar).sort().map(function (k) {
        var kutular = gruplar[k].sort(function (a, b) { return sira.indexOf(a.seviye) - sira.indexOf(b.seviye); })
          .map(function (x) {
            return "<div class='seviye-kutu " + kac(x.seviye) + (durum.golge[k] ? " golge" : "") +
              "'><div class='kpi-ad'>" +
              kac(SEVIYE[x.seviye] || x.seviye) + "</div><div class='deger'>" + sayi(x.adet, 0) + "</div></div>";
          }).join("");
        return "<div class='kriter-baslik'>" + kac(KRITER[k] || k) + "</div><div class='seviye-kutulari'>" +
          kutular + "</div>";
      }).join("");
  };

  /* Kriter 1 süre dağılımı: eşik kuralı (oto, oto dışı) başına bir panel. Uyarı ve düşüm
     bölgeleri arka planda renkli banttır; eşik günleri sonuç tablosundan gelir. */
  var KURAL_ADI = { OTO: "Oto dosyalar", OTO_DISI: "Oto dışı dosyalar", TUMU: "Bütün dosyalar" };
  /* golge: çizilen kriter gölgede mi; gölgede bayraklar nötr, "bayrak oluşmadan" her zaman ana seri rengi */
  function bayrakRengi(b, golge) {
    return golge && b !== "YOK" ? "var(--golge-" + b.toLowerCase() + ")" : BAYRAK_RENK[b];
  }
  function gunMetni(e) { return sayi(e.alt, 0) + (e.ust > e.alt ? "–" + sayi(e.ust, 0) : "") + ". gün"; }
  function surePaneli(k) {
    var altlar = k.altlar.sort(function (a, b) { return a - b; }), n = altlar.length;
    var ilk = k.kutular[altlar[0]], eksenGun = n * (Number(ilk.ust) - Number(ilk.alt));
    var sirali = ["YOK", "SARI", "TURUNCU", "KIRMIZI"].filter(function (b) { return k.bayraklar[b]; });
    var veri = altlar.map(function (alt) {
      var kutu = k.kutular[alt], aralik = bos(kutu.ust) ? sayi(kutu.alt, 0) + "+ gün" :
        sayi(kutu.alt, 0) + "–" + sayi(kutu.ust, 0) + " gün";
      return { ad: KURAL_ADI[k.ad] + ", " + aralik + ": " + sirali.map(function (b) {
          return BAYRAK_ADI[b] + " " + sayi(kutu.parcalar[b] || 0, 0); }).join(", "),
        ipucu: "<b>" + aralik + "</b><table>" + sirali.map(function (b) {
          return "<tr><td>" + BAYRAK_ADI[b] + "</td><td>" + sayi(kutu.parcalar[b] || 0, 0) + "</td></tr>";
        }).join("") + "</table>",
        parcalar: sirali.map(function (b) { return { adet: kutu.parcalar[b] || 0, renk: bayrakRengi(b, durum.golge.K1) }; }) };
    });
    var adim = Math.max(1, Math.ceil(n / 6)), etiketler = [];
    for (var i = 0; i < n; i += adim) { etiketler.push([i / n * 100, sayi(altlar[i], 0)]); }
    etiketler.push([100, bos(k.kutular[altlar[n - 1]].ust) ? sayi(altlar[n - 1], 0) + "+" :
      sayi(k.kutular[altlar[n - 1]].ust, 0)]);
    function ilkEsik(b) { return k.esikler.filter(function (e) { return e.bayrak === b; })[0]; }
    var sari = ilkEsik("SARI"), turuncu = ilkEsik("TURUNCU"), bolgeler = [];
    function konum(gun) { return Math.min(gun, eksenGun) / eksenGun * 100; }
    if (sari && sari.alt < eksenGun) {
      bolgeler.push({ sol: konum(sari.alt), genislik: konum(turuncu ? turuncu.alt : eksenGun) - konum(sari.alt),
        sinif: durum.golge.K1 ? "golge" : "sari", ad: "Uyarı" });
    }
    if (turuncu && turuncu.alt < eksenGun) {
      bolgeler.push({ sol: konum(turuncu.alt), genislik: 100 - konum(turuncu.alt),
        sinif: durum.golge.K1 ? "golge" : "turuncu", ad: "Puan düşümü" });
    }
    var esik = [sari ? "uyarı " + gunMetni(sari) : "", turuncu ? "düşüm " + gunMetni(turuncu) : ""]
      .filter(function (x) { return x; }).join(" · ");
    return "<div class='kural-paneli'><div class='kural-baslik'><b>" + kac(KURAL_ADI[k.ad] || k.ad) + "</b>" +
      "<span>" + sayi(k.toplam, 0) + " kapanan dönem · ortanca " + sayi(k.ortanca, 0) + " gün" +
      (esik ? " · " + kac(esik) : "") + "</span></div>" + histogram(veri, etiketler, [], 170, bolgeler) +
      "<div class='dg-eksen-adi'>Atamadan esas kaydına kadar geçen gün</div></div>";
  }
  CIZICILER["sure.ilk_islem_dagilim"] = function (kok, s) {
    var kurallar = {}, sira = [], tum = {};
    s.forEach(function (r) {
      var ad = al(r, "kural"), k = kurallar[ad], alt = Number(al(r, "alt"));
      if (!k) { k = kurallar[ad] = { ad: ad, kutular: {}, altlar: [], bayraklar: {}, esikler: [] }; sira.push(ad); }
      k.toplam = al(r, "toplam");
      k.ortanca = al(r, "ortanca");
      if (al(r, "tur") === "ESIK") {
        k.esikler.push({ bayrak: al(r, "bayrak"), alt: alt, ust: Number(al(r, "ust")) });
        return;
      }
      if (!k.kutular[alt]) { k.kutular[alt] = { alt: alt, ust: al(r, "ust"), parcalar: {} }; k.altlar.push(alt); }
      k.kutular[alt].parcalar[al(r, "bayrak")] = Number(al(r, "adet")) || 0;
      k.bayraklar[al(r, "bayrak")] = true;
      tum[al(r, "bayrak")] = true;
    });
    var baslik = kartUst("Kriter 1 · İlk İşlem Süresi", "Kapanan dönemlerde atamadan esas kaydına kadar geçen " +
      "gün; renk, kapanmadan önce ulaşılan en yüksek bayraktır" + (durum.golge.K1 ? " (gölge mod: bilgi amaçlı)" : ""));
    if (!sira.length) { kok.innerHTML = baslik + bosDurum("Henüz kapanan dönem yok."); return; }
    var sirali = ["YOK", "SARI", "TURUNCU", "KIRMIZI"].filter(function (b) { return tum[b]; });
    kok.innerHTML = baslik + "<div class='kural-panelleri'>" + sira.map(function (ad) {
      return surePaneli(kurallar[ad]); }).join("") + "</div>" +
      lejantKutulari(sirali.map(function (b) { return [BAYRAK_ADI[b], bayrakRengi(b, durum.golge.K1)]; }));
  };

  CIZICILER["sure.olaylar"] = function (kok, s) {
    durum.olaylar = {};
    var kayitlar = s.map(function (r) {
      var o = { dosya: al(r, "dosya_no"), avukat: al(r, "avukat_kodu"), atama: al(r, "atama_tarihi"),
        kriter: al(r, "kriter"), seviye: al(r, "seviye"), tarih: al(r, "olay_tarihi"),
        calisma: al(r, "calisma_kimligi"), sira: al(r, "son_sira") };
      var anahtar = [o.dosya, o.avukat, o.atama, o.kriter].join("|");
      (durum.olaylar[anahtar] = durum.olaylar[anahtar] || []).push(o);
      return o;
    });
    /* Son olaylar arka uçta seçilir ve sıralanır (son_sira: 1 en yeni); sayı ve eşitlik kuralı orada. */
    var son = kayitlar.filter(function (o) { return !bos(o.sira); }).sort(function (a, b) { return a.sira - b.sira; });
    kok.innerHTML = kartUst("Son Bayrak Olayları", "Olay tarihi eşik tarihidir; kayıtlar silinmez") +
      "<div class='kart-govde dolu'>" + tablo(["Tarih", "Dosya", "Seviye", "Çalışma"], son.map(function (o) {
        return "<tr>" + hucre(tarih(o.tarih)) + hucre("<b>" + kac(o.dosya) + "</b><div class='ikincil'>" +
          kac(KRITER[o.kriter]) + " · " + kac(o.avukat) + "</div>") + hucre(seviyeRozeti(o.seviye, o.kriter)) +
          hucre("<span class='mono'>" + kac(o.calisma) + "</span>") + "</tr>";
      })) + "</div>";
  };

  CIZICILER["sure.filtre"] = function (kok, s) {
    var o = s[0], f = durum.filtre;
    if (!o) { kok.innerHTML = ""; return; }
    var toplam = al(o, "toplam"), gosterilen = al(o, "gosterilen");
    var avukatlar = (al(o, "avukatlar") || []).concat(f.avukat ? [f.avukat] : [])
      .filter(function (v, i, d) { return d.indexOf(v) === i; }).sort();
    function secenek(ad, degerler, etiket) {
      return "<label>" + ad + "<select data-filtre='" + ad.toLowerCase() + "'><option value=''>Tümü</option>" +
        degerler.map(function (v) {
          return "<option value='" + kac(v) + "'" + (f[ad.toLowerCase()] === v ? " selected" : "") + ">" +
            kac(etiket ? etiket[v] || v : v) + "</option>";
        }).join("") + "</select></label>";
    }
    kok.innerHTML = kartUst("Dönem Listesi", f.seviye ? "Seçilen seviyedeki bütün dönemler" :
      "Açık dönemler ve süre puanı penceresinde düşüm almış dönemler; en ağır seviye önce. Kapanan ve " +
      "kapsam dışı dönemler seviye seçilince listelenir") + "<div class='filtreler'>" +
      secenek("Kriter", ["K1", "K2"], KRITER) + secenek("Seviye", SEVIYE_SIRASI, SEVIYE) +
      secenek("Avukat", avukatlar) +
      "<button class='temizle' data-temizle>Temizle</button><span class='bosluk'></span><span class='sayac'>" +
      (gosterilen < toplam ? "En ağır " + sayi(gosterilen, 0) + " / " + sayi(toplam, 0) + " dönem gösteriliyor; " +
        "daraltmak için filtreleyin" : sayi(toplam, 0) + " dönem") + "</span></div>";
    Array.prototype.forEach.call(kok.querySelectorAll("select[data-filtre]"), function (el) {
      el.onchange = function () {
        durum.filtre[el.getAttribute("data-filtre")] = el.value;
        sayfaAc("sure");
      };
    });
    tiklamaBagla(kok, "[data-temizle]", function () {
      durum.filtre = { kriter: "", seviye: "", avukat: "" };
      sayfaAc("sure");
    });
  };

  /* Düşüm hücresi: düşümün puana girip girmediği (gölge modda ve gölge döneminde girmez). */
  function dusumMetni(x, yok) {
    if (!x.dusum) { return yok; }
    return kac(DUSUM_DURUMU[x.dusumDurumu] || "Evet") + " · " + tarih(x.dusumTarihi);
  }
  CIZICILER["sure.liste"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return { kriter: al(r, "kriter"), dosya: al(r, "dosya_no"), avukat: al(r, "avukat_kodu"),
        brans: al(r, "brans"), atama: al(r, "atama_tarihi"), bitis: al(r, "bitis_tarihi"),
        bitisNedeni: al(r, "bitis_nedeni"), ref: al(r, "atama_ref"), seviye: al(r, "seviye"),
        enYuksek: al(r, "en_yuksek_seviye"), dusum: al(r, "dusum"), dusumTarihi: al(r, "dusum_tarihi"),
        dusumDurumu: al(r, "dusum_durumu"),
        gun: al(r, "sure_gun"), olcumSonu: al(r, "olcum_sonu"), sari: al(r, "esik_sari"),
        turuncu: al(r, "esik_turuncu"), kirmizi: al(r, "esik_kirmizi"), neden: al(r, "kapsam_disi_nedeni"),
        esas: al(r, "esas_ilk_giris"), surec: al(r, "surec_turu"), surecBas: al(r, "surec_baslangici"),
        dava: al(r, "dava_ilk_giris"), kayip: al(r, "kosul_kayip_tarihi"), kod: al(r, "rucu_kodu"),
        bakiye: al(r, "acik_bakiye") };
    });
    kok.innerHTML = "<div class='kart-govde dolu'>" +
      tablo(["Dosya", "Avukat", "Branş", "Atama", "#Süre", "Seviye", "Düşüm"], satirlar.map(function (x, i) {
        return "<tr class='tiklanir' data-sira='" + i + "'>" + hucre("<b>" + kac(x.dosya) +
          "</b><div class='ikincil'>" + kac(KRITER[x.kriter]) + "</div>") + hucre(kac(x.avukat)) +
          hucre(brans(x.brans)) + hucre(tarih(x.atama)) + hucre(bos(x.gun) ? "—" : sayi(x.gun, 0) + " gün", true, x.gun) +
          hucre(seviyeRozeti(x.seviye, x.kriter), false, SEVIYE_SIRASI.indexOf(x.seviye)) +
          hucre(dusumMetni(x, "—"), false, x.dusum ? Number(String(x.dusumTarihi).replace(/-/g, "")) : null) +
          "</tr>";
      }), "siralanabilir") + "</div>";
    tiklamaBagla(kok, "tr[data-sira]", function (el) {
      var x = satirlar[Number(el.getAttribute("data-sira"))];
      var olaylar = durum.olaylar[[x.dosya, x.avukat, x.atama, x.kriter].join("|")] || [];
      var tanim = [["Kriter", kac(KRITER[x.kriter])], ["Avukat", kac(x.avukat)], ["Branş", brans(x.brans)],
        ["Atama tarihi", tarih(x.atama)], ["Atama bitişi", tarih(x.bitis) + (x.bitisNedeni ? " · " +
          kac(BITIS[x.bitisNedeni] || x.bitisNedeni) : "")], ["Atama referansı", kac(x.ref)],
        ["Seviye", seviyeRozeti(x.seviye, x.kriter)], ["Ulaşılan en yüksek", seviyeRozeti(x.enYuksek, x.kriter)],
        ["Süre", bos(x.gun) ? "—" : sayi(x.gun, 0) + " gün (bitiş " + tarih(x.olcumSonu) + ")"],
        ["Sarı eşiği", tarih(x.sari)], ["Turuncu eşiği (düşüm)", tarih(x.turuncu)],
        ["Kırmızı eşiği", tarih(x.kirmizi)], ["Puan düşümü", dusumMetni(x, "Hayır")]];
      if (x.kriter === "K1") {
        tanim.push(["Esasın ilk girişi", tarih(x.esas)]);
      } else {
        tanim.push(["Süreç", kac(SUREC[x.surec] || x.surec)], ["Süreç başlangıcı", tarih(x.surecBas)],
          ["Dava esasının ilk girişi", tarih(x.dava)], ["Koşulun kalktığı gün", tarih(x.kayip)],
          ["Rücu kodu · açık bakiye", kac(x.kod) + " · " + tl(x.bakiye)]);
      }
      if (x.neden) { tanim.push(["Kapsam dışı nedeni", kac(KAPSAM_DISI[x.neden] || x.neden)]); }
      cekmeceAc("<div class='cekmece-ust'><div><div class='avukat-ad' id='cekmece-baslik'>" + kac(x.dosya) + "</div><div class='ikincil'>" +
        kac(KRITER[x.kriter]) + "</div></div><button class='dugme' data-kapat>Kapat</button></div><dl class='tanim'>" +
        tanim.map(function (t) { return "<dt>" + t[0] + "</dt><dd>" + t[1] + "</dd>"; }).join("") +
        "</dl><div class='kart-ust'><h2>Bayrak geçmişi</h2></div><div class='zaman-cizelgesi'>" +
        (olaylar.length ? olaylar.map(function (o) {
          return "<div class='zaman-oge'>" + seviyeRozeti(o.seviye, o.kriter) + "<span>" + tarih(o.tarih) +
            "</span><span class='mono'>" + kac(o.calisma) + "</span></div>";
        }).join("") : "<div class='ikincil'>Bayrak oluşmadı.</div>") + "</div>");
    });
  };

  CIZICILER["sure.eposta"] = function (kok, s) {
    // Gönderim kriter bazındadır: liste ancak hiçbir satır gönderilmeyecekse "gölge mod" sayılır.
    var golge = s.length && !s.some(function (r) { return al(r, "gonderilecek"); });
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre("<b>" + kac(al(r, "avukat_kodu")) + "</b>") + hucre(sayi(al(r, "kirmizi"), 0), true) +
        hucre(sayi(al(r, "turuncu"), 0), true) + hucre(sayi(al(r, "sari"), 0), true) +
        hucre("<b>" + sayi(al(r, "toplam"), 0) + "</b>", true) +
        hucre(al(r, "gonderilecek") ? rozet("GECTI", "Gönderilecek") : rozet("GOLGE_MOD", "Gölge mod")) + "</tr>";
    });
    kok.innerHTML = kartUstOzet("Gecikme E-postası Listesi" + bilgi("Aktif gecikmesi olan avukatlara " +
      "gönderilecek liste"), golge ? "Gölge mod açık: liste hazırlanır, gönderilmez" : null) + "<div class='kart-govde dolu'>" +
      tablo(["Avukat", "#Kırmızı", "#Turuncu", "#Sarı", "#Toplam", "Gönderim"], satirlar, "siralanabilir") +
      "</div>";
  };

  /* ---------- Puanlama Kuralları ---------- */
  CIZICILER["kurallar.hatalar"] = function (kok, s) {
    var hatalar = s.map(function (r) { return "<li>" + kac(al(r, "hata")) + "</li>"; }).join("");
    kok.hidden = !hatalar;
    kok.innerHTML = hatalar ? kartUst("Parametre Dosyası Geçersiz", null, rozet("KALDI", "Gece başlamaz")) +
      bilgiNotu("Gecelik çalışma bu dosyayla başlamaz; ekrandaki sonuçlar son başarılı gecenin " +
        "kurallarıyladır. Aşağıdaki hataları params.json ya da params_ek.json dosyasında düzeltin.") +
      "<div class='kart-govde'><ul class='hata-listesi'>" + hatalar + "</ul></div>" : "";
  };
  CIZICILER["kurallar.agirliklar"] = function (kok, s) {
    var kalemler = s.map(function (r) {
      return { sutun: al(r, "sutun"), agirlik: al(r, "agirlik"), teyit: al(r, "teyit_bekliyor"),
        aciklama: al(r, "aciklama") };
    });
    var serit = kalemler.map(function (k) {
      return "<div class='sutun-" + kac(k.sutun) + "' style='flex:" + (Number(k.agirlik) || 0) +
        "' data-ipucu=\"" + kac(kac(SUTUN[k.sutun] || k.sutun)) +
        "\"><div class='ad'>" + kac(SUTUN[k.sutun] || k.sutun) + "</div><div class='oran'>" + yuzde(k.agirlik, 0) +
        "</div></div>";
    }).filter(function (html, i) { return !puanaGirmez(kalemler[i].agirlik); }).join("");
    var ilk = kalemler[0] || {};
    kok.innerHTML = kartUst("Birleşik Puan Nasıl Hesaplanır?", "Her sütun sıfır ile yüz arasında puanlanır, " +
      "ağırlığıyla çarpılıp toplanır", teyitRozeti(ilk.teyit)) + teyitNotu(ilk.teyit, ilk.aciklama) +
      "<div class='kart-govde'><div class='adim-baslik'>Ağırlıklar</div>" +
      "<div class='agirlik-seridi'>" + serit + "</div>" + kalemler.map(function (k) {
        return satirCubuk(kac(SUTUN[k.sutun] || k.sutun), puanaGirmez(k.agirlik) ? "<span class='ikincil'>" +
          "Bu fazda puana girmez</span>" : "<b>" + yuzde(k.agirlik, 0) + "</b>", k.agirlik);
      }).join("") + "</div>";
  };

  function teyitRozeti(teyit) { return teyit ? rozet("TEYIT_BEKLIYOR", "Teyit bekliyor") : ""; }
  function teyitNotu(teyit, metin) { return teyit && metin ? bilgiNotu(kac(metin)) : ""; }
  CIZICILER["kurallar.notlar"] = function (kok, s) {
    var teyit = s.length && al(s[0], "teyit_bekliyor"), aciklama = s.length ? al(s[0], "aciklama") : "";
    var olcek = s.slice().reverse().map(function (r) {
      return "<div>" + notRozeti(al(r, "not_adi")) + "<div class='ikincil'>Birleşik puan ≥ " +
        sayi(al(r, "esik"), 0) + "</div></div>";
    }).join("");
    kok.innerHTML = kartUst("Performans Notu", "Yuvarlanmış birleşik puanın ulaştığı en yüksek eşik; not " +
      "yalnız birleşik puan hesaplanınca verilir", teyitRozeti(teyit)) + teyitNotu(teyit, aciklama) +
      "<div class='kart-govde'><div class='adim-baslik'>Not ölçeği" +
      "</div><div class='not-olcegi'>" + olcek + "</div></div>";
  };

  CIZICILER["kurallar.parametreler"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre(kac(al(r, "bolum"))) + hucre("<b>" + kac(al(r, "ad")) + "</b>") +
        hucre("<span class='mono'>" + kac(al(r, "deger")) + "</span>") +
        hucre(al(r, "teyit_bekliyor") ? rozet("TEYIT_BEKLIYOR", "Teyit bekliyor") : "") + "</tr>";
    });
    kok.innerHTML = kartUst("Parametreler " + bilgi("Teyit bekleyen değerler Hukuk onayıyla kesinleşir; " +
      "değişiklik hesap sürümünü değiştirir")) +
      "<div class='kart-govde dolu'>" + tablo(["Bölüm", "Ad", "Değer", ""], satirlar, "siralanabilir") + "</div>";
  };

  CIZICILER["kurallar.aciklamalar"] = function (kok, s) {
    kok.innerHTML = kartUst("Açıklamalar") + "<div class='kart-govde'>" + s.map(function (r) {
      return "<p style='margin:0 0 10px'><b>" + kac(al(r, "bolum")) + ":</b> " + kac(al(r, "aciklama")) + "</p>";
    }).join("") + "</div>";
  };

  /* ---------- Veri Durumu ---------- */
  CIZICILER["veri.kaynaklar"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      var kaynak = al(r, "kaynak");
      return "<tr>" + hucre("<b>" + sistemAdi(al(r, "sistem")) + "</b><div class='ikincil'>" +
        kac(KAYNAK_ACIKLAMA[kaynak] || kaynak) + "</div>") +
        hucre(kac(YONTEM[al(r, "yontem")] || al(r, "yontem"))) + hucre(tarih(al(r, "cekim_tarihi"))) +
        hucre(sayi(al(r, "satir_sayisi"), 0), true) + hucre(durumRozeti(al(r, "kalite_sonucu"))) +
        hucre(durumRozeti(al(r, "durum"))) + hucre(tarih(al(r, "son_basarili"))) +
        hucre(bos(al(r, "arsiv_yolu")) ? "<span class='ikincil'>—</span>" : ipucuRozeti("", "Arşivde",
          al(r, "arsiv_yolu"))) + "</tr>";
    });
    kok.innerHTML = kartUst("Kaynaklar", "Son gecelik çalışma; yöntem kaynaklar.json ayarından gelir") +
      "<div class='kart-govde dolu'>" + tablo(["Kaynak", "Yöntem", "Çekim", "#Satır", "Kalite", "Durum",
        "Son başarılı", "Ham arşiv"], satirlar, "siralanabilir") + "</div>";
  };

  CIZICILER["veri.calismalar"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre("<span class='mono'>" + kac(al(r, "calisma_kimligi")) + "</span><div class='ikincil'>" +
        kac(CALISMA_TURU[al(r, "tur")] || al(r, "tur")) + " · kesit " + tarih(al(r, "cekim_tarihi")) + "</div>") +
        hucre(tarih(al(r, "baslangic")) + "<div class='ikincil'>" + tarih(al(r, "bitis")) + "</div>") +
        hucre(durumRozeti(al(r, "durum")) + (al(r, "aciklama") ? "<div class='ikincil'>" + kac(al(r, "aciklama")) +
          "</div>" : "")) + "</tr>";
    });
    kok.innerHTML = kartUst("Son Çalışmalar") + "<div class='kart-govde dolu'>" +
      tablo(["Çalışma", "Başlangıç · bitiş", "Sonuç"], satirlar) + "</div>";
  };

  CIZICILER["veri.kalite"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      var kaynak = al(r, "kaynak");
      return "<tr>" + hucre("<b>" + kac(KAYNAK_ACIKLAMA[kaynak] || DENETIM_KAYNAGI[kaynak] || kaynak) +
        "</b><div class='ikincil'>" + denetimAdi(al(r, "kontrol")) +
        "</div>") + hucre(durumRozeti(al(r, "durum"))) + hucre(denetimSayisi(al(r, "deger")) + " / " +
        denetimSayisi(al(r, "esik")), true) + hucre(kac(al(r, "aciklama")) + "<div class='mono'>" +
        kac(al(r, "calisma_kimligi")) + " · " + tarih(al(r, "cekim_tarihi")) + "</div>") + "</tr>";
    });
    kok.innerHTML = kartUst("Kalite Kapısı", "Son çalışmanın geçmeyen ya da uyarı veren denetimleri") +
      (satirlar.length ? "<div class='kart-govde dolu'>" + tablo(["Denetim", "Durum", "#Değer / eşik",
        "Açıklama"], satirlar) + "</div>" : bosDurum("Son çalışmada bütün denetimler geçti."));
  };

  /* Düzeltme incelemesinin başlığı ve sayacı: tablo en yeni çelişkilerle sınırlıysa kaç tanesinin
     gösterildiği söylenir (sınır ve sıra arka uçta). */
  CIZICILER["veri.celiski_ozet"] = function (kok, s) {
    var o = s[0] || {}, toplam = al(o, "toplam"), gosterilen = al(o, "gosterilen");
    kok.innerHTML = kartUstOzet("Düzeltme İncelemesi" + bilgi("Kayıtlı bayrak olayı yeni hesapla çelişiyor " +
      "(geriye dönük veri değişikliği); en yeni tespit önce"), bos(toplam) ? null : gosterilen < toplam ?
      "En yeni " + sayi(gosterilen, 0) + " / " + sayi(toplam, 0) + " çelişki gösteriliyor" :
      sayi(toplam, 0) + " çelişki");
  };

  CIZICILER["veri.celiski"] = function (kok, s) {
    var satirlar = s.map(function (r) {
      return "<tr>" + hucre("<b>" + kac(al(r, "dosya_no")) + "</b><div class='ikincil'>" + kac(al(r, "avukat_kodu")) +
        " · atama " + tarih(al(r, "atama_tarihi")) + "</div>") + hucre(kac(KRITER[al(r, "kriter")])) +
        hucre(seviyeRozeti(al(r, "seviye"), al(r, "kriter"))) + hucre(tarih(al(r, "olay_tarihi")) + " → " +
        tarih(al(r, "olay_tarihi_yeni"))) + hucre(tarih(al(r, "tespit_tarihi")) + "<div class='mono'>" +
        kac(al(r, "calisma_kimligi")) + "</div>") + "</tr>";
    });
    kok.innerHTML = satirlar.length ? "<div class='kart-govde dolu'>" + tablo(["Dosya", "Kriter",
      "Seviye", "Olay tarihi: kayıtlı → yeni", "Tespit"], satirlar) + "</div>" : bosDurum("Çelişen olay yok.");
  };

  /* ---------- sayfa yükleme ---------- */
  function istek(sorgu) {
    var parcalar = Object.keys(sorgu).filter(function (k) { return !bos(sorgu[k]); }).map(function (k) {
      return encodeURIComponent(k) + "=" + encodeURIComponent(sorgu[k]);
    });
    return fetch(getWebAppBackendUrl("/api/sayfa") + "?" + parcalar.join("&"),
      { credentials: "same-origin" }).catch(function () {
      throw new Error("Sunucuya ulaşılamadı.");
    }).then(function (yanit) {
      if (!yanit.ok) { throw new Error("Sunucu hata verdi (HTTP " + yanit.status + ")."); }
      return yanit.json().catch(function () { throw new Error("Sunucu yanıtı okunamadı."); });
    }).then(function (veri) {
      if (!veri || typeof veri.bilesenler !== "object") { throw new Error("Sunucu yanıtı okunamadı."); }
      return veri;
    });
  }

  function sayfaBos(ad) {
    /* Okuma kesintisi kurulum günü gibi anlatılmaz: tablo okunamadıysa sonuç var ama gelmedi. */
    if (durum.okunamayan.length) {
      return "Bazı tablolar okunamadı (" + kac(durum.okunamayan.join(", ")) + "); bu bir okuma kesintisidir, " +
        "sonuçlar silinmedi. Birkaç saniye sonra sayfayı yeniden açın.";
    }
    var metin = { genel: "Henüz hesaplanmış sonuç yok. Zorunlu kaynaklar (" + sistemAdi("cekirdek") +
      ": dosya ve atama logları) bağlanıp ilk gecelik çalışma tamamlanınca bu sayfa dolar.",
      avukat: "Henüz avukat sonucu yok. İlk başarılı gecelik çalışmadan sonra dolar.",
      sure: "Süre takibi için esas kaydı gerekir: " + sistemAdi("dava_takip") + " bağlantısı ya da " +
        sistemAdi("cekirdek") + " takip bilgileri gelince açılır.",
      kurallar: "Parametre dosyası okunamadı.", veri: "Henüz çalışma kaydı yok. İlk gecelik çalışmadan " +
        "sonra dolar." };
    return metin[ad];
  }
  /* Yeniden çizimden sonra klavye odağı aynı denetime döner (filtre, avukat satırı, seçenek). */
  var ODAK_OZNITELIKLERI = ["data-filtre", "data-kod", "data-not-filtre", "data-dagilim", "data-temizle"];
  function odakSecicisi(el) {
    if (!el || !el.getAttribute) { return null; }
    var ad = ODAK_OZNITELIKLERI.filter(function (o) { return el.hasAttribute(o); })[0];
    if (!ad) { return null; }
    var bilesen = el.closest("[data-bilesen]");
    return (bilesen ? "[data-bilesen='" + bilesen.getAttribute("data-bilesen") + "'] " : "") + "[" + ad + "='" +
      String(el.getAttribute(ad) || "").replace(/['\\]/g, "") + "']";
  }
  /* Yanıtta olmayan bileşenin iletisi: Veri Durumu kendi bileşeni için kendine yönlendirmez;
     geçersiz parametrede kural kartları hata listesine yönlendirir. */
  function eksikBilesenMetni() {
    if (durum.sayfa === "veri") { return "Henüz bu denetim için kayıt yok."; }
    if (durum.sayfa === "kurallar" && durum.parametreHatasi) {
      return "Parametre dosyası geçersiz olduğu için hesaplanmadı; hatalar sayfanın başında.";
    }
    return "Bu bölümün sonucu henüz üretilmedi; nedeni Veri Durumu sayfasında.";
  }
  function ciz(bilesenler) {
    var odak = odakSecicisi(document.activeElement);
    if (bilesenler["ortak.adlar"]) { CIZICILER["ortak.adlar"](null, bilesenler["ortak.adlar"]); }
    var bolum = document.getElementById("sayfa-" + durum.sayfa);
    var sayfadakiler = Array.prototype.map.call(bolum.querySelectorAll("[data-bilesen]"), function (el) {
      return el.getAttribute("data-bilesen");
    });
    function veriVar(kayitlar) {
      return Array.isArray(kayitlar) && kayitlar.some(function (kayit) {
        return Object.keys(kayit).some(function (k) { return !bos(kayit[k]) && kayit[k] !== false; });
      });
    }
    /* Ortak şerit sayfanın başında (belge sırası) çizilir: gölge, bekleyen kaynak ve okuma durumu
       sonraki bileşenlerin boş durumunu belirler. */
    var secici = "#sayfa-" + durum.sayfa + " [data-bilesen], [data-bilesen^='ortak.']";
    Array.prototype.forEach.call(document.querySelectorAll(secici), function (kok) {
      var kimlik = kok.getAttribute("data-bilesen"), veri = bilesenler[kimlik];
      if (TAHSILAT_BILESENLERI.indexOf(kimlik) >= 0 && tahsilatBekleniyor() && !veriVar(veri)) {
        bekleniyorCiz(kok, kimlik);
        return;
      }
      if (veri === undefined) {
        kok.innerHTML = kimlik.indexOf("ortak.") === 0 ? "<span>Henüz çalışma yok</span>" :
          bosDurum(eksikBilesenMetni(), true);
        return;
      }
      try { CIZICILER[kimlik](kok, veri); } catch (hata) {
        kok.innerHTML = "<div class='hata-kutu'>Bileşen çizilemedi: " + kac(kimlik) + " · " + kac(hata.message) + "</div>";
      }
    });
    var hepsiBos = !sayfadakiler.some(function (k) { return veriVar(bilesenler[k]); });
    bolum.classList.toggle("veri-yok", hepsiBos);
    var not = bolum.querySelector(".sayfa-bos");
    if (not) { not.remove(); }
    if (hepsiBos) {
      bolum.querySelector(".sayfa-baslik").insertAdjacentHTML("afterend", "<div class='sayfa-bos'><b>" +
        "Bu sayfada henüz gösterilecek sonuç yok.</b><p>" + sayfaBos(durum.sayfa) + "</p>" +
        (durum.sayfa === "veri" ? "" : "<button class='dugme' data-git='veri'>Kaynakların durumunu gör" +
        "</button>") + "</div>");
      tiklamaBagla(bolum, "[data-git]", function (el) { sayfaAc(el.getAttribute("data-git")); });
    }
    var eksik = Object.keys(durum.eksikAlanlar);
    if (eksik.length) {
      var kutu = document.createElement("div");
      kutu.className = "hata-kutu";
      kutu.textContent = "Sözleşme dışı alan istendi: " + eksik.join(", ");
      document.getElementById("sayfa-" + durum.sayfa).prepend(kutu);
    }
    var hedef = odak ? document.querySelector(odak) : null;
    if (hedef) { hedef.focus({ preventScroll: true }); }
  }

  /* yuklenen[sayfa]: son başarılı yanıt ve o yanıtın seçimi (avukat, filtre). İstek hata verirse
     seçim buna geri alınır ve son başarılı görünüm yeniden çizilir; seçim ile veri ayrışmaz. */
  var yuklenen = {}, istekSirasi = 0;
  function filtreKopya(f) { return { kriter: f.kriter, seviye: f.seviye, avukat: f.avukat }; }
  function filtreAyni(a, b) { return a.kriter === b.kriter && a.seviye === b.seviye && a.avukat === b.avukat; }
  function istekHatasi(ad, bolum, hata, deneme) {
    var son = yuklenen[ad];
    if (son) {
      durum.kod = son.kod;
      durum.filtre = filtreKopya(son.filtre);
      ciz(son.bilesenler);
    } else {
      Array.prototype.forEach.call(bolum.querySelectorAll("[data-bilesen]"), function (el) {
        if (el.querySelector(".yukleniyor")) { el.innerHTML = bosDurum("Veri alınamadı.", true); }
      });
    }
    bolum.insertAdjacentHTML("afterbegin", "<div class='hata-kutu' role='alert'><span>Veri alınamadı: " +
      kac(hata.message) + (son ? " Son başarılı görünüm gösteriliyor." : "") + "</span><button " +
      "class='dugme' data-yeniden>Yeniden dene</button></div>");
    bolum.querySelector("[data-yeniden]").onclick = function () {
      durum.filtre = filtreKopya(deneme.filtre);
      sayfaAc(ad, ad === "avukat" ? { kod: deneme.kod } : null);
    };
  }
  /* ---------- adres: geri ve ileri tuşları ---------- */
  /* Seçilen sayfa, bölüm ve avukat adres çubuğuna yazılır (#genel/siralama, #avukat/AV-01/tahsilat)
     ve tarayıcı geçmişine girer; geri tuşu bir önceki ekrana döner. Dataiku'da uygulama bir
     çerçevede çalışır; çerçevenin adresi de tarayıcı geçmişine yazılır. */
  function adresKur(ad, kod) {
    var ek = ad === "avukat" ? [kod || durum.kod, durum.sekme !== "ozet" ? durum.sekme : null] :
      [durum.bolum[ad] && durum.bolum[ad] !== "ozet" ? durum.bolum[ad] : null];
    return "#" + [ad].concat(ek.filter(function (x) { return !bos(x); })).map(encodeURIComponent).join("/");
  }
  function adresParcalari() {
    return location.hash.replace(/^#\/?/, "").split("/").map(function (x) {
      try { return decodeURIComponent(x); } catch (hata) { return x; }
    });
  }
  /* Gezinti: adres değişirse yükleme adres olayıyla yapılır; aynıysa (ör. süzgeç) doğrudan. */
  function sayfaAc(ad, secim) {
    var hedef = adresKur(ad, ad === "avukat" && secim ? secim.kod : null);
    if (location.hash !== hedef) { location.hash = hedef; } else { sayfaYukle(ad, secim); }
  }
  /* Adres değişince bir kez uygulanır (tarayıcılar aynı geçiş için hem hashchange hem popstate
     olayı verebilir). */
  var uygulananAdres = null;
  function adresUygula() {
    if (uygulananAdres === location.hash) { return; }
    uygulananAdres = location.hash;
    var p = adresParcalari(), ad = SAYFALAR.indexOf(p[0]) >= 0 ? p[0] : "genel";
    var kodDegisti = ad === "avukat" && !bos(p[1]) && p[1] !== durum.kod;
    if (ad === "avukat") {
      if (!bos(p[1])) { durum.kod = p[1]; }
      sekmeSec(p[2] || "ozet");
    } else if (durum.bolum[ad] !== undefined) {
      bolumSec(ad, p[1] || "ozet");
      /* Geçersiz bölüm adı (#genel/xyz) gösterilen bölüme düzeltilir. */
      if (location.hash !== adresKur(ad) && !bos(p[1])) {
        uygulananAdres = adresKur(ad);
        history.replaceState(null, "", uygulananAdres);
      }
    }
    /* Zil ya da menü Süre Takibi süzgecini değiştirdiyse sayfa yüklü olsa da yeniden istenir. */
    var filtreDegisti = ad === "sure" && yuklenen.sure && !filtreAyni(yuklenen.sure.filtre, durum.filtre);
    if (ad !== durum.sayfa || kodDegisti || !yuklenen[ad] || filtreDegisti) {
      sayfaYukle(ad, kodDegisti ? { kod: durum.kod } : null);
    }
  }
  /* Sayfa içi bölüm ve avukat kartı sekmeleri: seçim adres çubuğuna yazılır. */
  function sekmeKumesi(kap, secici, nitelik, panelSecici, panelNitelik, deger, odakla) {
    var sekmeler = Array.prototype.slice.call(kap.querySelectorAll(secici));
    var secili = sekmeler.filter(function (b) { return b.getAttribute(nitelik) === deger; })[0] || sekmeler[0];
    if (!secili) { return null; }
    sekmeler.forEach(function (b) {
      b.classList.toggle("etkin", b === secili);
      b.setAttribute("aria-selected", b === secili ? "true" : "false");
      b.tabIndex = b === secili ? 0 : -1;
    });
    Array.prototype.forEach.call(kap.querySelectorAll(panelSecici), function (p) {
      p.classList.toggle("etkin", p.getAttribute(panelNitelik) === secili.getAttribute(nitelik));
    });
    if (odakla) { secili.focus(); }
    return secili.getAttribute(nitelik);
  }
  function bolumSec(ad, bolum, odakla) {
    durum.bolum[ad] = sekmeKumesi(document.getElementById("sayfa-" + ad), ".bolum-sekme", "data-bolum",
      ".bolum-panel", "data-bolum-panel", bolum, odakla) || "ozet";
  }
  function sekmeSec(sekme, odakla) {
    durum.sekme = sekmeKumesi(document.getElementById("sayfa-avukat"), ".sekme", "data-sekme",
      ".sekme-panel", "data-panel", sekme, odakla) || "ozet";
  }
  function sekmeleriBagla(secici, nitelik, sec) {
    Array.prototype.forEach.call(document.querySelectorAll(secici), function (el) {
      el.addEventListener("click", function () { sec(el.getAttribute(nitelik)); });
      el.addEventListener("keydown", function (e) {
        var kume = Array.prototype.slice.call(el.parentNode.querySelectorAll(secici)), i = kume.indexOf(el);
        var n = kume.length, hedef = { ArrowRight: (i + 1) % n, ArrowLeft: (i + n - 1) % n, Home: 0,
          End: n - 1 }[e.key];
        if (hedef !== undefined) { e.preventDefault(); sec(kume[hedef].getAttribute(nitelik), true); }
      });
    });
  }

  function sayfaYukle(ad, secim) {
    var sayfaDegisti = durum.sayfa !== ad, bolum = document.getElementById("sayfa-" + ad), sira = ++istekSirasi;
    durum.sayfa = ad;
    durum.eksikAlanlar = {};
    Array.prototype.forEach.call(document.querySelectorAll(".sayfa"), function (el) {
      el.classList.toggle("etkin", el.id === "sayfa-" + ad);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".menu-oge"), function (el) {
      var etkin = el.getAttribute("data-sayfa") === ad;
      el.classList.toggle("etkin", etkin);
      if (etkin) { el.setAttribute("aria-current", "page"); } else { el.removeAttribute("aria-current"); }
    });
    var sorgu = { ad: ad };
    if (ad === "avukat") { durum.kod = (secim && secim.kod) || durum.kod; sorgu.kod = durum.kod; }
    if (ad === "sure") { sorgu.kriter = durum.filtre.kriter; sorgu.seviye = durum.filtre.seviye; sorgu.avukat = durum.filtre.avukat; }
    Array.prototype.forEach.call(bolum.querySelectorAll(".hata-kutu"), function (el) { el.remove(); });
    if (yuklenen[ad]) {
      bolum.classList.add("yenileniyor");
    } else {
      Array.prototype.forEach.call(bolum.querySelectorAll("[data-bilesen]"), function (el) {
        if (el.id !== "neden-paneli") { el.innerHTML = yukleniyor(); }
      });
    }
    var deneme = { kod: durum.kod, filtre: filtreKopya(durum.filtre) };
    istek(sorgu).then(function (veri) {
      if (sira !== istekSirasi) { return; }
      bolum.classList.remove("yenileniyor");
      ciz(veri.bilesenler);
      yuklenen[ad] = { bilesenler: veri.bilesenler, kod: durum.kod, filtre: filtreKopya(durum.filtre) };
    }).catch(function (hata) {
      if (sira !== istekSirasi) { return; }
      bolum.classList.remove("yenileniyor");
      istekHatasi(ad, bolum, hata, deneme);
    });
    if (sayfaDegisti || (secim && secim.kod)) { window.scrollTo(0, 0); }
  }

  /* ---------- dışa aktarma ----------
     Bulunulan sayfanın o an seçili bölümünde (ya da avukat kartının seçili sekmesinde) ekranda
     görünen veri tabloları (table.tablo) indirilir; gizli bölüm ve sekmelerin tabloları girmez.
     Başlık ve hücreler ekrandaki metindir; tek değerli sayı hücresi (data-deger) sayı olarak
     gider, yüzde hücresi oran olarak tutulur. Arama ya da süzgeçle gizlenen satırlar dosyaya
     girmez. Excel dosyası (xlsx) harici kütüphane olmadan, sıkıştırmasız ZIP olarak kurulur;
     CSV noktalı virgülle ayrılır, ondalık virgüldür (Türkçe Excel). */
  function hucreMetni(el) {
    var kopya = el.cloneNode(true);
    Array.prototype.forEach.call(kopya.querySelectorAll(".bilgi, .cubuk, svg, button"), function (x) {
      x.parentNode.removeChild(x);
    });
    Array.prototype.forEach.call(kopya.querySelectorAll("div, p, br"), function (x) {
      x.parentNode.insertBefore(document.createTextNode(" · "), x);
    });
    return kopya.textContent.replace(/\s+/g, " ").replace(/(\s*·\s*)+/g, " · ")
      .replace(/^\s*·\s*|\s*·\s*$/g, "").trim();
  }
  function sayfaTablolari() {
    var sayfa = document.getElementById("sayfa-" + durum.sayfa);
    var gorunen = Array.prototype.filter.call(sayfa ? sayfa.querySelectorAll("table.tablo") : [], function (t) {
      return t.getClientRects().length > 0;  /* gizli bölüm ya da sekmedeki tablo kutu üretmez */
    });
    return gorunen.map(function (t) {
      var kart = t.closest(".kart, .kart-parca"), ust = kart ? kart.querySelector(".kart-ust") : null;
      var baslik = ust && ust.firstElementChild ? ust.firstElementChild.firstElementChild : null;
      var satirlar = Array.prototype.filter.call(t.tBodies[0].rows, function (r) {
        return r.style.display !== "none";
      }).map(function (r) {
        return Array.prototype.map.call(r.cells, function (c) {
          var metin = hucreMetni(c), d = c.getAttribute("data-deger");
          /* Yalnız sayı sütunu (td.sayi) sayı olarak gider; ikinci değeri olan hücre metin kalır
             (kaybolmasın). Diğer hücrelerde data-deger yalnız sıralama anahtarıdır (seviye, not, dosya
             yaşı ve tutar bandı numarası); etiket ve tarih metin kalır. */
          if (!c.classList.contains("sayi") || metin.indexOf(" · ") >= 0 || !/\d/.test(metin) ||
              TARIH_METNI.test(metin)) {
            return { metin: metin, sayi: null };
          }
          if (d !== null && d !== "" && !isNaN(Number(d))) {
            return { metin: metin, sayi: temizSayi(Number(d)), yuzde: metin.indexOf("%") >= 0 };
          }
          return metindenSayi(metin);
        });
      });
      return { ad: baslik ? hucreMetni(baslik) : SAYFA_ADI[durum.sayfa], satirlar: satirlar,
        basliklar: Array.prototype.map.call(t.tHead.rows[0].cells, hucreMetni) };
    }).filter(function (t) { return t.satirlar.length; });
  }
  /* Ham değeri taşımayan hücrede Türkçe biçimli düz sayı (1.234 · 87,50 · %12,5 · 22.711.455 TL) sayıya
     çevrilir; kısaltmalı tutar (Mn, bin), tarih ve kod metin kalır. */
  /* Kayan nokta artığı (342078,31999999995) dosyaya geçmez: altı ondalığa yuvarlanır. */
  function temizSayi(v) { return Math.round(v * 1e6) / 1e6; }
  var TARIH_METNI = /^\d{1,2}\.\d{1,2}\.\d{4}/;
  var TR_SAYI = /^(%?)(-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:,\d+)?)( TL)?$/;
  function metindenSayi(metin) {
    var m = TR_SAYI.exec(metin);
    if (!m || (m[1] && m[3])) { return { metin: metin, sayi: null }; }
    var deger = Number(m[2].replace(/\./g, "").replace(",", "."));
    return { metin: metin, sayi: m[1] ? deger / 100 : deger, yuzde: !!m[1] };
  }
  var SAYFA_ADI = { genel: "Genel Bakış", avukat: "Avukatlar", sure: "Süre Takibi", kurallar: "Puanlama Kuralları",
    veri: "Veri Durumu" };
  function dosyaAdi(uzanti) {
    var bolum = durum.sayfa === "avukat" ? durum.sekme : durum.bolum[durum.sayfa];
    return ["avukat_performans", durum.sayfa].concat(durum.sayfa === "avukat" && durum.kod ? [durum.kod] : [])
      .concat(bolum && bolum !== "ozet" ? [bolum] : [])
      .concat([new Date().toISOString().split("T")[0]]).join("_").replace(/[^\w.-]/g, "_") + "." + uzanti;
  }
  function indir(ad, veri, tur) {
    var adres = URL.createObjectURL(new Blob([veri], { type: tur })), a = document.createElement("a");
    a.href = adres;
    a.download = ad;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(adres); a.parentNode.removeChild(a); }, 1500);
  }
  function csvAlani(h, metin) {
    var deger = h && h.sayi !== null && !h.yuzde ? String(h.sayi).replace(".", ",") : metin;
    if (!(h && h.sayi !== null) && /^[=+\-@]/.test(deger)) { deger = "'" + deger; }  /* formül sayılmasın */
    return /[;"\n\r]/.test(deger) ? "\"" + deger.replace(/"/g, "\"\"") + "\"" : deger;
  }
  function csvOlustur(tablolar) {
    return "﻿" + tablolar.map(function (t) {
      return [csvAlani(null, t.ad), t.basliklar.map(function (b) { return csvAlani(null, b); }).join(";")]
        .concat(t.satirlar.map(function (r) {
          return r.map(function (h) { return csvAlani(h, h.metin); }).join(";");
        })).join("\r\n");
    }).join("\r\n\r\n") + "\r\n";
  }
  function xmlKac(m) {
    return String(m).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;")
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "");
  }
  function sutunHarfi(i) {
    var ad = "";
    for (var n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) { ad = String.fromCharCode(65 + (n - 1) % 26) + ad; }
    return ad;
  }
  function sayfaXml(t) {
    var genislik = t.basliklar.map(function (b) { return b.length; });
    var hucreXml = function (h, satir, sutun, stil) {
      var ref = sutunHarfi(sutun) + satir;
      genislik[sutun] = Math.max(genislik[sutun] || 0, h.metin.length);
      if (h.sayi !== null && isFinite(h.sayi)) {
        var bicim = h.yuzde ? 4 : Math.round(h.sayi) === h.sayi ? 2 : 3;
        return "<c r='" + ref + "' s='" + bicim + "'><v>" + h.sayi + "</v></c>";
      }
      return "<c r='" + ref + "' s='" + stil + "' t='inlineStr'><is><t xml:space='preserve'>" + xmlKac(h.metin) +
        "</t></is></c>";
    };
    var satirlar = [t.basliklar.map(function (b) { return { metin: b, sayi: null }; })].concat(t.satirlar)
      .map(function (r, i) {
        return "<row r='" + (i + 1) + "'>" + r.map(function (h, j) { return hucreXml(h, i + 1, j, i ? 0 : 1); })
          .join("") + "</row>";
      }).join("");
    var sutunlar = genislik.map(function (w, j) {
      return "<col min='" + (j + 1) + "' max='" + (j + 1) + "' width='" + Math.min(60, Math.max(8, w + 2)) +
        "' customWidth='" + 1 + "'/>";
    }).join("");
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?><worksheet xmlns='" + XLSX_AD.ana +
      "'><sheetViews><sheetView workbookViewId='0'><pane ySplit='1' topLeftCell='A2' activePane='bottomLeft'" +
      " state='frozen'/></sheetView></sheetViews><cols>" + sutunlar + "</cols><sheetData>" + satirlar +
      "</sheetData></worksheet>";
  }
  var SAYFA_ADI_EN_COK = 31;  /* Excel'in sayfa adı sınırı */
  var XLSX_AD = { ana: "http://schemas.openxmlformats.org/spreadsheetml/" + 2006 + "/main",
    iliski: "http://schemas.openxmlformats.org/officeDocument/" + 2006 + "/relationships",
    paket: "http://schemas.openxmlformats.org/package/" + 2006 + "/relationships",
    tur: "http://schemas.openxmlformats.org/package/" + 2006 + "/content-types",
    belge: "application/vnd.openxmlformats-officedocument.spreadsheetml." };
  function xlsxOlustur(tablolar) {
    var adlar = {}, xml = "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>";
    var sayfaAdlari = tablolar.map(function (t) {
      var kok = t.ad.replace(/[\[\]:*?\/\\]/g, " ").trim() || "Tablo", ad = kok.slice(0, SAYFA_ADI_EN_COK).trim();
      for (var n = 2; adlar[ad.toLocaleLowerCase("tr-TR")]; n++) {
        ad = kok.slice(0, SAYFA_ADI_EN_COK - String(n).length - 1).trim() + " " + n;
      }
      adlar[ad.toLocaleLowerCase("tr-TR")] = true;
      return ad;
    });
    var tur = xml + "<Types xmlns='" + XLSX_AD.tur + "'><Default Extension='rels' ContentType='" +
      "application/vnd.openxmlformats-package.relationships+xml'/><Default Extension='xml' ContentType='" +
      "application/xml'/><Override PartName='/xl/workbook.xml' ContentType='" + XLSX_AD.belge + "sheet.main+xml'/>" +
      "<Override PartName='/xl/styles.xml' ContentType='" + XLSX_AD.belge + "styles+xml'/>" +
      tablolar.map(function (t, i) {
        return "<Override PartName='/xl/worksheets/sheet" + (i + 1) + ".xml' ContentType='" + XLSX_AD.belge +
          "worksheet+xml'/>";
      }).join("") + "</Types>";
    var kokIliski = xml + "<Relationships xmlns='" + XLSX_AD.paket + "'><Relationship Id='rId" + 1 +
      "' Type='" + XLSX_AD.iliski + "/officeDocument' Target='xl/workbook.xml'/></Relationships>";
    var kitap = xml + "<workbook xmlns='" + XLSX_AD.ana + "' xmlns:r='" + XLSX_AD.iliski + "'><sheets>" +
      sayfaAdlari.map(function (ad, i) {
        return "<sheet name='" + xmlKac(ad) + "' sheetId='" + (i + 1) + "' r:id='rId" + (i + 1) + "'/>";
      }).join("") + "</sheets></workbook>";
    var kitapIliski = xml + "<Relationships xmlns='" + XLSX_AD.paket + "'>" + tablolar.map(function (t, i) {
      return "<Relationship Id='rId" + (i + 1) + "' Type='" + XLSX_AD.iliski + "/worksheet' Target='worksheets/sheet" +
        (i + 1) + ".xml'/>";
    }).join("") + "<Relationship Id='rId" + (tablolar.length + 1) + "' Type='" + XLSX_AD.iliski +
      "/styles' Target='styles.xml'/></Relationships>";
    var stiller = xml + "<styleSheet xmlns='" + XLSX_AD.ana + "'><numFmts count='1'><numFmt numFmtId='164' " +
      "formatCode='0.0%'/></numFmts><fonts count='2'><font><sz val='11'/><name val='Calibri'/></font><font><b/>" +
      "<sz val='11'/><name val='Calibri'/></font></fonts><fills count='2'><fill><patternFill patternType='none'/>" +
      "</fill><fill><patternFill patternType='gray125'/></fill></fills><borders count='1'><border><left/><right/>" +
      "<top/><bottom/><diagonal/></border></borders><cellStyleXfs count='1'><xf numFmtId='0' fontId='0' " +
      "fillId='0' borderId='0'/></cellStyleXfs><cellXfs count='5'><xf numFmtId='0' fontId='0' fillId='0' " +
      "borderId='0' xfId='0'/><xf numFmtId='0' fontId='1' fillId='0' borderId='0' xfId='0' " +
      "applyFont='1'/><xf numFmtId='3' fontId='0' fillId='0' borderId='0' xfId='0' applyNumberFormat='1'/>" +
      "<xf numFmtId='4' fontId='0' fillId='0' borderId='0' xfId='0' applyNumberFormat='1'/><xf " +
      "numFmtId='164' fontId='0' fillId='0' borderId='0' xfId='0' applyNumberFormat='1'/></cellXfs>" +
      "<cellStyles count='1'><cellStyle name='Normal' xfId='0' builtinId='0'/></cellStyles></styleSheet>";
    var dosyalar = [["[Content_Types].xml", tur], ["_rels/.rels", kokIliski], ["xl/workbook.xml", kitap],
      ["xl/_rels/workbook.xml.rels", kitapIliski], ["xl/styles.xml", stiller]].concat(tablolar.map(function (t, i) {
        return ["xl/worksheets/sheet" + (i + 1) + ".xml", sayfaXml(t)];
      }));
    return zipOlustur(dosyalar);
  }
  var CRC_TABLO = null;
  function crc32(bayt) {
    if (!CRC_TABLO) {
      CRC_TABLO = [];
      for (var n = 0; n < 256; n++) {
        var c = n;
        for (var k = 0; k < 8; k++) { c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; }
        CRC_TABLO[n] = c >>> 0;
      }
    }
    var crc = 0xFFFFFFFF;
    for (var i = 0; i < bayt.length; i++) { crc = CRC_TABLO[(crc ^ bayt[i]) & 0xFF] ^ (crc >>> 8); }
    return (crc ^ 0xFFFFFFFF) >>> 0;
  }
  /* Sıkıştırmasız ZIP (store): yerel başlıklar, merkez dizin, kapanış kaydı. */
  function zipOlustur(dosyalar) {
    var kodla = new TextEncoder(), parcalar = [], merkez = [], konum = 0, merkezBoy = 0;
    function u16(v) { return [v & 0xFF, (v >>> 8) & 0xFF]; }
    function u32(v) { return [v & 0xFF, (v >>> 8) & 0xFF, (v >>> 16) & 0xFF, (v >>> 24) & 0xFF]; }
    var TARIH = 0x21;  /* 1 Ocak 1980 (DOS tarihi) */
    dosyalar.forEach(function (d) {
      var ad = kodla.encode(d[0]), veri = kodla.encode(d[1]), crc = crc32(veri);
      var ortak = [].concat(u16(0x14), u16(0x0800), u16(0), u16(0), u16(TARIH), u32(crc), u32(veri.length),
        u32(veri.length), u16(ad.length), u16(0));
      var yerel = new Uint8Array(u32(0x04034b50).concat(ortak));
      parcalar.push(yerel, ad, veri);
      var giris = new Uint8Array(u32(0x02014b50).concat(u16(0x14), ortak, u16(0), u16(0), u16(0), u32(0), u32(konum)));
      merkez.push(giris, ad);
      merkezBoy += giris.length + ad.length;
      konum += yerel.length + ad.length + veri.length;
    });
    var son = new Uint8Array(u32(0x06054b50).concat(u16(0), u16(0), u16(dosyalar.length), u16(dosyalar.length),
      u32(merkezBoy), u32(konum), u16(0)));
    return new Blob(parcalar.concat(merkez, [son]));
  }
  function disaAktar(bicim) {
    var tablolar = sayfaTablolari();
    if (!tablolar.length) { window.alert("Bu bölümde indirilecek tablo yok."); return; }
    if (bicim === "csv") {
      indir(dosyaAdi("csv"), csvOlustur(tablolar), "text/csv");
    } else {
      indir(dosyaAdi("xlsx"), xlsxOlustur(tablolar), XLSX_AD.belge.replace(/\.$/, ".sheet"));
    }
  }

  function baslat() {
    document.getElementById("cekmece-arka").onclick = cekmeceKapat;
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { cekmeceKapat(); return; }
      cekmeceOdak(e);
      var th = e.target.closest ? e.target.closest("th.siralanir") : null;
      if (th && e.target === th && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); tabloSirala(th); }
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-disa-aktar]"), function (el) {
      el.addEventListener("click", function () { disaAktar(el.getAttribute("data-disa-aktar")); });
    });
    /* Menü bağlantıdır (href); Süre Takibi süzgeci sıfırlar, zil kırmızı aktif gecikmeleri açar. */
    Array.prototype.forEach.call(document.querySelectorAll(".menu-oge, .zil"), function (el) {
      el.addEventListener("click", function (e) {
        var ad = el.getAttribute("data-sayfa");
        e.preventDefault();
        if (ad === "sure") {
          var zil = el.classList.contains("zil");
          durum.filtre = { kriter: "", seviye: zil ? "KIRMIZI" : "", avukat: "" };
          durum.bolum.sure = zil ? "donemler" : "ozet";
        }
        if (ad === "genel") { durum.bolum.genel = "ozet"; }
        sayfaAc(ad);
      });
    });
    ipucuBagla();
    document.addEventListener("click", function (e) {
      var th = e.target.closest ? e.target.closest("th.siralanir") : null;
      if (th && !e.target.closest(".bilgi")) { tabloSirala(th); }
    });
    /* Sekmeler: tıklama; sol ve sağ ok, Home ve End tuşlarıyla geçiş (WAI-ARIA sekme düzeni).
       Avukat kartı sekmesi adresi yerinde değiştirir (replaceState; geri tuşu önceki sayfaya döner).
       Sayfa bölümü tıklamada geçmişe girer (pushState: geri tuşu önceki bölüme döner); ok
       tuşlarıyla gezinti geçmişe kayıt eklemez (replaceState). */
    sekmeleriBagla(".sekme", "data-sekme", function (sekme, odakla) {
      sekmeSec(sekme, odakla);
      uygulananAdres = adresKur("avukat");
      history.replaceState(null, "", uygulananAdres);
    });
    sekmeleriBagla(".bolum-sekme", "data-bolum", function (bolum, odakla) {
      var ad = durum.sayfa;
      bolumSec(ad, bolum, odakla);
      var hedef = adresKur(ad);
      if (location.hash !== hedef) {
        uygulananAdres = hedef;
        history[odakla ? "replaceState" : "pushState"](null, "", hedef);
      }
    });
    window.addEventListener("hashchange", adresUygula);
    window.addEventListener("popstate", adresUygula);
    durum.sayfa = null;
    adresUygula();
  }

  window.avukatPerformans = { CIZICILER: CIZICILER, sayfaAc: sayfaAc };
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", baslat); } else { baslat(); }
})();
