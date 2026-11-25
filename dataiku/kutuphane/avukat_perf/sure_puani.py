"""Süre ve Performans sütun puanı (dava takip sistemine bağlı).

Girdi Kriter 1 ve Kriter 2 değerlendirmelerinin birleşimidir (GIRDI sütunları).
Pencere (kesit − pencere_ay ay, kesit]; gölge gecelerinin kapsadığı günler sayılmaz (haric).
Risk altındaki dönem: düşüm eşiği (esik_turuncu) pencereye düşen ve ya düşüm almış ya da
süresinde kapanmış (KAPANDI) dönem; süresinden önce iade ya da koşul kaybıyla biten sayılmaz.
O: avukatın düşüm sayısı. E: avukatın her risk altındaki dönemi için aynı kriter, süreç ve
branştaki DİĞER avukatların düşüm oranının toplamı (grupta başka avukat yoksa aynı kriter ve
süreçteki, o da yoksa bütün diğerleri; bkz. referans). R = (O + k) ÷ (E + k); puan =
kırp(taban + eğim × (1 − R)). Yayın tabanı: E >= en_az_beklenen, kapsam >= en_az_kapsam.
yeterli: risk dönemlerinde en az yeterli_dosya farklı dosya (risk_dosya); altında puan
geçerlidir, ekranda 'Yeterli veri yok' uyarısıyla gösterilir.
Kapsam: avukatın penceredeki Kriter 1 dönemlerinden esas tarihi bilinenlerin oranı. Pencerede
ölçülen Kriter 1 dönemi olmayan avukatta tarihi bilinmeyen esas da yoktur: kapsam 1.
Gölge modda O, E ve R hesaplanır, puan yayımlanmaz (durum GOLGE_MOD).
"""
import pandas as pd

from avukat_perf.ortak import gun, sutun_kontrol
from avukat_perf.pencere import icinde
from avukat_perf.referans import digerlerinin_orani
from avukat_perf.sure_ozet import golge_kriterleri

GIRDI = ("avukat_kodu", "dosya_no", "kriter", "surec", "brans", "seviye", "dusum",
         "esik_turuncu")
GRUP = ["kriter", "surec", "brans"]
OLCULMEYEN = ("SULH", "IPTAL", "ESAS_ONCEDEN_VAR", "DOSYA_YOK")


def ham_puan(r, sp):
    """Kırpılmamış puan: taban + eğim × (1 − R) (açıklama metni de bunu kullanır)."""
    return sp["taban"] + sp["egim"] * (1.0 - r)


def puan_hesapla(o, e, sp):
    """(R, puan): R = (O + k) ÷ (E + k), puan 0-100 aralığına kırpılır."""
    r = (o + sp["guven_sabiti"]) / (e + sp["guven_sabiti"])
    return r, min(max(ham_puan(r, sp), 0.0), 100.0)


def risk_altindaki(degerlendirmeler, kesit, pencere_ay, haric=None):
    """Düşüm eşiği pencerede olan ve düşüm almış ya da süresinde kapanmış dönemler."""
    sutun_kontrol(degerlendirmeler, GIRDI, "degerlendirmeler")
    esik = gun(degerlendirmeler["esik_turuncu"])
    tablo = degerlendirmeler.assign(esik_turuncu=esik,
                                    dusum=degerlendirmeler["dusum"].astype(bool))
    secili = icinde(esik, kesit, pencere_ay, haric, degerlendirmeler["kriter"]) & (
        tablo["dusum"] | (tablo["seviye"] == "KAPANDI"))
    return tablo[secili].reset_index(drop=True)


def kapsam_hesapla(k1_degerlendirme, kesit, pencere_ay):
    """Avukat başına, penceredeki Kriter 1 dönemlerinden esas tarihi bilinenlerin oranı."""
    atama = gun(k1_degerlendirme["atama_tarihi"])
    neden = k1_degerlendirme["kapsam_disi_nedeni"]
    tablo = k1_degerlendirme[icinde(atama, kesit, pencere_ay) & ~neden.isin(OLCULMEYEN)]
    bilinen = tablo["kapsam_disi_nedeni"] != "ESAS_TARIHI_BILINMIYOR"
    oran = bilinen.groupby(tablo["avukat_kodu"]).mean().rename("kapsam")
    return oran.reset_index()


def _eksik_nedeni(satir, sp, golge):
    if golge:
        return "GOLGE_MOD"
    if round(satir.e, 9) < sp["en_az_beklenen"]:  # E kesirli oranların toplamı
        return "AZ_BEKLENEN"
    if satir.kapsam < sp["en_az_kapsam"]:
        return "KAPSAM_DUSUK"
    return None


def puanla(degerlendirmeler, kapsam, kesit, params, haric=None):
    """Avukat başına O, E, R, kapsam, puan, durum ve yeterli. kapsam: avukat_kodu, kapsam.

    haric: gölge gecelerinin kapsadığı gün aralıkları; o günlerdeki eşikler risk dönemine girmez.
    """
    sp = params["sure_puani"]
    risk = risk_altindaki(degerlendirmeler, kesit, sp["pencere_ay"], haric)
    risk = risk.assign(_bir=1.0, _dusum=risk["dusum"].astype(float))
    risk = risk.assign(diger_orani=digerlerinin_orani(risk, [GRUP, GRUP[:2]], "_dusum", "_bir",
                                                      False))
    tablo = risk.groupby("avukat_kodu").agg(
        risk_donemi=("dusum", "size"), risk_dosya=("dosya_no", "nunique"), o=("dusum", "sum"),
        e=("diger_orani", "sum"))
    tablo = tablo.reset_index().merge(kapsam[["avukat_kodu", "kapsam"]], on="avukat_kodu",
                                      how="left")
    tablo["kapsam"] = tablo["kapsam"].fillna(1.0)  # pencerede ölçülen Kriter 1 dönemi yok
    tablo["o"] = tablo["o"].astype(int)
    golge = any(golge_kriterleri(params).values())  # bir kriter gölgedeyse puan yayımlanmaz
    satirlar = []
    for satir in tablo.itertuples():
        r, puan = puan_hesapla(satir.o, satir.e, sp)
        neden = _eksik_nedeni(satir, sp, golge)
        satirlar.append((r, None if neden else puan, neden))
    ek = pd.DataFrame(satirlar, columns=["r", "puan", "eksik_nedeni"], index=tablo.index)
    tablo = pd.concat([tablo, ek.astype({"r": float, "puan": float})], axis=1)
    durum = tablo["eksik_nedeni"].map({"GOLGE_MOD": "GOLGE_MOD"}).fillna("VERI_YETERSIZ")
    return tablo.assign(durum=durum.where(tablo["eksik_nedeni"].notna(), "GECERLI"),
                        yeterli=tablo["risk_dosya"] >= sp["yeterli_dosya"])
