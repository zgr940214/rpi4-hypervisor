# Same upstream release; authenticated XZ archive, not a gzip hash override.
# Evidence: docs/xen-lab/evidence/source-mirrors/20261028/gnu-xz/.
SRC_URI:remove = "${GNU_MIRROR}/patch/patch-${PV}.tar.gz"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/p/patch/patch_${PV}.orig.tar.xz;downloadfilename=patch-${PV}.tar.xz"
SRC_URI[md5sum] = "78ad9937e4caadcba1526ef1853730d5"
SRC_URI[sha256sum] = "ac610bda97abe0d9f6b7c963255a11dcb196c25e337c61f94e4778d632f1d8fd"
require recipes-devtools/host-xz-bootstrap.inc
