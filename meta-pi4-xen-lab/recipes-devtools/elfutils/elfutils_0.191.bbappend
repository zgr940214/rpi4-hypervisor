# Same upstream elfutils-0.191 tag through the libbpf source mirror.
# Keep all distribution/CVE patches and licence checks unchanged.
SRC_URI:remove = "https://sourceware.org/elfutils/ftp/${PV}/${BP}.tar.bz2"
SRC_URI:append = " git://github.com/libbpf/elfutils-mirror.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "18a015c0b0787ba5acb39801ab7c17dac50f584d"

# autotools.bbclass installs gettext auxiliaries here when autopoint is skipped.
AUTOTOOLS_AUXDIR = "${S}/config"

# Release tarballs also include this standard gettext auxiliary. Poky's
# autoreconf skips autopoint, so install it from the built gettext-native.
DEPENDS:append = " gettext-native"
do_configure[prefuncs] += "pi4_elfutils_gettext_aux"
pi4_elfutils_gettext_aux() {
    install -m 0644 ${STAGING_DATADIR_NATIVE}/gettext/ABOUT-NLS ${S}/ABOUT-NLS
}

# Git omits the release's generated disassembler tables. Generate these on the
# build host, then stage the source headers for the cross build. Target binaries
# must never be executed as build tools.
DEPENDS:append:class-native = " bison-native flex-native"
EXTRA_OECONF:append:class-native = " --enable-maintainer-mode"
do_install:append:class-native() {
    install -d ${D}${datadir}/elfutils-source
    install -m 0644 ${S}/libcpu/i386_dis.h ${S}/libcpu/x86_64_dis.h ${D}${datadir}/elfutils-source/
}

DEPENDS:append:class-target = " elfutils-native"
do_configure:prepend:class-target() {
    install -m 0644 ${STAGING_DATADIR_NATIVE}/elfutils-source/i386_dis.h ${STAGING_DATADIR_NATIVE}/elfutils-source/x86_64_dis.h ${S}/libcpu/
    install -m 0644 ${STAGING_INCDIR_NATIVE}/elfutils/known-dwarf.h ${S}/libdw/
}

DEPENDS:append:class-nativesdk = " elfutils-native"
do_configure:prepend:class-nativesdk() {
    install -m 0644 ${STAGING_DATADIR_NATIVE}/elfutils-source/i386_dis.h ${STAGING_DATADIR_NATIVE}/elfutils-source/x86_64_dis.h ${S}/libcpu/
    install -m 0644 ${STAGING_INCDIR_NATIVE}/elfutils/known-dwarf.h ${S}/libdw/
}
