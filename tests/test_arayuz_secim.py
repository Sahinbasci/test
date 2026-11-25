"""Arayüz katmanında seçim, sıralama, pencere ve süzme kuralları (arayuz/sunum*.py).

Tablolar elle kurulur; her avukatın değerleri farklıdır, yanlış avukatın satırı gelirse test
düşer. Avukat seçimi prova çalışmasının tablolarıyla uçtan uca da denenir (ikinci ve son avukat).
"""
import pandas as pd

from arayuz import sunum, sunum_avukat, sunum_siralama, sunum_sure
from test_arayuz import _cikti
from yardimci import params_yukle

SUTUN_SIRASI = ["tahsilat", "sure", "kalite", "davranis"]
# Puan sırası: AV-02 (90), AV-03 ve AV-05 (80; eşitlikte kod), AV-01 (puan yok, en sonda).
LISTE = ["AV-02", "AV-03", "AV-05", "AV-01"]
# AV-04'ün birleşik puan satırı yok (listede değil) ama öteki tablolarda satırları var.
KODLAR = ["AV-01", "AV-02", "AV-03", "AV-04", "AV-05"]
AYLAR = ["2025-{:02d}".format(ay) for ay in (9, 10, 11, 12)] + [
    "2026-{:02d}".format(ay) for ay in range(1, 11)]


def _no(kod):
    return int(kod[-2:])


def _alt_basliklar(params):
    kodlar = params["kalite_davranis"]["alt_basliklar"]
    return [("kalite", ad) for ad in kodlar["kalite"]] + [
        ("davranis", ad) for ad in kodlar["davranis"]]


def _kart_tablolari(params):
    """Avukat kartı ve Genel Bakış'ın avukat tablosu için tablolar; satırlar karışık sırada."""
    mevcut = params["kalite_davranis"]["mevcut_alanlar"]
    df = pd.DataFrame
    return {
        "sonuc_birlesik": df({
            "avukat_kodu": ["AV-01", "AV-02", "AV-03", "AV-05"],
            "birlesik_puan": [None, 90.0, 80.0, 80.0],
            "performans_notu": [None, "A", "B+", "B+"], "genel_sira": [None, 1.0, 2.0, 2.0],
            "durum": ["EKSIK_SUTUN", "YAYIMLANDI", "YAYIMLANDI", "YAYIMLANDI"],
            "eksik_sutunlar": ["sure", None, None, None]}),
        "model_avukat": df([{"avukat_kodu": k, "unvan": "Büro " + k, "calisma_durumu": "DEVAM"}
                            for k in KODLAR]),
        "sonuc_puan_guncel": df([
            {"avukat_kodu": k, "sutun": sutun, "puan": _no(k) * 10.0 + SUTUN_SIRASI.index(sutun),
             "durum": "GECERLI", "agirlik": 0.25} for k in KODLAR
            for sutun in reversed(SUTUN_SIRASI)]),
        "sonuc_aciklama": df([
            {"avukat_kodu": k, "sutun": sutun, "sira": sira, "tur": "ADIM",
             "metin": "{} {} {}".format(k, sutun, sira)} for k in KODLAR
            for sutun, sira in (("birlesik", 1), ("tahsilat", 2), ("kalite", 1), ("tahsilat", 1))]),
        "sonuc_tahsilat_avukat": df([{"avukat_kodu": k, "n": _no(k) * 10.0, "puan": 70.0 + _no(k),
                                      "oran": _no(k) / 100.0, "durum": "GECERLI",
                                      "yeterli": True}
                                     for k in KODLAR]),
        "sonuc_tahsilat_brans": df([{"avukat_kodu": k, "brans": brans, "n": _no(k) * 3.0}
                                    for k in KODLAR for brans in ("KASKO", "TRAFIK")]),
        "sonuc_kalite_davranis_sutun": df([
            {"avukat_kodu": k, "sutun": sutun, "puanlanan": _no(k), "toplam": 6}
            for k in KODLAR for sutun in ("kalite", "davranis")]),
        "sonuc_kalite_davranis_alt": df([
            {"avukat_kodu": k, "sutun": sutun, "alt_baslik": ad, "puan": _no(k) * 100.0 + sira}
            for k in KODLAR for sira, (sutun, ad) in reversed(list(enumerate(
                _alt_basliklar(params))))]),
        "sonuc_mevcut_degerlendirme": df([
            {"avukat_kodu": k, "alt_baslik": ad, "puan": _no(k) + sira / 10.0}
            for k in KODLAR for sira, ad in reversed(list(enumerate(mevcut)))]),
        "sonuc_sure": df([{"avukat_kodu": k, "risk_dosya": _no(k) * 7, "yeterli": True}
                          for k in KODLAR]),
        "sonuc_sure_ozet": df([{"avukat_kodu": k, "kriter": kriter, "izleniyor": _no(k)}
                               for k in KODLAR for kriter in ("K1", "K2")]),
        # TRAFIK iki banttan toplanır (3 × no dosya); KASKO 10 dosya. Sıra avukata göre değişir.
        "sonuc_portfoy": df([
            {"avukat_kodu": k, "brans": brans, "tutar_bandi": bant, "aktif_dosya": aktif,
             "toplam_dosya": toplam, "aktif_rucu_tutari": 1000.0 * aktif}
            for k in KODLAR for brans, bant, aktif, toplam in (
                ("TRAFIK", 0, _no(k), 2 * _no(k)), ("KASKO", 0, 4, 10),
                ("TRAFIK", 1, 1, _no(k)))]),
        # 14 ay, iki branş; hesap anındaki ızgara 2025-11..2026-11 (son ay kısmi): kart bu
        # ızgarayı ay sırasıyla, branşlar toplanmış, tahsilatsız ayı sıfırla gösterir.
        "sonuc_tahsilat_aylik": df([
            {"avukat_kodu": k, "brans": brans, "ay": ay, "hareket_sayisi": 1,
             "tutar": _no(k) * 1000.0 + sira + (0.5 if brans == "KASKO" else 0.0),
             "ilk_ay": "2025-11", "son_ay": "2026-11", "son_ay_kismi": True}
            for k in KODLAR for sira, ay in reversed(list(enumerate(AYLAR)))
            for brans in ("TRAFIK", "KASKO")]),
        "birlesik_donem": df([
            {"avukat_kodu": k, "donem": donem, "yayin_surumu": surum,
             "birlesik_puan": puan + _no(k), "yayin_zamani": "2026-11-01 06:00:00"}
            for k in KODLAR for donem, surum, puan in (
                ("2026-10", 1, 70.0), ("2026-09", 2, 60.0), ("2026-09", 1, 50.0))]),
    }


def _kart(kod):
    params = params_yukle()
    return sunum_avukat.avukat(_kart_tablolari(params), params, kod), params


def _kart_avukati(kart, params):
    """Kartın her bileşeninin hangi avukata ait olduğu (değerlerden geri çözülür)."""
    no = {
        "baslik": kart["avukat.baslik"][0]["avukat_kodu"],
        "sutunlar": [int(k["puan"] // 10) for k in kart["avukat.sutunlar"]],
        "aciklama": [k["metin"].split()[0] for k in kart["avukat.aciklama"] if k["tur"] != "YOK"],
        "tahsilat": [int(k["n"] // 10) for k in kart["avukat.tahsilat"]],
        "brans": [int(k["n"] // 3) if k["toplam"] is False else int(k["n"] // 10)
                  for k in kart["avukat.brans"]],
        "kalite_davranis": [k["puanlanan"] for k in kart["avukat.kalite_davranis"]],
        "alt": [int(k["puan"] // 100) for k in kart["avukat.alt_basliklar"]],
        "mevcut": [int(k["puan"]) for k in kart["avukat.mevcut_degerlendirme"]],
        "sure": [k["risk_dosya"] // 7 for k in kart["avukat.sure"]],
        "sure_ozet": [k["izleniyor"] for k in kart["avukat.sure_ozet"]],
        "aylik": [int(k["tutar"] // 2000) for k in kart["avukat.aylik"] if not k["kismi"]],
        "gecmis": [int(k["birlesik_puan"]) % 10 for k in kart["avukat.gecmis"]]}
    assert len(no["alt"]) == len(_alt_basliklar(params)) and len(no["aylik"]) == 12
    return no


def test_avukat_karti_istenen_avukatin_verisini_gosterir():
    # Varsayılan (ilk) avukat AV-02'dir; listenin ortasındaki ve sonundaki avukat istenir.
    for kod in ("AV-03", "AV-01", "AV-05"):
        kart, params = _kart(kod)
        no = _no(kod)
        assert [k["avukat_kodu"] for k in kart["avukat.liste"]] == LISTE
        assert _kart_avukati(kart, params) == {
            "baslik": kod, "sutunlar": [no] * 4, "aciklama": [kod] * 4, "tahsilat": [no],
            "brans": [no] * 3, "kalite_davranis": [no, no], "alt": [no] * 13, "mevcut": [no] * 4,
            "sure": [no], "sure_ozet": [no, no], "aylik": [no] * 12, "gecmis": [no, no]}
        baslik = kart["avukat.baslik"][0]
        assert baslik["unvan"] == "Büro " + kod and baslik["yayimlanan"] == 3


def _karismaz(bilesenler):
    """Kartın bütün bileşenleri başlıktaki avukatındır."""
    no = _no(bilesenler["baslik"])
    assert {deger for ad, liste in bilesenler.items() if ad not in ("baslik", "aciklama")
            for deger in liste} == {no}, bilesenler["baslik"]
    assert set(bilesenler["aciklama"]) == {bilesenler["baslik"]}


def test_avukat_karti_kod_verilmezse_ya_da_listede_yoksa_ilk_avukat():
    # Kod verilmezse ya da hiçbir tabloda olmayan bir kod gelirse ilk avukat (en yüksek puan)
    # bütün bileşenleriyle gelir. Seçici kartın başlığındaki kodu izler.
    for kod in (None, "", "AV-99"):
        kart, params = _kart(kod)
        bilesenler = _kart_avukati(kart, params)
        assert bilesenler["baslik"] == "AV-02", kod
        _karismaz(bilesenler)
    # AV-04'ün başka tablolarda satırı var ama birleşik listede yok. Hangi kartın açılacağı
    # belgede tanımlı değil (bugün ilk avukatınki); yalnız kartın karışmadığı denetlenir.
    kart, params = _kart("AV-04")
    _karismaz(_kart_avukati(kart, params))


def test_avukat_karti_icindeki_siralar():
    kart, params = _kart("AV-01")
    assert [k["sutun"] for k in kart["avukat.sutunlar"]] == SUTUN_SIRASI
    # Açıklaması olmayan sütun (süre, davranış) içeriksiz YOK satırıyla gelir (puanı ve ağırlığı).
    assert [(k["sutun"], k["sira"]) for k in kart["avukat.aciklama"]] == [
        ("tahsilat", 1), ("tahsilat", 2), ("sure", 0), ("kalite", 1), ("davranis", 0),
        ("birlesik", 1)]
    assert [k["alt_baslik"] for k in kart["avukat.alt_basliklar"]] == [
        ad for _, ad in _alt_basliklar(params)]
    assert [k["alt_baslik"] for k in kart["avukat.mevcut_degerlendirme"]] == params[
        "kalite_davranis"]["mevcut_alanlar"]
    # Branşlar bantlardan toplanır, çok dosyalı branş önce: AV-01'de KASKO (10) > TRAFIK (3).
    assert [(k["brans"], k["toplam_dosya"], k["aktif_dosya"]) for k in kart["avukat.portfoy"]] == [
        ("KASKO", 10, 4), ("TRAFIK", 3, 2)]
    assert [k["brans"] for k in _kart("AV-05")[0]["avukat.portfoy"]] == ["TRAFIK", "KASKO"]
    # Izgaranın ayları eskiden yeniye; iki branşın tutarı ve hareket sayısı toplanır. Kesit
    # ayı (2026-11) tahsilatsızdır: sıfırla gelir ve kısmidir; ızgara dışındaki aylar gelmez.
    aylik = kart["avukat.aylik"]
    assert [k["ay"] for k in aylik] == AYLAR[2:] + ["2026-11"]
    assert aylik[0]["tutar"] == 2 * (1000.0 + 2) + 0.5 and aylik[0]["hareket_sayisi"] == 2
    assert (aylik[-1]["tutar"], aylik[-1]["hareket_sayisi"]) == (0, 0)
    assert [k["kismi"] for k in aylik] == [False] * 12 + [True]
    # Geçmiş: her dönemin son sürümü (2026-09'da 2. sürüm), dönem sırasıyla.
    assert [(k["donem"], k["yayin_surumu"], k["birlesik_puan"]) for k in
            kart["avukat.gecmis"]] == [("2026-09", 2, 61.0), ("2026-10", 1, 71.0)]


def test_avukat_listesi_puana_gore_bos_puan_sonda():
    params = params_yukle()
    tablolar = _kart_tablolari(params)
    liste = sunum_avukat.avukat(tablolar, params, None)["avukat.liste"]
    assert [(k["avukat_kodu"], k["birlesik_puan"]) for k in liste] == [
        ("AV-02", 90.0), ("AV-03", 80.0), ("AV-05", 80.0), ("AV-01", None)]
    assert liste[0]["unvan"] == "Büro AV-02"
    # Birleşik puan yalnız boş satırlardan oluşsa da liste koda göre sıralı ve tamdır.
    bos = tablolar["sonuc_birlesik"].assign(birlesik_puan=float("nan")).iloc[::-1]
    liste = sunum_avukat.avukat(dict(tablolar, sonuc_birlesik=bos), params, None)["avukat.liste"]
    assert [k["avukat_kodu"] for k in liste] == ["AV-01", "AV-02", "AV-03", "AV-05"]


def test_genel_avukat_tablosu_genel_siraya_gore_sirasiz_sonda():
    params = params_yukle()
    tablolar = _kart_tablolari(params)
    birlesik = tablolar["sonuc_birlesik"].iloc[::-1]  # giriş sırası sonucu etkilemez
    tablo = sunum_siralama.avukat_tablosu(dict(tablolar, sonuc_birlesik=birlesik))
    assert [(k["avukat_kodu"], k["genel_sira"]) for k in tablo] == [
        ("AV-02", 1.0), ("AV-03", 2.0), ("AV-05", 2.0), ("AV-01", None)]
    # Aktif dosya bütün branş ve bantlardan toplanır; gerçekleşen / beklenen avukatın kendi satırı.
    assert [(k["aktif_dosya"], k["gerceklesen_beklenen"]) for k in tablo] == [
        (2 + 4 + 1, 0.02), (3 + 4 + 1, 0.03), (5 + 4 + 1, 0.05), (1 + 4 + 1, 0.01)]
    eksik = sunum_siralama.avukat_tablosu(dict(tablolar, sonuc_portfoy=None,
                                             sonuc_tahsilat_avukat=None))
    assert [k["avukat_kodu"] for k in eksik] == ["AV-02", "AV-03", "AV-05", "AV-01"]
    assert {(k["aktif_dosya"], k["gerceklesen_beklenen"]) for k in eksik} == {(None, None)}


def test_avukat_secimi_prova_tablolarinda_ikinci_ve_son_avukat():
    tablolar, params = _cikti()
    liste = sunum.sayfa("avukat", tablolar, params)["bilesenler"]["avukat.liste"]
    kodlar = [k["avukat_kodu"] for k in liste]
    assert len(kodlar) >= 3 and len(set(kodlar)) == len(kodlar)
    tahsilat, portfoy = tablolar["sonuc_tahsilat_avukat"], tablolar["sonuc_portfoy"]
    for kod in (kodlar[1], kodlar[-1]):
        kart = sunum.sayfa("avukat", tablolar, params, {"kod": kod})["bilesenler"]
        assert kart["avukat.baslik"][0]["avukat_kodu"] == kod
        satir = tahsilat[tahsilat["avukat_kodu"] == kod]
        assert [k["n"] for k in kart["avukat.tahsilat"]] == list(satir["n"])
        aktif = portfoy.loc[portfoy["avukat_kodu"] == kod, "aktif_dosya"].sum()
        assert sum(k["aktif_dosya"] for k in kart["avukat.portfoy"]) == aktif
        ozet = tablolar["sonuc_sure_ozet"]
        assert sorted(k["dusum_sayisi"] for k in kart["avukat.sure_ozet"]) == sorted(
            ozet.loc[ozet["avukat_kodu"] == kod, "dusum_sayisi"])
        donem = tablolar["birlesik_donem"]
        assert [k["donem"] for k in kart["avukat.gecmis"]] == sorted(
            set(donem.loc[donem["avukat_kodu"] == kod, "donem"]))


def _donem(kriter, dosya, kod, seviye, sure, pencerede=False, atama="2026-10-01"):
    return {"kriter": kriter, "dosya_no": dosya, "avukat_kodu": kod, "seviye": seviye,
            "sure_gun": sure, "pencerede_dusum": pencerede, "atama_tarihi": pd.Timestamp(atama)}


def _sure_tablolari():
    k1 = [_donem("K1", "D-001", "AV-01", "SARI", 15), _donem("K1", "D-002", "AV-02", "KIRMIZI", 70),
          _donem("K1", "D-003", "AV-01", "TURUNCU", 30),
          _donem("K1", "D-004", "AV-03", "IZLENIYOR", 5),
          _donem("K1", "D-005", "AV-02", "KAPANDI", 40, pencerede=True),  # düşüm pencerede
          _donem("K1", "D-006", "AV-03", "KAPANDI", 45),  # pencere dışı: listede yok
          _donem("K1", "D-007", "AV-04", "KAPSAM_DISI", 0),
          _donem("K1", "D-008", "AV-01", "KIRMIZI", 90)]
    k2 = [_donem("K2", "D-101", "AV-02", "TURUNCU", 200),
          _donem("K2", "D-102", "AV-03", "SARI", 100),
          _donem("K2", "D-103", "AV-05", "KAPANDI", 300)]
    return {"sonuc_k1": pd.DataFrame(k1).drop(columns="kriter"),
            "sonuc_k2": pd.DataFrame(k2).drop(columns="kriter")}


def _sure(tablolar, secim=None):
    return sunum_sure.sure(tablolar, secim)


def test_sure_listesi_agir_seviye_ve_uzun_sure_once_kapananlardan_yalniz_pencerede_dusum():
    sonuc = _sure(_sure_tablolari())
    assert [(k["kriter"], k["dosya_no"]) for k in sonuc["sure.liste"]] == [
        ("K1", "D-008"), ("K1", "D-002"), ("K2", "D-101"), ("K1", "D-003"), ("K2", "D-102"),
        ("K1", "D-001"), ("K1", "D-004"), ("K1", "D-005")]
    # Avukat seçeneği ölçülen dönemi olan bütün avukatlardır: kapananı olan AV-05 var, yalnız
    # kapsam dışı dönemi olan AV-04 yok.
    assert sonuc["sure.filtre"] == [{"toplam": 8, "gosterilen": 8,
                                     "avukatlar": ["AV-01", "AV-02", "AV-03", "AV-05"]}]
    sayilar = {(k["kriter"], k["seviye"]): k["adet"] for k in sonuc["sure.seviyeler"]}
    assert sayilar == {("K1", "SARI"): 1, ("K1", "KIRMIZI"): 2, ("K1", "TURUNCU"): 1,
                       ("K1", "IZLENIYOR"): 1, ("K1", "KAPANDI"): 2, ("K1", "KAPSAM_DISI"): 1,
                       ("K2", "TURUNCU"): 1, ("K2", "SARI"): 1, ("K2", "KAPANDI"): 1}


def test_sure_filtresi_listeyi_suzer_secenek_ve_seviye_sayilarini_degistirmez():
    tablolar = _sure_tablolari()
    tam = _sure(tablolar)
    for secim, beklenen in (
            ({"avukat": "AV-01"}, ["D-008", "D-003", "D-001"]),
            ({"kriter": "K2"}, ["D-101", "D-102"]),
            ({"kriter": "K2", "seviye": "TURUNCU"}, ["D-101"]),
            # Seviye seçilince o seviyedeki bütün dönemler: kapananlar pencere dışı da gelir,
            # kapsam dışı dönem (nedeniyle) yalnız bu yolla görünür.
            ({"seviye": "KAPANDI"}, ["D-103", "D-006", "D-005"]),
            ({"seviye": "KAPSAM_DISI"}, ["D-007"]),
            ({"kriter": "K1", "avukat": "AV-03"}, ["D-004"]),
            ({"avukat": "AV-09"}, []),
            ({"kriter": "", "seviye": None}, [k["dosya_no"] for k in tam["sure.liste"]])):
        sonuc = _sure(tablolar, secim)
        assert [k["dosya_no"] for k in sonuc["sure.liste"]] == beklenen, secim
        assert sonuc["sure.filtre"][0]["toplam"] == len(beklenen), secim
        assert sonuc["sure.filtre"][0]["avukatlar"] == ["AV-01", "AV-02", "AV-03", "AV-05"], secim
        assert sonuc["sure.seviyeler"] == tam["sure.seviyeler"], secim


def _cok_donem(adet):
    """adet açık K1 dönemi: biri kırmızı (en kısa süre), ötekiler izleniyor, süre = sıra no.

    Sıralamada sona düşenler AV-09'undur ki sınırın dışında kalan avukat da seçenekte görünsün.
    """
    satirlar = [_donem("K1", "D-0000", "AV-01", "KIRMIZI", 0)]
    for no in range(1, adet):
        kod = "AV-09" if no <= adet - sunum_sure.EN_COK else "AV-0{}".format(no % 3 + 1)
        satirlar.append(_donem("K1", "D-{:04d}".format(no), kod, "IZLENIYOR", no))
    return pd.DataFrame(satirlar).drop(columns="kriter")


def test_sure_listesi_500_satir_siniri_ve_gercek_toplam():
    assert sunum_sure.EN_COK == 500
    for adet, gosterilen in ((499, 499), (500, 500), (501, 500), (531, 500)):
        sonuc = _sure({"sonuc_k1": _cok_donem(adet)})
        liste = sonuc["sure.liste"]
        assert sonuc["sure.filtre"][0]["toplam"] == adet, adet
        assert len(liste) == sonuc["sure.filtre"][0]["gosterilen"] == gosterilen, adet
        # Sınırda en ağır seviye ve en uzun süreler kalır; kesilen en kısa süreler.
        assert liste[0]["dosya_no"] == "D-0000"
        assert [k["sure_gun"] for k in liste[1:]] == list(range(adet - 1, adet - gosterilen, -1))
        avukatlar = sonuc["sure.filtre"][0]["avukatlar"]
        assert ("AV-09" in avukatlar) == (adet > 500) and "AV-09" not in {
            k["avukat_kodu"] for k in liste}, adet
    # Filtre sınırdan önce uygulanır: sınırın dışındaki AV-09 dönemleri filtreyle gelir.
    secili = _sure({"sonuc_k1": _cok_donem(531)}, {"avukat": "AV-09"})
    assert secili["sure.filtre"][0]["toplam"] == len(secili["sure.liste"]) == 31


def _olay(donem, gun, saat="00:00:00"):
    return {"dosya_no": donem["dosya_no"], "avukat_kodu": donem["avukat_kodu"],
            "atama_tarihi": donem["atama_tarihi"].strftime("%Y-%m-%d ") + saat, "kriter": "K1",
            "seviye": donem["seviye"], "olay_tarihi": pd.Timestamp(gun), "calisma_kimligi": "C1"}


def test_son_olaylar_gosterilenler_ve_filtreye_uyan_en_yeni_otuz():
    k1 = _cok_donem(531)
    donemler = k1.to_dict("records")
    gosterilen = {"D-0000"} | {"D-{:04d}".format(no) for no in range(32, 531)}
    olaylar = [_olay(d, "2026-01-01" if d["dosya_no"] in gosterilen else
                     pd.Timestamp("2026-10-01") + pd.Timedelta(days=int(d["sure_gun"])),
                     saat="14:30:00") for d in donemler]
    # Listede olmayan dönemin en yeni olayı (kapalı, pencere dışı) ve eski atama dönemi olayı.
    kapali = _donem("K1", "D-9999", "AV-02", "KAPANDI", 3)
    eski = dict(donemler[100], atama_tarihi=pd.Timestamp("2025-01-01"))
    olaylar += [_olay(kapali, "2026-11-19"), _olay(eski, "2026-11-18")]
    tablolar = {"sonuc_k1": pd.concat([k1, pd.DataFrame([kapali]).drop(columns="kriter")]),
                "bayrak_olay": pd.DataFrame(olaylar)}
    sonuc = _sure(tablolar)
    kayit = sonuc["sure.olaylar"]
    dosyalar = [k["dosya_no"] for k in kayit]
    # 500 gösterilen dönemin olayı + gösterilmeyen 31 dönemden en yeni 30'u (D-0002..D-0031;
    # en eskisi D-0001 kalır). Kapalı dönemin ve eski atama döneminin olayı gelmez.
    assert len(kayit) == 530 and len(set(dosyalar)) == 530
    assert "D-0001" not in dosyalar and {"D-0002", "D-0031"} <= set(dosyalar)
    assert "D-9999" not in dosyalar and dosyalar.count(donemler[100]["dosya_no"]) == 1
    assert dosyalar == sorted(dosyalar)
    # Avukat filtresi olaylara da uygulanır.
    secili = _sure(tablolar, {"avukat": "AV-09"})["sure.olaylar"]
    assert len(secili) == 31 and {k["avukat_kodu"] for k in secili} == {"AV-09"}


def test_eposta_ozeti_kirmizi_sonra_toplam_sirasi():
    eposta = pd.DataFrame([
        {"avukat_kodu": kod, "seviye": seviye, "dosya_no": "D-{:03d}".format(sira),
         "gonderilecek": kod != "AV-03"}
        for sira, (kod, seviye) in enumerate([
            ("AV-01", "SARI"), ("AV-01", "SARI"), ("AV-01", "SARI"), ("AV-02", "KIRMIZI"),
            ("AV-03", "KIRMIZI"), ("AV-03", "SARI"), ("AV-04", "TURUNCU")])])
    sonuc = _sure(dict(_sure_tablolari(), sonuc_eposta=eposta))["sure.eposta"]
    assert [(k["avukat_kodu"], k["sari"], k["turuncu"], k["kirmizi"], k["toplam"],
             k["gonderilecek"]) for k in sonuc] == [
        ("AV-03", 1, 0, 1, 2, False), ("AV-02", 0, 0, 1, 1, True),
        ("AV-01", 3, 0, 0, 3, True), ("AV-04", 0, 1, 0, 1, True)]


def test_eposta_ozeti_gonderilecek_ve_golgedeki_gecikmeleri_ayri_sayar():
    """Yedek yolda Kriter 1 gölgede, Kriter 2 canlıdır: avukatın Kriter 1 gecikmeleri
    gönderilecek satırda sayılmaz (önce iki kriterin toplamı "Gönderilecek")."""
    eposta = pd.DataFrame([
        {"avukat_kodu": "AV-01", "kriter": kriter, "seviye": seviye,
         "dosya_no": "D-{:03d}".format(sira), "gonderilecek": kriter == "K2"}
        for sira, (kriter, seviye) in enumerate([
            ("K1", "KIRMIZI"), ("K1", "SARI"), ("K1", "SARI"), ("K2", "TURUNCU")])])
    sonuc = _sure(dict(_sure_tablolari(), sonuc_eposta=eposta))["sure.eposta"]
    assert sorted((k["gonderilecek"], k["sari"], k["turuncu"], k["kirmizi"], k["toplam"])
                  for k in sonuc) == [(False, 2, 0, 1, 3), (True, 0, 1, 0, 1)]


def test_genel_bakis_yillik_aylik_oncelikli_ve_brans_sirasi():
    yillik = pd.DataFrame([
        {"avukat_kodu": kod, "yil": yil, "tutar": tutar, "yil_ici": yil == 2026}
        for kod, yil, tutar in (
            ("ATANAMAYAN", 2025, 9.0), ("ATANAMAYAN", 2026, 5000.0), ("AV-01", 2026, 100.0),
            ("AV-01", 2025, 900.0), ("AV-03", 2026, -50.0), ("AV-03", 2025, 10.0),
            ("AV-02", 2025, 1.0), ("AV-02", 2026, 300.0), ("AV-04", 2026, 300.0))])
    aylik = pd.DataFrame([
        {"avukat_kodu": kod, "brans": "TRAFIK", "ay": ay, "hareket_sayisi": 1,
         "tutar": (sira + 1) * (1.0 if kod == "AV-01" else 100.0),
         "ilk_ay": "2025-11", "son_ay": "2026-10", "son_ay_kismi": False}
        for sira, ay in enumerate(AYLAR) for kod in ("AV-01", "ATANAMAYAN")
        if ay != "2026-03"])  # Mart'ta tahsilat yok
    eposta = pd.DataFrame([
        {"avukat_kodu": "AV-01", "kriter": "K1", "dosya_no": "D-{:03d}".format(no),
         "seviye": seviye, "sure_gun": sure}
        for no, (seviye, sure) in enumerate([
            ("SARI", 50), ("TURUNCU", 25), ("SARI", 12), ("KIRMIZI", 70), ("SARI", 11),
            ("TURUNCU", 40), ("SARI", 10), ("KIRMIZI", 80), ("SARI", 13), ("SARI", 14)])])
    portfoy = pd.DataFrame([
        {"avukat_kodu": kod, "brans": brans, "tutar_bandi": bant, "aktif_dosya": aktif,
         "toplam_dosya": aktif, "aktif_rucu_tutari": 10.0 * aktif, "bant_etiketi": etiket}
        for kod, brans, bant, aktif, etiket in (
            ("AV-01", "KASKO", 0, 3, "A"), ("AV-02", "TRAFIK", 1, 2, "B"),
            ("AV-01", "TRAFIK", 0, 2, "A"), ("AV-02", "YANGIN", 1, 5, "B"))])
    sonuc = sunum.genel({"sonuc_tahsilat_yillik": yillik, "sonuc_tahsilat_aylik": aylik,
                         "sonuc_eposta": eposta, "sonuc_portfoy": portfoy}, params_yukle())
    # Bu yılın tahsilatına göre azalan (eşitlikte kod), eksi tutar da yazılamayanın önünde.
    assert [(k["avukat_kodu"], k["yil"]) for k in sonuc["genel.yillik"]] == [
        ("AV-02", 2025), ("AV-02", 2026), ("AV-04", 2026), ("AV-01", 2025), ("AV-01", 2026),
        ("AV-03", 2025), ("AV-03", 2026), ("ATANAMAYAN", 2025), ("ATANAMAYAN", 2026)]
    # Izgaranın 12 ayı, avukata yazılan ve yazılamayan ayrı; tahsilatsız Mart sıfır (önceden
    # atlanıyor, noktalar eşit aralıkla dizildiği için zaman ekseni kayıyordu). Kesit ay sonu.
    ay = sonuc["genel.aylik"]
    assert [k["ay"] for k in ay] == AYLAR[2:]
    assert (ay[0]["yazilan"], ay[0]["yazilamayan"]) == (3.0, 300.0)
    assert (ay[4]["ay"], ay[4]["yazilan"], ay[4]["yazilamayan"]) == ("2026-03", 0, 0)
    assert (ay[-1]["yazilan"], ay[-1]["yazilamayan"]) == (14.0, 1400.0)
    assert not any(k["kismi"] for k in ay)
    # Öncelikli liste: en ağır seviye, sonra en uzun süre; ilk 8.
    assert [(k["seviye"], k["sure_gun"]) for k in sonuc["genel.oncelikli"]] == [
        ("KIRMIZI", 80), ("KIRMIZI", 70), ("TURUNCU", 40), ("TURUNCU", 25), ("SARI", 50),
        ("SARI", 14), ("SARI", 13), ("SARI", 12)]
    assert [(k["brans"], k["aktif_dosya"]) for k in sonuc["genel.brans"]] == [
        ("YANGIN", 5), ("TRAFIK", 4), ("KASKO", 3)]
    assert [(k["tutar_bandi"], k["bant_etiketi"], k["aktif_dosya"]) for k in
            sonuc["genel.bant"]] == [(0, "A", 5), (1, "B", 7)]


def test_sutun_durumu_gecerli_varsa_bekleme_nedeni_yok():
    puan = pd.DataFrame([
        {"avukat_kodu": kod, "sutun": sutun, "puan": puan_, "durum": durum}
        for kod, sutun, puan_, durum in (
            ("AV-01", "tahsilat", 70.0, "GECERLI"), ("AV-02", "tahsilat", None, "VERI_YETERSIZ"),
            ("AV-03", "tahsilat", 80.0, "GECERLI"),
            ("AV-01", "sure", None, "KAYNAK_BEKLENIYOR"), ("AV-02", "sure", None, "GOLGE_MOD"),
            ("AV-03", "sure", None, "KAYNAK_BEKLENIYOR"),
            ("AV-01", "kalite", 60.0, "GECERLI"), ("AV-02", "kalite", None, "TEYIT_BEKLIYOR"))])
    satir = {k["sutun"]: k for k in sunum.genel({"sonuc_puan_guncel": puan}, params_yukle())[
        "genel.sutun_durumu"]}
    assert [k for k in satir] == SUTUN_SIRASI
    assert (satir["tahsilat"]["gecerli"], satir["tahsilat"]["ortalama"],
            satir["tahsilat"]["gecersiz"], satir["tahsilat"]["bekleme_nedeni"]) == (
        2, 75.0, 1, None)
    assert (satir["sure"]["gecerli"], satir["sure"]["gecersiz"],
            satir["sure"]["bekleme_nedeni"]) == (0, 0, "KAYNAK_BEKLENIYOR")
    # Tek geçerli puan bile varsa bekleme nedeni gösterilmez; bekleyen satır geçersiz sayılmaz.
    assert (satir["kalite"]["gecerli"], satir["kalite"]["gecersiz"],
            satir["kalite"]["bekleme_nedeni"]) == (1, 0, None)
    assert (satir["davranis"]["gecerli"], satir["davranis"]["ortalama"],
            satir["davranis"]["bekleme_nedeni"]) == (0, None, None)
