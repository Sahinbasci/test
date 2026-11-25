"""'Neden bu puanı aldı?' açıklamasının tahsilat satırları: üç bileşen ve birleşimi."""
from avukat_perf.aciklama_bicim import NEDEN, kesin, kirpma, sabit, sayi, sayim
from avukat_perf.tahsilat_puan import ham_puan, olay_puani, yeterli_mi

# Elle hesap ekrandaki sayılarla tutsun: beklenen 4, R 6 ondalık (R'deki 0,00005'lik yuvarlama
# puanda 0,0025 eder, ikinci ondalığı değiştirebilir); formüldeki n kesilmez, ağırlıklar
# yuvarlanmaz.
BILESEN = (("siklik", "Sıklık", "Olgun dosyalarda tahsilat yapılan dosya-ay"),
           ("guncellik", "Güncellik", "Son {} ayda tahsilat yapılan dosya-ay"))


def _olay(s, ad, baslik, kanit, tah):
    gerceklesen, beklenen = getattr(s, ad + "_o"), getattr(s, ad + "_e")
    r = olay_puani(gerceklesen, beklenen, tah)[0]
    k = sabit(tah["olay_guven_sabiti"])
    return [("KANIT", "{}: {} · beklenen: {} (elde tutulan süre × gruptaki diğer "
                     "avukatların tahsilat hızı)".format(
                kanit.format(tah["guncellik_pencere_ay"]), sabit(gerceklesen),
                sayi(beklenen, 4))),
            ("HESAP", "{} puanı: R = ({} + {}) ÷ ({} + {}) = {} → {}{}".format(
                baslik, sabit(gerceklesen), k, sayi(beklenen, 4), k, sayi(r, 6),
                sayi(getattr(s, "puan_" + ad)), kirpma(ham_puan(r, tah))))]


def tahsilat(s, tah):
    """Tahsilat sonuç satırından (sonuc_tahsilat_avukat) açıklama satırları."""
    k, taban, egim = sabit(tah["guven_sabiti"]), tah["taban"], tah["egim"]
    satirlar = [("KANIT", "Olgun dosya (elde tutma payıyla): " + sayim(s.n)),
                ("KANIT", "Gerçekleşen tahsilat: " + sayi(s.gerceklesen) + " TL"),
                ("KANIT", "Beklenen tahsilat: " + sayi(s.beklenen) + " TL")]
    if isinstance(s.eksik_nedeni, str):
        esik = "en az " + sayi(tah["en_az_olgun_dosya"], 0)
        return satirlar + [("ISTISNA", NEDEN[s.eksik_nedeni].format(esik))]
    if not yeterli_mi(s.n, tah):
        satirlar.append(("UYARI", "Yeterli veri yok: olgun dosya {}, en az {} olmalı. Puan az "
                         "veriyle hesaplandı; güven ayarı onu beklenen düzeye yaklaştırır.".format(
                             sayim(s.n), sayi(tah["yeterli_olgun_dosya"], 0))))
    satirlar += [
        ("HESAP", "Gerçekleşen ÷ beklenen = " + sayi(s.oran, 6)),
        ("HESAP", "R = ({n} × {o} + {k}) ÷ ({n} + {k}) = {r}".format(
            n=kesin(s.n), o=sayi(s.oran, 6), k=k, r=sayi(s.r, 6))),
        ("HESAP", "Tutar puanı = {} + {} × (R − 1) = {}{}".format(
            sabit(taban), sabit(egim), sayi(s.puan_tutar), kirpma(ham_puan(s.r, tah))))]
    for ad, baslik, kanit in BILESEN:
        satirlar += _olay(s, ad, baslik, kanit, tah)
    agirlik = tah["bilesen_agirliklari"]
    return satirlar + [("HESAP", "Tahsilat puanı = {} × {} + {} × {} + {} × {} = {}".format(
        sabit(agirlik["tutar"]), sayi(s.puan_tutar), sabit(agirlik["siklik"]),
        sayi(s.puan_siklik), sabit(agirlik["guncellik"]), sayi(s.puan_guncellik), sayi(s.puan)))]
