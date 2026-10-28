# Same original archives at verified URLs; original SHA256 checks remain enforced.
# Direct URI substitution permits distribution mirrors with different filenames.
# See docs/xen-lab/evidence/source-mirrors/20261028/archive-mirrors.json.
PI4_XEN_ARCHIVE_MIRRORS = " \
    http://ftp.debian.org/debian/pool/main/c/ca-certificates/ca-certificates_20260816.tar.xz https://deb.debian.org/debian/pool/main/c/ca-certificates/ca-certificates_20260816.tar.xz \
    http://ftp.debian.org/debian/pool/main/n/netbase/netbase_6.4.tar.xz https://deb.debian.org/debian/pool/main/n/netbase/netbase_6.4.tar.xz \
    http://ftp.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-9.6p1.tar.gz https://archive.ubuntu.com/ubuntu/pool/main/o/openssh/openssh_9.6p1.orig.tar.gz \
    http://libarchive.org/downloads/libarchive-3.7.9.tar.gz https://github.com/libarchive/libarchive/releases/download/v3.7.9/libarchive-3.7.9.tar.gz \
    http://netfilter.org/projects/iptables/files/iptables-1.8.10.tar.xz https://archive.ubuntu.com/ubuntu/pool/main/i/iptables/iptables_1.8.10.orig.tar.xz \
    http://www.openssl.org/source/openssl-3.5.9.tar.gz https://github.com/openssl/openssl/releases/download/openssl-3.5.9/openssl-3.5.9.tar.gz \
    http://www.thrysoee.dk/editline/libedit-20230828-3.1.tar.gz https://archive.ubuntu.com/ubuntu/pool/main/libe/libedit/libedit_3.1-20230828.orig.tar.gz \
    https://api.github.com/repos/raspberrypi/firmware/tarball/bc7f439c234e19371115e07b57c366df59cc1bc7 https://codeload.github.com/raspberrypi/firmware/legacy.tar.gz/bc7f439c234e19371115e07b57c366df59cc1bc7 \
    https://archive.hadrons.org/software/libmd/libmd-1.1.0.tar.xz https://deb.debian.org/debian/pool/main/libm/libmd/libmd_1.1.0.orig.tar.xz \
    https://busybox.net/downloads/busybox-1.36.1.tar.bz2 https://archive.ubuntu.com/ubuntu/pool/main/b/busybox/busybox_1.36.1.orig.tar.bz2 \
    https://cdn.kernel.org/pub/linux/utils/util-linux/v2.39/util-linux-2.39.3.tar.xz https://archive.ubuntu.com/ubuntu/pool/main/u/util-linux/util-linux_2.39.3.orig.tar.xz \
    https://cmake.org/files/v3.28/cmake-3.28.3.tar.gz https://archive.ubuntu.com/ubuntu/pool/main/c/cmake/cmake_3.28.3.orig.tar.gz \
    https://curl.se/download/curl-8.7.1.tar.xz https://github.com/curl/curl/releases/download/curl-8_7_1/curl-8.7.1.tar.xz \
    https://dbus.freedesktop.org/releases/dbus/dbus-1.14.10.tar.xz https://deb.debian.org/debian/pool/main/d/dbus/dbus_1.14.10.orig.tar.xz \
    https://download.gnome.org/sources//gtk-doc/1.33/gtk-doc-1.33.2.tar.xz https://deb.debian.org/debian/pool/main/g/gtk-doc/gtk-doc_1.33.2.orig.tar.xz \
    https://download.samba.org/pub/rsync/src/rsync-3.2.7.tar.gz https://deb.debian.org/debian/pool/main/r/rsync/rsync_3.2.7.orig.tar.gz \
    https://downloads.sourceforge.net/gptfdisk/1.0.9/gptfdisk-1.0.9.tar.gz https://deb.debian.org/debian/pool/main/g/gdisk/gdisk_1.0.9.orig.tar.gz \
    https://ftpmirror.gnu.org/gnu/bc/bc-1.07.1.tar.gz https://deb.debian.org/debian/pool/main/b/bc/bc_1.07.1.orig.tar.gz \
    https://ftpmirror.gnu.org/gnu/coreutils/coreutils-9.4.tar.xz https://archive.ubuntu.com/ubuntu/pool/main/c/coreutils/coreutils_9.4.orig.tar.xz \
    https://ftpmirror.gnu.org/gnu/diffutils/diffutils-3.10.tar.xz https://deb.debian.org/debian/pool/main/d/diffutils/diffutils_3.10.orig.tar.xz \
    https://ftpmirror.gnu.org/gnu/findutils/findutils-4.9.0.tar.xz https://deb.debian.org/debian/pool/main/f/findutils/findutils_4.9.0.orig.tar.xz \
    https://ftpmirror.gnu.org/gnu/gdbm/gdbm-1.23.tar.gz https://deb.debian.org/debian/pool/main/g/gdbm/gdbm_1.23.orig.tar.gz \
    https://ftpmirror.gnu.org/gnu/libidn/libidn2-2.3.7.tar.gz https://archive.ubuntu.com/ubuntu/pool/main/libi/libidn2/libidn2_2.3.7.orig.tar.gz \
    https://ftpmirror.gnu.org/gnu/libmicrohttpd/libmicrohttpd-1.0.1.tar.gz https://deb.debian.org/debian/pool/main/libm/libmicrohttpd/libmicrohttpd_1.0.1.orig.tar.gz \
    https://ftpmirror.gnu.org/gnu/make/make-4.4.1.tar.gz https://mirror.bazel.build/ftpmirror.gnu.org/gnu/make/make-4.4.1.tar.gz \
    https://ftpmirror.gnu.org/gnu/mpc/mpc-1.3.1.tar.gz https://deb.debian.org/debian/pool/main/m/mpclib3/mpclib3_1.3.1.orig.tar.gz \
    https://ftpmirror.gnu.org/gnu/mtools/mtools-4.0.49.tar.bz2 https://deb.debian.org/debian/pool/main/m/mtools/mtools_4.0.49.orig.tar.bz2 \
    https://ftpmirror.gnu.org/gnu/nettle/nettle-3.9.1.tar.gz https://archive.ubuntu.com/ubuntu/pool/main/n/nettle/nettle_3.9.1.orig.tar.gz \
    https://ftpmirror.gnu.org/gnu/parted/parted-3.6.tar.xz https://deb.debian.org/debian/pool/main/p/parted/parted_3.6.orig.tar.xz \
    https://ftpmirror.gnu.org/gnu/readline/readline-8.2.tar.gz https://deb.debian.org/debian/pool/main/r/readline/readline_8.2.orig.tar.gz \
    https://launchpad.net/debian/+archive/primary/+files/base-passwd_3.6.8.tar.xz https://deb.debian.org/debian/pool/main/b/base-passwd/base-passwd_3.6.8.tar.xz \
    https://libbsd.freedesktop.org/releases/libbsd-0.12.1.tar.xz https://archive.ubuntu.com/ubuntu/pool/main/libb/libbsd/libbsd_0.12.1.orig.tar.xz \
    https://netfilter.org/projects/libmnl/files/libmnl-1.0.5.tar.bz2 https://deb.debian.org/debian/pool/main/libm/libmnl/libmnl_1.0.5.orig.tar.bz2 \
    https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz https://mirror.bazel.build/sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz \
    https://www.cairographics.org/releases/pixman-0.42.2.tar.gz https://deb.debian.org/debian/pool/main/p/pixman/pixman_0.42.2.orig.tar.gz \
    https://www.mpfr.org/mpfr-4.2.1/mpfr-4.2.1.tar.xz https://archive.ubuntu.com/ubuntu/pool/main/m/mpfr4/mpfr4_4.2.1.orig.tar.xz \
"
