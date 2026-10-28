require xen-source.inc

# Enable only the services needed for a manually created ARM PV guest.
SYSTEMD_SERVICE:${PN}-xencommons = "proc-xen.mount xenstored.service xenconsoled.service xen-init-dom0.service"
SYSTEMD_AUTO_ENABLE:${PN}-xendomains = "disable"
SYSTEMD_AUTO_ENABLE:${PN}-xen-watchdog = "disable"
