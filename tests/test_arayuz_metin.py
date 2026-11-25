"""Arayüzün istemci denetimleri: JS ve CSS metninin denetimi.

Projede JS test koşucusu yok; davranışlar tarayıcıda denendi, burada kuralı taşıyan kod
parçalarının varlığı ve eskimiş metinlerin yokluğu sabitlenir. Her test düzeltme öncesi kodda
düşer.
"""
import json
import os
import re

from arayuz.sozlesme import BILESENLER
from avukat_perf import sema
from avukat_perf.portfoy import ATANAMAYAN
from test_arayuz import _cizici_bloklari, _oku
from test_arayuz_durum import _kod
from yardimci import KOK, params_yukle

GECELIK = ("genel.kpi", "genel.sutun_durumu", "genel.avukat_tablosu", "avukat.liste",
           "avukat.baslik", "avukat.sutunlar", "kurallar.notlar")


def _js():
    return _oku("uygulama.js")


def _bloklar():
    return _cizici_bloklari(_js())[0]


def _islev(js, ad):
    """`function ad(...) { ... }` gövdesi (ilk dengeli kapanışa kadar)."""
    bas = js.index("function " + ad + "(")
    derinlik, i = 0, js.index("{", bas)
    while True:
        derinlik += {"{": 1, "}": -1}.get(js[i], 0)
        if derinlik == 0:
            return js[bas:i + 1]
        i += 1


def test_gecelik_puan_yayimlandi_diye_gosterilmez():
    """4: her gece değişen birleşik puan, değişmez dönem yayınıyla aynı adı taşıyordu."""
    js, bloklar = _js(), _bloklar()
    durum = re.search(r"var DURUM = \{(.*?)\};", js, re.S).group(1)
    assert 'YAYIMLANDI: "Hesaplandı"' in durum
    assert 'var DONEM_DURUM = { YAYIMLANDI: "Yayımlandı" };' in js
    for kimlik in GECELIK:
        assert "Yayımlan" not in bloklar[kimlik] and "yayımlan" not in bloklar[kimlik], kimlik
    assert "DONEM_DURUM[" in bloklar["avukat.gecmis"]


def test_eskimis_metinler_yok():
    """6, 7, istemci 2 ve 13: kutu grafiği 'yayın tabanı', ipucu yalnız parametre, mutabakat
    vaadi, eski gölge adı ve yanlış renk yorumları."""
    js, bloklar = _js(), _bloklar()
    kutu = bloklar["genel.brans_oran"]
    assert "yayın taban" not in kutu and "Tabana ulaşan" not in kutu
    assert "yeterli veri eşiğine" in kutu
    assert "tahsilat raporuyla tutması" not in bloklar["genel.kpi"]
    assert "Parametreler son başarılı" not in js and '"Parametreler ya da " +' in js
    assert "CANLI_ONCESI" not in js and "canlı öncesi" not in js.lower()
    assert "mavi → gri → kırmızı" not in js and "sonuç tablosundaki nottan" not in js
    from arayuz.sozlesme_dislanan import GOSTERILMEYEN
    assert "üst şeritte" not in GOSTERILMEYEN["sonuc_puan_guncel.donem"]


def test_brans_ve_alt_baslik_kodu_jste_yazilmaz():
    """5, istemci 1: branş ve alt başlık adları ile renkleri koda bağlı JS sözlüklerindeydi."""
    js, params = _kod(_js()), params_yukle()
    kodlar = set(params["kalite"]["bilinen_branslar"]) | {
        kod for liste in params["kalite_davranis"]["alt_basliklar"].values() for kod in liste}
    kodlar |= set(params["kalite_davranis"]["mevcut_alanlar"])
    gorunen = re.findall(r"\b[A-Za-z_]+\b", js)
    assert not kodlar & set(gorunen), sorted(kodlar & set(gorunen))
    assert "BRANS_RENK" not in _js() and "var(--brans-diger)" not in _js()
    assert "BRANS_SIRA[kod] = al(r, \"sira\")" in _js()
    assert '"var(--brans-" + sira + ")"' in _islev(_js(), "bransRengi")


def test_oran_rengi_ve_yazisi_ayni_kesimle():
    """9, istemci 14: %99,6 kırmızı '%100' yazılıyordu; eşik elle yazılmış 1'di."""
    blok = _bloklar()["genel.avukat_tablosu"]
    assert "oran < BEKLENEN_ORAN" in blok and "yuzde(oran, 0, true)" in blok
    assert "oran < 1" not in blok


def test_atanamayan_kodu_kitaplikla_ayni():
    """İstemci 14: avukata yazılamayan satırın kodu JS'te kitaplıktakiyle aynı olmalı."""
    assert _js().count('"{}"'.format(ATANAMAYAN)) == 2


def test_eksik_bilesen_iletisi_sayfaya_gore():
    """12: Veri Durumu kendi eksik bileşeni için 'nedeni Veri Durumu sayfasında' diyordu."""
    govde = _islev(_js(), "eksikBilesenMetni")
    assert 'durum.sayfa === "veri"' in govde and "Henüz bu denetim için kayıt yok." in govde
    assert "eksikBilesenMetni()" in _islev(_js(), "ciz")


def test_son_olaylar_istemcide_kesilmez():
    """18, istemci 7: sınır arka uçta SON_OLAY, JS'te slice(0, 30) olarak iki yerdeydi."""
    js = _kod(_js())
    assert not re.findall(r"\bslice\(\s*\d+\s*,\s*\d+", js)
    blok = _bloklar()["sure.olaylar"]
    assert 'al(r, "son_sira")' in blok and ".slice(" not in blok


def test_kismi_son_ay_gorunur_ozette():
    """İstemci 4: kesitte bitmeyen son ay yalnız bilgi simgesinde kalıyordu."""
    bloklar = _bloklar()
    for kimlik in ("genel.aylik", "avukat.aylik"):
        assert re.search(r"kartUstOzet\([^;]*kismiNotu\(veri\)\)", bloklar[kimlik], re.S), kimlik
    assert "kartUstOzet(" in bloklar["genel.aylik_avukat"] and \
        '"Son ay kesite kadar"' in bloklar["genel.aylik_avukat"]


def test_tutar_ekseni_etiketi_adimdan():
    """İstemci 5: 2,5'lik adımda 1.250.000 çizgisi '1,3 Mn' yazılıyordu."""
    js = _js()
    assert "kisa(deger, olcek.adim)" in js and "function kisa(v, adim)" in js
    assert "ince ? 2 : 1" in _islev(js, "kisa")


def test_yuvarlaninca_sifir_olan_deger_isaretsiz():
    """İstemci 6: kayan nokta artığı '-0 TL', '-%0,0' görünüyordu."""
    js = _js()
    assert "yuvarlanmis(v, d).toLocaleString" in _islev(js, "sayi")
    assert "/[1-9]/.test(mutlak)" in _islev(js, "yuzde")
    yillik = _bloklar()["genel.yillik"]
    assert "eksiMi(d, 1)" in yillik and "d < 0" not in yillik


def test_ay_basligi_kacislanir():
    """İstemci 8: aylık avukat tablosunun sütun başlığında yıl kaçışsız giriyordu."""
    assert "kac(v)" not in _islev(_js(), "ayEtiketi")
    assert '"#" + kac(e.etiket) + (e.alt ? " " + kac(e.alt) : "")' in _bloklar()[
        "genel.aylik_avukat"]


def test_bolum_sekmesi_okla_gecmise_yazmaz_gecersiz_adres_duzelir():
    """İstemci 9: okla her bölüm geçişi geçmişe kayıt ekliyordu; #genel/xyz düzeltilmiyordu."""
    js = _js()
    assert 'history[odakla ? "replaceState" : "pushState"](null, "", hedef);' in js
    uygula = _islev(js, "adresUygula")
    assert "history.replaceState" in uygula and "Geçersiz bölüm" in uygula


def test_odaklanan_rozet_ve_acilir_dugme_erisilebilir():
    """İstemci 10: odaklanan rozetlerin açıklaması ekran okuyucuya ulaşmıyordu."""
    js = _js()
    literaller = re.findall(r'"(?:[^"\\\n]|\\.)*"', js)
    assert not [lit for lit in literaller if "tabindex='0'" in lit and "data-ipucu" in lit
                and "aria-label" not in lit and "role='img'" not in lit]
    assert "role='img' aria-label=" in _islev(js, "ipucuRozeti")
    baslik = _bloklar()["avukat.baslik"]
    assert "aria-controls='neden-paneli'" in baslik and 'setAttribute("aria-expanded"' in baslik
    assert "aria-hidden='true'" in _islev(js, "pasta")
    assert "role='group' aria-label='Not süzgeci'" in _bloklar()["genel.avukat_tablosu"]


def test_kullanilmayan_css_sinifi_yok():
    """İstemci 12: JS ve HTML'de karşılığı olmayan CSS sınıfları elle yapıştırılan dosyada
    bakımcıyı yanıltıyordu (sütun-* JS'te ad + kod olarak kurulur)."""
    css = re.sub(r"/\*.*?\*/", " ", _oku("stil.css"), flags=re.S)
    kok = re.search(r":root\s*\{(.*?)\}", css, re.S)
    kurallar = css[:kok.start()] + css[kok.end():]
    siniflar = set()
    for secici in re.findall(r"([^{}]+)\{", kurallar):
        if not secici.strip().startswith("@"):
            siniflar |= set(re.findall(r"\.([a-zA-Z_][\w-]*)", secici))
    kelimeler = set(re.findall(r"[\w-]+", _js() + _oku("index.html")))
    kullanilmayan = sorted(ad for ad in siniflar if ad not in kelimeler
                           and not ad.startswith("sutun-"))
    assert not kullanilmayan, kullanilmayan
    assert "altSinif" not in _js()


def test_golge_kriter_bazinda_cizilir():
    """e1: yedek yol gecesinde Kriter 2 canlıyken rozetler ve notlar 'gölge' diyordu."""
    js = _js()
    assert "durum.golgeMod" not in js
    assert "!!durum.golge[kriter]" in _islev(js, "golgeSeviye")
    cagrilar = re.findall(r"golgeSeviye\(([^()]*)\)", _kod(js))
    assert cagrilar and all("," in c for c in cagrilar), cagrilar
    assert not re.findall(r"seviyeRozeti\([^(),]*\)", _kod(js))
    assert 'al(d, "golge_ilk_islem")' in _bloklar()["ortak.durum"]


def test_tahsilat_hareketi_beklenirken_bos_durum():
    """e2 (D1): tahsilat hareketi bağlanmadan tahsilat bileşenleri 'kaynak bekleniyor' der."""
    js = _js()
    kaynak = re.search(r'var TAHSILAT_KAYNAGI = "([a-z_]+)";', js).group(1)
    assert sema.KAYNAKLAR[kaynak]["istege_bagli"]
    liste = re.search(r"var TAHSILAT_BILESENLERI = \[(.*?)\];", js, re.S).group(1)
    bilesenler = re.findall(r'"([a-z_.]+)"', liste)
    assert set(bilesenler) <= set(BILESENLER) and "avukat.tahsilat" in bilesenler
    assert {k for k in BILESENLER if "tahsilat" in json.dumps(BILESENLER[k]["kaynak"]) and
            k.split(".")[0] in ("genel", "avukat") and k not in (
                "genel.kpi", "genel.avukat_tablosu", "genel.dagilim", "avukat.sutunlar",
                "avukat.konum", "avukat.gecmis")} <= set(bilesenler)
    assert "tahsilatBekleniyor()" in _islev(js, "ciz")
    assert 'tahsilatBekleniyor() ? sistemAdi("tahsilat_raporu")' in _bloklar()["genel.kpi"]


def test_tahsilat_karti_tablo_basligi_kisa():
    """İstemci 3: 'Bileşen · gerçekleşen / beklenen' başlığı tabloyu 1280 px'te kırpıyordu."""
    assert "Bileşen · gerçekleşen" not in _bloklar()["avukat.tahsilat"]


def test_yeterli_veri_isareti_sure_sutununda_da():
    """e4 (D5): Genel Bakış sıralama tablosunda süre puanının yanında da kırmızı uyarı."""
    assert 'azVeriSatiri(al(r, "sure_yeterli"), al(r, "sure"))' in _bloklar()[
        "genel.avukat_tablosu"]


def test_parametre_hatasi_ve_okuma_kesintisi_seritte():
    """1, 2, 14: şerit okuma kesintisini, geçersiz parametreyi ve kalan dönem yayınını söyler."""
    blok = _bloklar()["ortak.durum"]
    for parca in ('"Veri okunamadı"', '"Parametre dosyası geçersiz"', "son_donem_karari",
                  'donem === "KALDI"'):
        assert parca in blok, parca
    assert "durum.okunamayan.length" in _islev(_js(), "sayfaBos")
    with open(os.path.join(KOK, "dataiku", "webapp", "index.html"), encoding="utf-8") as dosya:
        assert 'data-bilesen="kurallar.hatalar" hidden' in dosya.read()


def test_avukat_aramasi_bos_baslar_ve_secimde_korunur():
    """Arama kutusunun değeri kac()'tan geçmez (boş değer "—" olarak yazılıyordu); değer çizimden
    sonra durumdan atanır, avukat seçilince liste yeniden çizilse de arama korunur."""
    blok = _bloklar()["avukat.liste"]
    assert "value='" not in blok and "kac(durum.avukatArama" not in blok
    assert 'giris.value = durum.avukatArama || ""' in blok
