SUMMARY = "Unpartitioned ext4 root filesystem for the single Xen guest"
LICENSE = "MIT"
inherit core-image

IMAGE_INSTALL = "packagegroup-core-boot pi4-xen-guest-console pi4-xen-runtime-guest util-linux-agetty"
IMAGE_FEATURES = "empty-root-password allow-empty-password"
IMAGE_FSTYPES = "ext4"
IMAGE_LINK_NAME = "pi4-guest1"
IMAGE_ROOTFS_SIZE = "262144"
IMAGE_ROOTFS_EXTRA_SPACE = "32768"
IMAGE_OVERHEAD_FACTOR = "1.2"

# No outer-image package, boot script, or Wic recursion belongs in this rootfs.
EXTRA_IMAGEDEPENDS = ""
BAD_RECOMMENDATIONS:append = " kernel-modules"

ROOTFS_POSTPROCESS_COMMAND:append = " pi4_guest1_identity;"
pi4_guest1_identity() {
    printf 'guest1\n' > ${IMAGE_ROOTFS}${sysconfdir}/hostname
    printf '127.0.0.1 localhost guest1\n::1 localhost\n' > ${IMAGE_ROOTFS}${sysconfdir}/hosts
}
