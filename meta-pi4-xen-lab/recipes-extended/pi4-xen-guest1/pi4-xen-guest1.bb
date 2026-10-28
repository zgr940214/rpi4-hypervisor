SUMMARY = "The guest1 kernel, writable disk image, and Xen configuration"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://guest1.cfg.in"
S = "${WORKDIR}"
PACKAGE_ARCH = "${MACHINE_ARCH}"

# These real task edges rebuild this package after either guest rootfs or the
# shared Linux Image changes. The guest image never depends on this package.
do_install[depends] += "pi4-guest1-image:do_image_complete virtual/kernel:do_deploy"

do_install() {
    install -d ${D}${sysconfdir}/xen ${D}${localstatedir}/lib/xen/images/guest1
    install -m 0644 ${DEPLOY_DIR_IMAGE}/${KERNEL_IMAGETYPE} \
        ${D}${localstatedir}/lib/xen/images/guest1/Image
    cp --sparse=always --dereference ${DEPLOY_DIR_IMAGE}/pi4-guest1.ext4 \
        ${D}${localstatedir}/lib/xen/images/guest1/rootfs.ext4
    chmod 0600 ${D}${localstatedir}/lib/xen/images/guest1/rootfs.ext4
    sed -e 's/@@GUEST_MEMORY@@/${PI4_GUEST1_MEMORY_MIB}/g' \
        -e 's/@@GUEST_VCPUS@@/${PI4_GUEST1_VCPUS}/g' \
        ${WORKDIR}/guest1.cfg.in > ${D}${sysconfdir}/xen/guest1.cfg
    chmod 0644 ${D}${sysconfdir}/xen/guest1.cfg
}

FILES:${PN} = "${sysconfdir}/xen/guest1.cfg ${localstatedir}/lib/xen/images/guest1"
CONFFILES:${PN} = "${sysconfdir}/xen/guest1.cfg"
RDEPENDS:${PN} = "xen-tools-xl xen-tools-scripts-block util-linux-losetup"

# The kernel is an Image payload, not a userspace ELF to strip or debug-split.
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
