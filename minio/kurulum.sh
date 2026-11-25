#!/bin/sh
# MinIO kova kurulumu (Sözleşmeli Avukat Performans Sistemi).
#
# MinIO'da kod çalışmaz; bu dosya yalnız kovaları, sürümlemeyi ve Dataiku hizmet hesabının
# yetkisini kurar. Komutları MinIO yöneticisi çalıştırır (mc istemcisi gerekir).
#
# Ön koşul: mc takma adı tanımlı olmalı, ör.
#   mc alias set kurum https://MINIO-ADRESI YONETICI_ERISIM YONETICI_GIZLI
#
# Kullanım:
#   MC_ALIAS=kurum sh kurulum.sh
# İsteğe bağlı değişkenler:
#   KOVA_HAM        ham arşiv kovası          (varsayılan avukat-perf-ham)
#   KOVA_ISLENMIS   işlenmiş veri kovası      (varsayılan avukat-perf-islenmis)
#   HIZMET_HESABI   Dataiku'nun kullanacağı MinIO kullanıcısı (varsayılan dataiku-avukat-perf)
#   KILIT_GUN       ham kovada değiştirilemezlik (object lock) saklama süresi, gün.
#                   Boşsa kilit kurulmaz. Süre Hukuk ve bilgi güvenliği kararıdır; tahmin
#                   edilmez. Kilit yalnız kova ilk oluşturulurken açılabilir.
#   ESKI_SURUM_GUN  işlenmiş kovada eski (güncel olmayan) nesne sürümlerinin saklama süresi,
#                   gün. Dataiku veri kümelerini her gece baştan yazar; sürümleme açık kovada
#                   her gecenin kopyası eski sürüm olarak kalır. Boşsa kural kurulmaz ve eski
#                   sürümler süresiz birikir (uyarı yazılır). Süre saklama politikası kararıdır.
set -eu

ALIAS="${MC_ALIAS:?MC_ALIAS verilmedi (mc alias set ile tanımlanan ad)}"
KOVA_HAM="${KOVA_HAM:-avukat-perf-ham}"
KOVA_ISLENMIS="${KOVA_ISLENMIS:-avukat-perf-islenmis}"
HIZMET_HESABI="${HIZMET_HESABI:-dataiku-avukat-perf}"
KILIT_GUN="${KILIT_GUN:-}"
ESKI_SURUM_GUN="${ESKI_SURUM_GUN:-}"
POLITIKA_ADI="avukat-perf-dataiku"
DIZIN="$(cd "$(dirname "$0")" && pwd)"

echo "1/5 Kovalar"
if [ -n "$KILIT_GUN" ]; then
  mc mb --ignore-existing --with-lock "$ALIAS/$KOVA_HAM"
  mc retention set --default GOVERNANCE "${KILIT_GUN}d" "$ALIAS/$KOVA_HAM"
else
  mc mb --ignore-existing "$ALIAS/$KOVA_HAM"
fi
mc mb --ignore-existing "$ALIAS/$KOVA_ISLENMIS"

echo "2/5 Sürümleme (yanlışlıkla silme ve üzerine yazmaya karşı)"
mc version enable "$ALIAS/$KOVA_HAM"
mc version enable "$ALIAS/$KOVA_ISLENMIS"

echo "3/5 İşlenmiş kovada eski sürümlerin saklama süresi"
if [ -n "$ESKI_SURUM_GUN" ]; then
  mc ilm rule add --noncurrent-expire-days "$ESKI_SURUM_GUN" "$ALIAS/$KOVA_ISLENMIS"
else
  echo "UYARI: ESKI_SURUM_GUN verilmedi; işlenmiş kovada eski sürümler süresiz birikir."
fi

echo "4/5 Erişim politikası"
POLITIKA_DOSYASI="$(mktemp)"
sed -e "s/avukat-perf-ham/$KOVA_HAM/g" -e "s/avukat-perf-islenmis/$KOVA_ISLENMIS/g" \
  "$DIZIN/politika_dataiku.json" > "$POLITIKA_DOSYASI"
# mc RELEASE.2023-03 ve sonrası "policy create", öncesi "policy add" kullanır. Eski komuta
# yalnız yeni komut bu mc sürümünde yoksa düşülür; hata iletisi gizlenmez.
if mc admin policy create --help >/dev/null 2>&1; then
  mc admin policy create "$ALIAS" "$POLITIKA_ADI" "$POLITIKA_DOSYASI"
else
  mc admin policy add "$ALIAS" "$POLITIKA_ADI" "$POLITIKA_DOSYASI"
fi
rm -f "$POLITIKA_DOSYASI"

echo "5/5 Hizmet hesabı"
if mc admin user info "$ALIAS" "$HIZMET_HESABI" >/dev/null 2>&1; then
  echo "kullanıcı zaten var: $HIZMET_HESABI"
else
  echo "Kullanıcı yok. Gizli anahtarı yönetici belirler ve Dataiku bağlantısına girer:"
  echo "  mc admin user add $ALIAS $HIZMET_HESABI <GIZLI_ANAHTAR>"
  echo "Ardından bu betiği yeniden çalıştırın."
  exit 1
fi
# Politika zaten bağlıysa yeniden bağlanmaz (MinIO ikinci bağlamada hata döner, betik dururdu).
if mc admin user info "$ALIAS" "$HIZMET_HESABI" | grep -q "$POLITIKA_ADI"; then
  echo "politika zaten bağlı: $POLITIKA_ADI"
elif mc admin policy attach --help >/dev/null 2>&1; then
  mc admin policy attach "$ALIAS" "$POLITIKA_ADI" --user "$HIZMET_HESABI"
else  # RELEASE.2023-03 öncesi mc
  mc admin policy set "$ALIAS" "$POLITIKA_ADI" "user=$HIZMET_HESABI"
fi

echo "Kurulum tamam. Denetim:"
mc ls "$ALIAS/$KOVA_HAM" "$ALIAS/$KOVA_ISLENMIS"
mc version info "$ALIAS/$KOVA_HAM"
