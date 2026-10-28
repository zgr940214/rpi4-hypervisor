# Optional source mirrors; recipe SRCREV values and archive checksums remain enforced.
# The Pi4 kernel version/revision is pinned explicitly in its bbappend.
PREMIRRORS:prepend = " \
    https://ftpmirror.gnu.org/gnu/bison/bison-3.8.2.tar.xz https://mirror.bazel.build/ftp.gnu.org/gnu/bison/bison-3.8.2.tar.xz \
    https://zlib.net/zlib-1.3.1.tar.gz https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz \
    git://sourceware.org/git/binutils-gdb.git git://github.com/RTEMS/sourceware-mirror-binutils-gdb.git;protocol=https \
    git://git.kernel.org/pub/scm/linux/kernel/git/kdave/btrfs-progs.git git://github.com/kdave/btrfs-progs.git;protocol=https \
    git://salsa.debian.org/debian/debianutils.git git://github.com/CodeLinaro-mirror/yocto-mirrors_debianutils.git;protocol=https \
    git://git.kernel.org/pub/scm/utils/dtc/dtc.git git://github.com/dgibson/dtc.git;protocol=https \
    git://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git git://github.com/tytso/e2fsprogs.git;protocol=https \
    git://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git git://github.com/erofs/erofs-utils.git;protocol=https \
    git://sourceware.org/git/glibc.git git://github.com/CodeLinaro-mirror/yocto-mirrors_glibc.git;protocol=https \
    git://git.savannah.gnu.org/git/config.git git://github.com/chipp/gnu-config.git;protocol=https \
    git://git.yoctoproject.org/yocto-kernel-tools.git git://github.com/CodeLinaro-mirror/yocto-mirrors_yocto-kernel-tools.git;protocol=https \
    git://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git git://github.com/kmod-project/kmod.git;protocol=https \
    git://codeberg.org/jmoyer/libaio.git git://github.com/CodeLinaro-mirror/yocto-mirrors_libaio.git;protocol=https \
    git://gitlab.freedesktop.org/slirp/libslirp.git git://github.com/CodeLinaro-mirror/yocto-mirrors_libslirp.git;protocol=https \
    git://gitlab.gnome.org/GNOME/mobile-broadband-provider-info.git git://github.com/CodeLinaro-mirror/yocto-mirrors_mobile-broadband-provider-info.git;protocol=https \
    git://git.yoctoproject.org/opkg-utils git://github.com/CodeLinaro-mirror/yocto-mirrors_opkg-utils.git;protocol=https \
    git://gitlab.freedesktop.org/pkg-config/pkg-config.git git://github.com/CodeLinaro-mirror/yocto-mirrors_pkg-config.git;protocol=https \
    git://git.yoctoproject.org/pseudo git://github.com/CodeLinaro-mirror/yocto-mirrors_pseudo.git;protocol=https \
    git://gitlab.freedesktop.org/xdg/shared-mime-info.git git://github.com/CodeLinaro-mirror/yocto-mirrors_shared-mime-info.git;protocol=https \
    git://source.denx.de/u-boot/u-boot.git git://github.com/u-boot/u-boot.git;protocol=https \
    git://git.yoctoproject.org/update-rc.d git://github.com/CodeLinaro-mirror/yocto-mirrors_update-rc.d.git;protocol=https \
    git://git.yoctoproject.org/linux-yocto.git git://github.com/WindRiverLinux24/linux-yocto-6.6.git;protocol=https \
    git://git.yoctoproject.org/yocto-kernel-cache git://github.com/jhnc-oss/yocto-kernel-cache.git;protocol=https \
    git://sourceware.org/git/bzip2-tests.git git://github.com/CodeLinaro-mirror/qrdk_bzip2-tests.git;protocol=https \
    git://git.kernel.org/pub/scm/network/bridge/bridge-utils.git git://github.com/CodeLinaro-mirror/yocto-mirrors_bridge-utils.git;protocol=https \
    git://codeberg.org/xmlto/xmlto.git git://gitlab.com/freedesktop-sdk/mirrors/pagure/xmlto.git;protocol=https \
    git://salsa.debian.org/debian/ifupdown.git git://github.com/kmluoh/ifupdown.git;protocol=https \
"
