SUMMARY = "Bounded single-guest startup and pause/resume lab tools"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
inherit allarch

FILESEXTRAPATHS:prepend := "${PI4_XEN_LAYERDIR}/../scripts/target:"
SRC_URI = "file://guest1-common.sh file://guest1-start file://guest1-pause-demo file://guest1-counter"
S = "${WORKDIR}"
PACKAGES = "${PN}-dom0 ${PN}-guest"

do_install() {
    install -d ${D}${sbindir} ${D}${bindir}
    install -m 0644 ${WORKDIR}/guest1-common.sh ${D}${sbindir}/guest1-common.sh
    install -m 0755 ${WORKDIR}/guest1-start ${WORKDIR}/guest1-pause-demo ${D}${sbindir}/
    install -m 0755 ${WORKDIR}/guest1-counter ${D}${bindir}/
}
FILES:${PN}-dom0 = "${sbindir}/guest1-common.sh ${sbindir}/guest1-start ${sbindir}/guest1-pause-demo"
FILES:${PN}-guest = "${bindir}/guest1-counter"
RDEPENDS:${PN}-dom0 = "xen-tools-xl"
