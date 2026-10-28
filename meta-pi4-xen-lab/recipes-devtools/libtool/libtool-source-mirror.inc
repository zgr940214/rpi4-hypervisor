# Same upstream release; authenticated XZ archive, not a gzip hash override.
# Evidence: docs/xen-lab/evidence/source-mirrors/20261028/gnu-xz/.
SRC_URI:remove = "${GNU_MIRROR}/libtool/libtool-${PV}.tar.gz"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/libt/libtool/libtool_${PV}.orig.tar.xz;downloadfilename=libtool-${PV}.tar.xz"
SRC_URI[sha256sum] = "dd637e270439b208907ceead3f163470ed2ce5723ef97ffbda6463c64b57128a"
require recipes-devtools/host-xz-bootstrap.inc
