# Same upstream release, XZ distribution authenticated by Debian's signed
# source index. This explicitly selects a different compressed archive.
# Evidence: docs/xen-lab/evidence/source-mirrors/20261028/gnu-xz/.
SRC_URI:remove = "${GNU_MIRROR}/automake/automake-${PV}.tar.gz"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/a/automake-1.16/automake-1.16_${PV}.orig.tar.xz;downloadfilename=automake-${PV}.tar.xz"
SRC_URI[sha256sum] = "f01d58cd6d9d77fbdca9eb4bbd5ead1988228fdb73d6f7a201f5f8d6b118b469"
require recipes-devtools/host-xz-bootstrap.inc
