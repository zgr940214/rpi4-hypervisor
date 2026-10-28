SUMMARY = "Guest-only hvc0 console login for the local Xen lab"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
inherit allarch

SRC_URI = "file://autologin.conf"
S = "${WORKDIR}"

do_install() {
    install -d ${D}${sysconfdir}/systemd/system/serial-getty@hvc0.service.d
    install -m 0644 ${WORKDIR}/autologin.conf \
        ${D}${sysconfdir}/systemd/system/serial-getty@hvc0.service.d/
}
# systemd-serialgetty owns the enabled hvc0 link, using SERIAL_CONSOLES from
# the distro. This package owns only the guest's autologin drop-in.
RDEPENDS:${PN} = "systemd systemd-serialgetty util-linux-agetty shadow-base"
