"""API yanıtında yol izleme, kayıt listesinin çıkarılması ve sayfalama adımı.

Yol noktalı metin ("data.items") ya da parça listesidir (["sonuc.v2"]: anahtar nokta
içerirse); sayısal parça liste indeksidir ("results.0.rows"). Yanıtta olmayan yol ile değeri
null olan yol ayrılır: kayıt yolu bulunamazsa okuma sessizce boş dönmez, hata verir (yanlış
yol boş görüntü sayılırsa gözlem tabanı bozulurdu). Hata iletileri yalnız yol adını içerir.
İmleç kipinde imleç değeri sorgu parametresi olarak gönderilir; yanıtta tam adres olarak gelen
sonraki bağlantı (ör. OData nextLink) desteklenmez.
"""


def yol_izle(veri, yol):
    """(bulundu, değer): yol yanıtta var mı ve değeri."""
    parcalar = yol if isinstance(yol, list) else [p for p in str(yol or "").split(".") if p]
    for parca in parcalar:
        if isinstance(veri, dict) and parca in veri:
            veri = veri[parca]
        elif isinstance(veri, list) and str(parca).isdigit() and int(parca) < len(veri):
            veri = veri[int(parca)]
        else:
            return False, None
    return True, veri


def kayitlar(yanit, kayit_yolu):
    """Yanıttaki kayıt listesi. Yol boşsa yanıtın kendisi liste olmalı; değer null ise boş."""
    if not kayit_yolu:
        if isinstance(yanit, list):
            return yanit
        raise ValueError("yanıt liste değil; kaynak ayarında kayit_yolu verilmeli")
    bulundu, deger = yol_izle(yanit, kayit_yolu)
    if not bulundu:
        raise ValueError("kayit_yolu yanıtta yok: {}".format(kayit_yolu))
    if deger is None:
        return []
    if not isinstance(deger, list):
        raise ValueError("kayit_yolu bir liste göstermiyor: {}".format(kayit_yolu))
    return deger


def sonraki_imlec(yanit, sayfalama, sayfa_kayit):
    """Sonraki sayfanın imleci; yoksa None (son sayfa).

    Bazı API'ler son sayfada imleç alanını hiç yazmaz; bu son sayfa sayılır. Ama sayfa dolu
    geldiyse (boyut kadar kayıt) alanın olmaması ayar hatasıdır: okuma ilk sayfada bitip
    veriyi sessizce keserdi.
    """
    bulundu, imlec = yol_izle(yanit, sayfalama["sonraki_imlec_yolu"])
    if not bulundu and sayfalama.get("boyut") and len(sayfa_kayit) >= sayfalama["boyut"]:
        raise ValueError("sonraki_imlec_yolu dolu sayfada yanıtta yok: {}".format(
            sayfalama["sonraki_imlec_yolu"]))
    return imlec or None


def toplam(yanit, sayfalama):
    """sayfalama.toplam_yolu verilmişse yanıttaki toplam kayıt sayısı; değilse None."""
    if not sayfalama.get("toplam_yolu"):
        return None
    bulundu, deger = yol_izle(yanit, sayfalama["toplam_yolu"])
    if not bulundu or deger is None:
        raise ValueError("toplam_yolu yanıtta yok: {}".format(sayfalama["toplam_yolu"]))
    return int(deger)


def sayfa_sorgusu(sayfalama, sorgu, sayfa, ofset, imlec):
    tur = sayfalama["tur"]
    if tur == "sayfa":
        sorgu.update({sayfalama["sayfa_parametresi"]: sayfa,
                      sayfalama["boyut_parametresi"]: sayfalama.get("boyut", 1000)})
    elif tur == "ofset":
        sorgu.update({sayfalama["ofset_parametresi"]: ofset,
                      sayfalama["boyut_parametresi"]: sayfalama.get("boyut", 1000)})
    elif tur == "imlec" and imlec:
        sorgu[sayfalama["imlec_parametresi"]] = imlec
    return sorgu


def bitti(sayfalama, parca, imlec, okunan, toplam):
    tur, durdur = sayfalama["tur"], sayfalama.get("toplam_ile_dur") and toplam is not None
    return tur == "yok" or not parca or (tur == "imlec" and not imlec) or bool(
        durdur and okunan >= toplam)
