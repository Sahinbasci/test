"""Entegrasyon katmanı testleri: API okuyucu, kaynak normalleştirme, arşiv, ortam, akışlar."""
import json
import os
import shutil
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pandas as pd

from hat import akis, api, api_kimlik, arsiv, calisma, donem_akisi, gecmis, kaynak, okuma
from hat.ortam import YerelOrtam
from sentetik import uretici
from yardimci import KOK, hata_bekle, prova_ortami


class _Sunucu(object):
    """Testler için yerel JSON sunucusu; yanit(yol, sorgu, basliklar) -> (kod, gövde) ya da
    (kod, gövde, ek başlıklar)."""

    def __init__(self, yanit):
        istekler = self.istekler = []

        class Isleyici(BaseHTTPRequestHandler):
            def do_GET(self):
                adres = urlparse(self.path)
                sorgu = {k: v[0] for k, v in parse_qs(adres.query).items()}
                istekler.append((adres.path, sorgu, dict(self.headers)))
                sonuc = yanit(adres.path, sorgu, self.headers)
                self.send_response(sonuc[0])
                for ad, deger in (sonuc[2] if len(sonuc) > 2 else {}).items():
                    self.send_header(ad, deger)
                self.end_headers()
                self.wfile.write(json.dumps(sonuc[1]).encode("utf-8"))

            def do_POST(self):
                adres = urlparse(self.path)
                govde = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
                sorgu = {k: v[0] for k, v in parse_qs(govde).items()}
                istekler.append((adres.path, sorgu, dict(self.headers)))
                sonuc = yanit(adres.path, sorgu, self.headers)
                self.send_response(sonuc[0])
                for ad, deger in (sonuc[2] if len(sonuc) > 2 else {}).items():
                    self.send_header(ad, deger)
                self.end_headers()
                self.wfile.write(json.dumps(sonuc[1]).encode("utf-8"))

            def log_message(self, *argumanlar):
                pass

        self.sunucu = HTTPServer(("127.0.0.1", 0), Isleyici)
        self.adres = "http://127.0.0.1:{}".format(self.sunucu.server_port)
        threading.Thread(target=self.sunucu.serve_forever, daemon=True).start()

    def kapat(self):
        self.sunucu.shutdown()
        self.sunucu.server_close()


KAYITLAR = [{"no": "D-{}".format(i), "ic": {"tutar": i}} for i in range(1, 6)]


def test_api_sayfa_sayfalama_kimlik_ve_yeniden_deneme():
    durum = {"hata": 1}

    def yanit(yol, sorgu, basliklar):
        if basliklar.get("Authorization") != "Bearer gizli-anahtar":
            return 401, {}
        if durum["hata"]:
            durum["hata"] -= 1
            return 500, {}
        bas = (int(sorgu["page"]) - 1) * 2
        return 200, {"data": {"items": KAYITLAR[bas:bas + 2]}}

    sunucu = _Sunucu(yanit)
    try:
        ayar = {"adres": sunucu.adres + "/kayitlar", "kayit_yolu": "data.items",
                "kimlik": {"tur": "bearer", "gizli": "ANAHTAR"}, "sorgu": {"durum": "aktif"},
                "sayfalama": {"tur": "sayfa", "sayfa_parametresi": "page",
                              "boyut_parametresi": "size", "boyut": 2}}
        tablo = api.oku(ayar, {"ANAHTAR": "gizli-anahtar"}.get, uyku=lambda sure: None)
        assert list(tablo["no"]) == ["D-1", "D-2", "D-3", "D-4", "D-5"]
        assert list(tablo["ic.tutar"]) == [1, 2, 3, 4, 5]
        # 500 hatası + 3 dolu sayfa + son sayfayı doğrulayan boş sayfa.
        assert len(sunucu.istekler) == 5 and sunucu.istekler[-1][1]["durum"] == "aktif"
    finally:
        sunucu.kapat()


def test_api_ofset_ve_imlec_sayfalama():
    def yanit(yol, sorgu, basliklar):
        if yol == "/ofset":
            bas = int(sorgu["offset"])
            return 200, KAYITLAR[bas:bas + int(sorgu["limit"])]
        sira = int(sorgu.get("imlec", "0"))
        sonraki = str(sira + 3) if sira + 3 < len(KAYITLAR) else None
        return 200, {"kayitlar": KAYITLAR[sira:sira + 3], "sayfa": {"sonraki": sonraki}}

    sunucu = _Sunucu(yanit)
    try:
        ofset = api.oku({"adres": sunucu.adres + "/ofset", "sayfalama": {
            "tur": "ofset", "ofset_parametresi": "offset", "boyut_parametresi": "limit",
            "boyut": 2}}, None)
        imlec = api.oku({"adres": sunucu.adres + "/imlec", "kayit_yolu": "kayitlar",
                         "sayfalama": {"tur": "imlec", "imlec_parametresi": "imlec",
                                       "sonraki_imlec_yolu": "sayfa.sonraki"}}, None)
        assert len(ofset) == 5 and len(imlec) == 5
    finally:
        sunucu.kapat()


def test_api_istemci_hatasi_hemen_durur_ve_kimlik_turleri():
    sunucu = _Sunucu(lambda yol, sorgu, basliklar: (404, {}))
    try:
        assert hata_bekle(HTTPError, api.oku, {"adres": sunucu.adres + "/yok"}, None)
        assert len(sunucu.istekler) == 1
    finally:
        sunucu.kapat()
    gizli = {"G": "kullanici:sifre"}.get
    assert api_kimlik.kimlik_basligi({"tur": "basic", "gizli": "G"}, gizli) == {
        "Authorization": "Basic a3VsbGFuaWNpOnNpZnJl"}
    assert api_kimlik.kimlik_basligi({"tur": "baslik", "gizli": "G", "baslik_adi": "X-Api-Key"},
                               gizli) == {"X-Api-Key": "kullanici:sifre"}
    assert api_kimlik.kimlik_basligi(None, gizli) == {}
    assert hata_bekle(ValueError, api_kimlik.kimlik_basligi, {"tur": "oauth", "gizli": "G"}, gizli)


def test_api_oauth2_jeton_alip_bearer_ile_okur():
    def yanit(yol, sorgu, basliklar):
        if yol == "/jeton":
            dogru = sorgu.get("grant_type") == "client_credentials" and sorgu.get("scope") == "rucu"
            istemci = basliklar.get("Authorization") == "Basic aXN0ZW1jaTpzaXI=" or (
                sorgu.get("client_id") == "istemci" and sorgu.get("client_secret") == "sir")
            jeton = {"access_token": "J1", "expires_in": 3600}
            return (200, jeton) if dogru and istemci else (401, {})
        if basliklar.get("Authorization") != "Bearer J1":
            return 401, {}
        return 200, {"data": KAYITLAR[:2]}
    sunucu = _Sunucu(yanit)
    try:
        for dogrulama in ("basic", "govde"):
            ayar = {"adres": sunucu.adres + "/veri", "kayit_yolu": "data",
                    "kimlik": {"tur": "oauth2", "gizli": "OA", "kapsam": "rucu",
                               "jeton_adresi": sunucu.adres + "/jeton",
                               "istemci_dogrulama": dogrulama}}
            tablo = api.oku(ayar, {"OA": "istemci:sir"}.get)
            assert list(tablo["no"]) == ["D-1", "D-2"]
        assert hata_bekle(HTTPError, api.oku, ayar, {"OA": "istemci:yanlis"}.get)
    finally:
        sunucu.kapat()


def test_kaynak_okunamazsa_gece_kaldi_ve_kayda_gecer():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        ayarlar["kaynaklar"]["takip"]["dosya"]["yol"] = "olmayan/takip.csv"
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        assert sonuc["karar"] == "KALDI"
        kayit = ortam.tablo_oku("calisma_kaydi")
        takip = kayit[kayit["kaynak"] == "takip"].iloc[0]
        assert takip["durum"] == "KALDI" and takip["aciklama"].startswith("FileNotFoundError")
        kalite = ortam.tablo_oku("kalite_sonucu")
        hata = kalite[kalite["kontrol"] == "CEKIM_HATASI"]
        assert list(hata["kaynak"]) == ["takip"] and list(hata["durum"]) == ["KALDI"]
        assert ortam.tablo_oku("sonuc_tahsilat_avukat") is None
        ayarlar["kaynaklar"]["takip"]["yontem"] = "bekliyor"
        ayarlar["kaynaklar"]["dosya"]["dosya"]["yol"] = "olmayan/dosya.csv"
        zorunlu = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 03:00:00")
        assert zorunlu["karar"] == "KALDI" and zorunlu["eksik_kaynaklar"] == ["dosya"]
    finally:
        shutil.rmtree(kok)


def test_donem_sonu_ay_sonunu_kapsayan_gece_ister():
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        assert donem_akisi.calistir(ortam, params, "2026-10")["karar"] == "KAYNAK_BEKLENIYOR"
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        bayat = donem_akisi.calistir(ortam, params, "2026-11", simdi="2026-11-19 06:00:00")
        assert bayat["karar"] == "KALDI" and ortam.tablo_oku("puan_donem") is None
        kalite = ortam.tablo_oku("kalite_sonucu")
        kapsam = kalite[kalite["kontrol"] == "VERI_KAPSAMI"]
        assert list(kapsam["durum"]) == ["KALDI"]
        assert donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 06:00:00")[
            "karar"] == "GECTI"
    finally:
        shutil.rmtree(kok)


def _saat_diliminde(dilim, fonk):
    """fonk'u sürecin saat dilimi (TZ) dilim iken çalıştırır; sonra eski dilime döner."""
    eski = os.environ.get("TZ")
    os.environ["TZ"] = dilim
    time.tzset()
    try:
        return fonk()
    finally:
        if eski is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = eski
        time.tzset()


def _olc():
    """(simdi(), sürecin yerel saati, UTC, İstanbul saati); son ikisi süreç dilimine bağlı değil."""
    return calisma.simdi(), pd.Timestamp.now(), pd.Timestamp.now(tz="UTC").tz_localize(None), \
        pd.Timestamp.now(tz="Europe/Istanbul").tz_localize(None)


def test_calisma_zamani_sunucunun_saat_diliminden_bagimsiz_istanbul_saatidir():
    # Sunucu UTC ya da başka bir dilimde olabilir; simdi() yerel saate dönerse 02:00 çekimi bir
    # önceki güne yazılır. Geliştirici makinesi İstanbul'daysa yerel saat farkı görünmez; bu
    # yüzden dilim değiştirilir. POSIX biçimi (saat dilimi veritabanı gerekmez, yaz saati yok):
    # "XYZ-9" UTC+9, "XYZ+5" UTC-5 demektir.
    dilimler = (("UTC0", 0), ("XYZ-9", 9), ("XYZ+5", -5), ("TRT-3", 3))
    for dilim, utc_farki in dilimler if hasattr(time, "tzset") else ():  # Windows'ta yok
        simdi, yerel, utc, istanbul = _saat_diliminde(dilim, _olc)
        # Dilim gerçekten değişti: sürecin yerel saati UTC'den bu dilimin farkı kadar ileride.
        assert abs((yerel - utc).total_seconds() - utc_farki * 3600) < 5, dilim
        assert abs((simdi - istanbul).total_seconds()) < 5 and simdi.tzinfo is None, dilim
        # İstanbul'dan farklı her dilimde yerel saat de gerçekten farklı: test boşa geçmiyor.
        assert dilim == "TRT-3" or abs((yerel - istanbul).total_seconds()) > 3600, dilim
    fark = calisma.simdi() - pd.Timestamp.now(tz="Europe/Istanbul").tz_localize(None)
    assert abs(fark.total_seconds()) < 5 and calisma.simdi().tzinfo is None


def test_kaynak_normalle_eslesme_tarih_sayi_ve_genis_degerlendirme():
    ham = pd.DataFrame({"DOSYA_NO": ["D-1", "D-2", "D-3"], "AV_KOD": ["AV-1"] * 3,
                        "ATAMA_ZAMANI": ["12/10/2026 18:21:38", "01/02/2026 09:00:00", None],
                        "IPTAL_ZAMANI": [None, "bozuk", None]})
    ayar = {"alan_eslemesi": {"DOSYA_NO": "dosya_no", "AV_KOD": "avukat_kodu",
                              "ATAMA_ZAMANI": "atama_tarihi", "IPTAL_ZAMANI": "iptal_tarihi"},
            "tarih_bicimi": "%d/%m/%Y %H:%M:%S"}
    tablo = kaynak.normalle("atama_log", ham, ayar)
    assert tablo["atama_tarihi"].iloc[0] == pd.Timestamp("2026-10-12 18:21:38")
    assert tablo["iptal_tarihi"].iloc[1] == "bozuk" and pd.isna(tablo["atama_tarihi"].iloc[2])
    hareket = pd.DataFrame({"tutar": ["1.234,56", "-12,5", "abc", None]})
    sayi = kaynak.normalle("tahsilat_hareketi", hareket, {"sayi_bicimi": "tr"})["tutar"]
    assert list(sayi[:3]) == [1234.56, -12.5, "abc"] and pd.isna(sayi[3])
    # Sayı olarak gelen değer (API'de JSON sayısı) tr ayarında bozulmaz: 1234.56 → 123456 olurdu.
    sayisal = pd.DataFrame({"tutar": [1234.56, 1500.0, None]})
    sayi = kaynak.normalle("tahsilat_hareketi", sayisal, {"sayi_bicimi": "tr"})["tutar"]
    assert list(sayi[:2]) == [1234.56, 1500.0] and pd.isna(sayi[2])
    genis = pd.DataFrame({"avukat_kodu": ["AV-1"], "degerlendirme_tarihi": ["2026-01-01"],
                          "Hakimiyet": [4]})
    uzun = kaynak.normalle("degerlendirme", genis, {"genis_degerlendirme": {
        "Hakimiyet": "dosyaya_hakimiyet"}})
    assert list(uzun["alt_baslik"]) == ["dosyaya_hakimiyet"]


def test_kaynak_cek_yontemleri_ve_yer_tutucular():
    ortam = YerelOrtam(tempfile.mkdtemp(), kaynak_kok=KOK)
    assert kaynak.cek({"yontem": "bekliyor"}, ortam, {}) is None
    assert hata_bekle(ValueError, kaynak.cek, {"yontem": "ftp"}, ortam, {})
    dosya = kaynak.cek({"yontem": "dosya", "dosya": {
        "yol": "sentetik/veri/kaynak_degerlendirme_avukat.csv"}}, ortam, {})
    assert set(dosya.dtypes.astype(str)) == {"object"} and len(dosya) > 0
    yakalanan = {}
    eski = api.oku
    api.oku = lambda ayar, gizli: yakalanan.update(ayar) or pd.DataFrame()
    try:
        kaynak.cek({"yontem": "api", "api": {"adres": "x", "sorgu": {
            "gun": "{cekim_tarihi}", "bitis": "{kesit}"}}}, ortam,
            okuma.baglam(pd.Timestamp("2026-11-19")))
    finally:
        api.oku = eski
    assert yakalanan["sorgu"] == {"gun": "2026-11-19", "bitis": "2026-11-19"}
    # Her kaynak her gece tam görüntü verir: önceki çekimin tarihi yer tutucu olarak sunulmaz.
    assert set(okuma.baglam(pd.Timestamp("2026-11-19"))) == {"kesit", "cekim_tarihi"}


def test_gecelik_cekim_gunu_simdiden_ayrilamaz():
    """Çekim günü ve gözlem tabanı aynı andan (simdi) türetilir; ayrı bir cekim_tarihi
    verilseydi gün ile taban birbirinden kopardı."""
    import inspect
    assert list(inspect.signature(akis.gecelik).parameters) == ["ortam", "ayarlar", "params",
                                                               "simdi"]


def test_arsiv_uzerine_yazmaz_ve_ortam_turleri_korur():
    ortam = YerelOrtam(tempfile.mkdtemp())
    tablo = pd.DataFrame({"a": ["x", None], "t": pd.to_datetime(["2026-01-01", None]),
                          "s": [1.5, None], "n": [1, 2], "m": [True, False]})
    yol = arsiv.yaz(ortam, "dosya", tablo, "2026-11-19", "C1", {"yontem": "dosya"})
    assert ortam.arsiv_var(yol) and ortam.arsiv_var(yol.replace(yol.split("/")[-1],
                                                                "bilgi.json"))
    assert hata_bekle(ValueError, arsiv.yaz, ortam, "dosya", tablo, "2026-11-19", "C1", {})
    ortam.tablo_yaz("deneme", tablo)
    okunan = ortam.tablo_oku("deneme")
    assert [str(t) for t in okunan.dtypes] == ["object", "datetime64[ns]", "float64", "int64",
                                               "bool"]
    assert ortam.tablo_oku("olmayan") is None


def test_arsiv_bilgisi_normallestirme_ayarlarini_tasir():
    """Puanı değiştiren kaynak ayarları (alan eşlemesi, geniş değerlendirme, değer eşlemesi,
    biçimler) arşivin bilgi.json'unda kalır: ham arşivden yeniden üretim eşleme değişse de
    mümkündür (kural 4)."""
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        ayarlar["kaynaklar"]["degerlendirme"]["genis_degerlendirme"] = {"X": "dosyaya_hakimiyet"}
        ayarlar["kaynaklar"]["dosya"]["sayi_bicimi"] = "en"
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        bilgiler = {}
        for kok_klasor, _, dosyalar in os.walk(os.path.join(ortam.kok, "ham")):
            if "bilgi.json" in dosyalar:
                ad = [p for p in kok_klasor.split(os.sep) if p.startswith("kaynak=")][0][7:]
                with open(os.path.join(kok_klasor, "bilgi.json"), encoding="utf-8") as dosya:
                    bilgiler[ad] = json.load(dosya)
        assert bilgiler["degerlendirme"]["genis_degerlendirme"] == {"X": "dosyaya_hakimiyet"}
        assert bilgiler["dosya"]["sayi_bicimi"] == "en" and bilgiler["dosya"]["yontem"] == "dosya"
        assert set(kaynak.NORMALLEME) <= set(bilgiler["atama_log"])
        assert bilgiler["atama_log"]["alan_eslemesi"] == ayarlar["kaynaklar"]["atama_log"].get(
            "alan_eslemesi")
    finally:
        shutil.rmtree(kok)


def test_sentetik_uretici_az_avukatla_calisir():
    # Son iki avukat ayrılmış sayılıyordu: 3 ya da daha az avukatta yeniden atanacak başka
    # avukat kalmıyor, üretim IndexError ile çöküyordu. 4 ve üstünde kural (ve çıktı) aynı.
    for avukat, ayrilan in ((1, 0), (2, 0), (3, 1), (4, 2)):
        klasor = tempfile.mkdtemp()
        try:
            uretici.uret(klasor, 150, avukat)
            liste = pd.read_csv(os.path.join(klasor, "kaynak_degerlendirme_avukat.csv"))
            log = pd.read_csv(os.path.join(klasor, "kaynak_cekirdek_atama_log.csv"), dtype=str)
        finally:
            shutil.rmtree(klasor)
        assert list(liste["avukat_kodu"]) == ["AV-{:02d}".format(no) for no in
                                              range(1, avukat + 1)]
        assert (liste["calisma_durumu"] == "AYRILDI").sum() == ayrilan, avukat
        devam = set(liste.loc[liste["calisma_durumu"] == "DEVAM", "avukat_kodu"])
        normal = log[log["AV_KOD"].str.startswith("AV-")]
        assert len(normal) and set(normal["AV_KOD"]) <= devam, avukat
        # Yeniden atama her zaman başka bir avukata; tek avukatta yeniden atama yoktur.
        assert normal.groupby("DOSYA_NO")["AV_KOD"].agg(lambda kod: kod.is_unique).all()
        assert normal["DOSYA_NO"].duplicated().any() == (avukat > 1), avukat
    assert hata_bekle(ValueError, uretici.avukatlar, None, 0)  # avukatsız üretim anlamsız
    ortam, ayarlar, params, kok = prova_ortami(150, 3)
    try:
        assert akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")["karar"] == \
            "GECTI"
    finally:
        shutil.rmtree(kok)


def test_sentetik_varsayilan_uretim_depodaki_veriyle_bayti_baytina_ayni():
    # Üretici değişince depodaki sentetik/veri (8000 dosya, 30 avukat) yeniden üretilmeli;
    # az avukat düzeltmesi gibi değişiklikler varsayılan çıktıyı değiştirmemeli.
    depo, klasor = os.path.join(KOK, "sentetik", "veri"), tempfile.mkdtemp()
    try:
        sayilar = uretici.uret(klasor)
        # Yalnız CSV'ler: işletim sisteminin klasöre bıraktığı dosya (ör. .DS_Store) sayılmaz.
        csvler = sorted(ad for ad in os.listdir(depo) if ad.endswith(".csv"))
        assert sorted(os.listdir(klasor)) == csvler == sorted(ad + ".csv" for ad in sayilar)
        for ad in csvler:
            with open(os.path.join(depo, ad), "rb") as bir, \
                    open(os.path.join(klasor, ad), "rb") as iki:
                assert bir.read() == iki.read(), ad
    finally:
        shutil.rmtree(klasor)


def test_calisma_son_basarili():
    kayit = calisma.tablo([
        dict(calisma.satir("C1", "GECELIK", "dosya", "api", "2026-11-17", "2026-11-17"),
             durum="BASARILI", satir_sayisi=10),
        dict(calisma.satir("C2", "GECELIK", "dosya", "api", "2026-11-18", "2026-11-18"),
             durum="KALDI", satir_sayisi=3),
        dict(calisma.satir("C3", "GECELIK", "dosya", "api", "2026-11-19", "2026-11-19"),
             durum="BASARILI", satir_sayisi=12)])
    assert gecmis.son_basarili(kayit, "dosya", "2026-11-19") == (pd.Timestamp("2026-11-17"),
                                                                  10)
    assert gecmis.son_basarili(kayit, "atama_log", "2026-11-19") == (None, None)
    assert calisma.kimlik("2026-11-19 02:00:00").startswith("C20261119020000-")


def test_gecelik_uctan_uca_ve_ayni_gun_tekrar():
    ortam, ayarlar, params, kok = prova_ortami()
    try:
        ilk = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        assert ilk["karar"] == "GECTI" and ilk["eksik_kaynaklar"] == []
        tahsilat = ortam.tablo_oku("sonuc_tahsilat_avukat")
        # Avukatlara yazılan tahsilat grup tablosundakiyle tutar; beklenti diğer avukatlardan
        # kurulduğu için gerçekleşen ve beklenen toplamı eşit olmak zorunda değil.
        grup = ortam.tablo_oku("sonuc_tahsilat_grup")
        assert abs(tahsilat["gerceklesen"].sum() - grup["atfedilen"].sum()) < 1e-6
        assert (tahsilat["beklenen"] > 0).all()
        # Temiz provada tek uyarı, ataması olmayan avukatlardır (sentetik veride bilerek var);
        # başka kalıcı uyarı gerçek uyarıları gölgelerdi.
        kalite = ortam.tablo_oku("kalite_sonucu")
        uyarilar = kalite[kalite["durum"] != "GECTI"]
        assert set(zip(uyarilar["kaynak"], uyarilar["kontrol"])) <= {("iliski", "AVUKAT_AVUKAT")}
        assert "YINELENEN:hareket_no" in set(kalite["kontrol"])
        for ad in ("sonuc_k1", "sonuc_k2", "sonuc_sure", "sonuc_kalite_davranis_sutun",
                   "sonuc_birlesik", "sonuc_aciklama", "sonuc_portfoy", "sonuc_tahsilat_brans",
                   "bayrak_olay",
                   "gozlem_esas"):
            assert ortam.tablo_oku(ad) is not None, ad
        olay_sayisi = len(ortam.tablo_oku("bayrak_olay"))
        gozlem_sayisi = len(ortam.tablo_oku("gozlem_esas"))
        ikinci = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 03:00:00")
        assert ikinci["karar"] == "GECTI"
        assert len(ortam.tablo_oku("bayrak_olay")) == olay_sayisi
        assert len(ortam.tablo_oku("gozlem_esas")) == gozlem_sayisi
        assert ortam.tablo_oku("olay_celiski").empty
        calismalar = os.listdir(os.path.join(
            ortam.kok, "ham", "kaynak=dosya", "cekim_tarihi=2026-11-19"))
        assert len(calismalar) == 2
    finally:
        shutil.rmtree(kok)


def test_kalite_davranis_olcegi_teyitsizken_kalite_ve_davranis_teyit_bekler():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        params["kalite_davranis"]["olcek"] = {"en_dusuk": None, "en_yuksek": None}
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        assert sonuc["karar"] == "GECTI"
        assert sonuc["durumlar"]["kalite_davranis"] == "TEYIT_BEKLIYOR"
        puan = ortam.tablo_oku("sonuc_puan_guncel")
        kalite_davranis = puan[puan["sutun"].isin(["kalite", "davranis"])]
        assert not kalite_davranis.empty and set(kalite_davranis["durum"]) == {"TEYIT_BEKLIYOR"}
        assert ortam.tablo_oku("sonuc_kalite_davranis_sutun") is None
        assert (ortam.tablo_oku("sonuc_birlesik")["durum"] != "YAYIMLANDI").all()
        assert ortam.tablo_oku("sonuc_tahsilat_avukat") is not None
    finally:
        shutil.rmtree(kok)


def test_gecelik_baglanti_yoksa_hesap_yapmaz():
    ortam, ayarlar, params, kok = prova_ortami(200, 6)
    try:
        for ayar in ayarlar["kaynaklar"].values():
            ayar["yontem"] = "bekliyor"
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        assert sonuc["karar"] == "KAYNAK_BEKLENIYOR"
        assert set(sonuc["eksik_kaynaklar"]) == {"dosya", "atama_log"}
        assert ortam.tablo_oku("sonuc_tahsilat_avukat") is None
        assert set(ortam.tablo_oku("calisma_kaydi")["durum"]) == {"KAYNAK_BEKLENIYOR"}
    finally:
        shutil.rmtree(kok)


def test_gecelik_kapi_kaldiysa_son_gecerli_sonuc_korunur():
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-18 02:00:00")
        once = ortam.tablo_oku("sonuc_tahsilat_avukat")
        yol = os.path.join(kok, "sentetik", "veri", "kaynak_cekirdek_dosya.csv")
        pd.read_csv(yol, dtype=str).drop(columns="brans").to_csv(yol, index=False)
        sonuc = akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        assert sonuc["karar"] == "KALDI"
        pd.testing.assert_frame_equal(ortam.tablo_oku("sonuc_tahsilat_avukat"), once)
        kayit = ortam.tablo_oku("calisma_kaydi")
        assert "KALDI" in set(kayit["durum"])
        assert gecmis.son_basarili(kayit, "dosya", "2026-11-20")[0] == pd.Timestamp(
            "2026-11-18")
    finally:
        shutil.rmtree(kok)


def test_kacan_gece_avukat_lehine_ve_donem_yayini():
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        yol = os.path.join(kok, "sentetik", "veri", "kaynak_dava_takip_esas.csv")
        tam = pd.read_csv(yol, dtype=str)
        hedef = tam["dosya_no"].iloc[0]
        tam[tam["dosya_no"] != hedef].to_csv(yol, index=False)
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-16 02:00:00")
        tam.to_csv(yol, index=False)
        akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 02:00:00")
        gozlem = ortam.tablo_oku("gozlem_esas").set_index("anahtar")
        assert gozlem.loc[hedef, "dayanak"] == "GECELIK_GOZLEM"
        # 16'sı 02:00 çekiminde yoktu, 19'u çekiminde var: en erken olası gün 16'sı.
        assert gozlem.loc[hedef, "ilk_tarih"] == pd.Timestamp("2026-11-16")
        ilk = donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 03:00:00")
        tekrar = donem_akisi.calistir(ortam, params, "2026-10", simdi="2026-11-19 04:00:00")
        assert (ilk["yayin"], tekrar["yayin"]) == ("YENI", "DEGISMEDI")
        assert set(ortam.tablo_oku("birlesik_donem")["donem"]) == {"2026-10"}
    finally:
        shutil.rmtree(kok)


def test_ayni_gun_yeniden_calismada_taban_ayni_gunun_cekimidir():
    """19 Kasım 02:00 çekiminde olmayan esas 10:00'daki yeniden çalışmada görülürse gün içinde
    girilmiştir: ilk tarih 19 Kasım. Önceden taban önceki günün çekimiydi
    (16 Kasım); esas üç gün erken girilmiş sayılıyor, düşüm silinebiliyordu."""
    ortam, ayarlar, params, kok = prova_ortami(300, 8)
    try:
        yol = os.path.join(kok, "sentetik", "veri", "kaynak_dava_takip_esas.csv")
        tam = pd.read_csv(yol, dtype=str)
        hedef = tam["dosya_no"].iloc[0]
        tam[tam["dosya_no"] != hedef].to_csv(yol, index=False)
        for gece in ("2026-11-16 02:00:00", "2026-11-19 02:00:00"):
            akis.gecelik(ortam, ayarlar, params, simdi=gece)
        tam.to_csv(yol, index=False)
        assert akis.gecelik(ortam, ayarlar, params, simdi="2026-11-19 10:00:00")[
            "karar"] == "GECTI"
        gozlem = ortam.tablo_oku("gozlem_esas").set_index("anahtar")
        assert gozlem.loc[hedef, "onceki_basarili_cekim"] == pd.Timestamp("2026-11-19")
        assert gozlem.loc[hedef, "ilk_tarih"] == pd.Timestamp("2026-11-19")
        kayit = ortam.tablo_oku("calisma_kaydi")
        # Taban bu çalışmadan önce başlamış son başarılı çekimdir; sonrası (ileri tarihli) değil.
        assert gecmis.son_basarili(kayit, "dosya", "2026-11-19 10:00:00")[0] == pd.Timestamp(
            "2026-11-19")
        assert gecmis.son_basarili(kayit, "dosya", "2026-11-19 02:00:00")[0] == pd.Timestamp(
            "2026-11-16")
    finally:
        shutil.rmtree(kok)
