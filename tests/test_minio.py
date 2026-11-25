"""MinIO kurulum betiği (minio/kurulum.sh) sahte bir mc istemcisiyle çalıştırılır: hangi komutların
hangi sırayla çağrıldığı kayda yazılır. Gerçek MinIO davranışı kurulumda görülür."""
import os
import shutil
import subprocess
import tempfile

from yardimci import KOK

BETIK = os.path.join(KOK, "minio", "kurulum.sh")
SAHTE_MC = """#!/bin/sh
echo "$*" >> "$MC_KAYIT"
case "$*" in
  "admin user info"*) [ -n "$SAHTE_BAGLI" ] && echo "PolicyName: avukat-perf-dataiku"; exit 0 ;;
  "admin policy attach --help"|"admin policy create --help") exit 0 ;;
  "admin policy attach"*) [ -n "$SAHTE_BAGLI" ] && { echo "zaten bagli" >&2; exit 1; }; exit 0 ;;
  "admin policy set"*) echo "bu mc surumunde yok" >&2; exit 1 ;;
esac
exit 0
"""


def _calistir(**ortam):
    """(dönüş kodu, mc çağrıları, standart çıktı)."""
    klasor = tempfile.mkdtemp()
    try:
        mc = os.path.join(klasor, "mc")
        with open(mc, "w", encoding="utf-8") as dosya:
            dosya.write(SAHTE_MC)
        os.chmod(mc, 0o755)
        kayit = os.path.join(klasor, "kayit.txt")
        degisken = dict(os.environ, PATH=klasor + os.pathsep + os.environ.get("PATH", ""),
                        MC_ALIAS="kurum", MC_KAYIT=kayit, **ortam)
        sonuc = subprocess.run(["sh", BETIK], env=degisken, capture_output=True, timeout=60)
        with open(kayit, encoding="utf-8") as dosya:
            return sonuc.returncode, dosya.read().splitlines(), sonuc.stdout.decode("utf-8")
    finally:
        shutil.rmtree(klasor)


def test_eski_surum_suresi_verilirse_islenmis_kovaya_yasam_dongusu_kurulur():
    kod, cagrilar, cikti = _calistir(ESKI_SURUM_GUN="30")
    assert kod == 0, cikti
    assert ("ilm rule add --noncurrent-expire-days 30 kurum/avukat-perf-islenmis"
            in cagrilar)
    kod, cagrilar, cikti = _calistir()
    assert kod == 0 and not [c for c in cagrilar if c.startswith("ilm")]
    assert "ESKI_SURUM_GUN verilmedi" in cikti


def test_ikinci_calistirmada_bagli_politika_yeniden_baglanmaz():
    """MinIO bağlı politikayı yeniden bağlarken hata döner; betik denetim adımına gelmeden
    durmamalı. İlk kurulumda politika bağlanır."""
    kod, cagrilar, cikti = _calistir(SAHTE_BAGLI="1")
    assert kod == 0 and "Kurulum tamam" in cikti, cikti
    assert not [c for c in cagrilar if c.startswith("admin policy attach kurum")]
    kod, cagrilar, _ = _calistir()
    assert kod == 0
    assert "admin policy attach kurum avukat-perf-dataiku --user dataiku-avukat-perf" in cagrilar
    with open(BETIK, encoding="utf-8") as dosya:  # hata iletisi gizlenmez
        assert not [satir for satir in dosya if "policy" in satir and "2>/dev/null" in satir
                    and "--help" not in satir]
