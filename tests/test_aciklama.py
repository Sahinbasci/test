"""'Neden bu puanı aldı?' açıklaması testleri."""
import pandas as pd

from avukat_perf import aciklama
from yardimci import dort_sutunlu, params_yukle


TAHSILAT = ["avukat_kodu", "n", "gerceklesen", "beklenen", "oran", "r", "puan_tutar", "siklik_o",
            "siklik_e", "puan_siklik", "guncellik_o", "guncellik_e", "puan_guncellik", "puan",
            "eksik_nedeni", "durum"]


def _metinler(tablo, avukat, sutun):
    """Hesap adımları (özet ve eşitlik satırları test_aciklama_ozet.py'de)."""
    secili = tablo[(tablo["avukat_kodu"] == avukat) & (tablo["sutun"] == sutun)
                   & ~tablo["tur"].isin(["OZET", "ESITLIK"])]
    return list(zip(secili["tur"], secili["metin"]))


def test_turkce_sayi_bicimi():
    assert aciklama.sayi(1234567.891) == "1.234.567,89"
    assert aciklama.sayi(0.5, 4) == "0,5000"
    assert aciklama.sayi(-12.5, 1) == "-12,5"
    assert aciklama.sayi(float("nan")) == "—" and aciklama.sayi(None) == "—"
    # Yarım yukarı, birleşik puanla aynı kural (format() 74,06 ve 1.234 verirdi).
    assert aciklama.sayi(74.065) == "74,07" and aciklama.sayi(1234.5, 0) == "1.235"


def test_esikle_karsilastirilan_sayim_tabanin_altinda_kalir():
    # 19,996 dosya hesapta tabanın altındadır; açıklama "20,00" yazıp "en az 20" ile çelişmez.
    assert aciklama.sayim(19.996) == "19,99" and aciklama.sayim(20.004) == "20,00"
    assert aciklama.sayim(19.999999999999996) == "20,00"  # hesap da 9 ondalığa yuvarlar
    assert aciklama.sayim(0.7996, 1, 100) == "79,9" and aciklama.sayim(0.29, 1, 100) == "29,0"
    assert aciklama.sayim(None) == "—" and aciklama.sayim(float("nan")) == "—"
    tah = pd.DataFrame([("AV-1", 19.996, 0.0, 10.0, 0.0, None, None, "AZ_DOSYA", "VERI_YETERSIZ")],
                       columns=TAHSILAT[:6] + TAHSILAT[-3:])
    metin = _metinler(aciklama.uret(params_yukle(), tahsilat=tah), "AV-1", "tahsilat")
    assert metin[0] == ("KANIT", "Olgun dosya (elde tutma payıyla): 19,99")
    sure = pd.DataFrame([("AV-1", 40, 38, 0, 4.996, 0.7996, None, None, "AZ_BEKLENEN",
                          "VERI_YETERSIZ")],
                        columns=["avukat_kodu", "risk_donemi", "risk_dosya", "o", "e", "kapsam",
                                 "r", "puan", "eksik_nedeni", "durum"])
    metin = _metinler(aciklama.uret(params_yukle(), sure=sure), "AV-1", "sure")
    assert "(E): 4,99" in metin[0][1] and metin[1][1] == "Veri kapsamı: %79,9"


def test_tahsilat_hesap_adimlari_gercek_degerlerle():
    # AV-1: tutar 82,50; 30 dosyanın 24'ünde tahsilat (beklenen 18): R = 34 ÷ 28 → 85,71; son 12
    # ayda 2 dosyada (beklenen 5): R = 12 ÷ 15 = 0,8 → 65,00. 0,6 × 82,5 + 0,2 × 85,71 + 13 = 79,64
    tahsilat = pd.DataFrame([
        ("AV-1", 30.0, 1200.0, 1000.0, 1.2, 1.15, 82.5, 24.0, 18.0, 85.71, 2.0, 5.0, 65.0, 79.64,
         None, "GECERLI"),
        ("AV-2", 0.5, 100.0, 100.0, 1.0, None, None, 3.0, 3.0, None, 0.0, 0.0, None, None,
         "AZ_DOSYA", "VERI_YETERSIZ"),
        ("AV-3", 30.0, 9000.0, 1000.0, 9.0, 7.0, 100.0, 30.0, 1.0, 100.0, 0.0, 0.0, 75.0, 95.0,
         None, "GECERLI"),
        ("AV-4", 7.0, 700.0, 1000.0, 0.7, 0.88, 69.0, 3.0, 3.0, 75.0, 1.0, 1.0, 75.0, 71.4,
         None, "GECERLI")], columns=TAHSILAT)
    tablo = aciklama.uret(params_yukle(), tahsilat=tahsilat)
    av1 = _metinler(tablo, "AV-1", "tahsilat")
    assert av1[1] == ("KANIT", "Gerçekleşen tahsilat: 1.200,00 TL")
    assert av1[4] == ("HESAP", "R = (30 × 1,200000 + 10) ÷ (30 + 10) = 1,150000")
    assert av1[5] == ("HESAP", "Tutar puanı = 75 + 50 × (R − 1) = 82,50")
    assert av1[6:] == [
        ("KANIT", "Olgun dosyalarda tahsilat yapılan dosya-ay: 24 · beklenen: 18,0000 (elde "
                  "tutulan süre × gruptaki diğer avukatların tahsilat hızı)"),
        ("HESAP", "Sıklık puanı: R = (24 + 10) ÷ (18,0000 + 10) = 1,214286 → 85,71"),
        ("KANIT", "Son 12 ayda tahsilat yapılan dosya-ay: 2 · beklenen: 5,0000 (elde tutulan "
                  "süre × gruptaki diğer avukatların tahsilat hızı)"),
        ("HESAP", "Güncellik puanı: R = (2 + 10) ÷ (5,0000 + 10) = 0,800000 → 65,00"),
        ("HESAP", "Tahsilat puanı = 0,6 × 82,50 + 0,2 × 85,71 + 0,2 × 65,00 = 79,64")]
    assert _metinler(tablo, "AV-2", "tahsilat")[-1] == (
        "ISTISNA", "Puan üretilmedi: dosya sayısı yayın tabanının altında (en az 1).")
    av3 = _metinler(tablo, "AV-3", "tahsilat")
    assert av3[5][1].endswith("= 100,00 (0–100 aralığına kırpıldı)")
    assert av3[7][1].endswith("→ 100,00 (0–100 aralığına kırpıldı)")  # (30 + 10) ÷ (1 + 10)
    assert not av3[9][1].endswith("kırpıldı)")
    # AV-4: puan üretilir, olgun dosya yeterli veri eşiğinin (10) altında olduğu için uyarı satırı.
    av4 = _metinler(tablo, "AV-4", "tahsilat")
    assert av4[3] == ("UYARI", "Yeterli veri yok: olgun dosya 7,00, en az 10 olmalı. Puan az "
                               "veriyle hesaplandı; güven ayarı onu beklenen düzeye yaklaştırır.")
    assert av4[-1][1].endswith("= 71,40") and not any(tur == "UYARI" for tur, _ in av1 + av3)
    # Puanı geçerli satırda özet satırı en sona eklenir (AV-2'de puan yok, özet de yok).
    assert list(tablo["sira"]) == (list(range(1, 13)) + [1, 2, 3, 4] + list(range(1, 13)) +
                                   list(range(1, 14)))


KALITE = ["avukat_kodu", "sutun", "puanlanan", "toplam", "gereken", "puan", "durum"]


def test_kalite_davranis_yeterlilik_ve_eksik_degerlendirme():
    kalite_davranis = pd.DataFrame([("AV-1", "kalite", 4, 6, 4, 87.5, "GECERLI"),
                                    ("AV-1", "davranis", 4, 7, 5, None, "EKSIK_DEGERLENDIRME")],
                                   columns=KALITE)
    tablo = aciklama.uret(params_yukle(), kalite_davranis=kalite_davranis)
    assert _metinler(tablo, "AV-1", "kalite") == [
        ("KANIT", "Puanlanan alt başlık: 4 / 6"),
        ("HESAP", "Yeterlilik: puanlanan 4, gereken en az 4 → sağlanıyor"),
        ("HESAP", "Puan = puanlanan alt başlıkların ortalaması = 87,50")]
    assert _metinler(tablo, "AV-1", "davranis")[1] == (
        "HESAP", "Yeterlilik: puanlanan 4, gereken en az 5 → sağlanmıyor")


def test_kalite_davranis_yeterlilik_karari_sonuctan_gelir():
    """Karar ve gereken sayı çekirdeğin sonuç satırından okunur; açıklama kuralı parametreden
    yeniden kurmaz (kural yalnız çekirdekte değişirse açıklama sonuçla çelişirdi:
    4/6 satırı EKSIK_DEGERLENDIRME iken 'sağlanıyor' yazıyordu)."""
    satir = pd.DataFrame([("AV-1", "kalite", 4, 6, 5, None, "EKSIK_DEGERLENDIRME")],
                         columns=KALITE)
    metinler = _metinler(aciklama.uret(params_yukle(), kalite_davranis=satir), "AV-1", "kalite")
    assert metinler[1] == ("HESAP", "Yeterlilik: puanlanan 4, gereken en az 5 → sağlanmıyor")
    assert metinler[2] == ("ISTISNA", "Eksik değerlendirme: puan üretilmedi.")


def test_sure_ve_birlesik():
    sure = pd.DataFrame([("AV-1", 40, 38, 4, 8.0, 1.0, 14 / 18, 86.11, None, "GECERLI"),
                         ("AV-2", 40, 40, 4, 8.0, None, 14 / 18, None, "GOLGE_MOD", "GOLGE_MOD")],
                        columns=["avukat_kodu", "risk_donemi", "risk_dosya", "o", "e", "kapsam",
                                 "r", "puan", "eksik_nedeni", "durum"])
    birlesik = pd.DataFrame([
        ("AV-1", 80.0, 90.0, 85.0, 88.0, 85.05, "A", 1.0, "YAYIMLANDI", ""),
        ("AV-2", 80.0, None, None, 88.0, None, None, None, "EKSIK_SUTUN", "sure,kalite")],
        columns=["avukat_kodu", "tahsilat", "sure", "kalite", "davranis", "birlesik_puan",
                 "performans_notu", "genel_sira", "durum", "eksik_sutunlar"])
    tablo = aciklama.uret(dort_sutunlu(), sure=sure, birlesik=birlesik)
    assert _metinler(tablo, "AV-1", "sure")[2][1] == "R = (4 + 10) ÷ (8 + 10) = 0,777778"
    assert _metinler(tablo, "AV-2", "sure")[-1][0] == "ISTISNA"
    # Eşik Türkçe biçimde: kapsam yüzde olarak.
    dusuk = sure.assign(puan=None, eksik_nedeni="KAPSAM_DUSUK", durum="VERI_YETERSIZ")
    metin = _metinler(aciklama.uret(params_yukle(), sure=dusuk), "AV-1", "sure")[-1][1]
    assert metin == "Puan üretilmedi: veri kapsamı yayın tabanının altında (en az %80)."
    assert _metinler(tablo, "AV-1", "birlesik") == [(
        "HESAP", "Birleşik puan = 0,35 × 80,00 + 0,30 × 90,00 + 0,25 × 85,00 + 0,10 × 88,00"
        " = 85,05 → A")]
    assert _metinler(tablo, "AV-2", "birlesik") == [(
        "ISTISNA", "Birleşik puan hesaplanmadı; eksik sütun: Süre ve Performans, "
        "Hukuki Kalite.")]


def test_girdi_yoksa_bos_tablo():
    tablo = aciklama.uret(params_yukle())
    assert tablo.empty and list(tablo.columns) == ["avukat_kodu", "sutun", "sira", "tur",
                                                   "metin", "etki"]


def test_sabit_ve_ondalik_sabit_gorunur():
    """Güven sabiti ondalıklıysa yuvarlanmadan yazılır (7,5 '8' görünmez); tam sayı ondalıksız."""
    assert aciklama.sabit(10) == "10" and aciklama.sabit(10.0) == "10"
    assert aciklama.sabit(7.5) == "7,5" and aciklama.sabit(0.25) == "0,25"
    params = params_yukle()
    params["tahsilat"]["olay_guven_sabiti"] = 7.5
    tahsilat = pd.DataFrame([("AV-1", 30.0, 1200.0, 1000.0, 1.2, 1.15, 82.5, 24.0, 18.0, 85.71,
                              2.0, 5.0, 65.0, 79.64, None, "GECERLI")], columns=TAHSILAT)
    satirlar = _metinler(aciklama.uret(params, tahsilat=tahsilat), "AV-1", "tahsilat")
    assert "R = (24 + 7,5) ÷ (18,0000 + 7,5)" in satirlar[7][1], satirlar[7]


def test_sure_r_satirindaki_beklenen_dusumle_elle_hesap_tutar():
    # E eşikle karşılaştırılan KANIT satırında aşağı kesilir (4,99), R formülünde kesilmez
    # (3 + 10) ÷ (4,996 + 10) elle hesapla ekrandaki R'yi verir.
    sure = pd.DataFrame([("AV-1", 40, 38, 3, 4.996, 0.9, 13 / 14.996, 70.65, None, "GECERLI",
                          True)],
                        columns=["avukat_kodu", "risk_donemi", "risk_dosya", "o", "e", "kapsam",
                                 "r", "puan", "eksik_nedeni", "durum", "yeterli"])
    metin = _metinler(aciklama.uret(params_yukle(), sure=sure), "AV-1", "sure")
    r_satiri = [m for _, m in metin if m.startswith("R = (")][0]
    assert r_satiri.startswith("R = (3 + 10) ÷ (4,996000 + 10) = "), r_satiri
