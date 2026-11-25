"""Performans bilgisi içeren API yanıtları ortak HTTP önbelleğine bırakılmaz."""
from test_backend_onbellek import _arka_uc
from yardimci import params_yukle


def test_api_basarili_ve_hatali_yanitlari_http_onbellegine_girmez():
    alan = _arka_uc()
    alan["_veri"] = lambda: ({}, params_yukle())
    istemci = alan["app"].test_client()
    for yol, kod in (("/api/yenile", 200), ("/api/sayfa?ad=gecersiz", 400)):
        yanit = istemci.get(yol)
        assert yanit.status_code == kod
        assert yanit.headers.get("Cache-Control") == "no-store"
