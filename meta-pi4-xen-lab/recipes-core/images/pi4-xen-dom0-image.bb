SUMMARY = "Bootable Pi4 Xen Dom0 image with one manually started Linux guest"
LICENSE = "MIT"
inherit core-image extrausers
require pi4-xen-image-provenance.inc

IMAGE_FEATURES = "ssh-server-openssh"
IMAGE_INSTALL = " \
    packagegroup-core-boot \
    xen-tools-xl xen-tools-console xen-tools-xenstore xen-tools-xencommons \
    xen-tools-scripts-block xen-tools-libxenlight \
    pi4-xen-dom0-config pi4-xen-runtime-dom0 pi4-xen-guest1 \
    util-linux-losetup util-linux-lsblk coreutils \
    systemd \
    "
IMAGE_FSTYPES = "wic wic.bmap"
WKS_FILE = "pi4-xen.wks"
WKS_SEARCH_PATH:append = ":${PI4_XEN_LAYERDIR}/wic"
# This ARM card has only FAT/ext4 partitions. ISO9660, Syslinux, Btrfs,
# SquashFS and EROFS host tools are not used by its Wic plugins.
WKS_FILE_DEPENDS = "parted-native dosfstools-native mtools-native bmaptool-native e2fsprogs-native gptfdisk-native virtual/${TARGET_PREFIX}binutils"
IMAGE_ROOTFS_EXTRA_SPACE = "262144"
IMAGE_OVERHEAD_FACTOR = "1.3"

# Export inspections use the built e2fsprogs version, including orphan_file support.
# rm_work may remove the rootfs and task work but must retain these host tools.
RM_WORK_EXCLUDE_ITEMS:append = " recipe-sysroot-native"

IMAGE_BOOT_FILES:append = " xen-${MACHINE};xen"
do_image_wic[depends] += "xen:do_deploy u-boot-default-script:do_deploy"

# The locally generated password is for the Dom0 serial console. SSH remains
# public-key-only through the config package and the leading Include below.
EXTRA_USERS_PARAMS = "usermod -p '${PI4_XEN_ROOT_PASSWORD_HASH}' root;"

ROOTFS_POSTPROCESS_COMMAND:append = " pi4_dom0_identity;"
python pi4_dom0_identity() {
    from pathlib import Path
    root = Path(d.getVar('IMAGE_ROOTFS'))
    (root / 'etc/hostname').write_text('pi4-dom0\n')
    (root / 'etc/hosts').write_text('127.0.0.1 localhost pi4-dom0\n::1 localhost\n')
    sshd = root / 'etc/ssh/sshd_config'
    include = 'Include /etc/ssh/sshd_config.d/*.conf\n'
    config = sshd.read_text()
    if not config.startswith(include):
        sshd.write_text(include + config)
}
