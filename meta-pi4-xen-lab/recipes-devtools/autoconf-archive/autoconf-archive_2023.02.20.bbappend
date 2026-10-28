# The upstream tag contains the complete installed m4 payload. Directly
# installing those source files avoids generating optional manuals and
# bootstrapping gnulib's release-maintenance tooling. No binary is supplied.
SRC_URI:remove = "${GNU_MIRROR}/${BPN}/${BPN}-${PV}.tar.xz"
SRC_URI:append = " git://github.com/autoconf-archive/autoconf-archive.git;protocol=https;nobranch=1"
SRCREV = "4cd9fa38f0f6cd6998a8d25d25824a0d59ee4fea"
S = "${WORKDIR}/git"

do_configure[noexec] = "1"
do_compile[noexec] = "1"
do_install() {
    install -d ${D}${datadir}/aclocal ${D}${docdir}/${BPN}
    install -m 0644 ${S}/m4/*.m4 ${D}${datadir}/aclocal/
    install -m 0644 ${S}/COPYING ${S}/COPYING.EXCEPTION ${S}/README.md ${D}${docdir}/${BPN}/
}
