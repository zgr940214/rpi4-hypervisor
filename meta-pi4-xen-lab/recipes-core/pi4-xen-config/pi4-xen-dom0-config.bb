SUMMARY = "Dom0 public-key SSH, wired DHCP, and Xen service startup"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
inherit allarch systemd

FILESEXTRAPATHS:prepend := "${PI4_XEN_ACCESS_DIR}:"
SRC_URI = "file://id_ed25519.pub file://10-pi4-xen.conf file://20-wired.network file://pi4-xen-ready.service"
S = "${WORKDIR}"

SYSTEMD_SERVICE:${PN} = "pi4-xen-ready.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install() {
    install -d -m 0700 ${D}/root/.ssh
    install -m 0600 ${WORKDIR}/id_ed25519.pub ${D}/root/.ssh/authorized_keys
    install -d ${D}${sysconfdir}/ssh/sshd_config.d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${WORKDIR}/10-pi4-xen.conf ${D}${sysconfdir}/ssh/sshd_config.d/
    install -m 0644 ${WORKDIR}/20-wired.network ${D}${sysconfdir}/systemd/network/
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/pi4-xen-ready.service ${D}${systemd_system_unitdir}/
    install -d ${D}${sysconfdir}/systemd/system/multi-user.target.wants
    ln -s ${systemd_system_unitdir}/systemd-networkd.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/systemd-networkd.service
    ln -s ${systemd_system_unitdir}/systemd-resolved.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/systemd-resolved.service
}

FILES:${PN} += "/root/.ssh ${systemd_system_unitdir}/pi4-xen-ready.service"
RDEPENDS:${PN} = "openssh-sshd systemd xen-tools-xencommons xen-tools-xl"
