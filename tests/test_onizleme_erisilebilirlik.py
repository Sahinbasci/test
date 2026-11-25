"""Demo verisi görünür biçimde ayrılır; dar menüde bağlantı adları korunur."""
import os
from html.parser import HTMLParser

from araclar import onizleme
from yardimci import KOK


class _Menu(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.baglantilar = []

    def handle_starttag(self, etiket, nitelikler):
        nitelik = dict(nitelikler)
        if etiket == "a" and "menu-oge" in nitelik.get("class", "").split():
            self.baglantilar.append(nitelik)


def test_dar_ekranda_gizlenen_yazidan_bagimsiz_menu_adi():
    cozum = _Menu()
    with open(os.path.join(KOK, "dataiku", "webapp", "index.html"),
              encoding="utf-8") as dosya:
        cozum.feed(dosya.read())
    assert len(cozum.baglantilar) == 5
    assert all(a.get("aria-label", "").strip() for a in cozum.baglantilar)
    assert len({a["aria-label"] for a in cozum.baglantilar}) == 5


def test_onizleme_govdesi_sentetik_oldugunu_bildirir():
    kod, tur, veri = onizleme.yanit("/", {}, {})
    metin = veri.decode("utf-8").split("<body>", 1)[1]
    assert kod == 200 and tur.startswith("text/html")
    assert "Sentetik test verisi" in metin
    assert "resmî performans değerlendirmesinde kullanılmaz" in metin
