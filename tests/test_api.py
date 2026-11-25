"""API okuyucu: sunucunun sayfa boyutunu kısıtlaması, toplam kayıt sayısı, tekrar eden sayfa
ya da imleç ve kopan bağlantı."""
import http.client
import urllib.request

from hat import api
from test_hat_entegrasyon import KAYITLAR, _Sunucu
from yardimci import hata_bekle

SAYFA = {"tur": "sayfa", "sayfa_parametresi": "page", "boyut_parametresi": "size",
         "boyut": 1000}


def _kisitli(yol, sorgu, basliklar):
    """1000 istense de en çok 2 kayıt döndüren sunucu; toplam sayıyı da verir."""
    bas = (int(sorgu["page"]) - 1) * 2
    return 200, {"kayitlar": KAYITLAR[bas:bas + 2], "toplam": len(KAYITLAR)}


def test_sayfa_boyutunu_kisitlayan_sunucuda_kayit_kaybolmaz():
    sunucu = _Sunucu(_kisitli)
    try:
        tablo = api.oku({"adres": sunucu.adres + "/k", "kayit_yolu": "kayitlar",
                         "sayfalama": SAYFA}, None)
        assert list(tablo["no"]) == ["D-1", "D-2", "D-3", "D-4", "D-5"]
        # Toplam yolu okuma sonunda doğrulanır (boş sayfaya kadar okunur); toplam_ile_dur
        # verilirse son sayfadan sonrası istenmez (sonrasını isteyince hata veren sunucular).
        once = len(sunucu.istekler)
        api.oku({"adres": sunucu.adres + "/k", "kayit_yolu": "kayitlar",
                 "sayfalama": dict(SAYFA, toplam_yolu="toplam")}, None)
        assert len(sunucu.istekler) - once == 4
        once = len(sunucu.istekler)
        api.oku({"adres": sunucu.adres + "/k", "kayit_yolu": "kayitlar",
                 "sayfalama": dict(SAYFA, toplam_yolu="toplam", toplam_ile_dur=True)}, None)
        assert len(sunucu.istekler) - once == 3
    finally:
        sunucu.kapat()


def test_ayni_sayfa_ya_da_imlec_tekrar_gelirse_durur():
    sayac = {"imlec": 0}

    def yanit(yol, sorgu, basliklar):
        if yol == "/sabit":  # sayfa parametresini tanımayan sunucu hep ilk sayfayı döndürür
            return 200, KAYITLAR[:2]
        sayac["imlec"] += 1  # kayıtlar değişir ama imleç hep aynı: imleç tekrarı ayrıca yakalanır
        sira = sayac["imlec"] % len(KAYITLAR)
        return 200, {"kayitlar": KAYITLAR[sira:sira + 1], "sonraki": "ayni"}

    sunucu = _Sunucu(yanit)
    try:
        # Tekrar ikinci istekte fark edilir (en_cok_sayfa sınırına kadar istek gönderilmez).
        assert hata_bekle(RuntimeError, api.oku, {"adres": sunucu.adres + "/sabit",
                                                  "sayfalama": SAYFA, "en_cok_sayfa": 50}, None)
        assert len(sunucu.istekler) == 2
        imlec = {"tur": "imlec", "imlec_parametresi": "c", "sonraki_imlec_yolu": "sonraki"}
        assert hata_bekle(RuntimeError, api.oku, {"adres": sunucu.adres + "/imlec",
                                                  "kayit_yolu": "kayitlar", "en_cok_sayfa": 50,
                                                  "sayfalama": imlec}, None)
        assert len(sunucu.istekler) == 4
    finally:
        sunucu.kapat()


def test_cok_istek_429_yeniden_denenir_istemci_hatasi_denenmez():
    durum = {"n": 0}

    def yanit(yol, sorgu, basliklar):
        durum["n"] += 1
        return (429, {}) if durum["n"] == 1 else (200, KAYITLAR[:1])
    sunucu = _Sunucu(yanit)
    try:
        tablo = api.oku({"adres": sunucu.adres + "/k"}, None, uyku=lambda sure: None)
        assert len(tablo) == 1 and len(sunucu.istekler) == 2
    finally:
        sunucu.kapat()


def test_kopan_baglanti_yeniden_denenir():
    sunucu = _Sunucu(lambda yol, sorgu, basliklar: (200, KAYITLAR[:2]))
    asil, sayac = urllib.request.urlopen, {"n": 0}

    def kopan(*argumanlar, **secenek):
        sayac["n"] += 1
        if sayac["n"] == 1:
            raise http.client.RemoteDisconnected("bağlantı kapandı")
        return asil(*argumanlar, **secenek)
    try:
        urllib.request.urlopen = kopan
        tablo = api.oku({"adres": sunucu.adres + "/k"}, None, uyku=lambda sure: None)
        assert len(tablo) == 2 and sayac["n"] == 2
    finally:
        urllib.request.urlopen = asil
        sunucu.kapat()



def test_kayit_yolu_bulunamazsa_ya_da_liste_degilse_hata_verir():
    """Yanlış kayıt yolu boş görüntü sayılmaz (gözlem tabanı bozulurdu); liste indeksi ve
    noktalı anahtar (liste biçiminde yol) desteklenir."""
    govde = {"data": {"items": KAYITLAR[:2]}, "results": [{"rows": KAYITLAR[:3]}],
             "@odata": {"v": 1}, "a.b": KAYITLAR[:1], "bos": None}
    sunucu = _Sunucu(lambda yol, sorgu, basliklar: (200, govde))
    try:
        adres = sunucu.adres + "/k"
        for yanlis in ("items", "Data.items", "data.items.x", "@odata"):
            assert hata_bekle(ValueError, api.oku, {"adres": adres, "kayit_yolu": yanlis}, None)
        assert hata_bekle(ValueError, api.oku, {"adres": adres}, None)  # nesne yanıt, yol yok
        assert len(api.oku({"adres": adres, "kayit_yolu": "data.items"}, None)) == 2
        assert len(api.oku({"adres": adres, "kayit_yolu": "results.0.rows"}, None)) == 3
        assert len(api.oku({"adres": adres, "kayit_yolu": ["a.b"]}, None)) == 1
        assert api.oku({"adres": adres, "kayit_yolu": "bos"}, None).empty  # açık null boştur
    finally:
        sunucu.kapat()


def test_toplam_alani_kayit_sayisini_tutmazsa_hata_verir():
    """toplam_yolu kayıt yerine sayfa sayısını gösterirse okuma kesik sayılmaz, hata verir."""
    def yanit(yol, sorgu, basliklar):
        bas = (int(sorgu["page"]) - 1) * 2
        return 200, {"kayitlar": KAYITLAR[bas:bas + 2], "sayfa": 3, "toplam": len(KAYITLAR)}
    sunucu = _Sunucu(yanit)
    try:
        ayar = {"adres": sunucu.adres + "/k", "kayit_yolu": "kayitlar",
                "sayfalama": dict(SAYFA, toplam_yolu="sayfa")}
        assert hata_bekle(ValueError, api.oku, ayar, None)
        ayar["sayfalama"]["toplam_yolu"] = "toplam"
        assert len(api.oku(ayar, None)) == 5
    finally:
        sunucu.kapat()


def test_imlec_alani_dolu_sayfada_yoksa_hata_kisa_sayfada_son():
    def yanit(yol, sorgu, basliklar):
        return 200, {"kayitlar": KAYITLAR[:2] if yol == "/dolu" else KAYITLAR[:1]}
    sunucu = _Sunucu(yanit)
    try:
        imlec = {"tur": "imlec", "imlec_parametresi": "c", "sonraki_imlec_yolu": "@next",
                 "boyut": 2}
        assert hata_bekle(ValueError, api.oku, {"adres": sunucu.adres + "/dolu",
                                                "kayit_yolu": "kayitlar", "sayfalama": imlec},
                          None)
        assert len(api.oku({"adres": sunucu.adres + "/kisa", "kayit_yolu": "kayitlar",
                            "sayfalama": imlec}, None)) == 1
    finally:
        sunucu.kapat()


def test_retry_after_basligina_uyulur():
    durum, bekleme = {"n": 0}, []

    def yanit(yol, sorgu, basliklar):
        durum["n"] += 1
        return (429, {}, {"Retry-After": "7"}) if durum["n"] == 1 else (200, KAYITLAR[:1])
    sunucu = _Sunucu(yanit)
    try:
        api.oku({"adres": sunucu.adres + "/k"}, None, uyku=bekleme.append)
        assert bekleme == [7]
    finally:
        sunucu.kapat()


def test_oauth2_jetonu_okuma_sirasinda_bir_kez_yenilenir():
    durum = {"jeton": 0}

    def yanit(yol, sorgu, basliklar):
        if yol == "/jeton":
            durum["jeton"] += 1
            return 200, {"access_token": "j{}".format(durum["jeton"])}
        if basliklar.get("Authorization") != "Bearer j2" and sorgu.get("page") == "2":
            return 401, {}  # ikinci sayfada ilk jetonun süresi doldu
        bas = (int(sorgu["page"]) - 1) * 2
        return 200, {"kayitlar": KAYITLAR[bas:bas + 2]}
    sunucu = _Sunucu(yanit)
    try:
        kimlik = {"tur": "oauth2", "gizli": "OA", "jeton_adresi": sunucu.adres + "/jeton"}
        tablo = api.oku({"adres": sunucu.adres + "/k", "kayit_yolu": "kayitlar",
                         "sayfalama": SAYFA, "kimlik": kimlik}, {"OA": "istemci:sir"}.get)
        assert len(tablo) == 5 and durum["jeton"] == 2
    finally:
        sunucu.kapat()


def test_kimlik_basligi_yonlendirmede_tasinmaz():
    hedef = _Sunucu(lambda yol, sorgu, basliklar: (200, KAYITLAR[:1]))
    kaynak = _Sunucu(lambda yol, sorgu, basliklar: (302, {}, {"Location": hedef.adres + "/k"}))
    try:
        kimlik = {"tur": "bearer", "gizli": "ANAHTAR"}
        tablo = api.oku({"adres": kaynak.adres + "/k", "kimlik": kimlik},
                        {"ANAHTAR": "gizli-anahtar"}.get)
        assert len(tablo) == 1
        assert "Authorization" in kaynak.istekler[0][2]
        assert "Authorization" not in hedef.istekler[0][2]
    finally:
        hedef.kapat()
        kaynak.kapat()


def test_oauth2_istemci_kimligi_yonlendirmede_baska_sunucuya_gitmez():
    """Jeton ucu başka bir sunucuya yönlendirirse istemci sırrını taşıyan Basic başlığı oraya
    gönderilmez; veri isteğindeki kimlik başlığıyla aynı kural."""
    hedef = _Sunucu(lambda yol, sorgu, basliklar: (200, {"access_token": "j"}))
    kaynak = _Sunucu(lambda yol, sorgu, basliklar: (
        (302, {}, {"Location": hedef.adres + "/jeton"}) if yol == "/jeton"
        else (200, {"kayitlar": KAYITLAR[:1]})))
    try:
        kimlik = {"tur": "oauth2", "gizli": "OA", "jeton_adresi": kaynak.adres + "/jeton"}
        tablo = api.oku({"adres": kaynak.adres + "/k", "kayit_yolu": "kayitlar",
                         "sayfalama": {"tur": "yok"}, "kimlik": kimlik},
                        {"OA": "istemci:COK-GIZLI"}.get)
        assert len(tablo) == 1
        assert kaynak.istekler[0][2].get("Authorization", "").startswith("Basic ")
        assert hedef.istekler and "Authorization" not in hedef.istekler[0][2]
    finally:
        hedef.kapat()
        kaynak.kapat()


def test_anahtari_sorguda_isteyen_api_gizliden_okunur():
    # Anahtar ayar dosyasının sorgu bölümüne yazılmaz; kimlik.gizli adındaki gizliden gelir ve
    # her sayfa isteğinin sorgusuna eklenir, başlığa konmaz.
    sunucu = _Sunucu(_kisitli)
    try:
        kimlik = {"tur": "sorgu", "parametre": "api_key", "gizli": "ANAHTAR"}
        tablo = api.oku({"adres": sunucu.adres + "/k?bolge=tr", "kayit_yolu": "kayitlar",
                         "sayfalama": SAYFA, "kimlik": kimlik}, {"ANAHTAR": "gizli-1"}.get)
        assert len(tablo) == len(KAYITLAR)
        assert all(sorgu.get("api_key") == "gizli-1" and sorgu.get("bolge") == "tr"
                   for _, sorgu, _ in sunucu.istekler)
        assert all("Authorization" not in basliklar for _, _, basliklar in sunucu.istekler)
    finally:
        sunucu.kapat()


def test_kimlik_ayari_dogrulanir():
    from hat.api_kimlik import kimlik_hatalari
    assert kimlik_hatalari(None, "dosya.api") == []
    assert kimlik_hatalari({"tur": "bearer", "gizli": "A"}, "dosya.api") == []
    assert kimlik_hatalari({"tur": "Bearer", "gizli": "A"}, "dosya.api") == [
        "dosya.api: kimlik.tur basic | baslik | bearer | oauth2 | sorgu | yok olmalı"]
    assert kimlik_hatalari({"tur": "sorgu", "gizli": "A"}, "dosya.api") == [
        "dosya.api: sorgu kimliği için kimlik.parametre gerekir"]
    assert kimlik_hatalari({"tur": "oauth2", "gizli": "A"}, "x") == [
        "x: oauth2 kimliği için kimlik.jeton_adresi gerekir"]


def test_sorgudaki_anahtar_hata_iletisinde_maskelenir():
    # Bozuk adreste urllib'in iletisi adresi sorgusuyla verir; ileti çalışma kaydına yazıldığı
    # için anahtar (düz ve adreste kodlanmış hâli) maskelenir.
    from hat import okuma
    kimlik = {"tur": "sorgu", "parametre": "api_key", "gizli": "G"}
    for adres in ("api.example.com/v1/dosya", "https://api.example.com/v1/dosya listesi"):
        ayar = {"adres": adres, "kimlik": kimlik, "kayit_yolu": "data"}
        try:
            api.oku(ayar, {"G": "COK GIZLI/123&x"}.get)
            assert False, "bozuk adres hata vermeli"
        except Exception as hata:  # ileti kayda bu biçimde geçer
            metin = okuma.ileti(hata)
        assert "COK" not in metin and "GIZLI" not in metin and "***" in metin, metin
    # Anahtar iletide yoksa hata türü korunur (ör. kayıt yolu hatası ValueError kalır).
    sunucu = _Sunucu(lambda yol, sorgu, basliklar: (200, {"baska": []}))
    try:
        ayar = {"adres": sunucu.adres + "/k", "kimlik": kimlik, "kayit_yolu": "veri"}
        assert hata_bekle(ValueError, api.oku, ayar, {"G": "A"}.get)
    finally:
        sunucu.kapat()


def test_gizlinin_satir_sonu_kirpilir_ic_satir_sonu_degeri_yazmadan_durur():
    """Kopyala-yapıştırla sona eklenen satır sonu kırpılır, istek normal gider. İçte kalan satır
    sonunu http.client başlıkta reddeder ve iletiye değeri koyardı; değer yazılmadan durulur
    (ileti çalışma kaydına ve Veri Durumu sayfasına gidiyordu)."""
    from hat import okuma
    sunucu = _Sunucu(_kisitli)
    try:
        for tur, ek in (("bearer", {}), ("baslik", {"baslik_adi": "X-Anahtar"})):
            kimlik = dict({"tur": tur, "gizli": "JETON"}, **ek)
            ayar = {"adres": sunucu.adres + "/k", "kayit_yolu": "kayitlar", "sayfalama": SAYFA,
                    "kimlik": kimlik}
            assert len(api.oku(ayar, {"JETON": " GIZLI-JETON-123\r\n"}.get)) == len(KAYITLAR)
            baslik = sunucu.istekler[-1][2].get(ek.get("baslik_adi", "Authorization"))
            assert baslik in ("Bearer GIZLI-JETON-123", "GIZLI-JETON-123"), baslik
            try:
                api.oku(ayar, {"JETON": "GIZLI\nJETON-123"}.get)
                assert False, "iç satır sonu durmalı"
            except ValueError as hata:
                metin = okuma.ileti(hata)
            assert "GIZLI" not in metin and "JETON-123" not in metin and "JETON" in metin, metin
    finally:
        sunucu.kapat()


def test_gizli_deger_her_kimlik_turunde_maskelenir():
    from hat.api_kimlik import gizli_degerler, maskele
    gizli = {"G": "ist-1:sir/2"}.get
    for tur in ("bearer", "baslik", "sorgu", "basic", "oauth2"):
        degerler = gizli_degerler({"tur": tur, "gizli": "G"}, gizli)
        metin = maskele("istek: ist-1:sir/2 ist-1%3Asir%2F2 aXN0LTE6c2lyLzI=", degerler)
        assert "sir/2" not in metin and "sir%2F2" not in metin and "c2lyLzI" not in metin, tur
    # İki parçalı değerde (basic, oauth2) şifre tek başına geçse de maskelenir.
    assert maskele("şifre sir/2", gizli_degerler({"tur": "basic", "gizli": "G"}, gizli)) == \
        "şifre ***"
    assert gizli_degerler({"tur": "yok"}, gizli) == [] and gizli_degerler(None, gizli) == []


def test_oauth2_jeton_istegi_429_ve_zaman_asiminda_yeniden_denenir():
    import time
    durum = {"jeton": 0}

    def yanit(yol, sorgu, basliklar):
        if yol == "/jeton":
            durum["jeton"] += 1
            if durum["jeton"] == 2:
                time.sleep(1.0)  # ikinci deneme zaman aşımına düşer
            return (429, {}) if durum["jeton"] == 1 else (200, {"access_token": "j"})
        return 200, {"kayitlar": KAYITLAR[:2]}
    sunucu = _Sunucu(yanit)
    try:
        kimlik = {"tur": "oauth2", "gizli": "OA", "jeton_adresi": sunucu.adres + "/jeton",
                  "zaman_asimi_sn": 0.3}
        bekleme = []

        def uyku(saniye):  # tek iş parçacıklı sunucu zaman aşımına düşen isteği bitirsin
            bekleme.append(saniye)
            time.sleep(1.2 if saniye == 2 else 0)
        tablo = api.oku({"adres": sunucu.adres + "/k", "kayit_yolu": "kayitlar",
                         "sayfalama": {"tur": "yok"}, "kimlik": kimlik},
                        {"OA": "istemci:sir"}.get, uyku=uyku)
        assert len(tablo) == 2 and durum["jeton"] == 3 and bekleme == [1, 2]
    finally:
        sunucu.kapat()
