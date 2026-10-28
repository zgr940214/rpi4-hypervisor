require xen-source.inc

# Enable only the services needed for a manually created ARM PV guest.
SYSTEMD_SERVICE:${PN}-xencommons = "proc-xen.mount xenstored.service xenconsoled.service xen-init-dom0.service"
SYSTEMD_AUTO_ENABLE:${PN}-xendomains = "disable"
SYSTEMD_AUTO_ENABLE:${PN}-xen-watchdog = "disable"

# The manually started PV guest uses kernel blkback; no device-model QEMU is
# needed in Dom0. Remove the recipe recommendation as well as the image hint.
RRECOMMENDS:${PN}:remove = "qemu"
