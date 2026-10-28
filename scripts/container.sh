#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
image=pi4-xen-build:scarthgap
docker_cmd=(docker)
if [[ -n ${CODEX_PROXY_CERT:-} ]]; then
    docker_cmd=(env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock)
fi
action=${1:-shell}
shift || true
if [[ $action == build-container ]]; then
    args=()
    ca_bundle=${PI4_XEN_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}
    [[ -r $ca_bundle ]] || {
        printf 'Set PI4_XEN_CA_BUNDLE to a readable combined CA bundle.\n' >&2
        exit 1
    }
    args+=(--secret "id=ca_bundle,src=$ca_bundle")
    exec "${docker_cmd[@]}" build "${args[@]}" -t "$image" "$project_dir/container"
fi
args=(--rm --user "$(id -u):$(id -g)" --mount "type=bind,src=$project_dir,dst=/work" --workdir /work)
if [[ -n ${CODEX_PROXY_CERT:-} ]]; then
    args+=(--mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/host-ca-bundle.pem,readonly
        -e SSL_CERT_FILE=/run/host-ca-bundle.pem -e GIT_SSL_CAINFO=/run/host-ca-bundle.pem
        -e REQUESTS_CA_BUNDLE=/run/host-ca-bundle.pem -e CURL_CA_BUNDLE=/run/host-ca-bundle.pem)
fi
if [[ $action == shell ]]; then
    [[ -t 0 ]] && args+=(-it)
    exec "${docker_cmd[@]}" run "${args[@]}" "$image" bash
fi
exec "${docker_cmd[@]}" run "${args[@]}" "$image" /work/scripts/build.sh "$action" "$@"
