#!/usr/bin/env bash
# Build and execute a real ARM64 Xen integration test on QEMU virt.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"
action=${1:-validate}
shift || true
mkdir -p local/qemu/logs
docker_cmd=(docker)
if [[ -n ${CODEX_PROXY_CERT:-} ]]; then
    docker_cmd=(env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock)
fi
ca_bundle=${PI4_XEN_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}
runtime=(--rm --user "$(id -u):$(id -g)" --mount "type=bind,src=$project_dir,dst=/work" --workdir /work)
if [[ -r $ca_bundle ]]; then
    runtime+=(--mount "type=bind,src=$ca_bundle,dst=/run/host-ca.pem,readonly" -e GIT_SSL_CAINFO=/run/host-ca.pem)
fi
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
prepare() {
    ./scripts/container.sh build-container
    logged local/qemu/logs/container-build.log "${docker_cmd[@]}" build \
        --secret "id=ca_bundle,src=$ca_bundle" -f container/qemu.Dockerfile \
        -t pi4-xen-qemu:4.19 container
    python3 scripts/configure-access.py
    logged local/qemu/logs/xen-build.log "${docker_cmd[@]}" run "${runtime[@]}" \
        pi4-xen-qemu:4.19 /work/scripts/qemu/build-xen.sh
    logged local/qemu/logs/rootfs-build.log ./scripts/qemu/rootfs.sh prepare
    logged local/qemu/logs/rootfs-export.log ./scripts/qemu/export-rootfs.sh
}
case "$action" in
    prepare) prepare ;;
    validate)
        if [[ ! -f local/qemu/dom0.ext4 || ! -f local/qemu/xen ]]; then
            prepare
        fi
        result_dir="local/qemu/results/$(date -u +%Y%m%dT%H%M%SZ)"
        logged local/qemu/logs/validation.log "${docker_cmd[@]}" run "${runtime[@]}" \
            pi4-xen-qemu:4.19 python3 /work/scripts/qemu/run.py \
            --output "/work/$result_dir" "$@"
        printf 'QEMU evidence: %s/%s\n' "$project_dir" "$result_dir"
        ;;
    *) printf 'Usage: %s [prepare|validate] [runner arguments]\n' "$0" >&2; exit 2 ;;
esac
