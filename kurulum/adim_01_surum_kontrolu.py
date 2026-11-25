"""Kurulum adım 1: sürüm ve ortam kontrolü.

Projede yeni bir Python not defterinin ilk hücresine yapıştırıp çalıştırın. Çıktıda veri yoktur;
yalnız sürüm ve ayar bilgisi vardır. Python 3.7 ya da üstü, pandas 1.x ya da 2.x gerekir.
"kütüphane API: var" ise kütüphane 2. adımdaki paketlerle kurulabilir.
"""
import sys

import dataiku
import numpy
import pandas

print("python", sys.version.split()[0])
print("pandas", pandas.__version__, "numpy", numpy.__version__)
try:
    import flask
    print("flask", getattr(flask, "__version__", "?"))
except Exception as hata:  # web uygulamasının arka ucu Flask ister
    print("flask yok:", type(hata).__name__)
istemci = dataiku.api_client()
proje = istemci.get_default_project()
print("proje", proje.project_key)
print("kütüphane API:", "var" if hasattr(proje, "get_library") else "yok")
try:
    print("dss", istemci.get_instance_info().raw.get("dssVersion"))
except Exception as hata:
    print("dss sürümü okunamadı:", type(hata).__name__)
try:
    baglantilar = istemci.list_connections()
    ogeler = (baglantilar.items() if isinstance(baglantilar, dict)
              else [(getattr(oge, "name", "?"), oge) for oge in baglantilar])
    for ad, tanim in ogeler:
        tur = tanim.get("type") if isinstance(tanim, dict) else getattr(tanim, "type", "?")
        if tur in ("Filesystem", "S3"):
            print("bağlantı:", ad, tur)
except Exception as hata:
    print("bağlantı listesi okunamadı (yönetici yetkisi gerekebilir):", type(hata).__name__)
