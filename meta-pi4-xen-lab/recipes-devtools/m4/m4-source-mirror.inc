# Select GNU's signed XZ release of the SAME m4 1.4.19 source version.
# This is a different upstream archive format, not an accepted mismatch of
# Poky's original gzip archive. GNU signature and independent Bazel digest
# evidence are recorded in docs/xen-lab/evidence/source-mirrors/20261028/m4/.
SRC_URI:remove = "${GNU_MIRROR}/m4/m4-${PV}.tar.gz"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/m/m4/m4_${PV}.orig.tar.xz;downloadfilename=m4-${PV}.tar.xz"
SRC_URI[md5sum] = "0d90823e1426f1da2fd872df0311298d"
SRC_URI[sha256sum] = "63aede5c6d33b6d9b13511cd0be2cac046f2e70fd0a07aa9573a04a82783af96"
require recipes-devtools/host-xz-bootstrap.inc
