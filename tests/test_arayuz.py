"""Ekran–veri sözleşmesi testleri.

Arka uçta hesaplanıp ekranda gösterilmeyen sütun, ekranda olup arka uçta olmayan alan ve
arayüze elle yazılmış rakam bu testlerle yakalanır. Sonuç tabloları küçük bir sentetik
prova çalışmasından okunur (gecelik akış ve bir dönem yayını).
"""
import json
import os
import re
import shutil
import tempfile

from arayuz import sunum
from avukat_perf import portfoy, sema
from arayuz.sozlesme import BILESENLER
from arayuz.sozlesme_dislanan import GOSTERILMEYEN, IC_TABLOLAR
from arayuz.sunum_kural import _metin
from hat import akis, donem_akisi, veri_kumeleri
from yardimci import KOK, prova_ortami

WEBAPP = os.path.join(KOK, "dataiku", "webapp")
SIMDI = "2026-11-19 02:00:00"
_PROVA = {}


def _cikti():
    """Prova çalışmasının yazdığı bütün tablolar ve parametreler (bir kez çalışır)."""
    if not _PROVA:
        ortam, ayarlar, params, kok = prova_ortami()
        try:
            assert akis.gecelik(ortam, ayarlar, params, simdi=SIMDI)["karar"] == "GECTI"
            donem_akisi.calistir(ortam, params, "2026-10", simdi=SIMDI)
            adlar = sorted({ad.split(".")[0] for ad in os.listdir(
                os.path.join(ortam.kok, "tablolar"))})
            _PROVA["tablolar"] = {ad: ortam.tablo_oku(ad) for ad in adlar}
            _PROVA["params"] = params
        finally:
            shutil.rmtree(kok)
    return _PROVA["tablolar"], _PROVA["params"]


def _oku(ad):
    with open(os.path.join(WEBAPP, ad), encoding="utf-8") as dosya:
        return dosya.read()


def _kullanilan():
    kullanilan = {}
    for bilesen in BILESENLER.values():
        for tablo, sutunlar in bilesen["kaynak"].items():
            kullanilan.setdefault(tablo, set()).update(sutunlar)
    return kullanilan


def test_her_sonuc_sutunu_ekranda_ya_da_gerekceli_dislanmis():
    tablolar, _ = _cikti()
    kullanilan, dislanan = _kullanilan(), {}
    for anahtar, gerekce in GOSTERILMEYEN.items():
        assert gerekce.strip(), anahtar
        tablo, sutun = anahtar.split(".")
        dislanan.setdefault(tablo, set()).add(sutun)
    for ad, tablo in tablolar.items():
        if ad in IC_TABLOLAR:
            continue
        assert ad in kullanilan, "ekranda kullanılmayan tablo: " + ad
        gercek = set(tablo.columns)
        gosterilmeyen = gercek - kullanilan[ad] - dislanan.get(ad, set())
        assert not gosterilmeyen, (ad, "gerekçesiz gösterilmeyen", sorted(gosterilmeyen))
        assert not kullanilan[ad] - gercek, (ad, "arka uçta yok", sorted(kullanilan[ad] - gercek))
        assert not dislanan.get(ad, set()) - gercek, (ad, "eskimiş dışlama")
        assert not dislanan.get(ad, set()) & kullanilan[ad], (ad, "hem kullanılıyor hem dışlanmış")
    for ad in set(kullanilan) | set(IC_TABLOLAR):
        assert ad in tablolar, "hat bu tabloyu yazmıyor: " + ad
    assert all(gerekce.strip() for gerekce in IC_TABLOLAR.values())


def test_dataiku_veri_kumesi_listesi_hatla_ayni():
    tablolar, _ = _cikti()
    assert set(tablolar) == set(veri_kumeleri.CIKTI)
    assert len(veri_kumeleri.CIKTI) == len(set(veri_kumeleri.CIKTI))
    # Yöntem sistem düzeyinde verilir, kaynak düzeyinde ezilebilir.
    with open(os.path.join(KOK, "dataiku", "degiskenler", "kaynaklar.json"),
              encoding="utf-8") as dosya:
        ayarlar = json.load(dosya)
    ayarlar["sistemler"]["cekirdek"]["yontem"] = "dataiku"
    ayarlar["kaynaklar"]["atama_log"]["yontem"] = "bekliyor"
    beklenen = sorted(ayarlar["kaynaklar"][ad]["dataiku"]["veri_kumesi"] for ad, tanim in
                      sema.KAYNAKLAR.items() if tanim["sistem"] == "cekirdek" and ad != "atama_log")
    assert len(beklenen) >= 2
    assert veri_kumeleri.kaynak_veri_kumeleri(ayarlar) == beklenen


def test_html_bilesenleri_sozlesmeyle_ayni():
    html = _oku("index.html")
    bilesenler = re.findall(r'data-bilesen="([^"]+)"', html)
    assert len(bilesenler) == len(set(bilesenler))
    assert set(bilesenler) == set(BILESENLER)
    for sayfa in {b["sayfa"] for b in BILESENLER.values()} - {"ortak"}:
        assert 'id="sayfa-{}"'.format(sayfa) in html, sayfa
        assert 'data-sayfa="{}"'.format(sayfa) in html, sayfa


def _cizici_bloklari(js):
    baslangic = [(m.start(), m.group(1)) for m in re.finditer(
        r'CIZICILER\["([^"]+)"\]\s*=\s*function', js)]
    bloklar = {}
    for sira, (yer, kimlik) in enumerate(baslangic):
        son = baslangic[sira + 1][0] if sira + 1 < len(baslangic) else len(js)
        bolum = js.find("/* ----------", yer)
        bloklar[kimlik] = js[yer:min(son, bolum) if bolum > 0 else son]
    return bloklar, baslangic[0][0]


def test_cizici_alanlari_sozlesmeyle_birebir():
    js = _oku("uygulama.js")
    bloklar, ilk = _cizici_bloklari(js)
    assert set(bloklar) == set(BILESENLER)
    for kimlik, blok in bloklar.items():
        okunan = set(re.findall(r'\bal\([^,()]+,\s*"([a-z0-9_]+)"\)', blok))
        alanlar = set(BILESENLER[kimlik]["alanlar"])
        assert okunan == alanlar, (kimlik, "çizilmeyen", sorted(alanlar - okunan),
                                   "sözleşme dışı", sorted(okunan - alanlar))
    dinamik = re.findall(r'\bal\([^,()]+,\s*[^"\s][^)]*\)', js)
    assert dinamik == ["al(satir, alan)"], dinamik
    once = re.sub(r"/\*.*?\*/", " ", js[:ilk], flags=re.S)
    assert re.findall(r"\bal\(", once) == ["al("], "çizici dışında veri okunuyor"


def _sayfalar(tablolar, params):
    kod = tablolar["sonuc_birlesik"]["avukat_kodu"].iloc[0]
    return [("genel", None), ("avukat", {"kod": kod}), ("avukat", None), ("sure", None),
            ("sure", {"kriter": "K2", "seviye": "TURUNCU"}), ("kurallar", None), ("veri", None)]


def test_sayfa_verisi_tam_alanlarla_ve_json_uyumlu():
    tablolar, params = _cikti()
    for ad, secim in _sayfalar(tablolar, params):
        veri = sunum.sayfa(ad, tablolar, params, secim)
        json.dumps(veri, allow_nan=False)
        beklenen = {k for k, b in BILESENLER.items() if b["sayfa"] in (ad, "ortak")}
        assert set(veri["bilesenler"]) == beklenen, (ad, sorted(
            beklenen ^ set(veri["bilesenler"])))
        for kimlik, kayitlar in veri["bilesenler"].items():
            alanlar = BILESENLER[kimlik]["alanlar"]
            for kayit in kayitlar:
                assert list(kayit) == alanlar, kimlik
    secili = sunum.sayfa("sure", tablolar, params, {"kriter": "K2", "seviye": "TURUNCU"})
    assert {(k["kriter"], k["seviye"]) for k in secili["bilesenler"]["sure.liste"]} <= {
        ("K2", "TURUNCU")}


def test_genel_gostergeler_ve_liste_sirasi_tablolarla_tutar():
    tablolar, params = _cikti()
    kpi = sunum.sayfa("genel", tablolar, params)["bilesenler"]["genel.kpi"][0]
    portfoy, grup = tablolar["sonuc_portfoy"], tablolar["sonuc_tahsilat_grup"]
    ozet, birlesik = tablolar["sonuc_sure_ozet"], tablolar["sonuc_birlesik"]
    assert kpi["aktif_dosya"] == portfoy["aktif_dosya"].sum()
    assert abs(kpi["tahsilat_orani"] - grup["atfedilen"].sum() / grup["rucu_toplami"].sum()) < 1e-12
    assert kpi["atanamayan_tahsilat"] == grup["atanamayan"].sum()
    assert kpi["acik_kirmizi"] == ozet["acik_kirmizi"].sum()
    assert kpi["yayimlanan"] == (birlesik["durum"] == "YAYIMLANDI").sum()
    assert kpi["avukat_sayisi"] == len(birlesik)
    liste = sunum.sayfa("sure", tablolar, params)["bilesenler"]["sure.liste"]
    agirlik = [{"KIRMIZI": 0, "TURUNCU": 1, "SARI": 2, "IZLENIYOR": 3}.get(k["seviye"], 9)
               for k in liste]
    assert liste and agirlik == sorted(agirlik)


def test_son_gecede_uretilmeyen_sonuc_tablosu_gosterilmez():
    tablolar, params = _cikti()
    kayit = tablolar["calisma_kaydi"].copy()
    gece = kayit[(kayit["kaynak"] == "*") & (kayit["tur"] == "GECELIK")].index[-1]
    uretilen = [ad for ad in str(kayit.loc[gece, "uretilen"]).split(",") if ad.split("=")[0]
                not in ("sonuc_k1", "sonuc_k2")]
    kayit.loc[gece, "uretilen"] = ",".join(uretilen)
    bayat = dict(tablolar, calisma_kaydi=kayit)
    assert "sure.liste" not in sunum.sayfa("sure", bayat, params)["bilesenler"]
    assert "sure.liste" in sunum.sayfa("sure", tablolar, params)["bilesenler"]
    # Başarılı gece bilgisi yoksa (ör. ilk gece yarıda kaldı) hiçbir sonuç gösterilmez.
    eski = dict(tablolar, calisma_kaydi=kayit.drop(columns="uretilen"))
    assert "sure.liste" not in sunum.sayfa("sure", eski, params)["bilesenler"]


def test_golge_modda_sure_sutunu_bekliyor_sayilir():
    tablolar, params = _cikti()
    puan = tablolar["sonuc_puan_guncel"].copy()
    sure = puan.index[puan["sutun"] == "sure"]
    puan.loc[sure, "durum"], puan.loc[sure, "puan"] = "GOLGE_MOD", float("nan")
    puan.loc[sure[0], "durum"] = "VERI_YOK"
    satir = [k for k in sunum.sayfa("genel", dict(tablolar, sonuc_puan_guncel=puan), params)[
        "bilesenler"]["genel.sutun_durumu"] if k["sutun"] == "sure"][0]
    assert satir["bekleme_nedeni"] == "GOLGE_MOD" and satir["gecerli"] == 0
    assert satir["gecersiz"] == 1


def test_acilis_ve_kurulum_gunu_senaryolari():
    from araclar import yerel_calistir
    for senaryo in ("acilis", "bos"):
        klasor = tempfile.mkdtemp()
        try:
            ortam = yerel_calistir.calistir(klasor, yazdir=False, senaryo=senaryo)
            params = yerel_calistir.senaryo_ayarlari(senaryo)[1]
            tablolar = {ad: ortam.tablo_oku(ad) for ad in sunum.TABLOLAR}
            sayfalar = {ad: sunum.sayfa(ad, tablolar, params) for ad in
                        ("genel", "avukat", "sure", "kurallar", "veri")}
            json.dumps(sayfalar, allow_nan=False)
        finally:
            shutil.rmtree(klasor)
        kpi = sayfalar["genel"]["bilesenler"]["genel.kpi"][0]
        durum = {k["sutun"]: k["bekleme_nedeni"] for k in
                 sayfalar["genel"]["bilesenler"]["genel.sutun_durumu"]}
        if senaryo == "acilis":
            assert kpi["aktif_dosya"] > 0 and kpi["yayimlanan"] == 0
            # Ölçek teyit beklerken de mevcut alanlar bilgi amaçlı gösterilir.
            assert not tablolar["sonuc_mevcut_degerlendirme"].empty
            assert sayfalar["genel"]["bilesenler"]["genel.yillik"]
            # Kriter 2 (dava takip sistemi) yok: süre puanı iki kriter olmadan üretilmez.
            assert durum == {"tahsilat": None, "sure": "KAYNAK_BEKLENIYOR",
                             "kalite": "TEYIT_BEKLIYOR", "davranis": "TEYIT_BEKLIYOR"}
            assert sayfalar["genel"]["bilesenler"]["ortak.durum"][0]["golge_mod"] is True
        else:
            assert kpi["aktif_dosya"] is None and durum == {}
            kaynaklar = sayfalar["veri"]["bilesenler"]["veri.kaynaklar"]
            assert {k["durum"] for k in kaynaklar} == {"KAYNAK_BEKLENIYOR"}


def test_kaynak_yokken_sayfalar_bos_ve_hatasiz():
    _, params = _cikti()
    tablolar = {ad: None for ad in sunum.TABLOLAR}
    for ad in ("genel", "avukat", "sure", "kurallar", "veri"):
        veri = sunum.sayfa(ad, tablolar, params)
        json.dumps(veri, allow_nan=False)
        assert veri["bilesenler"]["ortak.durum"][0]["kesit"] is None
    kpi = sunum.sayfa("genel", tablolar, params)["bilesenler"]["genel.kpi"][0]
    assert kpi["aktif_dosya"] is None and kpi["sure_verisi"] is False
    assert len(sunum.sayfa("kurallar", tablolar, params)["bilesenler"]) == 7


# Ekranda (ipucu) ya da ekran okuyucuda görünen öznitelikler: değerleri metin gibi denetlenir.
GORUNUR_OZNITELIK = (r"\b(?:title|aria-label|placeholder|alt|data-ipucu)="
                     r"(?:'([^']*)|\\?\"([^\"\\]*))")


def _gorunur_oznitelikler(metin):
    return " ".join(tek or cift for tek, cift in re.findall(GORUNUR_OZNITELIK, metin))


def _veri_disi_metin(literal):
    """JS metninden etiket, stil ve SVG geometrisini ayıklar; kalan metin ekranda görünür.
    Görünen öznitelik değerleri (title, aria-label, placeholder, alt, data-ipucu) metne katılır."""
    gorunur = _gorunur_oznitelikler(literal[1:-1])
    metin = re.sub(r"<[^<>]*>", " ", literal[1:-1])
    metin = re.sub(r"[\w-]+='[^']*'?|[\w-]+=\"[^\"]*\"", " ", metin) + " " + gorunur
    metin = re.sub(r"<[a-z][^>]*$|#[0-9A-Fa-f]{3,6}\b|\b\d+px\b", " ", metin)
    return re.sub(r"Kriter [12]\b|\bK[12]\b", " ", metin)


def test_sekmeler_ve_ayrinti_penceresi_erisilebilir():
    """Sekmeler ilk açılışta seçili durumunu ve paneliyle bağını taşır; pencerenin adı vardır."""
    html, js = _oku("index.html"), _oku("uygulama.js")
    sekmeler = re.findall(r'<button class="sekme[^>]*>', html)
    assert len(sekmeler) == 5
    assert [s.count('aria-selected="true"') for s in sekmeler] == [1, 0, 0, 0, 0]
    for sekme in sekmeler:
        panel = re.search(r'aria-controls="([a-z-]+)"', sekme).group(1)
        kimlik = re.search(r'id="([a-z-]+)"', sekme).group(1)
        kalip = r'role="tabpanel" id="{}"\s+aria-labelledby="{}"'.format(panel, kimlik)
        assert re.search(kalip, html), sekme
    cekmece = re.search(r'<aside class="cekmece"[^>]*>', html).group(0)
    assert 'role="dialog"' in cekmece and 'aria-labelledby="cekmece-baslik"' in cekmece
    assert js.count("id='cekmece-baslik'") == 1
    # Sıralanan başlıklar klavyeyle de çalışır; satırlar tiklamaBagla ile odaklanabilir olur:
    # tabloda tek sekme durağı (ilk satır), satırlar arasında ok tuşlarıyla gezilir.
    assert "tabindex='0' aria-sort='none'" in js
    # Gezinme grubu: komşu tuş anındaki görünür sıradan bulunur; süzme ve sıralama durağı taşır.
    assert "function gorunenler(el)" in js and "function durakYenile(kap)" in js
    assert js.count("durakYenile(") >= 4  # tanım, bağlama, sıralama, not süzgeci


def test_arayuzde_elle_yazilmis_rakam_yok():
    html = re.sub(r"<[^>]*>", " ", _oku("index.html"))
    assert not re.findall(r"\d", html), "index.html metninde rakam"
    assert not re.findall(r"\d", _gorunur_oznitelikler(_oku("index.html"))), "index.html özniteliği"
    # Öznitelikteki rakam da görünür metindir (title ve aria-label atlanıyordu).
    assert re.search(r"\d", _veri_disi_metin("\"<span title='Son 12 ay'>\""))
    assert re.search(r"\d", _veri_disi_metin("\"<i aria-label=\"Bant 3\">\""))
    assert re.search(r"\d", _veri_disi_metin("\"<i aria-label=\\\"Bant 3\\\">\""))
    assert not re.search(r"\d", _veri_disi_metin("\"<b style='width:12px'>\""))
    js = _oku("uygulama.js")
    literaller = re.findall(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', js)
    rakamli = [lit for lit in literaller if re.search(r"\d", _veri_disi_metin(lit))]
    assert not rakamli, rakamli


def test_bant_etiketleri_ve_parametre_metni():
    params = {"tahsilat": {"tutar_bantlari": [50000, 250000]}}
    assert portfoy.bant_etiketleri(params) == {0: "50.000 altı", 1: "50.000 – 250.000",
                                             2: "250.000 ve üzeri"}
    assert portfoy.bant_etiketleri({"tahsilat": {"tutar_bantlari": []}}) == {0: "Tek bant"}
    assert _metin(True) == "Evet" and _metin(None) == "Tanımsız" and _metin(0.8) == "0,8"
    assert _metin(["TRAFIK", "KASKO"]) == "TRAFIK, KASKO" and _metin([]) == "Boş liste"
    assert _metin({"en_dusuk": None, "en_yuksek": 5}) == "en_dusuk: Tanımsız; en_yuksek: 5"


def test_yeterli_veri_uyarisi_tahsilat_puaninin_gosterildigi_her_yere_ulasir():
    """Olgun dosyası yeterli veri eşiğinin altındaki avukatın tahsilat puanı geçerlidir; Genel
    Bakış tablosu, sütun kadranı ve tahsilat kartı 'yeterli değil' işaretini taşır. İşaret tahsilat
    ve süre sütunundadır. Sütunu taşımayan (aktarımdan önceki gecenin) tabloyla sayfalar açılır."""
    tablolar, params = _cikti()
    tahsilat = tablolar["sonuc_tahsilat_avukat"]
    puanli = tahsilat[tahsilat["puan"].notna()]
    assert "yeterli" in tahsilat.columns and len(puanli) >= 2
    az, cok = puanli["avukat_kodu"].iloc[0], puanli["avukat_kodu"].iloc[1]
    degisik = dict(tablolar, sonuc_tahsilat_avukat=tahsilat.assign(
        yeterli=tahsilat["avukat_kodu"] != az))
    satir = {k["avukat_kodu"]: k for k in sunum.sayfa("genel", degisik, params)["bilesenler"][
        "genel.avukat_tablosu"]}
    assert satir[az]["tahsilat_yeterli"] is False and satir[cok]["tahsilat_yeterli"] is True
    sayfa = sunum.sayfa("avukat", degisik, params, {"kod": az})["bilesenler"]
    kadran = {k["sutun"]: k["yeterli"] for k in sayfa["avukat.sutunlar"]}
    sure = tablolar["sonuc_sure"].set_index("avukat_kodu")["yeterli"]
    assert kadran.pop("tahsilat") is False and kadran.pop("sure") is bool(sure[az])
    assert all(v is None for v in kadran.values())
    assert sayfa["avukat.tahsilat"][0]["yeterli"] is False
    eski = dict(tablolar, sonuc_tahsilat_avukat=tahsilat.drop(columns="yeterli"))
    for ad in ("genel", "avukat"):
        json.dumps(sunum.sayfa(ad, eski, params, {"kod": az}))
