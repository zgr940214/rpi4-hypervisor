#!/bin/sh
set -eu
parser_libpath=
for candidate in /work/build/tmp/sysroots-components/cortexa72/*/usr/lib /work/build/tmp/sysroots-components/cortexa72/*/lib; do
    test -d "$candidate" || continue
    parser_libpath="${parser_libpath}${parser_libpath:+:}${candidate}"
done
loader=/work/build/tmp/sysroots-components/cortexa72/glibc/usr/lib/ld-linux-aarch64.so.1
probe() {
    printf '\nINPUT=%s\n' "$1"
    set +e
    qemu-aarch64-static "$loader" --library-path "$parser_libpath" /probe/probe "$1"
    probe_status=$?
    set -e
    printf 'PROCESS_EXIT=%s\n' "$probe_status"
    return "$probe_status"
}
if probe 'target=/var/lib/xen/images/guest1/rootfs.ext4,format=raw,vdev=xvda,access=rw,backendtype=phy'; then
    printf 'ERROR: old input unexpectedly passed\n'
    exit 1
fi
probe 'format=raw,vdev=xvda,access=rw,backendtype=phy,target=/var/lib/xen/images/guest1/rootfs.ext4'
