"""Portföy ve aylık tahsilat (arayüz için).

Portföy: avukat, branş ve tutar bandı başına aktif dosya, toplam dosya ve aktif dosyaların
rücu tutarı; bant etiketi hesap anındaki sınırlardandır. Aktif: kesitte kapsamdaki açık atama
dönemi. Toplam: kesite kadar kapsamdaki bir atamayla avukatta bulunmuş tüm dosyalar.
Aylık tahsilat: avukat, branş ve ay başına, hareket tarihindeki avukata yazılan tahsilat.
Avukata yazılamayan tutar avukat_kodu ATANAMAYAN ile ayrı satırdadır. Pencere kesitin ayıyla
biten aylik_pencere_ay takvim ayıdır; ay ızgarası (ilk_ay, son_ay, son_ay_kismi) her satırda
hesap anındaki değerle durur, ekran tahsilatsız ayı sıfırla bu ızgaradan çizer.
Yıllık tahsilat: avukat ve takvim yılı başına, içinde bulunulan yıl önceki yılın aynı
dönemiyle karşılaştırılır (gereksinim: aylık ve yıllık tahsilatların karşılaştırılması).
"""
import pandas as pd

from avukat_perf import atama, tahsilat
from avukat_perf.aciklama import sayi
from avukat_perf.ortak import tek_gun
from avukat_perf.pencere import ay_sonu_mu, takvim_aylari
from avukat_perf.tahsilat_evren import dosyalari_hazirla, tutar_bandi_ekle

ATANAMAYAN = "ATANAMAYAN"
ANAHTAR = ["avukat_kodu", "brans", "tutar_bandi"]


def bant_etiketleri(params):
    """Tutar bandı numarası -> etiket (ör. 0: '40.000 altı')."""
    sinirlar = params["tahsilat"]["tutar_bantlari"]
    if not sinirlar:
        return {0: "Tek bant"}
    etiket = {0: sayi(sinirlar[0], 0) + " altı",
              len(sinirlar): sayi(sinirlar[-1], 0) + " ve üzeri"}
    for sira in range(1, len(sinirlar)):
        etiket[sira] = "{} – {}".format(sayi(sinirlar[sira - 1], 0), sayi(sinirlar[sira], 0))
    return etiket


def ozet(dosyalar, atamalar, kesit, params):
    """Avukat, branş ve tutar bandı başına portföy."""
    dosya = tutar_bandi_ekle(dosyalari_hazirla(dosyalar), params["tahsilat"])
    donem = atama.donemler(atamalar, kesit)
    tablo = donem.merge(dosya[["dosya_no", "brans", "tutar_bandi", "rucu_tutari"]],
                        on="dosya_no")
    toplam = tablo.groupby(ANAHTAR)["dosya_no"].nunique().rename("toplam_dosya")
    aktif = tablo[tablo["bitis_tarihi"].isna()].drop_duplicates(["avukat_kodu", "dosya_no"])
    aktif = aktif.groupby(ANAHTAR).agg(aktif_dosya=("dosya_no", "nunique"),
                                       aktif_rucu_tutari=("rucu_tutari", "sum"))
    sonuc = pd.concat([toplam, aktif], axis=1)
    sonuc = sonuc.fillna({"aktif_dosya": 0, "aktif_rucu_tutari": 0.0})
    sonuc = sonuc.astype({"aktif_dosya": int, "toplam_dosya": int}).reset_index()
    return sonuc.assign(bant_etiketi=sonuc["tutar_bandi"].map(bant_etiketleri(params)))


def aylik_tahsilat(dosyalar, atamalar, hareketler, kesit, params):
    """Avukat, branş ve ay (YYYY-AA) başına tahsilat tutarı ve hareket sayısı."""
    kesit = tek_gun(kesit)
    dosya = dosyalari_hazirla(dosyalar)
    donem = atama.donemler(atamalar, kesit)
    hareket = atama.hareket_atfet(hareketler, donem, kesit).merge(
        dosya[["dosya_no", "brans"]], on="dosya_no")
    ilk, aylar = takvim_aylari(kesit, params["tahsilat"]["aylik_pencere_ay"])
    hareket = hareket[hareket["hareket_tarihi"] >= ilk]
    hareket = hareket.assign(ay=hareket["hareket_tarihi"].dt.strftime("%Y-%m"),
                             avukat_kodu=hareket["avukat_kodu"].fillna(ATANAMAYAN))
    sonuc = hareket.groupby(["avukat_kodu", "brans", "ay"]).agg(
        tutar=("tutar", "sum"), hareket_sayisi=("tutar", "size"))
    return sonuc.reset_index().assign(ilk_ay=aylar[0], son_ay=aylar[-1],
                                      son_ay_kismi=not ay_sonu_mu(kesit))


def yillik_tahsilat(dosyalar, atamalar, hareketler, kesit, params):
    """Avukat ve takvim yılı başına tahsilat: son yillik_yil_sayisi yıl, içinde bulunulan yıl
    kesite kadar (yil_ici). Hareket tarihindeki avukata yazılır; yazılamayan ATANAMAYAN.

    ayni_donem_tutar her yılın 1 Ocak'tan kesitin ay ve gününe kadarki tahsilatıdır; kesit ay
    sonuysa ayın tamamı (28 Şubat 2029 kesitinde 29 Şubat 2028 dahil). İçinde
    bulunulan yılın satırında önceki yılın aynı dönemi (onceki_ayni_donem) ve değişim oranı
    (degisim) verilir; önceki dönem sıfır ya da negatifse değişim boştur. Tahsilatı olmayan
    yıl sıfırdır. Önceki yıl, gösterilmese de (yillik_yil_sayisi 1) karşılaştırma için hesaplanır.
    """
    kesit = tek_gun(kesit)
    dosya = dosyalari_hazirla(dosyalar)
    hareket = atama.hareket_atfet(hareketler, atama.donemler(atamalar, kesit), kesit)
    gosterilen = params["tahsilat"]["yillik_yil_sayisi"]
    yillar = list(range(kesit.year - max(gosterilen, 2) + 1, kesit.year + 1))
    hareket = hareket[hareket["dosya_no"].isin(dosya["dosya_no"]) &
                      hareket["hareket_tarihi"].dt.year.isin(yillar)]
    tarih = hareket["hareket_tarihi"]
    son_gun = 31 if ay_sonu_mu(kesit) else kesit.day
    ayni = (tarih.dt.month < kesit.month) | ((tarih.dt.month == kesit.month) &
                                              (tarih.dt.day <= son_gun))
    hareket = hareket.assign(yil=tarih.dt.year, ayni=hareket["tutar"].where(ayni, 0.0),
                             avukat_kodu=hareket["avukat_kodu"].fillna(ATANAMAYAN))
    tablo = hareket.groupby(["avukat_kodu", "yil"]).agg(
        tutar=("tutar", "sum"), hareket_sayisi=("tutar", "size"),
        ayni_donem_tutar=("ayni", "sum"))
    dizin = pd.MultiIndex.from_product([sorted(hareket["avukat_kodu"].unique()), yillar],
                                       names=["avukat_kodu", "yil"])
    tablo = tablo.reindex(dizin, fill_value=0).reset_index()
    onceki = tablo[tablo["yil"] == kesit.year - 1].set_index("avukat_kodu")["ayni_donem_tutar"]
    bu_yil = tablo["yil"] == kesit.year
    tablo["onceki_ayni_donem"] = tablo["avukat_kodu"].map(onceki).where(bu_yil)
    oran = tablo["tutar"] / tablo["onceki_ayni_donem"] - 1
    tablo["degisim"] = oran.where(tablo["onceki_ayni_donem"] >= tahsilat.YARIM_KURUS)
    tablo = tablo[tablo["yil"] > kesit.year - gosterilen].reset_index(drop=True)
    son = [kesit if yil == kesit.year else pd.Timestamp(year=yil, month=12, day=31)
           for yil in tablo["yil"]]
    return tablo.assign(yil_ici=tablo["yil"] == kesit.year, son_tarih=pd.to_datetime(son),
                        tutar=tablo["tutar"].astype(float),
                        hareket_sayisi=tablo["hareket_sayisi"].astype(int))
