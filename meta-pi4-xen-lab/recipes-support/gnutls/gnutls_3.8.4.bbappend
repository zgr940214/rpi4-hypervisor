# Build the same upstream 3.8.4 release from its immutable Git commit and
# the exact source gitlinks recorded by that release. Do not fetch developer
# test suites during configure or let bootstrap select moving dependencies.
FILESEXTRAPATHS:prepend := "${THISDIR}/gnutls:"
SRC_URI:remove = "https://www.gnupg.org/ftp/gcrypt/gnutls/v${SHRT_VER}/gnutls-${PV}.tar.xz"
SRC_URI:append = " \
    git://github.com/gnutls/gnutls.git;protocol=https;nobranch=1;name=gnutls;destsuffix=${BP} \
    git://gitlab.com/libidn/gnulib-mirror.git;protocol=https;nobranch=1;name=gnulib;destsuffix=${BP}/gnulib \
    git://gitlab.com/gnutls/nettle.git;protocol=https;nobranch=1;name=nettle;destsuffix=${BP}/devel/nettle \
    git://gitlab.com/gnutls/libtasn1.git;protocol=https;nobranch=1;name=libtasn1;destsuffix=${BP}/devel/libtasn1 \
    git://gitlab.com/gnutls/cligen.git;protocol=https;nobranch=1;name=cligen;destsuffix=${BP}/cligen \
    file://0001-bootstrap-allow-prepared-offline-submodules.patch \
"
SRCREV_gnutls = "4a4cefef6c194f8fbbffd7fb19651219421b085b"
SRCREV_gnulib = "41d5dae3b7d239f167f09e4398f3970845a0ddc0"
SRCREV_nettle = "236d79b8bc508ae089f63a75c16f87c7076babdf"
SRCREV_libtasn1 = "2b7ee166f031bea63c5e7badcedc69f1cea69c89"
SRCREV_cligen = "ed2ed7b19a5bcbc0f39505722058befc923eeeda"
SRCREV_FORMAT = "gnutls_gnulib_nettle_libtasn1_cligen"

# The release archive contains generated gnulib, command-line and autotools
# files. Generate them from the pinned inputs with Yocto's native tools.
DEPENDS:append = " gettext-native gperf-native bison-native libtasn1-native"
do_configure:prepend() {
    (
        cd ${S}
        GNUTLS_BOOTSTRAP_OFFLINE=yes ./bootstrap \
            --skip-po --no-git --gnulib-srcdir=gnulib --no-bootstrap-sync
    )
}
