"""Veri hattı: entegrasyon (kaynak okuma, API), ham arşiv, çalışma kaydı ve akışlar.

Puan formülleri ve iş kuralları avukat_perf kitaplığındadır. hesap.py yalnız hangi sonucun
hangi koşulda üretileceğini (kaynak var mı, teyit edildi mi, gölge mod) ve hesap sırasını
belirler; bu koşullar da hesap sürümüne girer. Ortam (yerel ya da Dataiku) dışarıdan verilir,
böylece aynı akış iki ortamda da çalışır.
"""
