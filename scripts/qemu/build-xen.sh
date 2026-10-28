#!/usr/bin/env bash
set -euo pipefail
cd /work
source_dir=/work/.cache/qemu/xen
output_dir=/work/local/qemu
revision=026c9fa29716b0ff0f8b7c687908e71ba29cf239
mkdir -p "$output_dir" /work/.cache/qemu
if [[ ! -d $source_dir/.git ]]; then
    git init -q "$source_dir"
    git -C "$source_dir" remote add origin https://github.com/xen-project/xen.git
    git -C "$source_dir" fetch --depth=1 origin "$revision"
    git -C "$source_dir" checkout --detach "$revision"
fi
[[ $(git -C "$source_dir" rev-parse HEAD) == "$revision" ]]
cd "$source_dir"
export PKG_CONFIG_LIBDIR=/usr/lib/aarch64-linux-gnu/pkgconfig:/usr/share/pkgconfig
make -C xen XEN_TARGET_ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
make -C xen -j2 XEN_TARGET_ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
install -m 0644 xen/xen "$output_dir/xen"
install -m 0644 xen/.config "$output_dir/xen.config"
./configure --build=x86_64-linux-gnu --host=aarch64-linux-gnu \
    --prefix=/usr --libdir=/usr/lib --disable-xen --disable-docs \
    --disable-stubdom --disable-ocamltools --disable-golang --disable-monitors \
    --disable-rombios --disable-seabios --disable-ovmf --disable-systemd \
    --disable-xsmpolicy --with-system-qemu=/bin/false --with-xenstored=xenstored
# Build the C toolstack needed for ARM PV guests. Python legacy bindings are
# deliberately outside this validation target; xl does not depend on them.
make install-tools-public-headers XEN_TARGET_ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    DESTDIR="$output_dir/xen-tools"
for component in libs xs-clients xenstored misc examples hotplug console xl helpers; do
    make -C tools -j2 "subdir-install-$component" XEN_TARGET_ARCH=arm64 \
        CROSS_COMPILE=aarch64-linux-gnu- DESTDIR="$output_dir/xen-tools"
done
install -d -m 0755 "$output_dir/xen-tools/var/log/xen" "$output_dir/xen-tools/var/lib/xen"
printf '%s\n' "$revision" > "$output_dir/xen-source-commit.txt"
file "$output_dir/xen" "$output_dir/xen-tools/usr/sbin/xl"
