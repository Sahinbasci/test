"""Kriter 2: Dava Açma Süresi (dava takip sistemine bağlı). Atama dönemi başına seviye, düşüm
ve süre. Süreç tablosu dosya başınadır. surec_turu ITIRAZ (itiraz nedeniyle durdurma) ya da
ARABULUCULUK ise kriter uygulanır; DOGRUDAN_DAVA, KESINLESTI ve boş kapsam dışıdır.
Başlangıç, süreç başlangıcı ile atama tarihinin büyüğüdür: yeniden atamada süre yeni
atamadan başlar. Bitiş sırasıyla: dava esas kaydının ilk girişi (KAPANDI), atamanın bitişi
(SONLANDI), koşulun kalktığı gün (KOSUL_DISI: dosya kapandı; bkz. hazirlik.kosul_goruntusu),
kesit. Koşul bugün sağlanmıyor ve kalktığı gün bilinmiyorsa ya da arşiv öncesinde kalkmışsa
(isteğe bağlı kosul_gorulme; ilk kalkış kalıcıdır) dönem kapsam dışıdır. Bugünkü kod kapanış
dışı başka bir kodsa (iade, atama bekleyen) bu yalnız sürmekte olan dönemi kapsam dışı yapar:
sona ermiş dönem bitişine kadar ölçülür, oluşmuş düşüm korunur. Kalktığı gün kesitten sonraysa
koşul kesitte sağlanıyordu (geçmiş kesit aynı sonucu verir).
Dava kaydı var ama ilk giriş günü bilinmiyorsa (arşiv öncesi; isteğe bağlı dava_gorulme) dönem
ölçülmez: DAVA_TARIHI_BILINMIYOR, kayıt atamadan önce de görülmüşse DAVA_ONCEDEN_VAR. Eşikler
takvim ayıdır; bayrak, düşüm ve KIRMIZI kuralı Kriter 1 ile ortaktır (avukat_perf/bayrak.py).
"""
import pandas as pd

from avukat_perf import atama as atama_gecmisi
from avukat_perf import bayrak
from avukat_perf.ortak import anahtar_kontrol, gun, sutun_kontrol, tek_gun

SUREC_SUTUNLARI = ("dosya_no", "brans", "surec_turu", "baslangic_tarihi", "dava_ilk_giris",
                   "kosul_kayip_tarihi", "rucu_kodu", "acik_bakiye")
ARABULUCULUK = "ARABULUCULUK"
UYGULANAN = ("ITIRAZ", ARABULUCULUK)
SURECLER = UYGULANAN + ("DOGRUDAN_DAVA", "KESINLESTI")  # bilinen süreç türleri (kalite kapısı)
TARIHLER = ("baslangic_tarihi", "dava_ilk_giris", "kosul_kayip_tarihi")
GORULME = ("dava_gorulme", "kosul_gorulme")  # isteğe bağlı: günü bilinmeyen kaydın görülmesi
SONUC_TARIHLERI = ("surec_baslangici", "dusum_tarihi", "olcum_sonu", "esik_sari",
                   "esik_turuncu", "esik_kirmizi")
SONUC_SUTUNLARI = ("kapsam_disi_nedeni", "seviye", "en_yuksek_seviye", "dusum",
                   "sure_gun") + SONUC_TARIHLERI
ONCE_BITERSE = {"KAPANDI": "DAVA_ONCEDEN_VAR", "SONLANDI": "SUREC_ATAMA_DISI",
                "KOSUL_DISI": "KOSUL_SAGLANMIYOR"}


def kosul_kalkti(rucu_kodu, acik_bakiye, kod):
    """Kriter 2 koşulu bugün sağlanmıyor mu: rücu kodu başka ya da açık bakiye sıfır ya da eksi.
    Boş bakiye bilinmez; koşul kalkmış sayılmaz (son bilinen durum sürer)."""
    return rucu_kodu != kod or bool(pd.notna(acik_bakiye) and acik_bakiye <= 0)


def _sonlanan_baska_kod(kayit, k2):
    """Dönem sona ermiş, dosyanın bugünkü kodu kapanış dışı başka kod (iade, atama bekleyen)."""
    kod = kayit["rucu_kodu"]
    return pd.notna(kayit["bitis_tarihi"]) and isinstance(kod, str) and \
        kod != k2["rucu_kodu"] and kod not in k2["kapanis_kodlari"]


def _baslangic_nedeni(kayit, tarih, k2):
    """Süreç ve koşul bakımından kapsam dışı nedeni; kapsamdaysa None."""
    if kayit["surec_turu"] not in UYGULANAN:
        return "SUREC_" + (kayit["surec_turu"] if isinstance(kayit["surec_turu"], str)
                           else "YOK")
    if tarih["baslangic_tarihi"] is None:
        return "BASLANGIC_YOK"
    kosul_simdi = not kosul_kalkti(kayit["rucu_kodu"], kayit["acik_bakiye"], k2["rucu_kodu"]) \
        or _sonlanan_baska_kod(kayit, k2)
    if (pd.isna(kayit["kosul_kayip_tarihi"]) and not kosul_simdi) or \
            pd.notna(kayit["kosul_gorulme"]):
        return "KOSUL_SAGLANMIYOR"
    return None


def _dava_nedeni(kayit, tarih):
    """Dava kaydı var ama ilk giriş günü bilinmiyorsa kapsam dışı nedeni; yoksa None."""
    gorulme = kayit["dava_gorulme"]
    if tarih["dava_ilk_giris"] is not None or pd.isna(gorulme):
        return None
    return "DAVA_ONCEDEN_VAR" if gorulme < kayit["atama_tarihi"] else "DAVA_TARIHI_BILINMIYOR"


def _donem_sonucu(kayit, kesit, k2):
    """Tek atama dönemi için SONUC_SUTUNLARI değerleri."""
    sonuc = dict.fromkeys(SONUC_SUTUNLARI)
    tarih = {ad: kayit[ad] if kayit[ad] <= kesit else None
             for ad in TARIHLER + ("bitis_tarihi",)}
    neden = _baslangic_nedeni(kayit, tarih, k2) or _dava_nedeni(kayit, tarih)
    bas = None if neden else max(tarih["baslangic_tarihi"], kayit["atama_tarihi"])
    adaylar = [(tarih["dava_ilk_giris"], "KAPANDI"), (tarih["bitis_tarihi"], "SONLANDI"),
               (tarih["kosul_kayip_tarihi"], "KOSUL_DISI")]
    adaylar = [aday for aday in adaylar if aday[0] is not None]
    son, kapanis = min(adaylar, key=lambda aday: aday[0]) if adaylar else (kesit, None)
    if neden is None and son < bas:
        neden = ONCE_BITERSE[kapanis]
    if neden is not None:
        sonuc.update(kapsam_disi_nedeni=neden, seviye="KAPSAM_DISI", dusum=False)
        return sonuc
    turuncu = bas + pd.DateOffset(months=k2["dusum_ay"])
    esik = bayrak.esikler(bas + pd.DateOffset(months=k2["uyari_ay"]), turuncu)
    seviye, en_yuksek, dusum = bayrak.degerlendir(esik, son, kapanis,
                                                  k2["sonlanan_atamada_dusum_korunur"])
    sonuc.update(seviye=seviye, en_yuksek_seviye=en_yuksek,
                 dusum=dusum, dusum_tarihi=turuncu if dusum else None,
                 sure_gun=(son - bas).days, surec_baslangici=bas, olcum_sonu=son,
                 esik_sari=esik["SARI"], esik_turuncu=turuncu, esik_kirmizi=esik["KIRMIZI"])
    return sonuc


def degerlendir(atamalar, surecler, kesit, params):
    """Kesit tarihinde, süreci olan dosyaların her kapsamdaki atama dönemi için sonuç.

    atamalar: atama.SUTUNLAR; surecler: SUREC_SUTUNLARI, dosya başına bir satır.
    """
    sutun_kontrol(surecler, SUREC_SUTUNLARI, "surecler")
    anahtar_kontrol(surecler, ("dosya_no",), "surecler")
    kesit = tek_gun(kesit)
    donem = atama_gecmisi.donemler(atamalar, kesit)
    bos = pd.Series(pd.NaT, index=surecler.index, dtype="datetime64[ns]")
    hazir = surecler.assign(acik_bakiye=surecler["acik_bakiye"].astype(float),
                            **{ad: gun(surecler[ad]) if ad in surecler.columns else bos
                               for ad in GORULME + TARIHLER})
    tablo = donem.merge(hazir, on="dosya_no").reset_index(drop=True)
    satirlar = [_donem_sonucu(kayit, kesit, params["kriter2"])
                for kayit in tablo.to_dict("records")]
    sonuc = pd.DataFrame(satirlar, columns=list(SONUC_SUTUNLARI))
    for sutun in SONUC_TARIHLERI:
        sonuc[sutun] = pd.to_datetime(sonuc[sutun])
    sonuc["dusum"] = sonuc["dusum"].astype(bool)
    return pd.concat([tablo.drop(columns=list(GORULME)), sonuc], axis=1)
