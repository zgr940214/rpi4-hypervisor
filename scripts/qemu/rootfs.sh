#!/usr/bin/env bash
# Build a Debian ARM64 validation rootfs, separate from the Yocto Pi4 image.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
action=${1:-prepare}

if [[ $action != --inside ]]; then
    mkdir -p "$project_dir/local/qemu/rootfs-builder" "$project_dir/local/qemu/logs"
    proot_source="$project_dir/local/qemu/rootfs-builder/proot"
    if [[ ! -d $proot_source/.git ]]; then
        git clone --depth 1 --branch v5.4.0 https://github.com/proot-me/proot.git "$proot_source"
    fi
    [[ $(git -C "$proot_source" rev-parse HEAD) == bd5a5f63d72f8210d8cee76195eb9f0749e5bd70 ]]
    [[ -z $(git -C "$proot_source" status --porcelain) ]] || {
        printf 'Refusing modified PRoot source; preserve local changes before rebuilding.\n' >&2
        exit 1
    }
    cat > "$project_dir/local/qemu/rootfs-builder/Dockerfile" <<'EOF'
FROM debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3
RUN --mount=type=secret,id=ca_bundle,mode=0444 \
    printf 'Acquire::https::CaInfo "/run/secrets/ca_bundle";\n' > /etc/apt/apt.conf.d/99-session-ca; \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      debootstrap debian-archive-keyring qemu-user-static proot e2fsprogs cpio xz-utils \
      ca-certificates wget gnupg rsync file && \
    rm /etc/apt/apt.conf.d/99-session-ca && rm -rf /var/lib/apt/lists/*
COPY proot /tmp/proot
RUN --mount=type=secret,id=ca_bundle,mode=0444 \
    printf 'Acquire::https::CaInfo "/run/secrets/ca_bundle";\n' > /etc/apt/apt.conf.d/99-session-ca; \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential libtalloc-dev pkg-config && \
    make -C /tmp/proot/src -j2 && install -m 0755 /tmp/proot/src/proot /usr/local/bin/proot && \
    rm /etc/apt/apt.conf.d/99-session-ca && rm -rf /var/lib/apt/lists/* /tmp/proot
WORKDIR /work
EOF
    docker build --secret id=ca_bundle,src=/etc/ssl/certs/ca-certificates.crt \
        -t pi4-xen-rootfs-builder:bookworm "$project_dir/local/qemu/rootfs-builder"
    [[ $action == build-tools ]] && exit 0
    exec docker run --rm --user 0:0 \
        --mount "type=bind,src=$project_dir,dst=/work" \
        --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/host-ca-bundle.pem,readonly \
        pi4-xen-rootfs-builder:bookworm /work/scripts/qemu/rootfs.sh --inside
fi

cd /work
rootfs=/work/local/qemu/rootfs
mkdir -p "$rootfs" /work/local/qemu/logs
export WGETRC=/tmp/qemu-rootfs-wgetrc
printf 'ca_certificate = /run/host-ca-bundle.pem\n' > "$WGETRC"
if [[ ! -e $rootfs/debootstrap/debootstrap && ! -e $rootfs/etc/debian_version ]]; then
    debootstrap --foreign --arch=arm64 --variant=minbase \
        --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
        bookworm "$rootfs" https://deb.debian.org/debian
fi
arm_run() {
    proot -0 -r "$rootfs" -q /usr/bin/qemu-aarch64-static \
        -b /proc -b /sys -b /dev -b /etc/resolv.conf \
        -b /run/host-ca-bundle.pem:/run/session-ca.pem \
        -w / /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin \
        HOME=/root LC_ALL=C DEBIAN_FRONTEND=noninteractive \
        http_proxy="${http_proxy:-${HTTP_PROXY:-}}" \
        https_proxy="${https_proxy:-${HTTPS_PROXY:-}}" \
        "$@"
}
if [[ -e $rootfs/debootstrap/debootstrap ]]; then
    if [[ -L $rootfs/proc ]]; then rm "$rootfs/proc"; fi
    mkdir -p "$rootfs/proc"
    arm_run /usr/bin/env DEBOOTSTRAP_DIR=/debootstrap /bin/sh /debootstrap/debootstrap --second-stage
fi
cat > "$rootfs/usr/sbin/policy-rc.d" <<'EOF'
#!/bin/sh
exit 101
EOF
chmod 0755 "$rootfs/usr/sbin/policy-rc.d"
cat > "$rootfs/etc/apt/sources.list" <<'EOF'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian bookworm main
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian-security bookworm-security main
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian bookworm-updates main
EOF
printf 'Acquire::https::CaInfo "/run/session-ca.pem";\n' > "$rootfs/etc/apt/apt.conf.d/99-session-ca"
arm_run /bin/sh -c 'apt-get update && apt-get install -y --no-install-recommends systemd-sysv udev openssh-server iproute2 iputils-ping procps util-linux kmod initramfs-tools busybox-static linux-image-arm64 libyajl2 libaio1 libfdt1 libpixman-1-0 libzstd1 liblzma5 zlib1g libncurses6 libtinfo6 libnl-3-200 libnl-route-3-200 libglib2.0-0 libuuid1 libbz2-1.0 libzstd1 libpng16-16 libvdeplug2 python3'

printf 'pi4-dom0\n' > "$rootfs/etc/hostname"
mkdir -p "$rootfs/etc/systemd/system/serial-getty@hvc0.service.d"
cat > "$rootfs/etc/systemd/system/serial-getty@hvc0.service.d/autologin.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear --keep-baud 115200,38400,9600 %I $TERM
EOF
mkdir -p "$rootfs/etc/systemd/system/getty.target.wants"
ln -sf /lib/systemd/system/serial-getty@.service "$rootfs/etc/systemd/system/getty.target.wants/serial-getty@hvc0.service"
arm_run passwd -d root
install -m 0755 scripts/target/guest1-start scripts/target/guest1-pause-demo "$rootfs/usr/sbin/"
install -m 0644 scripts/target/guest1-common.sh "$rootfs/usr/sbin/"
install -m 0755 scripts/target/guest1-counter "$rootfs/usr/bin/"
mkdir -p "$rootfs/root/.ssh"
install -m 0600 local/credentials/id_ed25519.pub "$rootfs/root/.ssh/authorized_keys"
chmod 0700 "$rootfs/root/.ssh"
cat > "$rootfs/etc/ssh/sshd_config.d/10-qemu-lab.conf" <<'EOF'
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
EOF
mkdir -p "$rootfs/etc/systemd/network" "$rootfs/etc/systemd/system/multi-user.target.wants"
cat > "$rootfs/etc/systemd/network/20-wired.network" <<'EOF'
[Match]
Name=en* eth*
[Network]
DHCP=yes
EOF
ln -sf /lib/systemd/system/systemd-networkd.service "$rootfs/etc/systemd/system/multi-user.target.wants/systemd-networkd.service"
cat > "$rootfs/etc/fstab" <<'EOF'
/dev/root / ext4 defaults 0 1
EOF
kernel=$(find "$rootfs/boot" -maxdepth 1 -name 'vmlinuz-*' -printf '%f\n' | sort -V | tail -1)
version=${kernel#vmlinuz-}
printf 'MODULES=list\n' > "$rootfs/etc/initramfs-tools/conf.d/qemu-modules"
for module in virtio_mmio virtio_blk virtio_net xen_blkfront xen_blkback loop ext4; do
    if find "$rootfs/lib/modules/$version" -name "${module//_/-}.ko*" -o -name "${module}.ko*" | grep -q .; then
        grep -qx "$module" "$rootfs/etc/initramfs-tools/modules" || printf '%s\n' "$module" >> "$rootfs/etc/initramfs-tools/modules"
    fi
done
arm_run update-initramfs -u -k "$version"
cp "$rootfs/boot/$kernel" /work/local/qemu/Image
cp "$rootfs/boot/initrd.img-$version" /work/local/qemu/initrd.img
cp "$rootfs/boot/config-$version" /work/local/qemu/kernel.config
arm_run dpkg-query -W > /work/local/qemu/logs/rootfs-packages.tsv
audit=$(arm_run dpkg --audit)
if [[ -n $audit ]]; then
    printf '%s\n' "$audit" >&2
    exit 1
fi
rm -f "$rootfs/etc/apt/apt.conf.d/99-session-ca"
printf 'PASS: ARM64 Debian rootfs, kernel and initrd prepared; Xen tools and disk export remain separate.\n'
