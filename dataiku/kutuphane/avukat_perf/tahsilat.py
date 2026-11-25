"""Tahsilat sütun puanı: tutar, sıklık ve güncellik bileşenlerinin ağırlıklı toplamı.

Üç bileşen de avukatın gerçekleşenini aynı dosya grubundan (gruplama: branş, dosya yaşı bandı,
tutar bandı) beklenene oranlar (bkz. tahsilat_tutar, tahsilat_olay, tahsilat_puan):
- Tutar: olgun dosyalarda avukata yazılan tahsilat ÷ beklenen tahsilat.
- Sıklık: olgun dosyalarda tahsilat yapılan dosya-ay sayısı ÷ elde tutulan süreden (dosya-yıl)
  beklenen sayı.
- Güncellik: aynısı, son dönemde (guncellik_pencere_ay) bütün dosyalarla.
Olgun dosya: kesitte branşının izleme süresini doldurmuş ve bu sürede kapsamdaki bir avukatta
bulunmuş dosya; avukatlar arasında elde tutma payıyla bölünür. Hareketler yalnız tahsilat
hareketlerini içermelidir; ters kayıt eksi tutarla gelir.
"""
from avukat_perf import atama, tahsilat_olay
from avukat_perf.ortak import tek_gun
from avukat_perf.tahsilat_evren import bantli_dosyalar, olgunlar
from avukat_perf.tahsilat_puan import YARIM_KURUS, puan_hesapla, puanla as _puanla  # noqa: F401
from avukat_perf.tahsilat_puan import yeterli_mi
from avukat_perf.tahsilat_tutar import tutar

ANAHTAR = ["avukat_kodu", "brans"]
TOPLANAN = ["n", "maruziyet", "gerceklesen", "beklenen", "siklik_o", "siklik_e", "guncellik_o",
            "guncellik_e"]


def puanla(dosyalar, atamalar, hareketler, kesit, params, kapanis=None):
    """Avukat başına tahsilat puanı ve grup başına oranlar: (avukat tablosu, grup tablosu).

    n kesirlidir: elde tutma paylarının toplamı. Avukata yazılamayan tahsilat (atamadan önce,
    sulh döneminde, boşlukta) puana girmez, grup tablosunda ayrı görünür.
    """
    avukat, gruplar, _ = hesapla(dosyalar, atamalar, hareketler, kesit, params, kapanis)
    return avukat, gruplar


def hesapla(dosyalar, atamalar, hareketler, kesit, params, kapanis=None):
    """(avukat, grup, avukat × branş) tabloları.

    kapanis: dosya_no -> kesitte tahsile kapalı dosyanın kapanış günü (bilinmiyorsa NaT); sıklık
    ve güncellikte dosyanın süresi o gün biter. Verilmezse bütün dosyalar açık sayılır.
    Branş tablosu aynı bileşenleri avukatın o branştaki dosyalarıyla verir. Puan en az
    en_az_olgun_dosya olgun dosyada üretilir; yeterli: olgun dosya en az yeterli_olgun_dosya
    (altında puan geçerlidir, ekranda 'Yeterli veri yok' uyarısıyla gösterilir). Avukatın
    puanı branş puanlarının ortalaması değildir; bütün dosyalarından hesaplanır.
    """
    tah = params["tahsilat"]
    if tah["enflasyon_duzeltme"]:
        raise ValueError("tahsilat: enflasyon_duzeltme henüz uygulanmadı")
    kesit = tek_gun(kesit)
    grup = list(tah["gruplama"])
    kirilim = grup + [ad for ad in ("brans",) if ad not in grup]
    dosya = bantli_dosyalar(dosyalar, kesit, tah)
    olgun = olgunlar(dosya, kesit, tah)
    donem = atama.donemler(atamalar, kesit)
    baslangic = olgun[["dosya_no", "rucuya_verilis_tarihi"]].rename(
        columns={"rucuya_verilis_tarihi": "baslangic"})
    pay = atama.elde_tutma_paylari(donem, baslangic, kesit, tah["elde_tutma_paydasi"]).merge(
        olgun, on="dosya_no")
    pay = pay.assign(maruziyet=pay["pay"] * pay["rucu_tutari"])
    hareket = atama.hareket_atfet(hareketler, donem, kesit)
    # Tutar da sıklık ve güncellik gibi [rücuya veriliş, kesit] aralığındaki tahsilatı sayar.
    olgun_hareket = hareket.merge(olgun[["dosya_no", "rucu_tutari", "rucuya_verilis_tarihi"]
                                        + kirilim], on="dosya_no")
    verilisten = olgun_hareket["hareket_tarihi"] >= olgun_hareket["rucuya_verilis_tarihi"]
    olgun_hareket = olgun_hareket[olgun_hareket["dosya_no"].isin(pay["dosya_no"]) & verilisten]
    gruplar, brans = tutar(pay, olgun_hareket, grup, kirilim)
    siklik, guncellik, siklik_hizi = tahsilat_olay.sayimlar(olgun, dosya, donem, hareket, kesit,
                                                             tah, kapanis)
    brans = brans.merge(siklik, on=ANAHTAR, how="left").merge(guncellik, on=ANAHTAR, how="outer")
    brans = brans.fillna({ad: 0.0 for ad in TOPLANAN})
    brans = brans.sort_values(ANAHTAR).reset_index(drop=True)
    avukat = _puanla(brans.groupby("avukat_kodu", as_index=False)[TOPLANAN].sum(), tah)
    durum = avukat["eksik_nedeni"].isna().map({True: "GECERLI", False: "VERI_YETERSIZ"})
    brans = _puanla(brans, tah)
    brans = brans.assign(yeterli=yeterli_mi(brans["n"], tah))
    # Grup tablosu kesitteki olgun dosya gruplarıdır; sıklık hızı dosyaların o banttaki süresinden.
    gruplar = gruplar.merge(siklik_hizi[grup + ["siklik_hizi"]], on=grup, how="left")
    avukat = avukat.assign(durum=durum, yeterli=yeterli_mi(avukat["n"], tah))
    return avukat, gruplar, brans
