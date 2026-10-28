require xen-source.inc

do_deploy:append() {
    install -m 0644 ${B}/xen/.config ${DEPLOYDIR}/xen-final.config
}
