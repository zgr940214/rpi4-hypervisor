#!/usr/bin/env bash
# Validate only the project's self-built Pi4 Yocto card image in QEMU virt.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"
action=${1:-validate}
shift || true
case "$action" in
    prepare|validate) ;;
    *) printf 'Usage: %s [prepare|validate] [runner arguments]\n' "$0" >&2; exit 2 ;;
esac
if [[ ! -f artifacts/pi4-xen-dom0-guest1.img ]]; then
    printf 'Missing self-built Pi4 image. Run ./scripts/container.sh build first.\n' >&2
    exit 1
fi
mkdir -p local/qemu-yocto/logs
docker_cmd=(docker)
if [[ -n ${CODEX_PROXY_CERT:-} ]]; then
    docker_cmd=(env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock)
fi
runtime=(--rm --user "$(id -u):$(id -g)" --mount "type=bind,src=$project_dir,dst=/work" --workdir /work)
ca_bundle=${PI4_XEN_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}
logged() {
    local logfile=$1
    shift
    set +e
    "$@" 2>&1 | tee "$logfile"
    local rc=${PIPESTATUS[0]}
    set -e
    printf 'COMMAND_EXIT_STATUS=%s\n' "$rc" | tee -a "$logfile"
    return "$rc"
}
if ! "${docker_cmd[@]}" image inspect pi4-xen-qemu:4.19 >/dev/null 2>&1; then
    ./scripts/container.sh build-container
    logged local/qemu-yocto/logs/container-build.log "${docker_cmd[@]}" build \
        --secret "id=ca_bundle,src=$ca_bundle" -f container/qemu.Dockerfile \
        -t pi4-xen-qemu:4.19 container
fi
# The Docker image supplies host emulation/inspection tools only. Xen, Linux,
# Dom0 and guest1 all come from the verified Yocto card image below.
logged local/qemu-yocto/logs/prepare.log "${docker_cmd[@]}" run "${runtime[@]}" \
    pi4-xen-qemu:4.19 python3 /work/scripts/qemu/prepare-yocto.py
[[ $action == prepare ]] && exit 0
python3 scripts/configure-access.py
result_dir="local/qemu-yocto/results/$(date -u +%Y%m%dT%H%M%SZ)"
logged local/qemu-yocto/logs/validation.log "${docker_cmd[@]}" run "${runtime[@]}" \
    pi4-xen-qemu:4.19 python3 /work/scripts/qemu/run.py \
    "$@" \
    --yocto-provenance /work/local/qemu-yocto/provenance.json \
    --xen /work/local/qemu-yocto/xen --kernel /work/local/qemu-yocto/Image \
    --rootfs /work/artifacts/pi4-xen-dom0-guest1.img --initrd '' \
    --dom0-args 'console=hvc0 earlycon=xenboot root=/dev/vda2 rw rootwait net.ifnames=0' \
    --dom0-manual-login \
    --prepare-command 'systemctl start pi4-xen-ready.service && systemctl is-active --quiet pi4-xen-ready.service' \
    --output "/work/$result_dir"
