#!/usr/bin/env bash
set -euo pipefail
cd /work
action=${1:-build}
shift || true
mkdir -p local/logs
log_file="/work/local/logs/${action}-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
exec > >(tee "$log_file") 2>&1
trap 'rc=$?; printf "COMMAND_EXIT_STATUS=%s\n" "$rc"; exit "$rc"' EXIT
export BB_ENV_PASSTHROUGH_ADDITIONS="${BB_ENV_PASSTHROUGH_ADDITIONS:-} HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy SSL_CERT_FILE GIT_SSL_CAINFO REQUESTS_CA_BUNDLE CURL_CA_BUNDLE WGETRC"
if [[ -n ${SSL_CERT_FILE:-} ]]; then
    export WGETRC=/tmp/pi4-xen-wgetrc
    printf 'ca_certificate = %s\n' "$SSL_CERT_FILE" > "$WGETRC"
fi
if [[ $action == test ]]; then
    python3 -m unittest discover -s tests -v
    exit 0
fi
python3 scripts/configure-access.py
python3 scripts/bootstrap.py
python3 scripts/init-build.py
set +u
source .cache/sources/poky/oe-init-build-env /work/build
set -u
case "$action" in
    prepare) bitbake-layers show-layers; bitbake-layers show-recipes xen xen-tools linux-yocto u-boot ;;
    parse) bitbake -p ;;
    plan) bitbake -g pi4-xen-dom0-image ;;
    build)
        bitbake pi4-xen-dom0-image
        /work/scripts/export-image.py
        ;;
    bitbake) bitbake "$@" ;;
    *) printf 'Unknown action: %s\n' "$action" >&2; exit 2 ;;
esac
