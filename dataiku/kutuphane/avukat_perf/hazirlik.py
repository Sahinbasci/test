"""Veri hazırlığı: kaynak tablolarından hesap girdilerinin kurulması (hazirlik parametreleri).

atama_donemleri: çekirdek sistemin avukat logundan atama dönemleri. Sulh amaçlı atama avukat
kodu listesinden ya da alan-değer eşleşmesinden tanınır. Bitiş, iptal tarihi ile dosyadaki
sonraki sulh dışı atamanın erkenidir. iptal_yorumu sonraki_atamaya_gore: sonraki atama varsa
YENIDEN_ATAMA, yoksa IADE; hatali_iptal: iptal tarihli her atama IPTAL (kapsam dışı). Kayıtlar
saatiyle sıralanır (aynı gün yeniden atamada dosya sonraki avukattadır), tarihler güne indirilir;
bitişi atama gününde ya da önce olan boş dönem çıkarılır. Aynı avukata kesintisiz yeniden
atamada (ayni_avukata_yeniden_atama) surer: dönem sürer; yeni_donem: yeni dönem açılır.
Geniş biçimli değerlendirme uzun biçime çevrilir. Kriter 2 süreçlerinde boş arabuluculuk
başlangıcı esasın en geç olası ilk giriş günüdür (bkz. gozlem.baslangic_esle).
"""
import pandas as pd

from avukat_perf import gozlem
from avukat_perf.kriter2 import ARABULUCULUK, SUREC_SUTUNLARI

DONEM_SUTUNLARI = ["dosya_no", "avukat_kodu", "atama_tarihi", "bitis_tarihi",
                   "bitis_nedeni", "atama_turu", "atama_ref"]


def atama_donemleri(atama_log, hz):
    """Çekirdek sistemin avukat logundan atama dönemi tablosu."""
    tablo = atama_log.sort_values(["dosya_no", "atama_tarihi", "avukat_kodu", "iptal_tarihi",
                                   "atama_ref"], na_position="last", kind="mergesort")
    tablo = tablo.reset_index(drop=True)
    sulh = tablo["avukat_kodu"].isin(hz["sulh_avukat_kodlari"])
    if hz["sulh_alani"]:
        sulh = sulh | tablo[hz["sulh_alani"]].isin(hz["sulh_degerleri"])
    iptal = tablo["iptal_tarihi"]
    hatali = hz["iptal_yorumu"] == "hatali_iptal"
    # Hatalı girilip iptal edilen atama önceki atamanın dönemini kesmez.
    sayilan = ~sulh & ~(iptal.notna() & hatali)
    sonraki = tablo[sayilan].groupby("dosya_no")["atama_tarihi"].shift(-1).reindex(tablo.index)
    bitis = iptal.where(sonraki.isna() | (iptal.notna() & (iptal <= sonraki)), sonraki)
    if hatali:
        neden = iptal.notna().map({True: "IPTAL", False: "YENIDEN_ATAMA"})
    else:
        neden = sonraki.notna().map({True: "YENIDEN_ATAMA", False: "IADE"})
    tablo = tablo.assign(atama_tarihi=pd.to_datetime(tablo["atama_tarihi"]).dt.normalize(),
                         bitis_tarihi=pd.to_datetime(bitis).dt.normalize(),
                         bitis_nedeni=neden.where(bitis.notna()),
                         atama_turu=sulh.map({True: "SULH", False: "NORMAL"}))
    bos = tablo["bitis_tarihi"].notna() & (tablo["bitis_tarihi"] <= tablo["atama_tarihi"])
    tablo = tablo.loc[~bos, DONEM_SUTUNLARI].reset_index(drop=True)
    return _surdur(tablo) if hz["ayni_avukata_yeniden_atama"] == "surer" else tablo


def _surdur(tablo):
    """Aynı avukata kesintisiz yeniden atamada dönemleri birleştirir; bitiş son kayıttan gelir.
    Sulh dönemi ve hatalı girilip iptal edilen kayıt (IPTAL) araya girmez, dönemi kesmez."""
    normal = tablo[(tablo["atama_turu"] == "NORMAL") & (tablo["bitis_nedeni"] != "IPTAL")]
    # Önceki dönem bu kaydın atamasıyla bitiyorsa (bitiş nedeni o zaman YENIDEN_ATAMA) kesinti yok.
    onceki = normal.groupby("dosya_no")[["avukat_kodu", "bitis_tarihi"]].shift(1)
    surer = ((normal["avukat_kodu"] == onceki["avukat_kodu"])
             & (onceki["bitis_tarihi"] == normal["atama_tarihi"]))
    son = normal.index.to_series().groupby((~surer).cumsum().values).transform("max")[~surer]
    tablo = tablo.copy()
    for sutun in ("bitis_tarihi", "bitis_nedeni"):
        tablo.loc[son.index, sutun] = tablo.loc[son.values, sutun].values
    return tablo.drop(surer[surer].index).reset_index(drop=True)


def degerlendirme_uzun(tablo, alan_kod):
    """Değerlendirme sisteminin geniş tablosunu (alan adı -> alt başlık kodu) uzun biçime alır."""
    if "degerlendiren" not in tablo.columns:
        tablo = tablo.assign(degerlendiren=None)
    kimlik = ["avukat_kodu", "degerlendirme_tarihi", "degerlendiren"]
    uzun = tablo.melt(id_vars=kimlik, value_vars=list(alan_kod), var_name="alt_baslik",
                      value_name="puan")
    return uzun.assign(alt_baslik=uzun["alt_baslik"].map(alan_kod))


def tahsilat_hareketleri(tablo, hz):
    """Yalnız tahsilat sayılan hareket türleri; parametre null ise hepsi."""
    turler = hz["tahsilat_hareket_turleri"]
    return tablo if turler is None else tablo[tablo["hareket_turu"].isin(turler)]


def k1_atamalari(donemler, dosya):
    """Kriter 1 girdisi: atama dönemleri ve dosyanın branşı."""
    return donemler.merge(dosya[["dosya_no", "brans"]], on="dosya_no", how="left")


def k1_esaslari(esas_gozlem):
    """Kriter 1 girdisi: dosya başına esasın ilk giriş günü, tarih bilinmiyor işareti ve
    esasın ilk görüldüğü çekim günü (tarihi bilinmeyen esas en geç o gün vardı)."""
    tablo = gozlem.bos() if esas_gozlem is None else esas_gozlem
    return pd.DataFrame({"dosya_no": tablo["anahtar"].values,
                         "esas_ilk_giris": pd.to_datetime(tablo["ilk_tarih"]).values,
                         "tarih_bilinmiyor": gozlem.tarih_bilinmiyor(tablo).values,
                         "ilk_gorulme": pd.to_datetime(tablo["ilk_gorulme"]).values})


def kosul_goruntusu(dosya, k2):
    """Kapanmış dosyaların koşul gözlemi girdisi (Kriter 2 koşul kaybı, tahsilat kapanışı): kod
    kapanis_kodlari'nda ya da rücu kodunda açık bakiye <= 0. Atama bekleyen ya da iade edilen
    dosyanın başka kodu kapanış değildir."""
    kod = dosya["rucu_kodu"]
    kayip = kod.isin(k2["kapanis_kodlari"]) | ((kod == k2["rucu_kodu"]) &
                                                (dosya["acik_bakiye"] <= 0))
    return pd.DataFrame({"dosya_no": dosya["dosya_no"],
                         "kosul_kayip": kayip.map({True: "EVET", False: None})})


def k2_surecleri(k2_goruntu, dosya, dava_gozlem, kosul_gozlem, esas_gozlem):
    """Kriter 2 girdisi: dosya başına süreç, başlangıç, dava ve koşul kaybı tarihleri.
    dava_gorulme, kosul_gorulme: günü bilinmeyen (arşiv öncesi) kaydın ilk görüldüğü çekim günü."""
    tablo = k2_goruntu[["dosya_no", "surec_turu", "baslangic_tarihi"]].merge(
        dosya[["dosya_no", "brans", "rucu_kodu", "acik_bakiye"]], on="dosya_no", how="left")
    tablo["dava_ilk_giris"] = tablo["dosya_no"].map(gozlem.tarih_esle(dava_gozlem))
    tablo["dava_gorulme"] = tablo["dosya_no"].map(gozlem.bilinmeyen_esle(dava_gozlem))
    tablo["kosul_kayip_tarihi"] = tablo["dosya_no"].map(gozlem.tarih_esle(kosul_gozlem))
    tablo["kosul_gorulme"] = tablo["dosya_no"].map(gozlem.bilinmeyen_esle(kosul_gozlem))
    bos_baslangic = (tablo["surec_turu"] == ARABULUCULUK) & tablo["baslangic_tarihi"].isna()
    esas = tablo["dosya_no"].map(gozlem.baslangic_esle(esas_gozlem))
    tablo["baslangic_tarihi"] = pd.to_datetime(tablo["baslangic_tarihi"]).where(
        ~bos_baslangic, esas)
    return tablo[list(SUREC_SUTUNLARI) + ["dava_gorulme", "kosul_gorulme"]]
