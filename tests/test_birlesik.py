"""Birleşik puan testleri. Süre dahil dört sütunda ağırlıklar 0,35 / 0,30 / 0,25 / 0,10
(tahsilat / sure / kalite / davranis; params.json agirliklar ikili karşılaştırmalarından).
Varsayılan params.json ilk fazdır (Süre puana girmez); dört sütunun kuralları dort_sutunlu()
ayarıyla, ilk faz dosyanın sonundaki testlerle sınanır."""
import pandas as pd

from avukat_perf import birlesik
from yardimci import agirlik_karsilastirmasi, dort_sutunlu, hata_bekle, params_yukle

SUTUNLAR = ("tahsilat", "sure", "kalite", "davranis")
GIRDI = ["avukat_kodu", "sutun", "puan", "durum"]


def _girdi(avukatlar):
    """{avukat: [tahsilat, sure, kalite, davranis]}; None olan sütun VERI_YETERSIZ olur."""
    satirlar = []
    for avukat, puanlar in avukatlar.items():
        for sutun, puan in zip(SUTUNLAR, puanlar):
            satirlar.append((avukat, sutun, puan, "VERI_YETERSIZ" if puan is None else "GECERLI"))
    return pd.DataFrame(satirlar, columns=GIRDI)


def _calistir(avukatlar, params=None):
    sonuc = birlesik.birlestir(_girdi(avukatlar), params or dort_sutunlu())
    return sonuc.set_index("avukat_kodu")


def test_dort_sutun_gecerliyse_puan_not_ve_sira():
    # Varsayılan ağırlık 35 / 30 / 25 / 10: 28 + 27 + 21,25 + 8,8 = 85,05
    sonuc = _calistir({"AV-1": [80, 90, 85, 88]})
    assert sonuc.loc["AV-1", "birlesik_puan"] == 85.05
    assert sonuc.loc["AV-1", "performans_notu"] == "A"
    assert sonuc.loc["AV-1", "genel_sira"] == 1 and sonuc.loc["AV-1", "durum"] == "YAYIMLANDI"
    assert sonuc.loc["AV-1", "eksik_sutunlar"] == ""


def test_agirlik_adayi_notu_degistirebilir():
    params = dort_sutunlu()
    params["agirliklar"] = agirlik_karsilastirmasi(35, 25, 30, 10)  # öteki aday
    sonuc = _calistir({"AV-1": [80, 90, 85, 88]}, params)
    assert sonuc.loc["AV-1", "birlesik_puan"] == 84.8
    assert sonuc.loc["AV-1", "performans_notu"] == "B+"
    params["agirliklar"] = agirlik_karsilastirmasi(30, 30, 25, 15)  # önceki varsayılan
    sonuc = _calistir({"AV-1": [80, 90, 85, 88]}, params)
    assert sonuc.loc["AV-1", "birlesik_puan"] == 85.45
    assert sonuc.loc["AV-1", "performans_notu"] == "A"


def test_bir_sutun_eksikse_puan_not_ve_sira_yayimlanmaz():
    sonuc = _calistir({"AV-1": [100, None, 100, 100], "AV-2": [60, 60, 60, 60]})
    av1 = sonuc.loc["AV-1"]
    assert pd.isna(av1["birlesik_puan"]) and av1["performans_notu"] is None
    assert pd.isna(av1["genel_sira"]) and av1["durum"] == "EKSIK_SUTUN"
    assert av1["eksik_sutunlar"] == "sure" and av1["tahsilat"] == 100.0
    assert sonuc.loc["AV-2", "genel_sira"] == 1


def test_satiri_hic_olmayan_sutun_da_eksik_sayilir():
    girdi = _girdi({"AV-1": [80, 90, 85, 88]})
    girdi = girdi[girdi["sutun"] != "kalite"]
    sonuc = birlesik.birlestir(girdi, dort_sutunlu()).set_index("avukat_kodu")
    assert sonuc.loc["AV-1", "eksik_sutunlar"] == "kalite"


def test_sure_gelmeden_hicbir_avukat_yayimlanmaz():
    sonuc = _calistir({"AV-1": [90, None, 90, 90], "AV-2": [70, None, None, 70]})
    assert set(sonuc["durum"]) == {"EKSIK_SUTUN"} and sonuc["genel_sira"].isna().all()
    assert list(sonuc["eksik_sutunlar"]) == ["sure", "sure,kalite"]


def test_not_sinirlari():
    notlar = dort_sutunlu()["notlar"]
    beklenen = {100: "A", 85: "A", 84.99: "B+", 75: "B+", 74.99: "B", 65: "B",
                64.99: "B-", 55: "B-", 54.99: "C", 0: "C"}
    for puan, harf in beklenen.items():
        assert birlesik.not_ver(puan, notlar) == harf, puan
    assert birlesik.not_ver(float("nan"), notlar) is None


def _eski_agirlik():
    """Ondalık aritmetik örnekleri 35 / 25 / 30 / 10 ağırlığıyla kurulmuştur."""
    params = dort_sutunlu()
    params["agirliklar"] = agirlik_karsilastirmasi(35, 25, 30, 10)
    return params


def test_kayan_nokta_hatasi_notu_dusurmez():
    puanlar = [74.07, 89.01, 89.84, 98.71]
    ham = sum(puan * agirlik for puan, agirlik in zip(puanlar, (0.35, 0.25, 0.30, 0.10)))
    assert ham < 85
    sonuc = _calistir({"AV-1": puanlar}, _eski_agirlik())
    assert sonuc.loc["AV-1", "birlesik_puan"] == 85.0
    assert sonuc.loc["AV-1", "performans_notu"] == "A"


def test_yarim_yukari_yuvarlama_elle_hesapla_ayni():
    # 0,35 × 85 + 0,25 × 85,58 + 0,30 × 84,5 + 0,10 × 85 = 84,995 → elle 85,00 (A).
    # Kayan noktayla toplam 84,99499… çıkar; round() 84,99 ve B+ verirdi.
    sonuc = _calistir({"AV-1": [85.0, 85.58, 84.5, 85.0], "AV-2": [75.0, 75.58, 74.5, 75.0],
                       "AV-3": [85.55, 76.01, 90.47, 62.09], "AV-4": [74.065, 80, 80, 80]},
                      _eski_agirlik())
    assert sonuc.loc["AV-1", "birlesik_puan"] == 85.0
    assert sonuc.loc["AV-1", "performans_notu"] == "A"
    assert sonuc.loc["AV-2", "performans_notu"] == "B+"
    assert sonuc.loc["AV-3", "birlesik_puan"] == 82.3
    # Sütun puanı da yarım yukarı: 74,065 → 74,07 (round() 74,06 verir).
    assert sonuc.loc["AV-4", "tahsilat"] == 74.07


def test_sutun_puani_yuvarlanip_birlestirilir():
    sonuc = _calistir({"AV-1": [84.996, 85.004, 85.0, 85.0]})
    assert sonuc.loc["AV-1", "tahsilat"] == 85.0 and sonuc.loc["AV-1", "sure"] == 85.0
    assert sonuc.loc["AV-1", "birlesik_puan"] == 85.0


def test_esit_puan_ayni_sirayi_alir():
    sonuc = _calistir({"AV-1": [80] * 4, "AV-2": [90] * 4, "AV-3": [80] * 4,
                       "AV-4": [70] * 4, "AV-5": [80, None, 80, 80]})
    yayimlanan = sonuc["genel_sira"].dropna().to_dict()
    assert yayimlanan == {"AV-1": 2, "AV-2": 1, "AV-3": 2, "AV-4": 4}
    assert pd.isna(sonuc.loc["AV-5", "genel_sira"])


def test_not_olcegi_parametredir():
    params = dort_sutunlu()
    params["notlar"] = [["A", 85], ["B+", 75], ["B-", 55], ["C", 0]]
    sonuc = _calistir({"AV-1": [70] * 4}, params)
    assert sonuc.loc["AV-1", "performans_notu"] == "B-"


def test_hatali_girdi_hata_verir():
    params = dort_sutunlu()
    tanimsiz = _girdi({"AV-1": [80] * 4}).replace({"sutun": {"sure": "hiz"}})
    yinelenen = pd.concat([_girdi({"AV-1": [80] * 4})] * 2)
    bos_puan = _girdi({"AV-1": [80] * 4}).assign(puan=[80, None, 80, 80])
    olcek_disi = _girdi({"AV-1": [80, 101, 80, 80]})
    eksik = _girdi({"AV-1": [80] * 4}).drop(columns="durum")
    for girdi in (tanimsiz, yinelenen, bos_puan, olcek_disi, eksik):
        assert hata_bekle(ValueError, birlesik.birlestir, girdi, params)


def test_metin_puan_sayiya_cevrilir():
    girdi = _girdi({"AV-1": [80, 90, 85, 88]})
    girdi = girdi.assign(puan=girdi["puan"].astype(str))
    sonuc = birlesik.birlestir(girdi, dort_sutunlu())
    assert sonuc["birlesik_puan"].iloc[0] == 85.05


def test_bos_girdi_bos_sonuc_verir():
    sonuc = birlesik.birlestir(pd.DataFrame([], columns=GIRDI), dort_sutunlu())
    assert sonuc.empty and "performans_notu" in sonuc.columns


def test_ilk_fazda_sure_birlesik_puana_girmez():
    """Varsayılan (ilk faz): ağırlıklar Tahsilat 0,50 / Kalite 0,36 / Davranış 0,14; Süre'nin
    puanı yoksa da avukat yayımlanır, varsa hesaba girmez. 0,5 × 80 + 0,36 × 85 + 0,14 × 88 =
    40 + 30,6 + 12,32 = 82,92."""
    sonuc = _calistir({"AV-1": [80, None, 85, 88], "AV-2": [80, 10, 85, 88],
                       "AV-3": [80, 90, None, 88]}, params_yukle())
    assert sonuc.loc["AV-1", "birlesik_puan"] == 82.92 == sonuc.loc["AV-2", "birlesik_puan"]
    assert sonuc.loc["AV-1", "durum"] == "YAYIMLANDI" and sonuc.loc["AV-1", "eksik_sutunlar"] == ""
    assert sonuc.loc["AV-2", "sure"] == 10.0  # bilgi olarak tabloda durur
    av3 = sonuc.loc["AV-3"]
    assert av3["durum"] == "EKSIK_SUTUN" and av3["eksik_sutunlar"] == "kalite"
    assert list(sonuc["genel_sira"].iloc[:2]) == [1, 1]


def test_birlesik_sutunlar_dogrulanir():
    from avukat_perf import params as pr
    for deger in ([], ["tahsilat", "tahsilat"], ["tahsilat", "sure_x"], "tahsilat", None):
        params = params_yukle()
        params["birlesik_sutunlar"] = deger
        assert any(h.startswith("birlesik_sutunlar:") for h in pr.dogrula(params)), deger
    assert pr.dogrula(dict(params_yukle(), birlesik_sutunlar=["tahsilat"])) == []
