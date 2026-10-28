# Explicit same-release Debian DFSG source packaging, authenticated through
# Ubuntu Noble's signed source index. The repack removes the nonfree info
# manual, retains upstream man pages, and replaces doc/Makefile with no-op
# documentation rules. Runtime version 1.35, original COPYING checksum, and
# all seven Poky patches are retained. See source-mirrors/20261028/tar/.
SRC_URI:remove = "${GNU_MIRROR}/tar/tar-${PV}.tar.bz2"
SRC_URI:append = " https://archive.ubuntu.com/ubuntu/pool/main/t/tar/tar_${PV}+dfsg.orig.tar.xz;downloadfilename=tar-${PV}+dfsg.orig.tar.xz"
SRC_URI[sha256sum] = "9ae57e981c1e73c0eebc2b26c9b0c4497fe310ef1d516ea430efb5470b71f7a8"
S = "${WORKDIR}/tar-${PV}+dfsg"
