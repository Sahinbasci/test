"""Kabul ölçütü 3, adalet: puan dosya sayısına, branşa ve tutar bandına bağlı yanlılık göstermez.

Adil dünya: her dosya grubunda (tahsilatta branş × dosya yaşı bandı × tutar bandı; sürede
kriter × süreç × branş) bütün avukatlar aynı oranda tahsilat yapar ve aynı oranda düşüm alır;
gruplar arasında oranlar çok farklıdır. Böyle bir dünyada portföyü küçük ya da büyük, tek
branşlı ya da karışık, yeniden atanmış dosyaları olan her avukat tahsilat puanının üç
bileşeninden de (tutar, sıklık, güncellik) tam 75 almalıdır. Bir avukat grubundan iyi ya da
kötüyse yönü doğru çıkmalıdır. Dosya yaşına göre adalet tests/test_tahsilat_bilesen.py'dedir.
"""
import pandas as pd

from avukat_perf import sure_puani, tahsilat
from yardimci import atama_tablosu, params_yukle

KESIT = "2026-11-19"
# Grup oranları bilerek çok farklı: yanlış bir genel oran kullanılsaydı branş yanlılığı çıkardı.
ORAN = {("TRAFIK", 10000.0): 0.60, ("TRAFIK", 90000.0): 0.30, ("KASKO", 20000.0): 0.45,
        ("YANGIN", 300000.0): 0.05, ("NAKLIYAT", 40000.0): 0.15}
# Avukat: [(branş, tutar, dosya sayısı)]; portföy büyüklüğü 30'dan 300'e, branş karışımı farklı.
PORTFOY = {"AV-01": [("TRAFIK", 10000.0, 30)],
           "AV-02": [("YANGIN", 300000.0, 300)],
           "AV-03": [("TRAFIK", 10000.0, 40), ("KASKO", 20000.0, 30), ("YANGIN", 300000.0, 30)],
           "AV-04": [("TRAFIK", 90000.0, 26), ("NAKLIYAT", 40000.0, 60)],
           "AV-05": [("KASKO", 20000.0, 150), ("TRAFIK", 10000.0, 6)]}
DEVIR = "2024-06-11"  # 01.01.2022 ile kesit arasının tam ortası: iki avukatın payı 0,5


def _params():
    params = params_yukle()
    params["tahsilat"]["tutar_bantlari"] = [50000]
    return params


def _adil_dunya(carpan=None):
    """Dosya, atama ve hareket tabloları; her dosyada tek tahsilat (grubun oranı × rücu tutarı).

    Her parçanın çift sayıda dosyası (beşte biri kadar) sürenin tam ortasında AV-06'ya geçer;
    bu dosyalarda iki avukat da kendi döneminde payı (0,5) kadar tutarı tahsil eder: dosya iki
    avukata yarım yarım sayılır, bir dosyadan fazla sayılmaz. Tahsilatların yarısı son 12
    aydadır (güncellik penceresi), her avukatın elindeki dosyaların yarısına düşer.
    carpan: {avukat: k}; o avukatın tahsilat tutarı k ile çarpılır.
    """
    dosya, atama, hareket, sira = [], [], [], 0
    for avukat, parcalar in sorted(PORTFOY.items()):
        for brans, tutar, adet in parcalar:
            devir = (adet // 5) // 2 * 2
            for no_ in range(adet):
                sira += 1
                no = "D-{:05d}".format(sira)
                dosya.append((no, brans, tutar, "2022-01-01"))
                if no_ >= devir:  # devredilmeyen dosya: tahsilat sırayla pencere içi ve öncesi
                    atama.append((no, avukat, brans, "2022-01-01"))
                    kim, tarih = avukat, "2026-03-01" if (no_ - devir) % 2 else "2023-06-01"
                else:
                    atama.append((no, avukat, brans, "2022-01-01", DEVIR, "YENIDEN_ATAMA"))
                    atama.append((no, "AV-06", brans, DEVIR))
                    hareket.append((no, "2023-06-01", ORAN[(brans, tutar)] * tutar * 0.5
                                    * (carpan or {}).get(avukat, 1.0)))
                    kim, tarih = "AV-06", "2026-03-01" if no_ % 2 else "2025-06-01"
                    hareket.append((no, tarih, ORAN[(brans, tutar)] * tutar * 0.5
                                    * (carpan or {}).get(kim, 1.0)))
                    continue
                hareket.append((no, tarih, ORAN[(brans, tutar)] * tutar
                                * (carpan or {}).get(kim, 1.0)))
    return (pd.DataFrame(dosya, columns=["dosya_no", "brans", "rucu_tutari",
                                         "rucuya_verilis_tarihi"]),
            atama_tablosu(atama),
            pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]))


def test_tahsilat_adil_dunyada_herkes_75():
    avukat, _ = tahsilat.puanla(*_adil_dunya(), kesit=KESIT, params=_params())
    avukat = avukat.set_index("avukat_kodu")
    assert sorted(avukat.index) == ["AV-01", "AV-02", "AV-03", "AV-04", "AV-05", "AV-06"]
    assert (avukat["durum"] == "GECERLI").all()
    assert (avukat["puan_tutar"] == 75.0).all(), avukat["puan_tutar"].to_dict()
    assert ((avukat["oran"] - 1.0).abs() < 1e-9).all()


def _taksitli_dunya():
    """Aynı portföyler; her dosya, elinde bulunduğu ayların branşına göre her 1., 2. ya da 3.
    ayında (ayın 15'i) tahsilat alır. Devir, takvimin üç türünün de başladığı ay başında
    (temmuz 2024). Herkes aynı başarıda."""
    aralik = {"TRAFIK": 1, "KASKO": 2, "NAKLIYAT": 2, "YANGIN": 3}
    aylar = list(pd.date_range("2022-01-01", "2026-11-01", freq="MS"))
    dosya, atama, hareket, sira = [], [], [], 0
    for avukat, parcalar in sorted(PORTFOY.items()):
        for brans, tutar, adet in parcalar:
            for no_ in range(adet):
                sira += 1
                no = "D-{:05d}".format(sira)
                dosya.append((no, brans, tutar, "2022-01-01"))
                if no_ < (adet // 5):
                    atama.append((no, avukat, brans, "2022-01-01", "2024-07-01", "YENIDEN_ATAMA"))
                    atama.append((no, "AV-06", brans, "2024-07-01"))
                else:
                    atama.append((no, avukat, brans, "2022-01-01"))
                hareket += [(no, str((ay + pd.Timedelta(days=14)).date()), 10.0)
                            for sira_ay, ay in enumerate(aylar) if sira_ay % aralik[brans] == 0]
    return (pd.DataFrame(dosya, columns=["dosya_no", "brans", "rucu_tutari",
                                         "rucuya_verilis_tarihi"]),
            atama_tablosu(atama),
            pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi", "tutar"]))


def test_taksitli_adil_dunyada_siklik_ve_guncellik_75():
    """Sıklık ve güncellik kişi-zaman sayımıdır: aynı başarıda portföy büyüklüğü, branş karışımı
    ve devir (kısa ya da uzun tutma) puanı değiştirmez. Ay uzunluğu farkından kalan sapma küçük."""
    avukat, _ = tahsilat.puanla(*_taksitli_dunya(), kesit=KESIT, params=_params())
    avukat = avukat.set_index("avukat_kodu")
    assert len(avukat) == 6 and (avukat["guncellik_o"] > 0).all()
    for bilesen in ("puan_siklik", "puan_guncellik"):
        assert (avukat[bilesen] - 75).abs().max() < 0.8, avukat[bilesen].to_dict()


def test_tahsilat_iyi_ve_kotu_avukatin_yonu_dogru():
    avukat, _ = tahsilat.puanla(*_adil_dunya({"AV-01": 1.3, "AV-02": 0.7}), kesit=KESIT,
                                params=_params())
    avukat = avukat.set_index("avukat_kodu")
    puan = avukat["puan"]
    assert puan["AV-01"] > 75.0 > puan["AV-02"]
    # Fark yalnız tutardadır: tahsilat yapılan dosya-ay sayısı değişmez, sıklık aynı kalır.
    temel, _ = tahsilat.puanla(*_adil_dunya(), kesit=KESIT, params=_params())
    temel = temel.set_index("avukat_kodu")
    assert avukat.loc["AV-01", "puan_tutar"] > 75.0 > avukat.loc["AV-02", "puan_tutar"]
    assert (avukat["puan_siklik"] == temel["puan_siklik"]).all()
    # AV-04'ün grupları (TRAFIK üst bant, NAKLIYAT) iki avukattan da etkilenmez.
    assert avukat.loc["AV-04", "puan_tutar"] == 75.0


def _sure_girdisi(sapma=None):
    """Her (süreç, branş) grubunda herkesin aynı oranda düşüm aldığı Kriter 1 dönemleri. Beklenen
    düşüm diğer avukatlardan kurulduğu için her grupta en az iki avukat vardır (tek avukatlı
    grup daha geniş katmanla karşılaştırılır; bkz. test_sure.py)."""
    gruplar = {("NORMAL", "TRAFIK"): 0.5, ("NORMAL", "YANGIN"): 0.1, ("NORMAL", "KASKO"): 0.2}
    adet = {"AV-01": {"TRAFIK": 40, "KASKO": 25}, "AV-02": {"YANGIN": 200},
            "AV-03": {"TRAFIK": 20, "YANGIN": 30, "KASKO": 50}}
    satirlar = []
    for avukat, branslar in sorted(adet.items()):
        for brans, sayi in branslar.items():
            dusum = int(round(sayi * gruplar[("NORMAL", brans)])) + (sapma or {}).get(avukat, 0)
            satirlar += [(avukat, "K1", "NORMAL", brans, "TURUNCU" if sira < dusum else
                          "KAPANDI", sira < dusum, "2026-06-01") for sira in range(sayi)]
    kapsam = pd.DataFrame({"avukat_kodu": sorted(adet), "kapsam": 1.0})
    tablo = pd.DataFrame(satirlar, columns=[ad for ad in sure_puani.GIRDI if ad != "dosya_no"])
    return tablo.assign(dosya_no=["D-{}".format(sira) for sira in range(len(tablo))]), kapsam


def test_sure_adil_dunyada_herkes_75():
    params = params_yukle()
    params["uyari"]["golge_mod"] = False
    girdi, kapsam = _sure_girdisi()
    tablo = sure_puani.puanla(girdi, kapsam, KESIT, params).set_index("avukat_kodu")
    assert (tablo["durum"] == "GECERLI").all()
    assert ((tablo["puan"] - 75.0).abs() < 1e-9).all(), tablo["puan"].to_dict()
    girdi, kapsam = _sure_girdisi({"AV-03": 5})
    puan = sure_puani.puanla(girdi, kapsam, KESIT, params).set_index("avukat_kodu")["puan"]
    assert puan["AV-03"] < 75.0 and puan["AV-01"] > 75.0


def test_gec_atama_etkisi_olculur_ve_bilinen_yonde():
    """Bilinen sınırlama (Hukuk'a iletilecek bilgi), hedef davranış değil.

    İki avukat aynı beceride: elde tuttukları her ay dosya başına aynı tutarı tahsil ederler.
    AV-GEC'in dosyaları rücuya verilişten 18 ay sonra atanmıştır. Atamadan önceki süre kimseye
    yazılmaz ama dosyanın beklentisi tam olarak atanan avukata girer (elde tutma payı ilk
    atamadan sayılır); bu yüzden geç atanan avukat aynı beceriyle 75'in altında kalır. Test
    etkinin yönünü ve büyüklüğünü sabitler: kural değişirse (ör. beklenti elde tutulan süreye
    göre kurulursa) bu test bilerek güncellenir.
    """
    kesit, aylik = pd.Timestamp(KESIT), 50.0
    dosya, atama, hareket, sira = [], [], [], 0
    for grup, baslangic in (("ERKEN", "2022-01-01"), ("GEC", "2023-07-01")):
        for k in range(5):  # beşer avukat; beklenti diğer avukatlardan kurulur
            for _ in range(30):
                sira += 1
                no = "D-{:05d}".format(sira)
                dosya.append((no, "TRAFIK", 10000.0, "2022-01-01"))
                atama.append((no, "AV-{}-{}".format(grup, k), "TRAFIK", baslangic))
                ay = (kesit - pd.Timestamp(baslangic)).days / 30.4375
                hareket.append((no, "2026-06-01", aylik * ay))
    girdi = (pd.DataFrame(dosya, columns=["dosya_no", "brans", "rucu_tutari",
                                          "rucuya_verilis_tarihi"]),
             atama_tablosu(atama), pd.DataFrame(hareket, columns=["dosya_no", "hareket_tarihi",
                                                                  "tutar"]))
    avukat = tahsilat.puanla(*girdi, kesit=KESIT, params=_params())[0].set_index("avukat_kodu")
    erken, gec = avukat.index.str.contains("ERKEN"), avukat.index.str.contains("GEC")
    tutar = avukat["puan_tutar"][erken].mean() - avukat["puan_tutar"][gec].mean()
    puan = avukat["puan"][erken].mean() - avukat["puan"][gec].mean()
    assert (avukat["puan_tutar"][gec] < 75.0).all() and (avukat["puan_tutar"][erken] > 75.0).all()
    # 18 aylık gecikme tutar bileşeninde yaklaşık 15 puanlık fark üretir (aynı beceri, 30'ar
    # dosya, beşer avukat). Sıklık ve güncellik kişi-zamanla ölçüldüğü için geç atama orada ceza
    # üretmez: atamadan önceki süre maruziyete girmez; tahsilatların hepsi aynı yaş bandında
    # (48-60 ay) ve o bantta herkes aynı süre tuttu, hepsi 75. Tahsilat puanındaki fark tutarın
    # ağırlığı kadardır (0,6 × 15).
    assert 14.5 < tutar < 15.5, tutar
    assert (avukat["puan_siklik"] == 75.0).all() and (avukat["puan_guncellik"] == 75.0).all()
    assert 8.7 < puan < 9.3, puan
