#!/usr/bin/env bash
# Package the real QEMU root filesystems after the matching Xen tools build.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
if [[ ${1:-} != --inside ]]; then
    exec docker run --rm --user 0:0 \
        --mount "type=bind,src=$project_dir,dst=/work" \
        pi4-xen-rootfs-builder:bookworm /work/scripts/qemu/export-rootfs.sh --inside
fi
cd /work
rootfs=/work/local/qemu/rootfs
guestfs=/work/local/qemu/guest-rootfs
tools=/work/local/qemu/xen-tools
test -f /work/local/qemu/Image
test -f /work/local/qemu/initrd.img
test -x "$tools/usr/sbin/xl"
test -x "$rootfs/lib/systemd/systemd"
if [[ ! -d $guestfs ]]; then
    mkdir "$guestfs"
    # Never copy an already embedded guest disk back into the guest rootfs.
    rsync -a --exclude=/var/lib/xen/images/guest1 "$rootfs/" "$guestfs/"
fi
kernel_version=$(basename "$(readlink -f "$rootfs/vmlinuz")")
kernel_version=${kernel_version#vmlinuz-}
test -d "$rootfs/lib/modules/$kernel_version"
mkdir -p "$guestfs/lib/modules"
rsync -a "$rootfs/lib/modules/$kernel_version" "$guestfs/lib/modules/"
install -m 0755 scripts/target/guest1-counter "$guestfs/usr/bin/"
printf 'guest1\n' > "$guestfs/etc/hostname"
printf '127.0.0.1 localhost guest1\n::1 localhost\n' > "$guestfs/etc/hosts"
printf 'LABEL=guest1 / ext4 defaults 0 1\n' > "$guestfs/etc/fstab"
rm -f "$guestfs/root/.ssh/authorized_keys"
mkdir -p "$guestfs/etc/systemd/system"
ln -sf /dev/null "$guestfs/etc/systemd/system/ssh.service"
rm -f "$guestfs/etc/systemd/system/multi-user.target.wants/qemu-xen.service"
ln -sf /dev/null "$guestfs/etc/systemd/system/qemu-xen.service"
truncate -s 0 "$guestfs/etc/machine-id"
rsync -a --chown=0:0 "$tools/" "$rootfs/"
install -m 0755 scripts/target/guest1-start scripts/target/guest1-pause-demo "$rootfs/usr/sbin/"
install -m 0644 scripts/target/guest1-common.sh "$rootfs/usr/sbin/"
for script in guest1-start guest1-pause-demo guest1-common.sh; do
    cmp "scripts/target/$script" "$rootfs/usr/sbin/$script"
done
proot -0 -r "$rootfs" -q /usr/bin/qemu-aarch64-static -w / /sbin/ldconfig
mkdir -p "$rootfs/usr/local/sbin" "$rootfs/etc/systemd/system/multi-user.target.wants"
cat > "$rootfs/usr/local/sbin/qemu-xen-start" <<'EOF'
#!/bin/bash
set -euo pipefail
grep -qx xen /sys/hypervisor/type
for driver in xenfs xen-evtchn xen-privcmd xen-gntdev xen-blkback loop; do
    modprobe "$driver"
done
mkdir -p /proc/xen /run/xen /run/lock/xen /var/log/xen
mountpoint -q /proc/xen || mount -t xenfs xenfs /proc/xen
grep -q control_d /proc/xen/capabilities
/etc/xen/scripts/launch-xenstore
init_dom0=$(find /usr/lib -type f -name xen-init-dom0 -print -quit)
test -n "$init_dom0"
"$init_dom0"
/usr/sbin/xenconsoled --pid-file=/run/xen/xenconsoled.pid
/usr/sbin/xl info
EOF
chmod 0755 "$rootfs/usr/local/sbin/qemu-xen-start"
cat > "$rootfs/etc/systemd/system/qemu-xen.service" <<'EOF'
[Unit]
Description=Start the matching Xen toolstack for the QEMU PV guest lab
After=systemd-udev-settle.service local-fs.target
Wants=systemd-udev-settle.service
ConditionPathExists=/sys/hypervisor/type

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/qemu-xen-start
RemainAfterExit=yes
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF
ln -sf /etc/systemd/system/qemu-xen.service "$rootfs/etc/systemd/system/multi-user.target.wants/qemu-xen.service"
# The upstream SysV aggregate unconditionally starts a QEMU device model.
# This lab is PV-only, and the explicit service above starts only its needs.
ln -sf /dev/null "$rootfs/etc/systemd/system/xencommons.service"
printf 'pi4-dom0\n' > "$rootfs/etc/hostname"
printf '127.0.0.1 localhost pi4-dom0\n::1 localhost\n' > "$rootfs/etc/hosts"
printf 'LABEL=dom0 / ext4 defaults 0 1\n' > "$rootfs/etc/fstab"
truncate -s 0 "$rootfs/etc/machine-id"
mkdir -p "$rootfs/etc/xen" "$rootfs/var/lib/xen/images/guest1"
install -m 0644 /work/local/qemu/Image "$rootfs/var/lib/xen/images/guest1/Image"
install -m 0644 /work/local/qemu/initrd.img "$rootfs/var/lib/xen/images/guest1/initrd.img"
for directory in "$rootfs" "$guestfs"; do
    rm -f "$directory/usr/sbin/policy-rc.d"
    rm -f "$directory/etc/apt/apt.conf.d/99-session-ca"
    find "$directory/var/cache/apt/archives" -maxdepth 1 -type f -name '*.deb' -delete
    for timer in apt-daily.timer apt-daily-upgrade.timer; do
        ln -sf /dev/null "$directory/etc/systemd/system/$timer"
    done
done

guest_image=/work/local/qemu/guest1.ext4
truncate -s 1536M "$guest_image.new"
mkfs.ext4 -F -q -L guest1 -d "$guestfs" "$guest_image.new"
e2fsck -fn "$guest_image.new"
mv "$guest_image.new" "$guest_image"
cp --sparse=always "$guest_image" "$rootfs/var/lib/xen/images/guest1/rootfs.ext4"
chmod 0600 "$rootfs/var/lib/xen/images/guest1/rootfs.ext4"
cat > "$rootfs/etc/xen/guest1.cfg" <<'EOF'
name = "guest1"
memory = 256
vcpus = 1
kernel = "/var/lib/xen/images/guest1/Image"
ramdisk = "/var/lib/xen/images/guest1/initrd.img"
disk = ["format=raw,vdev=xvda,access=rw,backendtype=phy,target=/var/lib/xen/images/guest1/rootfs.ext4"]
extra = "console=hvc0 root=/dev/xvda rw rootwait"
on_poweroff = "destroy"
on_reboot = "destroy"
on_crash = "destroy"
EOF
dom0_image=/work/local/qemu/dom0.ext4
truncate -s 4096M "$dom0_image.new"
mkfs.ext4 -F -q -L dom0 -d "$rootfs" "$dom0_image.new"
e2fsck -fn "$dom0_image.new"
mv "$dom0_image.new" "$dom0_image"
chown 1000:1000 /work/local/qemu/{Image,initrd.img,kernel.config,dom0.ext4,guest1.ext4}
printf 'PASS: QEMU Dom0 and guest filesystems exported with matching Xen tools.\n'
